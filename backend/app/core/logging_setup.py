"""
Structured logging utilities aligned with the project's logging standard.

Features:
- JSON output with required fields (timestamp, service, env, level, message).
- Correlation IDs (trace_id, request_id) managed via contextvars.
- Request context helpers (method, path, status_code, client_ip, user_id).
- FastAPI middleware for automatic request logging and ID propagation.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from collections import OrderedDict
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from fastapi import Request


# Context variables keep request-scoped values without global state.
trace_id_ctx: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
client_ip_ctx: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)
user_id_ctx: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
method_ctx: ContextVar[Optional[str]] = ContextVar("method", default=None)
path_ctx: ContextVar[Optional[str]] = ContextVar("path", default=None)
status_code_ctx: ContextVar[Optional[int]] = ContextVar("status_code", default=None)


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def set_correlation_ids(
    trace_id: Optional[str] = None, request_id: Optional[str] = None
) -> Tuple[str, str]:
    """Set or generate correlation IDs for the current context."""
    if trace_id is None:
        trace_id = str(uuid4())
    if request_id is None:
        request_id = str(uuid4())
    trace_id_ctx.set(trace_id)
    request_id_ctx.set(request_id)
    return trace_id, request_id


def set_request_context(
    *,
    client_ip: Optional[str] = None,
    user_id: Optional[str] = None,
    method: Optional[str] = None,
    path: Optional[str] = None,
    status_code: Optional[int] = None,
) -> None:
    """Attach request-scoped metadata to the current context."""
    if client_ip is not None:
        client_ip_ctx.set(client_ip)
    if user_id is not None:
        user_id_ctx.set(user_id)
    if method is not None:
        method_ctx.set(method)
    if path is not None:
        path_ctx.set(path)
    if status_code is not None:
        status_code_ctx.set(status_code)


def clear_context() -> None:
    """Reset context variables after a request completes."""
    trace_id_ctx.set(None)
    request_id_ctx.set(None)
    client_ip_ctx.set(None)
    user_id_ctx.set(None)
    method_ctx.set(None)
    path_ctx.set(None)
    status_code_ctx.set(None)


def _filtered_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values to keep logs concise."""
    return {k: v for k, v in payload.items() if v is not None}


class JsonLogFormatter(logging.Formatter):
    """Render log records as JSON with standard fields.
    
    error_code is placed immediately after 'level' field for high visibility.
    """

    def __init__(self, service: str, env: str) -> None:
        super().__init__()
        self.service = service
        self.env = env

    def format(self, record: logging.LogRecord) -> str:
        # Build payload with error_code prominently placed after level (for visibility)
        payload = OrderedDict([
            ("timestamp", _utc_now_iso()),
            ("service", self.service),
            ("env", self.env),
            ("level", record.levelname),
        ])
        
        # Add error_code immediately after level if present (makes it highly visible)
        error_code = getattr(record, "error_code", None)
        if error_code:
            payload["error_code"] = error_code
        
        # Continue with standard fields
        payload.update({
            "message": record.getMessage(),
            "trace_id": trace_id_ctx.get(),
            "request_id": request_id_ctx.get(),
            "client_ip": client_ip_ctx.get(),
            "user_id": user_id_ctx.get(),
            "method": method_ctx.get(),
            "path": path_ctx.get(),
            "status_code": status_code_ctx.get(),
        })

        # Accept extra_data dict for arbitrary safe metadata
        extra_data = getattr(record, "extra_data", None)
        if isinstance(extra_data, dict):
            payload.update(extra_data)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(_filtered_payload(payload), ensure_ascii=True)


def configure_logging(
    *,
    service_name: str,
    env: str = "dev",
    level: str = "INFO",
    stream = sys.stdout,
) -> None:
    """
    Configure root logging with JSON formatter and shared handler.

    Call once at service startup. Safe to call multiple times (replaces handlers).
    
    error_code fields are placed immediately after 'level' for high visibility in logs.
    """
    root = logging.getLogger()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter(service=service_name, env=env))

    # Replace existing handlers to avoid duplicate logs
    root.handlers.clear()
    root.addHandler(handler)

    # Align common uvicorn loggers with the same handler
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True


async def request_logging_middleware(request: Request, call_next):
    """
    FastAPI middleware to handle correlation IDs and structured request logs.
    """
    incoming_trace = request.headers.get("x-trace-id") or request.headers.get("x-request-id")
    incoming_request = request.headers.get("x-request-id")
    trace_id, request_id = set_correlation_ids(incoming_trace, incoming_request)

    set_request_context(
        client_ip=request.client.host if request.client else None,
        method=request.method,
        path=request.url.path,
    )

    start = time.perf_counter()
    response = None
    status_code: Optional[int] = None

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        logging.getLogger(__name__).exception(
            "Unhandled application error",
            extra={"error_code": "UNHANDLED_EXCEPTION"},
        )
        status_code = 500
        raise
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        status_code_to_log = status_code if status_code is not None else 500
        set_request_context(status_code=status_code_to_log)

        logging.getLogger("http").info(
            "http_request",
            extra={
                "extra_data": {
                    "duration_ms": duration_ms,
                }
            },
        )

        if response is not None:
            response.headers["X-Trace-Id"] = trace_id
            response.headers["X-Request-Id"] = request_id

        clear_context()
