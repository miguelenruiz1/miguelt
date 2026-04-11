"""Router for certification scheme credibility registry."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.core.errors import NotFoundError
from app.db.session import get_db_session
from app.models.certification import CertificationScheme
from app.schemas.certification import (
    CertificationSchemeResponse,
    CertificationSchemeUpdate,
)

router = APIRouter(
    prefix="/api/v1/compliance/certifications",
    tags=["certifications"],
)


@router.get("/", response_model=list[CertificationSchemeResponse])
async def list_schemes(
    _: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
    commodity: str | None = Query(None),
    scope: str | None = Query(None),
    is_active: bool | None = Query(True),
):
    q = select(CertificationScheme)
    if is_active is not None:
        q = q.where(CertificationScheme.is_active.is_(is_active))
    if scope:
        q = q.where(CertificationScheme.scope == scope)
    q = q.order_by(CertificationScheme.total_score.desc(), CertificationScheme.name)
    rows = (await db.execute(q)).scalars().all()
    if commodity:
        rows = [r for r in rows if commodity in (r.commodities or [])]
    return rows


@router.get("/{slug}", response_model=CertificationSchemeResponse)
async def get_scheme(
    slug: str,
    _: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    row = (
        await db.execute(
            select(CertificationScheme).where(CertificationScheme.slug == slug)
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"Certification scheme '{slug}' not found")
    return row


@router.patch("/{slug}", response_model=CertificationSchemeResponse)
async def update_scheme(
    slug: str,
    body: CertificationSchemeUpdate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    # Minimal admin gate: require is_superuser for score edits.
    if not user.get("is_superuser"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="admin required")

    row = (
        await db.execute(
            select(CertificationScheme).where(CertificationScheme.slug == slug)
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"Certification scheme '{slug}' not found")

    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    row.total_score = (
        row.ownership_score
        + row.transparency_score
        + row.audit_score
        + row.grievance_score
    )
    await db.flush()
    await db.refresh(row)
    return row
