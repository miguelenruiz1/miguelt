"""Router for compliance records — the core entity linking assets to frameworks."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, get_http_client
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger

log = get_logger(__name__)
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
from app.schemas.document_link import DocumentLinkCreate, DocumentLinkResponse, DocumentLinkWithUrl
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
    old_status = record.declaration_status
    for key, val in update_data.items():
        setattr(record, key, val)

    await db.flush()
    await db.refresh(record)

    # Auto-regenerate certificate when DDS is approved
    new_status = update_data.get("declaration_status")
    if new_status in ("submitted", "accepted", "approved") and old_status != new_status:
        try:
            from app.certificates.generator import CertificateGenerator
            gen = CertificateGenerator(db)
            user_id = uuid.UUID(user.get("id")) if user.get("id") not in (None, "system") else None
            await gen.generate(record.id, _tenant_id(user), user_id)
            log.info("auto_regen_on_dds", record_id=str(record.id), new_status=new_status)
        except Exception as exc:
            log.warning("auto_regen_failed", record_id=str(record.id), exc=str(exc))

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

    result = await _validate_record(record, fw, db)
    # Persist the compliance_status to DB
    record.compliance_status = result.compliance_status
    record.last_validated_at = result.checked_at
    record.validation_result = result.model_dump(mode="json")
    record.missing_fields = result.missing_fields
    await db.commit()
    return result


# ─── TRACES NT — DDS Export & Submission ───────────────────────────────────────

@router.post("/{record_id}/export-dds")
async def export_dds(
    record_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Export DDS payload in TRACES NT format (JSON).

    Use this to review the DDS before submitting, or to manually
    upload to TRACES NT if auto-submission is not configured.
    """
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

    # Load linked plots
    from app.models.plot import CompliancePlot
    links = (await db.execute(
        select(CompliancePlotLink).where(CompliancePlotLink.record_id == record_id)
    )).scalars().all()

    plots = []
    for link in links:
        plot = (await db.execute(
            select(CompliancePlot).where(CompliancePlot.id == link.plot_id)
        )).scalar_one_or_none()
        if plot:
            plots.append({
                "plot_code": plot.plot_code,
                "lat": float(plot.lat) if plot.lat else None,
                "lng": float(plot.lng) if plot.lng else None,
                "plot_area_ha": float(plot.plot_area_ha) if plot.plot_area_ha else None,
                "country_code": plot.country_code,
                "municipality": plot.municipality,
                "region": plot.region,
                "risk_level": plot.risk_level,
                "deforestation_free": plot.deforestation_free,
                "establishment_date": str(plot.establishment_date) if getattr(plot, "establishment_date", None) else None,
            })

    # Build record dict
    record_dict = {
        "id": str(record.id),
        "framework_slug": record.framework_slug,
        "hs_code": record.hs_code,
        "commodity_type": record.commodity_type,
        "product_description": record.product_description,
        "scientific_name": record.scientific_name,
        "quantity_kg": float(record.quantity_kg) if record.quantity_kg else 0,
        "country_of_production": record.country_of_production,
        "production_period_start": str(record.production_period_start) if record.production_period_start else "",
        "production_period_end": str(record.production_period_end) if record.production_period_end else "",
        "supplier_name": record.supplier_name,
        "supplier_address": record.supplier_address,
        "supplier_email": record.supplier_email,
        "buyer_name": record.buyer_name,
        "buyer_address": record.buyer_address,
        "buyer_email": record.buyer_email,
        "operator_eori": record.operator_eori,
        "activity_type": getattr(record, "activity_type", "export"),
        "deforestation_free_declaration": record.deforestation_free_declaration,
        "legal_compliance_declaration": record.legal_compliance_declaration,
        "signatory_name": getattr(record, "signatory_name", None),
        "signatory_role": getattr(record, "signatory_role", None),
        "signatory_date": str(getattr(record, "signatory_date", "")) if getattr(record, "signatory_date", None) else "",
        "prior_dds_references": getattr(record, "prior_dds_references", None),
    }

    from app.services.traces_service import build_dds_payload
    dds = build_dds_payload(record_dict, plots)

    return {
        "record_id": str(record_id),
        "dds_payload": dds,
        "traces_nt_configured": bool(get_settings().TRACES_NT_USERNAME),
        "format": "TRACES NT DDS v2",
    }


