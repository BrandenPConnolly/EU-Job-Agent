#!/usr/bin/env python3
"""
EU Job Agent — scrapes Arbeitnow, Adzuna, and Jooble for jobs across
DE, NL, FR, IE, BE, and GB, then scores each against your resume.

Usage:
    python main.py                          # run with defaults
    python main.py --countries DE NL        # filter countries
    python main.py --queries "data engineer" "etl developer"
    python main.py --min-score 0.5          # only show high-match jobs
    python main.py --no-ollama              # force regex matching
    python main.py --sources arbeitnow adzuna
"""
import argparse
import logging
import sys
from typing import Generator

from config import (
    COUNTRIES,
    MIN_MATCH_SCORE,
    OUTPUT_DIR,
    SEARCH_QUERIES,
)
from matcher import score_job
from models import Job
from output import print_summary, save_results
from scrapers import arbeitnow, adzuna, jooble

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ALL_SOURCES = ["arbeitnow", "adzuna", "jooble"]


def iter_jobs(queries: list[str], countries: list[str], sources: list[str]) -> Generator[Job, None, None]:
    for query in queries:
        logger.info("Searching: '%s'", query)
        if "arbeitnow" in sources:
            yield from arbeitnow.fetch(query, countries)
        if "adzuna" in sources:
            yield from adzuna.fetch(query, countries)
        if "jooble" in sources:
            yield from jooble.fetch(query, countries)


def deduplicate(jobs: list[Job]) -> list[Job]:
    seen: set[str] = set()
    unique: list[Job] = []
    for job in jobs:
        key = (job.title.lower().strip(), job.company.lower().strip(), job.country)
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EU Job Agent")
    parser.add_argument(
        "--countries", nargs="+", default=list(COUNTRIES.keys()),
        choices=list(COUNTRIES.keys()),
        help="Country codes to search (default: all)",
    )
    parser.add_argument(
        "--queries", nargs="+", default=SEARCH_QUERIES,
        help="Job search queries",
    )
    parser.add_argument(
        "--sources", nargs="+", default=ALL_SOURCES,
        choices=ALL_SOURCES,
        help="Job sources to use",
    )
    parser.add_argument(
        "--min-score", type=float, default=MIN_MATCH_SCORE,
        help="Minimum match score to display (0-1)",
    )
    parser.add_argument(
        "--no-ollama", action="store_true",
        help="Skip Ollama and use regex matching only",
    )
    parser.add_argument(
        "--output-dir", default=OUTPUT_DIR,
        help="Directory to save results",
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="Don't save results to disk",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.no_ollama:
        import matcher
        matcher._OLLAMA_AVAILABLE = False

    logger.info(
        "Starting EU Job Agent | countries=%s | sources=%s | queries=%d",
        args.countries, args.sources, len(args.queries),
    )

    all_jobs: list[Job] = []
    for job in iter_jobs(args.queries, args.countries, args.sources):
        scored = score_job(job)
        all_jobs.append(scored)
        logger.debug("  [%.2f] %s @ %s (%s)", scored.match_score, scored.title, scored.company, scored.country)

    unique_jobs = deduplicate(all_jobs)
    logger.info("Total: %d jobs fetched, %d after dedup", len(all_jobs), len(unique_jobs))

    if not unique_jobs:
        logger.warning("No jobs found. Check API credentials and network access.")
        sys.exit(0)

    if not args.no_save:
        paths = save_results(unique_jobs, args.output_dir)
        print(f"\nResults saved to:\n  JSON: {paths['json']}\n  CSV:  {paths['csv']}")

    print_summary(unique_jobs, min_score=args.min_score)


if __name__ == "__main__":
    main()
