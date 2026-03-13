"""Permission listing endpoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db_session
from app.domain.schemas import PermissionResponse
from app.services.role_service import RoleService

router = APIRouter(prefix="/api/v1/permissions", tags=["permissions"])


@router.get("", response_model=list[PermissionResponse])
async def list_permissions(
    _: Annotated[object, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[PermissionResponse]:
    svc = RoleService(db)
    perms = await svc.list_permissions()
    return [PermissionResponse.model_validate(p) for p in perms]
