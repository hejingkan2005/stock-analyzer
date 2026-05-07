"""Stub Playwright browser tool. Real implementation is left as future work."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ..utils.format import format_tool_result

BROWSER_DESCRIPTION = (
    "Open a JavaScript-rendered page in a real browser, take a snapshot, and "
    "interact with it. Currently a stub in the Python port — install Playwright "
    "and implement to enable."
)


class BrowserInput(BaseModel):
    action: str = Field(..., description="One of: navigate, snapshot, act, read, close.")
    url: str | None = Field(None, description="URL for 'navigate'.")
    selector: str | None = Field(None, description="CSS selector for 'act'.")
    text: str | None = Field(None, description="Text to type for 'act'.")


def _browser(**kwargs) -> str:  # noqa: ARG001
    return format_tool_result(
        {
            "error": (
                "browser tool is not implemented in the Python port. "
                "Install playwright (`pip install dexter-py[browser]`) and implement."
            )
        }
    )


browser_tool = StructuredTool.from_function(
    func=_browser,
    name="browser",
    description=BROWSER_DESCRIPTION,
    args_schema=BrowserInput,
)
