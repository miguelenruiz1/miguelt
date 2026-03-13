"""Audit log schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.domain.schemas.base import OrmBase


class AuditLogOut(OrmBase):
    id: str
    tenant_id: str
    user_id: str
    user_email: str | None
    user_name: str | None = None
    action: str
    description: str | None = None
    resource_type: str
    resource_id: str
    old_data: dict[str, Any] | None
    new_data: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class PaginatedAuditLogs(BaseModel):
    items: list[AuditLogOut]
    total: int
    offset: int
    limit: int
