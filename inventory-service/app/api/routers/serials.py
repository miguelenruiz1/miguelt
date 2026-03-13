"""Serial number tracking endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas import PaginatedSerials, SerialCreate, SerialOut, SerialUpdate
from app.services.serial_service import SerialService
from app.services.audit_service import InventoryAuditService

router = APIRouter(prefix="/api/v1/serials", tags=["serials"])


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


def _svc(db: AsyncSession = Depends(get_db_session)) -> SerialService:
    return SerialService(db)


@router.get("", response_model=PaginatedSerials)
async def list_serials(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    entity_id: str | None = None,
    status_id: str | None = None,
    warehouse_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    svc: SerialService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list(tenant_id, entity_id, status_id, warehouse_id, offset, limit)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.post("", response_model=SerialOut, status_code=201)
async def create_serial(
    body: SerialCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: SerialService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    data = body.model_dump()
    data["created_by"] = current_user.get("id")
    serial = await svc.create(tenant_id, data)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.serial.create", resource_type="serial",
        resource_id=serial.id, new_data=body.model_dump(mode="json"), ip_address=_ip(request),
    )
    return serial


@router.get("/{serial_id}", response_model=SerialOut)
async def get_serial(
    serial_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    svc: SerialService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    return await svc.get(tenant_id, serial_id)


@router.patch("/{serial_id}", response_model=SerialOut)
async def update_serial(
    serial_id: str,
    body: SerialUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: SerialService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    data = body.model_dump()
    data["updated_by"] = current_user.get("id")
    serial = await svc.update(tenant_id, serial_id, data)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.serial.update", resource_type="serial",
        resource_id=serial_id, new_data=body.model_dump(mode="json"), ip_address=_ip(request),
    )
    return serial


@router.delete("/{serial_id}", status_code=204)
async def delete_serial(
    serial_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: SerialService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete(tenant_id, serial_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.serial.delete", resource_type="serial",
        resource_id=serial_id, ip_address=_ip(request),
    )
    return Response(status_code=204)
