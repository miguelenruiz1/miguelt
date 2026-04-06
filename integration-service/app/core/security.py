"""JWT decoding + credential encryption helpers."""
from __future__ import annotations

import base64

from cryptography.fernet import Fernet
import jwt

from app.core.settings import get_settings


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def _get_fernet() -> Fernet:
    settings = get_settings()
    key = base64.urlsafe_b64encode(settings.ENCRYPTION_KEY.encode()[:32].ljust(32, b"\0"))
    return Fernet(key)


def encrypt_credentials(data: str) -> str:
    return _get_fernet().encrypt(data.encode()).decode()


def decrypt_credentials(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()
