"""Audit log endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id, require_permission
from app.db.session import get_db_session
from app.domain.schemas import AuditLogResponse, PaginatedResponse
from app.repositories.audit_repo import AuditRepository

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    _: Annotated[object, require_permission("admin.audit")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    action: str | None = None,
    user_id: str | None = None,
    resource_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    offset: int = 0,
    limit: int = 50,
) -> PaginatedResponse[AuditLogResponse]:
    repo = AuditRepository(db)
    logs, total = await repo.list(
        tenant_id=tenant_id,
        action=action,
        user_id=user_id,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )
    return PaginatedResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        offset=offset,
        limit=limit,
    )
