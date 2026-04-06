"""CSV report download endpoints + AI analysis."""
from __future__ import annotations

from datetime import date
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, get_redis, require_permission
from app.db.session import get_db_session
from app.services.reports_service import ReportsService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _svc(db: AsyncSession = Depends(get_db_session)) -> ReportsService:
    return ReportsService(db)


@router.get("/products")
async def download_products(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.products_csv(tenant_id)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=productos.csv"},
    )


@router.get("/stock")
async def download_stock(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.stock_csv(tenant_id)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=stock.csv"},
    )


@router.get("/suppliers")
async def download_suppliers(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.suppliers_csv(tenant_id)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=proveedores.csv"},
    )


@router.get("/movements")
async def download_movements(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    date_from: date | None = None,
    date_to: date | None = None,
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.movements_csv(tenant_id, date_from, date_to)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=movimientos.csv"},
    )


@router.get("/events")
async def download_events(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    date_from: date | None = None,
    date_to: date | None = None,
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.events_csv(tenant_id, date_from, date_to)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=eventos.csv"},
    )


@router.get("/serials")
async def download_serials(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.serials_csv(tenant_id)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=seriales.csv"},
    )


@router.get("/batches")
async def download_batches(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.batches_csv(tenant_id)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=lotes.csv"},
    )


@router.get("/purchase-orders")
async def download_purchase_orders(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    date_from: date | None = None,
    date_to: date | None = None,
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.purchase_orders_csv(tenant_id, date_from, date_to)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=ordenes-compra.csv"},
    )


