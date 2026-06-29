# EU Job Agent

A local Python agent that pulls job postings from EU job APIs, scores each one
against your profile using a local open-source LLM (with a deterministic keyword
fallback), and surfaces results in a web UI with clickable apply links — or as a
ranked markdown digest and CSV if you prefer the CLI.

Supports multiple profiles via separate config files. Ships with two:

| Config | Profile |
|--------|---------|
| `config.yaml` | Clinical informatics / healthcare data engineer |
| `config-sped.yaml` | Special education teacher (US-licensed, targeting international schools) |

Everything is configurable in the YAML files.

## How it works

```
config.yaml (profile + queries)
      |
      v
  sources  ──►  Arbeitnow (no key) + Jooble (all 6) + Adzuna (DE,NL,FR,IE,GB)
      |
      v
  US location filter (drops "City, ST" / "United States" results)
      |
      v
  dedupe (same role across sources collapses; richer record wins)
      |
      v
  scoring  ──►  Ollama local LLM  ──(if down)──►  keyword fallback
      |
      v
  Web UI (streamlit run app.py)  or  output/job-matches-<timestamp>.md + .csv
```

The agent uses official, terms-compliant APIs only — no scraping LinkedIn or Indeed.

## Quickstart

```bash
git clone https://github.com/BrandenPConnolly/EU-Job-Agent.git
cd EU-Job-Agent
git checkout claude/eu-job-scraper-agent-j4l37l

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env   # fill in API keys (see below)
```

### Web UI (recommended)

```bash
streamlit run app.py
# Opens at http://localhost:8501
```

Pick a profile in the sidebar, choose countries and sources, then click
**Run demo** (offline, no keys needed) or **Run search** (live).

### CLI

```bash
# No keys, keyword scoring — works immediately:
python run.py search --no-llm

# Special education profile:
python run.py --config config-sped.yaml search --no-llm

# Check which sources are credentialed and LLM status:
python run.py sources

# Offline demo (no network needed):
python run.py demo --no-llm
```

Reports land in `./output/`.

## Getting the most out of it

### 1. Add a Jooble key (covers all six countries including BE and FR)

Free key at https://jooble.org/api/about — email request, usually same day.

```bash
# put JOOBLE_API_KEY=your_key in .env
```

### 2. Add Adzuna for richer DE/NL/FR/IE/GB salary data

Free key pair at https://developer.adzuna.com/ → add `ADZUNA_APP_ID` and
`ADZUNA_APP_KEY` to `.env`.

### 3. Run the local LLM scorer

Install Ollama (https://ollama.com), then pull a model:

```bash
ollama pull llama3.2             # solid default, fast on a laptop
# or
ollama pull qwen2.5:7b-instruct  # sharper judgment, needs more VRAM
```

Set `OLLAMA_MODEL` in `.env` if using a non-default model. With Ollama running,
the web UI LLM toggle and `python run.py search` will use it automatically. If
Ollama is unreachable, every job falls back to the keyword scorer silently.

## Web UI features

- **Profile switcher** — dropdown auto-discovers all `config*.yaml` files
- **Country & source checkboxes** with flag emojis
- **Score slider, LLM toggle, per-source volume** controls
- **Run demo** — scores built-in sample jobs offline (great for testing)
- **Job cards** — colour-coded score badge (green/amber/red), fit bullets, concern
  bullets, and an **Apply →** button that opens the posting in a new tab
- **Filter bar** — narrow results by verdict, country, or source after a run
- **Summary metrics** — total / strong / possible / weak / scorer used
- **Data table + CSV download** in an expandable panel

## CLI reference

`--config` selects the profile and always goes **before** the subcommand:

```bash
python run.py search                                        # default profile, live
python run.py --config config-sped.yaml search             # wife's profile, live
python run.py search --countries nl,de,ie                  # filter countries
python run.py search --query "data engineer; ETL developer" # custom queries
python run.py search --per-source 40 --min-score 55 --top 30
python run.py search --no-llm                              # force keyword scorer
python run.py search --out ./reports                       # custom output dir
python run.py sources                                      # credential + LLM status
python run.py demo --no-llm                                # offline test
```

## Source coverage

| Source    | Key needed | Countries            | Notes                     |
|-----------|------------|----------------------|---------------------------|
| Arbeitnow | none       | DE, NL, BE, FR, IE, GB | Works on first launch  |
| Jooble    | free key   | NL, BE, DE, FR, IE, GB | Primary breadth source |
| Adzuna    | free pair  | DE, NL, FR, IE, GB  | No BE; good salary data   |

## Scoring

**LLM path (Ollama):** each job is sent to the model with your full profile
summary and the job description. The model returns a 0–100 score, verdict, fit
reasons, concerns, and a language-requirement flag. Temperature is set to 0.1
for consistent output.

**Keyword fallback:** used automatically when Ollama is unreachable. Points are
awarded for skill-term overlap (up to 55 pts), target-title match (25 pts), and
preferred location (12 pts). Language penalties apply to both paths:

| Language signal | Penalty |
|-----------------|---------|
| Non-English language hard required | −15 pts |
| Non-English language preferred (soft) | −5 pts |
| "No X required" / negated | 0 pts |
| English stated as working language | positive note added |

Covers Dutch, French, German, Flemish, Spanish, Italian, Portuguese, Polish, and
Nordic languages. Negation ("no Dutch required", "not mandatory") is handled.

## Multiple profiles

Each config file is self-contained — profile, queries, countries, and threshold.
To add a new one:

```bash
cp config.yaml config-myprofile.yaml
# edit config-myprofile.yaml
python run.py --config config-myprofile.yaml search
# also appears automatically in the web UI profile dropdown
```

## Tuning the match

In your config YAML:

- `profile.skills`, `profile.domains`, `profile.target_titles`,
  `profile.preferred_locations`, `profile.constraints` — feed both the LLM
  prompt and keyword scorer.
- `search.queries` — run against every country on every available source.
- `search.countries` — `[nl, be, de, fr, ie, gb]` by default.
- `scoring.min_score` — filter threshold (0–100).
- `scoring.use_llm` — set to `false` to always use keyword scorer.

## Extending it

- **New source:** subclass `JobSource` in `jobagent/sources/`, implement
  `fetch()` and `available`, add to `ALL_SOURCES` in `sources/__init__.py`,
  and list country coverage in `SUPPORTED` in `sources/base.py`.
- **AcademicTransfer:** `academictransfer.com` covers Amsterdam UMC, Erasmus MC,
  and other Dutch academic medical centers — a strong next source to add for the
  clinical informatics profile.
- **Scheduling:** wrap `python run.py search` in a cron job or launchd agent for
  a daily digest.

## Environment variables

| Variable         | Default                  | Description           |
|------------------|--------------------------|-----------------------|
| `JOOBLE_API_KEY` | —                        | Jooble API key        |
| `ADZUNA_APP_ID`  | —                        | Adzuna app ID         |
| `ADZUNA_APP_KEY` | —                        | Adzuna app key        |
| `OLLAMA_HOST`    | `http://localhost:11434` | Ollama server URL     |
| `OLLAMA_MODEL`   | `llama3.2`               | Model to use          |
