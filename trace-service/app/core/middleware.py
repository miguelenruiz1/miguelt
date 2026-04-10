"""Middlewares: correlation-id, request timing, idempotency check header."""
import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


_LOG_SKIP_PATHS = frozenset({"/health", "/ready", "/metrics"})


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Injects a correlation-id into every request context.
    - Reads X-Correlation-Id header if provided; otherwise generates one.
    - Binds it to structlog context so every log line carries it.
    - Adds it to the response headers.
    - Skips request_completed log spam for healthcheck/metrics paths.
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

        # Skip noisy healthcheck logs (Cloud Run pings every few seconds)
        if request.url.path not in _LOG_SKIP_PATHS:
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


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Enforces JWT auth on all endpoints by default.

    Whitelisted paths (no auth):
      - /health, /ready, /metrics, /docs, /openapi.json, /redoc
      - Static /uploads
      - /api/v1/internal/* (validated by S2S token)
      - Public verify endpoints

    For everything else, requires either:
      - Authorization: Bearer <jwt> header (validated by routers via Depends)
      - X-Service-Token header (S2S bypass)

    This middleware does NOT decode the JWT — it only enforces presence so
    routers without an explicit Depends still get protected. Routers should
    still call get_current_user() for full validation.
    """

    EXCLUDED_EXACT = {
        "/health", "/ready", "/metrics", "/docs", "/openapi.json", "/redoc",
    }
    EXCLUDED_PREFIX = (
        "/uploads/",
        "/api/v1/internal/",  # Internal S2S endpoints (use X-Service-Token)
        "/api/v1/anchoring/",  # S2S anchoring-as-a-service (validates X-Service-Token)
        "/api/v1/assets/metadata/",  # Public cNFT metadata (Solana explorers need unauthenticated access)
    )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        from app.core.settings import get_settings
        settings = get_settings()

        if not settings.REQUIRE_AUTH:
            return await call_next(request)

        path = request.url.path
        if path in self.EXCLUDED_EXACT:
            return await call_next(request)
        if any(path.startswith(p) for p in self.EXCLUDED_PREFIX):
            return await call_next(request)

        # Allow OPTIONS preflight without auth
        if request.method == "OPTIONS":
            return await call_next(request)

        # Accept either Bearer JWT or valid X-Service-Token
        has_bearer = (request.headers.get("Authorization", "").lower().startswith("bearer "))
        s2s_token = request.headers.get("X-Service-Token")
        has_valid_s2s = False
        if s2s_token:
            import secrets as _secrets
            has_valid_s2s = _secrets.compare_digest(s2s_token, settings.S2S_SERVICE_TOKEN)

        if not (has_bearer or has_valid_s2s):
            from fastapi.responses import ORJSONResponse
            status = 401 if not s2s_token else 403
            msg = ("Missing Authorization header (Bearer JWT) or X-Service-Token"
                   if not s2s_token else "Invalid service token")
            return ORJSONResponse(
                status_code=status,
                content={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": msg,
                    }
                },
            )

        return await call_next(request)
