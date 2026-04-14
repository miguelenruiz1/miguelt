"""Schemas for batch quality tests and batch plot origins."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase


QualityTestType = Literal[
    "humidity",
    "defects",
    "cadmium",
    "ffa",
    "iv",
    "dobi",
    "miu",
    "lovibond",
    "sensory_score",
    "other",
]


class QualityTestCreate(BaseModel):
    batch_id: str
    test_type: QualityTestType
    value: Decimal
    unit: str = Field(..., max_length=20)
    threshold_min: Decimal | None = None
    threshold_max: Decimal | None = None
    lab: str | None = Field(default=None, max_length=255)
    test_date: date
    doc_hash: str | None = Field(default=None, max_length=64)
    notes: str | None = None


class QualityTestOut(OrmBase):
    id: str
    tenant_id: str
    batch_id: str
    test_type: str
    value: Decimal
    unit: str
    threshold_min: Decimal | None = None
    threshold_max: Decimal | None = None
    passed: bool | None = None
    lab: str | None = None
    test_date: date
    doc_hash: str | None = None
    notes: str | None = None
    created_at: datetime


class BatchPlotOriginCreate(BaseModel):
    plot_id: str = Field(..., max_length=36)
    plot_code: str | None = Field(default=None, max_length=64)
    origin_quantity_kg: Decimal


class BatchPlotOriginOut(OrmBase):
    id: str
    tenant_id: str
    batch_id: str
    plot_id: str
    plot_code: str | None = None
    origin_quantity_kg: Decimal
    created_at: datetime
