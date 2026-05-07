"""Error classification utilities — mirrors src/utils/errors.ts (simplified)."""

from __future__ import annotations


def is_non_retryable_error(message: str) -> bool:
    m = message.lower()
    return any(
        kw in m
        for kw in (
            "401",
            "403",
            "invalid api key",
            "incorrect api key",
            "unauthorized",
            "forbidden",
            "not found",
            "permission",
        )
    )


def classify_error(message: str) -> str:
    m = message.lower()
    if "rate limit" in m or "429" in m:
        return "rate_limit"
    if "timeout" in m:
        return "timeout"
    if any(c in m for c in ("network", "fetch failed", "econnreset", "enotfound")):
        return "network"
    if any(c in m for c in ("401", "403", "unauthorized", "forbidden", "invalid api key")):
        return "auth"
    if "context" in m and ("length" in m or "window" in m or "exceed" in m):
        return "context_overflow"
    return "unknown"


def is_context_overflow_error(message: str) -> bool:
    return classify_error(message) == "context_overflow"


def format_user_facing_error(err: Exception) -> str:
    msg = str(err)
    kind = classify_error(msg)
    prefix = {
        "rate_limit": "Rate limit exceeded",
        "timeout": "Request timed out",
        "network": "Network error",
        "auth": "Authentication error",
        "context_overflow": "Context window exceeded",
    }.get(kind, "Error")
    return f"{prefix}: {msg}"
