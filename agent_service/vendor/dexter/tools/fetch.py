"""``web_fetch`` — download a URL, extract the readable article, return Markdown."""

from __future__ import annotations

import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ..utils.format import format_tool_result, truncate

WEB_FETCH_DESCRIPTION = (
    "Fetch a URL and return its main content as Markdown. Use when headlines "
    "from web_search or news tools aren't enough — e.g. to read article body, "
    "earnings transcripts, or SEC filing text."
)

DEFAULT_MAX_CHARS = 20_000

USER_AGENT = "Mozilla/5.0 (compatible; DexterPy/1.0; +https://github.com/virattt/dexter)"


class WebFetchInput(BaseModel):
    url: str = Field(..., description="Absolute URL to fetch.")
    max_chars: int = Field(DEFAULT_MAX_CHARS, description="Maximum characters to return.")


def _to_markdown(html: str) -> str:
    # Try Mozilla Readability first for clean article extraction.
    try:
        from readability import Document  # type: ignore
        from bs4 import BeautifulSoup
        import html2text

        doc = Document(html)
        title = doc.short_title()
        summary_html = doc.summary(html_partial=True)
        # Strip remaining tags noise
        soup = BeautifulSoup(summary_html, "lxml")
        h2t = html2text.HTML2Text()
        h2t.body_width = 0
        h2t.ignore_images = True
        body = h2t.handle(str(soup))
        return f"# {title}\n\n{body}".strip()
    except Exception:  # noqa: BLE001
        # Fallback: dumb text extraction
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            return soup.get_text(separator="\n").strip()
        except Exception:  # noqa: BLE001
            return html


def _web_fetch(url: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    try:
        resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=30.0, follow_redirects=True)
    except httpx.HTTPError as e:
        return format_tool_result({"error": f"network error: {e}", "url": url})
    if resp.status_code >= 400:
        return format_tool_result({"error": f"HTTP {resp.status_code}", "url": url})

    md = _to_markdown(resp.text)
    md = truncate(md, max_chars)
    return format_tool_result({"url": url, "content": md})


web_fetch_tool = StructuredTool.from_function(
    func=_web_fetch,
    name="web_fetch",
    description=WEB_FETCH_DESCRIPTION,
    args_schema=WebFetchInput,
)
