"""Role template repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RoleTemplate


class TemplateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, tenant_id: str) -> list[RoleTemplate]:
        result = await self.db.execute(
            select(RoleTemplate)
            .where(RoleTemplate.tenant_id == tenant_id)
            .order_by(RoleTemplate.is_default.desc(), RoleTemplate.name)
        )
        return list(result.scalars())

    async def get_by_id(self, template_id: str) -> RoleTemplate | None:
        result = await self.db.execute(
            select(RoleTemplate).where(RoleTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str, tenant_id: str) -> RoleTemplate | None:
        result = await self.db.execute(
            select(RoleTemplate).where(
                RoleTemplate.slug == slug, RoleTemplate.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> RoleTemplate:
        tmpl = RoleTemplate(**kwargs)
        self.db.add(tmpl)
        await self.db.flush()
        await self.db.refresh(tmpl)
        return tmpl

    async def update(self, tmpl: RoleTemplate, **kwargs) -> RoleTemplate:
        for k, v in kwargs.items():
            setattr(tmpl, k, v)
        await self.db.flush()
        await self.db.refresh(tmpl)
        return tmpl

    async def delete(self, tmpl: RoleTemplate) -> None:
        self.db.delete(tmpl)
        await self.db.flush()
