"""Email providers router — manage email provider configuration per tenant."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_tenant_id, require_permission
from app.db.session import get_db_session
from app.services.email_provider_service import EmailProviderService

router = APIRouter(prefix="/api/v1/email-providers", tags=["email-providers"])


def _svc(db: Annotated[AsyncSession, Depends(get_db_session)]) -> EmailProviderService:
    return EmailProviderService(db)


class EmailProviderConfigSave(BaseModel):
    credentials: dict[str, str]


class TestEmailRequest(BaseModel):
    to: EmailStr


@router.get("/catalog", summary="Email provider catalogue (public)")
async def get_catalog(svc: EmailProviderService = Depends(_svc)) -> list[dict]:
    return svc.get_catalog()


@router.get("/", summary="List email provider configs for tenant")
async def list_provider_configs(
    _user: Annotated[None, require_permission("email.manage")],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    svc: EmailProviderService = Depends(_svc),
) -> list[dict]:
    return await svc.list_configs(tenant_id)


@router.post("/{slug}", summary="Save/update email provider config")
async def save_provider_config(
    slug: str,
    body: EmailProviderConfigSave,
    _user: Annotated[None, require_permission("email.manage")],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    svc: EmailProviderService = Depends(_svc),
) -> dict:
    try:
        return await svc.save_config(
            tenant_id=tenant_id,
            slug=slug,
            credentials=body.credentials,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{slug}/activate", summary="Set email provider as active")
async def activate_provider(
    slug: str,
    _user: Annotated[None, require_permission("email.manage")],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    svc: EmailProviderService = Depends(_svc),
) -> dict:
    try:
        return await svc.set_active(tenant_id, slug)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/{slug}", summary="Delete email provider config")
async def delete_provider_config(
    slug: str,
    _user: Annotated[None, require_permission("email.manage")],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    svc: EmailProviderService = Depends(_svc),
) -> dict:
    deleted = await svc.delete_config(tenant_id, slug)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No configuration found for provider '{slug}'",
        )
    return {"deleted": True, "slug": slug}


@router.post("/{slug}/test", summary="Send test email via this provider")
async def test_provider(
    slug: str,
    body: TestEmailRequest,
    _user: Annotated[None, require_permission("email.manage")],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    svc: EmailProviderService = Depends(_svc),
) -> dict:
    # Temporarily activate this provider for the test send
    result = await svc.send_email(
        tenant_id=tenant_id,
        to=body.to,
        subject="Trace — Test de proveedor de correo",
        html_body="<h2>¡Funciona!</h2><p>Este es un correo de prueba enviado desde Trace.</p>",
    )
    return result
