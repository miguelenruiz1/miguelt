"""Email sending service using aiosmtplib."""
from __future__ import annotations

import logging
from email.message import EmailMessage
from html import escape as _html_escape
from string import Template

import aiosmtplib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.db.models import EmailConfig, EmailTemplate

logger = logging.getLogger(__name__)


def _html_escape_context(context: dict) -> dict:
    """Escape every string value so `$var` substitution can't inject HTML.

    The EmailTemplate bodies are author-trusted HTML but `context` carries
    user-provided data (full_name, company, invitation reason, etc.). Without
    this a user who registers with `full_name="<script>…</script>"` plants a
    stored XSS that executes in any webmail that renders HTML.
    """
    safe: dict = {}
    for k, v in context.items():
        if isinstance(v, str):
            safe[k] = _html_escape(v, quote=True)
        else:
            safe[k] = v
    return safe


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
        """Send an email. Platform Resend > SMTP/Mailhog fallback."""
        # 1. Platform-level Resend (configured by superuser, transparent to tenants)
        if self.settings.RESEND_API_KEY:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {self.settings.RESEND_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "from": self.settings.SMTP_FROM,
                            "to": [to],
                            "subject": subject,
                            "html": html_body,
                        },
                    )
                    if resp.status_code < 300:
                        logger.info("email_sent_via_resend", extra={"to": to})
                        return True
                    logger.warning("resend_failed status=%s", resp.status_code)
            except Exception:
                logger.exception("resend_error, falling back to SMTP")

        # 2. Fall back to SMTP (Mailhog in dev)
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
        """Render template variables ($var_name) using safe_substitute.

        Context values are HTML-escaped so user-controlled strings (names,
        companies, free-form notes) can't inject `<script>` into the body.
        The template author is trusted; the data feeding it is not.
        """
        return Template(html_body).safe_substitute(_html_escape_context(context))

    async def send_from_template(
        self,
        db: AsyncSession,
        tenant_id: str,
        slug: str,
        to: str,
        context: dict,
    ) -> bool:
        """Fetch template by slug, render, and send.

        Lookup order:
          1. Tenant-specific template (so admins can customize per tenant).
          2. Fallback to the 'default' tenant template seeded by migration 004.
        Without this fallback, every freshly-registered tenant has zero
        templates and all transactional emails (password reset, invitation,
        deactivation) silently fail.
        """
        result = await db.execute(
            select(EmailTemplate).where(
                EmailTemplate.tenant_id == tenant_id,
                EmailTemplate.slug == slug,
                EmailTemplate.is_active.is_(True),
            )
        )
        template = result.scalar_one_or_none()
        if not template and tenant_id != "default":
            result = await db.execute(
                select(EmailTemplate).where(
                    EmailTemplate.tenant_id == "default",
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
