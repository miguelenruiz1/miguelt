"""Platform AI settings endpoints — superuser only."""
from __future__ import annotations

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SuperUser, get_redis
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
    estimated_cost_per_analysis_usd: float | None = None
    alert_monthly_cost_usd: float | None = None
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
async def get_config_internal(db: AsyncSession = Depends(get_db_session), redis: aioredis.Redis = Depends(get_redis)):
    """Internal endpoint for other services to read AI config. No auth."""
    svc = AISettingsService(db, redis)
    return await svc.get_full_config()
