"""Cycle count endpoints: create, count items, approve, IRA analytics."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.services.audit_service import InventoryAuditService
from app.domain.schemas import (
    CycleCountCreate,
    CycleCountOut,
    CycleCountItemOut,
    PaginatedCycleCounts,
    RecordCountIn,
    RecountIn,
    IRAComputeOut,
    FeasibilityOut,
    ProductDiscrepancyOut,
)
from app.services.cycle_count_service import CycleCountService

router = APIRouter(prefix="/api/v1/cycle-counts", tags=["cycle-counts"])


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


def _item_to_out(item) -> dict:
    return CycleCountItemOut(
        id=item.id,
        tenant_id=item.tenant_id,
        cycle_count_id=item.cycle_count_id,
        product_id=item.product_id,
        product_name=item.product.name if item.product else None,
        product_sku=item.product.sku if item.product else None,
        location_id=item.location_id,
        batch_id=item.batch_id,
        system_qty=item.system_qty,
        counted_qty=item.counted_qty,
        discrepancy=item.discrepancy,
        recount_qty=item.recount_qty,
        recount_discrepancy=item.recount_discrepancy,
        root_cause=item.root_cause,
        counted_by=item.counted_by,
        counted_at=item.counted_at,
        notes=item.notes,
        movement_id=item.movement_id,
        created_at=item.created_at,
    ).model_dump(mode="json")


def _count_to_out(cc, svc=None) -> dict:
    """Serialize a CycleCount ORM instance to CycleCountOut dict."""
    items = [_item_to_out(item) for item in (cc.items or [])]

    feasibility = None
    if svc:
        feasibility = svc.compute_feasibility(cc)

    return CycleCountOut(
        id=cc.id,
        tenant_id=cc.tenant_id,
        count_number=cc.count_number,
        warehouse_id=cc.warehouse_id,
        warehouse_name=cc.warehouse.name if cc.warehouse else None,
        status=cc.status.value if hasattr(cc.status, "value") else cc.status,
        methodology=cc.methodology.value if cc.methodology and hasattr(cc.methodology, "value") else cc.methodology,
        assigned_counters=cc.assigned_counters or 1,
        minutes_per_count=cc.minutes_per_count or 2,
        scheduled_date=cc.scheduled_date,
        started_at=cc.started_at,
        completed_at=cc.completed_at,
        approved_at=cc.approved_at,
        approved_by=cc.approved_by,
        created_by=cc.created_by,
        notes=cc.notes,
        created_at=cc.created_at,
        items=items,
        feasibility=feasibility,
    ).model_dump(mode="json")


# ── List + Create (no path param — must come first) ─────────────────────────

@router.get("", response_model=PaginatedCycleCounts)
async def list_cycle_counts(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    status: str | None = None,
    warehouse_id: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> ORJSONResponse:
    svc = CycleCountService(db)
    counts, total = await svc.repo.list_counts(
        tenant_id=current_user["tenant_id"],
        status=status,
        warehouse_id=warehouse_id,
        offset=offset,
        limit=limit,
    )
    items = []
    for cc in counts:
        items.append(CycleCountOut(
            id=cc.id,
            tenant_id=cc.tenant_id,
            count_number=cc.count_number,
            warehouse_id=cc.warehouse_id,
            warehouse_name=cc.warehouse.name if cc.warehouse else None,
            status=cc.status.value if hasattr(cc.status, "value") else cc.status,
            methodology=cc.methodology.value if cc.methodology and hasattr(cc.methodology, "value") else cc.methodology,
            assigned_counters=cc.assigned_counters or 1,
            minutes_per_count=cc.minutes_per_count or 2,
            scheduled_date=cc.scheduled_date,
            started_at=cc.started_at,
            completed_at=cc.completed_at,
            approved_at=cc.approved_at,
            approved_by=cc.approved_by,
            created_by=cc.created_by,
            notes=cc.notes,
            created_at=cc.created_at,
        ).model_dump(mode="json"))
    return ORJSONResponse({
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
    })


@router.post("", status_code=201)
async def create_cycle_count(
    body: CycleCountCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = CycleCountService(db)
    audit = InventoryAuditService(db)
    cc = await svc.create_count(
        tenant_id=current_user["tenant_id"],
        warehouse_id=body.warehouse_id,
        product_ids=body.product_ids or None,
        methodology=body.methodology,
        assigned_counters=body.assigned_counters,
        minutes_per_count=body.minutes_per_count,
        scheduled_date=body.scheduled_date,
        notes=body.notes,
        created_by=current_user.get("id"),
    )
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.cycle_count.create", resource_type="cycle_count",
        resource_id=cc.id, new_data=body.model_dump(mode="json"), ip_address=_ip(request),
    )
    return ORJSONResponse(_count_to_out(cc, svc=svc), status_code=201)


# ── Analytics (literal path segments — must come before {cc_id}) ─────────────

@router.get("/analytics/ira-trend")
async def ira_trend(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    warehouse_id: str | None = None,
) -> ORJSONResponse:
    svc = CycleCountService(db)
    trend = await svc.get_ira_trend(current_user["tenant_id"], warehouse_id=warehouse_id)
    return ORJSONResponse(trend)


@router.get("/analytics/product-history/{product_id}")
async def product_discrepancy_history(
    product_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = CycleCountService(db)
    history = await svc.get_product_discrepancy_history(
        current_user["tenant_id"], product_id,
    )
    return ORJSONResponse(history)


# ── Single cycle count (path param) ─────────────────────────────────────────

@router.get("/{cc_id}")
async def get_cycle_count(
    cc_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = CycleCountService(db)
    cc = await svc._get_count(cc_id, current_user["tenant_id"])
    data = _count_to_out(cc, svc=svc)
    data["ira"] = svc._compute_ira(cc)
    return ORJSONResponse(data)


# ── State transitions ────────────────────────────────────────────────────────

@router.post("/{cc_id}/start")
async def start_cycle_count(
    cc_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = CycleCountService(db)
    audit = InventoryAuditService(db)
    cc = await svc.start_count(cc_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.cycle_count.start", resource_type="cycle_count",
        resource_id=cc_id, new_data={"status": "in_progress"}, ip_address=_ip(request),
    )
    return ORJSONResponse(_count_to_out(cc, svc=svc))


@router.post("/{cc_id}/items/{item_id}/count")
async def record_item_count(
    cc_id: str,
    item_id: str,
    body: RecordCountIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = CycleCountService(db)
    audit = InventoryAuditService(db)
    item = await svc.record_item_count(
        cc_id=cc_id,
        item_id=item_id,
        tenant_id=current_user["tenant_id"],
        counted_qty=body.counted_qty,
        counted_by=current_user.get("id"),
        notes=body.notes,
    )
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.cycle_count.count", resource_type="cycle_count",
        resource_id=cc_id, new_data={"item_id": item_id, **body.model_dump(mode="json")},
        ip_address=_ip(request),
    )
    return ORJSONResponse(_item_to_out(item))


@router.post("/{cc_id}/items/{item_id}/recount")
async def recount_item(
    cc_id: str,
    item_id: str,
    body: RecountIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = CycleCountService(db)
    audit = InventoryAuditService(db)
    item = await svc.recount_item(
        cc_id=cc_id,
        item_id=item_id,
        tenant_id=current_user["tenant_id"],
        recount_qty=body.recount_qty,
        root_cause=body.root_cause,
        counted_by=current_user.get("id"),
        notes=body.notes,
    )
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.cycle_count.recount", resource_type="cycle_count",
        resource_id=cc_id, new_data={"item_id": item_id, **body.model_dump(mode="json")},
        ip_address=_ip(request),
    )
    return ORJSONResponse(_item_to_out(item))


@router.post("/{cc_id}/complete")
async def complete_cycle_count(
    cc_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = CycleCountService(db)
    audit = InventoryAuditService(db)
    cc = await svc.complete_count(cc_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.cycle_count.complete", resource_type="cycle_count",
        resource_id=cc_id, new_data={"status": "completed"}, ip_address=_ip(request),
    )
    return ORJSONResponse(_count_to_out(cc, svc=svc))


@router.post("/{cc_id}/approve")
async def approve_cycle_count(
    cc_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = CycleCountService(db)
    audit = InventoryAuditService(db)
    cc = await svc.approve_count(
        cc_id, current_user["tenant_id"], approved_by=current_user.get("id"),
    )
    data = _count_to_out(cc, svc=svc)
    data["ira"] = svc._compute_ira(cc)
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.cycle_count.approve", resource_type="cycle_count",
        resource_id=cc_id, new_data={"status": "approved"}, ip_address=_ip(request),
    )
    return ORJSONResponse(data)


@router.post("/{cc_id}/cancel")
async def cancel_cycle_count(
    cc_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = CycleCountService(db)
    audit = InventoryAuditService(db)
    cc = await svc.cancel_count(cc_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.cycle_count.cancel", resource_type="cycle_count",
        resource_id=cc_id, new_data={"status": "canceled"}, ip_address=_ip(request),
    )
    return ORJSONResponse(_count_to_out(cc, svc=svc))


# ── Per-count IRA ────────────────────────────────────────────────────────────

@router.get("/{cc_id}/ira", response_model=IRAComputeOut)
async def get_cycle_count_ira(
    cc_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = CycleCountService(db)
    ira = await svc.compute_ira(cc_id, current_user["tenant_id"])
    return ORJSONResponse(ira)
