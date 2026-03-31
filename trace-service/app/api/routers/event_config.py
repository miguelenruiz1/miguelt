"""Event type configuration router — admin CRUD for custody event types."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import ORJSONResponse
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.domain.schemas import (
    EventTypeConfigCreate,
    EventTypeConfigUpdate,
    EventTypeConfigResponse,
)
from app.repositories.event_type_repo import EventTypeConfigRepository

log = get_logger(__name__)
router = APIRouter(prefix="/config/event-types", tags=["config"])


def _resp(row) -> dict:
    return EventTypeConfigResponse.model_validate(row).model_dump(mode="json")


@router.get("", summary="List event type configurations")
async def list_event_types(
    active_only: bool = Query(True),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    repo = EventTypeConfigRepository(db)
    rows, total = await repo.list(tenant_id, active_only=active_only, offset=offset, limit=limit)
    return ORJSONResponse(content={"items": [_resp(r) for r in rows], "total": total})


@router.get("/{config_id}", summary="Get event type config by ID")
async def get_event_type(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    repo = EventTypeConfigRepository(db)
    row = await repo.get_by_id(config_id)
    if not row or row.tenant_id != tenant_id:
        raise NotFoundError(f"Event type config '{config_id}' not found")
    return ORJSONResponse(content=_resp(row))


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create custom event type")
async def create_event_type(
    body: EventTypeConfigCreate,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    repo = EventTypeConfigRepository(db)
    existing = await repo.get_by_slug(tenant_id, body.slug)
    if existing:
        raise ConflictError(f"Event type '{body.slug}' already exists for this tenant")

    row = await repo.create(
        tenant_id=tenant_id,
        slug=body.slug,
        name=body.name,
        description=body.description,
        icon=body.icon,
        color=body.color,
        from_states=body.from_states,
        to_state=body.to_state,
        is_system=False,
        is_informational=body.is_informational,
        requires_wallet=body.requires_wallet,
        requires_notes=body.requires_notes,
        requires_reason=body.requires_reason,
        requires_admin=body.requires_admin,
        sort_order=body.sort_order,
    )
    await db.commit()
    log.info("event_type_created", slug=body.slug, tenant_id=str(tenant_id))
    return ORJSONResponse(status_code=status.HTTP_201_CREATED, content=_resp(row))


@router.patch("/{config_id}", summary="Update event type config")
async def update_event_type(
    config_id: uuid.UUID,
    body: EventTypeConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    repo = EventTypeConfigRepository(db)
    row = await repo.get_by_id(config_id)
    if not row or row.tenant_id != tenant_id:
        raise NotFoundError(f"Event type config '{config_id}' not found")

    updates = body.model_dump(exclude_unset=True)
    # System types: cannot change slug, from_states, to_state, is_informational
    if row.is_system:
        for protected in ("from_states", "to_state", "is_informational"):
            updates.pop(protected, None)

    row = await repo.update(row, **updates)
    await db.commit()
    log.info("event_type_updated", slug=row.slug, config_id=str(config_id))
    return ORJSONResponse(content=_resp(row))


@router.delete(
    "/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete custom event type (system types cannot be deleted)",
    response_class=Response,
)
async def delete_event_type(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    repo = EventTypeConfigRepository(db)
    row = await repo.get_by_id(config_id)
    if not row or row.tenant_id != tenant_id:
        raise NotFoundError(f"Event type config '{config_id}' not found")
    if row.is_system:
        raise ForbiddenError(f"Cannot delete system event type '{row.slug}'")

    await repo.delete(row)
    await db.commit()
    log.info("event_type_deleted", slug=row.slug, config_id=str(config_id))
    return Response(status_code=204)
