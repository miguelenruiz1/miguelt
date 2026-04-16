"""TOTP (Time-based One-Time Password) + recovery codes service.

Implements RFC 6238 TOTP using pyotp. Recovery codes are hashed with bcrypt
(same scheme as passwords) and stored in users.totp_recovery_codes as JSONB.

Pending TOTP secrets (from /2fa/setup before /2fa/verify) are kept in Redis
with a short TTL. This avoids persisting a half-configured secret on the user
row, and stops a second /setup call from wiping a previous pending attempt.
"""
from __future__ import annotations

import secrets
import string
from typing import Any

import pyotp
from redis import asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, UnauthorizedError, ValidationError
from app.core.security import hash_password, verify_password
from app.db.models import User


ISSUER = "Trace"
RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_LEN = 10  # 10 chars => ~59 bits entropy w/ alphanumeric
PENDING_SECRET_TTL = 600  # 10 minutes — enough for an operator to scan + verify


def _gen_recovery_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(RECOVERY_CODE_LEN))


def _pending_key(user_id: str) -> str:
    return f"totp:pending:{user_id}"


class TOTPService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis | None = None) -> None:
        self.db = db
        self.redis = redis

    async def _get_user(self, user_id: str) -> User:
        res = await self.db.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        return user

    async def setup(self, user_id: str) -> dict[str, Any]:
        """Generate a TOTP secret (unverified) and return provisioning URI.

        Secret is parked in Redis with a TTL until the user confirms a TOTP
        code via verify_and_enable(). If Redis is unavailable we fall back to
        persisting on the user row so the flow still works.
        """
        user = await self._get_user(user_id)
        secret = pyotp.random_base32()

        if self.redis is not None:
            await self.redis.setex(_pending_key(user_id), PENDING_SECRET_TTL, secret)
        else:
            # Fallback path: park the secret on the row but keep enabled=false.
            user.totp_secret = secret
            user.totp_enabled = False
            await self.db.flush()

        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name=ISSUER)
        return {
            "secret": secret,
            "otpauth_uri": uri,
            "issuer": ISSUER,
            "account": user.email,
        }

    async def verify_and_enable(self, user_id: str, totp_code: str) -> list[str]:
        """Verify TOTP code against pending secret; on success enable 2FA and
        return 10 plain recovery codes (one-time shown).
        """
        user = await self._get_user(user_id)

        pending: str | None = None
        if self.redis is not None:
            raw = await self.redis.get(_pending_key(user_id))
            pending = raw.decode() if isinstance(raw, (bytes, bytearray)) else raw
        secret = pending or user.totp_secret
        if not secret:
            raise ValidationError("2FA setup not started — call /setup first")

        if not pyotp.TOTP(secret).verify(totp_code, valid_window=1):
            raise UnauthorizedError("Código TOTP inválido")

        # Generate and hash 10 recovery codes
        plain_codes = [_gen_recovery_code() for _ in range(RECOVERY_CODE_COUNT)]
        hashed = [hash_password(c) for c in plain_codes]

        user.totp_secret = secret
        user.totp_recovery_codes = hashed
        user.totp_enabled = True
        await self.db.flush()

        if self.redis is not None:
            await self.redis.delete(_pending_key(user_id))
        return plain_codes

    async def verify_code(self, user: User, code: str) -> bool:
        """Verify either a TOTP code or a recovery code. If a recovery code
        matches, it is consumed (removed from the list). Returns True if valid.

        Recovery-code consumption is serialized via SELECT ... FOR UPDATE on
        the user row. Without the row lock, two concurrent requests with the
        same recovery code can both verify bcrypt in parallel and both pop()
        from the in-memory list, letting the code be spent twice.
        """
        if not user.totp_enabled or not user.totp_secret:
            return False

        # Try TOTP first (normal case)
        if pyotp.TOTP(user.totp_secret).verify(code, valid_window=1):
            return True

        # Recovery-code path: lock the user row and re-read the codes so two
        # concurrent callers can't both consume the same entry.
        locked = (
            await self.db.execute(
                select(User).where(User.id == user.id).with_for_update()
            )
        ).scalar_one_or_none()
        if locked is None:
            return False

        codes = list(locked.totp_recovery_codes or [])
        for i, h in enumerate(codes):
            try:
                if verify_password(code, h):
                    codes.pop(i)
                    locked.totp_recovery_codes = codes
                    await self.db.flush()
                    # Keep the caller's stale ORM instance in sync so any
                    # downstream code reading user.totp_recovery_codes sees
                    # the consumed list.
                    user.totp_recovery_codes = codes
                    return True
            except Exception:
                continue
        return False

    async def disable(self, user_id: str, password: str, totp_code: str) -> None:
        user = await self._get_user(user_id)
        if not user.totp_enabled:
            raise ValidationError("2FA no está habilitado")
        if not user.password_hash or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Contraseña incorrecta")
        if not await self.verify_code(user, totp_code):
            raise UnauthorizedError("Código 2FA inválido")
        user.totp_enabled = False
        user.totp_secret = None
        user.totp_recovery_codes = []
        await self.db.flush()
