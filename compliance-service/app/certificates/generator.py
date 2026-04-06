"""Certificate generation orchestrator — 10-step algorithm."""
from __future__ import annotations

import hashlib
import os
import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_http_client
from app.certificates.pdf_builder import render_certificate_pdf
from app.certificates.qr_builder import generate_qr, generate_qr_base64
from app.certificates.storage import get_storage
from app.core.errors import CertificateNotReadyError, NotFoundError
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.models.certificate import ComplianceCertificate
from app.models.document_link import ComplianceRecordDocument, CompliancePlotDocument
from app.models.framework import ComplianceFramework
from app.models.plot import CompliancePlot
from app.models.plot_link import CompliancePlotLink
from app.models.record import ComplianceRecord
from app.models.risk_assessment import ComplianceRiskAssessment
from app.models.supply_chain_node import ComplianceSupplyChainNode
from app.repositories.certificate_repo import CertificateRepository

log = get_logger(__name__)

VALID_STATUSES_FOR_CERT = {"compliant", "partial", "declared", "ready"}

# ── Lookup tables ───────────────────────────────────────────────────────────

COMMODITY_LABELS: dict[str, str] = {
    "cafe": "Café",
    "coffee": "Café",
    "cacao": "Cacao en grano",
    "cocoa": "Cacao en grano",
    "soja": "Soja",
    "soy": "Soja",
    "soya": "Soja",
    "palma": "Aceite de palma",
    "palm_oil": "Aceite de palma",
    "palm": "Aceite de palma",
    "madera": "Madera",
    "wood": "Madera",
    "timber": "Madera",
    "caucho": "Caucho",
    "rubber": "Caucho",
    "ganado": "Ganado bovino",
    "cattle": "Ganado bovino",
    "beef": "Ganado bovino",
}

COUNTRY_LABELS: dict[str, str] = {
    "CO": "Colombia",
    "BR": "Brasil",
    "PE": "Perú",
    "EC": "Ecuador",
    "MX": "México",
    "GT": "Guatemala",
    "HN": "Honduras",
    "CR": "Costa Rica",
    "NI": "Nicaragua",
    "SV": "El Salvador",
    "PA": "Panamá",
    "VE": "Venezuela",
    "BO": "Bolivia",
    "PY": "Paraguay",
    "UY": "Uruguay",
    "AR": "Argentina",
    "CL": "Chile",
    "ID": "Indonesia",
    "MY": "Malasia",
    "VN": "Vietnam",
    "GH": "Ghana",
    "CI": "Costa de Marfil",
    "NG": "Nigeria",
    "CM": "Camerún",
    "ET": "Etiopía",
    "KE": "Kenia",
    "TZ": "Tanzania",
    "UG": "Uganda",
    "CD": "Rep. Dem. del Congo",
    "CG": "Rep. del Congo",
}

RISK_LABELS: dict[str, str] = {
    "low": "Bajo",
    "standard": "Estándar",
    "high": "Alto",
}

# ── Required-fields validation ──────────────────────────────────────────────

# supplier_email is checked separately because either supplier_email or buyer_email
# is acceptable (matches submit_to_traces behavior).
REQUIRED_RECORD_FIELDS = [
    "hs_code",
    "commodity_type",
    "product_description",
    "quantity_kg",
    "country_of_production",
    "production_period_start",
    "production_period_end",
    "supplier_name",
    "supplier_address",
]


def _validate_record_for_certificate(
    record: ComplianceRecord,
    plots: list[dict[str, Any]],
) -> None:
    """Raise CertificateNotReadyError if the record is missing required data."""
    missing: list[str] = []

    for field in REQUIRED_RECORD_FIELDS:
        val = getattr(record, field, None)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)

    # Either supplier_email or buyer_email is acceptable (operator email)
    if not (
        (record.supplier_email and record.supplier_email.strip())
        or (record.buyer_email and record.buyer_email.strip())
    ):
        missing.append("supplier_email or buyer_email (operator email required)")

    if not record.deforestation_free_declaration:
        missing.append("deforestation_free_declaration (must be True)")

    if not record.legal_compliance_declaration:
        missing.append("legal_compliance_declaration (must be True)")

    if not plots:
        missing.append("plots (at least 1 plot must be linked)")

    # EUDR Art. 9.1.c / Art. 2.28: plots >= 4 ha require polygon
    for plot in plots:
        area = plot.get("plot_area_ha")
        has_polygon = (
            plot.get("geojson_arweave_url")
            or plot.get("geojson_hash")
            or plot.get("geojson_data")
            or plot.get("geolocation_type") == "polygon"
        )
        if area and float(area) >= 4.0 and not has_polygon:
            missing.append(
                f"plot '{plot.get('plot_code', '?')}': parcela >= 4 ha requiere poligono "
                "— EUDR Art. 9.1.c / Art. 2.28"
            )

    if missing:
        raise CertificateNotReadyError(
            f"Record is missing required fields for EUDR certification: {', '.join(missing)}"
        )


