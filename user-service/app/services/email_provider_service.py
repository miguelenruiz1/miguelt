"""Service for email provider configuration management and sending."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_credentials, encrypt_credentials
from app.repositories.email_provider_repo import EmailProviderRepository

logger = logging.getLogger(__name__)


def _read_credentials(config) -> dict:
    """Always return plaintext creds to callers, transparently handling
    both the new encrypted shape and legacy plaintext rows."""
    return decrypt_credentials(config.credentials if config else None)


# ─── Provider catalogue (platform-level only) ───────────────────────────────

PROVIDER_CATALOG: list[dict[str, Any]] = [
    {
        "slug": "resend",
        "name": "Resend",
        "description": "Email transaccional via Resend API. Configurado a nivel plataforma.",
        "color": "#000000",
        "fields": [
            {"key": "api_key",    "label": "API Key",    "type": "password", "required": True},
            {"key": "from_email", "label": "From Email", "type": "text",     "required": True},
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
                "configured": config is not None,
                "credentials_masked": _mask_credentials(_read_credentials(config)),
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
    ) -> dict:
        if slug not in _CATALOG_BY_SLUG:
            raise ValueError(f"Provider '{slug}' not in catalogue")
        prov = _CATALOG_BY_SLUG[slug]
        config = await self.repo.upsert(
            tenant_id=tenant_id,
            slug=slug,
            display_name=prov["name"],
            credentials=encrypt_credentials(credentials),
        )
        return {
            "slug": config.provider_slug,
            "display_name": config.display_name,
            "is_active": config.is_active,
            "configured": True,
            "credentials_masked": _mask_credentials(credentials),
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
            "configured": True,
            "credentials_masked": _mask_credentials(_read_credentials(config)),
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
        creds = _read_credentials(provider)

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

async def _send_via_resend(creds: dict, to: str, subject: str, html_body: str) -> None:
    # Timeout prevents a hung Resend API from blocking a request path forever
    # (email sends run inline on webhook/register endpoints).
    async with httpx.AsyncClient(timeout=15.0) as client:
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


_SENDERS = {
    "resend": _send_via_resend,
}
