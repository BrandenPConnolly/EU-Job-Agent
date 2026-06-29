import csv
import json
import logging
import os
from datetime import datetime
from typing import List

from models import Job

logger = logging.getLogger(__name__)


def save_results(jobs: List[Job], output_dir: str) -> dict[str, str]:
    """Save results as JSON and CSV. Returns paths written."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    json_path = os.path.join(output_dir, f"jobs_{ts}.json")
    csv_path = os.path.join(output_dir, f"jobs_{ts}.csv")

    records = [j.to_dict() for j in jobs]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    if records:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)

    logger.info("Saved %d jobs → %s, %s", len(jobs), json_path, csv_path)
    return {"json": json_path, "csv": csv_path}


def print_summary(jobs: List[Job], min_score: float = 0.0) -> None:
    filtered = [j for j in jobs if j.match_score >= min_score]
    filtered.sort(key=lambda j: j.match_score, reverse=True)

    print(f"\n{'='*70}")
    print(f"  EU JOB AGENT — {len(filtered)} jobs (score ≥ {min_score:.1f})")
    print(f"{'='*70}")

    by_country: dict[str, List[Job]] = {}
    for j in filtered:
        by_country.setdefault(j.country, []).append(j)

    for country, cjobs in sorted(by_country.items()):
        print(f"\n  [{country}]  {len(cjobs)} jobs")
        for j in cjobs:
            score_bar = "█" * int(j.match_score * 10) + "░" * (10 - int(j.match_score * 10))
            print(f"    {score_bar} {j.match_score:.2f}  {j.title}")
            print(f"           {j.company} | {j.location} | {j.source}")
            if j.salary:
                print(f"           Salary: {j.salary}")
            print(f"           {j.url}")
            if j.match_reason:
                print(f"           {j.match_reason}")
            print()
