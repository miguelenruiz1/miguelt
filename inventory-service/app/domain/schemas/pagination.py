"""Generic paginated response schemas for all list endpoints."""
from __future__ import annotations

from pydantic import BaseModel

from app.domain.schemas.config import (
    CustomFieldOut,
    CustomMovementFieldOut,
    CustomSupplierFieldOut,
    CustomWarehouseFieldOut,
    EventSeverityOut,
    EventStatusOut,
    EventTypeOut,
    MovementTypeOut,
    OrderTypeOut,
    ProductTypeOut,
    SerialStatusOut,
    SupplierTypeOut,
    WarehouseTypeOut,
)
from app.domain.schemas.customer import CustomerTypeOut
from app.domain.schemas.production import RecipeOut
from app.domain.schemas.warehouse import LocationOut, WarehouseOut


# ── Core entities ────────────────────────────────────────────────────────────

class PaginatedRecipes(BaseModel):
    items: list[RecipeOut]
    total: int
    offset: int
    limit: int


class PaginatedWarehouses(BaseModel):
    items: list[WarehouseOut]
    total: int
    offset: int
    limit: int


class PaginatedCustomerTypes(BaseModel):
    items: list[CustomerTypeOut]
    total: int
    offset: int
    limit: int


class PaginatedLocations(BaseModel):
    items: list[LocationOut]
    total: int
    offset: int
    limit: int


# ── Config types ─────────────────────────────────────────────────────────────

class PaginatedProductTypes(BaseModel):
    items: list[ProductTypeOut]
    total: int
    offset: int
    limit: int


class PaginatedOrderTypes(BaseModel):
    items: list[OrderTypeOut]
    total: int
    offset: int
    limit: int


class PaginatedSupplierTypes(BaseModel):
    items: list[SupplierTypeOut]
    total: int
    offset: int
    limit: int


class PaginatedMovementTypes(BaseModel):
    items: list[MovementTypeOut]
    total: int
    offset: int
    limit: int


class PaginatedWarehouseTypes(BaseModel):
    items: list[WarehouseTypeOut]
    total: int
    offset: int
    limit: int


class PaginatedEventTypes(BaseModel):
    items: list[EventTypeOut]
    total: int
    offset: int
    limit: int


class PaginatedEventSeverities(BaseModel):
    items: list[EventSeverityOut]
    total: int
    offset: int
    limit: int


class PaginatedEventStatuses(BaseModel):
    items: list[EventStatusOut]
    total: int
    offset: int
    limit: int


class PaginatedSerialStatuses(BaseModel):
    items: list[SerialStatusOut]
    total: int
    offset: int
    limit: int


class PaginatedCustomFields(BaseModel):
    items: list[CustomFieldOut]
    total: int
    offset: int
    limit: int


class PaginatedCustomSupplierFields(BaseModel):
    items: list[CustomSupplierFieldOut]
    total: int
    offset: int
    limit: int


class PaginatedCustomWarehouseFields(BaseModel):
    items: list[CustomWarehouseFieldOut]
    total: int
    offset: int
    limit: int


class PaginatedCustomMovementFields(BaseModel):
    items: list[CustomMovementFieldOut]
    total: int
    offset: int
    limit: int
