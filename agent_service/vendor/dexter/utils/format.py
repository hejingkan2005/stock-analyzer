"""Output formatting helpers."""

from __future__ import annotations

import json
from typing import Any


def format_tool_result(data: Any, sources: list[str] | None = None) -> str:
    """Mirror of formatToolResult from src/tools/types.ts.

    Returns a compact JSON string. The source URLs (if any) are appended as a
    trailing block so the LLM can cite them.
    """
    payload: dict[str, Any] = {"data": data}
    if sources:
        payload["sources"] = sources
    try:
        return json.dumps(payload, default=str, ensure_ascii=False)
    except Exception:
        return str(payload)


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n…[truncated; {len(text) - max_chars} more chars]"
