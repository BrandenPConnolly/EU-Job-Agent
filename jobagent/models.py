"""Core data structures shared across the agent."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from typing import Optional


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


@dataclass
class JobPosting:
    """A single normalized job posting from any source."""
    title: str
    company: str
    location: str
    country: str        # ISO-ish code we searched under: nl, be, de, fr, ie, gb
    url: str
    description: str = ""
    salary: str = ""
    posted: str = ""    # free-form date string from the source
    source: str = ""    # which provider produced it

    @property
    def dedupe_key(self) -> str:
        """Stable hash key so the same role from two sources collapses to one."""
        basis = f"{_norm(self.title)}|{_norm(self.company)}|{_norm(self.location)}"
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()

    @property
    def text_blob(self) -> str:
        return f"{self.title}\n{self.company}\n{self.location}\n{self.description}"


@dataclass
class ScoredJob:
    """A posting plus the agent's fit assessment."""
    job: JobPosting
    score: int                          # 0-100
    verdict: str                        # strong | possible | weak
    reasons: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    dutch_required: Optional[bool] = None
    entry_note: str = ""                # e.g. EU-family-member sponsorship note
    scored_by: str = "keyword"          # llm | keyword

    def to_row(self) -> dict:
        d = asdict(self.job)
        d.update(
            score=self.score,
            verdict=self.verdict,
            scored_by=self.scored_by,
            dutch_required=self.dutch_required,
            reasons=" | ".join(self.reasons),
            concerns=" | ".join(self.concerns),
            entry_note=self.entry_note,
        )
        return d
