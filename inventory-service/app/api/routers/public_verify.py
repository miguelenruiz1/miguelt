"""Public batch verification endpoint — NO AUTHENTICATION REQUIRED.

Allows consumers to verify batch authenticity and traceability via QR code.
Returns product info, batch dates, origin, and the complete blockchain proof chain.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.entity import Product
from app.db.models.enums import MovementType
from app.db.models.purchase_order import PurchaseOrder
from app.db.models.sales_order import SalesOrder
from app.db.models.stock import StockMovement
from app.db.models.supplier import Supplier
from app.db.models.tracking import EntityBatch
from app.db.session import get_db_session

router = APIRouter(prefix="/api/v1/public", tags=["public-verify"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ProofEntry(BaseModel):
    event_type: str
    description: str
    timestamp: datetime | None = None
    anchor_hash: str | None = None
    anchor_tx_sig: str | None = None
    solana_explorer_url: str | None = None


class BatchVerifyOut(BaseModel):
    batch_number: str
    product_name: str
    product_sku: str
    manufacture_date: date | None = None
    expiration_date: date | None = None
    expiration_status: str = "unknown"
    origin_supplier: str | None = None
    blockchain_asset_id: str | None = None
    blockchain_status: str = "none"
    anchor_hash: str | None = None
    anchor_status: str = "none"
    proof_chain: list[ProofEntry] = []
    total_events_anchored: int = 0
    verified_at: datetime


# ─── Endpoint ────────────────────────────────────────────────────────────────

@router.get("/batch/{tenant_id}/{batch_number}/verify", response_model=BatchVerifyOut)
async def verify_batch(
    tenant_id: str,
    batch_number: str,
    db: AsyncSession = Depends(get_db_session),
) -> BatchVerifyOut:
    """
    Public endpoint to verify a batch's authenticity and traceability.
    No authentication required — designed for QR code scanning by consumers.
    """
    # Find the batch
    batch = (await db.execute(
        select(EntityBatch).where(
            EntityBatch.batch_number == batch_number,
            EntityBatch.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()

    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Product info
    product = (await db.execute(
        select(Product).where(Product.id == batch.entity_id)
    )).scalar_one_or_none()

    product_name = product.name if product else "Unknown"
    product_sku = product.sku if product else "N/A"

    # Expiration status
    today = date.today()
    if not batch.expiration_date:
        exp_status = "no_expiry"
    elif batch.expiration_date < today:
        exp_status = "expired"
    elif (batch.expiration_date - today).days <= 30:
        exp_status = "expiring_soon"
    else:
        exp_status = "ok"

    # Origin supplier (from first purchase movement)
    supplier_name = None
    first_po_movement = (await db.execute(
        select(StockMovement).where(
            StockMovement.batch_id == batch.id,
            StockMovement.tenant_id == tenant_id,
            StockMovement.movement_type == MovementType.purchase,
        ).order_by(StockMovement.created_at).limit(1)
    )).scalar_one_or_none()

    if first_po_movement and first_po_movement.reference:
        po = (await db.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.po_number == first_po_movement.reference,
                PurchaseOrder.tenant_id == tenant_id,
            )
        )).scalar_one_or_none()
        if po:
            supplier = (await db.execute(
                select(Supplier.name).where(Supplier.id == po.supplier_id)
            )).scalar_one_or_none()
            supplier_name = supplier

    # Build proof chain
    proof_chain: list[ProofEntry] = []

    # 1. Batch creation
    if batch.anchor_hash:
        proof_chain.append(ProofEntry(
            event_type="batch_created",
            description=f"Lote {batch.batch_number} registrado en blockchain",
            timestamp=batch.created_at,
            anchor_hash=batch.anchor_hash,
            anchor_tx_sig=batch.anchor_tx_sig,
            solana_explorer_url=_explorer_url(batch.anchor_tx_sig),
        ))

    # 2. PO receipts
    po_movements = list((await db.execute(
        select(StockMovement).where(
            StockMovement.batch_id == batch.id,
            StockMovement.tenant_id == tenant_id,
            StockMovement.movement_type == MovementType.purchase,
        ).order_by(StockMovement.created_at)
    )).scalars().all())

    for pm in po_movements:
        if pm.anchor_hash:
            proof_chain.append(ProofEntry(
                event_type="goods_received",
                description=f"Mercancia recibida — ref: {pm.reference or 'N/A'}",
                timestamp=pm.created_at,
                anchor_hash=pm.anchor_hash,
                anchor_tx_sig=pm.anchor_tx_sig,
                solana_explorer_url=_explorer_url(pm.anchor_tx_sig),
            ))

    # 3. PO anchor
    if first_po_movement and first_po_movement.reference:
        po = (await db.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.po_number == first_po_movement.reference,
                PurchaseOrder.tenant_id == tenant_id,
            )
        )).scalar_one_or_none()
        if po and po.anchor_hash:
            proof_chain.append(ProofEntry(
                event_type="po_verified",
                description=f"Orden de compra {po.po_number} verificada en blockchain",
                timestamp=po.created_at,
                anchor_hash=po.anchor_hash,
                anchor_tx_sig=po.anchor_tx_sig,
                solana_explorer_url=_explorer_url(po.anchor_tx_sig),
            ))

    # 4. Dispatch movements (sale)
    sale_movements = list((await db.execute(
        select(StockMovement).where(
            StockMovement.batch_id == batch.id,
            StockMovement.tenant_id == tenant_id,
            StockMovement.movement_type == MovementType.sale,
        ).order_by(StockMovement.created_at)
    )).scalars().all())

    for sm in sale_movements:
        if sm.anchor_hash:
            proof_chain.append(ProofEntry(
                event_type="dispatched",
                description=f"Despacho registrado — ref: {sm.reference or 'N/A'}",
                timestamp=sm.created_at,
                anchor_hash=sm.anchor_hash,
                anchor_tx_sig=sm.anchor_tx_sig,
                solana_explorer_url=_explorer_url(sm.anchor_tx_sig),
            ))

    # 5. SO delivery anchors
    so_numbers = set()
    for sm in sale_movements:
        if sm.reference and sm.reference.startswith("SO:"):
            so_numbers.add(sm.reference[3:])

    for so_num in so_numbers:
        so = (await db.execute(
            select(SalesOrder).where(
                SalesOrder.order_number == so_num,
                SalesOrder.tenant_id == tenant_id,
            )
        )).scalar_one_or_none()
        if so and so.anchor_hash:
            proof_chain.append(ProofEntry(
                event_type="delivered",
                description=f"Entrega al cliente verificada — {so.order_number}",
                timestamp=so.delivered_date,
                anchor_hash=so.anchor_hash,
                anchor_tx_sig=so.anchor_tx_sig,
                solana_explorer_url=_explorer_url(so.anchor_tx_sig),
            ))

    # Sort proof chain chronologically
    proof_chain.sort(key=lambda e: e.timestamp or datetime.min)

    return BatchVerifyOut(
        batch_number=batch.batch_number,
        product_name=product_name,
        product_sku=product_sku,
        manufacture_date=batch.manufacture_date,
        expiration_date=batch.expiration_date,
        expiration_status=exp_status,
        origin_supplier=supplier_name,
        blockchain_asset_id=batch.blockchain_asset_id,
        blockchain_status=batch.blockchain_status,
        anchor_hash=batch.anchor_hash,
        anchor_status=batch.anchor_status,
        proof_chain=proof_chain,
        total_events_anchored=len([e for e in proof_chain if e.anchor_tx_sig]),
        verified_at=datetime.utcnow(),
    )


def _explorer_url(tx_sig: str | None) -> str | None:
    """Generate Solana explorer URL for a transaction signature."""
    if not tx_sig:
        return None
    if tx_sig.startswith("SIM_"):
        return f"https://explorer.solana.com/tx/{tx_sig}?cluster=devnet"
    return f"https://explorer.solana.com/tx/{tx_sig}"
