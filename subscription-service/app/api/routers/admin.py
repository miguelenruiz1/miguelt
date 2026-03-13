"""Admin/metrics router."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db_session
from app.domain.schemas import OverviewMetrics
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _svc(db: Annotated[AsyncSession, Depends(get_db_session)]) -> MetricsService:
    return MetricsService(db)


@router.get("/metrics/overview", response_model=OverviewMetrics)
async def get_overview(
    _: Annotated[dict, Depends(require_permission("subscription.view"))],
    svc: MetricsService = Depends(_svc),
):
    return await svc.get_overview()
