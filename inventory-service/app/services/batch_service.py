"""Business logic for batch tracking."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models.enums import MovementType
from app.db.models.stock import StockMovement
from app.db.models.tracking import EntityBatch
from app.db.models.entity import Product
from app.db.models.sales_order import SalesOrder, SalesOrderLine
from app.db.models.customer import Customer
from app.domain.schemas import BatchOut
from app.domain.schemas.tracking import (
    BatchDispatchEntry, BatchSearchResult, TraceForwardOut,
)
from app.repositories.batch_repo import BatchRepository


class BatchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = BatchRepository(db)

    async def list(
        self,
        tenant_id: str,
        entity_id: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ):
        return await self.repo.list(tenant_id, entity_id, is_active, offset, limit)

    async def get(self, tenant_id: str, batch_id: str):
        obj = await self.repo.get(tenant_id, batch_id)
        if not obj:
            raise NotFoundError("Lote no encontrado")
        return obj

    async def create(self, tenant_id: str, data: dict):
        if "metadata" in data:
            data["metadata_"] = data.pop("metadata")
        return await self.repo.create(tenant_id, data)

    async def update(self, tenant_id: str, batch_id: str, data: dict):
        obj = await self.repo.get(tenant_id, batch_id)
        if not obj:
            raise NotFoundError("Lote no encontrado")
        if "metadata" in data:
            data["metadata_"] = data.pop("metadata")
        return await self.repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def list_expiring(
        self,
        tenant_id: str,
        days: int = 30,
        offset: int = 0,
        limit: int = 50,
    ):
        return await self.repo.get_expiring_soon(tenant_id, days, offset=offset, limit=limit)

    async def delete(self, tenant_id: str, batch_id: str) -> None:
        obj = await self.get(tenant_id, batch_id)
        await self.repo.soft_delete(obj)

    async def search(
        self, tenant_id: str, batch_code: str, product_id: str | None = None,
    ) -> list[BatchSearchResult]:
        """Search batches by batch_number with dispatch/SO summary."""
        q = select(EntityBatch).where(
            EntityBatch.tenant_id == tenant_id,
            EntityBatch.batch_number.ilike(f"%{batch_code}%"),
        )
        if product_id:
            q = q.where(EntityBatch.entity_id == product_id)
        q = q.order_by(EntityBatch.created_at.desc()).limit(20)
        batches = list((await self.db.execute(q)).scalars().all())

        results = []
        today = date.today()
        for batch in batches:
            prod = (await self.db.execute(
                select(Product.name).where(Product.id == batch.entity_id)
            )).scalar_one_or_none()

            received = (await self.db.execute(
                select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
                    StockMovement.batch_id == batch.id,
                    StockMovement.tenant_id == tenant_id,
                    StockMovement.movement_type.in_([MovementType.purchase, MovementType.adjustment_in]),
                )
            )).scalar_one()

            dispatched = (await self.db.execute(
                select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
                    StockMovement.batch_id == batch.id,
                    StockMovement.tenant_id == tenant_id,
                    StockMovement.movement_type.in_([MovementType.sale, MovementType.adjustment_out, MovementType.waste]),
                )
            )).scalar_one()

            so_rows = (await self.db.execute(
                select(SalesOrder.id, SalesOrder.order_number, SalesOrder.customer_id)
                .join(SalesOrderLine, SalesOrderLine.order_id == SalesOrder.id)
                .where(
                    SalesOrderLine.batch_id == batch.id,
                    SalesOrder.tenant_id == tenant_id,
                )
                .distinct()
            )).all()

            if not batch.expiration_date:
                exp_status = "no_expiry"
            elif batch.expiration_date < today:
                exp_status = "expired"
            elif (batch.expiration_date - today).days <= 30:
                exp_status = "expiring_soon"
            else:
                exp_status = "ok"

            results.append(BatchSearchResult(
                batch=BatchOut.model_validate(batch),
                product_name=prod,
                total_received=float(received),
                total_dispatched=float(dispatched),
                current_qty=float(batch.quantity),
                expiration_status=exp_status,
                sales_orders=[
                    {"id": r[0], "order_number": r[1], "customer_id": r[2]}
                    for r in so_rows
                ],
            ))

        return results

    async def trace_forward(self, tenant_id: str, batch_id: str) -> TraceForwardOut:
        """Trace forward: batch -> which customers received it."""
        batch = await self.get(tenant_id, batch_id)

        prod = (await self.db.execute(
            select(Product.id, Product.name).where(Product.id == batch.entity_id)
        )).one_or_none()

        dispatch_types = [MovementType.sale, MovementType.adjustment_out, MovementType.transfer]
        movements = list((await self.db.execute(
            select(StockMovement).where(
                StockMovement.batch_id == batch_id,
                StockMovement.tenant_id == tenant_id,
                StockMovement.movement_type.in_(dispatch_types),
            ).order_by(StockMovement.created_at.desc())
        )).scalars().all())

        dispatches = []
        total_dispatched = 0.0
        for m in movements:
            so_number = None
            so_id = None
            customer_id = None
            customer_name = None

            if m.reference and m.reference.startswith("SO:"):
                so_num = m.reference[3:]
                so_row = (await self.db.execute(
                    select(SalesOrder.id, SalesOrder.order_number, SalesOrder.customer_id)
                    .where(
                        SalesOrder.order_number == so_num,
                        SalesOrder.tenant_id == tenant_id,
                    )
                )).one_or_none()
                if so_row:
                    so_id = so_row[0]
                    so_number = so_row[1]
                    customer_id = so_row[2]
                    cust = (await self.db.execute(
                        select(Customer.name).where(Customer.id == customer_id)
                    )).scalar_one_or_none()
                    customer_name = cust

            dispatches.append(BatchDispatchEntry(
                movement_id=m.id,
                movement_date=m.created_at,
                qty=float(m.quantity),
                sales_order_id=so_id,
                sales_order_number=so_number,
                customer_id=customer_id,
                customer_name=customer_name,
                warehouse_id=m.from_warehouse_id,
            ))
            total_dispatched += float(m.quantity)

        return TraceForwardOut(
            batch=BatchOut.model_validate(batch),
            product_id=batch.entity_id,
            product_name=prod[1] if prod else None,
            dispatches=dispatches,
            total_dispatched=total_dispatched,
            total_remaining=float(batch.quantity),
        )
