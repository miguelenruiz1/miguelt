"""Suppliers CRUD endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import ORJSONResponse

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas import PaginatedSuppliers, SupplierCreate, SupplierOut, SupplierUpdate
from app.services.supplier_service import SupplierService
from app.services.audit_service import InventoryAuditService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


@router.get("", response_model=PaginatedSuppliers)
async def list_suppliers(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    is_active: bool | None = True,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> ORJSONResponse:
    svc = SupplierService(db)
    items, total = await svc.list(
        tenant_id=current_user["tenant_id"],
        is_active=is_active,
        offset=offset,
        limit=limit,
    )
    return ORJSONResponse({
        "items": [SupplierOut.model_validate(s).model_dump(mode="json") for s in items],
        "total": total,
        "offset": offset,
        "limit": limit,
    })


@router.post("", response_model=SupplierOut, status_code=201)
async def create_supplier(
    body: SupplierCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = SupplierService(db)
    audit = InventoryAuditService(svc.db)
    data = body.model_dump()
    data["created_by"] = current_user.get("id")
    supplier = await svc.create(current_user["tenant_id"], data)
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.supplier.create", resource_type="supplier",
        resource_id=supplier.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return ORJSONResponse(SupplierOut.model_validate(supplier).model_dump(mode="json"), status_code=201)


@router.get("/{supplier_id}", response_model=SupplierOut)
async def get_supplier(
    supplier_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = SupplierService(db)
    supplier = await svc.get(supplier_id, current_user["tenant_id"])
    return ORJSONResponse(SupplierOut.model_validate(supplier).model_dump(mode="json"))


@router.patch("/{supplier_id}", response_model=SupplierOut)
async def update_supplier(
    supplier_id: str,
    body: SupplierUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = SupplierService(db)
    audit = InventoryAuditService(svc.db)
    old = await svc.get(supplier_id, current_user["tenant_id"])
    old_data = SupplierOut.model_validate(old).model_dump(mode="json")
    update_data = body.model_dump(exclude_none=True)
    update_data["updated_by"] = current_user.get("id")
    supplier = await svc.update(supplier_id, current_user["tenant_id"], update_data)
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.supplier.update", resource_type="supplier",
        resource_id=supplier.id, old_data=old_data,
        new_data=body.model_dump(exclude_none=True), ip_address=_ip(request),
    )
    return ORJSONResponse(SupplierOut.model_validate(supplier).model_dump(mode="json"))


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(
    supplier_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    svc = SupplierService(db)
    audit = InventoryAuditService(svc.db)
    await svc.delete(supplier_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.supplier.delete", resource_type="supplier",
        resource_id=supplier_id, ip_address=_ip(request),
    )
    await svc.db.commit()
    return Response(status_code=204)
