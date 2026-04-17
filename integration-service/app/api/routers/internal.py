"""Internal endpoints for inter-service communication.

Auth: ALL endpoints require X-Service-Token (constant-time comparison) so
the service can't be abused even when port 9004 is exposed to the host.
"""
from __future__ import annotations

import secrets as _secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.registry import get_adapter
from app.core.settings import get_settings
from app.db.session import get_db_session
from app.domain.schemas.integration import InvoiceResolutionOut
from app.services.resolution_service import ResolutionService


async def _verify_service_token(
    x_service_token: str = Header(..., alias="X-Service-Token"),
) -> str:
    """Constant-time comparison of the inter-service shared secret."""
    if not _secrets.compare_digest(x_service_token, get_settings().S2S_SERVICE_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid service token")
    return x_service_token


# Apply S2S auth to ALL internal routes via router-level dependency
router = APIRouter(
    prefix="/api/v1/internal",
    tags=["internal"],
    dependencies=[Depends(_verify_service_token)],
)


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
    # Map provider slug to resolution slug (e.g., matias → matias_fev for invoices)
    resolution_slug = f"{provider_slug}_fev" if not provider_slug.endswith(("_fev", "_nc", "_nd", "_ds", "_er", "_pos")) else provider_slug
    svc = ResolutionService(db)
    invoice_number: str | None = None
    try:
        # Try specific resolution first, fall back to legacy provider slug
        resolution = await svc.get_active_resolution(x_tenant_id, resolution_slug)
        if not resolution:
            resolution = await svc.get_active_resolution(x_tenant_id, provider_slug)
            resolution_slug = provider_slug
        if resolution:
            invoice_number, _ = await svc.get_next_number(x_tenant_id, resolution_slug)
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

    # Get credentials from DB — tenant-specific first, then global fallback
    import logging as _logging
    _log = _logging.getLogger("integration.internal")
    credentials = body.pop("credentials", {})
    if not credentials:
        try:
            from app.repositories.integration_repo import IntegrationConfigRepository
            from app.core.security import decrypt_credentials
            import json as _json
            repo = IntegrationConfigRepository(db)
            # Tenant-specific config only. The previous code fell back to
            # "platform" / "default" entries, meaning tenant B could emit
            # invoices to DIAN signed with tenant A's shared credentials —
            # a cross-tenant billing fraud risk. If a tenant has no config,
            # fail the request explicitly so the onboarding flow completes
            # the setup instead of silently using someone else's keys.
            config = await repo.get_by_provider(x_tenant_id, provider_slug)
            if config and config.credentials_enc:
                credentials = _json.loads(decrypt_credentials(config.credentials_enc))
                # Inherit simulation_mode from config if not in credentials
                if config.simulation_mode and "simulation_mode" not in credentials:
                    credentials["simulation_mode"] = True
                elif config.simulation_mode:
                    credentials["simulation_mode"] = True
                _log.info("credentials_loaded tenant=%s provider=%s simulation=%s", x_tenant_id, provider_slug, credentials.get("simulation_mode", False))
            else:
                _log.warning("no_credentials_found tenant=%s provider=%s", x_tenant_id, provider_slug)
        except Exception as exc:
            _log.exception("credentials_load_error tenant=%s provider=%s", x_tenant_id, provider_slug)
            raise HTTPException(status_code=500, detail=f"Failed to load credentials: {exc}")
    try:
        result = await adapter.create_invoice(credentials, body)
    except Exception as exc:
        _log.exception("adapter_create_invoice_error tenant=%s provider=%s", x_tenant_id, provider_slug)
        raise HTTPException(status_code=502, detail=f"Invoice creation failed: {exc}")

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

    # Get next number from resolution for the credit note (matias → matias_nc)
    resolution_slug = f"{provider_slug}_nc" if not provider_slug.endswith(("_fev", "_nc", "_nd", "_ds", "_er", "_pos")) else provider_slug
    svc = ResolutionService(db)
    credit_note_number: str | None = None
    try:
        resolution = await svc.get_active_resolution(x_tenant_id, resolution_slug)
        if not resolution:
            resolution = await svc.get_active_resolution(x_tenant_id, provider_slug)
            resolution_slug = provider_slug
        if resolution:
            credit_note_number, _ = await svc.get_next_number(x_tenant_id, resolution_slug)
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
    if not credentials:
        from app.repositories.integration_repo import IntegrationConfigRepository
        from app.core.security import decrypt_credentials
        import json as _json
        repo = IntegrationConfigRepository(db)
        # No cross-tenant fallback — see note in create_invoice_internal.
        config = await repo.get_by_provider(x_tenant_id, provider_slug)
        if config and config.credentials_enc:
            credentials = _json.loads(decrypt_credentials(config.credentials_enc))
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


