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

    We validate the audience and issuer **when the token carries them**.
    Legacy tokens minted before the aud/iss rollout (missing those claims)
    are still accepted, so we don't log everyone out on deploy; but a token
    that claims `aud=something-else` is rejected — which is what closes the
    cross-service JWT reuse hole.
    """
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_aud": False, "verify_iss": False},
    )
    aud = payload.get("aud")
    iss = payload.get("iss")
    if aud is not None and aud != JWT_AUDIENCE:
        raise jwt.InvalidAudienceError(f"unexpected aud={aud!r}")
    if iss is not None and iss != JWT_ISSUER:
        raise jwt.InvalidIssuerError(f"unexpected iss={iss!r}")
    return payload


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
