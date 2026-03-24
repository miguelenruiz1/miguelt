"""AI usage metrics endpoint."""
from __future__ import annotations

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SuperUser, get_redis
from app.db.session import get_db_session
from app.services.settings_service import AISettingsService

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


class ClearCacheRequest(BaseModel):
    confirm: bool


@router.get("")
async def get_metrics(_user: SuperUser, db: AsyncSession = Depends(get_db_session), redis: aioredis.Redis = Depends(get_redis)):
    svc = AISettingsService(db, redis)
    return await svc.get_metrics()


@router.delete("/cache")
async def clear_cache(body: ClearCacheRequest, _user: SuperUser, db: AsyncSession = Depends(get_db_session), redis: aioredis.Redis = Depends(get_redis)):
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Must confirm")
    svc = AISettingsService(db, redis)
    count = await svc.clear_all_caches()
    return {"status": "ok", "deleted": count}
