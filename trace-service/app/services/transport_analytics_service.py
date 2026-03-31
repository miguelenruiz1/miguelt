"""Transport and logistics KPIs computed from shipment_documents and custody_events."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, text, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ShipmentDocument, CustodyEvent, Asset


class TransportAnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def transport_kpis(
        self,
        tenant_id: uuid.UUID,
        period: str = "month",
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        tid = str(tenant_id)
        filters = [ShipmentDocument.tenant_id == tid]
        if date_from:
            filters.append(ShipmentDocument.created_at >= date_from)
        if date_to:
            filters.append(ShipmentDocument.created_at <= date_to)

        on_time = await self._on_time_delivery(tid, filters)
        avg_transit = await self._avg_transit_days(tid, filters)
        by_status = await self._shipments_by_status(tid, filters)
        by_period = await self._deliveries_by_period(tid, period, filters)
        avg_events = await self._avg_events_per_asset(tenant_id)
        carriers = await self._top_carriers(tid, filters)
        total_cost = await self._total_logistics_cost(tid, filters)

        return {
            "on_time_delivery_pct": on_time,
            "avg_transit_days": avg_transit,
            "shipments_by_status": by_status,
            "deliveries_by_period": by_period,
            "avg_events_per_asset": avg_events,
            "top_carriers": carriers,
            "total_logistics_cost": total_cost,
        }

    async def _on_time_delivery(self, tid: str, filters: list) -> float | None:
        result = await self._db.execute(
            select(
                func.count().filter(
                    ShipmentDocument.actual_arrival <= ShipmentDocument.estimated_arrival
                ),
                func.count(),
            )
            .where(
                ShipmentDocument.tenant_id == tid,
                ShipmentDocument.status == "delivered",
                ShipmentDocument.actual_arrival.is_not(None),
                ShipmentDocument.estimated_arrival.is_not(None),
            )
        )
        row = result.first()
        if not row or row[1] == 0:
            return None
        return round(row[0] * 100.0 / row[1], 1)

    async def _avg_transit_days(self, tid: str, filters: list) -> float | None:
        result = await self._db.execute(
            select(
                func.avg(
                    extract("epoch", ShipmentDocument.actual_arrival - ShipmentDocument.shipped_date) / 86400
                )
            ).where(
                ShipmentDocument.tenant_id == tid,
                ShipmentDocument.actual_arrival.is_not(None),
                ShipmentDocument.shipped_date.is_not(None),
            )
        )
        val = result.scalar_one_or_none()
        return round(float(val), 1) if val else None

    async def _shipments_by_status(self, tid: str, filters: list) -> dict[str, int]:
        result = await self._db.execute(
            select(ShipmentDocument.status, func.count())
            .where(ShipmentDocument.tenant_id == tid)
            .group_by(ShipmentDocument.status)
        )
        return {row[0]: row[1] for row in result.all()}

    async def _deliveries_by_period(self, tid: str, period: str, filters: list) -> list[dict]:
        trunc = func.date_trunc(period, ShipmentDocument.actual_arrival)
        result = await self._db.execute(
            select(trunc.label("period"), func.count().label("count"))
            .where(
                ShipmentDocument.tenant_id == tid,
                ShipmentDocument.status == "delivered",
                ShipmentDocument.actual_arrival.is_not(None),
            )
            .group_by(trunc)
            .order_by(trunc)
        )
        return [{"period": row[0].isoformat() if row[0] else None, "count": row[1]} for row in result.all()]

    async def _avg_events_per_asset(self, tenant_id: uuid.UUID) -> float | None:
        subq = (
            select(func.count(CustodyEvent.id).label("cnt"))
            .join(Asset, CustodyEvent.asset_id == Asset.id)
            .where(Asset.tenant_id == tenant_id)
            .group_by(CustodyEvent.asset_id)
            .subquery()
        )
        result = await self._db.execute(select(func.avg(subq.c.cnt)))
        val = result.scalar_one_or_none()
        return round(float(val), 1) if val else None

    async def _top_carriers(self, tid: str, filters: list, limit: int = 10) -> list[dict]:
        result = await self._db.execute(
            select(ShipmentDocument.carrier_name, func.count().label("shipments"))
            .where(
                ShipmentDocument.tenant_id == tid,
                ShipmentDocument.carrier_name.is_not(None),
            )
            .group_by(ShipmentDocument.carrier_name)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [{"carrier": row[0], "shipments": row[1]} for row in result.all()]

    async def _total_logistics_cost(self, tid: str, filters: list) -> dict:
        result = await self._db.execute(
            select(
                func.coalesce(func.sum(ShipmentDocument.freight_cost), 0),
                func.coalesce(func.sum(ShipmentDocument.insurance_cost), 0),
                func.coalesce(func.sum(ShipmentDocument.handling_cost), 0),
                func.coalesce(func.sum(ShipmentDocument.customs_cost), 0),
                func.coalesce(func.sum(ShipmentDocument.other_costs), 0),
                func.coalesce(func.sum(ShipmentDocument.total_logistics_cost), 0),
            ).where(ShipmentDocument.tenant_id == tid)
        )
        row = result.first()
        return {
            "freight": float(row[0]),
            "insurance": float(row[1]),
            "handling": float(row[2]),
            "customs": float(row[3]),
            "other": float(row[4]),
            "total": float(row[5]),
        }
