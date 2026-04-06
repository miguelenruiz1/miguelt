"""Inventory events endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas import (
    EventCreate, EventImpactCreate, EventOut, EventStatusChange, PaginatedEvents,
)
from app.services.event_service import EventService
from app.services.audit_service import InventoryAuditService

router = APIRouter(prefix="/api/v1/events", tags=["events"])


from app.api.deps import get_client_ip as _ip  # noqa: F401


def _svc(db: AsyncSession = Depends(get_db_session)) -> EventService:
    return EventService(db)


@router.get("", response_model=PaginatedEvents)
async def list_events(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    event_type_id: str | None = None,
    severity_id: str | None = None,
    status_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    svc: EventService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list(tenant_id, event_type_id, severity_id, status_id, offset, limit)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.post("", response_model=EventOut, status_code=201)
async def create_event(
    body: EventCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: EventService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    data = body.model_dump()
    if not data.get("reported_by"):
        data["reported_by"] = current_user.get("id")
    impacts = data.pop("impacts", [])
    event = await svc.create(tenant_id, data, impacts)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.event.create", resource_type="event",
        resource_id=event.id, new_data=body.model_dump(mode="json"), ip_address=_ip(request),
    )
    return event


@router.get("/{event_id}", response_model=EventOut)
async def get_event(
    event_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    svc: EventService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    return await svc.get(tenant_id, event_id)


@router.post("/{event_id}/status", response_model=EventOut)
async def change_event_status(
    event_id: str,
    body: EventStatusChange,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: EventService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    changed_by = body.changed_by or current_user.get("id")
    event = await svc.change_status(
        tenant_id, event_id, body.status_id,
        notes=body.notes, changed_by=changed_by, resolved_at=body.resolved_at,
    )
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.event.update_status", resource_type="event",
        resource_id=event_id, new_data=body.model_dump(mode="json"), ip_address=_ip(request),
    )
    return event


@router.post("/{event_id}/impacts", status_code=201)
async def add_event_impact(
    event_id: str,
    body: EventImpactCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: EventService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.add_impact(tenant_id, event_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.event.add_impact", resource_type="event",
        resource_id=event_id, new_data=body.model_dump(mode="json"), ip_address=_ip(request),
    )
    return result
