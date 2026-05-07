"""Per-query JSONL scratchpad of every tool call — mirrors src/agent/scratchpad.ts.

Each query gets a fresh file under ``.dexter/scratchpad/`` so that runs are
inspectable after the fact.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from ..utils.paths import scratchpad_dir


class Scratchpad:
    def __init__(self, query: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        suffix = secrets.token_hex(6)
        self.path: Path = scratchpad_dir() / f"{ts}_{suffix}.jsonl"
        self._fp = self.path.open("a", encoding="utf-8")
        self._write({"type": "init", "query": query, "ts": datetime.now().isoformat()})
        self.entries: list[dict[str, Any]] = []

    def _write(self, entry: dict[str, Any]) -> None:
        self._fp.write(json.dumps(entry, default=str, ensure_ascii=False) + "\n")
        self._fp.flush()

    def log_tool_result(self, name: str, args: dict, result: Any, error: str | None = None) -> None:
        entry = {
            "type": "tool_result",
            "ts": datetime.now().isoformat(),
            "tool": name,
            "args": args,
            "result": result if isinstance(result, (str, int, float, bool, type(None))) else str(result)[:5000],
            "error": error,
        }
        self.entries.append(entry)
        self._write(entry)

    def log_thinking(self, text: str) -> None:
        entry = {"type": "thinking", "ts": datetime.now().isoformat(), "text": text}
        self.entries.append(entry)
        self._write(entry)

    def log_answer(self, text: str) -> None:
        entry = {"type": "answer", "ts": datetime.now().isoformat(), "text": text}
        self.entries.append(entry)
        self._write(entry)

    def close(self) -> None:
        try:
            self._fp.close()
        except OSError:
            pass

    def __del__(self) -> None:
        self.close()
