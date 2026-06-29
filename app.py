"""
EU Job Agent — Streamlit frontend
Run with: streamlit run app.py
"""
from __future__ import annotations

import io
import sys
import threading
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EU Job Agent",
    page_icon="🇪🇺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _discover_configs() -> dict[str, Path]:
    """Find all config*.yaml files and return a friendly-name → path mapping."""
    root = Path(__file__).parent
    configs: dict[str, Path] = {}
    for p in sorted(root.glob("config*.yaml")):
        if p.name == "config.yaml":
            label = "Branden — Clinical Informatics"
        elif p.name == "config-sped.yaml":
            label = "Wife — Special Education"
        else:
            label = p.stem.replace("config-", "").replace("-", " ").title()
        configs[label] = p
    return configs


def _verdict_badge(verdict: str) -> str:
    colors = {"strong": "#1a7a4a", "possible": "#b07d00", "weak": "#8b1a1a"}
    bg = colors.get(verdict, "#555")
    return f'<span style="background:{bg};color:white;padding:2px 8px;border-radius:4px;font-size:0.8em;font-weight:600">{verdict.upper()}</span>'


def _score_bar(score: int) -> str:
    filled = int(score / 10)
    empty = 10 - filled
    color = "#1a7a4a" if score >= 70 else "#b07d00" if score >= 45 else "#8b1a1a"
    bar = f'<span style="color:{color}">{"█" * filled}{"░" * empty}</span>'
    return f'{bar} <strong style="color:{color}">{score}</strong>'


COUNTRY_LABELS = {
    "nl": "🇳🇱 Netherlands",
    "be": "🇧🇪 Belgium",
    "de": "🇩🇪 Germany",
    "fr": "🇫🇷 France",
    "ie": "🇮🇪 Ireland",
    "gb": "🇬🇧 United Kingdom",
}

SOURCE_LABELS = {
    "arbeitnow": "Arbeitnow (no key needed)",
    "jooble": "Jooble",
    "adzuna": "Adzuna",
}

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.image("https://em-content.zobj.net/source/google/387/flag-european-union_1f1ea-1f1fa.png", width=48)
st.sidebar.title("EU Job Agent")

configs = _discover_configs()
profile_label = st.sidebar.selectbox("Profile", list(configs.keys()))
config_path = configs[profile_label]

st.sidebar.markdown("---")
st.sidebar.subheader("Countries")
all_countries = list(COUNTRY_LABELS.keys())
selected_countries = [
    code for code, label in COUNTRY_LABELS.items()
    if st.sidebar.checkbox(label, value=True, key=f"country_{code}")
]

st.sidebar.markdown("---")
st.sidebar.subheader("Sources")
selected_sources = [
    src for src, label in SOURCE_LABELS.items()
    if st.sidebar.checkbox(label, value=True, key=f"src_{src}")
]

st.sidebar.markdown("---")
st.sidebar.subheader("Search settings")
per_source = st.sidebar.slider("Max jobs per source / query / country", 5, 50, 15)
min_score = st.sidebar.slider("Minimum match score", 0, 100, 40)
use_llm = st.sidebar.toggle("Use Ollama LLM scorer", value=True)

st.sidebar.markdown("---")
run_btn = st.sidebar.button("🔍 Run search", type="primary", use_container_width=True)
demo_btn = st.sidebar.button("🧪 Run demo (offline)", use_container_width=True)

# ── Previous results ───────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("Previous results")

def _discover_csvs() -> dict[str, Path]:
    output_dir = Path(__file__).parent / "output"
    csvs = sorted(output_dir.glob("jobs_*.csv"), reverse=True) + \
           sorted(output_dir.glob("job-matches-*.csv"), reverse=True)
    # dedupe while preserving order
    seen, unique = set(), []
    for p in csvs:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return {p.name: p for p in unique}

csv_files = _discover_csvs()
if csv_files:
    selected_csv_name = st.sidebar.selectbox(
        "Select a saved run", ["— none —"] + list(csv_files.keys())
    )
    load_csv_btn = st.sidebar.button("📂 Load", use_container_width=True,
                                     disabled=selected_csv_name == "— none —")
else:
    st.sidebar.caption("No saved runs found in `output/` yet.")
    selected_csv_name = "— none —"
    load_csv_btn = False

