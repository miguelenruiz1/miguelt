"""WM service: mass bin creation (SAP LS10) and empty-bin / capacity report."""
from __future__ import annotations

import itertools
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StockLevel, WarehouseLocation
from app.domain.schemas.wm import (
    BinBulkCreate, BinBulkResult, EmptyBinReport, EmptyBinReportItem,
)

# Hard cap to avoid a runaway mass-creation request.
MAX_BULK_BINS = 4096


class WMService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _generate_codes(self, body: BinBulkCreate) -> list[str]:
        ranges = []
        for seg in body.segments:
            vals = [str(v).zfill(seg.pad) for v in range(seg.start, seg.end + 1, seg.step)]
            ranges.append(vals)
        codes = []
        for combo in itertools.product(*ranges):
            code = body.separator.join(combo)
            if body.prefix:
                code = f"{body.prefix}{body.separator}{code}" if body.separator else f"{body.prefix}{code}"
            codes.append(code)
        return codes

    async def bulk_create_bins(self, tenant_id: str, body: BinBulkCreate, user_id: str | None) -> BinBulkResult:
        codes = self._generate_codes(body)
        if len(codes) > MAX_BULK_BINS:
            from app.core.errors import ValidationError
            raise ValidationError(
                f"La combinación genera {len(codes)} ubicaciones (máx {MAX_BULK_BINS}). "
                f"Reducí el rango de los segmentos."
            )

        # Existing codes in this warehouse → skip (idempotent).
        existing = set((await self.db.execute(
            select(WarehouseLocation.code).where(
                WarehouseLocation.tenant_id == tenant_id,
                WarehouseLocation.warehouse_id == body.warehouse_id,
            )
        )).scalars().all())

        created = 0
        skipped = 0
        for idx, code in enumerate(codes):
            if code in existing:
                skipped += 1
                continue
            self.db.add(WarehouseLocation(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                warehouse_id=body.warehouse_id,
                name=code,
                code=code,
                location_type="bin",
                location_kind=body.location_kind,
                storage_type_id=body.storage_type_id,
                storage_section_id=body.storage_section_id,
                height_m=body.height_m,
                max_weight_kg=body.max_weight_kg,
                max_volume_m3=body.max_volume_m3,
                max_capacity=body.max_capacity,
                sort_order=idx,
                created_by=user_id,
            ))
            created += 1
        await self.db.flush()
        return BinBulkResult(created=created, skipped=skipped, sample_codes=codes[:10])

    async def empty_bin_report(
        self, tenant_id: str, warehouse_id: str, storage_type_id: str | None = None,
    ) -> EmptyBinReport:
        # All physical bins of the warehouse.
        q = select(WarehouseLocation).where(
            WarehouseLocation.tenant_id == tenant_id,
            WarehouseLocation.warehouse_id == warehouse_id,
            WarehouseLocation.location_kind == "physical",
            WarehouseLocation.is_active.is_(True),
        )
        if storage_type_id:
            q = q.where(WarehouseLocation.storage_type_id == storage_type_id)
        bins = list((await self.db.execute(q.order_by(WarehouseLocation.sort_order))).scalars().all())

        # Location ids that currently hold stock (qty_on_hand > 0).
        occupied = set((await self.db.execute(
            select(StockLevel.location_id).where(
                StockLevel.tenant_id == tenant_id,
                StockLevel.location_id.is_not(None),
                StockLevel.qty_on_hand > Decimal("0"),
            ).distinct()
        )).scalars().all())

        empties = [b for b in bins if b.id not in occupied]
        total = len(bins)
        occ = total - len(empties)
        return EmptyBinReport(
            warehouse_id=warehouse_id,
            total_bins=total,
            empty_bins=len(empties),
            occupancy_pct=round((occ / total * 100), 1) if total else 0.0,
            items=[
                EmptyBinReportItem(
                    location_id=b.id, code=b.code, name=b.name,
                    storage_type_id=b.storage_type_id,
                    storage_section_id=b.storage_section_id,
                )
                for b in empties
            ],
        )
