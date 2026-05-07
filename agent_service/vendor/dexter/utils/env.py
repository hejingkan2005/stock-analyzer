"""Environment loading — calls dotenv on import."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    """Load .env from CWD then from DEXTER_HOME (no override)."""
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
    home_env = Path.home() / ".dexter" / ".env"
    if home_env.exists():
        load_dotenv(dotenv_path=home_env, override=False)


def get_env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


def has_env(name: str) -> bool:
    return bool(os.environ.get(name))
