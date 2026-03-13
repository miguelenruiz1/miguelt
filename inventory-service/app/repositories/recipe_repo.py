"""Repository for EntityRecipe and RecipeComponent."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import EntityRecipe, RecipeComponent


class RecipeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, tenant_id: str, is_active: bool | None = True,
        offset: int = 0, limit: int = 50,
    ) -> tuple[list[EntityRecipe], int]:
        base = select(EntityRecipe).where(EntityRecipe.tenant_id == tenant_id)
        if is_active is not None:
            base = base.where(EntityRecipe.is_active == is_active)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = (
            base
            .options(
                selectinload(EntityRecipe.components)
                .selectinload(RecipeComponent.component_entity),
            )
            .order_by(EntityRecipe.name)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(q)
        return list(result.scalars().unique().all()), total

    async def get(self, tenant_id: str, recipe_id: str) -> EntityRecipe | None:
        result = await self.db.execute(
            select(EntityRecipe)
            .options(
                selectinload(EntityRecipe.components)
                .selectinload(RecipeComponent.component_entity),
            )
            .where(EntityRecipe.tenant_id == tenant_id, EntityRecipe.id == recipe_id)
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict, components: list[dict]) -> EntityRecipe:
        recipe_id = str(uuid.uuid4())
        recipe = EntityRecipe(id=recipe_id, tenant_id=tenant_id, **data)
        self.db.add(recipe)
        for comp in components:
            self.db.add(RecipeComponent(id=str(uuid.uuid4()), tenant_id=tenant_id, recipe_id=recipe_id, **comp))
        await self.db.flush()
        await self.db.refresh(recipe, attribute_names=["components"])
        return recipe

    async def update(self, recipe: EntityRecipe, data: dict, components: list[dict] | None = None) -> EntityRecipe:
        for k, v in data.items():
            if v is not None:
                setattr(recipe, k, v)
        if components is not None:
            # Replace components
            for c in list(recipe.components):
                self.db.delete(c)
            await self.db.flush()
            for comp in components:
                self.db.add(RecipeComponent(id=str(uuid.uuid4()), tenant_id=recipe.tenant_id, recipe_id=recipe.id, **comp))
        await self.db.flush()
        await self.db.refresh(recipe, attribute_names=["components"])
        return recipe

    async def soft_delete(self, recipe: EntityRecipe) -> None:
        recipe.is_active = False
        await self.db.flush()