# ── Main area ──────────────────────────────────────────────────────────────────
st.title("🇪🇺 EU Job Agent")

# Load config to show profile headline
try:
    from jobagent.config import load_config
    _cfg = load_config(config_path)
    headline = _cfg.profile.get("headline", "").strip().replace("\n", " ")
    st.caption(f"**{profile_label}** — {headline[:200]}{'…' if len(headline) > 200 else ''}")
except Exception:
    pass

st.markdown("---")

# ── Run logic ─────────────────────────────────────────────────────────────────

def _run_search(config_path: Path, countries: list[str], sources: list[str],
                per_source: int, min_score: int, no_llm: bool, demo: bool):
    """Run the pipeline and return a RunResult (or raise)."""
    from jobagent.config import load_config
    from jobagent.pipeline import run as pipeline_run
    from jobagent.scoring import build_scorer
    from jobagent.models import JobPosting
    from jobagent.pipeline import RunResult

    cfg = load_config(config_path)
    cfg.search["countries"] = countries
    cfg.scoring["min_score"] = min_score

    # Restrict sources in the pipeline by monkey-patching build_sources
    from jobagent import sources as sources_mod
    orig_build = sources_mod.build_sources

    def filtered_build(c):
        return [s for s in orig_build(c) if s.name in sources]

    sources_mod.build_sources = filtered_build
    try:
        if demo:
            samples = [
                JobPosting(
                    title="Clinical Data Scientist (Oncology)", company="Amsterdam UMC",
                    location="Amsterdam, Netherlands", country="nl",
                    url="https://example.org/job/1",
                    description=("Build ML models on Databricks and PySpark for oncology outcomes. "
                                 "Epic Clarity and Caboodle data. MLflow, population health risk stratification. "
                                 "Python and SQL required. Working language is English."),
                    salary="65,000 - 80,000", posted="2026-06-20", source="demo",
                ),
                JobPosting(
                    title="SEN Teacher", company="The British School of Amsterdam",
                    location="Amsterdam, Netherlands", country="nl",
                    url="https://example.org/job/5",
                    description=("Seeking an experienced SEN/SEND teacher for our inclusive school. "
                                 "IEP development, differentiated instruction, learning support. "
                                 "English medium school. International environment."),
                    salary="42,000 - 52,000", posted="2026-06-22", source="demo",
                ),
                JobPosting(
                    title="Healthcare Data Engineer", company="Pacmed",
                    location="Amsterdam, Netherlands", country="nl",
                    url="https://example.org/job/2",
                    description=("SQL and Python ETL pipelines for clinical ML. Databricks, Azure DevOps. "
                                 "Dutch fluency required for working with clinicians."),
                    source="demo",
                ),
                JobPosting(
                    title="Senior Data Engineer", company="IQVIA",
                    location="Frankfurt, Germany", country="de",
                    url="https://example.org/job/3",
                    description=("ETL pipelines for healthcare analytics. Python, SQL Server, Tableau, SSIS. "
                                 "English working environment."),
                    salary="75,000 - 90,000", source="demo",
                ),
                JobPosting(
                    title="Special Education Teacher", company="International School Brussels",
                    location="Brussels, Belgium", country="be",
                    url="https://example.org/job/6",
                    description=("IB school seeks special education teacher for inclusive classroom. "
                                 "Experience with IEPs, differentiated instruction, autism support. "
                                 "English-medium instruction. No French required."),
                    salary="38,000 - 48,000", posted="2026-06-21", source="demo",
                ),
                JobPosting(
                    title="Frontend Engineer", company="A Startup",
                    location="Berlin, Germany", country="de",
                    url="https://example.org/job/4",
                    description="React and TypeScript. Build delightful UIs. Deutsch erforderlich.",
                    source="demo",
                ),
            ]
            scorer, mode = build_scorer(cfg, force_keyword=no_llm)
            scored = sorted(
                (scorer.score(j) for j in samples if j.country in countries),
                key=lambda s: s.score, reverse=True,
            )
            scored = [s for s in scored if s.score >= min_score]
            return RunResult(
                scored=scored, fetched=len(samples), deduped=len(samples),
                scorer_mode=mode, sources_used=["demo"],
            )
        else:
            return pipeline_run(cfg, per_source=per_source, force_keyword=no_llm, verbose=False)
    finally:
        sources_mod.build_sources = orig_build


