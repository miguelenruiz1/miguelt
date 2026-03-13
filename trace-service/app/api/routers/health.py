"""Liveness and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from app.core.settings import get_settings
from app.domain.schemas import HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=get_settings().APP_VERSION)


@router.get("/ready", response_model=ReadyResponse, summary="Readiness probe")
async def ready() -> ORJSONResponse:
    checks: dict[str, str] = {}
    overall = "ok"

    # Check Postgres
    try:
        from app.db.session import get_engine
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy", fromlist=["text"]).text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"
        overall = "degraded"

    # Check Redis
    try:
        from app.db.session import _engine  # just to avoid circular, we check redis separately
        import redis.asyncio as aioredis
        from app.core.settings import get_settings
        r = aioredis.from_url(get_settings().REDIS_URL, socket_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        overall = "degraded"

    status_code = 200 if overall == "ok" else 503
    return ORJSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks},
    )
