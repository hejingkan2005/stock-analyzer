"""Lightweight on-disk JSON cache for tool results.

Mirrors src/utils/cache.ts (simplified). Keys are deterministic hashes of
(endpoint, params).
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .paths import cache_dir


def _key(endpoint: str, params: dict[str, Any]) -> str:
    canonical = json.dumps([endpoint, params], sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def describe_request(endpoint: str, params: dict[str, Any]) -> str:
    parts = [f"{k}={v}" for k, v in sorted(params.items()) if v is not None]
    return f"{endpoint}?{'&'.join(parts)}" if parts else endpoint


def read_cache(endpoint: str, params: dict[str, Any], ttl_ms: int | None = None) -> dict[str, Any] | None:
    f = cache_dir() / f"{_key(endpoint, params)}.json"
    if not f.exists():
        return None
    try:
        payload = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None
    if ttl_ms is not None:
        age_ms = (time.time() - payload.get("_ts", 0)) * 1000
        if age_ms > ttl_ms:
            return None
    return {"data": payload["data"], "url": payload.get("url", "")}


def write_cache(endpoint: str, params: dict[str, Any], data: dict[str, Any], url: str) -> None:
    f = cache_dir() / f"{_key(endpoint, params)}.json"
    payload = {"_ts": time.time(), "data": data, "url": url}
    try:
        f.write_text(json.dumps(payload), encoding="utf-8")
    except Exception:
        pass
