"""FastAPI dependencies: tenant resolution and S2S auth."""
from __future__ import annotations

import uuid

from fastapi import Header, HTTPException

from app.core.settings import get_settings


async def get_tenant_id(
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
) -> uuid.UUID:
    """Resolve X-Tenant-Id header to UUID. Accepts UUID or any tenant slug."""
    if not x_tenant_id or len(x_tenant_id) > 255:
        raise HTTPException(status_code=400, detail="Invalid X-Tenant-Id")
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError:
        pass
    # For slug 'default', return the well-known UUID
    if x_tenant_id == "default":
        return uuid.UUID("00000000-0000-0000-0000-000000000001")
    # For any other slug, generate a deterministic UUID from the slug
    return uuid.uuid5(uuid.NAMESPACE_DNS, x_tenant_id)


async def verify_service_token(
    x_service_token: str = Header(..., alias="X-Service-Token"),
) -> str:
    """Validate inter-service shared secret."""
    settings = get_settings()
    if x_service_token != settings.S2S_SERVICE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid service token")
    return x_service_token
