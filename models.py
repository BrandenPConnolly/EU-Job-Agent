from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Job:
    title: str
    company: str
    location: str
    country: str
    url: str
    source: str
    description: str = ""
    salary: str = ""
    posted_at: Optional[str] = None
    match_score: float = 0.0
    match_reason: str = ""
    fetched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "country": self.country,
            "url": self.url,
            "source": self.source,
            "description": self.description[:500] if self.description else "",
            "salary": self.salary,
            "posted_at": self.posted_at,
            "match_score": self.match_score,
            "match_reason": self.match_reason,
            "fetched_at": self.fetched_at,
        }
