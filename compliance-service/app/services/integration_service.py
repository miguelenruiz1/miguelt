"""Compliance integration credentials manager — per-tenant encrypted API keys."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.settings import get_settings
from app.models.integration import ComplianceIntegration

log = get_logger(__name__)


_DEFAULT_TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Mask pattern: "xxxxxxx************yyyy" or full "********"
_MASK_RE = re.compile(r"^[^*]{0,7}\*{8,}.*$|^\*+$")


def _get_fernet() -> Fernet:
    settings = get_settings()
    key = settings.FERNET_KEY.strip() if settings.FERNET_KEY else ""
    if key:
        # Accept already-base64-encoded Fernet keys (44 chars)
        try:
            return Fernet(key.encode())
        except Exception:
            log.warning("fernet_key_invalid_falling_back_to_jwt_derivation")
    # Fallback (DEV ONLY): derive from JWT_SECRET
    secret = settings.JWT_SECRET.encode()
    key_bytes = hashlib.sha256(secret).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def _encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        log.error("integration_decrypt_invalid_token")
        return ""
    except Exception as exc:
        log.error("integration_decrypt_failed", exc=str(exc))
        return ""


def _mask(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 11:
        return "********"
    return value[:7] + "************" + value[-4:]


def _looks_masked(value: str) -> bool:
    return bool(_MASK_RE.match(value)) and "*" in value


PROVIDERS = {
    "gfw": {
        "display_name": "Global Forest Watch",
        "fields": ["api_key"],
        "description": "API para análisis satelital de deforestación (gratis)",
    },
    "traces_nt": {
        "display_name": "EU TRACES NT",
        "fields": ["username", "auth_key", "env", "client_id"],
        "description": "Portal de la UE para sumisión de Declaraciones de Diligencia Debida (DDS)",
    },
}


class IntegrationCredentialsService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID | None = None) -> None:
        self.db = db
        self.tenant_id = tenant_id or _DEFAULT_TENANT

    async def get_or_create(self, provider: str) -> ComplianceIntegration:
        result = await self.db.execute(
            select(ComplianceIntegration).where(
                ComplianceIntegration.provider == provider,
                ComplianceIntegration.tenant_id == self.tenant_id,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            meta = PROVIDERS.get(provider, {})
            integration = ComplianceIntegration(
                id=str(uuid.uuid4()),
                tenant_id=self.tenant_id,
                provider=provider,
                display_name=meta.get("display_name", provider),
                config={},
            )
            self.db.add(integration)
            await self.db.flush()
        return integration

    async def list_all(self) -> list[dict]:
        # Fields that are NOT secret and should be returned in clear-text
        NON_SECRET = {"env", "client_id", "username"}
        results = []
        for slug, meta in PROVIDERS.items():
            integ = await self.get_or_create(slug)
            creds = self._decrypt_credentials(integ)
            masked_creds = {k: _mask(v) for k, v in creds.items() if k not in NON_SECRET}
            for k in NON_SECRET:
                if k in creds:
                    masked_creds[k] = creds[k]
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
        # Validate env enum if provided
        if "env" in data and data["env"] not in (None, "acceptance", "production"):
            raise ValueError(f"Invalid env: {data['env']}. Must be 'acceptance' or 'production'.")
        # Merge new fields with existing — reject masked placeholders and whitespace
        for k, v in data.items():
            if not v or not isinstance(v, str):
                continue
            v = v.strip()
            if not v:
                continue
            if _looks_masked(v):
                continue
            existing[k] = v
        integ.credentials_enc = _encrypt(json.dumps(existing))
        integ.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        try:
            from app.api.deps import get_redis
            rd = await get_redis()
            await rd.delete(f"compliance:creds:{self.tenant_id}:{provider}")
        except Exception:
            pass
        return {"provider": provider, "is_configured": True, "updated_at": integ.updated_at.isoformat()}

    def _decrypt_credentials(self, integ: ComplianceIntegration) -> dict:
        if not integ.credentials_enc:
            return {}
        try:
            raw = _decrypt(integ.credentials_enc)
            if not raw:
                return {}
            return json.loads(raw)
        except Exception as exc:
            log.error("integration_decrypt_load_failed", exc=str(exc))
            return {}

    async def get_credentials(self, provider: str) -> dict:
        """Get decrypted credentials for use by services (per tenant)."""
        integ = await self.get_or_create(provider)
        return self._decrypt_credentials(integ)
