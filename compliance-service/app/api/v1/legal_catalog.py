"""Router for legal requirement catalogs + per-plot compliance tracking.

Exposes:
  GET  /api/v1/compliance/legal/catalogs                — list catalogs
  GET  /api/v1/compliance/legal/catalogs/{id}           — catalog + its requirements
  GET  /api/v1/compliance/legal/plots/{plot_id}/status  — per-plot checklist + summary
  PATCH /api/v1/compliance/legal/plots/{plot_id}/requirements/{req_id} — update status
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.core.errors import NotFoundError
from app.db.session import get_db_session
from app.models.legal_catalog import (
    LegalRequirement,
    LegalRequirementCatalog,
    PlotLegalCompliance,
)
from app.models.plot import CompliancePlot
from app.schemas.legal_catalog import (
    LegalCatalogResponse,
    LegalCatalogWithRequirements,
    LegalRequirementResponse,
    PlotLegalComplianceItem,
    PlotLegalComplianceResponse,
    PlotLegalComplianceSummary,
    PlotLegalComplianceUpdate,
)

router = APIRouter(
    prefix="/api/v1/compliance/legal",
    tags=["legal-catalog"],
)


def _tenant_id(user: dict) -> uuid.UUID:
    raw = str(user.get("tenant_id", "00000000-0000-0000-0000-000000000001"))
    try:
        return uuid.UUID(raw)
    except ValueError:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")


def _scale_applies(requirement_scale: str, plot_scale: str | None) -> bool:
    """Return whether a given requirement applies to a plot of a given scale."""
    if requirement_scale == "all":
        return True
    if plot_scale is None:
        # Unknown scale — assume requirement applies to be defensive.
        return True
    if requirement_scale == plot_scale:
        return True
    if requirement_scale == "medium_or_industrial" and plot_scale in ("medium", "industrial"):
        return True
    return False


@router.get("/catalogs", response_model=list[LegalCatalogResponse])
async def list_catalogs(
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
    country_code: str | None = Query(None),
    commodity: str | None = Query(None),
    is_active: bool | None = Query(True),
):
    _ = _tenant_id(user)
    q = select(LegalRequirementCatalog)
    if country_code:
        q = q.where(LegalRequirementCatalog.country_code == country_code)
    if commodity:
        q = q.where(LegalRequirementCatalog.commodity == commodity)
    if is_active is not None:
        q = q.where(LegalRequirementCatalog.is_active.is_(is_active))
    q = q.order_by(
        LegalRequirementCatalog.country_code,
        LegalRequirementCatalog.commodity,
        LegalRequirementCatalog.version.desc(),
    )
    return (await db.execute(q)).scalars().all()


@router.get("/catalogs/{catalog_id}", response_model=LegalCatalogWithRequirements)
async def get_catalog(
    catalog_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    _ = _tenant_id(user)
    cat = (
        await db.execute(
            select(LegalRequirementCatalog).where(
                LegalRequirementCatalog.id == catalog_id
            )
        )
    ).scalar_one_or_none()
    if cat is None:
        raise NotFoundError(f"Catalog '{catalog_id}' not found")
    reqs = (
        await db.execute(
            select(LegalRequirement)
            .where(LegalRequirement.catalog_id == catalog_id)
            .order_by(LegalRequirement.sort_order, LegalRequirement.code)
        )
    ).scalars().all()
    out = LegalCatalogWithRequirements.model_validate(cat)
    out.requirements = [LegalRequirementResponse.model_validate(r) for r in reqs]
    return out


async def _find_catalog_for_plot(
    db: AsyncSession, plot: CompliancePlot
) -> LegalRequirementCatalog | None:
    """Pick the active catalog that best matches a plot's country + crop."""
    commodity = (plot.crop_type or "").lower() or None
    q = select(LegalRequirementCatalog).where(
        LegalRequirementCatalog.country_code == plot.country_code,
        LegalRequirementCatalog.is_active.is_(True),
    )
    if commodity:
        q = q.where(LegalRequirementCatalog.commodity == commodity)
    q = q.order_by(LegalRequirementCatalog.version.desc())
    return (await db.execute(q)).scalars().first()


