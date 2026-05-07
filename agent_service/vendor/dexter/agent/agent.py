"""Core agent loop — mirrors src/agent/agent.ts.

Iterative tool-calling loop:
  1. Build a system prompt + history.
  2. Call the LLM (with tools bound).
  3. If it returned tool calls → execute (read-only ones in parallel), append
     results, loop.
  4. If it returned plain text → that's the final answer; loop ends.
  5. Hard cap on iterations.

Yields ``AgentEvent`` objects so the CLI can render progress in real time.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool

from ..llm import call_llm_with_messages
from ..tools.registry import get_tool_registry
from .prompts import FINAL_ANSWER_PROMPT, build_system_prompt
from .scratchpad import Scratchpad
from .types import (
    AgentConfig,
    AgentEvent,
    AnswerStartEvent,
    DoneEvent,
    ErrorEvent,
    ThinkingEvent,
    ToolEndEvent,
    ToolStartEvent,
)

DEFAULT_MAX_ITERATIONS = 10

# Tools that are NOT safe to run concurrently (they mutate state or need approval).
NON_CONCURRENT_TOOLS = {"write_file", "edit_file", "skill"}


class Agent:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.registry = get_tool_registry()
        self.tools: list[StructuredTool] = [r.tool for r in self.registry]
        self.tool_map: dict[str, StructuredTool] = {r.name: r.tool for r in self.registry}
        self.system_prompt = build_system_prompt()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, query: str, history: list[BaseMessage] | None = None) -> AsyncIterator[AgentEvent]:
        """Run the agent on ``query`` and yield events as it progresses."""
        start = time.time()
        scratchpad = Scratchpad(query)
        messages: list[BaseMessage] = [SystemMessage(self.system_prompt)]
        if history:
            messages.extend(history)
        messages.append(HumanMessage(query))

        tool_calls_log: list[dict[str, Any]] = []
        final_answer = ""

        try:
            for iteration in range(self.config.max_iterations):
                ai_msg: AIMessage = await asyncio.to_thread(
                    call_llm_with_messages,
                    messages,
                    self.config.model,
                    tools=self.tools,
                )

                # Tool calls present → execute them
                tcalls = getattr(ai_msg, "tool_calls", None) or []
                if tcalls:
                    if ai_msg.content:
                        text = _coerce_text(ai_msg.content)
                        if text.strip():
                            scratchpad.log_thinking(text)
                            yield ThinkingEvent(type="thinking", text=text)

                    messages.append(ai_msg)

                    tool_outputs = await self._execute_tool_calls(tcalls, scratchpad, tool_calls_log)
                    for out in tool_outputs:
                        yield out["start_event"]
                        yield out["end_event"]
                        messages.append(out["tool_message"])
                    continue  # next iteration

                # No tool calls → final answer
                final_answer = _coerce_text(ai_msg.content)
                scratchpad.log_answer(final_answer)
                yield AnswerStartEvent(type="answer_start")
                break
            else:
                # Hit max iterations: ask for a final answer with no tools bound.
                final_answer = await self._force_final_answer(messages, scratchpad)
                yield AnswerStartEvent(type="answer_start")

            yield DoneEvent(
                type="done",
                answer=final_answer,
                iterations=iteration + 1,
                total_time_ms=int((time.time() - start) * 1000),
                tool_calls=tool_calls_log,
            )
        except Exception as e:  # noqa: BLE001
            yield ErrorEvent(type="error", message=str(e))
        finally:
            scratchpad.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _execute_tool_calls(
        self,
        tcalls: list[dict[str, Any]],
        scratchpad: Scratchpad,
        log: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Run a batch of tool calls. Concurrent-safe ones go in parallel."""

        async def run_one(tc: dict[str, Any]) -> dict[str, Any]:
            name = tc["name"]
            args = tc.get("args") or {}
            call_id = tc.get("id") or ""
            tool = self.tool_map.get(name)
            start_event = ToolStartEvent(type="tool_start", name=name, args=args, call_id=call_id)

            if tool is None:
                err = f"unknown tool: {name}"
                scratchpad.log_tool_result(name, args, None, error=err)
                return {
                    "start_event": start_event,
                    "end_event": ToolEndEvent(type="tool_end", name=name, call_id=call_id, result_preview="", error=err),
                    "tool_message": ToolMessage(content=err, tool_call_id=call_id),
                }
            try:
                # StructuredTool.ainvoke accepts the args dict directly.
                result = await tool.ainvoke(args)
                result_text = result if isinstance(result, str) else json.dumps(result, default=str)
                scratchpad.log_tool_result(name, args, result_text)
                log.append({"name": name, "args": args, "result_preview": _preview(result_text)})
                return {
                    "start_event": start_event,
                    "end_event": ToolEndEvent(
                        type="tool_end",
                        name=name,
                        call_id=call_id,
                        result_preview=_preview(result_text),
                    ),
                    "tool_message": ToolMessage(content=result_text, tool_call_id=call_id),
                }
            except Exception as e:  # noqa: BLE001
                err = str(e)
                scratchpad.log_tool_result(name, args, None, error=err)
                return {
                    "start_event": start_event,
                    "end_event": ToolEndEvent(type="tool_end", name=name, call_id=call_id, result_preview="", error=err),
                    "tool_message": ToolMessage(content=f"ERROR: {err}", tool_call_id=call_id),
                }

        # Split into concurrent vs sequential
        concurrent: list[asyncio.Task] = []
        sequential: list[dict[str, Any]] = []
        for tc in tcalls:
            if tc["name"] in NON_CONCURRENT_TOOLS:
                sequential.append(tc)
            else:
                concurrent.append(asyncio.create_task(run_one(tc)))

        results: list[dict[str, Any]] = []
        if concurrent:
            results.extend(await asyncio.gather(*concurrent))
        for tc in sequential:
            results.append(await run_one(tc))
        return results

    async def _force_final_answer(self, messages: list[BaseMessage], scratchpad: Scratchpad) -> str:
        msgs = list(messages) + [HumanMessage(FINAL_ANSWER_PROMPT)]
        ai = await asyncio.to_thread(call_llm_with_messages, msgs, self.config.model)
        text = _coerce_text(ai.content)
        scratchpad.log_answer(text)
        return text


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------


def _coerce_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # LangChain message content can be a list of blocks
        parts: list[str] = []
        for blk in content:
            if isinstance(blk, str):
                parts.append(blk)
            elif isinstance(blk, dict):
                t = blk.get("text") or blk.get("content")
                if t:
                    parts.append(str(t))
        return "".join(parts)
    return str(content) if content is not None else ""


def _preview(text: str, n: int = 200) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= n else text[:n] + "…"
