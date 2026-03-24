"""Inter-service notification endpoint.

Exposes POST /api/v1/notifications/send so that other microservices
(subscription-service, compliance-service, etc.) can trigger email
notifications without direct SMTP access.

Auth: accepts ``X-Service-Key: internal`` header (simple shared secret
for trusted internal-network callers).  No JWT required.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

# ─── Accepted service keys (in production, move to env / vault) ───────────
_VALID_SERVICE_KEYS = {"internal"}


def _verify_service_key(request: Request) -> None:
    """Lightweight guard for inter-service calls."""
    key = request.headers.get("X-Service-Key", "")
    if key not in _VALID_SERVICE_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Service-Key",
        )


# ─── Schemas ──────────────────────────────────────────────────────────────

class SendNotificationRequest(BaseModel):
    to: EmailStr
    template_slug: str
    context: dict[str, Any] = {}


class SendNotificationResponse(BaseModel):
    sent: bool
    detail: str | None = None


# ─── Endpoint ─────────────────────────────────────────────────────────────

@router.post(
    "/send",
    response_model=SendNotificationResponse,
    dependencies=[Depends(_verify_service_key)],
)
async def send_notification(
    body: SendNotificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> SendNotificationResponse:
    """Render an email template and send it.

    1. Look up template by *slug* for the tenant (from ``X-Tenant-Id``).
    2. Render subject & body using ``$variable`` substitution.
    3. Send via :class:`EmailService` (active provider -> SMTP fallback).
    """
    tenant_id = request.headers.get("X-Tenant-Id", "default")
    email_svc = EmailService()

    sent = await email_svc.send_from_template(
        db=db,
        tenant_id=tenant_id,
        slug=body.template_slug,
        to=body.to,
        context=body.context,
    )

    if not sent:
        logger.warning(
            "notification_delivery_failed",
            extra={
                "template": body.template_slug,
                "to": body.to,
                "tenant_id": tenant_id,
            },
        )
        return SendNotificationResponse(
            sent=False,
            detail=f"Template '{body.template_slug}' not found or email delivery failed.",
        )

    return SendNotificationResponse(sent=True)
