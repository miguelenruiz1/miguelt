"""CompliancePlot — production plots / parcels, reusable across frameworks."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, Index, Integer, Numeric, Text, UniqueConstraint, text
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
        # Sanity ranges — invalid coordinates corrupt downstream geofencing.
        CheckConstraint(
            "lat IS NULL OR (lat BETWEEN -90 AND 90)",
            name="ck_compliance_plots_lat_range",
        ),
        CheckConstraint(
            "lng IS NULL OR (lng BETWEEN -180 AND 180)",
            name="ck_compliance_plots_lng_range",
        ),
        CheckConstraint(
            "plot_area_ha IS NULL OR plot_area_ha > 0",
            name="ck_compliance_plots_area_positive",
        ),
        CheckConstraint(
            "risk_level IN ('low','standard','high','critical')",
            name="ck_compliance_plots_risk_level",
        ),
        CheckConstraint(
            "geolocation_type IN ('point','polygon','multipolygon')",
            name="ck_compliance_plots_geo_type",
        ),
        CheckConstraint(
            "tenure_type IS NULL OR tenure_type IN ("
            "'owned','leased','sharecropped','concession',"
            "'indigenous_collective','afro_collective','baldio_adjudicado',"
            "'occupation','other')",
            name="ck_compliance_plots_tenure_type",
        ),
        CheckConstraint(
            "tenure_start_date IS NULL OR tenure_end_date IS NULL "
            "OR tenure_end_date >= tenure_start_date",
            name="ck_compliance_plots_tenure_dates",
        ),
        CheckConstraint(
            "capture_method IS NULL OR capture_method IN ("
            "'handheld_gps','rtk_gps','drone','manual_map','cadastral','survey','unknown')",
            name="ck_compliance_plots_capture_method",
        ),
        CheckConstraint(
            "producer_scale IS NULL OR producer_scale IN ('smallholder','medium','industrial')",
            name="ck_compliance_plots_producer_scale",
        ),
        CheckConstraint(
            "gps_accuracy_m IS NULL OR gps_accuracy_m >= 0",
            name="ck_compliance_plots_gps_accuracy_positive",
        ),
        Index(
            "ix_plots_cadastral",
            "cadastral_id",
            postgresql_where=text("cadastral_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    plot_code: Mapped[str] = mapped_column(Text, nullable=False)
    plot_area_ha: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    geolocation_type: Mapped[str] = mapped_column(Text, nullable=False, default="point")
    lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    geojson_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Local polygon storage
    geojson_arweave_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    geojson_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_code: Mapped[str] = mapped_column(Text, nullable=False, default="CO")
    region: Mapped[str | None] = mapped_column(Text, nullable=True)  # Departamento en CO
    municipality: Mapped[str | None] = mapped_column(Text, nullable=True)
    vereda: Mapped[str | None] = mapped_column(Text, nullable=True)  # CO: division sub-municipal rural
    # Frontera agricola UPRA — respuesta oficial CO a derechos de uso del suelo
    frontera_agricola_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    land_title_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    land_title_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Tenencia y propiedad (EUDR Art. 8.2.f — derecho legal de uso de la zona)
    owner_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    producer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    producer_id_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    producer_id_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    cadastral_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenure_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenure_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    tenure_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    indigenous_territory_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Capture metadata (MITECO EFI Tomas — precision vs accuracy, SOP trace)
    gps_accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    capture_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    capture_device: Mapped[str | None] = mapped_column(Text, nullable=True)
    capture_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Producer scale — differentiates legal requirements (MITECO EFI Alice)
    producer_scale: Mapped[str | None] = mapped_column(Text, nullable=True)
    deforestation_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    degradation_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # Art. 2(7) — distinct from deforestation
    cutoff_date_compliant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    legal_land_use: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_level: Mapped[str] = mapped_column(Text, nullable=False, default="standard")
    # Crop & production (EUDR Art. 9(1)(a)(d))
    crop_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    scientific_name: Mapped[str | None] = mapped_column(Text, nullable=True)  # Art. 9(1)(a) — e.g. Coffea arabica
    establishment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    renovation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    renovation_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_harvest_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # Art. 9(1)(d) — fecha/rango produccion
    satellite_report_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    satellite_report_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    satellite_verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
