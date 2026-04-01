"""Unified Business Partners CRUD — suppliers + customers in one entity."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.partner import PartnerCreate, PartnerUpdate, PartnerOut, PaginatedPartners
from app.services.partner_service import PartnerService
from app.services.audit_service import InventoryAuditService

router = APIRouter(prefix="/api/v1/partners", tags=["partners"])


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


@router.get("", response_model=PaginatedPartners)
async def list_partners(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    is_supplier: bool | None = None,
    is_customer: bool | None = None,
    is_active: bool | None = True,
    search: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    svc = PartnerService(db)
    items, total = await svc.list(
        current_user["tenant_id"],
        is_supplier=is_supplier, is_customer=is_customer,
        is_active=is_active, search=search,
        offset=offset, limit=limit,
    )
    return ORJSONResponse({
        "items": [PartnerOut.model_validate(p).model_dump(mode="json") for p in items],
        "total": total, "offset": offset, "limit": limit,
    })


@router.post("", response_model=PartnerOut, status_code=201)
async def create_partner(
    body: PartnerCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = PartnerService(db)
    audit = InventoryAuditService(svc.db)
    data = body.model_dump()
    data["created_by"] = current_user.get("id")
    partner = await svc.create(current_user["tenant_id"], data)
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.partner.create", resource_type="partner",
        resource_id=partner.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return ORJSONResponse(PartnerOut.model_validate(partner).model_dump(mode="json"), status_code=201)


@router.get("/{partner_id}", response_model=PartnerOut)
async def get_partner(
    partner_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
):
    svc = PartnerService(db)
    partner = await svc.get(partner_id, current_user["tenant_id"])
    return ORJSONResponse(PartnerOut.model_validate(partner).model_dump(mode="json"))


@router.patch("/{partner_id}", response_model=PartnerOut)
async def update_partner(
    partner_id: str,
    body: PartnerUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = PartnerService(db)
    audit = InventoryAuditService(svc.db)
    update_data = body.model_dump(exclude_none=True)
    update_data["updated_by"] = current_user.get("id")
    partner = await svc.update(partner_id, current_user["tenant_id"], update_data)
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.partner.update", resource_type="partner",
        resource_id=partner.id, new_data=body.model_dump(exclude_none=True), ip_address=_ip(request),
    )
    return ORJSONResponse(PartnerOut.model_validate(partner).model_dump(mode="json"))


@router.delete("/{partner_id}", status_code=204)
async def delete_partner(
    partner_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = PartnerService(db)
    audit = InventoryAuditService(svc.db)
    await svc.delete(partner_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.partner.delete", resource_type="partner",
        resource_id=partner_id, ip_address=_ip(request),
    )
    await svc.db.commit()
    from fastapi import Response
    return Response(status_code=204)
