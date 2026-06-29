"""Abstract base for pluggable job sources."""
from __future__ import annotations

import abc

from ..models import JobPosting

# Countries each source can serve. Keep in sync with provider implementations.
SUPPORTED = {
    "jooble":     {"nl", "be", "de", "fr", "ie", "gb"},
    "adzuna":     {"de", "nl", "fr", "ie", "gb"},   # no BE on Adzuna
    "arbeitnow":  {"de", "nl", "be", "fr", "ie", "gb"},
}


class JobSource(abc.ABC):
    name: str = "base"

    def __init__(self, config):
        self.config = config

    @property
    def available(self) -> bool:
        """True if this source has the credentials it needs."""
        return True

    def serves(self, country: str) -> bool:
        return country.lower() in SUPPORTED.get(self.name, set())

    @abc.abstractmethod
    def fetch(self, query: str, country: str, limit: int) -> list[JobPosting]:
        """Return up to `limit` postings for one query in one country."""
        raise NotImplementedError
