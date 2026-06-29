"""
Job-resume matching: tries Ollama LLM first, falls back to regex/keyword scoring.
"""
import json
import logging
import re
from typing import Optional

import requests

from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from models import Job
from resume import MUST_HAVE_KEYWORDS, NICE_TO_HAVE_KEYWORDS, RESUME_TEXT

logger = logging.getLogger(__name__)

_OLLAMA_AVAILABLE: Optional[bool] = None  # cached after first check

OLLAMA_PROMPT = """You are a job-resume matching assistant. Score how well the job matches the candidate's resume on a scale from 0.0 to 1.0.

RESUME SUMMARY:
{resume}

JOB:
Title: {title}
Company: {company}
Location: {location}
Description: {description}

Respond with JSON only — no other text:
{{"score": <float 0.0-1.0>, "reason": "<one sentence>"}}

Score guide:
- 0.8-1.0: Strong match — title, skills, and domain align well
- 0.5-0.8: Partial match — some relevant skills/experience
- 0.2-0.5: Weak match — tangentially related
- 0.0-0.2: Not a match
"""


def _check_ollama() -> bool:
    global _OLLAMA_AVAILABLE
    if _OLLAMA_AVAILABLE is not None:
        return _OLLAMA_AVAILABLE
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        available = any(OLLAMA_MODEL.split(":")[0] in m for m in models)
        if not available:
            logger.warning(
                "Ollama is running but model '%s' not found (available: %s). "
                "Run: ollama pull %s",
                OLLAMA_MODEL, models, OLLAMA_MODEL,
            )
        _OLLAMA_AVAILABLE = available
    except Exception:
        logger.info("Ollama not reachable at %s — using regex matcher", OLLAMA_BASE_URL)
        _OLLAMA_AVAILABLE = False
    return _OLLAMA_AVAILABLE


def _ollama_score(job: Job) -> Optional[tuple[float, str]]:
    prompt = OLLAMA_PROMPT.format(
        resume=RESUME_TEXT[:2000],
        title=job.title,
        company=job.company,
        location=job.location,
        description=(job.description or "")[:1000],
    )
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "")
        # Extract JSON from the response
        match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        if not match:
            return None
        parsed = json.loads(match.group())
        score = float(parsed.get("score", 0))
        reason = str(parsed.get("reason", ""))
        return max(0.0, min(1.0, score)), reason
    except Exception as exc:
        logger.debug("Ollama scoring failed: %s", exc)
        return None


def _regex_score(job: Job) -> tuple[float, str]:
    """Keyword-frequency scoring as fallback."""
    combined = (job.title + " " + job.description).lower()

    must_hits = [kw for kw in MUST_HAVE_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', combined)]
    nice_hits = [kw for kw in NICE_TO_HAVE_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', combined)]

    must_score = len(must_hits) / max(len(MUST_HAVE_KEYWORDS), 1)
    nice_score = len(nice_hits) / max(len(NICE_TO_HAVE_KEYWORDS), 1)
    score = round(0.65 * must_score + 0.35 * nice_score, 3)

    if must_hits:
        reason = f"Matched keywords: {', '.join(must_hits[:5])}"
        if nice_hits:
            reason += f"; also: {', '.join(nice_hits[:3])}"
    else:
        reason = f"Weak match — no core keywords found"

    return score, reason


def score_job(job: Job) -> Job:
    """Score job in-place and return it."""
    if _check_ollama():
        result = _ollama_score(job)
        if result:
            job.match_score, job.match_reason = result
            return job
        # Ollama failed mid-run; fall through to regex
        logger.debug("Ollama returned no result for '%s', falling back to regex", job.title)

    score, reason = _regex_score(job)
    job.match_score = score
    job.match_reason = "(regex) " + reason
    return job
