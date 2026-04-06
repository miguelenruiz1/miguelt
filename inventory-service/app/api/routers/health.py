"""Health and readiness endpoints.

- /health: liveness — process is up. Returns 200 always.
- /ready: readiness — DB + Redis + critical deps. Returns 503 when not serviceable.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> ORJSONResponse:
    """Liveness probe — does not check dependencies, only that the process answers."""
    return ORJSONResponse({"status": "ok", "service": "inventory-service"})


@router.get("/ready")
async def ready() -> ORJSONResponse:
    """Readiness probe — verifies DB and Redis are reachable."""
    from app.db.session import get_engine
    from sqlalchemy import text
    import redis.asyncio as aioredis
    from app.core.settings import get_settings

    settings = get_settings()
    checks: dict[str, str] = {}
    overall_ok = True

    # DB check
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=3.0)
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"fail: {str(exc)[:120]}"
        overall_ok = False

    # Redis check
    try:
        rd = aioredis.from_url(settings.REDIS_URL, socket_timeout=3)
        await asyncio.wait_for(rd.ping(), timeout=3.0)
        await rd.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"fail: {str(exc)[:120]}"
        overall_ok = False

    body = {"status": "ready" if overall_ok else "not_ready", "checks": checks}
    return ORJSONResponse(body, status_code=200 if overall_ok else 503)
