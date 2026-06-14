"""Warehouse-Management (WM) schemas — storage types, sections, bulk bins."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase

StorageKind = Literal["physical", "logical", "interim"]
PutawayStrategy = Literal["manual", "fixed_bin", "next_empty", "by_section"]
RemovalStrategy = Literal["fifo", "fefo", "lifo", "fixed_bin"]


# ─── Storage Type ─────────────────────────────────────────────────────────────

class StorageTypeCreate(BaseModel):
    warehouse_id: str
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=150)
    kind: StorageKind = "physical"
    putaway_strategy: PutawayStrategy = "manual"
    removal_strategy: RemovalStrategy = "fifo"
    capacity_check: bool = False
    handles_hu: bool = False
    is_active: bool = True
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    model_config = {"populate_by_name": True}


class StorageTypeUpdate(BaseModel):
    code: str | None = Field(None, max_length=20)
    name: str | None = Field(None, max_length=150)
    kind: StorageKind | None = None
    putaway_strategy: PutawayStrategy | None = None
    removal_strategy: RemovalStrategy | None = None
    capacity_check: bool | None = None
    handles_hu: bool | None = None
    is_active: bool | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    model_config = {"populate_by_name": True}


class StorageTypeOut(OrmBase):
    id: str
    tenant_id: str
    warehouse_id: str
    code: str
    name: str
    kind: str
    putaway_strategy: str
    removal_strategy: str
    capacity_check: bool
    handles_hu: bool
    is_active: bool
    # Read from the ORM attribute `metadata_` (column "metadata"); serialize as
    # "metadata". A plain alias would make Pydantic read obj.metadata — the
    # SQLAlchemy MetaData registry — which crashes serialization.
    metadata_: dict[str, Any] | None = Field(default=None, serialization_alias="metadata")


# ─── Storage Section ──────────────────────────────────────────────────────────

class StorageSectionCreate(BaseModel):
    storage_type_id: str
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=150)
    rotation_class: str | None = Field(None, max_length=10)
    is_active: bool = True
    sort_order: int = 0
    description: str | None = None


class StorageSectionUpdate(BaseModel):
    code: str | None = Field(None, max_length=20)
    name: str | None = Field(None, max_length=150)
    rotation_class: str | None = Field(None, max_length=10)
    is_active: bool | None = None
    sort_order: int | None = None
    description: str | None = None


class StorageSectionOut(OrmBase):
    id: str
    tenant_id: str
    storage_type_id: str
    code: str
    name: str
    rotation_class: str | None = None
    is_active: bool
    sort_order: int
    description: str | None = None


# ─── Bulk bin creation (SAP LS10) ─────────────────────────────────────────────

class BinSegment(BaseModel):
    """One numeric segment of a bin code: e.g. aisle 01..10, level 1..5."""
    start: int = Field(..., ge=0)
    end: int = Field(..., ge=0)
    step: int = Field(1, ge=1)
    pad: int = Field(2, ge=1, le=6)   # zero-padding width


class BinBulkCreate(BaseModel):
    """Generate bins by cartesian product of numeric segments.

    Example: separator="-", segments=[{1..2 pad1},{1..10 pad2},{1..4 pad2}]
    → codes 1-01-01 … 2-10-04 (SAP LS10 style mass creation).
    """
    warehouse_id: str
    storage_type_id: str | None = None
    storage_section_id: str | None = None
    location_kind: StorageKind = "physical"
    separator: str = Field("-", max_length=2)
    prefix: str = Field("", max_length=20)
    segments: list[BinSegment] = Field(..., min_length=1, max_length=4)
    # Default physical attributes applied to every generated bin
    height_m: float | None = None
    max_weight_kg: float | None = None
    max_volume_m3: float | None = None
    max_capacity: int | None = None


class BinBulkResult(BaseModel):
    created: int
    skipped: int          # already existed
    sample_codes: list[str]


class EmptyBinReportItem(BaseModel):
    location_id: str
    code: str
    name: str
    storage_type_id: str | None = None
    storage_section_id: str | None = None


class EmptyBinReport(BaseModel):
    warehouse_id: str
    total_bins: int
    empty_bins: int
    occupancy_pct: float
    items: list[EmptyBinReportItem]
