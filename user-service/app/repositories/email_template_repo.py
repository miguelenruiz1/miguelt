"""Email template repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EmailTemplate


class EmailTemplateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, tenant_id: str) -> list[EmailTemplate]:
        result = await self.db.execute(
            select(EmailTemplate)
            .where(EmailTemplate.tenant_id == tenant_id)
            .order_by(EmailTemplate.slug)
        )
        return list(result.scalars())

    async def get_by_id(self, template_id: str) -> EmailTemplate | None:
        result = await self.db.execute(
            select(EmailTemplate).where(EmailTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, tenant_id: str, slug: str) -> EmailTemplate | None:
        result = await self.db.execute(
            select(EmailTemplate).where(
                EmailTemplate.tenant_id == tenant_id,
                EmailTemplate.slug == slug,
            )
        )
        return result.scalar_one_or_none()

    async def update(self, template: EmailTemplate, **kwargs) -> EmailTemplate:
        for k, v in kwargs.items():
            setattr(template, k, v)
        await self.db.flush()
        await self.db.refresh(template)
        return template
