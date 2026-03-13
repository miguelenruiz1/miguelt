"""Warehouses CRUD endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import ORJSONResponse

from app.api.deps import ModuleUser, require_permission
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.session import get_db_session
from app.domain.schemas import WarehouseCreate, WarehouseOut, WarehouseUpdate
from app.domain.schemas.pagination import PaginatedWarehouses
from app.repositories.warehouse_repo import WarehouseRepository
from app.services.audit_service import InventoryAuditService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/warehouses", tags=["warehouses"])


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


@router.get("", response_model=PaginatedWarehouses)
async def list_warehouses(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    is_active: bool | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
) -> ORJSONResponse:
    repo = WarehouseRepository(db)
    items, total = await repo.list(current_user["tenant_id"], is_active=is_active, offset=offset, limit=limit)
    return ORJSONResponse(PaginatedWarehouses(items=items, total=total, offset=offset, limit=limit).model_dump(mode="json"))


@router.post("", response_model=WarehouseOut, status_code=201)
async def create_warehouse(
    body: WarehouseCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    tenant_id = current_user["tenant_id"]
    repo = WarehouseRepository(db)
    audit = InventoryAuditService(db)
    if await repo.get_by_code(body.code, tenant_id):
        raise ConflictError(f"Warehouse code {body.code!r} already exists")
    data = {"tenant_id": tenant_id, **body.model_dump(), "created_by": current_user.get("id")}
    wh = await repo.create(data)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.warehouse.create", resource_type="warehouse",
        resource_id=wh.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return ORJSONResponse(WarehouseOut.model_validate(wh).model_dump(mode="json"), status_code=201)


@router.get("/{warehouse_id}", response_model=WarehouseOut)
async def get_warehouse(
    warehouse_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    repo = WarehouseRepository(db)
    wh = await repo.get_by_id(warehouse_id, current_user["tenant_id"])
    if not wh:
        raise NotFoundError(f"Warehouse {warehouse_id!r} not found")
    return ORJSONResponse(WarehouseOut.model_validate(wh).model_dump(mode="json"))


@router.patch("/{warehouse_id}", response_model=WarehouseOut)
async def update_warehouse(
    warehouse_id: str,
    body: WarehouseUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    tenant_id = current_user["tenant_id"]
    repo = WarehouseRepository(db)
    audit = InventoryAuditService(db)
    wh = await repo.get_by_id(warehouse_id, tenant_id)
    if not wh:
        raise NotFoundError(f"Warehouse {warehouse_id!r} not found")
    old_data = WarehouseOut.model_validate(wh).model_dump(mode="json")
    if body.code and body.code != wh.code:
        if await repo.get_by_code(body.code, tenant_id):
            raise ConflictError(f"Warehouse code {body.code!r} already exists")
    update_data = body.model_dump(exclude_none=True)
    update_data["updated_by"] = current_user.get("id")
    wh = await repo.update(wh, update_data)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.warehouse.update", resource_type="warehouse",
        resource_id=wh.id, old_data=old_data,
        new_data=body.model_dump(exclude_none=True), ip_address=_ip(request),
    )
    return ORJSONResponse(WarehouseOut.model_validate(wh).model_dump(mode="json"))


@router.delete("/{warehouse_id}", status_code=204)
async def delete_warehouse(
    warehouse_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    tenant_id = current_user["tenant_id"]
    repo = WarehouseRepository(db)
    audit = InventoryAuditService(db)
    wh = await repo.get_by_id(warehouse_id, tenant_id)
    if not wh:
        raise NotFoundError(f"Warehouse {warehouse_id!r} not found")
    active_runs = await repo.count_active_production_runs(warehouse_id, tenant_id)
    if active_runs:
        raise ValidationError(
            f"No se puede eliminar: la bodega tiene {active_runs} orden(es) de producción activa(s)"
        )
    await repo.soft_delete(wh)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.warehouse.delete", resource_type="warehouse",
        resource_id=warehouse_id, ip_address=_ip(request),
    )
    return Response(status_code=204)
