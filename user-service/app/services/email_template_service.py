"""Email template management service."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models import EmailTemplate
from app.repositories.email_template_repo import EmailTemplateRepository


class EmailTemplateService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = EmailTemplateRepository(db)

    async def list(self, tenant_id: str) -> list[EmailTemplate]:
        return await self.repo.list(tenant_id)

    async def get(self, template_id: str) -> EmailTemplate:
        tpl = await self.repo.get_by_id(template_id)
        if not tpl:
            raise NotFoundError(f"Email template {template_id} not found")
        return tpl

    async def update(self, template_id: str, **kwargs) -> EmailTemplate:
        tpl = await self.get(template_id)
        return await self.repo.update(tpl, **kwargs)
