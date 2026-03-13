"""Production (BOM/Recipe) and cost layering models."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.entity import Product
    from app.db.models.stock import StockMovement
    from app.db.models.warehouse import Warehouse
    from app.db.models.tracking import EntityBatch


class EntityRecipe(Base):
    __tablename__ = "entity_recipes"

    id:               Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:        Mapped[str]        = mapped_column(String(255), nullable=False)
    name:             Mapped[str]        = mapped_column(String(255), nullable=False)
    output_entity_id: Mapped[str]        = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False
    )
    output_quantity:  Mapped[Decimal]    = mapped_column(Numeric(12, 4), nullable=False, server_default="1")
    description:      Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active:        Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    created_by:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:       Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:       Mapped[DateTime]   = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    output_entity: Mapped[Product]              = relationship("Product")
    components:    Mapped[list[RecipeComponent]] = relationship(
        "RecipeComponent", back_populates="recipe", cascade="all, delete-orphan"
    )
    production_runs: Mapped[list[ProductionRun]] = relationship("ProductionRun", back_populates="recipe")

    __table_args__ = (
        Index("ix_entity_recipes_tenant_id", "tenant_id"),
    )


class RecipeComponent(Base):
    __tablename__ = "recipe_components"

    id:                   Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:            Mapped[str]        = mapped_column(String(255), nullable=False, index=True)
    recipe_id:            Mapped[str]        = mapped_column(
        String(36), ForeignKey("entity_recipes.id", ondelete="CASCADE"), nullable=False
    )
    component_entity_id:  Mapped[str]        = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False
    )
    quantity_required:    Mapped[Decimal]    = mapped_column(Numeric(12, 4), nullable=False)
    notes:                Mapped[str | None] = mapped_column(Text, nullable=True)

    recipe:           Mapped[EntityRecipe] = relationship("EntityRecipe", back_populates="components")
    component_entity: Mapped[Product]      = relationship("Product")


class ProductionRun(Base):
    __tablename__ = "production_runs"

    id:           Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:    Mapped[str]            = mapped_column(String(255), nullable=False)
    recipe_id:    Mapped[str]            = mapped_column(
        String(36), ForeignKey("entity_recipes.id", ondelete="RESTRICT"), nullable=False
    )
    run_number:   Mapped[str]            = mapped_column(String(50), nullable=False)
    warehouse_id: Mapped[str]            = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    output_warehouse_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True
    )
    multiplier:   Mapped[Decimal]        = mapped_column(Numeric(12, 4), nullable=False, server_default="1")
    status:       Mapped[str]            = mapped_column(String(20), nullable=False, server_default="pending")
    started_at:   Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    performed_by: Mapped[str | None]     = mapped_column(String(255), nullable=True)
    updated_by:       Mapped[str | None]     = mapped_column(String(255), nullable=True)
    notes:            Mapped[str | None]     = mapped_column(Text, nullable=True)
    approved_by:      Mapped[str | None]     = mapped_column(String(255), nullable=True)
    approved_at:      Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_notes:  Mapped[str | None]     = mapped_column(Text, nullable=True)
    created_at:       Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipe:           Mapped[EntityRecipe] = relationship("EntityRecipe", back_populates="production_runs")
    warehouse:        Mapped[Warehouse]    = relationship("Warehouse", foreign_keys=[warehouse_id])
    output_warehouse: Mapped[Warehouse | None] = relationship("Warehouse", foreign_keys=[output_warehouse_id])

    __table_args__ = (
        UniqueConstraint("tenant_id", "run_number", name="uq_production_run_tenant_number"),
        Index("ix_production_runs_tenant_id", "tenant_id"),
        Index("ix_production_runs_status", "status"),
    )


class StockLayer(Base):
    __tablename__ = "stock_layers"

    id:                 Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:          Mapped[str]            = mapped_column(String(255), nullable=False)
    entity_id:          Mapped[str]            = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id:       Mapped[str]            = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    movement_id:        Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("stock_movements.id", ondelete="SET NULL"), nullable=True
    )
    quantity_initial:   Mapped[Decimal]        = mapped_column(Numeric(12, 4), nullable=False)
    quantity_remaining: Mapped[Decimal]        = mapped_column(Numeric(12, 4), nullable=False)
    unit_cost:          Mapped[Decimal]        = mapped_column(Numeric(12, 4), nullable=False)
    batch_id:           Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True
    )
    created_at:         Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    entity:    Mapped[Product]           = relationship("Product")
    warehouse: Mapped[Warehouse]         = relationship("Warehouse")
    movement:  Mapped[StockMovement | None] = relationship("StockMovement")
    batch:     Mapped[EntityBatch | None]   = relationship("EntityBatch")

    __table_args__ = (
        Index("ix_stock_layers_tenant_id", "tenant_id"),
        Index("ix_stock_layers_entity_wh", "entity_id", "warehouse_id"),
        Index("ix_stock_layers_remaining", "entity_id", "warehouse_id", "quantity_remaining"),
    )
