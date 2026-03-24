"""Router for compliance plots (production parcels)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.core.errors import ConflictError, NotFoundError
from app.db.session import get_db_session
from app.models.plot import CompliancePlot
from app.models.plot_link import CompliancePlotLink
from app.schemas.plot import PlotCreate, PlotResponse, PlotUpdate

router = APIRouter(
    prefix="/api/v1/compliance/plots",
    tags=["plots"],
)


def _tenant_id(user: dict) -> uuid.UUID:
    raw = str(user.get("tenant_id", "00000000-0000-0000-0000-000000000001"))
    try:
        return uuid.UUID(raw)
    except ValueError:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post("/", response_model=PlotResponse, status_code=status.HTTP_201_CREATED)
async def create_plot(
    body: PlotCreate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)

    # Check unique plot_code per tenant
    existing = (
        await db.execute(
            select(CompliancePlot).where(
                CompliancePlot.tenant_id == tid,
                CompliancePlot.plot_code == body.plot_code,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Plot code '{body.plot_code}' already exists for this tenant")

    data = body.model_dump(exclude_unset=True)
    # Map metadata -> metadata_
    if "metadata" in data:
        data["metadata_"] = data.pop("metadata")
    else:
        data["metadata_"] = {}

    plot = CompliancePlot(tenant_id=tid, **data)
    db.add(plot)
    await db.flush()
    await db.refresh(plot)
    return plot


@router.get("/", response_model=list[PlotResponse])
async def list_plots(
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
    organization_id: uuid.UUID | None = Query(None),
    risk_level: str | None = Query(None),
    is_active: bool | None = Query(None),
):
    tid = _tenant_id(user)
    q = select(CompliancePlot).where(CompliancePlot.tenant_id == tid)

    if organization_id is not None:
        q = q.where(CompliancePlot.organization_id == organization_id)
    if risk_level is not None:
        q = q.where(CompliancePlot.risk_level == risk_level)
    if is_active is not None:
        q = q.where(CompliancePlot.is_active.is_(is_active))

    q = q.order_by(CompliancePlot.created_at.desc())
    rows = (await db.execute(q)).scalars().all()
    return rows


@router.get("/{plot_id}", response_model=PlotResponse)
async def get_plot(
    plot_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    plot = (
        await db.execute(
            select(CompliancePlot).where(
                CompliancePlot.id == plot_id,
                CompliancePlot.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if plot is None:
        raise NotFoundError(f"Plot '{plot_id}' not found")
    return plot


@router.patch("/{plot_id}", response_model=PlotResponse)
async def update_plot(
    plot_id: uuid.UUID,
    body: PlotUpdate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    plot = (
        await db.execute(
            select(CompliancePlot).where(
                CompliancePlot.id == plot_id,
                CompliancePlot.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if plot is None:
        raise NotFoundError(f"Plot '{plot_id}' not found")

    update_data = body.model_dump(exclude_unset=True)
    if "metadata" in update_data:
        update_data["metadata_"] = update_data.pop("metadata")
    for key, val in update_data.items():
        setattr(plot, key, val)

    await db.flush()
    await db.refresh(plot)
    return plot


@router.delete("/{plot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plot(
    plot_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    plot = (
        await db.execute(
            select(CompliancePlot).where(
                CompliancePlot.id == plot_id,
                CompliancePlot.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if plot is None:
        raise NotFoundError(f"Plot '{plot_id}' not found")

    # Check no active record links
    link_count = (
        await db.execute(
            select(func.count()).select_from(CompliancePlotLink).where(
                CompliancePlotLink.plot_id == plot_id
            )
        )
    ).scalar_one()
    if link_count > 0:
        raise ConflictError(
            f"Cannot delete plot '{plot_id}': it is linked to {link_count} compliance record(s)"
        )

    await db.delete(plot)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
