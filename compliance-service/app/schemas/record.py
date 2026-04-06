"""Schemas for ComplianceRecord and CompliancePlotLink."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RecordCreate(BaseModel):
    asset_id: uuid.UUID | None = None
    framework_slug: str
    hs_code: str | None = None
    commodity_type: str | None = None
    product_description: str | None = None
    scientific_name: str | None = None
    quantity_kg: Decimal | None = None
    quantity_unit: str | None = None
    country_of_production: str | None = None
    production_period_start: date | None = None
    production_period_end: date | None = None
    supplier_name: str | None = None
    supplier_address: str | None = None
    supplier_email: str | None = None
    buyer_name: str | None = None
    buyer_address: str | None = None
    buyer_email: str | None = None
    operator_eori: str | None = None
    activity_type: str = "export"
    deforestation_free_declaration: bool = False
    legal_compliance_declaration: bool = False
    signatory_name: str | None = None
    signatory_role: str | None = None
    signatory_date: date | None = None
    prior_dds_references: list[str] | None = None
    metadata: dict | None = None


class RecordUpdate(BaseModel):
    hs_code: str | None = None
    commodity_type: str | None = None
    product_description: str | None = None
    scientific_name: str | None = None
    quantity_kg: Decimal | None = None
    quantity_unit: str | None = None
    country_of_production: str | None = None
    production_period_start: date | None = None
    production_period_end: date | None = None
    supplier_name: str | None = None
    supplier_address: str | None = None
    supplier_email: str | None = None
    buyer_name: str | None = None
    buyer_address: str | None = None
    buyer_email: str | None = None
    operator_eori: str | None = None
    activity_type: str | None = None
    deforestation_free_declaration: bool | None = None
    legal_compliance_declaration: bool | None = None
    signatory_name: str | None = None
    signatory_role: str | None = None
    signatory_date: date | None = None
    prior_dds_references: list[str] | None = None
    metadata: dict | None = None


class RecordResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    asset_id: uuid.UUID | None = None
    framework_id: uuid.UUID
    framework_slug: str
    hs_code: str | None
    commodity_type: str | None
    product_description: str | None
    scientific_name: str | None
    quantity_kg: Decimal | None
    quantity_unit: str
    country_of_production: str | None
    production_period_start: date | None
    production_period_end: date | None
    supplier_name: str | None
    supplier_address: str | None
    supplier_email: str | None
    buyer_name: str | None
    buyer_address: str | None
    buyer_email: str | None
    operator_eori: str | None
    activity_type: str = "export"
    deforestation_free_declaration: bool
    legal_compliance_declaration: bool
    legal_cert_hash: str | None
    deforestation_evidence_hash: str | None
    declaration_reference: str | None
    declaration_submission_date: date | None
    declaration_status: str
    declaration_url: str | None
    signatory_name: str | None = None
    signatory_role: str | None = None
    signatory_date: date | None = None
    prior_dds_references: list | None = None
    compliance_status: str
    last_validated_at: datetime | None
    validation_result: dict | None
    missing_fields: list | None
    documents_retention_until: date | None
    metadata_: dict | None = None
    created_at: datetime
    updated_at: datetime


class PlotLinkCreate(BaseModel):
    plot_id: uuid.UUID
    quantity_from_plot_kg: Decimal | None = None
    percentage_from_plot: Decimal | None = None


class PlotLinkResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    record_id: uuid.UUID
    plot_id: uuid.UUID
    quantity_from_plot_kg: Decimal | None
    percentage_from_plot: Decimal | None
