"""Rich + Typer CLI — entry point ``dexter``.

Mirrors the interactive loop of src/cli.tsx and src/index.tsx (without the
React-based Ink rendering). Slash commands provide model switching, history
management, and basic settings.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

import typer
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from .agent import Agent, AgentConfig
from .agent.types import (
    AnswerStartEvent,
    DoneEvent,
    ErrorEvent,
    ThinkingEvent,
    ToolEndEvent,
    ToolStartEvent,
)
from .llm import DEFAULT_MODEL
from .providers import resolve_provider
from .utils.config import get_setting, set_setting
from .utils.env import load_env

app = typer.Typer(
    add_completion=False,
    help="Dexter — autonomous AI agent for deep financial research (Python port).",
    rich_markup_mode="rich",
)

console = Console()

BANNER = """[bold cyan]
████████▄     ▄████████ ▀████    ▐████▀     ███        ▄████████    ▄████████
███   ▀███   ███    ███   ███▌   ████▀   ▀█████████▄   ███    ███   ███    ███
███    ███   ███    █▀     ███  ▐███       ▀███▀▀██   ███    █▀    ███    ███
███    ███  ▄███▄▄▄        ▀███▄███▀        ███   ▀  ▄███▄▄▄      ▄███▄▄▄▄██▀
███    ███ ▀▀███▀▀▀        ████▀██▄         ███     ▀▀███▀▀▀     ▀▀███▀▀▀▀▀
███    ███   ███    █▄    ▐███  ▀███        ███       ███    █▄  ▀███████████
███   ▄███   ███    ███  ▄███     ███▄      ███       ███    ███   ███    ███
████████▀    ██████████ ████       ███▄    ▄████▀     ██████████   ███    ███
[/bold cyan]"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_model(cli_arg: Optional[str]) -> str:
    if cli_arg:
        return cli_arg
    return get_setting("model", DEFAULT_MODEL)


def _print_intro(model: str) -> None:
    console.print(BANNER)
    provider = resolve_provider(model)
    console.print(
        Panel.fit(
            f"[bold]Model:[/bold] {model}  ·  [bold]Provider:[/bold] {provider.display_name}\n"
            "[dim]Ask anything. Slash commands: /help /model /clear /history /scratchpad /quit[/dim]",
            border_style="cyan",
        )
    )


async def _run_query(agent: Agent, query: str, history: list[BaseMessage]) -> tuple[str, list[dict]]:
    """Stream events to the console; return (final_answer, tool_calls)."""
    spinner_msg = "[cyan]thinking…[/cyan]"
    answer = ""
    tool_calls: list[dict] = []

    with console.status(spinner_msg, spinner="dots"):
        async for ev in agent.run(query, history):
            if isinstance(ev, ToolStartEvent):
                console.print(f"  [yellow]→[/yellow] [bold]{ev.name}[/bold] [dim]{_short_args(ev.args)}[/dim]")
            elif isinstance(ev, ToolEndEvent):
                if ev.error:
                    console.print(f"    [red]✗ {ev.name}: {ev.error}[/red]")
                else:
                    console.print(f"    [green]✓[/green] [dim]{ev.result_preview}[/dim]")
            elif isinstance(ev, ThinkingEvent):
                if ev.text.strip():
                    console.print(f"  [dim italic]{ev.text.strip()}[/dim italic]")
            elif isinstance(ev, AnswerStartEvent):
                pass
            elif isinstance(ev, DoneEvent):
                answer = ev.answer
                tool_calls = ev.tool_calls
            elif isinstance(ev, ErrorEvent):
                console.print(f"[bold red]Error:[/bold red] {ev.message}")

    if answer:
        console.print()
        console.print(Panel(Markdown(answer), title="Dexter", border_style="green"))
    return answer, tool_calls


def _short_args(args: dict) -> str:
    if not args:
        return ""
    parts = [f"{k}={v!r}" for k, v in list(args.items())[:3]]
    s = ", ".join(parts)
    return s[:100] + ("…" if len(s) > 100 else "")


