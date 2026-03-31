"""Repository for production emissions (material issues)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.production import ProductionEmission, ProductionEmissionLine


class EmissionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def next_emission_number(self, tenant_id: str) -> str:
        year = datetime.now(tz=timezone.utc).year
        prefix = f"EM-{year}-"
        result = await self._db.execute(
            select(func.count(ProductionEmission.id))
            .where(
                ProductionEmission.tenant_id == tenant_id,
                ProductionEmission.emission_number.like(f"{prefix}%"),
            )
        )
        count = result.scalar_one() or 0
        return f"{prefix}{count + 1:04d}"

    async def create(
        self,
        tenant_id: str,
        production_run_id: str,
        emission_number: str,
        emission_date: datetime,
        warehouse_id: str | None,
        notes: str | None,
        performed_by: str | None,
        lines: list[dict],
    ) -> ProductionEmission:
        emission = ProductionEmission(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            production_run_id=production_run_id,
            emission_number=emission_number,
            status="posted",
            emission_date=emission_date,
            warehouse_id=warehouse_id,
            notes=notes,
            performed_by=performed_by,
        )
        self._db.add(emission)
        await self._db.flush()

        for line_data in lines:
            line = ProductionEmissionLine(
                id=str(uuid.uuid4()),
                emission_id=emission.id,
                **line_data,
            )
            self._db.add(line)

        await self._db.flush()
        return emission

    async def get(self, tenant_id: str, emission_id: str) -> ProductionEmission | None:
        result = await self._db.execute(
            select(ProductionEmission)
            .options(selectinload(ProductionEmission.lines))
            .where(
                ProductionEmission.id == emission_id,
                ProductionEmission.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_run(self, tenant_id: str, run_id: str) -> list[ProductionEmission]:
        result = await self._db.execute(
            select(ProductionEmission)
            .options(selectinload(ProductionEmission.lines))
            .where(
                ProductionEmission.production_run_id == run_id,
                ProductionEmission.tenant_id == tenant_id,
            )
            .order_by(ProductionEmission.created_at.asc())
        )
        return list(result.scalars().all())

    async def total_emitted_by_component(self, run_id: str) -> dict[str, float]:
        """Return total emitted quantity per component_entity_id for a run."""
        result = await self._db.execute(
            select(
                ProductionEmissionLine.component_entity_id,
                func.sum(ProductionEmissionLine.actual_quantity).label("total"),
            )
            .join(ProductionEmission, ProductionEmissionLine.emission_id == ProductionEmission.id)
            .where(ProductionEmission.production_run_id == run_id)
            .group_by(ProductionEmissionLine.component_entity_id)
        )
        return {str(row[0]): float(row[1]) for row in result.all()}

    async def total_component_cost(self, run_id: str) -> float:
        """Return total cost of all emissions for a run."""
        result = await self._db.execute(
            select(func.coalesce(func.sum(ProductionEmissionLine.total_cost), 0))
            .join(ProductionEmission, ProductionEmissionLine.emission_id == ProductionEmission.id)
            .where(ProductionEmission.production_run_id == run_id)
        )
        return float(result.scalar_one())
