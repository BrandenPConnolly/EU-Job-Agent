"""Orchestration: fetch -> dedupe -> score -> rank."""
from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .models import JobPosting, ScoredJob
from .scoring import build_scorer
from .sources import build_sources


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
        for query in config.queries:
            for country in served:
                try:
                    items = src.fetch(query, country, per_source)
                except Exception as exc:
                    if verbose:
                        print(f"  ! {src.name} error on '{query}'/{country}: {exc}")
                    continue
                postings.extend(items)
                got += len(items)
        if verbose:
            print(f"  - {src.name}: {got} postings across {len(served)} countries")
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
        print("Fetching postings...")
    raw, used = fetch_all(config, per_source, verbose)
    unique = dedupe(raw)
    if verbose:
        print(f"Fetched {len(raw)}, {len(unique)} unique after dedupe.")

    scorer, mode = build_scorer(config, force_keyword=force_keyword)
    if verbose:
        print(f"Scoring with: {mode}")

    scored = [scorer.score(job) for job in unique]
    scored = [s for s in scored if s.score >= config.min_score]
    scored.sort(key=lambda s: s.score, reverse=True)

    return RunResult(
        scored=scored,
        fetched=len(raw),
        deduped=len(unique),
        scorer_mode=mode,
        sources_used=used,
    )
