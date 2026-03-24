"""Health and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from app.core.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> ORJSONResponse:
    settings = get_settings()
    return ORJSONResponse({"status": "ok", "version": settings.APP_VERSION})


@router.get("/ready")
async def ready() -> ORJSONResponse:
    checks: dict[str, str] = {}
    ok = True

    # ── DB check ──
    try:
        from app.db.session import get_engine
        from sqlalchemy import text

        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = str(exc)
        ok = False

    # ── Redis check ──
    try:
        from app.api.deps import get_redis

        rd = await get_redis()
        await rd.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = str(exc)
        ok = False

    # ── subscription-service reachable ──
    try:
        from app.api.deps import get_http_client

        settings = get_settings()
        http = get_http_client()
        resp = await http.get(f"{settings.SUBSCRIPTION_SERVICE_URL}/health", timeout=5.0)
        checks["subscription_service"] = "ok" if resp.status_code == 200 else f"status={resp.status_code}"
        if resp.status_code != 200:
            ok = False
    except Exception as exc:
        checks["subscription_service"] = str(exc)
        ok = False

    status_code = 200 if ok else 503
    return ORJSONResponse(
        {"status": "ready" if ok else "not_ready", "checks": checks},
        status_code=status_code,
    )