def _result_to_df(result) -> pd.DataFrame:
    rows = []
    for s in result.scored:
        j = s.job
        rows.append({
            "Score": s.score,
            "Verdict": s.verdict,
            "Title": j.title,
            "Company": j.company,
            "Location": j.location,
            "Country": COUNTRY_LABELS.get(j.country, j.country.upper()),
            "Salary": j.salary or "",
            "Posted": j.posted or "",
            "Source": j.source,
            "Fit": "; ".join(s.reasons),
            "Watch": "; ".join(s.concerns),
            "Scored by": s.scored_by,
            "URL": j.url,
        })
    return pd.DataFrame(rows)


def _show_results(result):
    scored = result.scored
    if not scored:
        st.warning("No matches found above the score threshold. Try lowering the minimum score or broadening your search.")
        return

    # ── Summary metrics ────────────────────────────────────────────────────────
    strong = sum(1 for s in scored if s.verdict == "strong")
    possible = sum(1 for s in scored if s.verdict == "possible")
    weak = sum(1 for s in scored if s.verdict == "weak")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total matches", len(scored))
    c2.metric("🟢 Strong", strong)
    c3.metric("🟡 Possible", possible)
    c4.metric("🔴 Weak", weak)
    c5.metric("Scorer", result.scorer_mode.split("(")[0].strip())

    st.markdown("---")

    # ── Filter bar ─────────────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        verdict_filter = st.multiselect(
            "Verdict", ["strong", "possible", "weak"],
            default=["strong", "possible"],
        )
    with fc2:
        country_codes = list({s.job.country for s in scored})
        country_filter = st.multiselect(
            "Country",
            options=country_codes,
            default=country_codes,
            format_func=lambda c: COUNTRY_LABELS.get(c, c.upper()),
        )
    with fc3:
        source_filter = st.multiselect(
            "Source",
            options=list({s.job.source for s in scored}),
            default=list({s.job.source for s in scored}),
        )

    filtered = [
        s for s in scored
        if s.verdict in verdict_filter
        and s.job.country in country_filter
        and s.job.source in source_filter
    ]

    st.caption(f"Showing {len(filtered)} of {len(scored)} matches")
    st.markdown("---")

    # ── Results cards ──────────────────────────────────────────────────────────
    for s in filtered:
        j = s.job
        country_flag = COUNTRY_LABELS.get(j.country, j.country.upper())

        with st.container(border=True):
            col_score, col_main, col_link = st.columns([1, 6, 1])

            with col_score:
                score_color = "#1a7a4a" if s.score >= 70 else "#b07d00" if s.score >= 45 else "#8b1a1a"
                st.markdown(
                    f'<div style="text-align:center;padding:8px">'
                    f'<div style="font-size:2em;font-weight:700;color:{score_color}">{s.score}</div>'
                    f'<div style="font-size:0.75em;color:{score_color};text-transform:uppercase;font-weight:600">{s.verdict}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            with col_main:
                st.markdown(f"**{j.title}**")
                meta_parts = [j.company, country_flag, j.location if j.location != country_flag else ""]
                if j.salary:
                    meta_parts.append(f"💰 {j.salary}")
                if j.posted:
                    meta_parts.append(f"📅 {j.posted[:10]}")
                meta_parts.append(f"via *{j.source}*")
                st.caption("  ·  ".join(p for p in meta_parts if p))

                if s.reasons:
                    st.markdown(
                        "✅ " + "  ·  ".join(s.reasons),
                        help="Why this job matches your profile",
                    )
                if s.concerns:
                    st.markdown(
                        "⚠️ " + "  ·  ".join(s.concerns),
                        help="Potential concerns or gaps",
                    )

            with col_link:
                if j.url:
                    st.markdown(
                        f'<div style="padding-top:12px">'
                        f'<a href="{j.url}" target="_blank" style="'
                        f'background:#0066cc;color:white;padding:6px 14px;'
                        f'border-radius:6px;text-decoration:none;font-size:0.85em;font-weight:600">'
                        f'Apply →</a></div>',
                        unsafe_allow_html=True,
                    )

    st.markdown("---")

    # ── Data table (downloadable) ──────────────────────────────────────────────
    with st.expander("📊 Full data table + CSV download"):
        df = _result_to_df(result)
        st.dataframe(
            df,
            column_config={
                "URL": st.column_config.LinkColumn("URL", display_text="Open →"),
                "Score": st.column_config.NumberColumn("Score", format="%d"),
            },
            hide_index=True,
            use_container_width=True,
        )
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            data=csv,
            file_name=f"eu-jobs-{profile_label.split('—')[0].strip().lower().replace(' ', '-')}.csv",
            mime="text/csv",
        )


