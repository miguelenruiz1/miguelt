"""Compliance integration credentials manager — encrypts/decrypts API keys."""
from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.models.integration import ComplianceIntegration


def _get_fernet() -> Fernet:
    secret = get_settings().JWT_SECRET.encode()
    key_bytes = hashlib.sha256(secret).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def _encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except (InvalidToken, Exception):
        return ""


def _mask(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 11:
        return "********"
    return value[:7] + "************" + value[-4:]


PROVIDERS = {
    "gfw": {
        "display_name": "Global Forest Watch",
        "fields": ["api_key"],
        "description": "API para análisis satelital de deforestación (gratis)",
    },
    "traces_nt": {
        "display_name": "EU TRACES NT",
        "fields": ["username", "auth_key", "env"],
        "description": "Portal de la UE para sumisión de Declaraciones de Diligencia Debida (DDS)",
    },
}


class IntegrationCredentialsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create(self, provider: str) -> ComplianceIntegration:
        result = await self.db.execute(select(ComplianceIntegration).where(ComplianceIntegration.provider == provider))
        integration = result.scalar_one_or_none()
        if not integration:
            meta = PROVIDERS.get(provider, {})
            integration = ComplianceIntegration(
                id=str(uuid.uuid4()),
                provider=provider,
                display_name=meta.get("display_name", provider),
                config={},
            )
            self.db.add(integration)
            await self.db.flush()
        return integration

    async def list_all(self) -> list[dict]:
        results = []
        for slug, meta in PROVIDERS.items():
            integ = await self.get_or_create(slug)
            creds = self._decrypt_credentials(integ)
            masked_creds = {k: _mask(v) for k, v in creds.items() if k != "env"}
            if "env" in creds:
                masked_creds["env"] = creds["env"]
            results.append({
                "provider": slug,
                "display_name": meta["display_name"],
                "description": meta.get("description", ""),
                "fields": meta["fields"],
                "is_configured": bool(integ.credentials_enc),
                "is_active": integ.is_active,
                "credentials": masked_creds,
                "updated_at": integ.updated_at.isoformat() if integ.updated_at else None,
            })
        return results

    async def update(self, provider: str, data: dict) -> dict:
        integ = await self.get_or_create(provider)
        existing = self._decrypt_credentials(integ)
        # Merge new fields with existing
        for k, v in data.items():
            if v:
                existing[k] = v
        integ.credentials_enc = _encrypt(json.dumps(existing))
        integ.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return {"provider": provider, "is_configured": True, "updated_at": integ.updated_at.isoformat()}

    def _decrypt_credentials(self, integ: ComplianceIntegration) -> dict:
        if not integ.credentials_enc:
            return {}
        try:
            return json.loads(_decrypt(integ.credentials_enc))
        except Exception:
            return {}

    async def get_credentials(self, provider: str) -> dict:
        """Get decrypted credentials for use by services."""
        integ = await self.get_or_create(provider)
        return self._decrypt_credentials(integ)
