# Chat Agent Microservice

A small FastAPI service that exposes a chat agent over HTTP. The Dash app's
"Chat Assistant" tab calls this service. The agent backend is pluggable so you
can later replace **dexter** with a different agent without touching the UI.

## Backends

| `AGENT_BACKEND` | Description                                  | Keys required |
| --------------- | -------------------------------------------- | ------------- |
| `dexter` (default) | [virattt/dexter](https://github.com/virattt/dexter) financial agent | `OPENAI_API_KEY`, `FINANCIAL_DATASETS_API_KEY` |
| `echo`          | Echoes the user message; no LLM calls.       | none          |

If the required keys are missing, the service still starts and the `/chat`
endpoint returns a clear "not configured" message so the UI keeps working.

## Install

The service ships as an optional dependency group of the main project:

```powershell
uv sync --extra agent
```

The dexter Python sources are **vendored** under `agent_service/vendor/dexter`
(from
[virattt/dexter @ fa967cd / legacy](https://github.com/virattt/dexter/tree/fa967cd008435ec213ba5c4fabc0c87a40b55442/legacy))
because the upstream repo no longer publishes a Python package — its `main`
branch is now a TypeScript app. No extra `uv add` step is needed.

## Configure

Set environment variables in your shell or a `.env` file (do **not** commit
real keys):

```powershell
$env:AGENT_BACKEND = "dexter"
$env:OPENAI_API_KEY = "sk-..."             # paste later
$env:FINANCIAL_DATASETS_API_KEY = "..."    # paste later
$env:EXA_API_KEY = "..."                   # optional, enables web search tool
$env:AGENT_ALLOWED_ORIGINS = "http://localhost:8050"
```

### Web search tool (Exa)

Dexter's news/web-search tool uses [Exa.ai](https://exa.ai). Set
`EXA_API_KEY` to enable it; if the variable is unset the tool simply returns
no results and the agent falls back to its other tools.

### Using OpenRouter (or any OpenAI-compatible provider)

OpenRouter exposes an OpenAI-compatible API, so dexter can use it with two
extra environment variables:

```powershell
$env:OPENAI_API_KEY  = "sk-or-v1-..."                  # your OpenRouter key
$env:OPENAI_BASE_URL = "https://openrouter.ai/api/v1"
$env:DEXTER_MODEL    = "openai/gpt-4o-mini"            # any OpenRouter model id
```

`DEXTER_MODEL` overrides dexter's default `gpt-4.1` and must use the
provider's namespaced model id (e.g. `openai/gpt-4o-mini`,
`anthropic/claude-3.5-sonnet`). The same pattern works for Together, Groq,
DeepInfra, etc. — just change `OPENAI_BASE_URL` and `DEXTER_MODEL`.

Leave `OPENAI_API_KEY` / `FINANCIAL_DATASETS_API_KEY` blank for now and the
service will report a friendly "not configured" response. Update them later
and restart.

## Run

Two ways to run locally:

### A) Two-process (default)

The Dash app talks to the agent over HTTP, like a real microservice:

```powershell
# Terminal 1 — agent
uv run --extra agent uvicorn agent_service.main:app --port 8765

# Terminal 2 — Dash
uv run python app.py
```

### B) In-process (simulates Azure)

Skip uvicorn entirely. The Dash callback imports `agent_service.adapters`
and calls the agent in the same Python process — exactly how it runs on
Azure Functions. Useful for reproducing production behavior or for a quick
single-terminal setup:

```powershell
$env:AGENT_INPROCESS = "1"
uv run --extra agent python app.py
```

`AGENT_INPROCESS` is auto-enabled on Azure (when `WEBSITE_HOSTNAME` is set);
forcing it to `1` locally turns it on, `0` turns it off.

Smoke test:

```powershell
curl http://localhost:8765/health
```

## API

`POST /chat`

```json
{
  "messages": [{"role": "user", "content": "What's Tencent's latest revenue?"}],
  "lang": "en"
}
```

Response:

```json
{ "reply": "...", "backend": "dexter" }
```

## Swapping the backend

Add a new class in `adapters.py` that exposes `name` and
`run(messages, lang) -> str`, then return it from `build_agent()` based on
`AGENT_BACKEND`. No other file changes are needed.
