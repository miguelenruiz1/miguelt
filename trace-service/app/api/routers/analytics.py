"""Analytics and KPI endpoints for trace-service."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.db.session import get_db_session
from app.services.transport_analytics_service import TransportAnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/transport")
async def transport_kpis(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db_session),
    period: str = Query("month", pattern="^(day|week|month)$"),
    date_from: str | None = None,
    date_to: str | None = None,
):
    svc = TransportAnalyticsService(db)
    df = datetime.fromisoformat(date_from) if date_from else None
    dt = datetime.fromisoformat(date_to) if date_to else None
    return await svc.transport_kpis(tenant_id, period, df, dt)
