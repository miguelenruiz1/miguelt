"""User management endpoints."""
from __future__ import annotations

from typing import Annotated

import httpx
import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_redis, get_tenant_id, require_permission
from app.core.settings import get_settings
from app.db.session import get_db_session
from app.domain.schemas import AdminUpdateUser, InviteUserRequest, PaginatedResponse, RoleSlim, UserResponse
from app.repositories.audit_repo import AuditRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])
_log = structlog.get_logger(__name__)


async def _enforce_user_limit(tenant_id: str) -> None:
    """Check subscription plan user limit via subscription-service.

    Raises 402 if the plan limit is reached. In production, fails CLOSED if
    subscription-service is unreachable (returns 503) so a competitor can't
    DoS subscription-service to bypass billing limits. In dev/test it fails open.
    """
    import os
    settings = get_settings()
    url = f"{settings.SUBSCRIPTION_SERVICE_URL}/api/v1/enforcement/check/{tenant_id}/users"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
        if resp.status_code == 402:
            body = resp.json()
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=body.get("detail", "Límite de usuarios del plan alcanzado"),
            )
        if resp.status_code != 200:
            _log.warning("enforcement_check_unexpected", status=resp.status_code, tenant=tenant_id)
    except httpx.RequestError as exc:
        env = os.environ.get("ENV", "dev").lower()
        _log.warning("enforcement_check_unreachable", tenant=tenant_id, error=str(exc), env=env)
        if env in ("prod", "production"):
            # Fail CLOSED in prod — refuse user creation if we can't verify the limit
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo verificar el límite del plan. Reintenta en un momento.",
            )


def _require_superuser(current_user: CurrentUser):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return current_user


async def _user_response(user, db: AsyncSession) -> UserResponse:
    svc = AuthService(db)
    roles = await svc.get_roles(user)
    permissions = await svc.get_permissions(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        tenant_id=user.tenant_id,
        avatar_url=user.avatar_url,
        phone=user.phone,
        job_title=user.job_title,
        company=user.company,
        bio=user.bio,
        timezone=user.timezone,
        language=user.language,
        invitation_sent_at=user.invitation_sent_at,
        invitation_accepted_at=user.invitation_accepted_at,
        must_change_password=user.must_change_password,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=[RoleSlim(id=r.id, name=r.name, slug=r.slug) for r in roles],
        permissions=sorted(permissions),
    )


@router.get("/all", response_model=PaginatedResponse[UserResponse])
async def list_all_users(
    _: Annotated[object, Depends(_require_superuser)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    search: str | None = Query(None),
    tenant_id: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[UserResponse]:
    """List users across all tenants — superuser only."""
    svc = UserService(db)
    users, total = await svc.list_all(offset=offset, limit=limit, search=search, tenant_id=tenant_id)
    items = [await _user_response(u, db) for u in users]
    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)


@router.post("", response_model=UserResponse, status_code=201)
async def invite_user(
    body: InviteUserRequest,
    _: Annotated[object, require_permission("admin.users")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> UserResponse:
    # Enforce plan user limit before creating
    await _enforce_user_limit(tenant_id)

    svc = AuthService(db)
    user = await svc.invite_user(
        tenant_id=tenant_id,
        email=body.email,
        full_name=body.full_name,
        role_ids=body.role_ids,
    )
    return await _user_response(user, db)


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    _: Annotated[object, require_permission("admin.users")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    offset: int = 0,
    limit: int = 50,
) -> PaginatedResponse[UserResponse]:
    svc = UserService(db)
    users, total = await svc.list(tenant_id, offset, limit)
    items = [await _user_response(u, db) for u in users]
    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: Annotated[dict, require_permission("admin.users")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> UserResponse:
    svc = UserService(db)
    # Superusers may bypass tenant scoping
    scope_tid = None if current_user.get("is_superuser") else tenant_id
    user = await svc.get(user_id, tenant_id=scope_tid)
    return await _user_response(user, db)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: AdminUpdateUser,
    current_user: Annotated[dict, require_permission("admin.users")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> UserResponse:
    data = body.model_dump(exclude_unset=True)
    if "is_superuser" in data and not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un superusuario puede modificar is_superuser",
        )
    svc = UserService(db)
    scope_tid = None if current_user.get("is_superuser") else tenant_id
    user = await svc.update(user_id, tenant_id=scope_tid, **data)
    # Audit trail: admin mutation on a user — record who did what.
    await AuditRepository(db).create(
        action="user.update",
        tenant_id=user.tenant_id,
        user_id=str(current_user.get("id")) if current_user.get("id") else None,
        user_email=current_user.get("email"),
        resource_type="user",
        resource_id=user_id,
        metadata={"fields": sorted(data.keys())},
    )
    return await _user_response(user, db)


@router.post("/{user_id}/resend-invitation", response_model=UserResponse)
async def resend_invitation(
    user_id: str,
    _: Annotated[object, require_permission("admin.users")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> UserResponse:
    svc = AuthService(db)
    user = await svc.resend_invitation(tenant_id, user_id)
    return await _user_response(user, db)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: str,
    _: Annotated[object, require_permission("admin.users")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> UserResponse:
    svc = AuthService(db)
    user = await svc.deactivate_user(tenant_id, user_id, redis)
    return await _user_response(user, db)


@router.post("/{user_id}/reactivate", response_model=UserResponse)
async def reactivate_user(
    user_id: str,
    _: Annotated[object, require_permission("admin.users")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> UserResponse:
    svc = AuthService(db)
    user = await svc.reactivate_user(tenant_id, user_id)
    return await _user_response(user, db)


@router.post("/{user_id}/roles/{role_id}", status_code=204, response_class=Response)
async def assign_role(
    user_id: str,
    role_id: str,
    current_user: Annotated[dict, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> Response:
    svc = UserService(db)
    scope_tid = None if current_user.get("is_superuser") else tenant_id
    await svc.assign_role(user_id, role_id, tenant_id=scope_tid)
    await AuditRepository(db).create(
        action="user.role_assigned",
        tenant_id=scope_tid or tenant_id,
        user_id=str(current_user.get("id")) if current_user.get("id") else None,
        user_email=current_user.get("email"),
        resource_type="user",
        resource_id=user_id,
        metadata={"role_id": role_id},
    )
    return Response(status_code=204)


@router.delete("/{user_id}/roles/{role_id}", status_code=204, response_class=Response)
async def remove_role(
    user_id: str,
    role_id: str,
    current_user: Annotated[dict, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> Response:
    svc = UserService(db)
    scope_tid = None if current_user.get("is_superuser") else tenant_id
    await svc.remove_role(user_id, role_id, tenant_id=scope_tid)
    await AuditRepository(db).create(
        action="user.role_removed",
        tenant_id=scope_tid or tenant_id,
        user_id=str(current_user.get("id")) if current_user.get("id") else None,
        user_email=current_user.get("email"),
        resource_type="user",
        resource_id=user_id,
        metadata={"role_id": role_id},
    )
    return Response(status_code=204)
