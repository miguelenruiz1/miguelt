"""Repository for Category CRUD."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import Category


def _slugify(text: str) -> str:
    """Simple slugification: lowercase, replace non-alphanumeric with hyphens."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class CategoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: str,
        search: str | None = None,
        is_active: bool | None = None,
        parent_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Category], int]:
        base_q = select(Category).where(Category.tenant_id == tenant_id)
        if is_active is not None:
            base_q = base_q.where(Category.is_active == is_active)
        if parent_id is not None:
            base_q = base_q.where(Category.parent_id == parent_id)
        if search:
            base_q = base_q.where(Category.name.ilike(f"%{search}%"))

        count_q = select(func.count()).select_from(base_q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = (
            base_q
            .options(joinedload(Category.parent))
            .order_by(Category.sort_order, Category.name)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(q)
        return list(result.scalars().unique().all()), total

    async def get_by_id(self, category_id: str, tenant_id: str) -> Category | None:
        result = await self.db.execute(
            select(Category)
            .options(joinedload(Category.parent))
            .where(
                Category.id == category_id,
                Category.tenant_id == tenant_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> Category:
        slug = _slugify(data.get("name", ""))
        cat = Category(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            slug=slug,
            **data,
        )
        self.db.add(cat)
        await self.db.flush()
        await self.db.refresh(cat)
        return cat

    async def update(self, category: Category, data: dict) -> Category:
        for k, v in data.items():
            setattr(category, k, v)
        if "name" in data and data["name"]:
            category.slug = _slugify(data["name"])
        category.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def delete(self, category: Category) -> None:
        await self.db.delete(category)
        await self.db.flush()
