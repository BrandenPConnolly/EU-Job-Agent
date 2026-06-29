# EU Job Agent

A local Python agent that pulls job postings from EU job APIs, scores each one
against your profile using a local open-source LLM (with a deterministic keyword
fallback), and writes a ranked markdown digest plus a CSV you can track in a
spreadsheet.

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
  US location filter (drops City, ST / "United States" results)
      |
      v
  dedupe (same role across sources collapses; richer record wins)
      |
      v
  scoring  ──►  Ollama local LLM  ──(if down)──►  keyword fallback
      |
      v
  output/job-matches-<timestamp>.md  +  .csv
```

The agent uses official, terms-compliant APIs only — no scraping LinkedIn or Indeed.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run with no keys (Arbeitnow only), keyword scoring:
python run.py search --no-llm

# Run the special education profile:
python run.py --config config-sped.yaml search --no-llm

# See which sources are ready and LLM status:
python run.py sources

# Offline demo — scores built-in samples, no network needed:
python run.py demo --no-llm
```

Reports land in `./output/`.

## Getting the most out of it

### 1. Add a Jooble key (covers all six countries including BE and FR)

```bash
cp .env.example .env
# put your key in JOOBLE_API_KEY=
```

Free key at https://jooble.org/api/about (email request, usually same day).

### 2. Add Adzuna for richer DE/NL/FR/IE/GB salary data

Free key pair at https://developer.adzuna.com/ → `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.

### 3. Run the local LLM scorer

Install Ollama (https://ollama.com), then pull a model:

```bash
ollama pull llama3.2          # solid default, fast on a laptop
# or
ollama pull qwen2.5:7b-instruct
# or, if you have the VRAM:
ollama pull qwen2.5:14b-instruct
```

Set `OLLAMA_MODEL` in `.env` to match. With Ollama running:

```bash
python run.py search
```

The LLM scorer uses `/api/chat` with `format: json` and `temperature: 0.1`. If the
server is down or a response is malformed, it falls back to the keyword scorer
per-posting. Every result records whether it was scored by `llm` or `keyword`.

## CLI reference

`--config` selects the profile and always goes before the subcommand:

```bash
# Clinical informatics profile (default):
python run.py search

# Special education profile:
python run.py --config config-sped.yaml search

# Filter countries and queries:
python run.py search --countries nl,de,ie --query "clinical data scientist; data engineer"

# Tune volume and threshold:
python run.py search --per-source 40 --min-score 55 --top 30

# Force keyword scorer (no Ollama needed):
python run.py search --no-llm

# Change output directory:
python run.py search --out ./reports

# Check source and LLM status:
python run.py sources
python run.py --config config-sped.yaml sources

# Offline demo (no network):
python run.py demo --no-llm
```

## Source coverage

| Source     | Key needed | Countries covered         | Notes                          |
|------------|------------|---------------------------|--------------------------------|
| Arbeitnow  | none       | DE, NL, BE, FR, IE, GB   | Works immediately, no key      |
| Jooble     | free key   | NL, BE, DE, FR, IE, GB   | Primary breadth source         |
| Adzuna     | free pair  | DE, NL, FR, IE, GB       | No BE; good salary data        |

## Multiple profiles

Each config file is fully self-contained — different profile, queries, countries, and scoring threshold. To add a new profile, copy an existing config and edit it:

```bash
cp config.yaml config-myprofile.yaml
# edit config-myprofile.yaml
python run.py --config config-myprofile.yaml search
```

## Tuning the match

Edit `config.yaml` (or whichever config file you're using):

- `profile.skills`, `profile.domains`, `profile.target_titles`,
  `profile.preferred_locations`, `profile.constraints` feed both the LLM prompt
  and the keyword scorer.
- `search.queries` — run against every country on every available source.
- `search.countries` — `[nl, be, de, fr, ie, gb]` by default.
- `scoring.min_score` — filter the report (0–100).
- `scoring.use_llm` — toggle the LLM path.

The keyword scorer awards points for:
- Skill-term overlap (up to 55 pts)
- Target-title match (25 pts)
- Preferred location (12 pts)
- Penalty for Dutch fluency required (−12 pts)

## Extending it

- **New source:** subclass `JobSource` in `jobagent/sources/`, implement
  `fetch()` and `available`, add it to `ALL_SOURCES` in `sources/__init__.py`,
  and list its country coverage in `SUPPORTED` in `sources/base.py`.
- **AcademicTransfer:** `academictransfer.com` covers Amsterdam UMC, Erasmus MC,
  and other Dutch academic medical centers — a strong next source to add.
- **Scheduling:** wrap `python run.py search` in a cron job or launchd agent
  for a fresh digest on a cadence.

## Environment variables

| Variable         | Default                    | Description                |
|------------------|----------------------------|----------------------------|
| `JOOBLE_API_KEY` | —                          | Jooble API key             |
| `ADZUNA_APP_ID`  | —                          | Adzuna app ID              |
| `ADZUNA_APP_KEY` | —                          | Adzuna app key             |
| `OLLAMA_HOST`    | `http://localhost:11434`   | Ollama server URL          |
| `OLLAMA_MODEL`   | `llama3.2`                 | Model to use               |
