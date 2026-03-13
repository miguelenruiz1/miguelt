"""Middlewares: correlation-id, request timing, idempotency check header."""
import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Injects a correlation-id into every request context.
    - Reads X-Correlation-Id header if provided; otherwise generates one.
    - Binds it to structlog context so every log line carries it.
    - Adds it to the response headers.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Correlation-Id"] = correlation_id
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)

        structlog.contextvars.bind_contextvars(
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        log = structlog.get_logger(__name__)
        log.info("request_completed")

        return response


class IdempotencyKeyMiddleware(BaseHTTPMiddleware):
    """
    Attaches the Idempotency-Key header value to request.state so
    routers and services can use it without re-reading headers.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        idempotency_key = request.headers.get("Idempotency-Key")
        request.state.idempotency_key = idempotency_key
        return await call_next(request)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Reads X-Tenant-Id header and attaches it to request.state.tenant_slug.
    Does not validate — validation happens in get_tenant_id() dependency.
    Excluded paths skip header requirement.
    """

    EXCLUDED = {"/health", "/ready", "/metrics", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path not in self.EXCLUDED:
            request.state.tenant_slug = request.headers.get("X-Tenant-Id", "")
        return await call_next(request)
