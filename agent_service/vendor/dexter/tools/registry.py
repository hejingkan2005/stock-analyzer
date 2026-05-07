"""Tool registry — mirrors src/tools/registry.ts.

Returns the list of LangChain ``StructuredTool`` instances that should be bound
to the LLM. Some tools are conditionally included based on which API keys are
configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .browser import BROWSER_DESCRIPTION, browser_tool
from .fetch import WEB_FETCH_DESCRIPTION, web_fetch_tool
from .filesystem import edit_file_tool, read_file_tool, write_file_tool
from .finance import ALL_FINANCE_TOOLS
from .search import WEB_SEARCH_DESCRIPTION, get_web_search_tool
from .skill import SKILL_TOOL_DESCRIPTION, skill_tool
from ..skills import discover_skills


@dataclass
class RegisteredTool:
    name: str
    tool: Any  # langchain StructuredTool
    description: str
    compact_description: str


def get_tool_registry() -> list[RegisteredTool]:
    tools: list[RegisteredTool] = []

    # All finance tools (flattened — no LLM router for v1)
    for t in ALL_FINANCE_TOOLS:
        tools.append(
            RegisteredTool(
                name=t.name,
                tool=t,
                description=t.description,
                compact_description=t.description,
            )
        )

    tools.append(
        RegisteredTool(
            name="web_fetch",
            tool=web_fetch_tool,
            description=WEB_FETCH_DESCRIPTION,
            compact_description="Fetch a URL and return main content as Markdown.",
        )
    )

    tools.append(
        RegisteredTool(
            name="browser",
            tool=browser_tool,
            description=BROWSER_DESCRIPTION,
            compact_description="(stub) Headless browser for JS-rendered pages.",
        )
    )

    tools.append(
        RegisteredTool(
            name="read_file",
            tool=read_file_tool,
            description=read_file_tool.description,
            compact_description="Read a local file.",
        )
    )
    tools.append(
        RegisteredTool(
            name="write_file",
            tool=write_file_tool,
            description=write_file_tool.description,
            compact_description="(stub) Create/overwrite a file.",
        )
    )
    tools.append(
        RegisteredTool(
            name="edit_file",
            tool=edit_file_tool,
            description=edit_file_tool.description,
            compact_description="(stub) Edit a file.",
        )
    )

    web_search = get_web_search_tool()
    if web_search is not None:
        tools.append(
            RegisteredTool(
                name="web_search",
                tool=web_search,
                description=WEB_SEARCH_DESCRIPTION,
                compact_description="Web search for current information.",
            )
        )

    if discover_skills():
        tools.append(
            RegisteredTool(
                name="skill",
                tool=skill_tool,
                description=SKILL_TOOL_DESCRIPTION,
                compact_description="Invoke a specialized skill workflow (DCF, X-research).",
            )
        )

    return tools


def get_tools() -> list:
    return [r.tool for r in get_tool_registry()]


def build_compact_tool_descriptions() -> str:
    lines: list[str] = []
    for r in get_tool_registry():
        lines.append(f"- **{r.name}**: {r.compact_description}")
    return "\n".join(lines)
