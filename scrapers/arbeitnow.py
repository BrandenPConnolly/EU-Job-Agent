"""
Arbeitnow public job board API — no API key required.
Docs: https://www.arbeitnow.com/api/job-board-api
Covers EU-wide listings; filter by country tag post-fetch.
"""
import logging
from typing import Generator

import requests

from config import MAX_JOBS_PER_SOURCE_PER_QUERY
from models import Job

logger = logging.getLogger(__name__)

BASE_URL = "https://www.arbeitnow.com/api/job-board-api"

# Arbeitnow uses language/location tags, not country codes.
# Map our country codes to relevant location keywords for post-filtering.
COUNTRY_LOCATION_MAP = {
    "DE": ["germany", "deutschland", "berlin", "munich", "münchen", "hamburg", "frankfurt", "cologne", "köln"],
    "NL": ["netherlands", "nederland", "amsterdam", "rotterdam", "the hague", "den haag", "eindhoven"],
    "FR": ["france", "paris", "lyon", "marseille", "toulouse", "nantes"],
    "IE": ["ireland", "dublin", "cork", "galway"],
    "BE": ["belgium", "belgique", "brussels", "bruxelles", "antwerp", "antwerpen", "ghent", "gent"],
    "GB": ["united kingdom", "uk", "london", "manchester", "edinburgh", "birmingham", "leeds", "glasgow"],
}


def _location_matches_country(location: str, country: str) -> bool:
    loc_lower = location.lower()
    return any(kw in loc_lower for kw in COUNTRY_LOCATION_MAP.get(country, []))


def fetch(query: str, countries: list[str], max_per_country: int = MAX_JOBS_PER_SOURCE_PER_QUERY) -> Generator[Job, None, None]:
    """Yield jobs from Arbeitnow matching query across given country list."""
    seen_slugs: set[str] = set()
    country_counts: dict[str, int] = {c: 0 for c in countries}
    page = 1

    while True:
        try:
            resp = requests.get(BASE_URL, params={"page": page}, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("Arbeitnow fetch error (page %d): %s", page, exc)
            break

        jobs = data.get("data", [])
        if not jobs:
            break

        query_lower = query.lower()
        for item in jobs:
            slug = item.get("slug", "")
            if slug in seen_slugs:
                continue

            title = item.get("title", "")
            description = item.get("description", "")
            location = item.get("location", "")
            company = item.get("company_name", "")
            url = item.get("url", f"https://www.arbeitnow.com/jobs/{slug}")
            posted_at = item.get("created_at", "")

            # Basic query relevance filter
            combined = (title + " " + description).lower()
            if query_lower not in combined and not any(
                word in combined for word in query_lower.split()
            ):
                continue

            for country in countries:
                if country_counts[country] >= max_per_country:
                    continue
                if _location_matches_country(location, country):
                    seen_slugs.add(slug)
                    country_counts[country] += 1
                    yield Job(
                        title=title,
                        company=company,
                        location=location,
                        country=country,
                        url=url,
                        source="arbeitnow",
                        description=description,
                        posted_at=str(posted_at),
                    )
                    break

        # Stop if all countries are saturated or no more pages
        if all(v >= max_per_country for v in country_counts.values()):
            break

        next_page_url = data.get("links", {}).get("next")
        if not next_page_url:
            break
        page += 1