# ---------------------------------------------------------------------------
# Slash command handler
# ---------------------------------------------------------------------------


def _handle_slash(cmd: str, history: list[BaseMessage], state: dict) -> bool:
    """Return True to continue the loop; False to exit."""
    parts = cmd.strip().split(maxsplit=1)
    head = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if head in ("/quit", "/exit", "/q"):
        console.print("[dim]bye[/dim]")
        return False
    if head == "/help":
        console.print(
            Panel(
                "[bold]/help[/bold]            show this help\n"
                "[bold]/model[/bold] [name]    show or switch model (e.g. /model claude-haiku-4-5)\n"
                "[bold]/clear[/bold]           clear conversation history\n"
                "[bold]/history[/bold]         show recent messages\n"
                "[bold]/scratchpad[/bold]      show last query's tool calls\n"
                "[bold]/quit[/bold]            exit",
                title="Slash commands",
                border_style="cyan",
            )
        )
        return True
    if head == "/model":
        if not arg:
            console.print(f"[bold]Current model:[/bold] {state['model']}")
        else:
            state["model"] = arg.strip()
            set_setting("model", state["model"])
            state["agent"] = Agent(AgentConfig(model=state["model"]))
            console.print(f"[green]switched to[/green] [bold]{state['model']}[/bold]")
        return True
    if head == "/clear":
        history.clear()
        console.print("[dim]history cleared[/dim]")
        return True
    if head == "/history":
        if not history:
            console.print("[dim](empty)[/dim]")
        for m in history[-10:]:
            role = "user" if isinstance(m, HumanMessage) else "dexter" if isinstance(m, AIMessage) else type(m).__name__
            console.print(f"[bold]{role}[/bold]: {Text(_coerce(m.content))[:200]}")
        return True
    if head == "/scratchpad":
        last = state.get("last_tool_calls", [])
        if not last:
            console.print("[dim]no tool calls yet[/dim]")
        for i, tc in enumerate(last, 1):
            console.print(f"[bold]{i}.[/bold] [yellow]{tc['name']}[/yellow] {tc['args']}")
            console.print(f"   [dim]{tc['result_preview']}[/dim]")
        return True

    console.print(f"[red]unknown command:[/red] {head}  (try /help)")
    return True


def _coerce(content) -> str:
    return content if isinstance(content, str) else str(content)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def chat(
    query: Optional[list[str]] = typer.Argument(None, help="If provided, run a single query and exit."),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name (e.g. gpt-4o, claude-haiku-4-5, ollama:llama3.1)."),
) -> None:
    """Start an interactive chat, or run a single query if one is provided."""
    load_env()
    chosen_model = _resolve_model(model)
    agent = Agent(AgentConfig(model=chosen_model))

    if query:
        q = " ".join(query)
        asyncio.run(_single_shot(agent, q))
        return

    _print_intro(chosen_model)
    asyncio.run(_repl(agent, chosen_model))


async def _single_shot(agent: Agent, query: str) -> None:
    await _run_query(agent, query, history=[])


async def _repl(agent: Agent, model: str) -> None:
    history: list[BaseMessage] = []
    state: dict = {"model": model, "agent": agent, "last_tool_calls": []}

    while True:
        try:
            line = Prompt.ask("[bold cyan]›[/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not line:
            continue
        if line.startswith("/"):
            if not _handle_slash(line, history, state):
                break
            continue

        agent = state["agent"]  # may have been swapped by /model
        try:
            answer, tool_calls = await _run_query(agent, line, history)
        except KeyboardInterrupt:
            console.print("[yellow]interrupted[/yellow]")
            continue

        if answer:
            history.append(HumanMessage(line))
            history.append(AIMessage(answer))
            state["last_tool_calls"] = tool_calls


@app.command()
def version() -> None:
    """Print the package version."""
    from . import __version__

    console.print(__version__)


def main() -> None:  # entry point compatibility
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
