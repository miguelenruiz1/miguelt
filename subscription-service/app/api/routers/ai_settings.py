"""Platform AI settings endpoints — superuser only."""
from __future__ import annotations

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_redis
from app.db.session import get_db_session
from app.services.ai_settings_service import AISettingsService

router = APIRouter(prefix="/api/v1/platform/ai", tags=["platform-ai"])


def _require_superuser(current_user: CurrentUser) -> dict:
    if not current_user.get("is_superuser"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    return current_user


SuperUser = Annotated[dict, Depends(_require_superuser)]


def _svc(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    redis: aioredis.Redis = Depends(get_redis),
) -> AISettingsService:
    return AISettingsService(db, redis)


# ─── Schemas ──────────────────────────────────────────────────────────────────

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


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_ai_settings(_user: SuperUser, svc: AISettingsService = Depends(_svc)):
    return await svc.get_settings_response()


@router.post("/settings")
async def update_ai_settings(
    body: UpdateSettingsRequest,
    _user: SuperUser,
    svc: AISettingsService = Depends(_svc),
):
    data = body.model_dump(exclude_none=True)
    return await svc.update_settings(data)


@router.patch("/settings/api-key")
async def update_api_key(
    body: UpdateApiKeyRequest,
    _user: SuperUser,
    svc: AISettingsService = Depends(_svc),
):
    if not body.api_key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty")
    return await svc.update_api_key(body.api_key.strip())


@router.post("/settings/test")
async def test_ai_connection(_user: SuperUser, svc: AISettingsService = Depends(_svc)):
    return await svc.test_connection()


@router.get("/metrics")
async def get_ai_metrics(_user: SuperUser, svc: AISettingsService = Depends(_svc)):
    return await svc.get_metrics()


@router.delete("/cache")
async def clear_ai_cache(
    body: ClearCacheRequest,
    _user: SuperUser,
    svc: AISettingsService = Depends(_svc),
):
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Must confirm cache deletion")
    count = await svc.clear_all_caches()
    return {"status": "ok", "deleted": count}


# ─── Inter-service endpoint — REQUIRES X-Service-Token ───────────────────────

async def _verify_service_token(
    x_service_token: str = Header(..., alias="X-Service-Token"),
) -> str:
    """Validate inter-service shared secret. Constant-time comparison."""
    import secrets as _secrets
    from app.core.settings import get_settings as _gs
    if not _secrets.compare_digest(x_service_token, _gs().S2S_SERVICE_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid service token")
    return x_service_token


@router.get("/config", dependencies=[Depends(_verify_service_token)])
async def get_ai_config_internal(
    db: AsyncSession = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    """S2S endpoint for inventory-service to fetch AI config.

    REQUIRES X-Service-Token header. Previously this was unauthenticated and
    leaked the Anthropic API key in plaintext to anyone who could reach
    /api/v1/platform/ai/config (mapped through the gateway).
    """
    svc = AISettingsService(db, redis)
    s = await svc.get_settings()
    raw_key = await svc.get_decrypted_key()
    return {
        "anthropic_api_key": raw_key or "",
        "anthropic_model_analysis": s.anthropic_model_analysis,
        "anthropic_max_tokens": s.anthropic_max_tokens,
        "anthropic_enabled": s.anthropic_enabled,
        "cache_ttl_minutes": s.cache_ttl_minutes,
        "cache_enabled": s.cache_enabled,
        "pnl_analysis_enabled": s.pnl_analysis_enabled,
        "global_daily_limit_free": s.global_daily_limit_free,
        "global_daily_limit_starter": s.global_daily_limit_starter,
        "global_daily_limit_professional": s.global_daily_limit_professional,
        "global_daily_limit_enterprise": s.global_daily_limit_enterprise,
    }
