"""Orchestration: fetch -> dedupe -> score -> rank."""
from __future__ import annotations

import re
from dataclasses import dataclass

from tqdm import tqdm

from .config import Config
from .models import JobPosting, ScoredJob
from .scoring import build_scorer
from .sources import build_sources

# US state names and abbreviations used to detect and drop US-based postings.
_US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york", "north carolina",
    "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
    "rhode island", "south carolina", "south dakota", "tennessee", "texas",
    "utah", "vermont", "virginia", "washington", "west virginia",
    "wisconsin", "wyoming", "district of columbia",
}
_US_ABBREVS = re.compile(
    r"\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA"
    r"|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX"
    r"|UT|VT|VA|WA|WV|WI|WY|DC)\b"
)
_US_COUNTRY = re.compile(r"\b(united states|usa|u\.s\.a\.?|u\.s\.)\b", re.IGNORECASE)


def _is_us_location(job: JobPosting) -> bool:
    loc = job.location.lower()
    if _US_COUNTRY.search(loc) or _US_COUNTRY.search(job.description[:200].lower()):
        return True
    if any(state in loc for state in _US_STATES):
        return True
    # "City, XX" where XX is a two-letter US state abbreviation
    if re.search(r",\s*" + _US_ABBREVS.pattern, job.location):
        return True
    return False


@dataclass
class RunResult:
    scored: list[ScoredJob]
    fetched: int
    deduped: int
    scorer_mode: str
    sources_used: list[str]


def fetch_all(config: Config, per_source: int, verbose: bool = True) -> tuple[list[JobPosting], list[str]]:
    sources = build_sources(config)
    postings: list[JobPosting] = []
    used: list[str] = []

    for src in sources:
        if not src.available:
            if verbose:
                print(f"  - {src.name}: skipped (no credentials)")
            continue
        served = [c for c in config.countries if src.serves(c)]
        if not served:
            continue
        got = 0
        tasks = [(q, c) for q in config.queries for c in served]
        with tqdm(tasks, desc=f"{src.name}", unit="req", leave=False, disable=not verbose) as pbar:
            for query, country in pbar:
                pbar.set_postfix(query=query[:20], country=country)
                try:
                    items = src.fetch(query, country, per_source)
                except Exception as exc:
                    tqdm.write(f"  ! {src.name} error on '{query}'/{country}: {exc}")
                    continue
                postings.extend(items)
                got += len(items)
        if verbose:
            tqdm.write(f"  - {src.name}: {got} postings across {len(served)} countries")
        if got:
            used.append(src.name)

    return postings, used


def dedupe(postings: list[JobPosting]) -> list[JobPosting]:
    seen: dict[str, JobPosting] = {}
    for p in postings:
        key = p.dedupe_key
        if key not in seen:
            seen[key] = p
        else:
            existing = seen[key]
            # Prefer the record with a longer description or salary data
            if len(p.description) > len(existing.description) or (p.salary and not existing.salary):
                seen[key] = p
    return list(seen.values())


def run(config: Config, per_source: int = 25, force_keyword: bool = False,
        verbose: bool = True) -> RunResult:
    if verbose:
        tqdm.write("Fetching postings...")
    raw, used = fetch_all(config, per_source, verbose)
    us_filtered = [j for j in raw if not _is_us_location(j)]
    if verbose and len(us_filtered) < len(raw):
        tqdm.write(f"  - dropped {len(raw) - len(us_filtered)} US-located postings")
    unique = dedupe(us_filtered)
    if verbose:
        tqdm.write(f"Fetched {len(raw)}, {len(unique)} unique after dedupe.")

    scorer, mode = build_scorer(config, force_keyword=force_keyword)
    if verbose:
        tqdm.write(f"Scoring with: {mode}")

    scored = [
        scorer.score(job)
        for job in tqdm(unique, desc="Scoring", unit="job", disable=not verbose)
    ]
    scored = [s for s in scored if s.score >= config.min_score]
    scored.sort(key=lambda s: s.score, reverse=True)

    return RunResult(
        scored=scored,
        fetched=len(raw),
        deduped=len(unique),
        scorer_mode=mode,
        sources_used=used,
    )
