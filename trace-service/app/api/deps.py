"""FastAPI dependency functions shared across routers."""
from __future__ import annotations

import re
import uuid

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, UnauthorizedError
from app.db.session import get_db_session


async def get_tenant_id(
    request: Request,
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    db: AsyncSession = Depends(get_db_session),
) -> uuid.UUID:
    """
    Resolves X-Tenant-Id (slug or UUID string) → validated tenant UUID.

    Caches the resolved UUID on request.state._tenant_id to avoid
    double DB lookups when multiple dependencies call this.
    """
    # Input length validation
    if len(x_tenant_id) > 255:
        raise UnauthorizedError("Invalid tenant identifier")

    # Check cache first
    cached = getattr(request.state, "_tenant_id", None)
    if cached is not None:
        return cached

    from app.db.models import Tenant
    from sqlalchemy import select

    # Try parsing as UUID first, then fall back to slug lookup
    tenant_uuid: uuid.UUID | None = None
    try:
        tenant_uuid = uuid.UUID(x_tenant_id)
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_uuid))
        tenant = result.scalar_one_or_none()
    except ValueError:
        # Not a UUID — treat as slug; validate format
        if not re.match(r'^[a-zA-Z0-9_-]+$', x_tenant_id):
            raise UnauthorizedError("Invalid tenant identifier")
        result = await db.execute(select(Tenant).where(Tenant.slug == x_tenant_id))
        tenant = result.scalar_one_or_none()

    if tenant is None or tenant.status != "active":
        raise UnauthorizedError("Invalid or inactive tenant")

    request.state._tenant_id = tenant.id
    return tenant.id
