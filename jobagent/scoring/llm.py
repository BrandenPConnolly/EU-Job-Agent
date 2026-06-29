"""Local open-source LLM scorer via Ollama, with per-job keyword fallback.

Uses /api/chat with format:json and temperature 0.1 for deterministic output.
Any failure (server down, model missing, bad JSON) silently falls back to
KeywordScorer for that posting, and each result records which path scored it.
"""
from __future__ import annotations

import json
import re

import requests

from ..models import JobPosting, ScoredJob
from .keyword import KeywordScorer

SYSTEM = (
    "You are a careful technical recruiter screening EU job postings for one "
    "candidate. Judge genuine fit, not enthusiasm. Respond with ONLY a JSON "
    "object — no prose, no markdown fences."
)

PROMPT = """Candidate profile:
{profile}

Job posting:
Title: {title}
Company: {company}
Location: {location} ({country})
Description: {description}

Return a JSON object with exactly these keys:
{{
  "score": <integer 0-100, overall fit>,
  "verdict": "strong" | "possible" | "weak",
  "reasons": [<up to 3 short strings on why it fits>],
  "concerns": [<up to 3 short strings on risks or gaps>],
  "dutch_required": <true|false — does the role require Dutch fluency?>,
  "entry_note": "<one short line on EU-family-member / sponsorship relevance, or empty>"
}}"""


class LLMScorer:
    def __init__(self, config):
        self.config = config
        self.host = config.ollama_host.rstrip("/")
        self.model = config.ollama_model
        self.fallback = KeywordScorer(config)
        self.profile = config.profile_summary

    def healthy(self) -> bool:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            if r.status_code != 200:
                return False
            models = [m.get("name", "") for m in r.json().get("models", [])]
            base = self.model.split(":")[0]
            if not any(base in m for m in models):
                return False
            return True
        except requests.RequestException:
            return False

    def score(self, job: JobPosting) -> ScoredJob:
        prompt = PROMPT.format(
            profile=self.profile,
            title=job.title,
            company=job.company or "unknown",
            location=job.location or "unknown",
            country=job.country.upper(),
            description=(job.description or "")[:2500],
        )
        try:
            resp = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1},
                },
                timeout=120,
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
            data = _parse_json(content)
        except (requests.RequestException, ValueError, KeyError):
            return self.fallback.score(job)

        if not data:
            return self.fallback.score(job)
        return _to_scored(job, data)


def _parse_json(content: str) -> dict | None:
    content = content.strip()
    content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
    try:
        return json.loads(content)
    except ValueError:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except ValueError:
            return None


def _to_scored(job: JobPosting, data: dict) -> ScoredJob:
    try:
        score = int(round(float(data.get("score", 0))))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))
    verdict = str(data.get("verdict", "")).lower()
    if verdict not in {"strong", "possible", "weak"}:
        verdict = "strong" if score >= 70 else "possible" if score >= 45 else "weak"

    def _list(key: str) -> list[str]:
        v = data.get(key, [])
        if isinstance(v, str):
            v = [v]
        return [str(x) for x in v][:3]

    return ScoredJob(
        job=job,
        score=score,
        verdict=verdict,
        reasons=_list("reasons"),
        concerns=_list("concerns"),
        dutch_required=data.get("dutch_required"),
        entry_note=str(data.get("entry_note", "") or ""),
        scored_by="llm",
    )
