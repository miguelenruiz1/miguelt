"""WM putaway rules, package types and handling units.

- ``PutawayRule`` (SAP storage-type search / Odoo putaway): steer a product (or
  its category) to a storage type + section.
- ``PackageType`` (Odoo) / storage-unit type (SAP): pallet/box master with
  weight & dimensions.
- ``HandlingUnit`` (SAP HU): a physically-moved unit (pallet/box) grouping stock.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PutawayRule(Base):
    __tablename__ = "wm_putaway_rules"

    id:                  Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:           Mapped[str]        = mapped_column(String(255), nullable=False)
    warehouse_id:        Mapped[str]        = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    # Match on a specific product OR a category OR a commodity_type (any may be null).
    match_product_id:    Mapped[str | None] = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=True
    )
    match_category_id:   Mapped[str | None] = mapped_column(
        String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=True
    )
    match_commodity:     Mapped[str | None] = mapped_column(String(20), nullable=True)
    dest_storage_type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("wm_storage_types.id", ondelete="SET NULL"), nullable=True
    )
    dest_storage_section_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("wm_storage_sections.id", ondelete="SET NULL"), nullable=True
    )
    priority:            Mapped[int]        = mapped_column(Integer, nullable=False, server_default="100")
    is_active:           Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    created_at:          Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_wm_putaway_rules_tenant_id", "tenant_id"),
        Index("ix_wm_putaway_rules_wh", "warehouse_id"),
        Index("ix_wm_putaway_rules_product", "match_product_id"),
    )


class PackageType(Base):
    __tablename__ = "wm_package_types"

    id:           Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:    Mapped[str]            = mapped_column(String(255), nullable=False)
    code:         Mapped[str]            = mapped_column(String(30), nullable=False)
    name:         Mapped[str]            = mapped_column(String(150), nullable=False)
    max_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    length_cm:    Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    width_cm:     Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    height_cm:    Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    is_active:    Mapped[bool]           = mapped_column(Boolean, nullable=False, server_default="true")
    created_at:   Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_wm_package_types_tenant_id", "tenant_id"),
    )


class HandlingUnit(Base):
    __tablename__ = "wm_handling_units"

    id:              Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:       Mapped[str]        = mapped_column(String(255), nullable=False)
    hu_number:       Mapped[str]        = mapped_column(String(40), nullable=False)
    package_type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("wm_package_types.id", ondelete="SET NULL"), nullable=True
    )
    warehouse_id:    Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True
    )
    location_id:     Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True
    )
    status:          Mapped[str]        = mapped_column(String(15), nullable=False, server_default="open")  # open|closed|shipped
    gross_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    created_at:      Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_wm_handling_units_tenant_id", "tenant_id"),
        Index("ix_wm_handling_units_hu_number", "tenant_id", "hu_number"),
    )
