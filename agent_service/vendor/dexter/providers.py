"""Canonical provider registry — single source of truth for LLM provider metadata.

Mirrors src/providers.ts from the TypeScript original.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderDef:
    id: str
    display_name: str
    model_prefix: str  # "" means the default (OpenAI)
    api_key_env_var: str | None = None
    fast_model: str | None = None
    context_window: int = 128_000


PROVIDERS: list[ProviderDef] = [
    ProviderDef("openai", "OpenAI", "", "OPENAI_API_KEY", "gpt-4.1-mini", 1_047_576),
    ProviderDef("anthropic", "Anthropic", "claude-", "ANTHROPIC_API_KEY", "claude-haiku-4-5", 200_000),
    ProviderDef("google", "Google", "gemini-", "GOOGLE_API_KEY", "gemini-2.0-flash-exp", 1_000_000),
    ProviderDef("xai", "xAI", "grok-", "XAI_API_KEY", "grok-2-mini", 131_072),
    ProviderDef("moonshot", "Moonshot", "kimi-", "MOONSHOT_API_KEY", "kimi-k2-5", 131_072),
    ProviderDef("deepseek", "DeepSeek", "deepseek-", "DEEPSEEK_API_KEY", "deepseek-v4-flash", 1_000_000),
    ProviderDef("openrouter", "OpenRouter", "openrouter:", "OPENROUTER_API_KEY", "openrouter:openai/gpt-4o-mini", 128_000),
    ProviderDef("ollama", "Ollama", "ollama:", None, None, 128_000),
]

_DEFAULT = next(p for p in PROVIDERS if p.id == "openai")


def resolve_provider(model_name: str) -> ProviderDef:
    """Return the provider whose model_prefix matches the model name (default: OpenAI)."""
    for p in PROVIDERS:
        if p.model_prefix and model_name.startswith(p.model_prefix):
            return p
    return _DEFAULT


def get_provider_by_id(provider_id: str) -> ProviderDef | None:
    return next((p for p in PROVIDERS if p.id == provider_id), None)


def get_fast_model(model_name: str) -> str:
    """Return the provider's fast variant for lightweight tasks; falls back to model_name."""
    return resolve_provider(model_name).fast_model or model_name
