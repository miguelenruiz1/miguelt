"""Stock level queries and movement operations."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import ORJSONResponse

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas import (
    AdjustStockIn,
    AdjustInStockIn,
    AdjustOutStockIn,
    AssignLocationIn,
    IssueStockIn,
    PaginatedStockLevels,
    QCActionIn,
    ReceiveStockIn,
    ReturnStockIn,
    StockLevelOut,
    StockMovementOut,
    TransferStockIn,
    WasteStockIn,
)
from app.db.models.stock import StockReservation
from app.repositories.stock_repo import StockRepository
from app.services.stock_service import StockService
from app.services.audit_service import InventoryAuditService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/stock", tags=["stock"])


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


@router.get("", response_model=PaginatedStockLevels)
async def list_stock(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    product_id: str | None = None,
    warehouse_id: str | None = None,
    variant_id: str | None = None,
    location_id: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> ORJSONResponse:
    repo = StockRepository(db)
    levels, total = await repo.list_levels(
        tenant_id=current_user["tenant_id"],
        product_id=product_id,
        warehouse_id=warehouse_id,
        variant_id=variant_id,
        location_id=location_id,
        offset=offset,
        limit=limit,
    )
    return ORJSONResponse(PaginatedStockLevels(
        items=[StockLevelOut.model_validate(sl) for sl in levels],
        total=total,
        offset=offset,
        limit=limit,
    ).model_dump(mode="json"))


@router.get("/availability/{product_id}")
async def get_stock_availability(
    product_id: str,
    warehouse_id: str | None = Query(None),
    current_user: ModuleUser = ...,
    db: AsyncSession = Depends(get_db_session),
):
    """Get stock availability for a product: on_hand, reserved, available, in_transit."""
    tenant_id = current_user.get("tenant_id", "default")
    repo = StockRepository(db)
    result = await repo.get_available_stock(tenant_id, product_id, warehouse_id)
    return ORJSONResponse(content=result)


@router.get("/reservations")
async def list_reservations(
    product_id: str | None = Query(None),
    status: str | None = Query("active"),
    current_user: ModuleUser = ...,
    db: AsyncSession = Depends(get_db_session),
):
    """List stock reservations, optionally filtered by product and status."""
    tenant_id = current_user.get("tenant_id", "default")
    q = select(StockReservation).where(StockReservation.tenant_id == tenant_id)
    if product_id:
        q = q.where(StockReservation.product_id == product_id)
    if status:
        q = q.where(StockReservation.status == status)
    q = q.order_by(StockReservation.reserved_at.desc()).limit(100)
    rows = (await db.execute(q)).scalars().all()
    return ORJSONResponse(content=[{
        "id": r.id,
        "sales_order_id": r.sales_order_id,
        "product_id": r.product_id,
        "warehouse_id": r.warehouse_id,
        "quantity": float(r.quantity),
        "status": r.status,
        "reserved_at": r.reserved_at.isoformat() if r.reserved_at else None,
    } for r in rows])


@router.patch("/levels/{level_id}/location", response_model=StockLevelOut)
async def assign_stock_location(
    level_id: str,
    body: AssignLocationIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    repo = StockRepository(db)
    audit = InventoryAuditService(db)
    level = await repo.assign_location(level_id, current_user["tenant_id"], body.location_id)
    if not level:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Stock level not found")
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.stock.assign_location", resource_type="stock",
        resource_id=level.id,
        new_data={"location_id": body.location_id},
        ip_address=_ip(request),
    )
    return ORJSONResponse(StockLevelOut.model_validate(level).model_dump(mode="json"))


@router.post("/relocate", response_model=StockMovementOut, status_code=201)
async def relocate_within_warehouse(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    product_id: str = Query(...),
    warehouse_id: str = Query(...),
    from_location_id: str = Query(...),
    to_location_id: str = Query(...),
    quantity: str = Query(...),
    variant_id: str | None = Query(None),
    notes: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    """Move stock between locations within the same warehouse. Creates a transfer movement."""
    from decimal import Decimal as D
    tenant_id = current_user.get("tenant_id", "default")
    svc = StockService(db)

    # Issue from source location
    from app.db.models.stock import StockLevel
    from sqlalchemy import select
    source_level = (await db.execute(
        select(StockLevel).where(
            StockLevel.product_id == product_id,
            StockLevel.warehouse_id == warehouse_id,
            StockLevel.location_id == from_location_id,
            StockLevel.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not source_level or float(source_level.qty_on_hand) < float(quantity):
        from app.core.errors import ValidationError
        raise ValidationError(f"Stock insuficiente en ubicacion origen: {float(source_level.qty_on_hand) if source_level else 0} disponible, {quantity} requerido")

    qty = D(quantity)
    source_level.qty_on_hand -= qty
    await db.flush()

    # Upsert destination location
    dest_level = (await db.execute(
        select(StockLevel).where(
            StockLevel.product_id == product_id,
            StockLevel.warehouse_id == warehouse_id,
            StockLevel.location_id == to_location_id,
            StockLevel.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if dest_level:
        dest_level.qty_on_hand += qty
    else:
        import uuid
        from app.db.models.stock import StockLevel as SL
        dest_level = SL(id=str(uuid.uuid4()), tenant_id=tenant_id, product_id=product_id, warehouse_id=warehouse_id,
                        location_id=to_location_id, qty_on_hand=qty, variant_id=variant_id)
        db.add(dest_level)
    await db.flush()

    # Create movement record
    from app.db.models.enums import MovementType
    movement = await svc.movement_repo.create({
        "tenant_id": tenant_id, "movement_type": MovementType.transfer,
        "product_id": product_id, "from_warehouse_id": warehouse_id, "to_warehouse_id": warehouse_id,
        "quantity": qty, "reference": f"RELOCATE:{from_location_id}->{to_location_id}",
        "notes": notes, "performed_by": current_user.get("id"), "variant_id": variant_id,
    })

    audit = InventoryAuditService(db)
    await audit.log(tenant_id=tenant_id, user=current_user, action="inventory.stock.relocate",
                    resource_type="stock", resource_id=movement.id,
                    new_data={"from_location": from_location_id, "to_location": to_location_id, "qty": str(qty)},
                    ip_address=_ip(request))

    return ORJSONResponse(StockMovementOut.model_validate(movement).model_dump(mode="json"))


@router.post("/receive", response_model=StockMovementOut, status_code=201)
async def receive_stock(
    body: ReceiveStockIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = StockService(db)
    audit = InventoryAuditService(db)
    movement = await svc.receive(
        tenant_id=current_user["tenant_id"],
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        quantity=body.quantity,
        unit_cost=body.unit_cost,
        reference=body.reference,
        notes=body.notes,
        batch_number=body.batch_number,
        performed_by=current_user.get("id"),
        variant_id=body.variant_id,
        location_id=body.location_id,
        uom=body.uom,
    )
    product_name = await svc.resolve_product_name(body.product_id, current_user["tenant_id"])
    warehouse_name = await svc.resolve_warehouse_name(body.warehouse_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.stock.receive", resource_type="stock",
        resource_id=movement.id,
        new_data={**body.model_dump(mode="json"), "product_name": product_name, "warehouse_name": warehouse_name},
        ip_address=_ip(request),
    )
    return ORJSONResponse(StockMovementOut.model_validate(movement).model_dump(mode="json"), status_code=201)


@router.post("/issue", response_model=StockMovementOut, status_code=201)
async def issue_stock(
    body: IssueStockIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = StockService(db)
    audit = InventoryAuditService(db)
    movement = await svc.issue(
        tenant_id=current_user["tenant_id"],
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        quantity=body.quantity,
        reference=body.reference,
        notes=body.notes,
        performed_by=current_user.get("id"),
        variant_id=body.variant_id,
        uom=body.uom,
    )
    product_name = await svc.resolve_product_name(body.product_id, current_user["tenant_id"])
    warehouse_name = await svc.resolve_warehouse_name(body.warehouse_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.stock.issue", resource_type="stock",
        resource_id=movement.id,
        new_data={**body.model_dump(mode="json"), "product_name": product_name, "warehouse_name": warehouse_name},
        ip_address=_ip(request),
    )
    return ORJSONResponse(StockMovementOut.model_validate(movement).model_dump(mode="json"), status_code=201)


@router.post("/transfer", response_model=StockMovementOut, status_code=201)
async def transfer_stock(
    body: TransferStockIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = StockService(db)
    audit = InventoryAuditService(db)
    movement = await svc.transfer(
        tenant_id=current_user["tenant_id"],
        product_id=body.product_id,
        from_warehouse_id=body.from_warehouse_id,
        to_warehouse_id=body.to_warehouse_id,
        quantity=body.quantity,
        notes=body.notes,
        performed_by=current_user.get("id"),
        variant_id=body.variant_id,
        uom=body.uom,
        from_location_id=body.from_location_id,
        to_location_id=body.to_location_id,
    )
    product_name = await svc.resolve_product_name(body.product_id, current_user["tenant_id"])
    from_wh_name = await svc.resolve_warehouse_name(body.from_warehouse_id, current_user["tenant_id"])
    to_wh_name = await svc.resolve_warehouse_name(body.to_warehouse_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.stock.transfer", resource_type="stock",
        resource_id=movement.id,
        new_data={
            **body.model_dump(mode="json"),
            "product_name": product_name,
            "from_warehouse_name": from_wh_name,
            "to_warehouse_name": to_wh_name,
        },
        ip_address=_ip(request),
    )
    return ORJSONResponse(StockMovementOut.model_validate(movement).model_dump(mode="json"), status_code=201)


@router.post("/transfer/initiate", response_model=StockMovementOut, status_code=201)
async def initiate_transfer(
    body: TransferStockIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = StockService(db)
    audit = InventoryAuditService(db)
    movement = await svc.initiate_transfer(
        tenant_id=current_user["tenant_id"],
        product_id=body.product_id,
        from_warehouse_id=body.from_warehouse_id,
        to_warehouse_id=body.to_warehouse_id,
        quantity=body.quantity,
        notes=body.notes,
        performed_by=current_user.get("id"),
        variant_id=body.variant_id,
        uom=body.uom,
    )
    product_name = await svc.resolve_product_name(body.product_id, current_user["tenant_id"])
    from_wh_name = await svc.resolve_warehouse_name(body.from_warehouse_id, current_user["tenant_id"])
    to_wh_name = await svc.resolve_warehouse_name(body.to_warehouse_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.stock.transfer_initiate", resource_type="stock",
        resource_id=movement.id,
        new_data={
            **body.model_dump(mode="json"),
            "product_name": product_name,
            "from_warehouse_name": from_wh_name,
            "to_warehouse_name": to_wh_name,
        },
        ip_address=_ip(request),
    )
    return ORJSONResponse(StockMovementOut.model_validate(movement).model_dump(mode="json"), status_code=201)


@router.post("/transfer/{movement_id}/complete", response_model=StockMovementOut)
async def complete_transfer(
    movement_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = StockService(db)
    audit = InventoryAuditService(db)
    movement = await svc.complete_transfer(
        tenant_id=current_user["tenant_id"],
        movement_id=movement_id,
    )
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.stock.transfer_complete", resource_type="stock",
        resource_id=movement.id,
        new_data={"movement_id": movement_id},
        ip_address=_ip(request),
    )
    return ORJSONResponse(StockMovementOut.model_validate(movement).model_dump(mode="json"))


@router.post("/adjust", response_model=StockMovementOut, status_code=201)
async def adjust_stock(
    body: AdjustStockIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = StockService(db)
    audit = InventoryAuditService(db)
    movement = await svc.adjust(
        tenant_id=current_user["tenant_id"],
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        new_qty=body.new_qty,
        reason=body.reason,
        performed_by=current_user.get("id"),
        variant_id=body.variant_id,
    )
    product_name = await svc.resolve_product_name(body.product_id, current_user["tenant_id"])
    warehouse_name = await svc.resolve_warehouse_name(body.warehouse_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.stock.adjust", resource_type="stock",
        resource_id=movement.id,
        new_data={**body.model_dump(mode="json"), "product_name": product_name, "warehouse_name": warehouse_name},
        ip_address=_ip(request),
    )
    return ORJSONResponse(StockMovementOut.model_validate(movement).model_dump(mode="json"), status_code=201)


@router.post("/adjust-in", response_model=StockMovementOut, status_code=201)
async def adjust_in_stock(
    body: AdjustInStockIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = StockService(db)
    audit = InventoryAuditService(db)
    movement = await svc.adjust_in(
        tenant_id=current_user["tenant_id"],
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        quantity=body.quantity,
        reason=body.reason,
        performed_by=current_user.get("id"),
        variant_id=body.variant_id,
        unit_cost=body.unit_cost,
        uom=body.uom,
    )
    product_name = await svc.resolve_product_name(body.product_id, current_user["tenant_id"])
    warehouse_name = await svc.resolve_warehouse_name(body.warehouse_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.stock.adjust_in", resource_type="stock",
        resource_id=movement.id,
        new_data={**body.model_dump(mode="json"), "product_name": product_name, "warehouse_name": warehouse_name},
        ip_address=_ip(request),
    )
    return ORJSONResponse(StockMovementOut.model_validate(movement).model_dump(mode="json"), status_code=201)


@router.post("/adjust-out", response_model=StockMovementOut, status_code=201)
async def adjust_out_stock(
    body: AdjustOutStockIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = StockService(db)
    audit = InventoryAuditService(db)
    movement = await svc.adjust_out(
        tenant_id=current_user["tenant_id"],
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        quantity=body.quantity,
        reason=body.reason,
        performed_by=current_user.get("id"),
        variant_id=body.variant_id,
        uom=body.uom,
    )
    product_name = await svc.resolve_product_name(body.product_id, current_user["tenant_id"])
    warehouse_name = await svc.resolve_warehouse_name(body.warehouse_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.stock.adjust_out", resource_type="stock",
        resource_id=movement.id,
        new_data={**body.model_dump(mode="json"), "product_name": product_name, "warehouse_name": warehouse_name},
        ip_address=_ip(request),
    )
    return ORJSONResponse(StockMovementOut.model_validate(movement).model_dump(mode="json"), status_code=201)


@router.post("/return", response_model=StockMovementOut, status_code=201)
async def return_stock(
    body: ReturnStockIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = StockService(db)
    audit = InventoryAuditService(db)
    movement = await svc.return_stock(
        tenant_id=current_user["tenant_id"],
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        quantity=body.quantity,
        reference=body.reference,
        notes=body.notes,
        performed_by=current_user.get("id"),
        variant_id=body.variant_id,
        unit_cost=body.unit_cost,
        uom=body.uom,
    )
    product_name = await svc.resolve_product_name(body.product_id, current_user["tenant_id"])
    warehouse_name = await svc.resolve_warehouse_name(body.warehouse_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.stock.return", resource_type="stock",
        resource_id=movement.id,
        new_data={**body.model_dump(mode="json"), "product_name": product_name, "warehouse_name": warehouse_name},
        ip_address=_ip(request),
    )
    return ORJSONResponse(StockMovementOut.model_validate(movement).model_dump(mode="json"), status_code=201)


@router.post("/waste", response_model=StockMovementOut, status_code=201)
async def waste_stock(
    body: WasteStockIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = StockService(db)
    audit = InventoryAuditService(db)
    movement = await svc.waste(
        tenant_id=current_user["tenant_id"],
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        quantity=body.quantity,
        reason=body.reason,
        performed_by=current_user.get("id"),
        variant_id=body.variant_id,
    )
    product_name = await svc.resolve_product_name(body.product_id, current_user["tenant_id"])
    warehouse_name = await svc.resolve_warehouse_name(body.warehouse_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.stock.waste", resource_type="stock",
        resource_id=movement.id,
        new_data={**body.model_dump(mode="json"), "product_name": product_name, "warehouse_name": warehouse_name},
        ip_address=_ip(request),
    )
    return ORJSONResponse(StockMovementOut.model_validate(movement).model_dump(mode="json"), status_code=201)


@router.post("/qc-approve", response_model=StockLevelOut)
async def qc_approve(
    body: QCActionIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = StockService(db)
    audit = InventoryAuditService(db)
    level = await svc.qc_approve(
        tenant_id=current_user["tenant_id"],
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        batch_id=body.batch_id,
        variant_id=body.variant_id,
    )
    product_name = await svc.resolve_product_name(body.product_id, current_user["tenant_id"])
    warehouse_name = await svc.resolve_warehouse_name(body.warehouse_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.stock.qc_approve", resource_type="stock",
        resource_id=level.id,
        new_data={**body.model_dump(mode="json"), "product_name": product_name, "warehouse_name": warehouse_name},
        ip_address=_ip(request),
    )
    return ORJSONResponse(StockLevelOut.model_validate(level).model_dump(mode="json"))


@router.post("/qc-reject", response_model=StockLevelOut)
async def qc_reject(
    body: QCActionIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = StockService(db)
    audit = InventoryAuditService(db)
    level = await svc.qc_reject(
        tenant_id=current_user["tenant_id"],
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        batch_id=body.batch_id,
        variant_id=body.variant_id,
        notes=body.notes,
    )
    product_name = await svc.resolve_product_name(body.product_id, current_user["tenant_id"])
    warehouse_name = await svc.resolve_warehouse_name(body.warehouse_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.stock.qc_reject", resource_type="stock",
        resource_id=level.id,
        new_data={**body.model_dump(mode="json"), "product_name": product_name, "warehouse_name": warehouse_name},
        ip_address=_ip(request),
    )
    return ORJSONResponse(StockLevelOut.model_validate(level).model_dump(mode="json"))
