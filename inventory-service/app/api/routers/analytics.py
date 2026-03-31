"""Analytics / overview endpoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
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


@router.get("/inventory-kpis")
async def inventory_kpis(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    db: AsyncSession = Depends(get_db_session),
    date_from: str | None = None,
    date_to: str | None = None,
) -> ORJSONResponse:
    """KPIs de inventario: fill rate, backorder rate, stockouts, ventas perdidas, calidad OC, lead time."""
    from datetime import datetime
    from sqlalchemy import func as F, and_
    from app.db.models.sales_order import SalesOrder, SalesOrderLine
    from app.db.models.purchase_order import PurchaseOrder, PurchaseOrderLine
    from app.db.models.alert import StockAlert
    from app.db.models.partner import BusinessPartner

    tid = current_user["tenant_id"]
    filters_so = [SalesOrder.tenant_id == tid]
    filters_po = [PurchaseOrder.tenant_id == tid]
    if date_from:
        df = datetime.fromisoformat(date_from)
        filters_so.append(SalesOrder.created_at >= df)
        filters_po.append(PurchaseOrder.created_at >= df)
    if date_to:
        dt = datetime.fromisoformat(date_to)
        filters_so.append(SalesOrder.created_at <= dt)
        filters_po.append(PurchaseOrder.created_at <= dt)

    # Fill rate: SO lines fully shipped / total SO lines (shipped+delivered SOs)
    fill_q = (
        select(
            F.count().label("total"),
            F.count().filter(SalesOrderLine.picked_quantity >= SalesOrderLine.quantity).label("filled"),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderLine.sales_order_id)
        .where(*filters_so, SalesOrder.status.in_(["shipped", "delivered"]))
    )
    fill_row = (await db.execute(fill_q)).first()
    fill_rate = round(fill_row[1] * 100.0 / fill_row[0], 1) if fill_row and fill_row[0] > 0 else None

    # Backorder rate
    total_so = (await db.execute(select(F.count()).where(*filters_so))).scalar_one()
    backorders = (await db.execute(
        select(F.count()).where(*filters_so, SalesOrder.backorder_parent_id.is_not(None))
    )).scalar_one()
    backorder_rate = round(backorders * 100.0 / total_so, 1) if total_so > 0 else 0

    # Stockout incidents
    alert_filters = [StockAlert.tenant_id == tid, StockAlert.alert_type == "out_of_stock"]
    if date_from:
        alert_filters.append(StockAlert.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        alert_filters.append(StockAlert.created_at <= datetime.fromisoformat(date_to))
    stockouts = (await db.execute(select(F.count()).where(*alert_filters))).scalar_one()

    # Lost sales estimate: (ordered - shipped) * unit_price where partial
    lost_q = (
        select(
            F.coalesce(
                F.sum((SalesOrderLine.quantity - SalesOrderLine.picked_quantity) * SalesOrderLine.unit_price),
                0,
            )
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderLine.sales_order_id)
        .where(
            *filters_so,
            SalesOrder.status.in_(["shipped", "delivered"]),
            SalesOrderLine.picked_quantity < SalesOrderLine.quantity,
        )
    )
    lost_sales = float((await db.execute(lost_q)).scalar_one())

    # PO quality: received POs with no rejection / total received POs
    received_pos = (await db.execute(
        select(F.count()).where(*filters_po, PurchaseOrder.status == "received")
    )).scalar_one()
    rejected_pos = (await db.execute(
        select(F.count()).where(*filters_po, PurchaseOrder.status == "received", PurchaseOrder.rejection_reason.is_not(None))
    )).scalar_one()
    po_quality = round((received_pos - rejected_pos) * 100.0 / received_pos, 1) if received_pos > 0 else None

    # Reception accuracy: PO lines where received_qty == ordered_qty / total
    acc_q = (
        select(
            F.count().label("total"),
            F.count().filter(PurchaseOrderLine.received_quantity >= PurchaseOrderLine.quantity).label("accurate"),
        )
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderLine.purchase_order_id)
        .where(*filters_po, PurchaseOrder.status == "received")
    )
    acc_row = (await db.execute(acc_q)).first()
    reception_accuracy = round(acc_row[1] * 100.0 / acc_row[0], 1) if acc_row and acc_row[0] > 0 else None

    return ORJSONResponse(content={
        "fill_rate_pct": fill_rate,
        "backorder_rate_pct": backorder_rate,
        "stockout_incidents": stockouts,
        "lost_sales_estimate": lost_sales,
        "po_quality_pct": po_quality,
        "reception_accuracy_pct": reception_accuracy,
        "total_sales_orders": total_so,
        "total_backorders": backorders,
        "total_received_pos": received_pos,
    })


@router.get("/eoq/{product_id}")
async def eoq_by_product(
    product_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    db: AsyncSession = Depends(get_db_session),
    ordering_cost: float = Query(50.0, description="Costo por orden de compra (S)"),
    holding_cost_pct: float = Query(25.0, description="Costo de mantener inventario como % del costo unitario (H%)"),
    working_days: int = Query(250, description="Dias laborables al ano"),
) -> ORJSONResponse:
    """EOQ (Wilson) para un producto especifico: Q*, N ordenes/ano, dias entre ordenes, punto de reorden."""
    import math
    from sqlalchemy import func as F
    from app.db.models.entity import Product
    from app.db.models.stock import StockMovement, StockLevel

    tid = current_user["tenant_id"]

    # Fetch product
    product = (await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tid)
    )).scalar_one_or_none()
    if not product:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Product not found")

    # Annual demand: sum of outgoing movements in last 12 months
    from datetime import datetime, timedelta
    one_year_ago = datetime.utcnow() - timedelta(days=365)
    demand_q = (
        select(F.coalesce(F.sum(StockMovement.quantity), 0))
        .where(
            StockMovement.tenant_id == tid,
            StockMovement.entity_id == product_id,
            StockMovement.movement_type.in_(["sale", "manual_out", "waste", "consumption"]),
            StockMovement.created_at >= one_year_ago,
        )
    )
    annual_demand = float((await db.execute(demand_q)).scalar_one())

    # Unit cost (average)
    avg_cost_q = (
        select(F.coalesce(F.avg(StockLevel.avg_cost), 0))
        .where(StockLevel.tenant_id == tid, StockLevel.entity_id == product_id)
    )
    unit_cost = float((await db.execute(avg_cost_q)).scalar_one())

    # EOQ calculation
    S = ordering_cost
    H = unit_cost * holding_cost_pct / 100.0 if unit_cost > 0 else 1.0
    D = annual_demand

    if D <= 0 or H <= 0:
        return ORJSONResponse(content={
            "product_id": product_id,
            "sku": product.sku,
            "name": product.name,
            "annual_demand": D,
            "eoq": None,
            "message": "Insufficient demand or cost data",
        })

    Q_star = math.sqrt(2 * D * S / H)
    N = D / Q_star  # orders per year
    T = working_days / N if N > 0 else None  # days between orders
    daily_demand = D / working_days
    lead_time = getattr(product, "lead_time_days", 0) or 0
    safety_stock = getattr(product, "min_stock_level", 0) or 0
    reorder_point = daily_demand * lead_time + safety_stock

    # Total cost
    ordering_total = (D / Q_star) * S
    holding_total = (Q_star / 2) * H
    total_cost = unit_cost * D + ordering_total + holding_total

    return ORJSONResponse(content={
        "product_id": product_id,
        "sku": product.sku,
        "name": product.name,
        "annual_demand": round(D, 2),
        "unit_cost": round(unit_cost, 2),
        "ordering_cost_S": S,
        "holding_cost_H": round(H, 4),
        "eoq_Q_star": round(Q_star, 2),
        "orders_per_year_N": round(N, 2),
        "days_between_orders_T": round(T, 1) if T else None,
        "reorder_point": round(reorder_point, 2),
        "daily_demand": round(daily_demand, 2),
        "ordering_cost_total": round(ordering_total, 2),
        "holding_cost_total": round(holding_total, 2),
        "total_annual_cost": round(total_cost, 2),
    })
