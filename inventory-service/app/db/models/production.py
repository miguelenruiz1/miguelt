"""Production v2 — BOM, production runs, emissions, receipts, cost layering."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.entity import Product
    from app.db.models.stock import StockMovement
    from app.db.models.warehouse import Warehouse
    from app.db.models.tracking import EntityBatch


# ── BOM / Recipe ─────────────────────────────────────────────────────────────

class EntityRecipe(Base):
    """Bill of Materials — defines components needed to produce an output product."""
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

    # v2 fields
    bom_type:                 Mapped[str]     = mapped_column(String(20), nullable=False, server_default="production")
    standard_cost:            Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    planned_production_size:  Mapped[int]     = mapped_column(Integer, nullable=False, server_default="1")
    # v3: manufacturing versions
    version:                  Mapped[str]     = mapped_column(String(20), nullable=False, server_default="v1")
    is_default:               Mapped[bool]    = mapped_column(Boolean, nullable=False, server_default="true")

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
    resources:     Mapped[list[RecipeResource]] = relationship(
        "RecipeResource", back_populates="recipe", cascade="all, delete-orphan"
    )
    production_runs: Mapped[list[ProductionRun]] = relationship("ProductionRun", back_populates="recipe")

    __table_args__ = (
        Index("ix_entity_recipes_tenant_id", "tenant_id"),
    )


class RecipeComponent(Base):
    """A single component (ingredient/material) within a BOM."""
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

    # v2 fields
    issue_method:           Mapped[str]     = mapped_column(String(20), nullable=False, server_default="manual")
    scrap_percentage:       Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, server_default="0")
    lead_time_offset_days:  Mapped[int]     = mapped_column(Integer, nullable=False, server_default="0")

    recipe:           Mapped[EntityRecipe] = relationship("EntityRecipe", back_populates="components")
    component_entity: Mapped[Product]      = relationship("Product")


# ── Production Run (Order) ───────────────────────────────────────────────────

class ProductionRun(Base):
    """Production order — lifecycle: planned → released → in_progress → completed → closed."""
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
    status:       Mapped[str]            = mapped_column(String(20), nullable=False, server_default="planned")

    # v2: order type and priority
    order_type:   Mapped[str]            = mapped_column(String(20), nullable=False, server_default="standard")
    priority:     Mapped[int]            = mapped_column(Integer, nullable=False, server_default="50")

    # v2: dates
    planned_start_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    planned_end_date:   Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_start_date:  Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end_date:    Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Legacy timestamps
    started_at:   Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # v2: actual output and costs
    actual_output_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    total_component_cost:   Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_production_cost:  Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    unit_production_cost:   Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)
    variance_amount:        Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    # v2: linked documents
    linked_sales_order_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    linked_customer_id:    Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Performer and approval
    performed_by:     Mapped[str | None]     = mapped_column(String(255), nullable=True)
    updated_by:       Mapped[str | None]     = mapped_column(String(255), nullable=True)
    notes:            Mapped[str | None]     = mapped_column(Text, nullable=True)
    approved_by:      Mapped[str | None]     = mapped_column(String(255), nullable=True)
    approved_at:      Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_notes:  Mapped[str | None]     = mapped_column(Text, nullable=True)
    created_at:       Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    recipe:           Mapped[EntityRecipe] = relationship("EntityRecipe", back_populates="production_runs")
    warehouse:        Mapped[Warehouse]    = relationship("Warehouse", foreign_keys=[warehouse_id])
    output_warehouse: Mapped[Warehouse | None] = relationship("Warehouse", foreign_keys=[output_warehouse_id])
    # v3: resource cost
    total_resource_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    emissions:        Mapped[list[ProductionEmission]] = relationship("ProductionEmission", back_populates="production_run", cascade="all, delete-orphan")
    receipts:         Mapped[list[ProductionReceipt]]  = relationship("ProductionReceipt", back_populates="production_run", cascade="all, delete-orphan")
    resource_costs:   Mapped[list[ProductionRunResourceCost]] = relationship("ProductionRunResourceCost", back_populates="production_run", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "run_number", name="uq_production_run_tenant_number"),
        Index("ix_production_runs_tenant_id", "tenant_id"),
        Index("ix_production_runs_status", "status"),
    )


# ── Emission (Material Issue) ────────────────────────────────────────────────

class ProductionEmission(Base):
    """Material issue document — removes components from inventory into WIP."""
    __tablename__ = "production_emissions"

    id:                Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:         Mapped[str]            = mapped_column(String(255), nullable=False)
    production_run_id: Mapped[str]            = mapped_column(
        String(36), ForeignKey("production_runs.id", ondelete="RESTRICT"), nullable=False
    )
    emission_number:   Mapped[str]            = mapped_column(String(50), nullable=False)
    status:            Mapped[str]            = mapped_column(String(20), nullable=False, server_default="posted")
    emission_date:     Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    warehouse_id:      Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True
    )
    notes:             Mapped[str | None]     = mapped_column(Text, nullable=True)
    performed_by:      Mapped[str | None]     = mapped_column(String(255), nullable=True)
    created_at:        Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    production_run: Mapped[ProductionRun] = relationship("ProductionRun", back_populates="emissions")
    lines:          Mapped[list[ProductionEmissionLine]] = relationship(
        "ProductionEmissionLine", back_populates="emission", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_prod_emissions_tenant", "tenant_id"),
        Index("ix_prod_emissions_run", "production_run_id"),
    )


class ProductionEmissionLine(Base):
    """Single component issued in an emission."""
    __tablename__ = "production_emission_lines"

    id:                  Mapped[str]            = mapped_column(String(36), primary_key=True)
    emission_id:         Mapped[str]            = mapped_column(
        String(36), ForeignKey("production_emissions.id", ondelete="CASCADE"), nullable=False
    )
    component_entity_id: Mapped[str]            = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False
    )
    planned_quantity:    Mapped[Decimal]        = mapped_column(Numeric(12, 4), nullable=False)
    actual_quantity:     Mapped[Decimal]        = mapped_column(Numeric(12, 4), nullable=False)
    unit_cost:           Mapped[Decimal]        = mapped_column(Numeric(12, 4), nullable=False, server_default="0")
    total_cost:          Mapped[Decimal]        = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    batch_id:            Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True
    )
    warehouse_id:        Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True
    )
    variance_quantity:   Mapped[Decimal]        = mapped_column(Numeric(12, 4), nullable=False, server_default="0")

    emission:         Mapped[ProductionEmission] = relationship("ProductionEmission", back_populates="lines")
    component_entity: Mapped[Product]           = relationship("Product")

    __table_args__ = (
        Index("ix_prod_emission_lines_emission", "emission_id"),
    )


# ── Receipt (Finished Goods Receipt) ─────────────────────────────────────────

class ProductionReceipt(Base):
    """Receipt document — receives finished goods from WIP into inventory."""
    __tablename__ = "production_receipts"

    id:                  Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:           Mapped[str]            = mapped_column(String(255), nullable=False)
    production_run_id:   Mapped[str]            = mapped_column(
        String(36), ForeignKey("production_runs.id", ondelete="RESTRICT"), nullable=False
    )
    receipt_number:      Mapped[str]            = mapped_column(String(50), nullable=False)
    status:              Mapped[str]            = mapped_column(String(20), nullable=False, server_default="posted")
    receipt_date:        Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    output_warehouse_id: Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True
    )
    notes:               Mapped[str | None]     = mapped_column(Text, nullable=True)
    performed_by:        Mapped[str | None]     = mapped_column(String(255), nullable=True)
    created_at:          Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    production_run: Mapped[ProductionRun] = relationship("ProductionRun", back_populates="receipts")
    lines:          Mapped[list[ProductionReceiptLine]] = relationship(
        "ProductionReceiptLine", back_populates="receipt", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_prod_receipts_tenant", "tenant_id"),
        Index("ix_prod_receipts_run", "production_run_id"),
    )


class ProductionReceiptLine(Base):
    """Single product received in a receipt."""
    __tablename__ = "production_receipt_lines"

    id:                Mapped[str]            = mapped_column(String(36), primary_key=True)
    receipt_id:        Mapped[str]            = mapped_column(
        String(36), ForeignKey("production_receipts.id", ondelete="CASCADE"), nullable=False
    )
    entity_id:         Mapped[str]            = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False
    )
    planned_quantity:  Mapped[Decimal]        = mapped_column(Numeric(12, 4), nullable=False)
    received_quantity: Mapped[Decimal]        = mapped_column(Numeric(12, 4), nullable=False)
    unit_cost:         Mapped[Decimal]        = mapped_column(Numeric(14, 6), nullable=False, server_default="0")
    total_cost:        Mapped[Decimal]        = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    batch_id:          Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True
    )
    is_complete:       Mapped[bool]           = mapped_column(Boolean, nullable=False, server_default="false")

    receipt: Mapped[ProductionReceipt] = relationship("ProductionReceipt", back_populates="lines")
    entity:  Mapped[Product]           = relationship("Product")

    __table_args__ = (
        Index("ix_prod_receipt_lines_receipt", "receipt_id"),
    )


# ── Resources / Work Centers ──────────────────────────────────────────────────

class ProductionResource(Base):
    """Work center: labor, machine, or overhead resource used in production."""
    __tablename__ = "production_resources"

    id:                      Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:               Mapped[str]            = mapped_column(String(255), nullable=False)
    name:                    Mapped[str]            = mapped_column(String(255), nullable=False)
    resource_type:           Mapped[str]            = mapped_column(String(20), nullable=False, server_default="labor")
    cost_per_hour:           Mapped[Decimal]        = mapped_column(Numeric(12, 4), nullable=False, server_default="0")
    cost_per_unit:           Mapped[Decimal]        = mapped_column(Numeric(12, 4), nullable=False, server_default="0")
    capacity_hours_per_day:  Mapped[Decimal]        = mapped_column(Numeric(6, 2), nullable=False, server_default="8")
    efficiency_pct:          Mapped[Decimal]        = mapped_column(Numeric(5, 2), nullable=False, server_default="100")
    shifts_per_day:          Mapped[int]            = mapped_column(Integer, nullable=False, server_default="1")
    available_hours_override: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    is_active:               Mapped[bool]           = mapped_column(Boolean, nullable=False, server_default="true")
    notes:                   Mapped[str | None]     = mapped_column(Text, nullable=True)
    created_by:              Mapped[str | None]     = mapped_column(String(255), nullable=True)
    updated_by:              Mapped[str | None]     = mapped_column(String(255), nullable=True)
    created_at:              Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:              Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_production_resources_tenant", "tenant_id"),
    )


class RecipeResource(Base):
    """Junction: which resources a recipe needs, with hours and setup time."""
    __tablename__ = "recipe_resources"

    id:               Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:        Mapped[str]            = mapped_column(String(255), nullable=False)
    recipe_id:        Mapped[str]            = mapped_column(String(36), ForeignKey("entity_recipes.id", ondelete="CASCADE"), nullable=False)
    resource_id:      Mapped[str]            = mapped_column(String(36), ForeignKey("production_resources.id", ondelete="RESTRICT"), nullable=False)
    hours_per_unit:   Mapped[Decimal]        = mapped_column(Numeric(8, 4), nullable=False)
    setup_time_hours: Mapped[Decimal]        = mapped_column(Numeric(8, 4), nullable=False, server_default="0")
    notes:            Mapped[str | None]     = mapped_column(Text, nullable=True)

    recipe:   Mapped[EntityRecipe]       = relationship("EntityRecipe", back_populates="resources")
    resource: Mapped[ProductionResource] = relationship("ProductionResource")

    __table_args__ = (
        UniqueConstraint("recipe_id", "resource_id", name="uq_recipe_resource"),
        Index("ix_recipe_resources_recipe", "recipe_id"),
    )


class ProductionRunResourceCost(Base):
    """Actual resource costs tracked per production run."""
    __tablename__ = "production_run_resource_costs"

    id:                 Mapped[str]            = mapped_column(String(36), primary_key=True)
    production_run_id:  Mapped[str]            = mapped_column(String(36), ForeignKey("production_runs.id", ondelete="RESTRICT"), nullable=False)
    resource_id:        Mapped[str]            = mapped_column(String(36), ForeignKey("production_resources.id", ondelete="RESTRICT"), nullable=False)
    planned_hours:      Mapped[Decimal]        = mapped_column(Numeric(8, 4), nullable=False)
    actual_hours:       Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    cost_per_hour:      Mapped[Decimal]        = mapped_column(Numeric(12, 4), nullable=False)
    total_cost:         Mapped[Decimal]        = mapped_column(Numeric(14, 2), nullable=False)
    created_at:         Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    production_run: Mapped[ProductionRun]    = relationship("ProductionRun", back_populates="resource_costs")
    resource:       Mapped[ProductionResource] = relationship("ProductionResource")

    __table_args__ = (
        Index("ix_run_resource_costs_run", "production_run_id"),
    )


# ── Cost Layering (FIFO) ────────────────────────────────────────────────────

class StockLayer(Base):
    """FIFO cost layer for inventory valuation."""
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
