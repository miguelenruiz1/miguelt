"""JWT token validation."""
from __future__ import annotations

from jose import jwt

from app.core.settings import get_settings


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
