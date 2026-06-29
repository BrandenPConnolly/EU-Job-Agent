"""
Jooble API — requires free API key.
Sign up: https://jooble.org/api/about
Env var: JOOBLE_API_KEY
Supports all target countries via location strings.
"""
import logging
from typing import Generator

import requests

from config import JOOBLE_API_KEY, MAX_JOBS_PER_SOURCE_PER_QUERY
from models import Job

logger = logging.getLogger(__name__)

BASE_URL = "https://jooble.org/api/{key}"

# Map country codes to Jooble location search strings
COUNTRY_LOCATIONS = {
    "DE": "Germany",
    "NL": "Netherlands",
    "FR": "France",
    "IE": "Ireland",
    "BE": "Belgium",
    "GB": "United Kingdom",
}


def fetch(query: str, countries: list[str], max_per_country: int = MAX_JOBS_PER_SOURCE_PER_QUERY) -> Generator[Job, None, None]:
    if not JOOBLE_API_KEY:
        logger.info("Jooble API key not set (JOOBLE_API_KEY) — skipping")
        return

    url = BASE_URL.format(key=JOOBLE_API_KEY)

    for country_code in countries:
        location = COUNTRY_LOCATIONS.get(country_code)
        if not location:
            continue

        page = 1
        fetched = 0
        while fetched < max_per_country:
            payload = {
                "keywords": query,
                "location": location,
                "page": page,
                "resultonpage": min(20, max_per_country - fetched),
            }
            try:
                resp = requests.post(url, json=payload, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.warning("Jooble error [%s, page %d]: %s", country_code, page, exc)
                break

            jobs = data.get("jobs", [])
            if not jobs:
                break

            for item in jobs:
                yield Job(
                    title=item.get("title", ""),
                    company=item.get("company", ""),
                    location=item.get("location", ""),
                    country=country_code,
                    url=item.get("link", ""),
                    source="jooble",
                    description=item.get("snippet", ""),
                    salary=item.get("salary", ""),
                    posted_at=item.get("updated", ""),
                )
                fetched += 1
                if fetched >= max_per_country:
                    break

            if len(jobs) < payload["resultonpage"]:
                break
            page += 1
