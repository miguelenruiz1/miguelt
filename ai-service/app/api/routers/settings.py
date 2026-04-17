"""Platform AI settings endpoints — superuser only."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ServiceToken, SuperUser, get_redis
from app.db.session import get_db_session
from app.services.settings_service import AISettingsService

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


def _svc(db: AsyncSession = Depends(get_db_session), redis: aioredis.Redis = Depends(get_redis)) -> AISettingsService:
    return AISettingsService(db, redis)


class UpdateSettingsRequest(BaseModel):
    anthropic_model_analysis: str | None = None
    anthropic_model_premium: str | None = None
    anthropic_max_tokens: int | None = None
    anthropic_enabled: bool | None = None
    global_daily_limit_free: int | None = None
    global_daily_limit_starter: int | None = None
    global_daily_limit_professional: int | None = None
    global_daily_limit_enterprise: int | None = None
    cache_ttl_minutes: int | None = None
    cache_enabled: bool | None = None
    # Money-shaped fields use Decimal so Pydantic doesn't collapse to float
    # and lose the trailing precision that matters when accumulating monthly
    # costs across hundreds of analyses. The DB stores these as Numeric.
    estimated_cost_per_analysis_usd: Decimal | None = None
    alert_monthly_cost_usd: Decimal | None = None
    pnl_analysis_enabled: bool | None = None


class UpdateApiKeyRequest(BaseModel):
    api_key: str


class ClearCacheRequest(BaseModel):
    confirm: bool


@router.get("")
async def get_ai_settings(_user: SuperUser, svc: AISettingsService = Depends(_svc)):
    return await svc.get_settings_response()


@router.post("")
async def update_ai_settings(body: UpdateSettingsRequest, _user: SuperUser, svc: AISettingsService = Depends(_svc)):
    return await svc.update_settings(body.model_dump(exclude_none=True))


@router.patch("/api-key")
async def update_api_key(body: UpdateApiKeyRequest, _user: SuperUser, svc: AISettingsService = Depends(_svc)):
    if not body.api_key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty")
    return await svc.update_api_key(body.api_key.strip())


@router.post("/test")
async def test_connection(_user: SuperUser, svc: AISettingsService = Depends(_svc)):
    return await svc.test_connection()


@router.get("/config")
async def get_config_internal(
    _token: ServiceToken,
    db: AsyncSession = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Internal endpoint for other services to read AI config. Requires service token."""
    svc = AISettingsService(db, redis)
    return await svc.get_full_config()


@router.get("/audit/cross-tenant")
async def get_cross_tenant_audit(
    _user: SuperUser,
    redis: aioredis.Redis = Depends(get_redis),
    month: str | None = Query(None, description="YYYY-MM format, defaults to current month"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List all superuser cross-tenant access events. Superuser only."""
    target_month = month or datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"audit:cross_tenant:{target_month}"
    total = await redis.llen(key)
    raw = await redis.lrange(key, offset, offset + limit - 1)
    items = [json.loads(r) for r in raw]
    return {"items": items, "total": total, "month": target_month, "offset": offset, "limit": limit}
