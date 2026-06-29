"""
Adzuna Jobs API — requires free account.
Sign up: https://developer.adzuna.com/
Env vars: ADZUNA_APP_ID, ADZUNA_APP_KEY
Supported EU countries: DE, NL, FR, IE, GB (no BE)
"""
import logging
from typing import Generator

import requests

from config import ADZUNA_APP_ID, ADZUNA_APP_KEY, ADZUNA_SUPPORTED, MAX_JOBS_PER_SOURCE_PER_QUERY
from models import Job

logger = logging.getLogger(__name__)

BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"


def fetch(query: str, countries: list[str], max_per_country: int = MAX_JOBS_PER_SOURCE_PER_QUERY) -> Generator[Job, None, None]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        logger.info("Adzuna credentials not set (ADZUNA_APP_ID / ADZUNA_APP_KEY) — skipping")
        return

    for country_code in countries:
        slug = country_code.lower()
        if slug not in ADZUNA_SUPPORTED:
            logger.debug("Adzuna does not support country %s — skipping", country_code)
            continue

        fetched = 0
        page = 1
        while fetched < max_per_country:
            results_per_page = min(50, max_per_country - fetched)
            url = BASE_URL.format(country=slug, page=page)
            params = {
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_APP_KEY,
                "what": query,
                "results_per_page": results_per_page,
                "content-type": "application/json",
            }
            try:
                resp = requests.get(url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.warning("Adzuna error [%s, page %d]: %s", country_code, page, exc)
                break

            results = data.get("results", [])
            if not results:
                break

            for item in results:
                salary_parts = []
                if item.get("salary_min"):
                    salary_parts.append(f"min {item['salary_min']:.0f}")
                if item.get("salary_max"):
                    salary_parts.append(f"max {item['salary_max']:.0f}")
                salary = " / ".join(salary_parts)

                yield Job(
                    title=item.get("title", ""),
                    company=item.get("company", {}).get("display_name", ""),
                    location=item.get("location", {}).get("display_name", ""),
                    country=country_code,
                    url=item.get("redirect_url", ""),
                    source="adzuna",
                    description=item.get("description", ""),
                    salary=salary,
                    posted_at=item.get("created", ""),
                )
                fetched += 1
                if fetched >= max_per_country:
                    break

            if len(results) < results_per_page:
                break
            page += 1
