"""Configuration models: ProductType, OrderType, CustomFields, etc."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.entity import Product
    from app.db.models.purchase_order import PurchaseOrder
    from app.db.models.supplier import Supplier
    from app.db.models.category import Category
    from app.db.models.warehouse import Warehouse
    from app.db.models.stock import StockMovement


# ─── ProductType ─────────────────────────────────────────────────────────────

class ProductType(Base):
    __tablename__ = "product_types"

    id:              Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:       Mapped[str]        = mapped_column(String(255), nullable=False)
    name:            Mapped[str]        = mapped_column(String(150), nullable=False)
    slug:            Mapped[str]        = mapped_column(String(150), nullable=False)
    description:     Mapped[str | None] = mapped_column(Text, nullable=True)
    color:           Mapped[str | None] = mapped_column(String(20), nullable=True, server_default="#6366f1")
    is_active:       Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    tracks_serials:  Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    tracks_batches:  Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    requires_qc:     Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    entry_rule_location_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True
    )
    dispatch_rule:   Mapped[str]        = mapped_column(String(10), nullable=False, server_default="fifo")
    rotation_target_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by:      Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by:      Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:      Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:      Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    default_category_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    products: Mapped[list[Product]] = relationship("Product", back_populates="product_type")
    default_category: Mapped[Category | None] = relationship("Category", foreign_keys=[default_category_id])

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_product_type_tenant_slug"),
        Index("ix_product_types_tenant_id", "tenant_id"),
    )


# ─── OrderType ───────────────────────────────────────────────────────────────

class OrderType(Base):
    __tablename__ = "order_types"

    id:          Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:   Mapped[str]        = mapped_column(String(255), nullable=False)
    name:        Mapped[str]        = mapped_column(String(150), nullable=False)
    slug:        Mapped[str]        = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color:       Mapped[str | None] = mapped_column(String(20), nullable=True, server_default="#10b981")
    is_active:   Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    created_by:  Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by:  Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:  Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:  Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    purchase_orders: Mapped[list[PurchaseOrder]] = relationship("PurchaseOrder", back_populates="order_type")

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_order_type_tenant_slug"),
        Index("ix_order_types_tenant_id", "tenant_id"),
    )


# ─── DynamicMovementType ────────────────────────────────────────────────────

class DynamicMovementType(Base):
    __tablename__ = "movement_types"

    id:                Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:         Mapped[str]        = mapped_column(String(255), nullable=False)
    name:              Mapped[str]        = mapped_column(String(150), nullable=False)
    slug:              Mapped[str]        = mapped_column(String(150), nullable=False)
    description:       Mapped[str | None] = mapped_column(Text, nullable=True)
    direction:         Mapped[str]        = mapped_column(String(20), nullable=False, server_default="in")
    affects_cost:      Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    requires_reference: Mapped[bool]      = mapped_column(Boolean, nullable=False, server_default="false")
    color:             Mapped[str | None] = mapped_column(String(20), nullable=True, server_default="#3b82f6")
    is_active:         Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    is_system:         Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    sort_order:        Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    created_by:        Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by:        Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:        Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:        Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    movements: Mapped[list[StockMovement]] = relationship("StockMovement", back_populates="dynamic_movement_type")
    custom_fields: Mapped[list[CustomMovementField]] = relationship(
        "CustomMovementField", cascade="all, delete-orphan",
        primaryjoin="DynamicMovementType.id == foreign(CustomMovementField.movement_type_id)",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_movement_type_tenant_slug"),
        Index("ix_movement_types_tenant_id", "tenant_id"),
    )


# ─── DynamicWarehouseType ───────────────────────────────────────────────────

class DynamicWarehouseType(Base):
    __tablename__ = "warehouse_types"

    id:          Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:   Mapped[str]        = mapped_column(String(255), nullable=False)
    name:        Mapped[str]        = mapped_column(String(150), nullable=False)
    slug:        Mapped[str]        = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color:       Mapped[str | None] = mapped_column(String(20), nullable=True, server_default="#f59e0b")
    is_active:   Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    is_system:   Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    sort_order:  Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    created_by:  Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by:  Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:  Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:  Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    warehouses: Mapped[list[Warehouse]] = relationship("Warehouse", back_populates="dynamic_warehouse_type")
    custom_fields: Mapped[list[CustomWarehouseField]] = relationship(
        "CustomWarehouseField", cascade="all, delete-orphan",
        primaryjoin="DynamicWarehouseType.id == foreign(CustomWarehouseField.warehouse_type_id)",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_warehouse_type_tenant_slug"),
        Index("ix_warehouse_types_tenant_id", "tenant_id"),
    )


# ─── CustomProductField ─────────────────────────────────────────────────────

class CustomProductField(Base):
    __tablename__ = "custom_product_fields"

    id:              Mapped[str]             = mapped_column(String(36), primary_key=True)
    tenant_id:       Mapped[str]             = mapped_column(String(255), nullable=False)
    product_type_id: Mapped[str | None]      = mapped_column(
        String(36), ForeignKey("product_types.id", ondelete="CASCADE"), nullable=True, index=True,
    )
    label:           Mapped[str]             = mapped_column(String(150), nullable=False)
    field_key:       Mapped[str]             = mapped_column(String(100), nullable=False)
    field_type:      Mapped[str]             = mapped_column(String(20), nullable=False, server_default="text")
    options:         Mapped[list | None]     = mapped_column(JSON, nullable=True)
    required:        Mapped[bool]            = mapped_column(Boolean, nullable=False, server_default="false")
    sort_order:      Mapped[int]             = mapped_column(Integer, nullable=False, server_default="0")
    is_active:       Mapped[bool]            = mapped_column(Boolean, nullable=False, server_default="true")
    created_by:      Mapped[str | None]      = mapped_column(String(255), nullable=True)
    updated_by:      Mapped[str | None]      = mapped_column(String(255), nullable=True)
    created_at:      Mapped[DateTime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:      Mapped[DateTime]        = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "field_key", "product_type_id", name="uq_custom_field_tenant_key_pt"),
        Index("ix_custom_product_fields_tenant_id", "tenant_id"),
        Index("ix_custom_product_fields_product_type", "tenant_id", "product_type_id"),
    )


# ─── SupplierType ────────────────────────────────────────────────────────────

class SupplierType(Base):
    __tablename__ = "supplier_types"

    id:          Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:   Mapped[str]        = mapped_column(String(255), nullable=False)
    name:        Mapped[str]        = mapped_column(String(150), nullable=False)
    slug:        Mapped[str]        = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color:       Mapped[str | None] = mapped_column(String(20), nullable=True, server_default="#f59e0b")
    is_active:   Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    created_by:  Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by:  Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:  Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:  Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    suppliers: Mapped[list[Supplier]] = relationship("Supplier", back_populates="supplier_type")
    custom_fields: Mapped[list[CustomSupplierField]] = relationship(
        "CustomSupplierField", cascade="all, delete-orphan",
        primaryjoin="SupplierType.id == foreign(CustomSupplierField.supplier_type_id)",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_supplier_type_tenant_slug"),
        Index("ix_supplier_types_tenant_id", "tenant_id"),
    )


# ─── CustomSupplierField ────────────────────────────────────────────────────

class CustomSupplierField(Base):
    __tablename__ = "custom_supplier_fields"

    id:               Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:        Mapped[str]        = mapped_column(String(255), nullable=False)
    supplier_type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("supplier_types.id", ondelete="CASCADE"), nullable=True,
    )
    label:      Mapped[str]        = mapped_column(String(150), nullable=False)
    field_key:  Mapped[str]        = mapped_column(String(100), nullable=False)
    field_type: Mapped[str]        = mapped_column(String(20), nullable=False, server_default="text")
    options:    Mapped[list | None] = mapped_column(JSON, nullable=True)
    required:   Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    sort_order: Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    is_active:  Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "field_key", "supplier_type_id", name="uq_custom_supplier_field_tenant_key_st"),
        Index("ix_custom_supplier_fields_tenant_id", "tenant_id"),
        Index("ix_custom_supplier_fields_supplier_type", "tenant_id", "supplier_type_id"),
    )


# ─── CustomWarehouseField ──────────────────────────────────────────────────

class CustomWarehouseField(Base):
    __tablename__ = "custom_warehouse_fields"

    id:                Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:         Mapped[str]        = mapped_column(String(255), nullable=False)
    warehouse_type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouse_types.id", ondelete="CASCADE"), nullable=True,
    )
    label:      Mapped[str]        = mapped_column(String(150), nullable=False)
    field_key:  Mapped[str]        = mapped_column(String(100), nullable=False)
    field_type: Mapped[str]        = mapped_column(String(20), nullable=False, server_default="text")
    options:    Mapped[list | None] = mapped_column(JSON, nullable=True)
    required:   Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    sort_order: Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    is_active:  Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "field_key", "warehouse_type_id", name="uq_custom_warehouse_field_tenant_key_wt"),
        Index("ix_custom_warehouse_fields_tenant_id", "tenant_id"),
        Index("ix_custom_warehouse_fields_warehouse_type", "tenant_id", "warehouse_type_id"),
    )


# ─── CustomMovementField ──────────────────────────────────────────────────

class CustomMovementField(Base):
    __tablename__ = "custom_movement_fields"

    id:               Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:        Mapped[str]        = mapped_column(String(255), nullable=False)
    movement_type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("movement_types.id", ondelete="CASCADE"), nullable=True,
    )
    label:      Mapped[str]        = mapped_column(String(150), nullable=False)
    field_key:  Mapped[str]        = mapped_column(String(100), nullable=False)
    field_type: Mapped[str]        = mapped_column(String(20), nullable=False, server_default="text")
    options:    Mapped[list | None] = mapped_column(JSON, nullable=True)
    required:   Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    sort_order: Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    is_active:  Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "field_key", "movement_type_id", name="uq_custom_movement_field_tenant_key_mt"),
        Index("ix_custom_movement_fields_tenant_id", "tenant_id"),
        Index("ix_custom_movement_fields_movement_type", "tenant_id", "movement_type_id"),
    )
