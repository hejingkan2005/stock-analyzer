"""FastAPI microservice that wraps a chat agent (dexter by default).

Run locally:
    uv run --extra agent uvicorn agent_service.main:app --port 8765

Environment variables (see adapters.py):
    AGENT_BACKEND               "dexter" | "echo"   (default: dexter)
    OPENAI_API_KEY              required for dexter
    FINANCIAL_DATASETS_API_KEY  required for dexter
    AGENT_ALLOWED_ORIGINS       optional, comma-separated CORS origins
                                (default: http://localhost:8050)
"""

from __future__ import annotations

import logging
import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .adapters import build_agent

logger = logging.getLogger("agent_service")
logging.basicConfig(level=logging.INFO)


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., max_length=8000)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., max_length=40)
    lang: Literal["zh", "en"] = "zh"


class ChatResponse(BaseModel):
    reply: str
    backend: str


_agent = build_agent()
logger.info("Agent backend selected: %s", _agent.name)

app = FastAPI(title="Stock Analyzer Chat Agent", version="0.1.0")

_origins = [
    o.strip()
    for o in (os.getenv("AGENT_ALLOWED_ORIGINS") or "http://localhost:8050").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "backend": _agent.name}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages must be non-empty")
    try:
        reply = _agent.run([m.model_dump() for m in req.messages], req.lang)
    except RuntimeError as exc:
        logger.exception("Agent error")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected agent error")
        raise HTTPException(status_code=500, detail="Internal agent error") from exc
    return ChatResponse(reply=reply or "", backend=_agent.name)
