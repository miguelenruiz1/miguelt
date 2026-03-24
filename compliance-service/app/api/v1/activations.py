"""Router for tenant framework activations."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.core.errors import ConflictError, NotFoundError
from app.db.session import get_db_session
from app.models.activation import TenantFrameworkActivation
from app.models.framework import ComplianceFramework
from app.schemas.activation import ActivationCreate, ActivationResponse, ActivationUpdate

router = APIRouter(
    prefix="/api/v1/compliance/activations",
    tags=["activations"],
)


def _tenant_id(user: dict) -> uuid.UUID:
    raw = str(user.get("tenant_id", "00000000-0000-0000-0000-000000000001"))
    try:
        return uuid.UUID(raw)
    except ValueError:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("/", response_model=list[ActivationResponse])
async def list_activations(
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    q = (
        select(TenantFrameworkActivation)
        .where(TenantFrameworkActivation.tenant_id == tid)
        .order_by(TenantFrameworkActivation.activated_at.desc())
    )
    rows = (await db.execute(q)).scalars().all()

    # Enrich with framework_slug
    results = []
    for act in rows:
        fw = (
            await db.execute(
                select(ComplianceFramework).where(ComplianceFramework.id == act.framework_id)
            )
        ).scalar_one_or_none()
        # Build response manually to inject framework_slug
        data = {
            "id": act.id,
            "tenant_id": act.tenant_id,
            "framework_id": act.framework_id,
            "is_active": act.is_active,
            "export_destination": act.export_destination,
            "activated_at": act.activated_at,
            "activated_by": act.activated_by,
            "metadata_": act.metadata_,
            "framework_slug": fw.slug if fw else "unknown",
        }
        results.append(ActivationResponse(**data))
    return results


@router.post("/", response_model=ActivationResponse, status_code=status.HTTP_201_CREATED)
async def activate_framework(
    body: ActivationCreate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)

    # Lookup framework by slug
    fw = (
        await db.execute(
            select(ComplianceFramework).where(ComplianceFramework.slug == body.framework_slug)
        )
    ).scalar_one_or_none()
    if fw is None:
        raise NotFoundError(f"Framework '{body.framework_slug}' not found")

    # Check duplicate
    existing = (
        await db.execute(
            select(TenantFrameworkActivation).where(
                TenantFrameworkActivation.tenant_id == tid,
                TenantFrameworkActivation.framework_id == fw.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Framework '{body.framework_slug}' already activated for this tenant")

    user_id = user.get("id")
    act = TenantFrameworkActivation(
        tenant_id=tid,
        framework_id=fw.id,
        is_active=True,
        export_destination=body.export_destination,
        activated_by=uuid.UUID(str(user_id)) if user_id else None,
        metadata_=body.metadata or {},
    )
    db.add(act)
    await db.flush()
    await db.refresh(act)

    return ActivationResponse(
        id=act.id,
        tenant_id=act.tenant_id,
        framework_id=act.framework_id,
        is_active=act.is_active,
        export_destination=act.export_destination,
        activated_at=act.activated_at,
        activated_by=act.activated_by,
        metadata_=act.metadata_,
        framework_slug=fw.slug,
    )


@router.patch("/{framework_slug}", response_model=ActivationResponse)
async def update_activation(
    framework_slug: str,
    body: ActivationUpdate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)

    fw = (
        await db.execute(
            select(ComplianceFramework).where(ComplianceFramework.slug == framework_slug)
        )
    ).scalar_one_or_none()
    if fw is None:
        raise NotFoundError(f"Framework '{framework_slug}' not found")

    act = (
        await db.execute(
            select(TenantFrameworkActivation).where(
                TenantFrameworkActivation.tenant_id == tid,
                TenantFrameworkActivation.framework_id == fw.id,
            )
        )
    ).scalar_one_or_none()
    if act is None:
        raise NotFoundError(f"No activation found for framework '{framework_slug}'")

    update_data = body.model_dump(exclude_unset=True)
    # Map metadata -> metadata_
    if "metadata" in update_data:
        update_data["metadata_"] = update_data.pop("metadata")
    for key, val in update_data.items():
        setattr(act, key, val)
    await db.flush()
    await db.refresh(act)

    return ActivationResponse(
        id=act.id,
        tenant_id=act.tenant_id,
        framework_id=act.framework_id,
        is_active=act.is_active,
        export_destination=act.export_destination,
        activated_at=act.activated_at,
        activated_by=act.activated_by,
        metadata_=act.metadata_,
        framework_slug=fw.slug,
    )


@router.delete("/{framework_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_framework(
    framework_slug: str,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)

    fw = (
        await db.execute(
            select(ComplianceFramework).where(ComplianceFramework.slug == framework_slug)
        )
    ).scalar_one_or_none()
    if fw is None:
        raise NotFoundError(f"Framework '{framework_slug}' not found")

    act = (
        await db.execute(
            select(TenantFrameworkActivation).where(
                TenantFrameworkActivation.tenant_id == tid,
                TenantFrameworkActivation.framework_id == fw.id,
            )
        )
    ).scalar_one_or_none()
    if act is None:
        raise NotFoundError(f"No activation found for framework '{framework_slug}'")

    await db.delete(act)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
