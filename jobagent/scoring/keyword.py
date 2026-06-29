"""Deterministic keyword scorer — fallback when Ollama is unreachable.

Rewards: skill-term overlap (capped at 55 pts), target-title match (25 pts),
preferred-location match (12 pts). Penalizes non-English language requirements
(-15 pts) or ambiguous/bilingual requirements (-5 pts).
"""
from __future__ import annotations

import re

from ..models import JobPosting, ScoredJob

# Non-English languages and their native-language equivalents.
# Each entry: (language_name_en, native_word, fluency_signal_pattern)
_LANGUAGES = [
    ("Dutch",      "nederlands",  r"dutch|nederlands(e|talig)?"),
    ("French",     "français",    r"french|fran[cç]ais(e)?"),
    ("German",     "deutsch",     r"german|deutsch(e|kenntnisse)?"),
    ("Flemish",    "vlaams",      r"flemish|vlaams(e)?"),
    ("Spanish",    "español",     r"spanish|espa[nñ]ol"),
    ("Italian",    "italiano",    r"italian(o)?"),
    ("Portuguese", "português",   r"portugu[eê]s(e)?"),
    ("Polish",     "polski",      r"polish|polski"),
    ("Swedish",    "svenska",     r"swedish|svenska"),
    ("Danish",     "dansk",       r"danish|dansk"),
    ("Finnish",    "suomi",       r"finnish|suomi"),
    ("Norwegian",  "norsk",       r"norwegian|norsk"),
]

# Fluency/requirement signal words
_HARD_SIGNALS = re.compile(
    r"\b(required|fluent|fluen|native|mandatory|essential|proficien|"
    r"vereist|verplicht|requis|erforderlich|voraussetzung)\b",
    re.IGNORECASE,
)
_SOFT_SIGNALS = re.compile(
    r"\b(preferred|advantage|plus|bonus|desirable|nice\s+to\s+have)\b",
    re.IGNORECASE,
)
_NEGATION = re.compile(r"\b(no|not|without|don.t|doesn.t)\s*$", re.IGNORECASE)

# English positively mentioned as the working language
_ENGLISH_WORKING = re.compile(
    r"(working\s+language[s]?\s+(is\s+)?english"
    r"|english[\w\s]{0,20}working\s+language"
    r"|english[\w\s]{0,10}(only|medium|first\s+language)"
    r"|our\s+(team\s+)?language\s+is\s+english"
    r"|we\s+work\s+in\s+english"
    r"|international\s+(team|environment|school|company)[\w\s,]{0,60}english)",
    re.IGNORECASE,
)

_WINDOW = 55  # chars to scan on each side of a language mention


def _signal_is_negated(text: str, sig_start: int) -> bool:
    """True if a negation word immediately precedes the signal (within ~15 chars)."""
    before = text[max(0, sig_start - 15):sig_start]
    return bool(_NEGATION.search(before))


def _detect_language_requirement(text: str) -> tuple[str | None, bool]:
    """
    Returns (language_name, is_required).
    language_name is None if no non-English language requirement detected.
    is_required is True for hard requirements, False for preferred/bonus.
    """
    t = (text or "").lower()

    for lang_name, _, lang_pat in _LANGUAGES:
        lang_re = re.compile(rf"\b({lang_pat})\b", re.IGNORECASE)
        for m in lang_re.finditer(t):
            ls, le = m.span()
            # Check negation right before the language word itself
            if _NEGATION.search(t[max(0, ls - 10):ls]):
                continue

            before = t[max(0, ls - _WINDOW):ls]
            after = t[le:le + _WINDOW]
            context = before + " " + after

            # Hard signal in context, not negated
            for sig in _HARD_SIGNALS.finditer(context):
                if not _signal_is_negated(context, sig.start()):
                    return lang_name, True

            # Soft signal in context
            if _SOFT_SIGNALS.search(context):
                return lang_name, False

    return None, False


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"\W+", (text or "").lower()) if len(t) > 2}


def _phrase_in(phrase: str, raw_text: str, token_set: set[str]) -> bool:
    if " " in phrase:
        return phrase in raw_text
    return phrase in token_set


class KeywordScorer:
    def __init__(self, config):
        p = config.profile
        self.skills = [s.lower() for s in p.get("skills", [])]
        self.titles = [t.lower() for t in p.get("target_titles", [])]
        self.locations = [l.lower() for l in p.get("preferred_locations", [])]

    def score(self, job: JobPosting) -> ScoredJob:
        title = job.title.lower()
        blob = job.text_blob.lower()
        blob_tokens = _tokens(blob)
        title_tokens = _tokens(title)

        matched_skills = [s for s in self.skills if _phrase_in(s, blob, blob_tokens)]
        title_hits = [t for t in self.titles if _phrase_in(t, title, title_tokens)]
        loc_hit = any(l in (job.location.lower() + " " + blob) for l in self.locations)

        skill_pts = min(55, len(matched_skills) * 9)
        title_pts = 25 if title_hits else 0
        loc_pts = 12 if loc_hit else 0

        lang, is_required = _detect_language_requirement(blob)
        english_working = bool(_ENGLISH_WORKING.search(blob))

        if lang and is_required:
            lang_penalty = 15
        elif lang and not is_required:
            lang_penalty = 5   # soft preference, small nudge
        else:
            lang_penalty = 0

        raw = skill_pts + title_pts + loc_pts - lang_penalty
        score = max(0, min(100, raw))
        verdict = "strong" if score >= 70 else "possible" if score >= 45 else "weak"

        reasons: list[str] = []
        if title_hits:
            reasons.append(f"title matches target role ({', '.join(title_hits[:2])})")
        if matched_skills:
            reasons.append(f"{len(matched_skills)} skill matches: {', '.join(matched_skills[:6])}")
        if loc_hit:
            reasons.append("in a preferred location")
        if english_working:
            reasons.append("English stated as working language")

        concerns: list[str] = []
        if lang and is_required:
            concerns.append(f"{lang} fluency required")
        elif lang and not is_required:
            concerns.append(f"{lang} preferred (not required)")
        if not matched_skills:
            concerns.append("no core-skill overlap detected")

        return ScoredJob(
            job=job,
            score=score,
            verdict=verdict,
            reasons=reasons,
            concerns=concerns,
            dutch_required=lang == "Dutch" and is_required,
            entry_note="",
            scored_by="keyword",
        )
