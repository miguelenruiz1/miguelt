"""Audit log endpoints for inventory-service."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.audit import AuditLogOut, PaginatedAuditLogs
from app.services.audit_service import InventoryAuditService

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=PaginatedAuditLogs)
async def list_audit_logs(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("admin.audit"))],
    db: AsyncSession = Depends(get_db_session),
    action: str | None = None,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=200),
) -> ORJSONResponse:
    svc = InventoryAuditService(db)
    items, total = await svc.list(
        current_user["tenant_id"],
        action=action,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )
    return ORJSONResponse({
        "items": [AuditLogOut.model_validate(i).model_dump(mode="json") for i in items],
        "total": total,
        "offset": offset,
        "limit": limit,
    })


@router.get("/entity/{resource_type}/{resource_id}", response_model=PaginatedAuditLogs)
async def entity_timeline(
    resource_type: str,
    resource_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("admin.audit"))],
    db: AsyncSession = Depends(get_db_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> ORJSONResponse:
    svc = InventoryAuditService(db)
    items, total = await svc.entity_timeline(
        current_user["tenant_id"],
        resource_type,
        resource_id,
        offset=offset,
        limit=limit,
    )
    return ORJSONResponse({
        "items": [AuditLogOut.model_validate(i).model_dump(mode="json") for i in items],
        "total": total,
        "offset": offset,
        "limit": limit,
    })
