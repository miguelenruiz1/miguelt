"""Blockchain anchoring status, verification, and webhook endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.db.session import get_db_session
from app.core.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/api/v1/blockchain", tags=["blockchain"])

_ENTITY_MAP = {
    "purchase_order": "purchase_orders",
    "sales_order": "sales_orders",
    "batch": "entity_batches",
    "movement": "stock_movements",
}


# ─── Schemas ─────────────────────────────────────────────────────────────────

class AnchorStatusOut(BaseModel):
    entity_type: str
    entity_id: str
    anchor_hash: str | None = None
    anchor_status: str = "none"
    anchor_tx_sig: str | None = None
    anchored_at: str | None = None


class WebhookPayload(BaseModel):
    payload_hash: str
    solana_tx_sig: str
    anchor_status: str = "anchored"


class VerifyOut(BaseModel):
    entity_type: str
    entity_id: str
    anchor_hash: str | None = None
    is_anchored: bool = False
    solana_tx_sig: str | None = None
    solana_verified: bool = False
    solana_status: dict[str, Any] | None = None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/status/{entity_type}/{entity_id}", response_model=AnchorStatusOut)
async def get_anchor_status(
    entity_type: str,
    entity_id: str,
    _user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
) -> AnchorStatusOut:
    """Get the blockchain anchoring status for a given entity."""
    table = _ENTITY_MAP.get(entity_type)
    if not table:
        raise HTTPException(status_code=400, detail=f"Unknown entity_type: {entity_type}")

    from sqlalchemy import text
    row = (await db.execute(
        text(f"SELECT anchor_hash, anchor_status, anchor_tx_sig, anchored_at FROM {table} WHERE id = :id"),
        {"id": entity_id},
    )).first()

    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")

    return AnchorStatusOut(
        entity_type=entity_type,
        entity_id=entity_id,
        anchor_hash=row[0],
        anchor_status=row[1] or "none",
        anchor_tx_sig=row[2],
        anchored_at=row[3].isoformat() if row[3] else None,
    )


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def anchor_webhook(
    body: WebhookPayload,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """
    Callback from trace-service when a hash is anchored on Solana.
    Updates the corresponding entity's anchor fields.
    """
    from sqlalchemy import text

    now = datetime.now(tz=timezone.utc)
    updated = False

    for table in _ENTITY_MAP.values():
        result = await db.execute(
            text(
                f"UPDATE {table} SET anchor_status = 'anchored', "
                f"anchor_tx_sig = :tx_sig, anchored_at = :now "
                f"WHERE anchor_hash = :hash AND anchor_status = 'pending'"
            ),
            {"tx_sig": body.solana_tx_sig, "now": now, "hash": body.payload_hash},
        )
        if result.rowcount > 0:
            updated = True

    if updated:
        await db.commit()
        log.info("anchor_webhook_applied", hash=body.payload_hash[:16], tx_sig=body.solana_tx_sig[:20])
        return {"status": "updated"}

    log.warning("anchor_webhook_no_match", hash=body.payload_hash[:16])
    return {"status": "no_match"}


@router.get("/verify/{entity_type}/{entity_id}", response_model=VerifyOut)
async def verify_anchor(
    entity_type: str,
    entity_id: str,
    _user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
) -> VerifyOut:
    """
    Verify an entity's anchor hash on Solana via trace-service.
    """
    table = _ENTITY_MAP.get(entity_type)
    if not table:
        raise HTTPException(status_code=400, detail=f"Unknown entity_type: {entity_type}")

    from sqlalchemy import text
    row = (await db.execute(
        text(f"SELECT anchor_hash, anchor_status, anchor_tx_sig FROM {table} WHERE id = :id"),
        {"id": entity_id},
    )).first()

    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")

    anchor_hash, anchor_status, anchor_tx_sig = row[0], row[1], row[2]

    if not anchor_hash or anchor_status == "none":
        return VerifyOut(entity_type=entity_type, entity_id=entity_id)

    # Query trace-service for on-chain verification
    from app.clients import trace_client
    verify_result = await trace_client.verify_anchor(anchor_hash)

    if verify_result:
        return VerifyOut(
            entity_type=entity_type,
            entity_id=entity_id,
            anchor_hash=anchor_hash,
            is_anchored=verify_result.get("is_anchored", False),
            solana_tx_sig=verify_result.get("solana_tx_sig"),
            solana_verified=verify_result.get("solana_verified", False),
            solana_status=verify_result.get("solana_status"),
        )

    return VerifyOut(
        entity_type=entity_type,
        entity_id=entity_id,
        anchor_hash=anchor_hash,
        is_anchored=anchor_status == "anchored",
        solana_tx_sig=anchor_tx_sig,
    )
