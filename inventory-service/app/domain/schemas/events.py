"""Inventory event schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase


class EventImpactCreate(BaseModel):
    entity_id: str
    quantity_impact: Decimal = Decimal("0")
    batch_id: str | None = None
    serial_id: str | None = None
    notes: str | None = None


class EventCreate(BaseModel):
    event_type_id: str
    severity_id: str
    status_id: str
    warehouse_id: str | None = None
    title: str = Field(..., max_length=255)
    description: str | None = None
    occurred_at: datetime
    reported_by: str | None = None
    metadata: dict[str, Any] = {}
    impacts: list[EventImpactCreate] = []


class EventStatusChange(BaseModel):
    status_id: str
    notes: str | None = None
    changed_by: str | None = None
    resolved_at: datetime | None = None


class EventImpactOut(OrmBase):
    id: str
    event_id: str
    entity_id: str
    quantity_impact: Decimal
    batch_id: str | None
    serial_id: str | None
    movement_id: str | None
    notes: str | None


class EventStatusLogOut(OrmBase):
    id: str
    event_id: str
    from_status_id: str | None
    to_status_id: str
    changed_by: str | None
    notes: str | None
    created_at: datetime


class EventOut(OrmBase):
    id: str
    tenant_id: str
    event_type_id: str
    severity_id: str
    status_id: str
    warehouse_id: str | None
    title: str
    description: str | None
    occurred_at: datetime
    resolved_at: datetime | None
    reported_by: str | None
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime
    impacts: list[EventImpactOut] = []
    status_logs: list[EventStatusLogOut] = []


class PaginatedEvents(BaseModel):
    items: list[EventOut]
    total: int
    offset: int
    limit: int
