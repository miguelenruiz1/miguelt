"""Repository for StockAlert."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import StockAlert, Product
from app.db.models.warehouse import Warehouse


class AlertRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: str,
        is_resolved: bool | None = None,
        alert_type: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        q = select(StockAlert).where(StockAlert.tenant_id == tenant_id)
        if is_resolved is not None:
            q = q.where(StockAlert.is_resolved == is_resolved)
        if alert_type:
            q = q.where(StockAlert.alert_type == alert_type)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        q = q.order_by(StockAlert.created_at.desc()).offset(offset).limit(limit)
        alerts = list((await self.db.execute(q)).scalars().all())

        # Batch-load product and warehouse names
        product_ids = {a.product_id for a in alerts if a.product_id}
        warehouse_ids = {a.warehouse_id for a in alerts if a.warehouse_id}

        products_map: dict[str, Product] = {}
        if product_ids:
            res = await self.db.execute(select(Product).where(Product.id.in_(product_ids)))
            products_map = {p.id: p for p in res.scalars().all()}

        warehouses_map: dict[str, Warehouse] = {}
        if warehouse_ids:
            res = await self.db.execute(select(Warehouse).where(Warehouse.id.in_(warehouse_ids)))
            warehouses_map = {w.id: w for w in res.scalars().all()}

        enriched = []
        for a in alerts:
            product = products_map.get(a.product_id)
            warehouse = warehouses_map.get(a.warehouse_id) if a.warehouse_id else None
            enriched.append({
                "id": a.id,
                "tenant_id": a.tenant_id,
                "product_id": a.product_id,
                "warehouse_id": a.warehouse_id,
                "batch_id": a.batch_id,
                "alert_type": a.alert_type,
                "message": a.message,
                "current_qty": a.current_qty,
                "threshold_qty": a.threshold_qty,
                "is_read": a.is_read,
                "is_resolved": a.is_resolved,
                "created_at": a.created_at,
                "resolved_at": a.resolved_at,
                "product_name": product.name if product else None,
                "product_sku": product.sku if product else None,
                "warehouse_name": warehouse.name if warehouse else None,
                "uom": product.unit_of_measure if product else None,
            })
        return enriched, total

    async def create(self, data: dict) -> StockAlert:
        obj = StockAlert(id=str(uuid.uuid4()), **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def mark_read(self, alert_id: str, tenant_id: str) -> StockAlert | None:
        result = await self.db.execute(
            select(StockAlert).where(StockAlert.id == alert_id, StockAlert.tenant_id == tenant_id)
        )
        alert = result.scalar_one_or_none()
        if alert:
            alert.is_read = True
            await self.db.flush()
        return alert

    async def resolve(self, alert_id: str, tenant_id: str) -> StockAlert | None:
        result = await self.db.execute(
            select(StockAlert).where(StockAlert.id == alert_id, StockAlert.tenant_id == tenant_id)
        )
        alert = result.scalar_one_or_none()
        if alert:
            alert.is_resolved = True
            alert.resolved_at = datetime.now(timezone.utc)
            await self.db.flush()
        return alert

    async def get_expiry_alert(
        self, tenant_id: str, batch_id: str, alert_type: str,
    ) -> StockAlert | None:
        """Find an existing unresolved expiry alert for a specific batch."""
        result = await self.db.execute(
            select(StockAlert).where(
                StockAlert.tenant_id == tenant_id,
                StockAlert.batch_id == batch_id,
                StockAlert.alert_type == alert_type,
                StockAlert.is_resolved == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def count_unread(self, tenant_id: str) -> int:
        return (await self.db.execute(
            select(func.count()).where(
                StockAlert.tenant_id == tenant_id,
                StockAlert.is_read == False,  # noqa: E712
                StockAlert.is_resolved == False,  # noqa: E712
            )
        )).scalar_one()
