"""Warehouse-Management (WM) foundation models.

Adopts the shared Odoo/SAP-WM model: a warehouse is subdivided into
**storage types** (rack, bulk/block, picking, interim/logical) and, within a
type, **storage sections** (a business grouping such as fast/slow rotation,
refrigerated, hazardous). Bins (`WarehouseLocation`) point to a storage type
and section so putaway/removal strategies can reason about them.

Everything here is opt-in: a warehouse with a single default location keeps
working without ever creating a storage type.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    pass


class StorageType(Base):
    """SAP *tipo de almacén* / Odoo location-type — how stock is held.

    e.g. ``rack`` (pallet racking), ``block`` (floor block), ``picking``
    (small-bin pick face), ``interim`` (logical receiving/issue/QA/production
    zones, SAP 9xx). Carries the default putaway/removal strategy for its bins.
    """
    __tablename__ = "wm_storage_types"

    id:           Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:    Mapped[str]        = mapped_column(String(255), nullable=False)
    warehouse_id: Mapped[str]        = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    code:         Mapped[str]        = mapped_column(String(20), nullable=False)   # e.g. "001"
    name:         Mapped[str]        = mapped_column(String(150), nullable=False)
    kind:         Mapped[str]        = mapped_column(String(20), nullable=False, server_default="physical")  # physical|logical|interim
    # Default strategies applied to bins of this type (overridable per material).
    putaway_strategy:  Mapped[str]   = mapped_column(String(30), nullable=False, server_default="manual")   # manual|fixed_bin|next_empty|by_section
    removal_strategy:  Mapped[str]   = mapped_column(String(30), nullable=False, server_default="fifo")      # fifo|fefo|lifo|fixed_bin
    capacity_check:    Mapped[bool]  = mapped_column(Boolean, nullable=False, server_default="false")
    handles_hu:        Mapped[bool]  = mapped_column(Boolean, nullable=False, server_default="false")        # manages handling units / pallets
    is_active:    Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    metadata_:    Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_by:   Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by:   Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:   Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:   Mapped[DateTime]   = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("warehouse_id", "code", name="uq_wm_storage_type_wh_code"),
        Index("ix_wm_storage_types_tenant_id", "tenant_id"),
        Index("ix_wm_storage_types_warehouse_id", "warehouse_id"),
    )


class StorageSection(Base):
    """SAP *área de almacenamiento* — a business grouping within a storage type.

    e.g. fast-rotation, slow-rotation, refrigerated, hazardous. Used by putaway
    to steer a product to the right zone.
    """
    __tablename__ = "wm_storage_sections"

    id:              Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:       Mapped[str]        = mapped_column(String(255), nullable=False)
    storage_type_id: Mapped[str]        = mapped_column(
        String(36), ForeignKey("wm_storage_types.id", ondelete="CASCADE"), nullable=False
    )
    code:            Mapped[str]        = mapped_column(String(20), nullable=False)   # e.g. "001"
    name:            Mapped[str]        = mapped_column(String(150), nullable=False)
    rotation_class:  Mapped[str | None] = mapped_column(String(10), nullable=True)    # A|B|C / fast|slow
    is_active:       Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    sort_order:      Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    description:     Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at:      Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:      Mapped[DateTime]   = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("storage_type_id", "code", name="uq_wm_storage_section_type_code"),
        Index("ix_wm_storage_sections_tenant_id", "tenant_id"),
        Index("ix_wm_storage_sections_storage_type_id", "storage_type_id"),
    )
