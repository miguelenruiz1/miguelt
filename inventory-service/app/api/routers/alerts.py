"""Stock alerts and Kardex endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.alert import KardexEntry, PaginatedAlerts, StockAlertOut
from app.services.alert_service import AlertService

router = APIRouter(prefix="/api/v1", tags=["alerts"])

Viewer = Annotated[dict, Depends(require_permission("inventory.view"))]
Manager = Annotated[dict, Depends(require_permission("inventory.manage"))]


@router.get("/alerts", response_model=PaginatedAlerts)
async def list_alerts(
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
    is_resolved: bool | None = None,
    alert_type: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    svc = AlertService(db)
    items, total = await svc.list_alerts(
        user["tenant_id"], is_resolved=is_resolved, alert_type=alert_type, offset=offset, limit=limit,
    )
    return PaginatedAlerts(items=items, total=total, offset=offset, limit=limit)


@router.get("/alerts/unread-count")
async def unread_alert_count(
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    svc = AlertService(db)
    count = await svc.count_unread(user["tenant_id"])
    return {"count": count}


@router.post("/alerts/{alert_id}/read", response_model=StockAlertOut)
async def mark_alert_read(
    alert_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    svc = AlertService(db)
    a = await svc.mark_read(alert_id, user["tenant_id"])
    if not a:
        from fastapi import HTTPException
        raise HTTPException(404, "Alert not found")
    return a


@router.post("/alerts/{alert_id}/acknowledge", response_model=StockAlertOut)
async def acknowledge_alert(
    alert_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    """Alias of `/read` — common UX expectation (`acknowledge`)."""
    svc = AlertService(db)
    a = await svc.mark_read(alert_id, user["tenant_id"])
    if not a:
        from fastapi import HTTPException
        raise HTTPException(404, "Alert not found")
    return a


@router.get("/alerts/rules")
async def list_alert_rules(
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    """List the active reorder/min-stock rules derived from product config.

    Rules aren't a separate entity today — they live as `min_stock_level`
    and `reorder_point` on each product. This endpoint exposes them as a
    flat list so the UI can show 'active rules' without re-deriving.
    """
    from sqlalchemy import select, or_
    from app.db.models.entity import Product
    rows = (await db.execute(
        select(
            Product.id, Product.sku, Product.name,
            Product.min_stock_level, Product.reorder_point,
            Product.reorder_quantity, Product.auto_reorder,
        ).where(
            Product.tenant_id == user["tenant_id"],
            Product.is_active.is_(True),
            or_(
                Product.min_stock_level > 0,
                Product.reorder_point > 0,
            ),
        )
    )).all()
    return [
        {
            "product_id": r.id, "sku": r.sku, "name": r.name,
            "min_stock_level": r.min_stock_level,
            "reorder_point": r.reorder_point,
            "reorder_quantity": r.reorder_quantity,
            "auto_reorder": r.auto_reorder,
        }
        for r in rows
    ]


@router.post("/alerts/{alert_id}/resolve", response_model=StockAlertOut)
async def resolve_alert(
    alert_id: str,
    _module: ModuleUser,
    user: Manager,
    db: AsyncSession = Depends(get_db_session),
):
    svc = AlertService(db)
    a = await svc.resolve(alert_id, user["tenant_id"])
    if not a:
        from fastapi import HTTPException
        raise HTTPException(404, "Alert not found")
    return a


@router.post("/alerts/scan")
async def scan_alerts(
    _module: ModuleUser,
    user: Manager,
    db: AsyncSession = Depends(get_db_session),
):
    """Manually trigger stock + expiry alert scan."""
    svc = AlertService(db)
    stock_alerts = await svc.check_and_generate(user["tenant_id"])
    expiry_alerts = await svc.check_expiry_alerts(user["tenant_id"])
    all_alerts = stock_alerts + expiry_alerts
    return {"created": len(all_alerts), "alerts": all_alerts}


@router.get("/kardex/{product_id}", response_model=list[KardexEntry])
async def get_kardex(
    product_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
    warehouse_id: str | None = None,
):
    svc = AlertService(db)
    return await svc.get_kardex(user["tenant_id"], product_id, warehouse_id)
