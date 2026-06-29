"""Arbeitnow public job board API. No key required.

Returns recent EU postings (Germany-heavy, many remote/English roles).
Not query-filtered server-side, so we fetch pages and filter locally.
Useful on first launch because it needs no credentials.
"""
from __future__ import annotations

import re

import requests

from ..models import JobPosting
from .base import JobSource

ENDPOINT = "https://www.arbeitnow.com/api/job-board-api"

COUNTRY_HINTS = {
    "nl": ["netherlands", "amsterdam", "rotterdam", "utrecht", "tilburg", "groningen", "eindhoven", "the hague", "den haag"],
    "be": ["belgium", "belgique", "brussels", "bruxelles", "antwerp", "antwerpen", "ghent", "gent", "leuven"],
    "de": ["germany", "deutschland", "berlin", "munich", "münchen", "cologne", "köln", "hamburg", "frankfurt", "düsseldorf"],
    "fr": ["france", "paris", "lyon", "marseille", "toulouse", "nantes", "bordeaux", "strasbourg"],
    "gb": ["united kingdom", "england", "london", "manchester", "cambridge", "edinburgh", "birmingham", "leeds", "glasgow"],
    "ie": ["ireland", "dublin", "cork", "galway", "limerick"],
}


class ArbeitnowSource(JobSource):
    name = "arbeitnow"

    def fetch(self, query: str, country: str, limit: int, max_pages: int = 4) -> list[JobPosting]:
        terms = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
        hints = COUNTRY_HINTS.get(country.lower(), [])
        out: list[JobPosting] = []
        url = ENDPOINT

        for _ in range(max_pages):
            try:
                resp = requests.get(url, timeout=20)
                resp.raise_for_status()
                payload = resp.json()
            except (requests.RequestException, ValueError):
                break

            for j in payload.get("data", []) or []:
                loc = (j.get("location") or "").lower()
                if hints and not any(h in loc for h in hints):
                    continue
                blob = f"{j.get('title', '')} {j.get('description', '')}".lower()
                if terms and not any(t in blob for t in terms):
                    continue
                out.append(
                    JobPosting(
                        title=(j.get("title") or "").strip(),
                        company=(j.get("company_name") or "").strip(),
                        location=(j.get("location") or "").strip(),
                        country=country.lower(),
                        url=j.get("url", ""),
                        description=_strip_html(j.get("description", ""))[:1200],
                        salary="",
                        posted=str(j.get("created_at", "")),
                        source=self.name,
                    )
                )
                if len(out) >= limit:
                    return out

            url = (payload.get("links") or {}).get("next") or ""
            if not url:
                break
        return out


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").replace("&nbsp;", " ").strip()
