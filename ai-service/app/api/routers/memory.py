"""Tenant AI memory endpoints."""
from __future__ import annotations

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, _assert_tenant_access, get_redis
from app.db.session import get_db_session
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


def _svc(db: AsyncSession = Depends(get_db_session), redis: aioredis.Redis = Depends(get_redis)) -> AnalysisService:
    return AnalysisService(db, redis)


@router.get("/{tenant_id}")
async def get_memory(tenant_id: str, user: CurrentUser, svc: AnalysisService = Depends(_svc)):
    _assert_tenant_access(user, tenant_id, action="ai.memory.read", resource="tenant_memory")
    return await svc.get_tenant_memory(tenant_id)


@router.delete("/{tenant_id}")
async def delete_memory(tenant_id: str, user: CurrentUser, svc: AnalysisService = Depends(_svc)):
    _assert_tenant_access(user, tenant_id, action="ai.memory.delete", resource="tenant_memory")
    deleted = await svc.delete_tenant_memory(tenant_id)
    return {"status": "ok", "deleted": deleted}


@router.delete("/{tenant_id}/last")
async def delete_last(tenant_id: str, user: CurrentUser, svc: AnalysisService = Depends(_svc)):
    _assert_tenant_access(user, tenant_id, action="ai.memory.delete_last", resource="last_analysis")
    deleted = await svc.delete_last_analysis(tenant_id)
    return {"status": "ok", "deleted": deleted}
