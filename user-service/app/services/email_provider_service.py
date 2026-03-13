"""Service for email provider configuration management and sending."""
from __future__ import annotations

import logging
from email.message import EmailMessage
from typing import Any

import aiosmtplib
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.email_provider_repo import EmailProviderRepository

logger = logging.getLogger(__name__)


# ─── Provider catalogue (hardcoded) ──────────────────────────────────────────

PROVIDER_CATALOG: list[dict[str, Any]] = [
    {
        "slug": "gmail",
        "name": "Gmail (API)",
        "description": "Envío de correo vía API de Gmail con OAuth2.",
        "color": "#EA4335",
        "fields": [
            {"key": "client_id",     "label": "Client ID",     "type": "text",     "required": True},
            {"key": "client_secret", "label": "Client Secret", "type": "password", "required": True},
            {"key": "refresh_token", "label": "Refresh Token", "type": "password", "required": True},
        ],
    },
    {
        "slug": "outlook",
        "name": "Outlook 365",
        "description": "Envío de correo vía Microsoft Graph API.",
        "color": "#0078D4",
        "fields": [
            {"key": "client_id",     "label": "Client ID",     "type": "text",     "required": True},
            {"key": "client_secret", "label": "Client Secret", "type": "password", "required": True},
            {"key": "tenant_id",     "label": "Tenant ID",     "type": "text",     "required": True},
            {"key": "refresh_token", "label": "Refresh Token", "type": "password", "required": True},
        ],
    },
    {
        "slug": "sendgrid",
        "name": "SendGrid",
        "description": "Plataforma de email transaccional de Twilio, confiable y escalable.",
        "color": "#1A82E2",
        "fields": [
            {"key": "api_key",    "label": "API Key",      "type": "password", "required": True},
            {"key": "from_email", "label": "From Email",   "type": "text",     "required": True},
            {"key": "from_name",  "label": "From Name",    "type": "text",     "required": False},
        ],
    },
    {
        "slug": "mailgun",
        "name": "Mailgun",
        "description": "Email API de Sinch, ideal para desarrolladores.",
        "color": "#F06B56",
        "fields": [
            {"key": "api_key",    "label": "API Key",      "type": "password", "required": True},
            {"key": "domain",     "label": "Domain",       "type": "text",     "required": True},
            {"key": "from_email", "label": "From Email",   "type": "text",     "required": True},
        ],
    },
    {
        "slug": "aws_ses",
        "name": "AWS SES",
        "description": "Amazon Simple Email Service, escalable y económico.",
        "color": "#FF9900",
        "fields": [
            {"key": "access_key_id",     "label": "Access Key ID",     "type": "text",     "required": True},
            {"key": "secret_access_key", "label": "Secret Access Key", "type": "password", "required": True},
            {"key": "region",            "label": "Region",            "type": "text",     "required": True},
            {"key": "from_email",        "label": "From Email",        "type": "text",     "required": True},
        ],
    },
    {
        "slug": "postmark",
        "name": "Postmark",
        "description": "Email transaccional rápido con excelente deliverability.",
        "color": "#FFDE00",
        "fields": [
            {"key": "server_api_token", "label": "Server API Token", "type": "password", "required": True},
            {"key": "from_email",       "label": "From Email",       "type": "text",     "required": True},
        ],
    },
    {
        "slug": "resend",
        "name": "Resend",
        "description": "API moderna de email para desarrolladores, simple y potente.",
        "color": "#000000",
        "fields": [
            {"key": "api_key",    "label": "API Key",    "type": "password", "required": True},
            {"key": "from_email", "label": "From Email", "type": "text",     "required": True},
        ],
    },
    {
        "slug": "smtp",
        "name": "SMTP Genérico",
        "description": "Conexión SMTP directa — compatible con cualquier servidor de correo.",
        "color": "#6B7280",
        "fields": [
            {"key": "host",       "label": "Host",     "type": "text",     "required": True},
            {"key": "port",       "label": "Port",     "type": "text",     "required": True},
            {"key": "username",   "label": "Username", "type": "text",     "required": False},
            {"key": "password",   "label": "Password", "type": "password", "required": False},
            {"key": "use_tls",    "label": "Use TLS",  "type": "text",     "required": False},
            {"key": "from_email", "label": "From Email", "type": "text",   "required": True},
        ],
    },
]

