"""Repository for production resources (work centers)."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.production import ProductionResource, ProductionRunResourceCost, ProductionRun


class ResourceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list(self, tenant_id: str, active_only: bool = True) -> list[ProductionResource]:
        q = select(ProductionResource).where(ProductionResource.tenant_id == tenant_id)
        if active_only:
            q = q.where(ProductionResource.is_active.is_(True))
        q = q.order_by(ProductionResource.name)
        return list((await self._db.execute(q)).scalars().all())

    async def get(self, tenant_id: str, resource_id: str) -> ProductionResource | None:
        result = await self._db.execute(
            select(ProductionResource).where(
                ProductionResource.id == resource_id,
                ProductionResource.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> ProductionResource:
        resource = ProductionResource(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self._db.add(resource)
        await self._db.flush()
        return resource

    async def update(self, resource: ProductionResource, data: dict) -> ProductionResource:
        for k, v in data.items():
            if v is not None and hasattr(resource, k):
                setattr(resource, k, v)
        await self._db.flush()
        return resource

    async def soft_delete(self, resource: ProductionResource) -> None:
        resource.is_active = False
        await self._db.flush()

    async def committed_hours(self, resource_id: str, date_from: str | None = None, date_to: str | None = None) -> Decimal:
        """Sum planned_hours for active production runs using this resource."""
        q = (
            select(func.coalesce(func.sum(ProductionRunResourceCost.planned_hours), 0))
            .join(ProductionRun, ProductionRunResourceCost.production_run_id == ProductionRun.id)
            .where(
                ProductionRunResourceCost.resource_id == resource_id,
                ProductionRun.status.in_(["planned", "released", "in_progress"]),
            )
        )
        if date_from:
            q = q.where(ProductionRun.planned_end_date >= date_from)
        if date_to:
            q = q.where(ProductionRun.planned_start_date <= date_to)
        result = await self._db.execute(q)
        return Decimal(str(result.scalar_one()))
