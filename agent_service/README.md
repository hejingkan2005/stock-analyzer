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
(an async event-based Python port, currently `dexter-py 2026.5.7`). No extra
`uv add` step is needed.

## Configure

Set environment variables in your shell or a `.env` file (do **not** commit
real keys):

```powershell
$env:AGENT_BACKEND = "dexter"
$env:OPENAI_API_KEY = "sk-..."             # paste later
$env:FINANCIAL_DATASETS_API_KEY = "..."    # paste later
$env:EXASEARCH_API_KEY = "..."             # optional, enables Exa web search
$env:DEXTER_HOME = "$env:TEMP\dexter"      # optional, scratchpad/cache dir
$env:AGENT_ALLOWED_ORIGINS = "http://localhost:8050"
```

### Web search tool

Dexter's web-search tool auto-selects a provider based on which key is set:
`EXASEARCH_API_KEY` ([Exa.ai](https://exa.ai)) is preferred, falling back to
`PERPLEXITY_API_KEY` then `TAVILY_API_KEY`. If none are set the tool is
omitted from the registry and the agent falls back to its other tools.

### Cache directory

Dexter persists its scratchpad and tool cache under `~/.dexter` by default;
set `DEXTER_HOME` to override (the adapter auto-points it at the OS temp dir
if you don't set it, so it Just Works on Azure).

### Using OpenRouter (or any OpenAI-compatible provider)

OpenRouter exposes an OpenAI-compatible API, so dexter can use it with two
extra environment variables:

Two equivalent options:

```powershell
# Option 1 — native OpenRouter prefix (recommended)
$env:OPENROUTER_API_KEY = "sk-or-v1-..."
$env:DEXTER_MODEL       = "openrouter:openai/gpt-4o-mini"

# Option 2 — repurpose the OpenAI client at the OpenRouter endpoint
$env:OPENAI_API_KEY  = "sk-or-v1-..."
$env:OPENAI_BASE_URL = "https://openrouter.ai/api/v1"
$env:DEXTER_MODEL    = "openai/gpt-4o-mini"
```

`DEXTER_MODEL` overrides dexter's default `gpt-4o-mini`. The new dexter is
multi-provider and routes by prefix (`openrouter:`, `claude-`, `gemini-`,
`groq:`, etc.) — no monkey-patching required.

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
