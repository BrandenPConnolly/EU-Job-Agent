"""Output: ranked markdown digest and a CSV for tracking."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .pipeline import RunResult

TIERS = [("strong", "Strong fit"), ("possible", "Possible fit"), ("weak", "Weak fit")]

CSV_FIELDS = [
    "score", "verdict", "title", "company", "location", "country",
    "salary", "posted", "source", "scored_by", "dutch_required",
    "reasons", "concerns", "entry_note", "url",
]


def write_reports(result: RunResult, out_dir: str | Path, top: int | None = None) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")

    md_path = out / f"job-matches-{stamp}.md"
    csv_path = out / f"job-matches-{stamp}.csv"

    md_path.write_text(_markdown(result, top), encoding="utf-8")
    _write_csv(result, csv_path)
    return {"markdown": str(md_path), "csv": str(csv_path)}


def _markdown(result: RunResult, top: int | None) -> str:
    rows = result.scored[:top] if top else result.scored
    lines = [
        "# EU job matches",
        "",
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"Sources: {', '.join(result.sources_used) or 'none'}  ",
        f"Scoring: {result.scorer_mode}  ",
        f"Fetched {result.fetched}, {result.deduped} unique, {len(result.scored)} above threshold.",
        "",
    ]

    for tier_key, tier_label in TIERS:
        tier_rows = [s for s in rows if s.verdict == tier_key]
        if not tier_rows:
            continue
        lines.append(f"## {tier_label} ({len(tier_rows)})")
        lines.append("")
        for s in tier_rows:
            j = s.job
            header = f"### {s.score} | {j.title}"
            if j.company:
                header += f" at {j.company}"
            lines.append(header)
            meta = f"{j.location or j.country.upper()} | {j.source}"
            if j.salary:
                meta += f" | {j.salary}"
            if j.posted:
                meta += f" | {j.posted}"
            lines.append(meta + "  ")
            if s.reasons:
                lines.append("- Fit: " + "; ".join(s.reasons))
            if s.concerns:
                lines.append("- Watch: " + "; ".join(s.concerns))
            if s.dutch_required:
                lines.append("- Note: Dutch fluency appears required")
            if s.entry_note:
                lines.append("- Entry: " + s.entry_note)
            if j.url:
                lines.append(f"- Link: {j.url}")
            lines.append("")

    return "\n".join(lines)


def _write_csv(result: RunResult, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for s in result.scored:
            writer.writerow(s.to_row())
