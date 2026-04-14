"""Schemas for the certification scheme registry."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SchemeType = Literal["commodity_specific", "generic", "national"]
SchemeScope = Literal["legality", "chain_of_custody", "sustainability", "full"]


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CertificationSchemeResponse(OrmBase):
    id: uuid.UUID
    slug: str
    name: str
    scheme_type: SchemeType
    scope: SchemeScope
    commodities: list[str]
    ownership_score: int
    transparency_score: int
    audit_score: int
    grievance_score: int
    total_score: int
    covers_eudr_ambitos: list[str]
    reference_url: str | None = None
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CertificationSchemeUpdate(BaseModel):
    name: str | None = None
    scheme_type: SchemeType | None = None
    scope: SchemeScope | None = None
    commodities: list[str] | None = None
    ownership_score: int | None = Field(default=None, ge=0, le=3)
    transparency_score: int | None = Field(default=None, ge=0, le=3)
    audit_score: int | None = Field(default=None, ge=0, le=3)
    grievance_score: int | None = Field(default=None, ge=0, le=3)
    covers_eudr_ambitos: list[str] | None = None
    reference_url: str | None = None
    notes: str | None = None
    is_active: bool | None = None
