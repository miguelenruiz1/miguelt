"""Internal endpoints for inter-service communication — no JWT auth required.

These endpoints are only accessible within the Docker network (not exposed externally).
Protected by X-Tenant-Id header presence only (same pattern as subscription-service module checks).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.registry import get_adapter
from app.db.session import get_db_session
from app.domain.schemas.integration import InvoiceResolutionOut
from app.services.resolution_service import ResolutionService

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])


@router.post("/invoices/{provider_slug}")
async def create_invoice_internal(
    provider_slug: str,
    body: dict,
    x_tenant_id: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Create an invoice via adapter — no auth, no DB config required.

    Uses ResolutionService to assign the next invoice number from the
    tenant's active resolution for this provider.
    """
    adapter = get_adapter(provider_slug)
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No adapter for provider: {provider_slug}",
        )

    # Get next invoice number from resolution
    svc = ResolutionService(db)
    invoice_number: str | None = None
    try:
        if provider_slug == "sandbox":
            await svc.ensure_sandbox_resolution(x_tenant_id)
        resolution = await svc.get_active_resolution(x_tenant_id, provider_slug)
        if resolution:
            invoice_number, _ = await svc.get_next_number(x_tenant_id, provider_slug)
            body["invoice_number"] = invoice_number
            body["resolution"] = {
                "prefix": resolution.prefix,
                "from": resolution.range_from,
                "to": resolution.range_to,
                "resolution_number": resolution.resolution_number,
                "start_date": resolution.valid_from.strftime("%d-%m-%Y"),
                "end_date": resolution.valid_to.strftime("%d-%m-%Y"),
            }
    except Exception:
        # Resolution errors should not block invoicing — log and continue
        import logging
        logging.getLogger("integration.internal").exception(
            "resolution_error tenant=%s provider=%s", x_tenant_id, provider_slug
        )

    credentials = body.pop("credentials", {})
    result = await adapter.create_invoice(credentials, body)

    # Inject invoice_number into the response
    if invoice_number:
        result["invoice_number"] = invoice_number

    return result


@router.post("/credit-notes/{provider_slug}")
async def create_credit_note_internal(
    provider_slug: str,
    body: dict,
    x_tenant_id: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a credit note via adapter — no auth, internal only.

    Uses ResolutionService to assign the next number from the
    tenant's active resolution for this provider.
    """
    adapter = get_adapter(provider_slug)
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No adapter for provider: {provider_slug}",
        )

    # Get next number from resolution for the credit note
    svc = ResolutionService(db)
    credit_note_number: str | None = None
    try:
        if provider_slug == "sandbox":
            await svc.ensure_sandbox_resolution(x_tenant_id)
        resolution = await svc.get_active_resolution(x_tenant_id, provider_slug)
        if resolution:
            credit_note_number, _ = await svc.get_next_number(x_tenant_id, provider_slug)
            body["credit_note_number"] = credit_note_number
            body["resolution"] = {
                "prefix": resolution.prefix,
                "from": resolution.range_from,
                "to": resolution.range_to,
                "resolution_number": resolution.resolution_number,
                "start_date": resolution.valid_from.strftime("%d-%m-%Y"),
                "end_date": resolution.valid_to.strftime("%d-%m-%Y"),
            }
    except Exception:
        import logging
        logging.getLogger("integration.internal").exception(
            "resolution_error tenant=%s provider=%s (credit_note)", x_tenant_id, provider_slug
        )

    credentials = body.pop("credentials", {})
    result = await adapter.create_credit_note(credentials, body)

    if credit_note_number:
        result["credit_note_number"] = credit_note_number

    return result


@router.get("/resolutions/{provider}", response_model=InvoiceResolutionOut | None)
async def get_resolution_internal(
    provider: str,
    x_tenant_id: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Get active resolution for a tenant — internal, no auth."""
    svc = ResolutionService(db)
    return await svc.get_active_resolution(x_tenant_id, provider)
