"""CompliancePlot — production plots / parcels, reusable across frameworks."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, Index, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class CompliancePlot(Base):
    __tablename__ = "compliance_plots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "plot_code", name="uq_plot_tenant_code"),
        Index("ix_plots_tenant", "tenant_id"),
        Index("ix_plots_org", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    plot_code: Mapped[str] = mapped_column(Text, nullable=False)
    plot_area_ha: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    geolocation_type: Mapped[str] = mapped_column(Text, nullable=False, default="point")
    lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    geojson_arweave_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    geojson_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_code: Mapped[str] = mapped_column(Text, nullable=False, default="CO")
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    municipality: Mapped[str | None] = mapped_column(Text, nullable=True)
    land_title_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    land_title_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    deforestation_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cutoff_date_compliant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    legal_land_use: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_level: Mapped[str] = mapped_column(Text, nullable=False, default="standard")
    # Crop establishment & renovation (EUDR Colombia gap)
    establishment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    crop_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    renovation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    renovation_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    satellite_report_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    satellite_report_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    satellite_verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
