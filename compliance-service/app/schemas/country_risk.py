"""Schemas for country risk benchmarks."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RiskLevel = Literal["negligible", "low", "standard", "high", "critical"]
DeforestationPrevalence = Literal[
    "very_low", "low", "medium", "high", "very_high"
]


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CountryRiskBenchmarkResponse(OrmBase):
    id: uuid.UUID
    country_code: str
    risk_level: RiskLevel
    cpi_score: int | None = None
    cpi_rank: int | None = None
    conflict_flag: bool
    deforestation_prevalence: DeforestationPrevalence | None = None
    indigenous_risk_flag: bool
    notes: str | None = None
    source: str
    as_of_date: date
    is_current: bool
    created_at: datetime


class CountryRiskBenchmarkUpdate(BaseModel):
    risk_level: RiskLevel
    cpi_score: int | None = Field(default=None, ge=0, le=100)
    cpi_rank: int | None = None
    conflict_flag: bool = False
    deforestation_prevalence: DeforestationPrevalence | None = None
    indigenous_risk_flag: bool = False
    notes: str | None = None
    source: str
    as_of_date: date