# ── CSV display (shared by saved-run loader and live results table) ───────────

def _show_df_results(df: pd.DataFrame, source_label: str = ""):
    """Render cards + filter bar directly from a CSV-shaped DataFrame."""
    if df.empty:
        st.warning("No rows in this file.")
        return

    # Normalise column names (both old and new CSV formats)
    df.columns = [c.strip() for c in df.columns]
    col_map = {c.lower(): c for c in df.columns}

    def _col(name: str, default=""):
        return df[col_map[name]] if name in col_map else default

    # Ensure score is numeric
    if "score" in col_map:
        df[col_map["score"]] = pd.to_numeric(df[col_map["score"]], errors="coerce").fillna(0).astype(int)

    # Summary metrics
    scores = _col("score")
    verdicts = _col("verdict")
    strong   = int((verdicts == "strong").sum())  if hasattr(verdicts, "sum") else 0
    possible = int((verdicts == "possible").sum()) if hasattr(verdicts, "sum") else 0
    weak     = int((verdicts == "weak").sum())     if hasattr(verdicts, "sum") else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", len(df))
    c2.metric("🟢 Strong",   strong)
    c3.metric("🟡 Possible", possible)
    c4.metric("🔴 Weak",     weak)
    st.markdown("---")

    # Filter bar
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        v_opts   = sorted(df[col_map["verdict"]].dropna().unique()) if "verdict" in col_map else []
        v_filter = st.multiselect("Verdict", v_opts, default=[v for v in ["strong", "possible"] if v in v_opts], key=f"vf_{source_label}")
    with fc2:
        c_opts   = sorted(df[col_map["country"]].dropna().unique()) if "country" in col_map else []
        c_filter = st.multiselect("Country", c_opts, default=c_opts,
                                  format_func=lambda c: COUNTRY_LABELS.get(c, c.upper()),
                                  key=f"cf_{source_label}")
    with fc3:
        s_opts   = sorted(df[col_map["source"]].dropna().unique()) if "source" in col_map else []
        s_filter = st.multiselect("Source", s_opts, default=s_opts, key=f"sf_{source_label}")

    mask = pd.Series([True] * len(df))
    if v_filter and "verdict" in col_map:
        mask &= df[col_map["verdict"]].isin(v_filter)
    if c_filter and "country" in col_map:
        mask &= df[col_map["country"]].isin(c_filter)
    if s_filter and "source" in col_map:
        mask &= df[col_map["source"]].isin(s_filter)

    filtered = df[mask].sort_values(col_map.get("score", df.columns[0]), ascending=False)
    st.caption(f"Showing {len(filtered)} of {len(df)} matches")
    st.markdown("---")

    # Cards
    for _, row in filtered.iterrows():
        score   = int(row.get(col_map.get("score", ""), 0) or 0)
        verdict = str(row.get(col_map.get("verdict", ""), "") or "").lower()
        title   = str(row.get(col_map.get("title", ""), "") or "")
        company = str(row.get(col_map.get("company", ""), "") or "")
        location= str(row.get(col_map.get("location", ""), "") or "")
        country = str(row.get(col_map.get("country", ""), "") or "")
        salary  = str(row.get(col_map.get("salary", ""), "") or "")
        posted  = str(row.get(col_map.get("posted", ""), "") or "")
        source  = str(row.get(col_map.get("source", ""), "") or "")
        reasons = str(row.get(col_map.get("reasons", ""), "") or "")
        concerns= str(row.get(col_map.get("concerns", ""), "") or "")
        url     = str(row.get(col_map.get("url", ""), "") or "")

        score_color = "#1a7a4a" if score >= 70 else "#b07d00" if score >= 45 else "#8b1a1a"
        country_flag = COUNTRY_LABELS.get(country, country.upper())

        with st.container(border=True):
            col_sc, col_main, col_lnk = st.columns([1, 6, 1])

            with col_sc:
                st.markdown(
                    f'<div style="text-align:center;padding:8px">'
                    f'<div style="font-size:2em;font-weight:700;color:{score_color}">{score}</div>'
                    f'<div style="font-size:0.75em;color:{score_color};text-transform:uppercase;font-weight:600">{verdict}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            with col_main:
                st.markdown(f"**{title}**")
                meta = [company, country_flag, location if location != country_flag else ""]
                if salary:
                    meta.append(f"💰 {salary}")
                if posted and posted not in ("nan", ""):
                    meta.append(f"📅 {str(posted)[:10]}")
                if source:
                    meta.append(f"via *{source}*")
                st.caption("  ·  ".join(p for p in meta if p))
                if reasons and reasons not in ("nan", ""):
                    st.markdown("✅ " + reasons)
                if concerns and concerns not in ("nan", ""):
                    st.markdown("⚠️ " + concerns)

            with col_lnk:
                if url and url not in ("nan", ""):
                    st.markdown(
                        f'<div style="padding-top:12px">'
                        f'<a href="{url}" target="_blank" style="background:#0066cc;color:white;'
                        f'padding:6px 14px;border-radius:6px;text-decoration:none;font-size:0.85em;font-weight:600">'
                        f'Apply →</a></div>',
                        unsafe_allow_html=True,
                    )

    st.markdown("---")
    with st.expander("📊 Full data table + CSV download"):
        url_col = col_map.get("url", None)
        col_cfg = {}
        if url_col:
            col_cfg[url_col] = st.column_config.LinkColumn(url_col, display_text="Open →")
        st.dataframe(filtered, column_config=col_cfg, hide_index=True, use_container_width=True)
        st.download_button(
            "⬇️ Download filtered CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name=f"eu-jobs-filtered.csv",
            mime="text/csv",
        )


# ── Trigger runs ──────────────────────────────────────────────────────────────
if run_btn or demo_btn:
    if not selected_countries:
        st.error("Select at least one country.")
    elif not selected_sources:
        st.error("Select at least one source.")
    else:
        label = "Running demo scoring…" if demo_btn else f"Searching {len(selected_countries)} countries across {len(selected_sources)} sources…"
        with st.spinner(label):
            try:
                result = _run_search(
                    config_path=config_path,
                    countries=selected_countries,
                    sources=selected_sources,
                    per_source=per_source,
                    min_score=min_score,
                    no_llm=not use_llm,
                    demo=bool(demo_btn),
                )
                st.session_state["result"] = result
                st.session_state["result_profile"] = profile_label
            except Exception as exc:
                st.error(f"Search failed: {exc}")
                raise

# ── Load saved CSV ─────────────────────────────────────────────────────────────
if load_csv_btn and selected_csv_name != "— none —":
    csv_path = csv_files[selected_csv_name]
    try:
        loaded_df = pd.read_csv(csv_path)
        st.session_state["csv_df"] = loaded_df
        st.session_state["csv_name"] = selected_csv_name
        st.session_state.pop("result", None)  # clear live result so CSV view takes over
    except Exception as exc:
        st.error(f"Could not load {selected_csv_name}: {exc}")

# ── Display ────────────────────────────────────────────────────────────────────
if "result" in st.session_state:
    result = st.session_state["result"]
    cached_profile = st.session_state.get("result_profile", "")
    if cached_profile:
        st.subheader(f"Results — {cached_profile}")
    _show_results(result)
elif "csv_df" in st.session_state:
    csv_name = st.session_state.get("csv_name", "saved run")
    st.subheader(f"📂 {csv_name}")
    _show_df_results(st.session_state["csv_df"], source_label=csv_name)
else:
    st.info("Configure your search in the sidebar and click **Run search** or **Run demo** to get started.")
    st.markdown("""
**Quick start:**
1. Pick a profile in the sidebar
2. Choose countries and sources
3. Click **🧪 Run demo** to test with sample jobs (no API keys or network needed)
4. Click **🔍 Run search** for live results
5. Or pick a previous run from **Previous results** in the sidebar and click **📂 Load**
""")
