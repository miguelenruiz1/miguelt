"""JWT decoding + credential encryption helpers."""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
import jwt

from app.core.settings import get_settings


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def _fernet_from_sha256() -> Fernet:
    """Derive the Fernet key via SHA-256(ENCRYPTION_KEY).

    SHA-256 maps any-length input to 32 uniformly-distributed bytes — unlike
    the previous truncate+null-pad scheme which collapsed two distinct keys
    sharing a 32-char prefix (and produced low-entropy keys when the raw
    value was shorter than 32 chars).
    """
    settings = get_settings()
    digest = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _fernet_legacy() -> Fernet:
    """Legacy key derivation kept for rolling decrypt of pre-fix ciphertexts.

    Anything encrypted before the SHA-256 switch is still readable; new
    writes always use the SHA-256 key. Remove this helper after a migration
    pass re-encrypts every stored credential.
    """
    settings = get_settings()
    raw = settings.ENCRYPTION_KEY.encode()[:32].ljust(32, b"\0")
    return Fernet(base64.urlsafe_b64encode(raw))


def encrypt_credentials(data: str) -> str:
    return _fernet_from_sha256().encrypt(data.encode()).decode()


def decrypt_credentials(encrypted: str) -> str:
    token = encrypted.encode()
    try:
        return _fernet_from_sha256().decrypt(token).decode()
    except InvalidToken:
        # Fall back to the legacy key — ciphertext from before the fix.
        return _fernet_legacy().decrypt(token).decode()
