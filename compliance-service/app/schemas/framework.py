"""Schemas for ComplianceFramework."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class FrameworkResponse(OrmBase):
    id: uuid.UUID
    slug: str
    name: str
    description: str | None
    issuing_body: str | None
    target_markets: list[str]
    applicable_commodities: list[str]
    requires_geolocation: bool
    requires_dds: bool
    requires_scientific_name: bool
    document_retention_years: int
    cutoff_date: date | None
    legal_reference: str | None
    validation_rules: dict
    is_active: bool
    version: str
    created_at: datetime
    updated_at: datetime
