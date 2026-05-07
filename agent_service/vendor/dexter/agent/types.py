"""Agent event types and config — mirrors src/agent/types.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class AgentConfig:
    model: str = "gpt-4o-mini"
    max_iterations: int = 10
    channel: str = "cli"


# Event variants -------------------------------------------------------------


@dataclass
class ToolStartEvent:
    type: Literal["tool_start"]
    name: str
    args: dict[str, Any]
    call_id: str


@dataclass
class ToolEndEvent:
    type: Literal["tool_end"]
    name: str
    call_id: str
    result_preview: str
    error: str | None = None


@dataclass
class ThinkingEvent:
    type: Literal["thinking"]
    text: str


@dataclass
class AnswerStartEvent:
    type: Literal["answer_start"]


@dataclass
class AnswerChunkEvent:
    type: Literal["answer_chunk"]
    text: str


@dataclass
class DoneEvent:
    type: Literal["done"]
    answer: str
    iterations: int
    total_time_ms: int
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ErrorEvent:
    type: Literal["error"]
    message: str


AgentEvent = (
    ToolStartEvent
    | ToolEndEvent
    | ThinkingEvent
    | AnswerStartEvent
    | AnswerChunkEvent
    | DoneEvent
    | ErrorEvent
)
