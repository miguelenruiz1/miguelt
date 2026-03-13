"""Warehouse and WarehouseLocation models."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import WarehouseType
from sqlalchemy import Enum

if TYPE_CHECKING:
    from app.db.models.config import DynamicWarehouseType
    from app.db.models.stock import StockLevel


class Warehouse(Base):
    __tablename__ = "warehouses"

    id:                 Mapped[str]           = mapped_column(String(36), primary_key=True)
    tenant_id:          Mapped[str]           = mapped_column(String(255), nullable=False)
    name:               Mapped[str]           = mapped_column(String(150), nullable=False)
    code:               Mapped[str]           = mapped_column(String(50), nullable=False)
    type:               Mapped[WarehouseType] = mapped_column(
        Enum(WarehouseType, native_enum=False), nullable=False, server_default="main"
    )
    warehouse_type_id:  Mapped[str | None]    = mapped_column(
        String(36), ForeignKey("warehouse_types.id", ondelete="SET NULL"), nullable=True
    )
    address:            Mapped[dict | None]   = mapped_column(JSONB, nullable=True)
    is_active:          Mapped[bool]          = mapped_column(Boolean, nullable=False, server_default="true")
    is_default:         Mapped[bool]          = mapped_column(Boolean, nullable=False, server_default="false")
    cost_per_sqm:       Mapped[float | None]  = mapped_column(Numeric(12, 2), nullable=True)
    total_area_sqm:     Mapped[float | None]  = mapped_column(Numeric(12, 2), nullable=True)
    max_stock_capacity: Mapped[int | None]    = mapped_column(Integer, nullable=True)
    created_by:         Mapped[str | None]    = mapped_column(String(255), nullable=True)
    updated_by:         Mapped[str | None]    = mapped_column(String(255), nullable=True)
    created_at:         Mapped[DateTime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:         Mapped[DateTime]      = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    dynamic_warehouse_type: Mapped[DynamicWarehouseType | None] = relationship(
        "DynamicWarehouseType", back_populates="warehouses"
    )
    stock_levels: Mapped[list[StockLevel]] = relationship("StockLevel", back_populates="warehouse")
    locations:    Mapped[list[WarehouseLocation]] = relationship(
        "WarehouseLocation", back_populates="warehouse"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_warehouse_tenant_code"),
        Index("ix_warehouses_tenant_id", "tenant_id"),
        Index("ix_warehouses_warehouse_type_id", "warehouse_type_id"),
    )


class WarehouseLocation(Base):
    __tablename__ = "warehouse_locations"

    id:                 Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:          Mapped[str]        = mapped_column(String(255), nullable=False)
    warehouse_id:       Mapped[str]        = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    parent_location_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True
    )
    name:               Mapped[str]        = mapped_column(String(150), nullable=False)
    code:               Mapped[str]        = mapped_column(String(50), nullable=False)
    description:        Mapped[str | None] = mapped_column(Text, nullable=True)
    location_type:      Mapped[str]        = mapped_column(
        String(20), nullable=False, server_default="bin"
    )
    is_active:          Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    sort_order:         Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    created_by:         Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by:         Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:         Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:         Mapped[DateTime]   = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    warehouse: Mapped[Warehouse] = relationship("Warehouse", back_populates="locations")
    parent:    Mapped[WarehouseLocation | None] = relationship(
        "WarehouseLocation", remote_side="WarehouseLocation.id"
    )

    __table_args__ = (
        UniqueConstraint("warehouse_id", "code", name="uq_location_warehouse_code"),
        Index("ix_warehouse_locations_tenant_id", "tenant_id"),
        Index("ix_warehouse_locations_warehouse_id", "warehouse_id"),
    )
