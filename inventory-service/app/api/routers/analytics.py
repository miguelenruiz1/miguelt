"""Analytics / overview endpoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse

from sqlalchemy import select

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


@router.get("/committed-stock", summary="Stock comprometido — reservas activas")
async def get_committed_stock(
    current_user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Returns summary of committed stock: products with active reservations, total qty, total value."""
    tenant_id = current_user.get("tenant_id", "default")

    from sqlalchemy import func as sa_func, and_
    from app.db.models.stock import StockLevel
    from app.db.models.entity import Product

    # Query stock levels with qty_reserved > 0
    q = (
        select(
            sa_func.count(sa_func.distinct(StockLevel.product_id)).label("products_count"),
            sa_func.coalesce(sa_func.sum(StockLevel.qty_reserved), 0).label("total_qty"),
        )
        .where(
            StockLevel.tenant_id == tenant_id,
            StockLevel.qty_reserved > 0,
        )
    )
    row = (await db.execute(q)).one()

    # Calculate cost value from stock levels
    cost_q = (
        select(
            sa_func.coalesce(
                sa_func.sum(StockLevel.qty_reserved * Product.last_purchase_cost), 0
            ).label("total_cost_value"),
        )
        .join(Product, Product.id == StockLevel.product_id)
        .where(
            StockLevel.tenant_id == tenant_id,
            StockLevel.qty_reserved > 0,
        )
    )
    cost_row = (await db.execute(cost_q)).one()

    # Calculate sale value from actual SO line prices (the real committed value)
    from app.db.models.stock import StockReservation
    from app.db.models.sales_order import SalesOrderLine
    sale_q = (
        select(
            sa_func.coalesce(
                sa_func.sum(StockReservation.quantity * SalesOrderLine.unit_price), 0
            ).label("total_sale_value"),
        )
        .join(SalesOrderLine, SalesOrderLine.id == StockReservation.sales_order_line_id)
        .where(
            StockReservation.tenant_id == tenant_id,
            StockReservation.status == "active",
        )
    )
    sale_row = (await db.execute(sale_q)).one()

    return ORJSONResponse(content={
        "products_with_reservations": row.products_count,
        "total_reserved_qty": float(row.total_qty),
        "total_reserved_value": float(sale_row.total_sale_value),
        "total_reserved_cost": float(cost_row.total_cost_value),
        "currency": "COP",
    })