# ── Helpers ─────────────────────────────────────────────────────────────────

def _fmt_date(d: date | datetime | str | None) -> str:
    """Format a date-like value to dd/mm/yyyy string."""
    if d is None:
        return "—"
    if isinstance(d, str):
        return d
    if isinstance(d, datetime):
        return d.strftime("%d/%m/%Y")
    return d.strftime("%d/%m/%Y")


def _fmt_lat(lat: float | None) -> str:
    """Format latitude as '1.856234°N' or '1.856234°S'."""
    if lat is None:
        return "—"
    suffix = "N" if lat >= 0 else "S"
    return f"{abs(lat):.6f}°{suffix}"


def _fmt_lng(lng: float | None) -> str:
    """Format longitude as '76.051823°O' or '76.051823°E'."""
    if lng is None:
        return "—"
    suffix = "O" if lng < 0 else "E"
    return f"{abs(lng):.6f}°{suffix}"


def _build_blockchain_context(asset_data: dict | None) -> dict[str, Any]:
    """Build the blockchain context dict from trace-service asset data."""
    from app.core.settings import get_settings
    solana_network = get_settings().SOLANA_NETWORK
    network_labels = {
        "devnet": "Solana Devnet",
        "testnet": "Solana Testnet",
        "mainnet-beta": "Solana Mainnet",
    }
    network = network_labels.get(solana_network, f"Solana {solana_network}")

    if asset_data is None:
        return {
            "network": network,
            "cnft_address": None,
            "tx_sig": None,
            "explorer_url": None,
            "is_simulated": True,
        }

    cnft_address = asset_data.get("blockchain_asset_id") or asset_data.get("solana_address")
    tx_sig = asset_data.get("blockchain_tx_signature") or asset_data.get("blockchain_tx")
    blockchain_status = asset_data.get("blockchain_status", "")

    is_simulated = blockchain_status in ("SIMULATED", "SKIPPED", "PENDING", "")

    # Detect placeholder addresses
    if cnft_address and (
        str(cnft_address).startswith("pending_")
        or str(cnft_address).startswith("sim")
    ):
        cnft_address = None
        is_simulated = True

    explorer_url = None
    if cnft_address:
        cluster_param = "?cluster=devnet" if solana_network == "devnet" else ""
        explorer_url = f"https://explorer.solana.com/address/{cnft_address}{cluster_param}"

    return {
        "network": network,
        "cnft_address": cnft_address,
        "tx_sig": tx_sig,
        "explorer_url": explorer_url,
        "is_simulated": is_simulated,
    }


