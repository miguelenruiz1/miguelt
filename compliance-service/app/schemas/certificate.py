"""Schemas for ComplianceCertificate."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CertificateResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    record_id: uuid.UUID
    certificate_number: str
    framework_slug: str
    asset_id: uuid.UUID
    status: str
    pdf_url: str | None
    pdf_hash: str | None
    pdf_size_bytes: int | None
    verify_url: str
    qr_code_url: str | None
    valid_from: date
    valid_until: date
    generated_at: datetime | None
    generated_by: uuid.UUID | None
    generation_error: str | None
    solana_cnft_address: str | None
    solana_tx_sig: str | None
    metadata: dict = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata", "metadata_"),
    )
    created_at: datetime
    updated_at: datetime


class CertificateListResponse(BaseModel):
    items: list[CertificateResponse]
    total: int


class RevokeRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class VerifyResponse(BaseModel):
    valid: bool
    status: str
    certificate_number: str
    framework: str | None = None
    commodity_type: str | None = None
    quantity_kg: float | None = None
    country_of_production: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    deforestation_free: bool | None = None
    legal_compliance: bool | None = None
    plots_count: int | None = None
    blockchain: dict | None = None
    pdf_url: str | None = None
    generated_at: datetime | None = None
    message: str | None = None
