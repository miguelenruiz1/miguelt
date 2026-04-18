"""JWT token validation — subscription-service only decodes, never creates tokens."""
from __future__ import annotations

import jwt

from app.core.settings import get_settings


def decode_token(token: str) -> dict:
    """Decode and verify JWT. Raises JWTError on failure."""
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM], audience="trace", issuer="trace.user-service")
