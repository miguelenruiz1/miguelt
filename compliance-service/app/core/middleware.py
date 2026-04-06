"""Request middleware — correlation ID, tenant resolution, security headers."""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

log = get_logger(__name__)

_EXCLUDE = frozenset({"/health", "/ready", "/metrics", "/docs", "/openapi.json", "/redoc"})
_EXCLUDE_PREFIXES = ("/api/v1/compliance/verify",)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
        request.state.correlation_id = cid
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=cid)

        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Correlation-Id"] = cid
        response.headers["X-Response-Time-Ms"] = str(elapsed)

        # Skip noisy healthcheck logs (Cloud Run pings every few seconds)
        if request.url.path not in ("/health", "/ready", "/metrics"):
            log.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                elapsed_ms=elapsed,
            )
        return response


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in _EXCLUDE or any(path.startswith(p) for p in _EXCLUDE_PREFIXES):
            return await call_next(request)
        request.state.tenant_slug = request.headers.get("X-Tenant-Id", "default")
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
