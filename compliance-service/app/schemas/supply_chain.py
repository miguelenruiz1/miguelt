"""Schemas for EUDR supply chain nodes (Art. 9.1.e-f)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SupplyChainNodeCreate(BaseModel):
    sequence_order: int
    role: str
    actor_name: str
    actor_address: str | None = None
    actor_country: str | None = None
    actor_tax_id: str | None = None
    actor_eori: str | None = None
    handoff_date: date | None = None
    quantity_kg: Decimal | None = None
    verification_status: str = "unverified"
    notes: str | None = None


class SupplyChainNodeUpdate(BaseModel):
    sequence_order: int | None = None
    role: str | None = None
    actor_name: str | None = None
    actor_address: str | None = None
    actor_country: str | None = None
    actor_tax_id: str | None = None
    actor_eori: str | None = None
    handoff_date: date | None = None
    quantity_kg: Decimal | None = None
    verification_status: str | None = None
    notes: str | None = None


class SupplyChainNodeResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    record_id: uuid.UUID
    sequence_order: int
    role: str
    actor_name: str
    actor_address: str | None
    actor_country: str | None
    actor_tax_id: str | None
    actor_eori: str | None
    handoff_date: date | None
    quantity_kg: Decimal | None
    verification_status: str
    notes: str | None
    metadata_: dict
    created_at: datetime
    updated_at: datetime


class ReorderRequest(BaseModel):
    """Reorder supply chain nodes."""
    order: list[dict]  # [{node_id: uuid, sequence_order: int}]
