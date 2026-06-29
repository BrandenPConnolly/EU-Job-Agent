"""Deterministic keyword scorer — fallback when Ollama is unreachable.

Rewards: skill-term overlap (capped at 55 pts), target-title match (25 pts),
preferred-location match (12 pts). Penalizes: Dutch fluency required (-12 pts).
"""
from __future__ import annotations

import re

from ..models import JobPosting, ScoredJob

_DUTCH_REQUIRED = re.compile(
    r"(dutch[\w\s]{0,25}(required|fluen|native|mandatory|essential|proficien))"
    r"|((required|fluen|native|mandatory)[\w\s]{0,25}dutch)"
    r"|(nederlands\s*(vereist|verplicht))|nederlandstalig",
    re.IGNORECASE,
)


def _dutch_required(text: str) -> bool:
    return bool(_DUTCH_REQUIRED.search(text or ""))


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"\W+", (text or "").lower()) if len(t) > 2}


def _phrase_in(phrase: str, raw_text: str, token_set: set[str]) -> bool:
    """Multi-word skills matched as substring; single words matched as tokens."""
    if " " in phrase:
        return phrase in raw_text
    return phrase in token_set


class KeywordScorer:
    def __init__(self, config):
        p = config.profile
        self.skills = [s.lower() for s in p.get("skills", [])]
        self.titles = [t.lower() for t in p.get("target_titles", [])]
        self.locations = [l.lower() for l in p.get("preferred_locations", [])]

    def score(self, job: JobPosting) -> ScoredJob:
        title = job.title.lower()
        blob = job.text_blob.lower()
        blob_tokens = _tokens(blob)
        title_tokens = _tokens(title)

        matched_skills = [s for s in self.skills if _phrase_in(s, blob, blob_tokens)]
        title_hits = [t for t in self.titles if _phrase_in(t, title, title_tokens)]
        loc_hit = any(l in (job.location.lower() + " " + blob) for l in self.locations)

        skill_pts = min(55, len(matched_skills) * 9)
        title_pts = 25 if title_hits else 0
        loc_pts = 12 if loc_hit else 0

        dutch = _dutch_required(blob)
        dutch_penalty = 12 if dutch else 0

        raw = skill_pts + title_pts + loc_pts - dutch_penalty
        score = max(0, min(100, raw))
        verdict = "strong" if score >= 70 else "possible" if score >= 45 else "weak"

        reasons: list[str] = []
        if title_hits:
            reasons.append(f"title matches target role ({', '.join(title_hits[:2])})")
        if matched_skills:
            reasons.append(f"{len(matched_skills)} skill matches: {', '.join(matched_skills[:6])}")
        if loc_hit:
            reasons.append("in a preferred location")

        concerns: list[str] = []
        if dutch:
            concerns.append("posting signals Dutch fluency required")
        if not matched_skills:
            concerns.append("no core-skill overlap detected")

        return ScoredJob(
            job=job,
            score=score,
            verdict=verdict,
            reasons=reasons,
            concerns=concerns,
            dutch_required=dutch,
            entry_note="",
            scored_by="keyword",
        )
