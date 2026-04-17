"""Credential encryption helpers for JSONB-backed secret storage.

Rationale: `EmailProviderConfig.credentials` is a JSONB column that holds
tenant-provided API keys (Resend token today, more providers tomorrow).
Storing them in plaintext means anyone with read access to the user-service
DB walks out with every tenant's outbound-email credentials.

This module provides `encrypt_credentials` / `decrypt_credentials` built on
Fernet with the key derived from `settings.JWT_SECRET` (which is already
mandatory in production via a settings validator).

Format on disk: `{"__enc": "<Fernet-token>"}` — any row that does NOT match
that shape is treated as legacy plaintext and returned as-is, so we can roll
the change out without needing a backfill migration first.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.settings import get_settings


_ENC_KEY = "__enc"


def _fernet() -> Fernet:
    """Derive the Fernet key via SHA-256(JWT_SECRET).

    JWT_SECRET is the strongest server-only secret we already gate in prod
    (>=32 chars, not a known placeholder), so reusing it avoids introducing
    a second mandatory env var just for this. If we ever need key rotation
    independent of JWT we add a dedicated ENCRYPTION_KEY setting and keep a
    dual-decrypt fallback here, same as integration-service.
    """
    settings = get_settings()
    digest = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_credentials(credentials: dict[str, Any] | None) -> dict[str, Any]:
    """Return a JSONB-safe dict whose values are encrypted.

    An empty / None input is stored as empty dict (not encrypted) so the UI
    can still distinguish "configured but empty" from "never configured".
    """
    if not credentials:
        return {}
    payload = json.dumps(credentials, sort_keys=True).encode()
    token = _fernet().encrypt(payload).decode()
    return {_ENC_KEY: token}


def decrypt_credentials(stored: dict[str, Any] | None) -> dict[str, Any]:
    """Inverse of encrypt_credentials, with a plaintext-legacy fallback.

    Returns an empty dict if the input is missing. If the row looks
    encrypted (`{"__enc": "..."}`) we decrypt; otherwise we assume it's a
    legacy plaintext dict and return it verbatim. A corrupt ciphertext
    (wrong key, truncated, etc.) returns {} and logs — better than
    500-ing on every request for that tenant.
    """
    if not stored:
        return {}
    if isinstance(stored, dict) and _ENC_KEY in stored and len(stored) == 1:
        token = stored[_ENC_KEY]
        if not isinstance(token, str):
            return {}
        try:
            raw = _fernet().decrypt(token.encode()).decode()
            return json.loads(raw)
        except (InvalidToken, ValueError, json.JSONDecodeError):
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "credentials_decrypt_failed: returning empty dict"
            )
            return {}
    # Legacy plaintext — return shallow copy to avoid mutating the model.
    return dict(stored) if isinstance(stored, dict) else {}
