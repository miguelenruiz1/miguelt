"""Role management endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_tenant_id, require_permission
from app.db.session import get_db_session
from app.domain.schemas import (
    BulkSetPermissionsRequest,
    CreateFromTemplateRequest,
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleTemplateCreate,
    RoleTemplateResponse,
    RoleTemplateUpdate,
    RoleUpdate,
)
from app.services.role_service import RoleService

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])


# ── Templates (before /{role_id} to avoid path conflict) ─────────────────────

@router.get("/templates", response_model=list[RoleTemplateResponse])
async def list_templates(
    _: Annotated[object, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> list[RoleTemplateResponse]:
    svc = RoleService(db)
    templates = await svc.list_templates(tenant_id)
    return [RoleTemplateResponse.model_validate(t) for t in templates]


@router.post("/templates", response_model=RoleTemplateResponse, status_code=201)
async def create_template(
    body: RoleTemplateCreate,
    _: Annotated[object, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> RoleTemplateResponse:
    svc = RoleService(db)
    tmpl = await svc.create_template(
        tenant_id=tenant_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        icon=body.icon,
        permissions=body.permissions,
    )
    return RoleTemplateResponse.model_validate(tmpl)


@router.patch("/templates/{template_id}", response_model=RoleTemplateResponse)
async def update_template(
    template_id: str,
    body: RoleTemplateUpdate,
    _: Annotated[object, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> RoleTemplateResponse:
    svc = RoleService(db)
    updates = body.model_dump(exclude_none=True)
    tmpl = await svc.update_template(template_id, **updates)
    return RoleTemplateResponse.model_validate(tmpl)


@router.delete("/templates/{template_id}", status_code=204, response_class=Response)
async def delete_template(
    template_id: str,
    _: Annotated[object, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    svc = RoleService(db)
    await svc.delete_template(template_id)
    return Response(status_code=204)


@router.post("/from-template", response_model=RoleResponse, status_code=201)
async def create_from_template(
    body: CreateFromTemplateRequest,
    _: Annotated[object, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> RoleResponse:
    svc = RoleService(db)
    role = await svc.create_from_template(tenant_id, body.template_id)
    return RoleResponse.model_validate(role)


# ── Roles ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[RoleResponse])
async def list_roles(
    _: Annotated[object, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> list[RoleResponse]:
    svc = RoleService(db)
    roles = await svc.list(tenant_id)
    return [RoleResponse.model_validate(r) for r in roles]


@router.post("", response_model=RoleResponse, status_code=201)
async def create_role(
    body: RoleCreate,
    _: Annotated[object, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> RoleResponse:
    svc = RoleService(db)
    role = await svc.create(
        name=body.name,
        slug=body.slug,
        description=body.description,
        tenant_id=tenant_id,
    )
    return RoleResponse.model_validate(role)


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    current_user: Annotated[dict, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> RoleResponse:
    svc = RoleService(db)
    scope_tid = None if current_user.get("is_superuser") else tenant_id
    role = await svc.get(role_id, tenant_id=scope_tid)
    return RoleResponse.model_validate(role)


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    body: RoleUpdate,
    current_user: Annotated[dict, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> RoleResponse:
    svc = RoleService(db)
    scope_tid = None if current_user.get("is_superuser") else tenant_id
    updates = body.model_dump(exclude_none=True)
    role = await svc.update(role_id, tenant_id=scope_tid, **updates)
    return RoleResponse.model_validate(role)


@router.delete("/{role_id}", status_code=204, response_class=Response)
async def delete_role(
    role_id: str,
    current_user: Annotated[dict, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> Response:
    svc = RoleService(db)
    scope_tid = None if current_user.get("is_superuser") else tenant_id
    await svc.delete(role_id, tenant_id=scope_tid)
    return Response(status_code=204)


@router.get("/{role_id}/permissions", response_model=list[PermissionResponse])
async def get_role_permissions(
    role_id: str,
    current_user: Annotated[dict, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> list[PermissionResponse]:
    svc = RoleService(db)
    scope_tid = None if current_user.get("is_superuser") else tenant_id
    perms = await svc.get_role_permissions(role_id, tenant_id=scope_tid)
    return [PermissionResponse.model_validate(p) for p in perms]


@router.put("/{role_id}/permissions", status_code=204, response_class=Response)
async def set_role_permissions(
    role_id: str,
    body: BulkSetPermissionsRequest,
    current_user: Annotated[dict, require_permission("admin.roles")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> Response:
    svc = RoleService(db)
    scope_tid = None if current_user.get("is_superuser") else tenant_id
    await svc.set_role_permissions(role_id, body.permission_ids, tenant_id=scope_tid)
    return Response(status_code=204)
