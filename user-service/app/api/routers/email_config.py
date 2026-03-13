"""Email configuration endpoints (SMTP settings per tenant)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id, require_permission
from app.core.settings import get_settings
from app.db.session import get_db_session
from app.domain.schemas import EmailConfigOut, EmailConfigUpdate
from app.repositories.email_config_repo import EmailConfigRepository
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/email-config", tags=["email-config"])


def _env_defaults(tenant_id: str) -> EmailConfigOut:
    """Return env var SMTP defaults as EmailConfigOut."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return EmailConfigOut(
        id="",
        tenant_id=tenant_id,
        smtp_host=settings.SMTP_HOST,
        smtp_port=settings.SMTP_PORT,
        smtp_user=settings.SMTP_USER or None,
        smtp_password=None,
        smtp_from=settings.SMTP_FROM,
        smtp_use_tls=settings.SMTP_USE_TLS,
        admin_email=None,
        test_email=None,
        created_at=now,
        updated_at=now,
    )


@router.get("", response_model=EmailConfigOut)
async def get_email_config(
    _: Annotated[object, require_permission("email.manage")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> EmailConfigOut:
    try:
        repo = EmailConfigRepository(db)
        config = await repo.get_by_tenant(tenant_id)
    except Exception:
        logger.debug("email_configs table not available, returning env defaults")
        return _env_defaults(tenant_id)

    if config:
        out = EmailConfigOut.model_validate(config)
        out.smtp_password = "*****" if config.smtp_password else None
        return out
    return _env_defaults(tenant_id)


@router.put("", response_model=EmailConfigOut)
async def update_email_config(
    body: EmailConfigUpdate,
    _: Annotated[object, require_permission("email.manage")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> EmailConfigOut:
    repo = EmailConfigRepository(db)
    data = body.model_dump(exclude_none=True)
    # If password is the mask, don't update it
    if data.get("smtp_password") == "*****":
        data.pop("smtp_password")
    config = await repo.upsert(tenant_id, **data)
    out = EmailConfigOut.model_validate(config)
    out.smtp_password = "*****" if config.smtp_password else None
    return out


@router.post("/test-connection")
async def test_smtp_connection(
    _: Annotated[object, require_permission("email.manage")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> dict:
    email_svc = EmailService()
    result = await email_svc.test_connection(db, tenant_id)
    return result
