"""Business logic for batch tracking."""
from __future__ import annotations

import asyncio
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
from app.db.models.purchase_order import PurchaseOrder
from app.domain.schemas import BatchOut
from app.domain.schemas.tracking import (
    BatchDispatchEntry, BatchSearchResult, BlockchainProofEntry, TraceForwardOut,
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
        batch = await self.repo.create(tenant_id, data)

        # ── Mint cNFT if product has track_on_chain=true ───────────────
        try:
            product = (await self.db.execute(
                select(Product).where(Product.id == batch.entity_id)
            )).scalar_one_or_none()

            if product and product.track_on_chain:
                batch.blockchain_status = "pending"
                await self.db.flush()

                asyncio.create_task(self._mint_batch_cnft(
                    tenant_id=tenant_id,
                    batch=batch,
                    product=product,
                ))
        except Exception:
            pass  # Non-fatal

        return batch

    async def _mint_batch_cnft(self, tenant_id: str, batch, product) -> None:
        """Background task: mint cNFT for batch via trace-service."""
        try:
            from app.clients import trace_client

            result = await trace_client.mint_batch_cnft(
                tenant_id=tenant_id,
                batch_id=batch.id,
                batch_number=batch.batch_number,
                product_name=product.name,
                product_type=product.product_type_id,
                manufacture_date=batch.manufacture_date.isoformat() if batch.manufacture_date else None,
                expiration_date=batch.expiration_date.isoformat() if batch.expiration_date else None,
            )

            if result:
                # Update batch with blockchain info — need a fresh session
                from app.db.session import get_db
                async with get_db() as session:
                    from sqlalchemy import update
                    await session.execute(
                        update(EntityBatch)
                        .where(EntityBatch.id == batch.id)
                        .values(
                            blockchain_asset_id=result.get("id"),
                            blockchain_tx_sig=result.get("blockchain_tx_signature"),
                            blockchain_status=result.get("blockchain_status", "pending"),
                        )
                    )
        except Exception:
            pass  # Best-effort

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
                anchor_hash=m.anchor_hash,
                anchor_tx_sig=m.anchor_tx_sig,
            ))
            total_dispatched += float(m.quantity)

        # ── Build blockchain proof chain ───────────────────────────────
        proof_chain = await self._build_proof_chain(tenant_id, batch, movements)

        return TraceForwardOut(
            batch=BatchOut.model_validate(batch),
            product_id=batch.entity_id,
            product_name=prod[1] if prod else None,
            dispatches=dispatches,
            total_dispatched=total_dispatched,
            total_remaining=float(batch.quantity),
            blockchain_proof=proof_chain,
        )

    async def _build_proof_chain(
        self, tenant_id: str, batch, movements: list,
    ) -> list[BlockchainProofEntry]:
        """Build the complete blockchain proof chain for a batch."""
        chain: list[BlockchainProofEntry] = []

        # 1. Batch creation anchor
        if batch.anchor_hash:
            chain.append(BlockchainProofEntry(
                event_type="batch_created",
                entity_type="batch",
                entity_id=batch.id,
                anchor_hash=batch.anchor_hash,
                anchor_tx_sig=batch.anchor_tx_sig,
                timestamp=batch.created_at,
            ))

        # 2. PO receipt that brought this batch in (purchase movements)
        po_movements = (await self.db.execute(
            select(StockMovement).where(
                StockMovement.batch_id == batch.id,
                StockMovement.tenant_id == tenant_id,
                StockMovement.movement_type.in_([MovementType.purchase]),
            ).order_by(StockMovement.created_at)
        )).scalars().all()

        for pm in po_movements:
            if pm.anchor_hash:
                chain.append(BlockchainProofEntry(
                    event_type="po_receipt",
                    entity_type="movement",
                    entity_id=pm.id,
                    anchor_hash=pm.anchor_hash,
                    anchor_tx_sig=pm.anchor_tx_sig,
                    timestamp=pm.created_at,
                ))
            # Also check the PO itself
            if pm.reference and pm.reference.startswith("PO-"):
                po = (await self.db.execute(
                    select(PurchaseOrder).where(
                        PurchaseOrder.po_number == pm.reference,
                        PurchaseOrder.tenant_id == tenant_id,
                    )
                )).scalar_one_or_none()
                if po and po.anchor_hash:
                    chain.append(BlockchainProofEntry(
                        event_type="po_anchored",
                        entity_type="purchase_order",
                        entity_id=po.id,
                        anchor_hash=po.anchor_hash,
                        anchor_tx_sig=po.anchor_tx_sig,
                        timestamp=po.created_at,
                    ))

        # 3. Dispatch movements (sale/transfer)
        for m in movements:
            if m.anchor_hash:
                chain.append(BlockchainProofEntry(
                    event_type="dispatched",
                    entity_type="movement",
                    entity_id=m.id,
                    anchor_hash=m.anchor_hash,
                    anchor_tx_sig=m.anchor_tx_sig,
                    timestamp=m.created_at,
                ))

        # 4. SO delivery anchors
        so_numbers = set()
        for m in movements:
            if m.reference and m.reference.startswith("SO:"):
                so_numbers.add(m.reference[3:])

        for so_num in so_numbers:
            so = (await self.db.execute(
                select(SalesOrder).where(
                    SalesOrder.order_number == so_num,
                    SalesOrder.tenant_id == tenant_id,
                )
            )).scalar_one_or_none()
            if so and so.anchor_hash:
                chain.append(BlockchainProofEntry(
                    event_type="so_delivered",
                    entity_type="sales_order",
                    entity_id=so.id,
                    anchor_hash=so.anchor_hash,
                    anchor_tx_sig=so.anchor_tx_sig,
                    timestamp=so.delivered_date,
                ))

        return chain
