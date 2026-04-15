"""Goods Receipt Note (GRN) endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission, get_client_ip as _ip
from app.db.session import get_db_session
from app.domain.schemas.goods_receipt import GRNCreate, GRNOut
from app.services.grn_service import GRNService
from app.services.audit_service import InventoryAuditService


router = APIRouter(tags=["goods-receipts"])


@router.post("/api/v1/purchase-orders/{po_id}/receipts", response_model=GRNOut, status_code=201)
async def create_grn(
    po_id: str,
    body: GRNCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.receive"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = GRNService(db)
    audit = InventoryAuditService(db)
    grn = await svc.create_grn(
        tenant_id=current_user["tenant_id"],
        po_id=po_id,
        receipt_date=body.receipt_date,
        notes=body.notes,
        attachments=body.attachments,
        lines=[ln.model_dump() for ln in body.lines],
        performed_by=current_user.get("id"),
    )
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.grn.create", resource_type="goods_receipt",
        resource_id=grn.id,
        new_data={"grn_number": grn.grn_number, "po_id": po_id, "has_discrepancy": grn.has_discrepancy},
        ip_address=_ip(request),
    )
    grn = await svc.get_grn(current_user["tenant_id"], grn.id)
    return ORJSONResponse(GRNOut.model_validate(grn).model_dump(mode="json"))


@router.get("/api/v1/purchase-orders/{po_id}/receipts", response_model=list[GRNOut])
async def list_grns_for_po(
    po_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = GRNService(db)
    items = await svc.list_for_po(current_user["tenant_id"], po_id)
    return ORJSONResponse([GRNOut.model_validate(g).model_dump(mode="json") for g in items])


@router.get("/api/v1/goods-receipts/{grn_id}", response_model=GRNOut)
async def get_grn(
    grn_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = GRNService(db)
    grn = await svc.get_grn(current_user["tenant_id"], grn_id)
    return ORJSONResponse(GRNOut.model_validate(grn).model_dump(mode="json"))
