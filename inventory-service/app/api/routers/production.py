"""Production run endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ProductionModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas import PaginatedProductionRuns, ProductionRunCreate, ProductionRunOut, ProductionRunReject
from app.services.production_service import ProductionService
from app.services.audit_service import InventoryAuditService

router = APIRouter(prefix="/api/v1/production-runs", tags=["production"])


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


def _svc(db: AsyncSession = Depends(get_db_session)) -> ProductionService:
    return ProductionService(db)


@router.get("", response_model=PaginatedProductionRuns)
async def list_runs(
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    status: str | None = None,
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
    audit = InventoryAuditService(db)
    performed_by = current_user.get("id")
    run = await svc.create_run(tenant_id, body.model_dump(), performed_by)
    await audit.log(
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
    tenant_id = current_user.get("tenant_id", "default")
    return await svc.get_run(tenant_id, run_id)


@router.post("/{run_id}/execute", response_model=ProductionRunOut)
async def execute_run(
    run_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    performed_by = current_user.get("id")
    run = await svc.execute_run(tenant_id, run_id, performed_by)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.production.execute", resource_type="production_run",
        resource_id=run_id, new_data={"status": "in_progress"}, ip_address=_ip(request),
    )
    return run


@router.post("/{run_id}/finish", response_model=ProductionRunOut)
async def finish_run(
    run_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    run = await svc.finish_run(tenant_id, run_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.production.finish", resource_type="production_run",
        resource_id=run_id, new_data={"status": "awaiting_approval"}, ip_address=_ip(request),
    )
    return run


@router.post("/{run_id}/approve", response_model=ProductionRunOut)
async def approve_run(
    run_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    approved_by = current_user.get("id")
    run = await svc.approve_run(tenant_id, run_id, approved_by)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.production.approve", resource_type="production_run",
        resource_id=run_id, new_data={"status": "completed", "approved_by": approved_by},
        ip_address=_ip(request),
    )
    return run


@router.post("/{run_id}/reject", response_model=ProductionRunOut)
async def reject_run(
    run_id: str,
    body: ProductionRunReject,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    rejected_by = current_user.get("id")
    run = await svc.reject_run(tenant_id, run_id, body.rejection_notes, rejected_by)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.production.reject", resource_type="production_run",
        resource_id=run_id, new_data={"status": "rejected", "rejection_notes": body.rejection_notes},
        ip_address=_ip(request),
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
    audit = InventoryAuditService(db)
    await svc.delete_run(tenant_id, run_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.production.delete", resource_type="production_run",
        resource_id=run_id, ip_address=_ip(request),
    )
    return Response(status_code=204)
