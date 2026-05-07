"""Multi-provider LLM factory + retry — mirrors src/model/llm.ts.

The factory uses ``langchain-*`` packages, which are imported lazily so users
can install just the provider they need.
"""

from __future__ import annotations

import os
import time
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage

from .providers import resolve_provider
from .utils.errors import classify_error, is_non_retryable_error
from .utils.logger import logger

DEFAULT_MODEL = "gpt-4o-mini"


def _require_api_key(env_var: str) -> str:
    val = os.environ.get(env_var)
    if not val:
        raise RuntimeError(f"[LLM] {env_var} not found in environment variables")
    return val


def get_chat_model(model_name: str = DEFAULT_MODEL, *, streaming: bool = False, temperature: float | None = None) -> BaseChatModel:
    """Return a configured LangChain chat model for ``model_name``.

    Provider is resolved by prefix; falls back to OpenAI.
    """
    provider = resolve_provider(model_name)
    pid = provider.id
    common: dict[str, Any] = {"model": model_name, "streaming": streaming}
    if temperature is not None:
        common["temperature"] = temperature

    if pid == "openai":
        from langchain_openai import ChatOpenAI

        # Optional override: point the default OpenAI provider at any
        # OpenAI-compatible endpoint (e.g. OpenRouter, LiteLLM, vLLM)
        # by setting OPENAI_BASE_URL in .env.
        base_url = os.environ.get("OPENAI_BASE_URL")
        kwargs: dict[str, Any] = {"api_key": _require_api_key("OPENAI_API_KEY"), **common}
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOpenAI(**kwargs)

    if pid == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Install 'langchain-anthropic' to use Anthropic models") from e
        return ChatAnthropic(api_key=_require_api_key("ANTHROPIC_API_KEY"), **common)

    if pid == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Install 'langchain-google-genai' to use Gemini models") from e
        return ChatGoogleGenerativeAI(google_api_key=_require_api_key("GOOGLE_API_KEY"), **common)

    if pid == "xai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=_require_api_key("XAI_API_KEY"),
            base_url="https://api.x.ai/v1",
            **common,
        )

    if pid == "openrouter":
        from langchain_openai import ChatOpenAI

        common["model"] = model_name.removeprefix("openrouter:")
        return ChatOpenAI(
            api_key=_require_api_key("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            **common,
        )

    if pid == "moonshot":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=_require_api_key("MOONSHOT_API_KEY"),
            base_url="https://api.moonshot.cn/v1",
            **common,
        )

    if pid == "deepseek":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=_require_api_key("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
            **common,
        )

    if pid == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Install 'langchain-ollama' to use Ollama models") from e
        common["model"] = model_name.removeprefix("ollama:")
        if base_url := os.environ.get("OLLAMA_BASE_URL"):
            common["base_url"] = base_url
        return ChatOllama(**common)

    # Fallback: OpenAI
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(api_key=_require_api_key("OPENAI_API_KEY"), **common)


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------


def _retry(fn, provider_id: str, max_attempts: int = 3):
    last_err: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            kind = classify_error(msg)
            logger.error("[%s API] %s error (attempt %d/%d): %s", provider_id, kind, attempt + 1, max_attempts, msg)
            if is_non_retryable_error(msg):
                raise
            last_err = e
            if attempt == max_attempts - 1:
                break
            time.sleep(0.5 * (2 ** attempt))
    assert last_err is not None
    raise last_err


# ---------------------------------------------------------------------------
# Convenience callers
# ---------------------------------------------------------------------------


def call_llm_with_messages(
    messages: list[BaseMessage],
    model: str = DEFAULT_MODEL,
    *,
    tools: list | None = None,
    temperature: float | None = None,
):
    """Single (non-streaming) call. Returns the AIMessage."""
    provider = resolve_provider(model)
    chat = get_chat_model(model, streaming=False, temperature=temperature)
    if tools:
        chat = chat.bind_tools(tools)
    return _retry(lambda: chat.invoke(messages), provider.id)


def call_llm(
    user_prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    system_prompt: str | None = None,
    tools: list | None = None,
    temperature: float | None = None,
):
    from langchain_core.messages import HumanMessage

    msgs: list[BaseMessage] = []
    if system_prompt:
        msgs.append(SystemMessage(system_prompt))
    msgs.append(HumanMessage(user_prompt))
    return call_llm_with_messages(msgs, model, tools=tools, temperature=temperature)
