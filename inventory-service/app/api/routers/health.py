"""Health and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> ORJSONResponse:
    return ORJSONResponse({"status": "ok", "service": "inventory-service"})


@router.get("/ready")
async def ready() -> ORJSONResponse:
    from app.db.session import get_engine
    from sqlalchemy import text
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return ORJSONResponse({"status": "ready"})
    except Exception as exc:
        return ORJSONResponse({"status": "not_ready", "detail": str(exc)}, status_code=503)
