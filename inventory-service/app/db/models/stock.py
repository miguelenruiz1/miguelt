"""StockLevel, StockMovement and StockReservation models."""
from __future__ import annotations

import uuid as _uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import MovementType
from sqlalchemy import Enum, Integer

if TYPE_CHECKING:
    from app.db.models.config import DynamicMovementType
    from app.db.models.entity import Product
    from app.db.models.events import InventoryEvent
    from app.db.models.variant import ProductVariant
    from app.db.models.warehouse import Warehouse, WarehouseLocation
    from app.db.models.tracking import EntityBatch
    from app.db.models.sales_order import SalesOrder, SalesOrderLine


class StockLevel(Base):
    __tablename__ = "stock_levels"

    id:            Mapped[str]     = mapped_column(String(36), primary_key=True)
    tenant_id:     Mapped[str]     = mapped_column(String(255), nullable=False)
    product_id:    Mapped[str]     = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id:  Mapped[str]     = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    location_id:   Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True
    )
    batch_id:      Mapped[str | None] = mapped_column(
        String(36), ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True
    )
    variant_id:    Mapped[str | None] = mapped_column(
        String(36), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    qty_on_hand:   Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default="0")
    qty_reserved:  Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default="0")
    qty_in_transit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default="0")
    reorder_point: Mapped[int]     = mapped_column(Integer, nullable=False, server_default="0")
    max_stock:         Mapped[int]     = mapped_column(Integer, nullable=False, server_default="-1")
    qc_status:         Mapped[str]     = mapped_column(String(20), nullable=False, server_default="approved")
    weighted_avg_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    last_count_at:     Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:    Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at:    Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    product:   Mapped[Product]   = relationship("Product", back_populates="stock_levels")
    warehouse: Mapped[Warehouse] = relationship("Warehouse", back_populates="stock_levels")
    location:  Mapped[WarehouseLocation | None] = relationship("WarehouseLocation")
    batch:     Mapped[EntityBatch | None] = relationship("EntityBatch")
    variant:   Mapped[ProductVariant | None] = relationship("ProductVariant")

    __table_args__ = (
        # Unique constraint on (product_id, warehouse_id, batch_id, variant_id) is managed
        # by index uq_stock_product_warehouse_batch_variant in migration 019 using
        # COALESCE to handle NULLs.
        Index("ix_stock_levels_tenant_id", "tenant_id"),
        Index("ix_stock_levels_tenant_product_wh", "tenant_id", "product_id", "warehouse_id"),
        Index("ix_stock_level_traceability", "tenant_id", "batch_id", "variant_id"),
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id:                Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:         Mapped[str]            = mapped_column(String(255), nullable=False)
    movement_type:     Mapped[MovementType]   = mapped_column(
        Enum(MovementType, native_enum=False), nullable=False
    )
    movement_type_id:  Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("movement_types.id", ondelete="SET NULL"), nullable=True
    )
    product_id:        Mapped[str]            = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    from_warehouse_id: Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True
    )
    to_warehouse_id:   Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True
    )
    quantity:          Mapped[Decimal]        = mapped_column(Numeric(18, 4), nullable=False)
    original_qty:      Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    uom:               Mapped[str]            = mapped_column(String(20), nullable=False, server_default="primary")
    unit_cost:         Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    reference:         Mapped[str | None]     = mapped_column(String(255), nullable=True)
    notes:             Mapped[str | None]     = mapped_column(Text, nullable=True)
    variant_id:        Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    batch_id:          Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    batch_number:      Mapped[str | None]     = mapped_column(String(100), nullable=True)
    performed_by:      Mapped[str | None]     = mapped_column(String(255), nullable=True)
    event_id:          Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("inventory_events.id", ondelete="SET NULL"), nullable=True
    )
    cost_total:        Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    layer_consumed_ids: Mapped[list | None]   = mapped_column(JSONB, nullable=True)
    status:            Mapped[str]            = mapped_column(String(20), nullable=False, server_default="completed")
    completed_at:      Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at:        Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    product:                Mapped[Product]          = relationship("Product", back_populates="movements")
    dynamic_movement_type:  Mapped[DynamicMovementType | None] = relationship(
        "DynamicMovementType", back_populates="movements"
    )
    from_warehouse: Mapped[Warehouse | None] = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse:   Mapped[Warehouse | None] = relationship("Warehouse", foreign_keys=[to_warehouse_id])
    batch:          Mapped[EntityBatch | None] = relationship("EntityBatch", lazy="noload")
    event:          Mapped[InventoryEvent | None] = relationship("InventoryEvent", foreign_keys=[event_id])

    __table_args__ = (
        Index("ix_stock_movements_tenant_id", "tenant_id"),
        Index("ix_stock_movements_product_id", "product_id"),
        Index("ix_stock_movements_type", "movement_type"),
        Index("ix_stock_movements_created_at", "created_at"),
        Index("ix_stock_movements_from_warehouse", "from_warehouse_id"),
        Index("ix_stock_movements_to_warehouse", "to_warehouse_id"),
        Index("ix_stock_movements_tenant_product_created", "tenant_id", "product_id", "created_at"),
        Index("ix_stock_movements_tenant_type_created", "tenant_id", "movement_type", "created_at"),
    )


class StockReservation(Base):
    """Traceability record for stock reservations tied to Sales Orders."""
    __tablename__ = "stock_reservations"

    id:                   Mapped[str]            = mapped_column(String(36), primary_key=True, default=lambda: str(_uuid.uuid4()))
    tenant_id:            Mapped[str]            = mapped_column(String(255), nullable=False)
    sales_order_id:       Mapped[str]            = mapped_column(
        String(36), ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False
    )
    sales_order_line_id:  Mapped[str]            = mapped_column(
        String(36), ForeignKey("sales_order_lines.id", ondelete="CASCADE"), nullable=False
    )
    product_id:           Mapped[str]            = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    variant_id:           Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    warehouse_id:         Mapped[str]            = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    quantity:             Mapped[Decimal]        = mapped_column(Numeric(18, 4), nullable=False)
    status:               Mapped[str]            = mapped_column(String(20), nullable=False, server_default="active")
    reserved_at:          Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    released_at:          Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_reason:      Mapped[str | None]     = mapped_column(String(50), nullable=True)

    # Relationships
    product:              Mapped[Product]          = relationship("Product")
    warehouse:            Mapped[Warehouse]        = relationship("Warehouse")
    sales_order:          Mapped[SalesOrder]       = relationship("SalesOrder")
    sales_order_line:     Mapped[SalesOrderLine]   = relationship("SalesOrderLine")

    __table_args__ = (
        Index("ix_reservation_so", "sales_order_id"),
        Index("ix_reservation_product_wh", "product_id", "warehouse_id"),
        Index("ix_reservation_tenant_status", "tenant_id", "status"),
    )
