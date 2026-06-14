"""WM movement-order endpoints (internal bin->bin documents).

Under /api/v1/wm (gateway route already covers it). User-facing name is
"orden de movimiento de almacén" — NOT transport (that's the logistics module).
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import ORJSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, get_client_ip as _ip, require_permission
from app.core.errors import ConflictError, NotFoundError
from app.db.models import OperationType, TransferOrder
from app.db.session import get_db_session
from app.domain.schemas.wm_transfer import (
    ConfirmLineIn, MovementOrderCreate, MovementOrderLineOut, MovementOrderOut,
    OperationTypeCreate, OperationTypeOut,
)
from app.services.audit_service import InventoryAuditService
from app.services.movement_order_service import MovementOrderService

router = APIRouter(prefix="/api/v1/wm", tags=["wm-movement"])


# ─── Operation Types ──────────────────────────────────────────────────────────

@router.get("/operation-types", response_model=list[OperationTypeOut])
async def list_operation_types(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    items = list((await db.execute(
        select(OperationType).where(OperationType.tenant_id == current_user["tenant_id"])
        .order_by(OperationType.code)
    )).scalars().all())
    return ORJSONResponse([OperationTypeOut.model_validate(i).model_dump(mode="json") for i in items])


@router.post("/operation-types", response_model=OperationTypeOut, status_code=201)
async def create_operation_type(
    body: OperationTypeCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    tenant_id = current_user["tenant_id"]
    dup = (await db.execute(
        select(OperationType).where(
            OperationType.tenant_id == tenant_id, OperationType.code == body.code,
        )
    )).scalar_one_or_none()
    if dup:
        raise ConflictError(f"Operation type {body.code!r} already exists")
    obj = OperationType(id=str(uuid.uuid4()), tenant_id=tenant_id, **body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return ORJSONResponse(OperationTypeOut.model_validate(obj).model_dump(mode="json"), status_code=201)


@router.post("/operation-types/seed", response_model=list[OperationTypeOut], status_code=201)
async def seed_operation_types(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    created = await MovementOrderService(db).seed_operation_types(current_user["tenant_id"])
    await db.commit()
    return ORJSONResponse(
        [OperationTypeOut.model_validate(i).model_dump(mode="json") for i in created], status_code=201,
    )


@router.post("/interim-zones", status_code=201)
async def ensure_interim_zones(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    warehouse_id: str = Query(...),
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    zones = await MovementOrderService(db).ensure_interim_locations(current_user["tenant_id"], warehouse_id)
    await db.commit()
    return ORJSONResponse(
        {"zones": [{"code": c, "location_id": loc.id, "name": loc.name} for c, loc in zones.items()]},
        status_code=201,
    )


# ─── Movement Orders ──────────────────────────────────────────────────────────

def _order_out(order: TransferOrder, lines) -> dict:
    out = MovementOrderOut.model_validate(order)
    out.lines = [MovementOrderLineOut.model_validate(ln) for ln in lines]
    return out.model_dump(mode="json")


@router.get("/movement-orders", response_model=list[MovementOrderOut])
async def list_movement_orders(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    warehouse_id: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    q = select(TransferOrder).where(TransferOrder.tenant_id == current_user["tenant_id"])
    if warehouse_id:
        q = q.where(TransferOrder.warehouse_id == warehouse_id)
    if status:
        q = q.where(TransferOrder.status == status)
    q = q.order_by(TransferOrder.created_at.desc()).limit(200)
    orders = list((await db.execute(q)).scalars().all())
    svc = MovementOrderService(db)
    result = []
    for o in orders:
        lines = await svc.list_lines(current_user["tenant_id"], o.id)
        result.append(_order_out(o, lines))
    return ORJSONResponse(result)


@router.post("/movement-orders", response_model=MovementOrderOut, status_code=201)
async def create_movement_order(
    body: MovementOrderCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    tenant_id = current_user["tenant_id"]
    svc = MovementOrderService(db)
    order = await svc.create_order(tenant_id, body, current_user.get("id"))
    lines = await svc.list_lines(tenant_id, order.id)
    await InventoryAuditService(db).log(
        tenant_id=tenant_id, user=current_user, action="inventory.wm.movement_order.create",
        resource_type="wm_movement_order", resource_id=order.id,
        new_data={"to_number": order.to_number, "lines": len(lines)}, ip_address=_ip(request),
    )
    await db.commit()
    return ORJSONResponse(_order_out(order, lines), status_code=201)


@router.get("/movement-orders/{order_id}", response_model=MovementOrderOut)
async def get_movement_order(
    order_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = MovementOrderService(db)
    order = await svc.get_order(current_user["tenant_id"], order_id)
    if not order:
        raise NotFoundError(f"Movement order {order_id!r} not found")
    lines = await svc.list_lines(current_user["tenant_id"], order_id)
    return ORJSONResponse(_order_out(order, lines))


@router.post("/movement-orders/{order_id}/lines/{line_id}/confirm", response_model=MovementOrderLineOut)
async def confirm_movement_line(
    order_id: str,
    line_id: str,
    body: ConfirmLineIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    line = await MovementOrderService(db).confirm_line(
        current_user["tenant_id"], order_id, line_id, body, current_user.get("id"),
    )
    await db.commit()
    return ORJSONResponse(MovementOrderLineOut.model_validate(line).model_dump(mode="json"))
