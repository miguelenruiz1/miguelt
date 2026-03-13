"""CSV report download endpoints."""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
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
