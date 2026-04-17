"""Internal S2S endpoints for inter-service calls.

Protected by the shared `X-Service-Token` header (matches
`settings.S2S_SERVICE_TOKEN`). Exposes read-only data that other services
need without relying on user-session JWTs.

Added for FASE2 billing completeness:
- GET /internal/email-config/{tenant_id} — active Resend credentials
- GET /internal/tenant-owner-email/{tenant_id} — first superuser/admin email
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.db.models import EmailProviderConfig, User
from app.db.session import get_db_session

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])


def require_s2s(x_service_token: Annotated[str | None, Header()] = None) -> None:
    # Constant-time comparison so an attacker can't recover the token
    # byte-by-byte via response-time measurements. The other backends
    # already use compare_digest; this one was the odd one out.
    import secrets as _secrets
    settings = get_settings()
    expected = settings.S2S_SERVICE_TOKEN
    if not x_service_token or not _secrets.compare_digest(x_service_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing service token",
        )


@router.get("/email-config/{tenant_id}", summary="Active email provider credentials (S2S)")
async def get_email_config(
    tenant_id: str,
    _ok: Annotated[None, Depends(require_s2s)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    result = await db.execute(
        select(EmailProviderConfig).where(
            EmailProviderConfig.tenant_id == tenant_id,
            EmailProviderConfig.is_active.is_(True),
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail="No active email provider")
    creds = cfg.credentials or {}
    return {
        "slug": cfg.provider_slug,
        "api_key": creds.get("api_key", ""),
        "from_email": creds.get("from_email", "onboarding@resend.dev"),
        "is_test_mode": cfg.is_test_mode,
    }


@router.get(
    "/tenant-owner-email/{tenant_id}",
    summary="First superuser / admin email for a tenant (S2S)",
)
async def get_tenant_owner_email(
    tenant_id: str,
    _ok: Annotated[None, Depends(require_s2s)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    # Prefer superusers, then admins by created_at
    result = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_id, User.is_active.is_(True))
        .order_by(User.is_superuser.desc(), User.created_at.asc())
    )
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=404, detail="No active user found for tenant")
    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": getattr(user, "full_name", None),
        "is_superuser": user.is_superuser,
    }
