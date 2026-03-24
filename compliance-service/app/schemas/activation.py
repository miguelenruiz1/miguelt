"""Schemas for TenantFrameworkActivation."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ActivationCreate(BaseModel):
    framework_slug: str
    export_destination: list[str] | None = None
    metadata: dict | None = None


class ActivationUpdate(BaseModel):
    export_destination: list[str] | None = None
    metadata: dict | None = None
    is_active: bool | None = None


class ActivationResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    framework_id: uuid.UUID
    is_active: bool
    export_destination: list[str] | None
    activated_at: datetime
    activated_by: uuid.UUID | None
    metadata_: dict
    framework_slug: str
