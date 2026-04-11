"""Schemas for CompliancePlot."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# Tenure types reconocidos (debe coincidir con la CHECK constraint del modelo)
TenureType = Literal[
    "owned",
    "leased",
    "sharecropped",
    "concession",
    "indigenous_collective",
    "afro_collective",
    "baldio_adjudicado",
    "occupation",
    "other",
]

CaptureMethod = Literal[
    "handheld_gps",
    "rtk_gps",
    "drone",
    "manual_map",
    "cadastral",
    "survey",
    "unknown",
]

ProducerScale = Literal["smallholder", "medium", "industrial"]

# Tipos de identificacion legal de personas/empresas. Cubre Colombia (CC, CE,
# NIT, RUT, PASAPORTE) + cross-LATAM mas comunes (RUC Peru/Ecuador, CURP/RFC
# Mexico, CPF/CNPJ Brasil, CI Bolivia/Paraguay/Uruguay).
IdentifierType = Literal[
    "CC",       # Cedula de ciudadania (Colombia)
    "CE",       # Cedula de extranjeria (Colombia)
    "NIT",      # NIT empresa (Colombia)
    "RUT",      # RUT (Colombia, Chile, Uruguay)
    "PASAPORTE",
    "RUC",      # Peru, Ecuador
    "CURP",     # Mexico
    "RFC",      # Mexico
    "CPF",      # Brasil personas
    "CNPJ",     # Brasil empresas
    "CI",       # Bolivia, Paraguay, Uruguay
    "DNI",      # Peru, Argentina, Espana
    "OTRO",
]


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class _PlotTenureFields(BaseModel):
    """Mixin con los campos de tenencia/propiedad EUDR Art. 8.2.f."""

    # Reject unknown fields so typos like `latitude` instead of `lat`,
    # `area_hectares` instead of `plot_area_ha`, etc. fail loudly with 422
    # instead of silently dropping data and creating half-empty plot rows.
    model_config = ConfigDict(extra="forbid")

    owner_name: str | None = Field(default=None, max_length=200)
    owner_id_type: IdentifierType | None = None
    owner_id_number: str | None = Field(default=None, max_length=50)
    producer_name: str | None = Field(default=None, max_length=200)
    producer_id_type: IdentifierType | None = None
    producer_id_number: str | None = Field(default=None, max_length=50)
    cadastral_id: str | None = Field(default=None, max_length=200)
    tenure_type: TenureType | None = None
    tenure_start_date: date | None = None
    tenure_end_date: date | None = None
    indigenous_territory_flag: bool | None = None
    # Capture metadata (MITECO EFI Tomás — precisión vs exactitud)
    gps_accuracy_m: Decimal | None = None
    capture_method: CaptureMethod | None = None
    capture_device: str | None = Field(default=None, max_length=120)
    capture_date: date | None = None
    # Producer scale (MITECO EFI Alice — legalidad diferencial)
    producer_scale: ProducerScale | None = None

    @model_validator(mode="after")
    def _check_tenure_dates(self) -> "_PlotTenureFields":
        if (
            self.tenure_start_date is not None
            and self.tenure_end_date is not None
            and self.tenure_end_date < self.tenure_start_date
        ):
            raise ValueError(
                "tenure_end_date debe ser >= tenure_start_date"
            )
        # Coherencia: si flag indigenous esta activo, exigir tenure_type
        # consistente. No bloqueamos si esta vacio (puede establecerse despues).
        if self.indigenous_territory_flag and self.tenure_type and self.tenure_type not in (
            "indigenous_collective", "afro_collective", "concession", "other",
        ):
            raise ValueError(
                "tenure_type incompatible con indigenous_territory_flag=true. "
                "Use indigenous_collective, afro_collective, concession u other."
            )
        return self


class PlotCreate(_PlotTenureFields):
    plot_code: str
    organization_id: uuid.UUID | None = None
    plot_area_ha: Decimal | None = None
    geolocation_type: str = "point"
    lat: Decimal | None = None
    lng: Decimal | None = None
    geojson_data: dict | None = None
    geojson_arweave_url: str | None = None
    geojson_hash: str | None = None
    country_code: str = "CO"
    region: str | None = None
    municipality: str | None = None
    land_title_number: str | None = None
    land_title_hash: str | None = None
    deforestation_free: bool = False
    cutoff_date_compliant: bool = False
    legal_land_use: bool = False
    risk_level: str = "standard"
    establishment_date: date | None = None
    crop_type: str | None = None
    renovation_date: date | None = None
    renovation_type: str | None = None
    satellite_report_url: str | None = None
    satellite_report_hash: str | None = None
    metadata: dict | None = None


class PlotUpdate(_PlotTenureFields):
    plot_code: str | None = None
    organization_id: uuid.UUID | None = None
    plot_area_ha: Decimal | None = None
    geolocation_type: str | None = None
    lat: Decimal | None = None
    lng: Decimal | None = None
    geojson_data: dict | None = None
    geojson_arweave_url: str | None = None
    geojson_hash: str | None = None
    country_code: str | None = None
    region: str | None = None
    municipality: str | None = None
    land_title_number: str | None = None
    land_title_hash: str | None = None
    deforestation_free: bool | None = None
    cutoff_date_compliant: bool | None = None
    legal_land_use: bool | None = None
    risk_level: str | None = None
    establishment_date: date | None = None
    crop_type: str | None = None
    renovation_date: date | None = None
    renovation_type: str | None = None
    satellite_report_url: str | None = None
    satellite_report_hash: str | None = None
    metadata: dict | None = None


class PlotResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    organization_id: uuid.UUID | None = None
    plot_code: str
    plot_area_ha: Decimal | None = None
    geolocation_type: str
    lat: Decimal | None = None
    lng: Decimal | None = None
    geojson_data: dict | None = None
    geojson_arweave_url: str | None = None
    geojson_hash: str | None = None
    country_code: str
    region: str | None = None
    municipality: str | None = None
    land_title_number: str | None = None
    land_title_hash: str | None = None
    # Tenencia / propiedad (EUDR Art. 8.2.f)
    owner_name: str | None = None
    owner_id_type: str | None = None
    owner_id_number: str | None = None
    producer_name: str | None = None
    producer_id_type: str | None = None
    producer_id_number: str | None = None
    cadastral_id: str | None = None
    tenure_type: str | None = None
    tenure_start_date: date | None = None
    tenure_end_date: date | None = None
    indigenous_territory_flag: bool = False
    gps_accuracy_m: Decimal | None = None
    capture_method: str | None = None
    capture_device: str | None = None
    capture_date: date | None = None
    producer_scale: str | None = None
    deforestation_free: bool
    cutoff_date_compliant: bool
    legal_land_use: bool
    risk_level: str
    establishment_date: date | None = None
    crop_type: str | None = None
    renovation_date: date | None = None
    renovation_type: str | None = None
    satellite_report_url: str | None = None
    satellite_report_hash: str | None = None
    satellite_verified_at: datetime | None = None
    is_active: bool
    metadata_: dict | None = None
    created_at: datetime
    updated_at: datetime
