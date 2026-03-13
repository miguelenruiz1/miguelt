"""Cycle count models: sessions, item lines, and IRA snapshots."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime, Enum, ForeignKey, Index, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import CycleCountStatus, CycleCountMethodology

if TYPE_CHECKING:
    from app.db.models.entity import Product
    from app.db.models.warehouse import Warehouse, WarehouseLocation
    from app.db.models.tracking import EntityBatch
    from app.db.models.stock import StockMovement


class CycleCount(Base):
    __tablename__ = "cycle_counts"

    id:             Mapped[str]                    = mapped_column(String(36), primary_key=True)
    tenant_id:      Mapped[str]                    = mapped_column(String(255), nullable=False)
    count_number:   Mapped[str]                    = mapped_column(String(20), nullable=False)
    warehouse_id:   Mapped[str]                    = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    status:         Mapped[CycleCountStatus]       = mapped_column(
        Enum(CycleCountStatus, native_enum=False), nullable=False,
        server_default=CycleCountStatus.draft.value,
    )
    scheduled_date: Mapped[datetime | None]        = mapped_column(DateTime(timezone=True), nullable=True)
    started_at:     Mapped[datetime | None]        = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at:   Mapped[datetime | None]        = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at:    Mapped[datetime | None]        = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by:    Mapped[str | None]             = mapped_column(String(255), nullable=True)
    methodology:    Mapped[CycleCountMethodology | None] = mapped_column(
        Enum(CycleCountMethodology, native_enum=False), nullable=True,
    )
    assigned_counters: Mapped[int]                 = mapped_column(nullable=False, server_default="1")
    minutes_per_count: Mapped[int]                 = mapped_column(nullable=False, server_default="2")
    created_by:     Mapped[str | None]             = mapped_column(String(255), nullable=True)
    updated_by:     Mapped[str | None]             = mapped_column(String(255), nullable=True)
    notes:          Mapped[str | None]             = mapped_column(Text, nullable=True)
    created_at:     Mapped[datetime]               = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    warehouse: Mapped[Warehouse] = relationship("Warehouse")
    items:     Mapped[list[CycleCountItem]] = relationship(
        "CycleCountItem", back_populates="cycle_count", cascade="all, delete-orphan",
        order_by="CycleCountItem.created_at",
    )
    ira_snapshot: Mapped[IRASnapshot | None] = relationship(
        "IRASnapshot", back_populates="cycle_count", uselist=False,
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "count_number", name="uq_cycle_count_number"),
        Index("ix_cycle_counts_tenant_id", "tenant_id"),
        Index("ix_cycle_counts_status", "status"),
        Index("ix_cycle_counts_warehouse_id", "warehouse_id"),
    )


class CycleCountItem(Base):
    __tablename__ = "cycle_count_items"

    id:             Mapped[str]              = mapped_column(String(36), primary_key=True)
    tenant_id:      Mapped[str]              = mapped_column(String(255), nullable=False)
    cycle_count_id: Mapped[str]              = mapped_column(
        String(36), ForeignKey("cycle_counts.id", ondelete="CASCADE"), nullable=False
    )
    product_id:     Mapped[str]              = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    location_id:    Mapped[str | None]       = mapped_column(
        String(36), ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True
    )
    batch_id:       Mapped[str | None]       = mapped_column(
        String(36), ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True
    )
    system_qty:     Mapped[Decimal]          = mapped_column(Numeric(12, 4), nullable=False, server_default="0")
    counted_qty:    Mapped[Decimal | None]   = mapped_column(Numeric(12, 4), nullable=True)
    discrepancy:    Mapped[Decimal | None]   = mapped_column(Numeric(12, 4), nullable=True)
    recount_qty:    Mapped[Decimal | None]   = mapped_column(Numeric(12, 4), nullable=True)
    recount_discrepancy: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    root_cause:     Mapped[str | None]       = mapped_column(String(500), nullable=True)
    counted_by:     Mapped[str | None]       = mapped_column(String(255), nullable=True)
    counted_at:     Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    notes:          Mapped[str | None]       = mapped_column(Text, nullable=True)
    movement_id:    Mapped[str | None]       = mapped_column(
        String(36), ForeignKey("stock_movements.id", ondelete="SET NULL"), nullable=True
    )
    created_at:     Mapped[datetime]         = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    cycle_count: Mapped[CycleCount]              = relationship("CycleCount", back_populates="items")
    product:     Mapped[Product]                  = relationship("Product")
    location:    Mapped[WarehouseLocation | None] = relationship("WarehouseLocation")
    batch:       Mapped[EntityBatch | None]       = relationship("EntityBatch")
    movement:    Mapped[StockMovement | None]     = relationship("StockMovement")

    __table_args__ = (
        Index("ix_cycle_count_items_tenant_id", "tenant_id"),
        Index("ix_cycle_count_items_cycle_count_id", "cycle_count_id"),
        Index("ix_cycle_count_items_product_id", "product_id"),
    )


class IRASnapshot(Base):
    __tablename__ = "ira_snapshots"

    id:                Mapped[str]              = mapped_column(String(36), primary_key=True)
    tenant_id:         Mapped[str]              = mapped_column(String(255), nullable=False)
    cycle_count_id:    Mapped[str]              = mapped_column(
        String(36), ForeignKey("cycle_counts.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id:      Mapped[str | None]       = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True
    )
    total_items:       Mapped[int]              = mapped_column(nullable=False, server_default="0")
    accurate_items:    Mapped[int]              = mapped_column(nullable=False, server_default="0")
    ira_percentage:    Mapped[Decimal]          = mapped_column(Numeric(6, 2), nullable=False, server_default="0")
    total_system_value:  Mapped[Decimal]        = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    total_counted_value: Mapped[Decimal]        = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    value_accuracy:    Mapped[Decimal]          = mapped_column(Numeric(6, 2), nullable=False, server_default="0")
    snapshot_date:     Mapped[datetime]         = mapped_column(DateTime(timezone=True), nullable=False)
    created_at:        Mapped[datetime]         = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    cycle_count: Mapped[CycleCount] = relationship("CycleCount", back_populates="ira_snapshot")

    __table_args__ = (
        UniqueConstraint("cycle_count_id", name="uq_ira_snapshot_cycle_count"),
        Index("ix_ira_snapshots_tenant_id", "tenant_id"),
        Index("ix_ira_snapshots_warehouse_id", "warehouse_id"),
    )
