"""Command-line interface for the EU job agent."""
from __future__ import annotations

import argparse
import sys

from .config import load_config
from .models import JobPosting
from .pipeline import RunResult, run
from .report import write_reports
from .scoring import build_scorer
from .sources import build_sources


def _cmd_sources(args) -> int:
    config = load_config(args.config)
    print("Configured sources:")
    for src in build_sources(config):
        status = "ready" if src.available else "needs credentials"
        served = ", ".join(c for c in config.countries if src.serves(c)) or "-"
        print(f"  {src.name:12s} {status:18s} serves: {served}")
    if config.use_llm:
        scorer = __import__("jobagent.scoring.llm", fromlist=["LLMScorer"]).LLMScorer(config)
        llm_ok = scorer.healthy()
        print(f"\nScoring: LLM ({config.ollama_model}) — {'reachable' if llm_ok else 'NOT reachable, will use keyword fallback'}")
    else:
        print("\nScoring: keyword only (use_llm=false in config)")
    return 0


def _cmd_search(args) -> int:
    config = load_config(args.config)
    if args.countries:
        config.search["countries"] = [c.strip().lower() for c in args.countries.split(",")]
    if args.query:
        config.search["queries"] = [q.strip() for q in args.query.split(";") if q.strip()]
    if args.min_score is not None:
        config.scoring["min_score"] = args.min_score

    result = run(
        config,
        per_source=args.per_source,
        force_keyword=args.no_llm,
        verbose=not args.quiet,
    )
    paths = write_reports(result, args.out, top=args.top)
    print(f"\nWrote {len(result.scored)} matches:")
    print(f"  {paths['markdown']}")
    print(f"  {paths['csv']}")
    _print_top(result, n=min(10, len(result.scored)))
    return 0


def _cmd_demo(args) -> int:
    """Offline demo: scores built-in sample postings, no network needed."""
    config = load_config(args.config)
    samples = [
        JobPosting(
            title="Clinical Data Scientist (Oncology)",
            company="Amsterdam UMC",
            location="Amsterdam, Netherlands",
            country="nl",
            url="https://example.org/job/1",
            description=(
                "Build ML models on Databricks and PySpark for oncology outcomes. "
                "Epic Clarity and Caboodle data. MLflow, Unity Catalog, population "
                "health risk stratification. Python and SQL required."
            ),
            salary="65,000 - 80,000",
            posted="2026-06-20",
            source="demo",
        ),
        JobPosting(
            title="Healthcare Data Engineer",
            company="Pacmed",
            location="Amsterdam, Netherlands",
            country="nl",
            url="https://example.org/job/2",
            description=(
                "SQL and Python ETL pipelines for clinical ML. Databricks, Azure "
                "DevOps. Dutch fluency required for working with clinicians."
            ),
            source="demo",
        ),
        JobPosting(
            title="Senior Data Engineer",
            company="IQVIA",
            location="Frankfurt, Germany",
            country="de",
            url="https://example.org/job/3",
            description=(
                "Build and maintain ETL pipelines for healthcare analytics. "
                "Python, SQL Server, Tableau, SSIS experience preferred."
            ),
            salary="75,000 - 90,000",
            source="demo",
        ),
        JobPosting(
            title="Frontend Engineer",
            company="A Startup",
            location="Berlin, Germany",
            country="de",
            url="https://example.org/job/4",
            description="React and TypeScript. Build delightful UIs.",
            source="demo",
        ),
    ]
    scorer, mode = build_scorer(config, force_keyword=args.no_llm)
    scored = sorted((scorer.score(j) for j in samples), key=lambda s: s.score, reverse=True)
    result = RunResult(
        scored=scored,
        fetched=len(samples),
        deduped=len(samples),
        scorer_mode=mode,
        sources_used=["demo"],
    )
    paths = write_reports(result, args.out)
    print(f"Demo scored {len(scored)} sample postings using: {mode}")
    print(f"  {paths['markdown']}")
    _print_top(result, n=len(scored))
    return 0


def _print_top(result: RunResult, n: int) -> None:
    if not result.scored:
        print("  (no matches above threshold)")
        return
    print("\nTop matches:")
    for s in result.scored[:n]:
        line = f"  {s.score:3d} [{s.verdict:8s}] {s.job.title}"
        if s.job.company:
            line += f" @ {s.job.company}"
        line += f"  [{s.job.country.upper()}]"
        print(line)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jobagent", description="EU job-matching agent")
    p.add_argument("--config", default=None, help="path to config.yaml")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="fetch, score, and report live postings")
    s.add_argument("--countries", help="override, comma-separated (e.g. nl,de,gb)")
    s.add_argument("--query", help="override; separate multiple with ';'")
    s.add_argument("--per-source", type=int, default=25, help="max postings per source/query/country")
    s.add_argument("--min-score", type=int, default=None)
    s.add_argument("--top", type=int, default=None, help="cap rows in the markdown digest")
    s.add_argument("--no-llm", action="store_true", help="force keyword scorer")
    s.add_argument("--out", default="output")
    s.add_argument("--quiet", action="store_true")
    s.set_defaults(func=_cmd_search)

    d = sub.add_parser("demo", help="score built-in samples offline (no network)")
    d.add_argument("--no-llm", action="store_true")
    d.add_argument("--out", default="output")
    d.set_defaults(func=_cmd_demo)

    v = sub.add_parser("sources", help="list sources and credential status")
    v.set_defaults(func=_cmd_sources)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
