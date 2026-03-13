"""Analytics / overview endpoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.services.analytics_service import AnalyticsService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = AnalyticsService(db)
    data = await svc.overview(current_user["tenant_id"])
    return ORJSONResponse(data)


@router.get("/occupation")
async def occupation(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    db: AsyncSession = Depends(get_db_session),
    warehouse_id: str | None = None,
) -> ORJSONResponse:
    svc = AnalyticsService(db)
    data = await svc.occupation(current_user["tenant_id"], warehouse_id=warehouse_id)
    return ORJSONResponse(data)


@router.get("/abc")
async def abc_classification(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    db: AsyncSession = Depends(get_db_session),
    months: int = 12,
) -> ORJSONResponse:
    svc = AnalyticsService(db)
    data = await svc.abc_classification(current_user["tenant_id"], months=months)
    return ORJSONResponse(data)


@router.get("/eoq")
async def eoq(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    db: AsyncSession = Depends(get_db_session),
    ordering_cost: float = 50.0,
    holding_cost_pct: float = 25.0,
) -> ORJSONResponse:
    svc = AnalyticsService(db)
    data = await svc.eoq(current_user["tenant_id"], ordering_cost=ordering_cost, holding_cost_pct=holding_cost_pct)
    return ORJSONResponse(data)


@router.get("/stock-policy")
async def stock_policy(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = AnalyticsService(db)
    data = await svc.stock_policy(current_user["tenant_id"])
    return ORJSONResponse(data)


@router.get("/storage-valuation")
async def storage_valuation(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = AnalyticsService(db)
    data = await svc.storage_valuation(current_user["tenant_id"])
    return ORJSONResponse(data)
