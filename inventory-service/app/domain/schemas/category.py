"""Category schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase


class CategoryCreate(BaseModel):
    name: str = Field(..., max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    parent_id: str | None = None
    is_active: bool = True
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    parent_id: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class CategoryOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    slug: str
    description: str | None = None
    parent_id: str | None = None
    parent_name: str | None = None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PaginatedCategories(BaseModel):
    items: list[CategoryOut]
    total: int
    offset: int
    limit: int
