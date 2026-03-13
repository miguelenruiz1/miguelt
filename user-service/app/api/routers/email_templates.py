"""Email template management endpoints."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_tenant_id, require_permission
from app.db.session import get_db_session
from app.domain.schemas import EmailTemplateOut, EmailTemplateUpdate, TestEmailRequest
from app.repositories.email_config_repo import EmailConfigRepository
from app.services.email_service import EmailService
from app.services.email_template_service import EmailTemplateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/email-templates", tags=["email-templates"])


@router.get("", response_model=list[EmailTemplateOut])
async def list_templates(
    _: Annotated[object, require_permission("email.view")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> list[EmailTemplateOut]:
    svc = EmailTemplateService(db)
    templates = await svc.list(tenant_id)
    return [EmailTemplateOut.model_validate(t) for t in templates]


@router.get("/{template_id}", response_model=EmailTemplateOut)
async def get_template(
    template_id: str,
    _: Annotated[object, require_permission("email.view")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> EmailTemplateOut:
    svc = EmailTemplateService(db)
    tpl = await svc.get(template_id)
    return EmailTemplateOut.model_validate(tpl)


@router.put("/{template_id}", response_model=EmailTemplateOut)
async def update_template(
    template_id: str,
    body: EmailTemplateUpdate,
    _: Annotated[object, require_permission("email.manage")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> EmailTemplateOut:
    svc = EmailTemplateService(db)
    updates = body.model_dump(exclude_none=True)
    tpl = await svc.update(template_id, **updates)
    return EmailTemplateOut.model_validate(tpl)


@router.post("/{template_id}/test", status_code=200)
async def test_template(
    template_id: str,
    body: TestEmailRequest,
    _: Annotated[object, require_permission("email.manage")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> dict:
    svc = EmailTemplateService(db)
    tpl = await svc.get(template_id)

    # Resolve recipient: body.to → test_email from config → error
    recipient = body.to
    if not recipient:
        try:
            config_repo = EmailConfigRepository(db)
            email_config = await config_repo.get_by_tenant(tenant_id)
            if email_config and email_config.test_email:
                recipient = email_config.test_email
        except Exception:
            pass  # Table might not exist

    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se proporcionó un destinatario. Configura un email de prueba en Configuración SMTP o envía uno en el body.",
        )

    # Render with sample data
    email_svc = EmailService()
    sample_context = {
        "user_name": "Usuario de Prueba",
        "user_email": recipient,
        "link": "https://example.com/test-link",
        "app_name": "Trace",
        "tenant_name": tenant_id,
    }
    rendered_subject = email_svc.render_template(tpl.subject, sample_context)
    rendered_body = email_svc.render_template(tpl.html_body, sample_context)

    sent = await email_svc.send(
        recipient, f"[TEST] {rendered_subject}", rendered_body,
        db=db, tenant_id=tenant_id,
    )

    if not sent:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo enviar el correo a {recipient}. Verifica la configuración SMTP.",
        )

    return {"sent": True, "recipient": recipient}
