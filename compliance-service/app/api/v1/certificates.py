"""Router for compliance certificates — PDF generation, listing, verification."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.certificates.generator import CertificateGenerator
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.models.certificate import ComplianceCertificate
from app.models.plot_link import CompliancePlotLink
from app.models.record import ComplianceRecord
from app.repositories.certificate_repo import CertificateRepository
from app.schemas.certificate import (
    CertificateListResponse,
    CertificateResponse,
    RevokeRequest,
    VerifyResponse,
)

log = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/compliance",
    tags=["certificates"],
)


def _tenant_id(user: dict) -> uuid.UUID:
    raw = str(user.get("tenant_id", "00000000-0000-0000-0000-000000000001"))
    try:
        return uuid.UUID(raw)
    except ValueError:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")


def _user_id(user: dict) -> uuid.UUID | None:
    uid = user.get("id")
    if uid is None:
        return None
    try:
        return uuid.UUID(str(uid))
    except (ValueError, TypeError):
        return None


# ─── Authenticated endpoints (require ModuleUser) ─────────────────────────


@router.post(
    "/records/{record_id}/certificate",
    response_model=CertificateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_certificate(
    record_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Generate a PDF certificate for a compliance record.

    Returns 201 for new certificates, or 200 with existing active cert (idempotent).
    """
    tid = _tenant_id(user)
    uid = _user_id(user)

    generator = CertificateGenerator(db)
    cert = await generator.generate(record_id=record_id, tenant_id=tid, user_id=uid)

    return cert


@router.get(
    "/records/{record_id}/certificate",
    response_model=CertificateResponse,
)
async def get_record_certificate(
    record_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Get the active certificate for a compliance record."""
    tid = _tenant_id(user)
    repo = CertificateRepository(db)

    # Verify record belongs to tenant
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

    cert = await repo.get_by_record(record_id)
    if cert is None:
        raise NotFoundError(f"No active certificate for record '{record_id}'")

    return cert


@router.get(
    "/certificates",
    response_model=CertificateListResponse,
)
async def list_certificates(
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
    framework_slug: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    year: int | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List all certificates for the tenant."""
    tid = _tenant_id(user)
    repo = CertificateRepository(db)

    items, total = await repo.list(
        tenant_id=tid,
        framework_slug=framework_slug,
        status=status_filter,
        year=year,
        offset=offset,
        limit=limit,
    )

    return CertificateListResponse(items=items, total=total)


@router.get(
    "/certificates/{certificate_id}",
    response_model=CertificateResponse,
)
async def get_certificate(
    certificate_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Get a certificate by ID."""
    tid = _tenant_id(user)
    repo = CertificateRepository(db)

    cert = await repo.get_by_id(certificate_id)
    if cert is None or cert.tenant_id != tid:
        raise NotFoundError(f"Certificate '{certificate_id}' not found")

    return cert


@router.get(
    "/certificates/{certificate_id}/download",
)
async def download_certificate(
    certificate_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Download the PDF file for a certificate."""
    from fastapi.responses import FileResponse
    from pathlib import Path

    tid = _tenant_id(user)
    repo = CertificateRepository(db)
    cert = await repo.get_by_id(certificate_id)
    if cert is None or cert.tenant_id != tid:
        raise NotFoundError(f"Certificate '{certificate_id}' not found")

    if not cert.pdf_url:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="PDF not generated yet")

    # Remote URLs (S3/GCS) — redirect the client to download directly.
    if cert.pdf_url.startswith(("http://", "https://", "gs://")):
        from fastapi.responses import RedirectResponse
        target = cert.pdf_url
        if target.startswith("gs://"):
            # Convert gs://bucket/key → public https URL
            without = target[5:]
            target = f"https://storage.googleapis.com/{without}"
        return RedirectResponse(url=target)

    # Local file:// URL fallback (DEV only). Defense in depth: validate that
    # the resolved path lives inside the certificates directory to prevent
    # arbitrary file disclosure if pdf_url is ever tampered with.
    from app.certificates.storage import LocalStorage
    from fastapi import HTTPException
    pdf_path = Path(cert.pdf_url.replace("file://", "")).resolve()
    base_dir = LocalStorage.BASE_DIR.resolve()
    try:
        pdf_path.relative_to(base_dir)
    except ValueError:
        raise HTTPException(status_code=404, detail="PDF file not found")
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"{cert.certificate_number}.pdf",
    )


