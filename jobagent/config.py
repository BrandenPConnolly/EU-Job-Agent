"""Configuration loading: YAML profile + environment secrets."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"


@dataclass
class Config:
    profile: dict = field(default_factory=dict)
    search: dict = field(default_factory=dict)
    scoring: dict = field(default_factory=dict)
    # secrets from environment
    jooble_key: str = ""
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    @property
    def countries(self) -> list[str]:
        return [c.lower() for c in self.search.get("countries", [])]

    @property
    def queries(self) -> list[str]:
        return self.search.get("queries", [])

    @property
    def min_score(self) -> int:
        return int(self.scoring.get("min_score", 0))

    @property
    def use_llm(self) -> bool:
        return bool(self.scoring.get("use_llm", True))

    @property
    def profile_summary(self) -> str:
        """Compact natural-language profile the scorer reasons against."""
        p = self.profile
        bits = []
        if p.get("headline"):
            bits.append(p["headline"])
        if p.get("skills"):
            bits.append("Core skills: " + ", ".join(p["skills"]) + ".")
        if p.get("domains"):
            bits.append("Domains: " + ", ".join(p["domains"]) + ".")
        if p.get("target_titles"):
            bits.append("Target roles: " + ", ".join(p["target_titles"]) + ".")
        if p.get("preferred_locations"):
            bits.append("Preferred locations: " + ", ".join(p["preferred_locations"]) + ".")
        if p.get("constraints"):
            bits.append("Constraints: " + " ".join(p["constraints"]))
        return "\n".join(bits)


def load_config(path: str | os.PathLike | None = None) -> Config:
    cfg_path = Path(path) if path else DEFAULT_CONFIG
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")
    raw = yaml.safe_load(cfg_path.read_text()) or {}
    return Config(
        profile=raw.get("profile", {}),
        search=raw.get("search", {}),
        scoring=raw.get("scoring", {}),
        jooble_key=os.getenv("JOOBLE_API_KEY", ""),
        adzuna_app_id=os.getenv("ADZUNA_APP_ID", ""),
        adzuna_app_key=os.getenv("ADZUNA_APP_KEY", ""),
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
    )
