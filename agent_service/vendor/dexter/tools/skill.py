"""``skill`` tool — invokes a SKILL.md workflow by name."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ..skills import discover_skills, get_skill
from ..utils.format import format_tool_result

SKILL_TOOL_DESCRIPTION = (
    "Invoke a specialized skill workflow by name. Returns the workflow's "
    "instructions which you should then follow step-by-step. Each skill should "
    "be invoked at most once per query."
)


class SkillInput(BaseModel):
    name: str = Field(..., description="Skill name (one of the available skills listed in the system prompt).")


def _skill(name: str) -> str:
    s = get_skill(name)
    if not s:
        available = ", ".join(x.name for x in discover_skills()) or "(none)"
        return format_tool_result({"error": f"unknown skill: {name}. Available: {available}"})
    # Include a relative path hint so the LLM can read sibling files via read_file
    extras_dir = s.path.parent
    return format_tool_result({
        "name": s.name,
        "instructions": s.body,
        "skill_dir": str(extras_dir),
    })


skill_tool = StructuredTool.from_function(
    func=_skill,
    name="skill",
    description=SKILL_TOOL_DESCRIPTION,
    args_schema=SkillInput,
)
