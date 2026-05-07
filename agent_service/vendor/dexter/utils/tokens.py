"""Token estimation helpers (tiktoken if installed, else heuristic)."""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    try:  # pragma: no cover
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Heuristic: ~4 chars per token
        return max(1, len(text) // 4)


def get_auto_compact_threshold(context_window: int) -> int:
    """Trigger compaction when we've used ~70% of the model's context window."""
    return int(context_window * 0.70)