@router.get("/pnl")
async def get_pnl_report(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    date_from: date | None = None,
    date_to: date | None = None,
    product_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    from datetime import datetime as _dt, timezone as _tz
    from app.services.pnl_service import PnLService
    tenant_id = current_user.get("tenant_id", "default")
    svc = PnLService(db)
    dt_from = _dt.combine(date_from, _dt.min.time()).replace(tzinfo=_tz.utc) if date_from else _dt(2020, 1, 1, tzinfo=_tz.utc)
    dt_to = _dt.combine(date_to, _dt.max.time()).replace(tzinfo=_tz.utc) if date_to else _dt.now(_tz.utc)
    if product_id:
        return await svc.get_product_pnl(product_id, tenant_id, dt_from, dt_to)
    return await svc.get_full_pnl(tenant_id, dt_from, dt_to)


@router.get("/pnl/pdf")
async def download_pnl_pdf(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    from datetime import datetime as _dt, timezone as _tz
    from fastapi.responses import Response
    from app.services.pnl_service import PnLService
    from app.services.pdf_report_service import generate_pnl_pdf
    tenant_id = current_user.get("tenant_id", "default")
    svc = PnLService(db)
    dt_from = _dt.combine(date_from, _dt.min.time()).replace(tzinfo=_tz.utc) if date_from else _dt(2020, 1, 1, tzinfo=_tz.utc)
    dt_to = _dt.combine(date_to, _dt.max.time()).replace(tzinfo=_tz.utc) if date_to else _dt.now(_tz.utc)
    pnl = await svc.get_full_pnl(tenant_id, dt_from, dt_to)
    pdf_bytes = generate_pnl_pdf(pnl, tenant_name="TraceLog")
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=pnl_report.pdf"})


@router.get("/pnl/analysis")
async def get_pnl_ai_analysis(
    request: Request,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    date_from: date | None = None,
    date_to: date | None = None,
    force: bool = Query(False, description="Skip cache and regenerate"),
    db: AsyncSession = Depends(get_db_session),
):
    """Proxy to ai-service for P&L analysis."""
    import json as _json
    from datetime import datetime as _dt, timezone as _tz
    from app.services.pnl_service import PnLService
    from app.core.settings import get_settings
    import httpx

    from decimal import Decimal as _Decimal
    from uuid import UUID as _UUID

    def _default(o: object):
        if isinstance(o, (_dt, date)):
            return o.isoformat()
        if isinstance(o, _Decimal):
            return float(o)
        if isinstance(o, _UUID):
            return str(o)
        raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")

    tenant_id = current_user.get("tenant_id", "default")
    settings = get_settings()

    # 1. Get PnL data from local DB
    svc = PnLService(db)
    dt_from = _dt.combine(date_from, _dt.min.time()).replace(tzinfo=_tz.utc) if date_from else _dt(2020, 1, 1, tzinfo=_tz.utc)
    dt_to = _dt.combine(date_to, _dt.max.time()).replace(tzinfo=_tz.utc) if date_to else _dt.now(_tz.utc)
    pnl = await svc.get_full_pnl(tenant_id, dt_from, dt_to)

    # 2. Get business context from local DB
    from app.db.models.category import Category
    from app.db.models.config import ProductType
    from app.db.models.warehouse import Warehouse
    from app.db.models.partner import BusinessPartner as Partner
    from sqlalchemy import select as sa_select

    categories = [r[0] for r in (await db.execute(sa_select(Category.name).where(Category.tenant_id == tenant_id).limit(20))).all()]
    product_types = [r[0] for r in (await db.execute(sa_select(ProductType.name).where(ProductType.tenant_id == tenant_id).limit(10))).all()]
    warehouses = [r[0] for r in (await db.execute(sa_select(Warehouse.name).where(Warehouse.tenant_id == tenant_id).limit(10))).all()]
    try:
        suppliers = [r[0] for r in (await db.execute(sa_select(Partner.name).where(Partner.tenant_id == tenant_id, Partner.is_supplier == True, Partner.is_active == True).limit(15))).all()]  # noqa: E712
    except Exception:
        suppliers = []

    # Enrich products with category/type names
    from app.db.models import Product
    cat_map = {r[0]: (r[1] or "") for r in (await db.execute(sa_select(Product.id, Category.name).outerjoin(Category, Product.category_id == Category.id).where(Product.tenant_id == tenant_id))).all()}
    type_map = {r[0]: (r[1] or "") for r in (await db.execute(sa_select(Product.id, ProductType.name).outerjoin(ProductType, Product.product_type_id == ProductType.id).where(Product.tenant_id == tenant_id))).all()}

    for p in pnl.get("products", []):
        pid = p.get("product_id", "")
        p["categoria"] = cat_map.get(pid, "")
        p["tipo"] = type_map.get(pid, "")

    biz_context = {
        "empresa": tenant_id,
        "categorias_productos": categories,
        "tipos_producto": product_types,
        "bodegas": warehouses,
        "proveedores_activos": suppliers,
    }

    # 2b. Enrich with inventory intelligence for AI
    from app.db.models.stock import StockMovement, StockLevel
    from sqlalchemy import func as sa_func, and_

    # Stock alerts: products below min_stock or reorder_point
    low_stock = []
    try:
        low_q = await db.execute(
            sa_select(Product.sku, Product.name, Product.min_stock_level, Product.reorder_point,
                      sa_func.coalesce(sa_func.sum(StockLevel.qty_on_hand), 0).label("qty"))
            .outerjoin(StockLevel, and_(StockLevel.product_id == Product.id, StockLevel.tenant_id == tenant_id))
            .where(Product.tenant_id == tenant_id, Product.is_active == True)  # noqa: E712
            .group_by(Product.id)
            .having(sa_func.coalesce(sa_func.sum(StockLevel.qty_on_hand), 0) <= Product.reorder_point)
            .limit(10)
        )
        for r in low_q.all():
            low_stock.append({"sku": r.sku, "nombre": r.name, "stock": float(r.qty), "minimo": r.min_stock_level, "reorden": r.reorder_point})
    except Exception:
        pass
    biz_context["alertas_stock_bajo"] = low_stock

    # Cost variations: products where last purchase cost differs > 30% from previous
    cost_variations = []
    try:
        from app.db.models.cost_history import ProductCostHistory
        cost_q = await db.execute(
            sa_select(Product.sku, Product.name, ProductCostHistory.unit_cost_base_uom, ProductCostHistory.supplier_name, ProductCostHistory.received_at)
            .join(Product, ProductCostHistory.product_id == Product.id)
            .where(ProductCostHistory.tenant_id == tenant_id, ProductCostHistory.received_at >= dt_from)
            .order_by(ProductCostHistory.received_at.desc())
            .limit(30)
        )
        cost_by_product = {}
        for r in cost_q.all():
            if r.sku not in cost_by_product:
                cost_by_product[r.sku] = []
            cost_by_product[r.sku].append({"costo": float(r.unit_cost_base_uom or 0), "proveedor": r.supplier_name, "fecha": str(r.received_at.date()) if r.received_at else ""})
        for sku, costs in cost_by_product.items():
            if len(costs) >= 2:
                latest = costs[0]["costo"]
                previous = costs[1]["costo"]
                if previous > 0:
                    variation = abs(latest - previous) / previous * 100
                    if variation > 30:
                        cost_variations.append({"sku": sku, "costo_actual": latest, "costo_anterior": previous, "variacion_pct": round(variation, 1), "proveedor": costs[0]["proveedor"]})
    except Exception:
        pass
    biz_context["variaciones_costo_compra"] = cost_variations

    # Recent movements summary (last 7 days)
    recent_movements = []
    try:
        seven_days_ago = _dt.now(_tz.utc) - _dt.resolution * 7 * 24 * 3600 * 1_000_000
        mov_q = await db.execute(
            sa_select(StockMovement.movement_type, sa_func.count().label("qty"), sa_func.sum(StockMovement.cost_total).label("valor"))
            .where(StockMovement.tenant_id == tenant_id, StockMovement.created_at >= dt_from)
            .group_by(StockMovement.movement_type)
        )
        for r in mov_q.all():
            recent_movements.append({"tipo": str(r.movement_type), "cantidad": r.qty, "valor_total": float(r.valor or 0)})
    except Exception:
        pass
    biz_context["resumen_movimientos"] = recent_movements

    # Products with negative margin in period
    productos_margen_negativo = []
    for p in pnl.get("products", []):
        s = p.get("summary", {})
        margin = s.get("gross_margin_pct", 0)
        if margin is not None and margin < 0:
            productos_margen_negativo.append({"sku": p.get("product_sku"), "nombre": p.get("product_name"), "margen": round(margin, 1), "perdida": round(s.get("gross_profit", 0), 0)})
    biz_context["productos_margen_negativo"] = productos_margen_negativo

    # 3. Call ai-service (forward user's Bearer token)
    auth_header = request.headers.get("authorization", "")
    try:
        payload = _json.dumps({
            "tenant_id": tenant_id,
            "date_from": str(date_from or "2020-01-01"),
            "date_to": str(date_to or _dt.now(_tz.utc).date()),
            "force": force,
            "pnl_data": pnl,
            "business_context": biz_context,
        }, default=_default, ensure_ascii=False)
        hdrs: dict[str, str] = {"Content-Type": "application/json"}
        if auth_header:
            hdrs["Authorization"] = auth_header
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.AI_SERVICE_URL}/api/v1/analyze/pnl",
                content=payload,
                headers=hdrs,
            )
        if resp.status_code == 200:
            return resp.json()
        # Forward error from ai-service
        err = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        raise HTTPException(status_code=resp.status_code, detail=err.get("error", err.get("detail", f"AI service error: {resp.status_code}")))
    except httpx.RequestError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error": "ai_unavailable", "message": f"AI service unreachable: {str(exc)}"})
