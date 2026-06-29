import os

# ── Countries ──────────────────────────────────────────────────────────────────
# Mapping of ISO country code → Adzuna country slug
COUNTRIES = {
    "DE": "de",
    "NL": "nl",
    "FR": "fr",
    "IE": "ie",
    "BE": "be",  # Adzuna doesn't support BE — scraped via Arbeitnow/Jooble only
    "GB": "gb",  # UK
}

# ── Search terms ───────────────────────────────────────────────────────────────
SEARCH_QUERIES = [
    "data engineer",
    "clinical data analyst",
    "health informatics",
    "ETL developer",
    "analytics engineer",
    "clinical informatics",
]

# ── API credentials (set via env vars or .env file) ────────────────────────────
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY", "")

# Adzuna supports these countries (BE not available):
ADZUNA_SUPPORTED = {"de", "nl", "fr", "ie", "gb"}

# ── Ollama ─────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# ── Scoring thresholds ─────────────────────────────────────────────────────────
MIN_MATCH_SCORE = float(os.getenv("MIN_MATCH_SCORE", "0.4"))  # 0-1

# ── Output ─────────────────────────────────────────────────────────────────────
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
MAX_JOBS_PER_SOURCE_PER_QUERY = int(os.getenv("MAX_JOBS_PER_SOURCE", "25"))
