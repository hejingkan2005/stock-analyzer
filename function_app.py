"""Azure Functions entrypoint.

Routes:
- ``/agent/*`` -> FastAPI chat agent (``agent_service.main:app``) mounted at
  ``/agent`` so its own ``/chat`` and ``/health`` endpoints become
  ``/agent/chat`` and ``/agent/health``.
- everything else -> Dash app (Flask WSGI).

Both surfaces live in the same Function App, so the Dash UI can call the
agent via a same-origin URL (see ``_resolve_agent_service_url`` in app.py).
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import azure.functions as func

from app import server as flask_app

logger = logging.getLogger("function_app")

# Build the agent ASGI app lazily. If the optional ``agent`` extra (FastAPI,
# langchain, etc.) is missing, the Dash surface still works; only the chat
# endpoint will return 503.
_agent_asgi = None
_agent_import_error: Exception | None = None
try:
    from fastapi import FastAPI

    from agent_service.main import app as _agent_app

    _agent_asgi = FastAPI(title="Stock Analyzer (agent mount)")
    _agent_asgi.mount("/agent", _agent_app)
except Exception as exc:  # pragma: no cover - depends on deploy-time deps
    _agent_import_error = exc
    logger.warning("Agent service not available: %s", exc)


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _is_agent_path(req: func.HttpRequest) -> bool:
    path = urlparse(req.url).path.lstrip("/").lower()
    return path == "agent" or path.startswith("agent/")


def _agent_unavailable_response() -> func.HttpResponse:
    detail = (
        "Agent service is not available in this deployment. "
        f"Import error: {_agent_import_error!r}"
    )
    return func.HttpResponse(detail, status_code=503, mimetype="text/plain")


def _dispatch(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    if _is_agent_path(req):
        if _agent_asgi is None:
            return _agent_unavailable_response()
        return func.AsgiMiddleware(_agent_asgi).handle(req, context)
    return func.WsgiMiddleware(flask_app.wsgi_app).handle(req, context)


_HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]


@app.route(route="{*route}", methods=_HTTP_METHODS)
def dash_proxy(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return _dispatch(req, context)


@app.route(route="", methods=_HTTP_METHODS)
def dash_proxy_root(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return _dispatch(req, context)
