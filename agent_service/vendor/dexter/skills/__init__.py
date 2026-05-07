"""Skill discovery & loading — mirrors src/skills/loader.ts and registry.ts.

A "skill" is a SKILL.md file with YAML frontmatter (``name``, ``description``)
and a Markdown body containing the workflow instructions. Skills are exposed to
the LLM through the ``skill`` tool: the agent picks one by name and gets back
the full Markdown body.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import frontmatter

SKILLS_ROOT = Path(__file__).parent


@dataclass
class Skill:
    name: str
    description: str
    body: str
    path: Path


_skills_cache: list[Skill] | None = None


def discover_skills() -> list[Skill]:
    """Walk this package looking for SKILL.md files. Cached after first call."""
    global _skills_cache
    if _skills_cache is not None:
        return _skills_cache

    skills: list[Skill] = []
    for md in SKILLS_ROOT.rglob("SKILL.md"):
        try:
            post = frontmatter.load(md)
        except Exception:  # noqa: BLE001
            continue
        name = (post.metadata.get("name") or md.parent.name).strip()
        description = str(post.metadata.get("description") or "").strip()
        skills.append(Skill(name=name, description=description, body=post.content, path=md))

    _skills_cache = sorted(skills, key=lambda s: s.name)
    return _skills_cache


def get_skill(name: str) -> Skill | None:
    return next((s for s in discover_skills() if s.name == name), None)


def build_skill_metadata_section() -> str:
    """Build the bullet list of skill names + descriptions for the system prompt."""
    skills = discover_skills()
    if not skills:
        return ""
    lines: list[str] = []
    for s in skills:
        lines.append(f"- **{s.name}**: {s.description}")
    return "\n".join(lines)
