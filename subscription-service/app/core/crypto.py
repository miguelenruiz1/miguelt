"""Credential encryption helpers for JSONB-backed gateway secrets.

`PaymentGatewayConfig.credentials` holds Wompi / Stripe / etc. API keys. We
encrypt at rest using Fernet with the key derived from `JWT_SECRET` (already
production-gated). Legacy plaintext rows are returned transparently so the
rollout doesn't need a data migration first — new writes land encrypted,
reads handle both shapes.

Keep in sync with `user-service/app/core/crypto.py`.
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
    settings = get_settings()
    digest = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_credentials(credentials: dict[str, Any] | None) -> dict[str, Any]:
    if not credentials:
        return {}
    payload = json.dumps(credentials, sort_keys=True).encode()
    token = _fernet().encrypt(payload).decode()
    return {_ENC_KEY: token}


def decrypt_credentials(stored: dict[str, Any] | None) -> dict[str, Any]:
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
    return dict(stored) if isinstance(stored, dict) else {}