@router.post("/{record_id}/submit-traces")
async def submit_to_traces(
    record_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Submit DDS to TRACES NT (EU information system).

    Requires TRACES_NT_USERNAME and TRACES_NT_AUTH_KEY in environment.
    If not configured, returns the DDS payload for manual submission.
    """
    # First export the DDS
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

    if record.compliance_status not in ("ready", "declared", "compliant"):
        raise ValidationError(
            f"Record must be 'ready', 'declared' or 'compliant' to submit. "
            f"Current status: {record.compliance_status}"
        )

    # Load plots
    from app.models.plot import CompliancePlot
    links = (await db.execute(
        select(CompliancePlotLink).where(CompliancePlotLink.record_id == record_id)
    )).scalars().all()

    plots = []
    for link in links:
        plot = (await db.execute(
            select(CompliancePlot).where(CompliancePlot.id == link.plot_id)
        )).scalar_one_or_none()
        if plot:
            plots.append({
                "plot_code": plot.plot_code,
                "lat": float(plot.lat) if plot.lat else None,
                "lng": float(plot.lng) if plot.lng else None,
                "plot_area_ha": float(plot.plot_area_ha) if plot.plot_area_ha else None,
                "country_code": plot.country_code,
                "municipality": plot.municipality,
                "risk_level": plot.risk_level,
                "deforestation_free": plot.deforestation_free,
                "establishment_date": str(plot.establishment_date) if getattr(plot, "establishment_date", None) else None,
            })

    record_dict = {
        "id": str(record.id),
        "framework_slug": record.framework_slug,
        "hs_code": record.hs_code,
        "commodity_type": record.commodity_type,
        "product_description": record.product_description,
        "scientific_name": record.scientific_name,
        "quantity_kg": float(record.quantity_kg) if record.quantity_kg else 0,
        "country_of_production": record.country_of_production,
        "production_period_start": str(record.production_period_start) if record.production_period_start else "",
        "production_period_end": str(record.production_period_end) if record.production_period_end else "",
        "supplier_name": record.supplier_name,
        "supplier_address": record.supplier_address,
        "supplier_email": record.supplier_email,
        "buyer_name": record.buyer_name,
        "buyer_address": record.buyer_address,
        "buyer_email": record.buyer_email,
        "operator_eori": record.operator_eori,
        "activity_type": getattr(record, "activity_type", "export"),
        "deforestation_free_declaration": record.deforestation_free_declaration,
        "legal_compliance_declaration": record.legal_compliance_declaration,
        "signatory_name": getattr(record, "signatory_name", None),
        "signatory_role": getattr(record, "signatory_role", None),
        "signatory_date": str(getattr(record, "signatory_date", "")) if getattr(record, "signatory_date", None) else "",
        "prior_dds_references": getattr(record, "prior_dds_references", None),
    }

    from app.services.traces_service import build_dds_payload, TracesNTService
    dds = build_dds_payload(record_dict, plots)

    svc = await TracesNTService.from_db(db)
    result = await svc.submit_dds(dds)

    # If submitted successfully, update record with reference
    if result.get("submitted") and result.get("reference_number"):
        record.declaration_reference = result["reference_number"]
        record.declaration_status = "submitted"
        record.declaration_submission_date = date.today()
        await db.flush()
        await db.commit()
        log.info("dds_submitted_traces", record_id=str(record_id), ref=result["reference_number"])

    return {
        "record_id": str(record_id),
        **result,
    }


# ─── Evidence documents ────────────────────────────────────────────────────────

from app.models.document_link import ComplianceRecordDocument


@router.post("/{record_id}/documents", response_model=DocumentLinkResponse, status_code=status.HTTP_201_CREATED)
async def attach_document(
    record_id: uuid.UUID,
    body: DocumentLinkCreate,
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
            select(ComplianceRecordDocument).where(
                ComplianceRecordDocument.record_id == record_id,
                ComplianceRecordDocument.media_file_id == body.media_file_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("Document already linked to this record")

    # Try to fetch file metadata from media-service for hash/filename caching
    file_hash = None
    filename = None
    try:
        http = get_http_client()
        settings = get_settings()
        resp = await http.get(
            f"{settings.MEDIA_SERVICE_URL}/api/v1/internal/media/files/{body.media_file_id}",
            headers={
                "X-Service-Token": settings.S2S_SERVICE_TOKEN,
                "X-Tenant-Id": str(tid),
            },
        )
        if resp.status_code == 200:
            fdata = resp.json()
            file_hash = fdata.get("file_hash")
            filename = fdata.get("original_filename") or fdata.get("filename")
    except Exception:
        pass

    doc = ComplianceRecordDocument(
        tenant_id=tid,
        record_id=record_id,
        media_file_id=body.media_file_id,
        document_type=body.document_type,
        file_hash=file_hash,
        filename=filename,
        description=body.description,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.get("/{record_id}/documents", response_model=list[DocumentLinkWithUrl])
async def list_record_documents(
    record_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)

    docs = (
        await db.execute(
            select(ComplianceRecordDocument).where(
                ComplianceRecordDocument.record_id == record_id,
                ComplianceRecordDocument.tenant_id == tid,
            )
        )
    ).scalars().all()

    # Enrich with media URLs
    results = []
    http = get_http_client()
    settings = get_settings()
    for doc in docs:
        url = None
        try:
            resp = await http.get(
                f"{settings.MEDIA_SERVICE_URL}/api/v1/internal/media/files/{doc.media_file_id}",
                headers={
                    "X-Service-Token": settings.S2S_SERVICE_TOKEN,
                    "X-Tenant-Id": str(tid),
                },
            )
            if resp.status_code == 200:
                url = resp.json().get("url")
        except Exception:
            pass
        r = DocumentLinkWithUrl.model_validate(doc)
        r.url = url
        results.append(r)

    return results


@router.delete("/{record_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_document(
    record_id: uuid.UUID,
    doc_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    doc = (
        await db.execute(
            select(ComplianceRecordDocument).where(
                ComplianceRecordDocument.id == doc_id,
                ComplianceRecordDocument.record_id == record_id,
                ComplianceRecordDocument.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if doc is None:
        raise NotFoundError("Document link not found")

    await db.delete(doc)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── Media reference counts (shared across records + plots) ──────────────────

@router.post("/media-reference-counts")
async def media_reference_counts(
    file_ids: list[str],
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Count how many compliance records and plots reference each media file."""
    from sqlalchemy import func
    from app.models.document_link import ComplianceRecordDocument, CompliancePlotDocument

    tid = _tenant_id(user)
    uuids = [uuid.UUID(fid) for fid in file_ids]

    # Count from record documents
    rec_rows = (
        await db.execute(
            select(
                ComplianceRecordDocument.media_file_id,
                func.count(ComplianceRecordDocument.id).label("count"),
            )
            .where(
                ComplianceRecordDocument.media_file_id.in_(uuids),
                ComplianceRecordDocument.tenant_id == tid,
            )
            .group_by(ComplianceRecordDocument.media_file_id)
        )
    ).all()

    # Count from plot documents
    plot_rows = (
        await db.execute(
            select(
                CompliancePlotDocument.media_file_id,
                func.count(CompliancePlotDocument.id).label("count"),
            )
            .where(
                CompliancePlotDocument.media_file_id.in_(uuids),
                CompliancePlotDocument.tenant_id == tid,
            )
            .group_by(CompliancePlotDocument.media_file_id)
        )
    ).all()

    counts: dict[str, int] = {}
    for r in rec_rows:
        counts[str(r[0])] = counts.get(str(r[0]), 0) + r[1]
    for r in plot_rows:
        counts[str(r[0])] = counts.get(str(r[0]), 0) + r[1]

    return {"counts": counts, "source": "compliance"}
