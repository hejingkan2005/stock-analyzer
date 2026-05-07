"""Web search tools — Exa, Perplexity, Tavily.

The registry picks ONE based on which API key is set, in this preference order:
Exa → Perplexity → Tavily. Only the chosen tool is exposed as ``web_search``.
"""

from __future__ import annotations

import os

import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ..utils.format import format_tool_result

WEB_SEARCH_DESCRIPTION = (
    "Search the web for current information. Use for headlines, recent events, "
    "or facts not covered by the financial-data tools."
)


class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query.")
    max_results: int = Field(5, description="Maximum results (default 5).")


# ---------------------------------------------------------------------------
# Exa
# ---------------------------------------------------------------------------


def _exa_search(query: str, max_results: int = 5) -> str:
    api_key = os.environ.get("EXASEARCH_API_KEY", "")
    resp = httpx.post(
        "https://api.exa.ai/search",
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json={
            "query": query,
            "numResults": max_results,
            "contents": {"highlights": True},
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    cleaned = [
        {
            "title": r.get("title"),
            "url": r.get("url"),
            "highlights": r.get("highlights", []),
            "publishedDate": r.get("publishedDate"),
        }
        for r in data.get("results", [])
    ]
    return format_tool_result(cleaned)


exa_search = StructuredTool.from_function(
    func=_exa_search,
    name="web_search",
    description=WEB_SEARCH_DESCRIPTION,
    args_schema=WebSearchInput,
)


# ---------------------------------------------------------------------------
# Perplexity
# ---------------------------------------------------------------------------


def _perplexity_search(query: str, max_results: int = 5) -> str:  # noqa: ARG001
    api_key = os.environ.get("PERPLEXITY_API_KEY", "")
    resp = httpx.post(
        "https://api.perplexity.ai/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "sonar",
            "messages": [
                {"role": "system", "content": "Be concise. Cite sources."},
                {"role": "user", "content": query},
            ],
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    answer = data["choices"][0]["message"]["content"]
    citations = data.get("citations", [])
    return format_tool_result({"answer": answer, "citations": citations})


perplexity_search = StructuredTool.from_function(
    func=_perplexity_search,
    name="web_search",
    description=WEB_SEARCH_DESCRIPTION,
    args_schema=WebSearchInput,
)


# ---------------------------------------------------------------------------
# Tavily
# ---------------------------------------------------------------------------


def _tavily_search(query: str, max_results: int = 5) -> str:
    api_key = os.environ.get("TAVILY_API_KEY", "")
    resp = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": True,
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    cleaned = {
        "answer": data.get("answer"),
        "results": [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "content": r.get("content"),
            }
            for r in data.get("results", [])
        ],
    }
    return format_tool_result(cleaned)


tavily_search = StructuredTool.from_function(
    func=_tavily_search,
    name="web_search",
    description=WEB_SEARCH_DESCRIPTION,
    args_schema=WebSearchInput,
)


def get_web_search_tool() -> StructuredTool | None:
    """Return the web_search tool to register based on configured API keys."""
    if os.environ.get("EXASEARCH_API_KEY"):
        return exa_search
    if os.environ.get("PERPLEXITY_API_KEY"):
        return perplexity_search
    if os.environ.get("TAVILY_API_KEY"):
        return tavily_search
    return None