_CATALOG_BY_SLUG: dict[str, dict] = {p["slug"]: p for p in PROVIDER_CATALOG}


def _mask_credentials(credentials: dict) -> dict:
    return {k: "••••••" for k in credentials} if credentials else {}


class EmailProviderService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = EmailProviderRepository(db)
        self.db = db

    def get_catalog(self) -> list[dict]:
        return PROVIDER_CATALOG

    async def list_configs(self, tenant_id: str) -> list[dict]:
        saved = {c.provider_slug: c for c in await self.repo.list_for_tenant(tenant_id)}
        result = []
        for prov in PROVIDER_CATALOG:
            slug = prov["slug"]
            config = saved.get(slug)
            entry: dict[str, Any] = {
                "slug": slug,
                "display_name": prov["name"],
                "is_active": config.is_active if config else False,
                "is_test_mode": config.is_test_mode if config else True,
                "configured": config is not None,
                "credentials_masked": _mask_credentials(config.credentials) if config else {},
                "updated_at": config.updated_at.isoformat() if config else None,
                "name": prov["name"],
                "description": prov["description"],
                "color": prov["color"],
                "fields": prov["fields"],
            }
            result.append(entry)
        return result

    async def save_config(
        self,
        tenant_id: str,
        slug: str,
        credentials: dict[str, str],
        is_test_mode: bool,
    ) -> dict:
        if slug not in _CATALOG_BY_SLUG:
            raise ValueError(f"Provider '{slug}' not in catalogue")
        prov = _CATALOG_BY_SLUG[slug]
        config = await self.repo.upsert(
            tenant_id=tenant_id,
            slug=slug,
            display_name=prov["name"],
            credentials=credentials,
            is_test_mode=is_test_mode,
        )
        return {
            "slug": config.provider_slug,
            "display_name": config.display_name,
            "is_active": config.is_active,
            "is_test_mode": config.is_test_mode,
            "configured": True,
            "credentials_masked": _mask_credentials(config.credentials),
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }

    async def set_active(self, tenant_id: str, slug: str) -> dict:
        if slug not in _CATALOG_BY_SLUG:
            raise ValueError(f"Provider '{slug}' not in catalogue")
        config = await self.repo.set_active(tenant_id, slug)
        return {
            "slug": config.provider_slug,
            "display_name": config.display_name,
            "is_active": config.is_active,
            "is_test_mode": config.is_test_mode,
            "configured": True,
            "credentials_masked": _mask_credentials(config.credentials),
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }

    async def delete_config(self, tenant_id: str, slug: str) -> bool:
        return await self.repo.delete(tenant_id, slug)

    async def get_active(self, tenant_id: str) -> dict | None:
        configs = await self.repo.list_for_tenant(tenant_id)
        active = next((c for c in configs if c.is_active), None)
        if active is None:
            return None
        prov = _CATALOG_BY_SLUG.get(active.provider_slug, {})
        return {
            "slug": active.provider_slug,
            "display_name": active.display_name,
            "is_test_mode": active.is_test_mode,
            "description": prov.get("description", ""),
            "color": prov.get("color", "#666"),
        }

    # ─── Send email via active provider ───────────────────────────────────────

    async def send_email(
        self,
        tenant_id: str,
        to: str,
        subject: str,
        html_body: str,
    ) -> dict:
        """Send email through the active provider. Returns {ok, provider?, error?}."""
        active = await self.repo.list_for_tenant(tenant_id)
        provider = next((c for c in active if c.is_active), None)
        if provider is None:
            return {"ok": False, "error": "No active email provider configured"}

        slug = provider.provider_slug
        creds = provider.credentials or {}

        try:
            sender = _SENDERS.get(slug)
            if sender is None:
                return {"ok": False, "error": f"No sender implementation for '{slug}'"}
            await sender(creds, to, subject, html_body)
            logger.info("email_sent_via_provider", extra={"provider": slug, "to": to})
            return {"ok": True, "provider": slug}
        except Exception as exc:
            logger.exception("email_provider_send_failed", extra={"provider": slug, "to": to, "error": str(exc)})
            return {"ok": False, "provider": slug, "error": str(exc)}


# ─── Provider-specific send implementations ──────────────────────────────────

