"""Production (BOM/Recipe) and cost layer schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase


# ─── Recipe ─────────────────────────────────────────────────────────────────

class RecipeComponentCreate(BaseModel):
    component_entity_id: str
    quantity_required: Decimal = Field(..., gt=0)
    notes: str | None = None


class RecipeCreate(BaseModel):
    name: str = Field(..., max_length=255)
    output_entity_id: str
    output_quantity: Decimal = Field(Decimal("1"), gt=0)
    description: str | None = None
    is_active: bool = True
    components: list[RecipeComponentCreate] = []


class RecipeUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    output_entity_id: str | None = None
    output_quantity: Decimal | None = None
    description: str | None = None
    is_active: bool | None = None
    components: list[RecipeComponentCreate] | None = None


class RecipeComponentOut(OrmBase):
    id: str
    recipe_id: str
    component_entity_id: str
    quantity_required: Decimal
    notes: str | None


class RecipeOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    output_entity_id: str
    output_quantity: Decimal
    description: str | None
    is_active: bool
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime
    components: list[RecipeComponentOut] = []


# ─── Production Run ─────────────────────────────────────────────────────────

class ProductionRunCreate(BaseModel):
    recipe_id: str
    warehouse_id: str
    output_warehouse_id: str | None = None
    multiplier: Decimal = Field(Decimal("1"), gt=0)
    notes: str | None = None


class ProductionRunReject(BaseModel):
    rejection_notes: str = Field(..., min_length=1, max_length=2000)


class ProductionRunOut(OrmBase):
    id: str
    tenant_id: str
    recipe_id: str
    run_number: str
    warehouse_id: str
    output_warehouse_id: str | None = None
    multiplier: Decimal
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    performed_by: str | None
    updated_by: str | None = None
    notes: str | None
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_notes: str | None = None
    created_at: datetime


class PaginatedProductionRuns(BaseModel):
    items: list[ProductionRunOut]
    total: int
    offset: int
    limit: int


# ─── Stock Layer ────────────────────────────────────────────────────────────

class StockLayerOut(OrmBase):
    id: str
    tenant_id: str
    entity_id: str
    warehouse_id: str
    movement_id: str | None
    quantity_initial: Decimal
    quantity_remaining: Decimal
    unit_cost: Decimal
    batch_id: str | None
    created_at: datetime
