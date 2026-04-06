"""Batch tracking endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas import BatchCreate, BatchOut, BatchUpdate, PaginatedBatches
from app.domain.schemas.tracking import (
    BatchSearchResult, TraceForwardOut,
)
from app.services.batch_service import BatchService
from app.services.audit_service import InventoryAuditService

router = APIRouter(prefix="/api/v1/batches", tags=["batches"])


from app.api.deps import get_client_ip as _ip  # noqa: F401


def _svc(db: AsyncSession = Depends(get_db_session)) -> BatchService:
    return BatchService(db)


@router.get("/expiring", response_model=PaginatedBatches)
async def list_expiring_batches(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    days: int = Query(30, ge=1, le=365),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    svc: BatchService = Depends(_svc),
):
    """List active batches expiring within the next N days."""
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_expiring(tenant_id, days, offset=offset, limit=limit)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("", response_model=PaginatedBatches)
async def list_batches(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    entity_id: str | None = None,
    is_active: bool | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    svc: BatchService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list(tenant_id, entity_id, is_active, offset, limit)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.post("", response_model=BatchOut, status_code=201)
async def create_batch(
    body: BatchCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: BatchService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    data = body.model_dump()
    data["created_by"] = current_user.get("id")
    batch = await svc.create(tenant_id, data)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.batch.create", resource_type="batch",
        resource_id=batch.id, new_data=body.model_dump(mode="json"), ip_address=_ip(request),
    )
    return batch


@router.get("/search", response_model=list[BatchSearchResult])
async def search_batches(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    batch_code: str = Query(..., min_length=1),
    product_id: str | None = None,
    svc: BatchService = Depends(_svc),
):
    """Search batches by batch_number with dispatch/SO summary."""
    tenant_id = current_user.get("tenant_id", "default")
    return await svc.search(tenant_id, batch_code, product_id)


@router.get("/{batch_id}/trace-forward", response_model=TraceForwardOut)
async def trace_forward(
    batch_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    svc: BatchService = Depends(_svc),
):
    """Trace forward: batch -> which customers received it."""
    tenant_id = current_user.get("tenant_id", "default")
    return await svc.trace_forward(tenant_id, batch_id)


@router.get("/{batch_id}", response_model=BatchOut)
async def get_batch(
    batch_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    svc: BatchService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    return await svc.get(tenant_id, batch_id)


@router.patch("/{batch_id}", response_model=BatchOut)
async def update_batch(
    batch_id: str,
    body: BatchUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: BatchService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    data = body.model_dump()
    data["updated_by"] = current_user.get("id")
    batch = await svc.update(tenant_id, batch_id, data)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.batch.update", resource_type="batch",
        resource_id=batch_id, new_data=body.model_dump(mode="json"), ip_address=_ip(request),
    )
    return batch


@router.delete("/{batch_id}", status_code=204)
async def delete_batch(
    batch_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: BatchService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete(tenant_id, batch_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.batch.delete", resource_type="batch",
        resource_id=batch_id, ip_address=_ip(request),
    )
    return Response(status_code=204)
