"""HTTP client for the Financial Datasets API.

Mirrors src/tools/finance/api.ts. Provides a small ``api`` wrapper with optional
on-disk caching for immutable historical data.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

import httpx

from ...utils.cache import describe_request, read_cache, write_cache
from ...utils.logger import logger

BASE_URL = "https://api.financialdatasets.ai"

TTL_15M = 15 * 60 * 1000
TTL_1H = 60 * 60 * 1000
TTL_24H = 24 * 60 * 60 * 1000


def _api_key() -> str:
    return os.environ.get("FINANCIAL_DATASETS_API_KEY", "")


def _headers() -> dict[str, str]:
    return {"x-api-key": _api_key()} if _api_key() else {}


def _build_url(endpoint: str, params: dict[str, Any]) -> str:
    # Filter None and flatten lists like httpx would
    cleaned: list[tuple[str, str]] = []
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            for item in v:
                cleaned.append((k, str(item)))
        else:
            cleaned.append((k, str(v)))
    qs = urlencode(cleaned)
    return f"{BASE_URL}{endpoint}?{qs}" if qs else f"{BASE_URL}{endpoint}"


def get(
    endpoint: str,
    params: dict[str, Any] | None = None,
    *,
    cacheable: bool = False,
    ttl_ms: int | None = None,
) -> dict[str, Any]:
    params = params or {}
    label = describe_request(endpoint, params)

    if cacheable:
        cached = read_cache(endpoint, params, ttl_ms)
        if cached:
            return cached

    url = _build_url(endpoint, params)

    if not _api_key():
        logger.warning("[Financial Datasets API] call without key: %s", label)

    try:
        resp = httpx.get(url, headers=_headers(), timeout=30.0)
    except httpx.HTTPError as e:
        raise RuntimeError(f"[Financial Datasets API] request failed for {label}: {e}") from e

    if resp.status_code >= 400:
        raise RuntimeError(
            f"[Financial Datasets API] request failed: {resp.status_code} {resp.reason_phrase}"
        )

    try:
        data = resp.json()
    except ValueError as e:
        raise RuntimeError(f"[Financial Datasets API] parse error for {label}: {e}") from e

    result = {"data": data, "url": url}
    if cacheable:
        write_cache(endpoint, params, data, url)
    return result


def post(endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json", **_headers()}
    try:
        resp = httpx.post(url, json=body, headers=headers, timeout=30.0)
    except httpx.HTTPError as e:
        raise RuntimeError(f"[Financial Datasets API] POST {endpoint} failed: {e}") from e
    if resp.status_code >= 400:
        raise RuntimeError(
            f"[Financial Datasets API] request failed: {resp.status_code} {resp.reason_phrase}"
        )
    try:
        data = resp.json()
    except ValueError as e:
        raise RuntimeError(f"[Financial Datasets API] parse error for POST {endpoint}: {e}") from e
    return {"data": data, "url": url}


def strip_fields_deep(value: Any, fields: tuple[str, ...]) -> Any:
    """Recursively remove the given keys from dicts to reduce token usage."""
    skip = set(fields)

    def walk(node: Any) -> Any:
        if isinstance(node, list):
            return [walk(x) for x in node]
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items() if k not in skip}
        return node

    return walk(value)
