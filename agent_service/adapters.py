"""Pluggable agent adapters.

Each adapter exposes a single method ``run(messages, lang) -> str``. This keeps
the HTTP layer agnostic of the underlying agent so the backend can be swapped
later (dexter, a different LangGraph agent, a hosted API, etc.) without
changing the Dash UI or the FastAPI surface.
"""

from __future__ import annotations

import os
import re
from typing import Iterable, Protocol


ChatMessage = dict  # {"role": "user"|"assistant"|"system", "content": str}

_ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


class Agent(Protocol):
    name: str

    def run(self, messages: list[ChatMessage], lang: str) -> str: ...


def _last_user_text(messages: Iterable[ChatMessage]) -> str:
    for msg in reversed(list(messages)):
        if msg.get("role") == "user":
            return str(msg.get("content") or "")
    return ""


class NotConfiguredAgent:
    """Fallback used when no real backend is wired up or keys are missing."""

    name = "not-configured"

    def __init__(self, reason: str):
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
    """Adapter around the open-source `virattt/dexter` LangGraph agent.

    Dexter's Python implementation is no longer published from the repo root
    (the project moved to TypeScript). We vendor the legacy Python package
    from commit ``fa967cd`` under ``agent_service/vendor/dexter`` so we can
    import it directly. Source:
    https://github.com/virattt/dexter/tree/fa967cd008435ec213ba5c4fabc0c87a40b55442/legacy
    """

    name = "dexter"

    def __init__(self):
        self._agent_cls = None

    def _load(self):
        if self._agent_cls is not None:
            return
        # Make the vendored sources importable as the top-level ``dexter``
        # package (its internal imports use ``from dexter.xxx import ...``).
        import sys
        from pathlib import Path

        vendor_root = Path(__file__).resolve().parent / "vendor"
        if str(vendor_root) not in sys.path:
            sys.path.insert(0, str(vendor_root))

        try:
            from dexter.agent import Agent as DexterAgentCls  # type: ignore
        except Exception as exc:  # pragma: no cover - import-time failure
            raise RuntimeError(
                "Failed to import the vendored dexter package. Make sure the "
                "agent extras are installed (`uv sync --extra agent`). "
                f"Underlying error: {exc}"
            ) from exc

        # OpenAI-compatible providers (e.g. OpenRouter, Together, Groq) are
        # supported by routing dexter's ChatOpenAI through a custom base URL.
        # Activate when OPENAI_BASE_URL is set.
        base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
        if base_url:
            try:
                from langchain_openai import ChatOpenAI as _ChatOpenAI
                import dexter.model as _dexter_model  # type: ignore

                _orig = _ChatOpenAI

                def _patched_chat_openai(*args, **kwargs):  # type: ignore[no-untyped-def]
                    kwargs.setdefault("base_url", base_url)
                    # OpenRouter uses the same OPENAI_API_KEY var; nothing to do.
                    return _orig(*args, **kwargs)

                _dexter_model.ChatOpenAI = _patched_chat_openai  # type: ignore[attr-defined]
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(
                    f"Failed to configure custom OpenAI base URL: {exc}"
                ) from exc

        self._agent_cls = DexterAgentCls
        self._patch_dexter_writable_paths()

    @staticmethod
    def _patch_dexter_writable_paths() -> None:
        """Redirect dexter's on-disk caches to a writable directory.

        Dexter writes to ``./.dexter/settings.json`` and ``./.dexter/context/``
        relative to the process CWD. On Azure Functions / App Service the
        package directory is read-only, so we point both at a writable temp
        path (``DEXTER_HOME`` if set, otherwise ``$TMPDIR/dexter``).
        """
        import tempfile
        from pathlib import Path

        base_dir = Path(os.getenv("DEXTER_HOME") or os.path.join(tempfile.gettempdir(), "dexter"))
        try:
            base_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return  # if even tmp is unwritable, let dexter fail loudly later

        try:
            import dexter.utils.config as _cfg  # type: ignore
            import dexter.utils.context as _ctx  # type: ignore

            _cfg.SETTINGS_FILE = base_dir / "settings.json"

            _orig_init = _ctx.ContextManager.__init__

            def _patched_init(self, context_dir: str = str(base_dir / "context"), *args, **kwargs):  # type: ignore[no-untyped-def]
                # Force the context directory to live under our writable base
                # regardless of the caller-supplied path.
                _orig_init(self, context_dir=str(base_dir / "context"), *args, **kwargs)

            _ctx.ContextManager.__init__ = _patched_init  # type: ignore[assignment]
        except Exception:
            # If the internal layout changed, just leave defaults; the
            # original FileSystem error will surface in the user's reply.
            pass

    def run(self, messages: list[ChatMessage], lang: str) -> str:
        del lang  # dexter does not accept a language hint; set it in the query if needed.
        self._load()
        assert self._agent_cls is not None

        query = _last_user_text(messages)
        if not query:
            return ""

        # Dexter prints to stdout while it works. Capture stdout so server
        # logs stay clean and only the final answer is returned to the UI.
        import contextlib
        import io

        # DEXTER_MODEL overrides dexter's default ("gpt-4.1"). Required when
        # using OpenRouter, where models are namespaced like
        # "openai/gpt-4o-mini" or "anthropic/claude-3.5-sonnet".
        model_name = os.getenv("DEXTER_MODEL")
        # Step caps: dexter's defaults (20 / 5) can run for many minutes when
        # a query has no matching data (e.g. HK tickers in financial-datasets);
        # lower them to fail fast unless the operator opts back in.
        kwargs: dict = {}
        if model_name:
            kwargs["model"] = model_name
        try:
            kwargs["max_steps"] = int(os.getenv("DEXTER_MAX_STEPS", "8"))
            kwargs["max_steps_per_task"] = int(os.getenv("DEXTER_MAX_STEPS_PER_TASK", "3"))
        except ValueError:
            pass
        agent = self._agent_cls(**kwargs)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                answer = agent.run(query)
        except Exception as exc:
            raise RuntimeError(f"Dexter agent invocation failed: {exc}") from exc

        cleaned = str(answer or "").strip()
        if cleaned:
            return cleaned
        # Dexter sometimes returns an empty answer (e.g. all tool calls failed
        # because the data provider doesn't support the ticker). Do NOT fall
        # back to the captured stdout — it's CLI progress noise (spinners,
        # box-drawing characters, ANSI codes) that renders as garbage in the
        # chat bubble. Return a clean, actionable message instead.
        msg = (
            "Sorry, I couldn't produce an answer for that query. "
            "The financial-datasets backend mostly covers US-listed tickers, "
            "so questions about HK tickers (e.g. 0700.HK) often fail; try the "
            "US ADR instead (e.g. TCEHY for Tencent, BABA for Alibaba), or "
            "rephrase the question."
        )
        log_tail = "\n".join(
            _strip_ansi(line).rstrip()
            for line in buf.getvalue().splitlines()[-6:]
            if _strip_ansi(line).strip()
        )
        if log_tail:
            msg += f"\n\nLast agent activity:\n{log_tail}"
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
        Point dexter at an OpenAI-compatible provider such as OpenRouter,
        Together, or Groq. Example: https://openrouter.ai/api/v1
    DEXTER_MODEL (optional):
        Override dexter's default model name ("gpt-4.1"). Required with
        OpenRouter, e.g. "openai/gpt-4o-mini".
    """
    backend = (os.getenv("AGENT_BACKEND") or "dexter").strip().lower()

    if backend == "echo":
        return EchoAgent()

    if backend == "dexter":
        missing = [
            name
            for name in ("OPENAI_API_KEY", "FINANCIAL_DATASETS_API_KEY")
            if not os.getenv(name)
        ]
        if missing:
            return NotConfiguredAgent(
                f"Missing environment variables: {', '.join(missing)}"
            )
        return DexterAgent()
    return NotConfiguredAgent(f"Unknown AGENT_BACKEND={backend!r}")