@router.post(
    "/certificates/{certificate_id}/regenerate",
    response_model=CertificateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def regenerate_certificate(
    certificate_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Force regenerate a certificate (supersedes the old one)."""
    tid = _tenant_id(user)
    uid = _user_id(user)
    repo = CertificateRepository(db)

    old_cert = await repo.get_by_id(certificate_id)
    if old_cert is None or old_cert.tenant_id != tid:
        raise NotFoundError(f"Certificate '{certificate_id}' not found")

    generator = CertificateGenerator(db)

    # Supersede the old cert first
    await repo.supersede_existing(old_cert.record_id)

    # Generate a fresh one
    cert = await generator.generate(
        record_id=old_cert.record_id,
        tenant_id=tid,
        user_id=uid,
    )
    return cert


@router.post(
    "/certificates/{certificate_id}/revoke",
    response_model=CertificateResponse,
)
async def revoke_certificate(
    certificate_id: uuid.UUID,
    body: RevokeRequest,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Revoke a certificate."""
    tid = _tenant_id(user)
    generator = CertificateGenerator(db)
    cert = await generator.revoke(
        certificate_id=certificate_id,
        tenant_id=tid,
        reason=body.reason,
    )
    return cert


# ─── Public endpoint (NO auth, NO module gate, NO tenant header) ──────────


@router.get(
    "/verify/{certificate_number}",
    response_model=VerifyResponse,
)
async def verify_certificate(
    certificate_number: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Public verification endpoint — no authentication required.

    Returns verification data for the given certificate number.
    """
    repo = CertificateRepository(db)
    cert = await repo.get_by_number(certificate_number)

    if cert is None:
        return VerifyResponse(
            valid=False,
            status="not_found",
            certificate_number=certificate_number,
            message="Certificate not found. It may have been revoked or does not exist.",
        )

    now = date.today()
    is_valid = (
        cert.status == "active"
        and cert.valid_from <= now <= cert.valid_until
    )

    # Load record for additional info
    record = (
        await db.execute(
            select(ComplianceRecord).where(ComplianceRecord.id == cert.record_id)
        )
    ).scalar_one_or_none()

    # Count plots
    plots_count = None
    if record is not None:
        count_q = select(func.count()).where(CompliancePlotLink.record_id == record.id)
        plots_count = (await db.execute(count_q)).scalar_one()

    blockchain = None
    if cert.solana_cnft_address or cert.solana_tx_sig:
        blockchain = {
            "cnft_address": cert.solana_cnft_address,
            "tx_signature": cert.solana_tx_sig,
        }

    message = None
    if cert.status == "revoked":
        message = "This certificate has been revoked."
    elif cert.status == "superseded":
        message = "This certificate has been superseded by a newer version."
    elif not is_valid and cert.status == "active":
        message = "This certificate has expired."

    return VerifyResponse(
        valid=is_valid,
        status=cert.status,
        certificate_number=cert.certificate_number,
        framework=cert.framework_slug,
        commodity_type=record.commodity_type if record else None,
        quantity_kg=float(record.quantity_kg) if record and record.quantity_kg else None,
        country_of_production=record.country_of_production if record else None,
        valid_from=cert.valid_from,
        valid_until=cert.valid_until,
        deforestation_free=record.deforestation_free_declaration if record else None,
        legal_compliance=record.legal_compliance_declaration if record else None,
        plots_count=plots_count,
        blockchain=blockchain,
        pdf_url=cert.pdf_url,
        generated_at=cert.generated_at,
        message=message,
    )