@router.get("/plots/{plot_id}/status", response_model=PlotLegalComplianceSummary)
async def get_plot_legal_status(
    plot_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    plot = (
        await db.execute(
            select(CompliancePlot).where(
                CompliancePlot.id == plot_id, CompliancePlot.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if plot is None:
        raise NotFoundError(f"Plot '{plot_id}' not found")

    catalog = await _find_catalog_for_plot(db, plot)
    if catalog is None:
        return PlotLegalComplianceSummary(
            plot_id=plot_id,
            catalog_id=None,
            producer_scale=plot.producer_scale,
            total_requirements=0,
            applicable_requirements=0,
            satisfied=0,
            missing=0,
            pending=0,
            na=0,
            blocking_missing=0,
            items=[],
        )

    reqs = (
        await db.execute(
            select(LegalRequirement)
            .where(LegalRequirement.catalog_id == catalog.id)
            .order_by(LegalRequirement.sort_order, LegalRequirement.code)
        )
    ).scalars().all()

    statuses = (
        await db.execute(
            select(PlotLegalCompliance).where(
                PlotLegalCompliance.plot_id == plot_id,
                PlotLegalCompliance.tenant_id == tid,
            )
        )
    ).scalars().all()
    by_req = {s.requirement_id: s for s in statuses}

    items: list[PlotLegalComplianceItem] = []
    sat = miss = pend = na = blocking_miss = applicable = 0
    for req in reqs:
        applies = _scale_applies(req.applies_to_scale, plot.producer_scale)
        existing = by_req.get(req.id)
        if existing:
            current_status = existing.status
        else:
            current_status = "na" if not applies else "pending"
        if applies:
            applicable += 1
            if current_status == "satisfied":
                sat += 1
            elif current_status == "missing":
                miss += 1
                if req.is_blocking:
                    blocking_miss += 1
            elif current_status == "pending":
                pend += 1
            elif current_status == "na":
                na += 1
        else:
            na += 1
        items.append(
            PlotLegalComplianceItem(
                requirement=LegalRequirementResponse.model_validate(req),
                compliance=(
                    PlotLegalComplianceResponse.model_validate(existing) if existing else None
                ),
            )
        )

    return PlotLegalComplianceSummary(
        plot_id=plot_id,
        catalog_id=catalog.id,
        producer_scale=plot.producer_scale,
        total_requirements=len(reqs),
        applicable_requirements=applicable,
        satisfied=sat,
        missing=miss,
        pending=pend,
        na=na,
        blocking_missing=blocking_miss,
        items=items,
    )


@router.patch(
    "/plots/{plot_id}/requirements/{requirement_id}",
    response_model=PlotLegalComplianceResponse,
)
async def update_plot_requirement_status(
    plot_id: uuid.UUID,
    requirement_id: uuid.UUID,
    body: PlotLegalComplianceUpdate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    plot = (
        await db.execute(
            select(CompliancePlot).where(
                CompliancePlot.id == plot_id, CompliancePlot.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if plot is None:
        raise NotFoundError(f"Plot '{plot_id}' not found")

    req = (
        await db.execute(
            select(LegalRequirement).where(LegalRequirement.id == requirement_id)
        )
    ).scalar_one_or_none()
    if req is None:
        raise NotFoundError(f"Legal requirement '{requirement_id}' not found")

    existing = (
        await db.execute(
            select(PlotLegalCompliance).where(
                PlotLegalCompliance.plot_id == plot_id,
                PlotLegalCompliance.requirement_id == requirement_id,
                PlotLegalCompliance.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()

    raw_user = str(user.get("user_id") or user.get("id") or "")
    reviewer = None
    try:
        reviewer = uuid.UUID(raw_user) if raw_user else None
    except ValueError:
        reviewer = None

    if existing is None:
        row = PlotLegalCompliance(
            tenant_id=tid,
            plot_id=plot_id,
            requirement_id=requirement_id,
            status=body.status,
            evidence_media_id=body.evidence_media_id,
            evidence_notes=body.evidence_notes,
            evidence_weight=body.evidence_weight or "primary",
            reviewed_by=reviewer,
            reviewed_at=datetime.now(tz=timezone.utc),
        )
        db.add(row)
    else:
        existing.status = body.status
        existing.evidence_media_id = body.evidence_media_id
        existing.evidence_notes = body.evidence_notes
        if body.evidence_weight is not None:
            existing.evidence_weight = body.evidence_weight
        existing.reviewed_by = reviewer
        existing.reviewed_at = datetime.now(tz=timezone.utc)
        row = existing

    await db.flush()
    await db.refresh(row)
    return row
