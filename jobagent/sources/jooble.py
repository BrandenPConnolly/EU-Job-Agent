"""Jooble REST API. Free key from https://jooble.org/api/about

Covers all six target countries including BE and FR, making it the primary
breadth source. Searches multiple city strings per country to improve recall.
Endpoint: POST https://jooble.org/api/{key}
"""
from __future__ import annotations

import re

import requests

from ..models import JobPosting
from .base import JobSource

# Multiple location strings per country increase recall.
COUNTRY_LOCATIONS = {
    "nl": ["Netherlands", "Amsterdam", "Rotterdam", "Utrecht", "Tilburg", "Groningen"],
    "be": ["Belgium", "Brussels", "Antwerp", "Ghent"],
    "de": ["Germany", "Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne"],
    "fr": ["France", "Paris", "Lyon", "Marseille", "Toulouse", "Nantes"],
    "ie": ["Ireland", "Dublin", "Cork", "Galway"],
    "gb": ["United Kingdom", "London", "Manchester", "Edinburgh", "Birmingham"],
}

ENDPOINT = "https://jooble.org/api/{key}"


class JoobleSource(JobSource):
    name = "jooble"

    @property
    def available(self) -> bool:
        return bool(self.config.jooble_key)

    def fetch(self, query: str, country: str, limit: int) -> list[JobPosting]:
        if not self.available:
            return []

        out: list[JobPosting] = []
        seen: set[str] = set()
        locations = COUNTRY_LOCATIONS.get(country.lower(), [country.upper()])
        per_location = max(1, limit // len(locations))
        url = ENDPOINT.format(key=self.config.jooble_key)

        for loc in locations:
            body = {"keywords": query, "location": loc, "ResultOnPage": per_location}
            try:
                resp = requests.post(url, json=body, timeout=20)
                resp.raise_for_status()
                jobs = resp.json().get("jobs", []) or []
            except (requests.RequestException, ValueError):
                continue

            for j in jobs:
                link = j.get("link", "")
                if not link or link in seen:
                    continue
                seen.add(link)
                out.append(
                    JobPosting(
                        title=j.get("title", "").strip(),
                        company=(j.get("company") or "").strip(),
                        location=(j.get("location") or loc).strip(),
                        country=country.lower(),
                        url=link,
                        description=_strip_html(j.get("snippet", "")),
                        salary=(j.get("salary") or "").strip(),
                        posted=(j.get("updated") or "").strip(),
                        source=self.name,
                    )
                )
                if len(out) >= limit:
                    return out
        return out


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").replace("&nbsp;", " ").strip()
