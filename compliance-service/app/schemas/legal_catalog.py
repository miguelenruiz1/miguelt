"""Pydantic schemas for the legal requirements catalog."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Ambito = Literal[
    "land_use_rights",
    "environmental_protection",
    "labor_rights",
    "human_rights",
    "third_party_rights_fpic",
    "fiscal_customs_anticorruption",
]

AppliesToScale = Literal[
    "all",
    "smallholder",
    "medium",
    "industrial",
    "medium_or_industrial",
]

ComplianceStatus = Literal["satisfied", "missing", "na", "pending"]
EvidenceWeight = Literal["primary", "secondary", "affidavit"]


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LegalRequirementResponse(OrmBase):
    id: uuid.UUID
    catalog_id: uuid.UUID
    ambito: Ambito
    code: str
    title: str
    description: str | None = None
    legal_reference: str | None = None
    applies_to_scale: AppliesToScale
    required_document_type: str | None = None
    is_blocking: bool
    sort_order: int


class LegalCatalogResponse(OrmBase):
    id: uuid.UUID
    country_code: str
    commodity: str
    version: str
    source: str | None = None
    source_url: str | None = None
    is_active: bool
    created_at: datetime


class LegalCatalogWithRequirements(LegalCatalogResponse):
    requirements: list[LegalRequirementResponse] = Field(default_factory=list)


class PlotLegalComplianceResponse(OrmBase):
    id: uuid.UUID
    plot_id: uuid.UUID
    requirement_id: uuid.UUID
    status: ComplianceStatus
    evidence_media_id: uuid.UUID | None = None
    evidence_notes: str | None = None
    evidence_weight: EvidenceWeight = "primary"
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PlotLegalComplianceUpdate(BaseModel):
    status: ComplianceStatus
    evidence_media_id: uuid.UUID | None = None
    evidence_notes: str | None = None
    evidence_weight: EvidenceWeight | None = None


class PlotLegalComplianceItem(BaseModel):
    """Denormalized view: a requirement + its current status for a plot."""
    requirement: LegalRequirementResponse
    compliance: PlotLegalComplianceResponse | None = None


class PlotLegalComplianceSummary(BaseModel):
    plot_id: uuid.UUID
    catalog_id: uuid.UUID | None = None
    producer_scale: str | None = None
    total_requirements: int
    applicable_requirements: int
    satisfied: int
    missing: int
    pending: int
    na: int
    blocking_missing: int
    items: list[PlotLegalComplianceItem]
