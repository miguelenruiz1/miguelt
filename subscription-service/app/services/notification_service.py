"""Sends notifications to users via user-service HTTP API."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Fire-and-forget notification sender via user-service."""

    def __init__(self) -> None:
        settings = get_settings()
        self.user_service_url = settings.USER_SERVICE_URL
        self.http = httpx.AsyncClient(timeout=10.0)

    async def send(
        self,
        tenant_id: str,
        to_email: str,
        template_slug: str,
        context: dict[str, Any],
    ) -> bool:
        """Send a notification through user-service.  Returns True on success."""
        try:
            resp = await self.http.post(
                f"{self.user_service_url}/api/v1/notifications/send",
                json={
                    "to": to_email,
                    "template_slug": template_slug,
                    "context": context,
                },
                headers={
                    "X-Tenant-Id": tenant_id,
                    "X-Service-Key": "internal",
                },
            )
            if resp.status_code == 200:
                logger.info(
                    "notification_sent",
                    extra={"template": template_slug, "to": to_email},
                )
                return True

            logger.warning(
                "notification_send_non_200",
                extra={
                    "template": template_slug,
                    "to": to_email,
                    "status": resp.status_code,
                    "body": resp.text[:200],
                },
            )
            return False
        except Exception as exc:
            logger.warning(
                "notification_send_failed",
                extra={"error": str(exc), "template": template_slug, "to": to_email},
            )
            return False

    # ─── Convenience helpers ─────────────────────────────────────────────────

    async def notify_welcome(
        self,
        tenant_id: str,
        user_email: str,
        user_name: str,
    ) -> bool:
        """Welcome email after first registration or plan activation."""
        return await self.send(
            tenant_id,
            user_email,
            "welcome",
            {
                "user_name": user_name,
                "user_email": user_email,
                "dashboard_url": "https://app.tracelog.co",
            },
        )

    async def notify_payment_received(
        self,
        tenant_id: str,
        to_email: str,
        *,
        invoice_number: str,
        amount: str,
        currency: str = "COP",
        period: str = "",
    ) -> bool:
        """Payment confirmation email."""
        return await self.send(
            tenant_id,
            to_email,
            "payment_received",
            {
                "invoice_number": invoice_number,
                "amount": amount,
                "currency": currency,
                "period": period,
            },
        )

    async def notify_invoice_generated(
        self,
        tenant_id: str,
        to_email: str,
        *,
        invoice_number: str,
        amount: str,
        currency: str = "COP",
        due_date: str = "",
        pay_url: str = "",
    ) -> bool:
        """New invoice notification."""
        return await self.send(
            tenant_id,
            to_email,
            "invoice_generated",
            {
                "invoice_number": invoice_number,
                "amount": amount,
                "currency": currency,
                "due_date": due_date,
                "pay_url": pay_url,
            },
        )

    async def notify_trial_ended(
        self,
        tenant_id: str,
        to_email: str,
        *,
        user_name: str = "",
        plans_url: str = "https://app.tracelog.co/planes",
    ) -> bool:
        """Trial period ended notification."""
        return await self.send(
            tenant_id,
            to_email,
            "trial_ended",
            {
                "user_name": user_name,
                "plans_url": plans_url,
            },
        )

    async def notify_plan_limit(
        self,
        tenant_id: str,
        to_email: str,
        *,
        resource: str,
        current: int | str,
        limit: int | str,
        plan_name: str = "",
        upgrade_url: str = "https://app.tracelog.co/planes",
    ) -> bool:
        """Resource limit reached notification."""
        return await self.send(
            tenant_id,
            to_email,
            "plan_limit_reached",
            {
                "resource": resource,
                "current": str(current),
                "limit": str(limit),
                "plan_name": plan_name,
                "upgrade_url": upgrade_url,
            },
        )

    async def notify_certificate_generated(
        self,
        tenant_id: str,
        to_email: str,
        *,
        cert_number: str,
        commodity: str,
        pdf_url: str = "",
        verify_url: str = "",
    ) -> bool:
        """EUDR certificate generated notification."""
        return await self.send(
            tenant_id,
            to_email,
            "certificate_generated",
            {
                "cert_number": cert_number,
                "commodity": commodity,
                "pdf_url": pdf_url,
                "verify_url": verify_url,
            },
        )

    async def close(self) -> None:
        """Gracefully close the underlying HTTP client."""
        await self.http.aclose()
