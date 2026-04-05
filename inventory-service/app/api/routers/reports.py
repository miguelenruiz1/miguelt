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
    from datetime import datetime as _dt, timezone as _tz
    from app.services.pnl_service import PnLService
    from app.core.settings import get_settings
    import httpx

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

    # 3. Call ai-service (forward user's Bearer token)
    auth_header = request.headers.get("authorization", "")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.AI_SERVICE_URL}/api/v1/analyze/pnl",
                json={
                    "tenant_id": tenant_id,
                    "date_from": str(date_from or "2020-01-01"),
                    "date_to": str(date_to or _dt.now(_tz.utc).date()),
                    "force": force,
                    "pnl_data": pnl,
                    "business_context": biz_context,
                },
                headers={"Authorization": auth_header} if auth_header else {},
            )
        if resp.status_code == 200:
            return resp.json()
        # Forward error from ai-service
        err = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        raise HTTPException(status_code=resp.status_code, detail=err.get("error", err.get("detail", f"AI service error: {resp.status_code}")))
    except httpx.RequestError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error": "ai_unavailable", "message": f"AI service unreachable: {str(exc)}"})
