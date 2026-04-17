"""Service for payment gateway configuration management."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_credentials, encrypt_credentials
from app.repositories.payment_repo import PaymentGatewayRepository


def _read_credentials(config) -> dict:
    """Return plaintext credentials for a config row, handling both the new
    encrypted shape and legacy plaintext rows."""
    return decrypt_credentials(config.credentials if config else None)


# ─── Gateway catalogue (hardcoded) ────────────────────────────────────────────

GATEWAY_CATALOG: list[dict[str, Any]] = [
    {
        "slug": "wompi",
        "name": "Wompi",
        "description": "Pasarela de pagos de Bancolombia. Acepta tarjetas, PSE, Nequi y Bancolombia.",
        "color": "#5C2D91",
        "fields": [
            {"key": "public_key",     "label": "Llave pública (pub_...)",  "type": "text",     "required": True},
            {"key": "private_key",    "label": "Llave privada (prv_...)",  "type": "password", "required": True},
            {"key": "events_secret",  "label": "Secreto de eventos",       "type": "password", "required": False},
            {"key": "integrity_key",  "label": "Llave de integridad",      "type": "password", "required": True},
        ],
    },
]

_CATALOG_BY_SLUG: dict[str, dict] = {g["slug"]: g for g in GATEWAY_CATALOG}


def _mask_credentials(credentials: dict) -> dict:
    """Replace all credential values with bullets."""
    return {k: "••••••" for k in credentials} if credentials else {}


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = PaymentGatewayRepository(db)
        self.db = db

    def get_catalog(self) -> list[dict]:
        return GATEWAY_CATALOG

    async def list_configs(self, tenant_id: str) -> list[dict]:
        """Return catalogue enriched with saved config (credentials masked)."""
        saved = {c.gateway_slug: c for c in await self.repo.list_for_tenant(tenant_id)}
        result = []
        for gw in GATEWAY_CATALOG:
            slug = gw["slug"]
            config = saved.get(slug)
            entry: dict[str, Any] = {
                "slug": slug,
                "display_name": gw["name"],
                "is_active": config.is_active if config else False,
                "is_test_mode": config.is_test_mode if config else True,
                "configured": config is not None,
                "credentials_masked": _mask_credentials(_read_credentials(config)),
                "updated_at": config.updated_at.isoformat() if config else None,
                # catalogue metadata
                "name": gw["name"],
                "description": gw["description"],
                "color": gw["color"],
                "fields": gw["fields"],
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
            raise ValueError(f"Gateway '{slug}' not in catalogue")
        gw = _CATALOG_BY_SLUG[slug]
        config = await self.repo.upsert(
            tenant_id=tenant_id,
            slug=slug,
            display_name=gw["name"],
            credentials=encrypt_credentials(credentials),
            is_test_mode=is_test_mode,
        )
        return {
            "slug": config.gateway_slug,
            "display_name": config.display_name,
            "is_active": config.is_active,
            "is_test_mode": config.is_test_mode,
            "configured": True,
            "credentials_masked": _mask_credentials(credentials),
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }

    async def set_active(self, tenant_id: str, slug: str) -> dict:
        if slug not in _CATALOG_BY_SLUG:
            raise ValueError(f"Gateway '{slug}' not in catalogue")
        config = await self.repo.set_active(tenant_id, slug)
        return {
            "slug": config.gateway_slug,
            "display_name": config.display_name,
            "is_active": config.is_active,
            "is_test_mode": config.is_test_mode,
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
        gw = _CATALOG_BY_SLUG.get(active.gateway_slug, {})
        return {
            "slug": active.gateway_slug,
            "display_name": active.display_name,
            "is_test_mode": active.is_test_mode,
            "description": gw.get("description", ""),
            "color": gw.get("color", "#666"),
        }
