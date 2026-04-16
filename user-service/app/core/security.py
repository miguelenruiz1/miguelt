"""JWT token creation/validation and password hashing."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from jwt import PyJWTError as JWTError  # noqa: F401  (re-exported for callers)
from passlib.context import CryptContext

from app.core.settings import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT identity claims. user-service issues the tokens; every other service
# (subscription, inventory, etc.) should decode with audience="trace" to
# reject tokens that were minted for a different system sharing the secret.
# Verification is *optional* during rollout — legacy tokens in flight lack
# these claims — and tightens to strict once all active refresh tokens
# have rotated (ACCESS=15min, REFRESH=7d).
JWT_ISSUER = "trace.user-service"
JWT_AUDIENCE = "trace"


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, tenant_id: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "type": "access",
        "iat": now,
        "exp": exp,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str, tenant_id: str) -> tuple[str, str]:
    """Returns (token, jti)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid4())
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "type": "refresh",
        "jti": jti,
        "iat": now,
        "exp": exp,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict:
    """Decode and verify JWT. Raises JWTError on failure.

    During the rollout window we decode without audience/issuer checks so
    legacy tokens stay valid. When an older token (missing `aud`) is seen,
    PyJWT would normally reject it; by passing `options={'verify_aud':
    False}` we accept both legacy and new tokens. Tighten by removing the
    override once all active refresh tokens have rotated.
    """
    settings = get_settings()
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
        options={"verify_aud": False, "verify_iss": False},
    )


def create_2fa_challenge_token(user_id: str, tenant_id: str) -> str:
    """Short-lived (5min) token issued after password-verified but before TOTP."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "type": "2fa_challenge",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token_2fa(user_id: str, tenant_id: str) -> str:
    """Access token with `2fa: true` claim — used by endpoints that require
    that the user completed a full 2FA login in this session.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "type": "access",
        "2fa": True,
        "iat": now,
        "exp": exp,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
