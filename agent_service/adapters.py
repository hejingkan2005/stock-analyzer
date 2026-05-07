"""Pluggable agent adapters.

Each adapter exposes a single method ``run(messages, lang) -> str``. This keeps
the HTTP layer agnostic of the underlying agent so the backend can be swapped
later without changing the Dash UI or the FastAPI surface.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Protocol


ChatMessage = dict  # {"role": "user"|"assistant"|"system", "content": str}

_ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


class Agent(Protocol):
    name: str

    def run(self, messages: list[ChatMessage], lang: str) -> str: ...


class NotConfiguredAgent:
    """Fallback used when no real backend is wired up or keys are missing."""

    name = "not-configured"

    def __init__(self, reason: str) -> None:
        self._reason = reason

    def run(self, messages: list[ChatMessage], lang: str) -> str:
        del messages  # not used; reply is fixed
        if lang == "zh":
            return (
                "聊天助手尚未配置。\n"
                f"原因: {self._reason}\n"
                "请在 agent_service 的环境变量中设置 OPENAI_API_KEY 与 "
                "FINANCIAL_DATASETS_API_KEY，并安装相应的后端依赖后重启服务。"
            )
        return (
            "Chat assistant is not configured.\n"
            f"Reason: {self._reason}\n"
            "Set OPENAI_API_KEY and FINANCIAL_DATASETS_API_KEY in the "
            "agent_service environment, install the backend dependencies, "
            "then restart the service."
        )


class DexterAgent:
    """Adapter around the open-source `virattt/dexter-py` financial agent.

    We vendor the package under ``agent_service/vendor/dexter`` so it can be
    imported without an extra `uv add`. The agent exposes an async iterator
    of ``AgentEvent`` objects; we drive it to completion and return the
    final ``DoneEvent.answer``.
    """

    name = "dexter"

    def __init__(self) -> None:
        self._loaded = False
        self._Agent = None  # type: ignore[assignment]
        self._AgentConfig = None  # type: ignore[assignment]
        self._DoneEvent = None  # type: ignore[assignment]
        self._ErrorEvent = None  # type: ignore[assignment]

    def _load(self) -> None:
        if self._loaded:
            return

        # 1. Make the vendored sources importable as the top-level ``dexter``
        #    package (its internal imports use ``from dexter.xxx import ...``).
        vendor_root = Path(__file__).resolve().parent / "vendor"
        if str(vendor_root) not in sys.path:
            sys.path.insert(0, str(vendor_root))

        # 2. Force DEXTER_HOME to a writable directory before any dexter
        #    submodule touches the filesystem. Azure Functions has a
        #    read-only package dir; the user's $HOME may be writable but
        #    $TMPDIR is the safest universal choice.
        if not os.environ.get("DEXTER_HOME"):
            os.environ["DEXTER_HOME"] = os.path.join(tempfile.gettempdir(), "dexter")

        try:
            from dexter.agent import (  # type: ignore
                Agent as DexterAgentCls,
                AgentConfig,
                DoneEvent,
                ErrorEvent,
            )
        except Exception as exc:  # pragma: no cover - import-time failure
            raise RuntimeError(
                "Failed to import the vendored dexter package. Make sure the "
                "agent extras are installed (`uv sync --extra agent`). "
                f"Underlying error: {exc}"
            ) from exc

        self._Agent = DexterAgentCls
        self._AgentConfig = AgentConfig
        self._DoneEvent = DoneEvent
        self._ErrorEvent = ErrorEvent
        self._loaded = True

    def run(self, messages: list[ChatMessage], lang: str) -> str:
        del lang  # dexter does not accept a language hint; set it in the query if needed.
        self._load()
        assert self._Agent is not None and self._AgentConfig is not None

        query = _last_user_text(messages)
        if not query:
            return ""

        # The new dexter is multi-provider. Three ways to point at OpenRouter:
        #   1. DEXTER_MODEL=openrouter:openai/gpt-4o-mini   + OPENROUTER_API_KEY
        #   2. DEXTER_MODEL=gpt-4o-mini + OPENAI_API_KEY=<openrouter-key>
        #      + OPENAI_BASE_URL=https://openrouter.ai/api/v1
        # Default model name kept the same as upstream ("gpt-4o-mini").
        model = os.getenv("DEXTER_MODEL", "gpt-4o-mini")
        try:
            max_iters = int(os.getenv("DEXTER_MAX_STEPS", "10"))
        except ValueError:
            max_iters = 10

        cfg = self._AgentConfig(model=model, max_iterations=max_iters)
        agent = self._Agent(cfg)

        async def _drive() -> tuple[str, str | None]:
            answer = ""
            error = None
            async for event in agent.run(query):
                if isinstance(event, self._DoneEvent):
                    answer = event.answer or ""
                elif isinstance(event, self._ErrorEvent):
                    error = event.message
            return answer, error

        try:
            answer, error = asyncio.run(_drive())
        except Exception as exc:
            raise RuntimeError(f"Dexter agent invocation failed: {exc}") from exc

        cleaned = _strip_ansi(str(answer or "")).strip()
        if cleaned:
            return cleaned

        # Empty answer: provide a friendly fallback so the chat bubble shows
        # something actionable instead of a blank message.
        msg = (
            "Sorry, I couldn't produce an answer for that query. "
            "The financial-datasets backend mostly covers US-listed tickers, "
            "so questions about HK tickers (e.g. 0700.HK) often fail; try the "
            "US ADR instead (e.g. TCEHY for Tencent, BABA for Alibaba), or "
            "rephrase the question."
        )
        if error:
            msg += f"\n\nLast error: {error}"
        return msg


class EchoAgent:
    """Trivial backend useful for UI development without any keys."""

    name = "echo"

    def run(self, messages: list[ChatMessage], lang: str) -> str:
        text = _last_user_text(messages)
        if lang == "zh":
            return f"[echo] 你说: {text}"
        return f"[echo] You said: {text}"


def build_agent() -> Agent:
    """Pick an adapter based on environment variables.

    AGENT_BACKEND:
        - "dexter"  (default) -> DexterAgent, requires the keys below
        - "echo"              -> EchoAgent (no keys needed; useful for dev)
    OPENAI_API_KEY, FINANCIAL_DATASETS_API_KEY:
        Required for the dexter backend. If missing we return a
        NotConfiguredAgent that explains how to fix it.
    OPENAI_BASE_URL (optional):
        Point the OpenAI provider at any OpenAI-compatible endpoint
        (e.g. https://openrouter.ai/api/v1).
    DEXTER_MODEL (optional):
        Model id passed to the agent. Default: gpt-4o-mini.
        Use ``openrouter:<provider>/<model>`` to route via OpenRouter.
    """
    backend = (os.getenv("AGENT_BACKEND") or "dexter").lower()
    if backend == "echo":
        return EchoAgent()
    if backend == "dexter":
        # The new dexter is multi-provider, so the required key depends on
        # which model the user picked. We only hard-require an OpenAI-style
        # key by default and the financial datasets key (always needed).
        missing = []
        if not (os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")):
            missing.append("OPENAI_API_KEY (or OPENROUTER_API_KEY)")
        if not os.getenv("FINANCIAL_DATASETS_API_KEY"):
            missing.append("FINANCIAL_DATASETS_API_KEY")
        if missing:
            return NotConfiguredAgent(
                f"Missing environment variables: {', '.join(missing)}"
            )
        return DexterAgent()
    return NotConfiguredAgent(f"Unknown AGENT_BACKEND={backend!r}")


def _last_user_text(messages: Iterable[ChatMessage]) -> str:
    for msg in reversed(list(messages)):
        if msg.get("role") == "user":
            return str(msg.get("content") or "").strip()
    return ""
