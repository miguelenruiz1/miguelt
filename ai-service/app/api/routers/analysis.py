"""Analysis endpoints — receives data from other services and returns AI insights."""
from __future__ import annotations

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_redis
from app.db.session import get_db_session
from app.domain.schemas import AnalyzePnLRequest, PnLAnalysis
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api/v1/analyze", tags=["analysis"])


def _svc(db: AsyncSession = Depends(get_db_session), redis: aioredis.Redis = Depends(get_redis)) -> AnalysisService:
    return AnalysisService(db, redis)


@router.post("/pnl", response_model=PnLAnalysis)
async def analyze_pnl(body: AnalyzePnLRequest, svc: AnalysisService = Depends(_svc)):
    """Analyze P&L data. Called by inventory-service with the PnL payload."""
    return await svc.analyze_pnl(
        tenant_id=body.tenant_id,
        date_from=body.date_from,
        date_to=body.date_to,
        pnl_data=body.pnl_data,
        business_context=body.business_context,
        force=body.force,
    )