async def _send_via_sendgrid(creds: dict, to: str, subject: str, html_body: str) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {creds['api_key']}", "Content-Type": "application/json"},
            json={
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": creds.get("from_email", "noreply@trace.app"), "name": creds.get("from_name", "Trace")},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_body}],
            },
        )
        resp.raise_for_status()


async def _send_via_mailgun(creds: dict, to: str, subject: str, html_body: str) -> None:
    domain = creds["domain"]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.mailgun.net/v3/{domain}/messages",
            auth=("api", creds["api_key"]),
            data={
                "from": creds.get("from_email", f"noreply@{domain}"),
                "to": [to],
                "subject": subject,
                "html": html_body,
            },
        )
        resp.raise_for_status()


async def _send_via_postmark(creds: dict, to: str, subject: str, html_body: str) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.postmarkapp.com/email",
            headers={
                "X-Postmark-Server-Token": creds["server_api_token"],
                "Content-Type": "application/json",
            },
            json={
                "From": creds.get("from_email", "noreply@trace.app"),
                "To": to,
                "Subject": subject,
                "HtmlBody": html_body,
            },
        )
        resp.raise_for_status()


async def _send_via_resend(creds: dict, to: str, subject: str, html_body: str) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {creds['api_key']}", "Content-Type": "application/json"},
            json={
                "from": creds.get("from_email", "noreply@trace.app"),
                "to": [to],
                "subject": subject,
                "html": html_body,
            },
        )
        resp.raise_for_status()


async def _send_via_aws_ses(creds: dict, to: str, subject: str, html_body: str) -> None:
    try:
        import boto3
    except ImportError:
        raise RuntimeError("boto3 is required for AWS SES — pip install boto3")

    client = boto3.client(
        "ses",
        aws_access_key_id=creds["access_key_id"],
        aws_secret_access_key=creds["secret_access_key"],
        region_name=creds.get("region", "us-east-1"),
    )
    client.send_email(
        Source=creds.get("from_email", "noreply@trace.app"),
        Destination={"ToAddresses": [to]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
        },
    )


async def _send_via_gmail(creds: dict, to: str, subject: str, html_body: str) -> None:
    """Send via Gmail API using OAuth2 refresh token."""
    async with httpx.AsyncClient() as client:
        # Refresh the access token
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "refresh_token": creds["refresh_token"],
                "grant_type": "refresh_token",
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        # Build RFC 2822 message
        import base64
        msg = EmailMessage()
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(html_body, subtype="html")
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        resp = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"raw": raw},
        )
        resp.raise_for_status()


async def _send_via_outlook(creds: dict, to: str, subject: str, html_body: str) -> None:
    """Send via Microsoft Graph API using OAuth2 refresh token."""
    async with httpx.AsyncClient() as client:
        # Refresh the access token
        token_resp = await client.post(
            f"https://login.microsoftonline.com/{creds['tenant_id']}/oauth2/v2.0/token",
            data={
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "refresh_token": creds["refresh_token"],
                "grant_type": "refresh_token",
                "scope": "https://graph.microsoft.com/Mail.Send",
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        resp = await client.post(
            "https://graph.microsoft.com/v1.0/me/sendMail",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={
                "message": {
                    "subject": subject,
                    "body": {"contentType": "HTML", "content": html_body},
                    "toRecipients": [{"emailAddress": {"address": to}}],
                },
            },
        )
        resp.raise_for_status()


async def _send_via_smtp(creds: dict, to: str, subject: str, html_body: str) -> None:
    msg = EmailMessage()
    msg["From"] = creds.get("from_email", "noreply@trace.app")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(html_body, subtype="html")

    use_tls = str(creds.get("use_tls", "true")).lower() in ("true", "1", "yes")
    port = int(creds.get("port", 587))
    start_tls = not use_tls and port == 587

    await aiosmtplib.send(
        msg,
        hostname=creds["host"],
        port=port,
        username=creds.get("username") or None,
        password=creds.get("password") or None,
        use_tls=use_tls,
        start_tls=start_tls,
    )


_SENDERS = {
    "sendgrid": _send_via_sendgrid,
    "mailgun": _send_via_mailgun,
    "postmark": _send_via_postmark,
    "resend": _send_via_resend,
    "aws_ses": _send_via_aws_ses,
    "gmail": _send_via_gmail,
    "outlook": _send_via_outlook,
    "smtp": _send_via_smtp,
}
