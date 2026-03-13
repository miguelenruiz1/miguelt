"""Email sending service using aiosmtplib."""
from __future__ import annotations

import logging
from email.message import EmailMessage
from string import Template

import aiosmtplib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.db.models import EmailConfig, EmailTemplate

logger = logging.getLogger(__name__)


def _env_smtp_config(settings) -> dict:
    """Build SMTP config dict from env vars."""
    return {
        "hostname": settings.SMTP_HOST,
        "port": settings.SMTP_PORT,
        "username": settings.SMTP_USER or None,
        "password": settings.SMTP_PASSWORD or None,
        "use_tls": settings.SMTP_USE_TLS,
        "from_addr": settings.SMTP_FROM,
        "admin_email": None,
        "test_email": None,
    }


class EmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def _get_smtp_config(self, db: AsyncSession, tenant_id: str) -> dict:
        """Load SMTP config from DB for tenant, falling back to env vars."""
        try:
            result = await db.execute(
                select(EmailConfig).where(EmailConfig.tenant_id == tenant_id)
            )
            config = result.scalar_one_or_none()
        except Exception:
            # Table might not exist yet (migration not run)
            logger.debug("email_configs table not available, using env vars")
            return _env_smtp_config(self.settings)

        if config and config.smtp_host:
            return {
                "hostname": config.smtp_host,
                "port": config.smtp_port or 587,
                "username": config.smtp_user or None,
                "password": config.smtp_password or None,
                "use_tls": config.smtp_use_tls,
                "from_addr": config.smtp_from or self.settings.SMTP_FROM,
                "admin_email": config.admin_email,
                "test_email": config.test_email,
            }
        return _env_smtp_config(self.settings)

    async def send(
        self,
        to: str,
        subject: str,
        html_body: str,
        db: AsyncSession | None = None,
        tenant_id: str | None = None,
        is_system: bool = False,
    ) -> bool:
        """Send an email. Tries active email provider first, falls back to SMTP."""
        # Try active email provider first
        if db and tenant_id:
            try:
                from app.services.email_provider_service import EmailProviderService
                provider_svc = EmailProviderService(db)
                active = await provider_svc.get_active(tenant_id)
                if active:
                    result = await provider_svc.send_email(tenant_id, to, subject, html_body)
                    return result.get("ok", False)
            except Exception:
                logger.debug("email_provider_dispatch_failed, falling back to SMTP")

        # Fall back to legacy SMTP config
        if db and tenant_id:
            smtp_cfg = await self._get_smtp_config(db, tenant_id)
        else:
            smtp_cfg = _env_smtp_config(self.settings)

        msg = EmailMessage()
        msg["From"] = smtp_cfg["from_addr"]
        msg["To"] = to
        msg["Subject"] = subject

        # Add admin CC for system emails (not test sends)
        if is_system and smtp_cfg.get("admin_email"):
            msg["Cc"] = smtp_cfg["admin_email"]

        msg.set_content(html_body, subtype="html")

        use_tls = smtp_cfg["use_tls"]
        port = smtp_cfg["port"]
        # STARTTLS: only when TLS is off and port is 587
        start_tls = not use_tls and port == 587

        try:
            await aiosmtplib.send(
                msg,
                hostname=smtp_cfg["hostname"],
                port=port,
                username=smtp_cfg["username"],
                password=smtp_cfg["password"],
                use_tls=use_tls,
                start_tls=start_tls,
            )
            logger.info("email_sent", extra={"to": to, "subject": subject})
            return True
        except Exception as exc:
            logger.exception("email_send_failed", extra={
                "to": to, "subject": subject,
                "smtp_host": smtp_cfg["hostname"], "smtp_port": port,
                "error": str(exc),
            })
            return False

    @staticmethod
    def render_template(html_body: str, context: dict) -> str:
        """Render template variables ($var_name) using safe_substitute."""
        return Template(html_body).safe_substitute(context)

    async def send_from_template(
        self,
        db: AsyncSession,
        tenant_id: str,
        slug: str,
        to: str,
        context: dict,
    ) -> bool:
        """Fetch template by slug, render, and send."""
        result = await db.execute(
            select(EmailTemplate).where(
                EmailTemplate.tenant_id == tenant_id,
                EmailTemplate.slug == slug,
                EmailTemplate.is_active.is_(True),
            )
        )
        template = result.scalar_one_or_none()
        if not template:
            logger.warning("email_template_not_found", extra={"slug": slug, "tenant_id": tenant_id})
            return False

        rendered_subject = self.render_template(template.subject, context)
        rendered_body = self.render_template(template.html_body, context)
        return await self.send(to, rendered_subject, rendered_body, db=db, tenant_id=tenant_id, is_system=True)

    async def test_connection(self, db: AsyncSession, tenant_id: str) -> dict:
        """Test SMTP connection for tenant config. Returns {ok, error?}."""
        smtp_cfg = await self._get_smtp_config(db, tenant_id)
        use_tls = smtp_cfg["use_tls"]
        port = smtp_cfg["port"]
        start_tls = not use_tls and port == 587

        try:
            smtp = aiosmtplib.SMTP(
                hostname=smtp_cfg["hostname"],
                port=port,
                use_tls=use_tls,
            )
            await smtp.connect()
            if start_tls:
                await smtp.starttls()
            if smtp_cfg["username"] and smtp_cfg["password"]:
                await smtp.login(smtp_cfg["username"], smtp_cfg["password"])
            await smtp.quit()
            return {"ok": True}
        except Exception as exc:
            logger.warning("smtp_test_failed", extra={
                "tenant_id": tenant_id,
                "smtp_host": smtp_cfg["hostname"],
                "smtp_port": port,
                "error": str(exc),
            })
            return {"ok": False, "error": str(exc)}
