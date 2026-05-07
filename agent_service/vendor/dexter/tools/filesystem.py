"""Filesystem tools — read_file, write_file (stub), edit_file (stub).

The TS original sandboxes file paths under the project working directory and
requires user approval for write/edit. The Python port currently only
implements ``read_file`` (read-only is safe). ``write_file`` and ``edit_file``
return a "not implemented" message so the agent can still see them in the tool
catalogue and fall back gracefully.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ..utils.format import format_tool_result, truncate


class ReadFileInput(BaseModel):
    path: str = Field(..., description="Path to read (absolute or workspace-relative).")
    max_chars: int = Field(50_000, description="Max chars to return (default 50,000).")


def _read_file(path: str, max_chars: int = 50_000) -> str:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return format_tool_result({"error": f"file not found: {p}"})
    if not p.is_file():
        return format_tool_result({"error": f"not a regular file: {p}"})
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return format_tool_result({"error": f"read failed: {e}"})
    return format_tool_result({"path": str(p), "content": truncate(text, max_chars)})


read_file_tool = StructuredTool.from_function(
    func=_read_file,
    name="read_file",
    description="Read a local file by path. Returns the file content as text.",
    args_schema=ReadFileInput,
)


class WriteFileInput(BaseModel):
    path: str = Field(..., description="Destination file path.")
    content: str = Field(..., description="Full content to write.")


def _write_file(path: str, content: str) -> str:  # noqa: ARG001
    return format_tool_result(
        {"error": "write_file is not implemented in the Python port (requires approval workflow)."}
    )


write_file_tool = StructuredTool.from_function(
    func=_write_file,
    name="write_file",
    description="(Stub) Create or overwrite a file. Currently disabled in the Python port.",
    args_schema=WriteFileInput,
)


class EditFileInput(BaseModel):
    path: str = Field(..., description="File path to edit.")
    old_text: str = Field(..., description="Exact text to find.")
    new_text: str = Field(..., description="Replacement text.")


def _edit_file(path: str, old_text: str, new_text: str) -> str:  # noqa: ARG001
    return format_tool_result(
        {"error": "edit_file is not implemented in the Python port (requires approval workflow)."}
    )


edit_file_tool = StructuredTool.from_function(
    func=_edit_file,
    name="edit_file",
    description="(Stub) Edit a file by string replacement. Currently disabled in the Python port.",
    args_schema=EditFileInput,
)