class CertificateGenerator:
    """Orchestrates certificate PDF generation."""

    def __init__(self, session: AsyncSession) -> None:
        self.db = session
        self.repo = CertificateRepository(session)
        self.storage = get_storage()
        self.settings = get_settings()

    async def generate(
        self,
        record_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> ComplianceCertificate:
        """Generate a certificate following the 10-step algorithm.

        On error the certificate row is updated with generation_error
        instead of raising.
        """

        # ── Step 1: Load record, validate status ──────────────────────────────
        record = (
            await self.db.execute(
                select(ComplianceRecord).where(
                    ComplianceRecord.id == record_id,
                    ComplianceRecord.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if record is None:
            raise NotFoundError(f"Record '{record_id}' not found")

        if record.compliance_status not in VALID_STATUSES_FOR_CERT:
            raise CertificateNotReadyError(
                f"Record status '{record.compliance_status}' is not eligible for certification. "
                f"Must be one of: {', '.join(sorted(VALID_STATUSES_FOR_CERT))}"
            )

        # ── Step 1b: Load plots early for validation ──────────────────────────
        plot_links = (
            await self.db.execute(
                select(CompliancePlotLink).where(CompliancePlotLink.record_id == record_id)
            )
        ).scalars().all()

        plots: list[dict[str, Any]] = []
        for link in plot_links:
            plot = (
                await self.db.execute(
                    select(CompliancePlot).where(CompliancePlot.id == link.plot_id)
                )
            ).scalar_one_or_none()
            if plot is not None:
                lat = float(plot.lat) if plot.lat else None
                lng = float(plot.lng) if plot.lng else None
                plots.append({
                    "plot_code": plot.plot_code,
                    "country_code": plot.country_code,
                    "region": plot.region,
                    "municipality": plot.municipality,
                    "lat": lat,
                    "lng": lng,
                    "lat_formatted": _fmt_lat(lat),
                    "lng_formatted": _fmt_lng(lng),
                    "plot_area_ha": float(plot.plot_area_ha) if plot.plot_area_ha else None,
                    "geolocation_type": getattr(plot, "geolocation_type", None),
                    "geojson_data": getattr(plot, "geojson_data", None),
                    "geojson_arweave_url": plot.geojson_arweave_url,
                    "geojson_hash": plot.geojson_hash,
                    "deforestation_free": plot.deforestation_free,
                    "cutoff_date_compliant": plot.cutoff_date_compliant,
                    "legal_land_use": plot.legal_land_use,
                    "risk_level": plot.risk_level,
                    "risk_label": RISK_LABELS.get(plot.risk_level or "", "Estándar"),
                    "establishment_date": _fmt_date(getattr(plot, "establishment_date", None)),
                    "crop_type": getattr(plot, "crop_type", None),
                    "renovation_date": _fmt_date(getattr(plot, "renovation_date", None)),
                    "renovation_type": getattr(plot, "renovation_type", None),
                    "quantity_from_plot_kg": float(link.quantity_from_plot_kg) if link.quantity_from_plot_kg else None,
                    "percentage_from_plot": float(link.percentage_from_plot) if link.percentage_from_plot else None,
                })

        # ── Step 1c: Validate required fields ─────────────────────────────────
        _validate_record_for_certificate(record, plots)

        # ── Step 2: Idempotency — return existing active cert ─────────────────
        existing = await self.repo.get_by_record(record_id, status="active")
        if existing is not None:
            log.info("certificate_exists", record_id=str(record_id), cert_id=str(existing.id))
            return existing

        # Load framework
        framework = (
            await self.db.execute(
                select(ComplianceFramework).where(ComplianceFramework.id == record.framework_id)
            )
        ).scalar_one_or_none()

        now = datetime.now(tz=timezone.utc)
        year = now.year
        cert_number = await self.repo.get_next_number(year)
        verify_url = f"{self.settings.CERTIFICATE_VERIFY_BASE_URL}/{cert_number}"

        valid_from = now.date()
        retention_years = framework.document_retention_years if framework else 5
        valid_until = date(year + retention_years, valid_from.month, valid_from.day)

        # ── Step 3: Create DB row with status=generating ──────────────────────
        cert = await self.repo.create(
            tenant_id=tenant_id,
            record_id=record_id,
            certificate_number=cert_number,
            framework_slug=record.framework_slug,
            asset_id=record.asset_id,
            status="generating",
            verify_url=verify_url,
            valid_from=valid_from,
            valid_until=valid_until,
            generated_by=user_id,
            metadata_={},
        )

        try:
            # ── Step 4: Generate QR code → upload to storage ──────────────────
            qr_bytes = generate_qr(verify_url)
            qr_filename = f"{cert_number}_qr.png"
            qr_url = await self.storage.upload(
                tenant_id=str(tenant_id),
                year=year,
                filename=qr_filename,
                data=qr_bytes,
                content_type="image/png",
            )
            qr_base64 = generate_qr_base64(verify_url)

            # ── Step 5: Fetch asset data from trace-service (non-fatal) ───────
            asset_data: dict | None = None
            if record.asset_id is not None:
                try:
                    http = get_http_client()
                    resp = await http.get(
                        f"{self.settings.TRACE_SERVICE_URL}/api/v1/assets/{record.asset_id}",
                        headers={"X-Tenant-Id": str(tenant_id)},
                    )
                    if resp.status_code == 200:
                        asset_data = resp.json()
                except Exception as exc:
                    log.warning("asset_fetch_failed", asset_id=str(record.asset_id), error=str(exc))

            # ── Step 5b: Load risk assessment, supply chain, documents ────────
            risk_assessment_data: dict | None = None
            ra = (
                await self.db.execute(
                    select(ComplianceRiskAssessment).where(
                        ComplianceRiskAssessment.record_id == record_id,
                        ComplianceRiskAssessment.tenant_id == tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if ra is not None:
                risk_assessment_data = {
                    "country_risk_level": ra.country_risk_level,
                    "country_risk_label": RISK_LABELS.get(ra.country_risk_level or "", "—"),
                    "country_risk_notes": ra.country_risk_notes,
                    "country_benchmarking_source": ra.country_benchmarking_source,
                    "supply_chain_risk_level": ra.supply_chain_risk_level,
                    "supply_chain_risk_label": RISK_LABELS.get(ra.supply_chain_risk_level or "", "—"),
                    "supply_chain_notes": ra.supply_chain_notes,
                    "supplier_verification_status": ra.supplier_verification_status,
                    "traceability_confidence": ra.traceability_confidence,
                    "regional_risk_level": ra.regional_risk_level,
                    "regional_risk_label": RISK_LABELS.get(ra.regional_risk_level or "", "—"),
                    "deforestation_prevalence": ra.deforestation_prevalence,
                    "indigenous_rights_risk": ra.indigenous_rights_risk,
                    "overall_risk_level": ra.overall_risk_level,
                    "overall_risk_label": RISK_LABELS.get(ra.overall_risk_level or "", ra.overall_risk_level or "—"),
                    "conclusion": ra.conclusion,
                    "conclusion_notes": ra.conclusion_notes,
                    "mitigation_measures": ra.mitigation_measures or [],
                    "status": ra.status,
                    "assessed_at": _fmt_date(ra.assessed_at),
                }

            supply_chain_data: list[dict] = []
            sc_nodes = (
                await self.db.execute(
                    select(ComplianceSupplyChainNode)
                    .where(
                        ComplianceSupplyChainNode.record_id == record_id,
                        ComplianceSupplyChainNode.tenant_id == tenant_id,
                    )
                    .order_by(ComplianceSupplyChainNode.sequence_order)
                )
            ).scalars().all()
            role_labels = {
                "producer": "Productor", "collector": "Recolector",
                "processor": "Procesador", "exporter": "Exportador",
                "importer": "Importador", "trader": "Comerciante",
            }
            for node in sc_nodes:
                supply_chain_data.append({
                    "sequence_order": node.sequence_order,
                    "role": node.role,
                    "role_label": role_labels.get(node.role, node.role),
                    "actor_name": node.actor_name,
                    "actor_country": node.actor_country,
                    "actor_country_label": COUNTRY_LABELS.get((node.actor_country or "").upper(), node.actor_country),
                    "actor_tax_id": node.actor_tax_id,
                    "actor_eori": node.actor_eori,
                    "handoff_date": _fmt_date(node.handoff_date),
                    "quantity_kg": float(node.quantity_kg) if node.quantity_kg else None,
                    "verification_status": node.verification_status,
                })

            doc_type_labels = {
                "land_title": "Título de tierra", "legal_cert": "Certificado legal",
                "deforestation_report": "Reporte de deforestación",
                "satellite_image": "Imagen satelital",
                "supplier_declaration": "Declaración de proveedor",
                "transport_doc": "Documento de transporte",
                "geojson_boundary": "Polígono GeoJSON", "other": "Otro",
            }
            record_docs_data: list[dict] = []
            rec_docs = (
                await self.db.execute(
                    select(ComplianceRecordDocument).where(
                        ComplianceRecordDocument.record_id == record_id,
                        ComplianceRecordDocument.tenant_id == tenant_id,
                    )
                )
            ).scalars().all()
            for doc in rec_docs:
                record_docs_data.append({
                    "document_type": doc.document_type,
                    "type_label": doc_type_labels.get(doc.document_type, doc.document_type),
                    "filename": doc.filename,
                    "file_hash": doc.file_hash,
                    "description": doc.description,
                    "uploaded_at": _fmt_date(doc.uploaded_at),
                })

            # ── Step 6: Build context & render HTML with Jinja2 ───────────────
            blockchain = _build_blockchain_context(asset_data)

            fw_name = framework.name if framework else record.framework_slug.upper()
            fw_cutoff = _fmt_date(framework.cutoff_date) if framework and framework.cutoff_date else "31/12/2020"

            context = {
                "certificate": {
                    "number": cert_number,
                    "verify_url": verify_url,
                    "valid_from": _fmt_date(valid_from),
                    "valid_until": _fmt_date(valid_until),
                    "status": "active",
                    "generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "qr_code_base64": qr_base64,
                },
                "framework": {
                    "slug": record.framework_slug,
                    "name": fw_name,
                    "full_name": (
                        "Reglamento (UE) 2023/1115 — Productos libres de deforestación"
                        if record.framework_slug == "eudr"
                        else fw_name
                    ),
                    "issuing_body": framework.issuing_body if framework else None,
                    "legal_reference": framework.legal_reference if framework else None,
                    "cutoff_date": fw_cutoff,
                    "document_retention_years": retention_years,
                },
                "record": {
                    "id": str(record.id),
                    "commodity_type": record.commodity_type,
                    "commodity_label": COMMODITY_LABELS.get(
                        (record.commodity_type or "").lower(), record.commodity_type
                    ),
                    "hs_code": record.hs_code,
                    "product_description": record.product_description,
                    "scientific_name": record.scientific_name,
                    "quantity_kg": float(record.quantity_kg) if record.quantity_kg else None,
                    "quantity_unit": record.quantity_unit,
                    "country_of_production": record.country_of_production,
                    "country_label": COUNTRY_LABELS.get(
                        (record.country_of_production or "").upper(),
                        record.country_of_production,
                    ),
                    "production_period_start": _fmt_date(record.production_period_start),
                    "production_period_end": _fmt_date(record.production_period_end),
                    "supplier_name": record.supplier_name,
                    "supplier_address": record.supplier_address,
                    "supplier_email": record.supplier_email,
                    "buyer_name": record.buyer_name,
                    "buyer_address": record.buyer_address,
                    "buyer_email": record.buyer_email,
                    "operator_eori": record.operator_eori,
                    "deforestation_free_declaration": record.deforestation_free_declaration,
                    "legal_compliance_declaration": record.legal_compliance_declaration,
                    "declaration_reference": record.declaration_reference,
                    "declaration_submission_date": _fmt_date(record.declaration_submission_date),
                    "declaration_status": record.declaration_status,
                    # Annex II #2 — Activity type
                    "activity_type": getattr(record, "activity_type", "export"),
                    # Annex II #10 — Signatory
                    "signatory_name": getattr(record, "signatory_name", None),
                    "signatory_role": getattr(record, "signatory_role", None),
                    "signatory_date": _fmt_date(getattr(record, "signatory_date", None)),
                    # Annex II #8 — Prior DDS references
                    "prior_dds_references": getattr(record, "prior_dds_references", None),
                },
                "plots": plots,
                "risk_assessment": risk_assessment_data,
                "supply_chain": supply_chain_data,
                "documents": record_docs_data,
                "blockchain": blockchain,
                "tenant": {
                    "name": "TraceLog",
                },
            }

            # ── Step 7: Generate PDF with WeasyPrint ─────────────────────────
            # Run WeasyPrint in a thread so the sync render doesn't block the
            # event loop for 1-10 seconds (a single PDF generation could
            # otherwise stall every other request on the worker).
            import asyncio as _asyncio
            pdf_bytes = await _asyncio.to_thread(render_certificate_pdf, context)

            # ── Step 8: Upload PDF to storage ────────────────────────────────
            pdf_filename = f"{cert_number}.pdf"
            pdf_url = await self.storage.upload(
                tenant_id=str(tenant_id),
                year=year,
                filename=pdf_filename,
                data=pdf_bytes,
                content_type="application/pdf",
            )

            pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

            # ── Step 9: Update DB: status=active, urls, hashes ───────────────
            cert = await self.repo.update(
                cert,
                status="active",
                pdf_url=pdf_url,
                pdf_hash=pdf_hash,
                pdf_size_bytes=len(pdf_bytes),
                qr_code_url=qr_url,
                generated_at=now,
                generation_error=None,
            )

            # ── Step 10: Supersede previous certs (exclude the one we just made) ─
            await self.repo.supersede_existing(record_id, exclude_id=cert.id)

            log.info(
                "certificate_generated",
                cert_id=str(cert.id),
                cert_number=cert_number,
                record_id=str(record_id),
            )

        except Exception as exc:
            log.error(
                "certificate_generation_failed",
                cert_id=str(cert.id),
                error=str(exc),
            )
            cert = await self.repo.update(
                cert,
                status="generating",
                generation_error=str(exc),
            )

        return cert

    async def revoke(
        self,
        certificate_id: uuid.UUID,
        tenant_id: uuid.UUID,
        reason: str,
    ) -> ComplianceCertificate:
        """Revoke a certificate."""
        cert = await self.repo.get_by_id(certificate_id)
        if cert is None or cert.tenant_id != tenant_id:
            raise NotFoundError(f"Certificate '{certificate_id}' not found")

        cert = await self.repo.update(
            cert,
            status="revoked",
            generation_error=f"Revoked: {reason}",
        )

        log.info(
            "certificate_revoked",
            cert_id=str(cert.id),
            cert_number=cert.certificate_number,
            reason=reason,
        )
        return cert
