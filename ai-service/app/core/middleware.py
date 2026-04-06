"""Request middleware — correlation ID, timing."""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id, method=request.method, path=request.url.path)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Correlation-Id"] = correlation_id
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)

        structlog.contextvars.bind_contextvars(status_code=response.status_code, elapsed_ms=elapsed_ms)
        if request.url.path not in ("/health", "/ready", "/metrics"):
            structlog.get_logger(__name__).info("request_completed")
        return response
