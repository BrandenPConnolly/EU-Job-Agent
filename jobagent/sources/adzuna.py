"""Adzuna Jobs API. Free key pair from https://developer.adzuna.com/

Covers DE, NL, FR, IE, and GB of our targets. No BE support.
Good for structured salary data and well-tagged job categories.
"""
from __future__ import annotations

import requests

from ..models import JobPosting
from .base import JobSource

# Map internal code -> Adzuna country path segment.
ADZUNA_COUNTRY = {"de": "de", "nl": "nl", "fr": "fr", "ie": "ie", "gb": "gb"}
BASE = "https://api.adzuna.com/v1/api/jobs/{cc}/search/{page}"


class AdzunaSource(JobSource):
    name = "adzuna"

    @property
    def available(self) -> bool:
        return bool(self.config.adzuna_app_id and self.config.adzuna_app_key)

    def fetch(self, query: str, country: str, limit: int) -> list[JobPosting]:
        cc = ADZUNA_COUNTRY.get(country.lower())
        if not self.available or cc is None:
            return []

        out: list[JobPosting] = []
        page = 1
        while len(out) < limit:
            params = {
                "app_id": self.config.adzuna_app_id,
                "app_key": self.config.adzuna_app_key,
                "what": query,
                "results_per_page": min(50, limit - len(out)),
                "content-type": "application/json",
            }
            try:
                resp = requests.get(BASE.format(cc=cc, page=page), params=params, timeout=20)
                resp.raise_for_status()
                results = resp.json().get("results", []) or []
            except (requests.RequestException, ValueError):
                break

            if not results:
                break
            for r in results:
                out.append(
                    JobPosting(
                        title=r.get("title", "").strip(),
                        company=(r.get("company", {}) or {}).get("display_name", "").strip(),
                        location=(r.get("location", {}) or {}).get("display_name", "").strip(),
                        country=country.lower(),
                        url=r.get("redirect_url", ""),
                        description=(r.get("description", "") or "").strip(),
                        salary=_salary(r),
                        posted=(r.get("created", "") or "").strip(),
                        source=self.name,
                    )
                )
                if len(out) >= limit:
                    break

            if len(results) < 50:
                break
            page += 1
        return out


def _salary(r: dict) -> str:
    lo, hi = r.get("salary_min"), r.get("salary_max")
    if lo and hi:
        return f"{int(lo):,} - {int(hi):,}"
    if lo:
        return f"from {int(lo):,}"
    return ""
