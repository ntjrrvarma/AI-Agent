"""Load settings from environment (.env supported via python-dotenv)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    primary_provider: str  # "local" | "gemini"
    openai_base_url: str
    openai_api_key: str
    local_model: str
    gemini_model: str
    gemini_api_key: str | None
    database_path: Path
    skills_dir: Path
    recent_messages_limit: int
    summarize_every_n_messages: int


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    provider = os.environ.get("PRIMARY_PROVIDER", "local").strip().lower()
    if provider not in ("local", "gemini"):
        provider = "local"

    db_raw = os.environ.get("DATABASE_PATH", str(PROJECT_ROOT / "agent_memory.sqlite"))
    skills_raw = os.environ.get("SKILLS_DIR", str(PROJECT_ROOT / "skills"))

    return Settings(
        primary_provider=provider,
        openai_base_url=os.environ.get(
            "OPENAI_BASE_URL", "http://127.0.0.1:1234/v1"
        ).rstrip("/"),
        openai_api_key=os.environ.get("OPENAI_API_KEY", "lm-studio"),
        local_model=os.environ.get("LOCAL_MODEL", "local-model"),
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        gemini_api_key=os.environ.get("GEMINI_API_KEY") or None,
        database_path=Path(db_raw).expanduser().resolve(),
        skills_dir=Path(skills_raw).expanduser().resolve(),
        recent_messages_limit=int(os.environ.get("RECENT_MESSAGES_LIMIT", "40")),
        summarize_every_n_messages=int(os.environ.get("SUMMARIZE_EVERY_N_MESSAGES", "30")),
    )
