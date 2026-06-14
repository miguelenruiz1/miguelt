"""WM material master data (SAP "Gestión de almacenes" views 1 & 2).

Per product × warehouse: removal/putaway strategy, fixed bin, picking storage
type, WM unit of measure, lot/serial/hazmat flags, GS1-128, and palletization
(units per storage unit). Drives putaway proposals and removal planning.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProductWarehouseData(Base):
    __tablename__ = "wm_product_warehouse_data"

    id:                  Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:           Mapped[str]        = mapped_column(String(255), nullable=False)
    product_id:          Mapped[str]        = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id:        Mapped[str]        = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    removal_strategy:    Mapped[str]        = mapped_column(String(15), nullable=False, server_default="fifo")   # fifo|fefo|lifo|fixed_bin
    putaway_strategy:    Mapped[str]        = mapped_column(String(15), nullable=False, server_default="manual")  # manual|fixed_bin|next_empty|by_section
    fixed_bin_id:        Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True
    )
    picking_storage_type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("wm_storage_types.id", ondelete="SET NULL"), nullable=True
    )
    wm_uom:              Mapped[str | None] = mapped_column(String(20), nullable=True)
    lot_managed:         Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    serial_managed:      Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    hazmat:              Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    gs1_enabled:         Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    storage_unit_type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("wm_package_types.id", ondelete="SET NULL"), nullable=True
    )
    units_per_storage_unit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    max_qty_per_bin:     Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    created_at:          Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:          Mapped[DateTime]   = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_wm_product_wh_data"),
        Index("ix_wm_product_wh_data_tenant_id", "tenant_id"),
        Index("ix_wm_product_wh_data_product", "product_id"),
    )
