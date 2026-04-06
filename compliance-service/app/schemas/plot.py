"""Schemas for CompliancePlot."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PlotCreate(BaseModel):
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


class PlotUpdate(BaseModel):
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
    organization_id: uuid.UUID | None
    plot_code: str
    plot_area_ha: Decimal | None
    geolocation_type: str
    lat: Decimal | None
    lng: Decimal | None
    geojson_data: dict | None = None
    geojson_arweave_url: str | None
    geojson_hash: str | None
    country_code: str
    region: str | None
    municipality: str | None
    land_title_number: str | None
    land_title_hash: str | None
    deforestation_free: bool
    cutoff_date_compliant: bool
    legal_land_use: bool
    risk_level: str
    establishment_date: date | None = None
    crop_type: str | None = None
    renovation_date: date | None = None
    renovation_type: str | None = None
    satellite_report_url: str | None
    satellite_report_hash: str | None
    satellite_verified_at: datetime | None
    is_active: bool
    metadata_: dict | None = None
    created_at: datetime
    updated_at: datetime
