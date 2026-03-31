"""Production v2 endpoints — runs, emissions, receipts."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ProductionModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas import (
    PaginatedProductionRuns, ProductionRunCreate, ProductionRunOut, ProductionRunUpdate,
    EmissionCreate, EmissionOut,
    ReceiptCreate, ReceiptOut,
    MRPRequest, MRPResult, CapacityResult,
)
from app.services.production_service import ProductionService
from app.services.audit_service import InventoryAuditService

router = APIRouter(prefix="/api/v1/production-runs", tags=["production"])


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


def _svc(db: AsyncSession = Depends(get_db_session)) -> ProductionService:
    return ProductionService(db)


# ── Runs CRUD ────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedProductionRuns)
async def list_runs(
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    status: str | None = None,
    order_type: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    svc: ProductionService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_runs(tenant_id, status, offset, limit)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.post("", response_model=ProductionRunOut, status_code=201)
async def create_run(
    body: ProductionRunCreate,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    performed_by = current_user.get("id")
    run = await svc.create_run(tenant_id, body.model_dump(), performed_by)
    await InventoryAuditService(db).log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.production.create", resource_type="production_run",
        resource_id=run.id, new_data=body.model_dump(mode="json"), ip_address=_ip(request),
    )
    return run


@router.get("/{run_id}", response_model=ProductionRunOut)
async def get_run(
    run_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    svc: ProductionService = Depends(_svc),
):
    return await svc.get_run(current_user.get("tenant_id", "default"), run_id)


@router.patch("/{run_id}", response_model=ProductionRunOut)
async def update_run(
    run_id: str,
    body: ProductionRunUpdate,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    run = await svc.update_run(tenant_id, run_id, body.model_dump(exclude_none=True))
    await InventoryAuditService(db).log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.production.update", resource_type="production_run",
        resource_id=run_id, new_data=body.model_dump(mode="json", exclude_none=True), ip_address=_ip(request),
    )
    return run


@router.delete("/{run_id}", status_code=204)
async def delete_run(
    run_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    tenant_id = current_user.get("tenant_id", "default")
    await svc.delete_run(tenant_id, run_id)
    await InventoryAuditService(db).log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.production.delete", resource_type="production_run",
        resource_id=run_id, ip_address=_ip(request),
    )
    return Response(status_code=204)


# ── Status Transitions ───────────────────────────────────────────────────────

@router.post("/{run_id}/release", response_model=ProductionRunOut)
async def release_run(
    run_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    run = await svc.release_run(tenant_id, run_id, current_user.get("id"))
    await InventoryAuditService(db).log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.production.release", resource_type="production_run",
        resource_id=run_id, new_data={"status": "released"}, ip_address=_ip(request),
    )
    return run


@router.post("/{run_id}/cancel", response_model=ProductionRunOut)
async def cancel_run(
    run_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    run = await svc.cancel_run(tenant_id, run_id)
    await InventoryAuditService(db).log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.production.cancel", resource_type="production_run",
        resource_id=run_id, new_data={"status": "canceled"}, ip_address=_ip(request),
    )
    return run


@router.post("/{run_id}/close", response_model=ProductionRunOut)
async def close_run(
    run_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    run = await svc.close_run(tenant_id, run_id)
    await InventoryAuditService(db).log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.production.close", resource_type="production_run",
        resource_id=run_id, new_data={"status": "closed"}, ip_address=_ip(request),
    )
    return run


# ── Emissions (Material Issue) ───────────────────────────────────────────────

@router.post("/{run_id}/emissions", response_model=EmissionOut, status_code=201)
async def create_emission(
    run_id: str,
    body: EmissionCreate,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    performed_by = current_user.get("id")
    emission = await svc.create_emission(tenant_id, run_id, body.model_dump(), performed_by)
    await InventoryAuditService(db).log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.production.emission", resource_type="production_emission",
        resource_id=emission.id, new_data={"run_id": run_id}, ip_address=_ip(request),
    )
    return emission


@router.get("/{run_id}/emissions", response_model=list[EmissionOut])
async def list_emissions(
    run_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    svc: ProductionService = Depends(_svc),
):
    return await svc.list_emissions(current_user.get("tenant_id", "default"), run_id)


# ── Receipts (Finished Goods) ────────────────────────────────────────────────

@router.post("/{run_id}/receipts", response_model=ReceiptOut, status_code=201)
async def create_receipt(
    run_id: str,
    body: ReceiptCreate,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    performed_by = current_user.get("id")
    receipt = await svc.create_receipt(tenant_id, run_id, body.model_dump(), performed_by)
    await InventoryAuditService(db).log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.production.receipt", resource_type="production_receipt",
        resource_id=receipt.id, new_data={"run_id": run_id}, ip_address=_ip(request),
    )
    return receipt


@router.get("/{run_id}/receipts", response_model=list[ReceiptOut])
async def list_receipts(
    run_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    svc: ProductionService = Depends(_svc),
):
    return await svc.list_receipts(current_user.get("tenant_id", "default"), run_id)


# ── MRP ──────────────────────────────────────────────────────────────────────

@router.post("/mrp/explode", response_model=MRPResult)
async def mrp_explode(
    body: MRPRequest,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("production.manage"))],
    svc: ProductionService = Depends(_svc),
):
    return await svc.mrp_explode(current_user.get("tenant_id", "default"), body.model_dump())


# ── Capacity Check ───────────────────────────────────────────────────────────

@router.post("/{run_id}/check-capacity", response_model=CapacityResult)
async def check_capacity(
    run_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("production.view"))],
    svc: ProductionService = Depends(_svc),
):
    return await svc.check_capacity(current_user.get("tenant_id", "default"), run_id)
