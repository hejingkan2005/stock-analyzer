"""Path helpers — mirrors src/utils/paths.ts."""

from __future__ import annotations

import os
from pathlib import Path


def dexter_root() -> Path:
    """Return the .dexter/ working directory under the user's home."""
    root = Path(os.environ.get("DEXTER_HOME") or Path.home() / ".dexter")
    root.mkdir(parents=True, exist_ok=True)
    return root


def dexter_path(*parts: str) -> Path:
    p = dexter_root().joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def scratchpad_dir() -> Path:
    p = dexter_root() / "scratchpad"
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_dir() -> Path:
    p = dexter_root() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def settings_path() -> Path:
    return dexter_root() / "settings.json"
