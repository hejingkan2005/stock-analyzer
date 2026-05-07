"""Exa.ai web search tool for dexter.

Uses the public Exa REST API (https://docs.exa.ai/reference/search). Requires
``EXA_API_KEY`` to be set in the environment. Returns a list of
:class:`SearchResult` objects so it is a drop-in for the previous Google
News tool.
"""

from __future__ import annotations

import os
from datetime import datetime

import requests
from langchain.tools import tool
from pydantic import BaseModel, Field

from dexter.tools.search.models import SearchResult

_EXA_ENDPOINT = "https://api.exa.ai/search"


class SearchExaInput(BaseModel):
    query: str = Field(description="The search query, e.g. 'Apple earnings Q3 2025'.")
    max_results: int = Field(default=5, description="Maximum number of results to return.")


def _parse_published_date(raw) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


@tool(args_schema=SearchExaInput)
def search_exa(query: str, max_results: int = 5) -> list[SearchResult]:
    """
    Search the web with Exa.ai for articles, news, or pages matching a query.
    Use this for recent news, current events, or information about specific
    topics that require up-to-date web data.
    """
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return []

    payload = {
        "query": query,
        "numResults": int(max_results),
        "type": "auto",
        "category": "news",
    }
    try:
        response = requests.post(
            _EXA_ENDPOINT,
            json=payload,
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            timeout=15,
        )
    except requests.RequestException:
        return []

    if response.status_code != 200:
        return []

    try:
        data = response.json()
    except ValueError:
        return []

    results: list[SearchResult] = []
    for item in (data.get("results") or [])[:max_results]:
        url = item.get("url")
        if not url:
            continue
        results.append(
            SearchResult(
                title=item.get("title") or url,
                url=url,
                published_date=_parse_published_date(item.get("publishedDate")),
            )
        )
    return results
