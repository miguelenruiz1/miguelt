"""Router for compliance records — the core entity linking assets to frameworks."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select

async def _resolve_active_cert_number(db, record_id, tenant_id) -> str | None:
    """Return the active ComplianceCertificate number for a record, or None.

    Used by DDS builders — previously they called
    ``getattr(record, 'certificate_number', None)`` which always returned None
    because the record model has no such field.
    """
    from app.models.certificate import ComplianceCertificate
    row = (
        await db.execute(
            select(ComplianceCertificate.certificate_number)
            .where(
                ComplianceCertificate.record_id == record_id,
                ComplianceCertificate.tenant_id == tenant_id,
                ComplianceCertificate.status == "active",
            )
            .order_by(ComplianceCertificate.generated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return row
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, get_http_client
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.db.session import get_db_session
from app.models.framework import ComplianceFramework
from app.models.plot_link import CompliancePlotLink
from app.models.record import ComplianceRecord
from app.schemas.document_link import DocumentLinkCreate, DocumentLinkResponse, DocumentLinkWithUrl
from app.schemas.record import (
    PlotLinkCreate,
    PlotLinkResponse,
    RecordCreate,
    RecordResponse,
    RecordUpdate,
)
from app.schemas.validation import ValidationResult

log = get_logger(__name__)

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

    # Check geolocation requirement (single pass — was duplicated)
    missing_plots = False
    if framework.requires_geolocation:
        links = (
            await db.execute(
                select(CompliancePlotLink).where(CompliancePlotLink.record_id == record.id)
            )
        ).scalars().all()
        if not links:
            missing.append("plots (at least one geolocation-tagged plot required)")
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

    # Operator email — required by certificate generator and TRACES NT submit.
    # Either supplier_email or buyer_email is acceptable. Tracking it here keeps
    # the validator consistent with _validate_record_for_certificate.
    has_email = bool(
        (record.supplier_email and record.supplier_email.strip())
        or (record.buyer_email and record.buyer_email.strip())
    )
    if not has_email:
        missing.append("operator_email (supplier_email or buyer_email required)")

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

    # Validate asset exists via trace-service ONLY if asset_id was provided.
    # Standalone compliance records (no logistics asset) are allowed.
    if body.asset_id is not None:
        try:
            resp = await http.get(
                f"{settings.TRACE_SERVICE_URL}/api/v1/assets/{body.asset_id}",
                headers={"X-Tenant-Id": str(tid)},
            )
            if resp.status_code == 404:
                raise NotFoundError(f"Asset '{body.asset_id}' not found in trace-service")
        except NotFoundError:
            raise
        except Exception as exc:
            # If trace-service is unreachable, allow creation with a logged warning
            log.warning(
                "asset_validation_skipped",
                asset_id=str(body.asset_id),
                error=str(exc)[:200],
            )

    # Lookup framework by slug
    fw = (
        await db.execute(
            select(ComplianceFramework).where(ComplianceFramework.slug == body.framework_slug)
        )
    ).scalar_one_or_none()
    if fw is None:
        raise NotFoundError(f"Framework '{body.framework_slug}' not found")

    # Upsert semantics (MITECO/QA feedback): the auto-create-on-mint flow
    # pre-populates a shell record when an asset is minted, so a subsequent
    # POST with the same (asset_id, framework) used to collide. Treat the
    # POST as an idempotent upsert: if a record already exists AND it is
    # still pending/not_required (i.e. the operator hasn't submitted it),
    # merge the new fields into it and return 200. If it's already been
    # submitted, still 409 because overwriting submitted evidence is unsafe.
    data = body.model_dump(exclude={"framework_slug"}, exclude_unset=True)
    if "metadata" in data:
        data["metadata_"] = data.pop("metadata")

    if body.asset_id is not None:
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
            if existing.declaration_status not in ("not_required", "pending"):
                raise ConflictError(
                    f"Record for asset '{body.asset_id}' already submitted "
                    f"(declaration_status='{existing.declaration_status}'). "
                    "Use PATCH to update specific fields."
                )
            # Merge — only overwrite fields the client actually sent.
            for key, val in data.items():
                setattr(existing, key, val)
            await db.flush()
            await db.refresh(existing)
            return existing

    if "metadata_" not in data:
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

    # EUDR Art. 12: 5-year retention — block deletion if retention watermark
    # is set and still in the future. Applies even to 'not_required' records
    # if a manual retention date was set.
    if record.documents_retention_until is not None and record.documents_retention_until > date.today():
        raise ValidationError(
            f"Record está en periodo de retención EUDR hasta "
            f"{record.documents_retention_until.isoformat()} (Art. 12, 5 años). "
            "No se puede eliminar hasta esa fecha."
        )

    # Pre-check: a record with an issued certificate cannot be deleted.
    # Without this check the cascade blows up with a 500 on the FK to
    # compliance_certificates.record_id.
    from app.models.certificate import ComplianceCertificate as _Cert
    cert_count = (
        await db.execute(
            select(func.count())
            .select_from(_Cert)
            .where(_Cert.record_id == record_id, _Cert.tenant_id == tid)
        )
    ).scalar_one()
    if cert_count and cert_count > 0:
        raise ConflictError(
            f"No se puede eliminar: el record tiene {cert_count} certificado(s) "
            "emitido(s). Revoque primero los certificados o use el flujo de "
            "archivado si necesita conservar la evidencia."
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

    # CRITICAL: validate that the plot belongs to the SAME tenant. Without this
    # an attacker could link a deforestation-free plot from another tenant to
    # their own record and obtain a falsified certificate.
    from app.models.plot import CompliancePlot
    plot = (
        await db.execute(
            select(CompliancePlot).where(
                CompliancePlot.id == body.plot_id,
                CompliancePlot.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if plot is None:
        raise NotFoundError(f"Plot '{body.plot_id}' not found")

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
            # Clear any previous error
            md = dict(record.metadata_ or {})
            md.pop("last_cert_error", None)
            record.metadata_ = md
        except Exception as exc:
            log.warning("auto_regen_failed", record_id=str(record.id), exc=str(exc))
            # Surface the error to the UI via metadata_.last_cert_error so the
            # user can see why the cert was not generated after the DDS approval.
            md = dict(record.metadata_ or {})
            md["last_cert_error"] = {
                "message": str(exc)[:500],
                "occurred_at": datetime.now(tz=timezone.utc).isoformat(),
                "trigger": "auto_regen_on_dds",
            }
            record.metadata_ = md
            await db.flush()

    return record


# ─── Dry-run validation ─────────────────────────────────────────────────────

class CadmiumTestIn(_BaseModel):
    """Cadmium lab result payload.

    EU Reg 2023/915 caps Cd in cocoa-derived final products at 0.60 mg/kg.
    We compare the declared value against that threshold and persist the
    result on the compliance record for later DDS validation.
    """
    value_mg_per_kg: float
    test_date: date
    lab: str
    doc_hash: str | None = None
    notes: str | None = None


CADMIUM_EU_THRESHOLD_MG_PER_KG = 0.60


@router.post("/{record_id}/cadmium-test", response_model=RecordResponse)
async def register_cadmium_test(
    record_id: uuid.UUID,
    body: CadmiumTestIn,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Persist a cadmium lab result on the record (cacao-only)."""
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

    record.cadmium_mg_per_kg = body.value_mg_per_kg
    record.cadmium_test_date = body.test_date
    record.cadmium_test_lab = body.lab
    record.cadmium_test_doc_hash = body.doc_hash
    record.cadmium_eu_compliant = body.value_mg_per_kg <= CADMIUM_EU_THRESHOLD_MG_PER_KG
    if body.notes:
        md = dict(record.metadata_ or {})
        md.setdefault("cadmium_notes", []).append({
            "date": body.test_date.isoformat(),
            "notes": body.notes[:500],
        })
        record.metadata_ = md

    await db.flush()
    await db.refresh(record)
    log.info(
        "cadmium_test_registered",
        record_id=str(record.id),
        value=body.value_mg_per_kg,
        eu_compliant=record.cadmium_eu_compliant,
    )
    return record


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
    # Persist the compliance_status to DB (session dependency commits)
    record.compliance_status = result.compliance_status
    record.last_validated_at = result.checked_at
    record.validation_result = result.model_dump(mode="json")
    record.missing_fields = result.missing_fields
    await db.flush()
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

    # Load linked plots + their evidence documents (Art. 9.4 retention).
    from app.models.plot import CompliancePlot
    from app.models.document_link import CompliancePlotDocument, ComplianceRecordDocument
    links = (await db.execute(
        select(CompliancePlotLink).where(CompliancePlotLink.record_id == record_id)
    )).scalars().all()

    plots = []
    for link in links:
        plot = (await db.execute(
            select(CompliancePlot).where(CompliancePlot.id == link.plot_id)
        )).scalar_one_or_none()
        if plot:
            plot_docs = (await db.execute(
                select(CompliancePlotDocument).where(
                    CompliancePlotDocument.plot_id == plot.id,
                )
            )).scalars().all()
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
                "geojson_data": getattr(plot, "geojson_data", None),
                "geojson_arweave_url": getattr(plot, "geojson_arweave_url", None),
                "geojson_hash": getattr(plot, "geojson_hash", None),
                "satellite_report_url": getattr(plot, "satellite_report_url", None),
                "satellite_report_hash": getattr(plot, "satellite_report_hash", None),
                "geolocation_type": getattr(plot, "geolocation_type", None),
                "establishment_date": str(plot.establishment_date) if getattr(plot, "establishment_date", None) else None,
                "land_title_number": getattr(plot, "land_title_number", None),
                # EUDR Art. 8.2.f — derecho de uso / tenencia / titular
                "owner_name": getattr(plot, "owner_name", None),
                "owner_id_type": getattr(plot, "owner_id_type", None),
                "owner_id_number": getattr(plot, "owner_id_number", None),
                "producer_name": getattr(plot, "producer_name", None),
                "producer_id_type": getattr(plot, "producer_id_type", None),
                "producer_id_number": getattr(plot, "producer_id_number", None),
                "cadastral_id": getattr(plot, "cadastral_id", None),
                "tenure_type": getattr(plot, "tenure_type", None),
                "tenure_start_date": str(plot.tenure_start_date) if getattr(plot, "tenure_start_date", None) else None,
                "tenure_end_date": str(plot.tenure_end_date) if getattr(plot, "tenure_end_date", None) else None,
                "indigenous_territory_flag": bool(getattr(plot, "indigenous_territory_flag", False)),
                "documents": [
                    {
                        "id": str(d.id),
                        "media_file_id": str(d.media_file_id),
                        "document_type": d.document_type,
                        "filename": d.filename,
                        "file_hash": d.file_hash,
                        "description": d.description,
                        "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
                    }
                    for d in plot_docs
                ],
            })

    # Tambien documentos a nivel del record
    record_docs = (await db.execute(
        select(ComplianceRecordDocument).where(
            ComplianceRecordDocument.record_id == record_id,
        )
    )).scalars().all()

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
        "asset_id": str(record.asset_id) if record.asset_id else None,
        "certificate_number": await _resolve_active_cert_number(db, record_id, tid),
        "geo_location_confidential": getattr(record, "geo_location_confidential", False),
        "documents": [
            {
                "id": str(d.id),
                "media_file_id": str(d.media_file_id),
                "document_type": d.document_type,
                "filename": d.filename,
                "file_hash": d.file_hash,
                "description": d.description,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            }
            for d in record_docs
        ],
    }

    # Fetch custody events from trace-service for full traceability
    traceability_events = []
    try:
        settings = get_settings()
        trace_url = getattr(settings, "TRACE_SERVICE_URL", "")
        if trace_url and record.asset_id:
            http = get_http_client()
            resp = await http.get(
                f"{trace_url}/api/v1/assets/{record.asset_id}/events?limit=200",
                headers={
                    "X-Tenant-Id": user.get("tenant_id", "default") if isinstance(user, dict) else "default",
                    "X-Service-Token": settings.S2S_SERVICE_TOKEN,
                },
            )
            if resp.status_code == 200:
                events_data = resp.json().get("items", [])
                for ev in events_data:
                    traceability_events.append({
                        "event_id": ev.get("id"),
                        "event_type": ev.get("event_type"),
                        "timestamp": ev.get("timestamp"),
                        "from_wallet": ev.get("from_wallet"),
                        "to_wallet": ev.get("to_wallet"),
                        "location": ev.get("location"),
                        "notes": ev.get("notes"),
                        "event_hash": ev.get("event_hash"),
                        "anchored": ev.get("anchored", False),
                        "solana_tx_sig": ev.get("solana_tx_sig"),
                    })
    except Exception as exc:
        log.warning("dds_traceability_fetch_failed", record_id=str(record_id), exc=str(exc))

    from app.services.traces_service import build_dds_payload
    dds = build_dds_payload(record_dict, plots)

    return {
        "record_id": str(record_id),
        "dds_payload": dds,
        "traceability": traceability_events,
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

    # Lock the record row to serialize concurrent submits (e.g. user double-click).
    # Re-check status INSIDE the locked txn so the second click sees 'submitted'
    # and is rejected without re-hitting TRACES NT.
    record = (
        await db.execute(
            select(ComplianceRecord)
            .where(
                ComplianceRecord.id == record_id,
                ComplianceRecord.tenant_id == tid,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if record is None:
        raise NotFoundError(f"Record '{record_id}' not found")

    if record.declaration_status == "submitted" and record.declaration_reference:
        # Idempotent: return the existing reference instead of re-submitting
        return {
            "record_id": str(record_id),
            "submitted": True,
            "reference_number": record.declaration_reference,
            "already_submitted": True,
        }

    if record.compliance_status not in ("compliant", "partial", "declared", "ready"):
        raise ValidationError(
            f"Record must be 'compliant' (or at least 'partial') before submitting. "
            f"Current status: {record.compliance_status}"
        )

    # Operator email is mandatory for TRACES NT — fail-fast with a clear error.
    if not (record.buyer_email or record.supplier_email):
        raise ValidationError(
            "Falta operator/supplier email — TRACES NT lo requiere para sumisión DDS."
        )

    # Load plots + their evidence documents (Art. 9.4 retention)
    from app.models.plot import CompliancePlot
    from app.models.document_link import CompliancePlotDocument, ComplianceRecordDocument
    links = (await db.execute(
        select(CompliancePlotLink).where(CompliancePlotLink.record_id == record_id)
    )).scalars().all()

    plots = []
    for link in links:
        plot = (await db.execute(
            select(CompliancePlot).where(CompliancePlot.id == link.plot_id)
        )).scalar_one_or_none()
        if plot:
            plot_docs = (await db.execute(
                select(CompliancePlotDocument).where(
                    CompliancePlotDocument.plot_id == plot.id,
                )
            )).scalars().all()
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
                "geojson_data": getattr(plot, "geojson_data", None),
                "geojson_arweave_url": getattr(plot, "geojson_arweave_url", None),
                "geojson_hash": getattr(plot, "geojson_hash", None),
                "satellite_report_url": getattr(plot, "satellite_report_url", None),
                "satellite_report_hash": getattr(plot, "satellite_report_hash", None),
                "geolocation_type": getattr(plot, "geolocation_type", None),
                "establishment_date": str(plot.establishment_date) if getattr(plot, "establishment_date", None) else None,
                "land_title_number": getattr(plot, "land_title_number", None),
                # EUDR Art. 8.2.f — derecho de uso / tenencia / titular
                "owner_name": getattr(plot, "owner_name", None),
                "owner_id_type": getattr(plot, "owner_id_type", None),
                "owner_id_number": getattr(plot, "owner_id_number", None),
                "producer_name": getattr(plot, "producer_name", None),
                "producer_id_type": getattr(plot, "producer_id_type", None),
                "producer_id_number": getattr(plot, "producer_id_number", None),
                "cadastral_id": getattr(plot, "cadastral_id", None),
                "tenure_type": getattr(plot, "tenure_type", None),
                "tenure_start_date": str(plot.tenure_start_date) if getattr(plot, "tenure_start_date", None) else None,
                "tenure_end_date": str(plot.tenure_end_date) if getattr(plot, "tenure_end_date", None) else None,
                "indigenous_territory_flag": bool(getattr(plot, "indigenous_territory_flag", False)),
                "documents": [
                    {
                        "id": str(d.id),
                        "media_file_id": str(d.media_file_id),
                        "document_type": d.document_type,
                        "filename": d.filename,
                        "file_hash": d.file_hash,
                        "description": d.description,
                        "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
                    }
                    for d in plot_docs
                ],
            })

    record_docs_submit = (await db.execute(
        select(ComplianceRecordDocument).where(
            ComplianceRecordDocument.record_id == record_id,
        )
    )).scalars().all()

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
        "asset_id": str(record.asset_id) if record.asset_id else None,
        "certificate_number": await _resolve_active_cert_number(db, record_id, tid),
        "geo_location_confidential": getattr(record, "geo_location_confidential", False),
        "documents": [
            {
                "id": str(d.id),
                "media_file_id": str(d.media_file_id),
                "document_type": d.document_type,
                "filename": d.filename,
                "file_hash": d.file_hash,
                "description": d.description,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            }
            for d in record_docs_submit
        ],
        "signatory_name": getattr(record, "signatory_name", None),
        "signatory_role": getattr(record, "signatory_role", None),
        "signatory_date": str(getattr(record, "signatory_date", "")) if getattr(record, "signatory_date", None) else "",
        "prior_dds_references": getattr(record, "prior_dds_references", None),
    }

    from app.services.traces_service import build_dds_payload, TracesNTService
    dds = build_dds_payload(record_dict, plots)

    svc = await TracesNTService.from_db(db, tenant_id=tid)
    result = await svc.submit_dds(dds)

    # If submitted successfully, update record with reference
    if result.get("submitted") and result.get("reference_number"):
        record.declaration_reference = result["reference_number"]
        record.declaration_status = "submitted"
        submission_day = date.today()
        record.declaration_submission_date = submission_day
        # EUDR Art. 12: keep evidence accessible for at least 5 years after
        # submission. Set the retention watermark unless already set to a
        # later date (eg. manual override).
        retention_target = date(submission_day.year + 5, submission_day.month, submission_day.day)
        if record.documents_retention_until is None or record.documents_retention_until < retention_target:
            record.documents_retention_until = retention_target
        await db.flush()
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

    # Check duplicate (tenant-scoped to avoid cross-tenant existence probes)
    existing = (
        await db.execute(
            select(ComplianceRecordDocument).where(
                ComplianceRecordDocument.record_id == record_id,
                ComplianceRecordDocument.media_file_id == body.media_file_id,
                ComplianceRecordDocument.tenant_id == tid,
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
