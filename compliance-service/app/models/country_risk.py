"""Country risk benchmark model.

Static per-country risk data used by the RiskDecisionTree service to adjust
the final risk label. Sourced from public indices (TI CPI, GFW, ACLED).
A single row per (country_code, as_of_date). Only the row with
is_current=true is used for live decisions.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Date, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class CountryRiskBenchmark(Base):
    __tablename__ = "country_risk_benchmarks"
    __table_args__ = (
        UniqueConstraint("country_code", "as_of_date", name="uq_country_risk_current"),
        CheckConstraint(
            "risk_level IN ('negligible','low','standard','high','critical')",
            name="ck_country_risk_level",
        ),
        CheckConstraint(
            "cpi_score IS NULL OR (cpi_score BETWEEN 0 AND 100)",
            name="ck_country_risk_cpi_range",
        ),
        CheckConstraint(
            "deforestation_prevalence IS NULL OR deforestation_prevalence IN "
            "('very_low','low','medium','high','very_high')",
            name="ck_country_risk_def_prevalence",
        ),
        Index("ix_country_risk_country", "country_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(Text, nullable=False)
    cpi_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpi_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conflict_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deforestation_prevalence: Mapped[str | None] = mapped_column(Text, nullable=True)
    indigenous_risk_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )
