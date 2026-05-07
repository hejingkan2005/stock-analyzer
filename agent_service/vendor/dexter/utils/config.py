"""User settings persisted at .dexter/settings.json."""

from __future__ import annotations

import json
from typing import Any

from .paths import settings_path


def load_settings() -> dict[str, Any]:
    p = settings_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(data: dict[str, Any]) -> None:
    p = settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_setting(key: str, default: Any = None) -> Any:
    return load_settings().get(key, default)


def set_setting(key: str, value: Any) -> None:
    data = load_settings()
    data[key] = value
    save_settings(data)
