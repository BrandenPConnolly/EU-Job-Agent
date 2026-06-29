# EU Job Agent

Scrapes EU job boards for roles matching your resume, scores them with an open-source LLM (Ollama) and falls back to regex keyword matching.

## Sources

| Source | Countries | API Key? |
|--------|-----------|----------|
| [Arbeitnow](https://www.arbeitnow.com/api/job-board-api) | DE, NL, FR, IE, BE, GB | None — public API |
| [Adzuna](https://developer.adzuna.com/) | DE, NL, FR, IE, GB | Free registration |
| [Jooble](https://jooble.org/api/about) | DE, NL, FR, IE, BE, GB | Free registration |

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy and fill in credentials
cp .env.example .env
# Edit .env with your Adzuna + Jooble keys

# 3. (Optional) Install Ollama + model for LLM matching
#    https://ollama.com/download
ollama pull llama3.2

# 4. Run
python main.py
```

## Usage

```bash
# All defaults (all countries, all sources, all queries)
python main.py

# Filter by country
python main.py --countries DE NL IE

# Custom search queries
python main.py --queries "data engineer" "clinical informatics" "analytics engineer"

# Only use Arbeitnow (no API key needed)
python main.py --sources arbeitnow

# Force regex matching (no Ollama needed)
python main.py --no-ollama

# Only show strong matches
python main.py --min-score 0.6

# Skip saving to disk
python main.py --no-save
```

## Matching

1. **Ollama (LLM)** — if Ollama is running locally with the configured model, each job is scored 0–1 by the LLM against your full resume. Scores reflect title, skill, and domain alignment.
2. **Regex fallback** — if Ollama is unreachable or the model isn't available, keyword frequency scoring is used based on must-have and nice-to-have terms from your resume.

Edit `resume.py` to update your profile or tune keyword lists.

## Output

Results are saved to `output/` as both JSON and CSV, and a ranked summary is printed to the terminal.

## Configuration

All settings can be set via environment variables or `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ADZUNA_APP_ID` | — | Adzuna app ID |
| `ADZUNA_APP_KEY` | — | Adzuna app key |
| `JOOBLE_API_KEY` | — | Jooble API key |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Model to use |
| `MIN_MATCH_SCORE` | `0.4` | Display threshold (0–1) |
| `MAX_JOBS_PER_SOURCE` | `25` | Jobs per source per query per country |
| `OUTPUT_DIR` | `output` | Where to save results |
