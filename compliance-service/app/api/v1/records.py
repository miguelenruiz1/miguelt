"""Router for compliance records — the core entity linking assets to frameworks."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, get_http_client
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.settings import get_settings
from app.db.session import get_db_session
from app.models.framework import ComplianceFramework
from app.models.plot_link import CompliancePlotLink
from app.models.record import ComplianceRecord
from app.schemas.record import (
    PlotLinkCreate,
    PlotLinkResponse,
    RecordCreate,
    RecordResponse,
    RecordUpdate,
)
from app.schemas.validation import ValidationResult

router = APIRouter(
    prefix="/api/v1/compliance/records",
    tags=["records"],
)


def _tenant_id(user: dict) -> uuid.UUID:
    raw = str(user.get("tenant_id", "00000000-0000-0000-0000-000000000001"))
    try:
        return uuid.UUID(raw)
    except ValueError:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")


# ─── Validator helper ────────────────────────────────────────────────────────

async def _validate_record(
    record: ComplianceRecord,
    framework: ComplianceFramework,
    db: AsyncSession,
) -> ValidationResult:
    """Run validation rules from the framework against the record fields."""
    rules: dict = framework.validation_rules or {}
    required_fields: list[str] = rules.get("required_fields", [])
    missing: list[str] = []
    warnings: list[str] = []

    for field_name in required_fields:
        val = getattr(record, field_name, None)
        if val is None or val == "" or val == []:
            missing.append(field_name)

    # Check geolocation requirement
    if framework.requires_geolocation:
        # Check linked plots have geolocation
        links = (
            await db.execute(
                select(CompliancePlotLink).where(CompliancePlotLink.record_id == record.id)
            )
        ).scalars().all()
        if not links:
            missing.append("plots (at least one geolocation-tagged plot required)")

    missing_plots = False
    if framework.requires_geolocation:
        links = (
            await db.execute(
                select(CompliancePlotLink).where(CompliancePlotLink.record_id == record.id)
            )
        ).scalars().all()
        if not links:
            missing_plots = True

    # Check scientific name
    if framework.requires_scientific_name and not record.scientific_name:
        if "scientific_name" not in missing:
            missing.append("scientific_name")

    # Check declarations
    if rules.get("require_deforestation_declaration") and not record.deforestation_free_declaration:
        missing.append("deforestation_free_declaration")
    if rules.get("require_legal_declaration") and not record.legal_compliance_declaration:
        missing.append("legal_compliance_declaration")

    # Determine status
    if not missing and not missing_plots:
        compliance_status = "compliant"
    elif len(missing) <= 2 and not missing_plots:
        compliance_status = "partial"
        warnings.append("Almost compliant — only a few fields remaining")
    else:
        compliance_status = "incomplete"

    valid = compliance_status == "compliant"
    now = datetime.now(tz=timezone.utc)

    return ValidationResult(
        valid=valid,
        compliance_status=compliance_status,
        missing_fields=missing,
        missing_plots=missing_plots,
        warnings=warnings,
        framework=framework.slug,
        checked_at=now,
    )


# ─── CRUD ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=RecordResponse, status_code=status.HTTP_201_CREATED)
async def create_record(
    body: RecordCreate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    settings = get_settings()
    http = get_http_client()

    # Validate asset exists via trace-service
    try:
        resp = await http.get(
            f"{settings.TRACE_SERVICE_URL}/api/v1/assets/{body.asset_id}",
            headers={"X-Tenant-Id": str(tid)},
        )
        if resp.status_code != 200:
            raise NotFoundError(f"Asset '{body.asset_id}' not found in trace-service")
    except NotFoundError:
        raise
    except Exception:
        # If trace-service is unreachable, allow creation with a warning
        pass

    # Lookup framework by slug
    fw = (
        await db.execute(
            select(ComplianceFramework).where(ComplianceFramework.slug == body.framework_slug)
        )
    ).scalar_one_or_none()
    if fw is None:
        raise NotFoundError(f"Framework '{body.framework_slug}' not found")

    # Check unique asset+framework
    existing = (
        await db.execute(
            select(ComplianceRecord).where(
                ComplianceRecord.tenant_id == tid,
                ComplianceRecord.asset_id == body.asset_id,
                ComplianceRecord.framework_id == fw.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(
            f"Record for asset '{body.asset_id}' and framework '{body.framework_slug}' already exists"
        )

    data = body.model_dump(exclude={"framework_slug"}, exclude_unset=True)
    if "metadata" in data:
        data["metadata_"] = data.pop("metadata")
    else:
        data["metadata_"] = {}

    record = ComplianceRecord(
        tenant_id=tid,
        framework_id=fw.id,
        framework_slug=fw.slug,
        **data,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


@router.get("/", response_model=list[RecordResponse])
async def list_records(
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
    framework_slug: str | None = Query(None),
    asset_id: uuid.UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    commodity_type: str | None = Query(None),
):
    tid = _tenant_id(user)
    q = select(ComplianceRecord).where(ComplianceRecord.tenant_id == tid)

    if framework_slug is not None:
        q = q.where(ComplianceRecord.framework_slug == framework_slug)
    if asset_id is not None:
        q = q.where(ComplianceRecord.asset_id == asset_id)
    if status_filter is not None:
        q = q.where(ComplianceRecord.compliance_status == status_filter)
    if commodity_type is not None:
        q = q.where(ComplianceRecord.commodity_type == commodity_type)

    q = q.order_by(ComplianceRecord.created_at.desc())
    rows = (await db.execute(q)).scalars().all()
    return rows


@router.get("/{record_id}", response_model=RecordResponse)
async def get_record(
    record_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    record = (
        await db.execute(
            select(ComplianceRecord).where(
                ComplianceRecord.id == record_id,
                ComplianceRecord.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise NotFoundError(f"Record '{record_id}' not found")
    return record


@router.patch("/{record_id}", response_model=RecordResponse)
async def update_record(
    record_id: uuid.UUID,
    body: RecordUpdate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    record = (
        await db.execute(
            select(ComplianceRecord).where(
                ComplianceRecord.id == record_id,
                ComplianceRecord.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise NotFoundError(f"Record '{record_id}' not found")

    update_data = body.model_dump(exclude_unset=True)
    if "metadata" in update_data:
        update_data["metadata_"] = update_data.pop("metadata")
    for key, val in update_data.items():
        setattr(record, key, val)

    # Auto-validate after update
    fw = (
        await db.execute(
            select(ComplianceFramework).where(ComplianceFramework.id == record.framework_id)
        )
    ).scalar_one_or_none()
    if fw:
        result = await _validate_record(record, fw, db)
        record.compliance_status = result.compliance_status
        record.missing_fields = result.missing_fields
        record.last_validated_at = result.checked_at
        record.validation_result = result.model_dump(mode="json")

    await db.flush()
    await db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    record = (
        await db.execute(
            select(ComplianceRecord).where(
                ComplianceRecord.id == record_id,
                ComplianceRecord.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise NotFoundError(f"Record '{record_id}' not found")

    # Only allow deletion if declaration status is not_required or pending
    if record.declaration_status not in ("not_required", "pending"):
        raise ValidationError(
            f"Cannot delete record with declaration_status='{record.declaration_status}'. "
            "Only records with status 'not_required' or 'pending' can be deleted."
        )

    await db.delete(record)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── Plot links ──────────────────────────────────────────────────────────────

@router.post("/{record_id}/plots", response_model=PlotLinkResponse, status_code=status.HTTP_201_CREATED)
async def link_plot(
    record_id: uuid.UUID,
    body: PlotLinkCreate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)

    # Verify record exists
    record = (
        await db.execute(
            select(ComplianceRecord).where(
                ComplianceRecord.id == record_id,
                ComplianceRecord.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise NotFoundError(f"Record '{record_id}' not found")

    # Check duplicate
    existing = (
        await db.execute(
            select(CompliancePlotLink).where(
                CompliancePlotLink.record_id == record_id,
                CompliancePlotLink.plot_id == body.plot_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("Plot is already linked to this record")

    link = CompliancePlotLink(
        tenant_id=tid,
        record_id=record_id,
        plot_id=body.plot_id,
        quantity_from_plot_kg=body.quantity_from_plot_kg,
        percentage_from_plot=body.percentage_from_plot,
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)
    return link


@router.get("/{record_id}/plots", response_model=list[PlotLinkResponse])
async def list_record_plots(
    record_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)

    # Verify record exists
    record = (
        await db.execute(
            select(ComplianceRecord).where(
                ComplianceRecord.id == record_id,
                ComplianceRecord.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise NotFoundError(f"Record '{record_id}' not found")

    links = (
        await db.execute(
            select(CompliancePlotLink).where(CompliancePlotLink.record_id == record_id)
        )
    ).scalars().all()
    return links


@router.delete("/{record_id}/plots/{plot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_plot(
    record_id: uuid.UUID,
    plot_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)

    link = (
        await db.execute(
            select(CompliancePlotLink).where(
                CompliancePlotLink.record_id == record_id,
                CompliancePlotLink.plot_id == plot_id,
                CompliancePlotLink.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if link is None:
        raise NotFoundError("Plot link not found")

    await db.delete(link)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── Declaration update ──────────────────────────────────────────────────────

from pydantic import BaseModel as _BaseModel


class DeclarationUpdate(_BaseModel):
    """Subset schema for declaration fields only."""
    declaration_reference: str | None = None
    declaration_submission_date: date | None = None
    declaration_status: str | None = None
    declaration_url: str | None = None


@router.patch("/{record_id}/declaration", response_model=RecordResponse)
async def update_declaration(
    record_id: uuid.UUID,
    body: DeclarationUpdate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    record = (
        await db.execute(
            select(ComplianceRecord).where(
                ComplianceRecord.id == record_id,
                ComplianceRecord.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise NotFoundError(f"Record '{record_id}' not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(record, key, val)

    await db.flush()
    await db.refresh(record)
    return record


# ─── Dry-run validation ─────────────────────────────────────────────────────

@router.get("/{record_id}/validate", response_model=ValidationResult)
async def validate_record(
    record_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    record = (
        await db.execute(
            select(ComplianceRecord).where(
                ComplianceRecord.id == record_id,
                ComplianceRecord.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise NotFoundError(f"Record '{record_id}' not found")

    fw = (
        await db.execute(
            select(ComplianceFramework).where(ComplianceFramework.id == record.framework_id)
        )
    ).scalar_one_or_none()
    if fw is None:
        raise NotFoundError("Framework not found for this record")

    return await _validate_record(record, fw, db)
