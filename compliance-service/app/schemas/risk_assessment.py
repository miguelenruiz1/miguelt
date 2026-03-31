"""Schemas for EUDR risk assessments (Art. 10-11)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentCreate(BaseModel):
    record_id: uuid.UUID
    country_risk_level: str | None = None
    country_risk_notes: str | None = None
    country_benchmarking_source: str | None = None
    supply_chain_risk_level: str | None = None
    supply_chain_notes: str | None = None
    supplier_verification_status: str = "not_started"
    traceability_confidence: str = "none"
    regional_risk_level: str | None = None
    deforestation_prevalence: str | None = None
    indigenous_rights_risk: bool = False
    corruption_index_note: str | None = None
    mitigation_measures: list[dict] | None = None
    additional_info_requested: bool = False
    independent_audit_required: bool = False
    overall_risk_level: str | None = None
    conclusion: str | None = None
    conclusion_notes: str | None = None


class RiskAssessmentUpdate(BaseModel):
    country_risk_level: str | None = None
    country_risk_notes: str | None = None
    country_benchmarking_source: str | None = None
    supply_chain_risk_level: str | None = None
    supply_chain_notes: str | None = None
    supplier_verification_status: str | None = None
    traceability_confidence: str | None = None
    regional_risk_level: str | None = None
    deforestation_prevalence: str | None = None
    indigenous_rights_risk: bool | None = None
    corruption_index_note: str | None = None
    mitigation_measures: list[dict] | None = None
    additional_info_requested: bool | None = None
    independent_audit_required: bool | None = None
    overall_risk_level: str | None = None
    conclusion: str | None = None
    conclusion_notes: str | None = None


class RiskAssessmentResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    record_id: uuid.UUID
    assessed_by: uuid.UUID | None
    assessed_at: datetime | None
    country_risk_level: str | None
    country_risk_notes: str | None
    country_benchmarking_source: str | None
    supply_chain_risk_level: str | None
    supply_chain_notes: str | None
    supplier_verification_status: str
    traceability_confidence: str
    regional_risk_level: str | None
    deforestation_prevalence: str | None
    indigenous_rights_risk: bool
    corruption_index_note: str | None
    mitigation_measures: list | None
    additional_info_requested: bool
    independent_audit_required: bool
    overall_risk_level: str | None
    conclusion: str | None
    conclusion_notes: str | None
    status: str
    metadata_: dict
    created_at: datetime
    updated_at: datetime
