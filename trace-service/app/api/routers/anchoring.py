"""Anchoring-as-a-Service API.

Internal endpoints that other microservices call to anchor SHA-256 hashes
on the Solana blockchain via the Memo Program.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db_session
from app.repositories.anchor_repo import AnchorRequestRepository
from app.services.anchor_service import enqueue_anchor

log = get_logger(__name__)

router = APIRouter(prefix="/anchoring", tags=["anchoring"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class AnchorHashRequest(BaseModel):
    tenant_id: str = Field(..., description="UUID of the tenant")
    source_service: str = Field(..., description="Calling service name (e.g. 'inventory-service')")
    source_entity_type: str = Field(..., description="Entity type (e.g. 'purchase_order', 'sales_order')")
    source_entity_id: str = Field(..., description="Entity ID in the source service")
    payload_hash: str = Field(..., min_length=64, max_length=64, description="Pre-computed SHA-256 hex digest")
    callback_url: str | None = Field(None, description="Webhook URL to call when anchoring completes")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra metadata to store")


class AnchorHashResponse(BaseModel):
    id: str
    payload_hash: str
    anchor_status: str
    message: str


class AnchorStatusResponse(BaseModel):
    id: str
    payload_hash: str
    anchor_status: str
    solana_tx_sig: str | None = None
    attempts: int
    last_error: str | None = None
    created_at: str
    anchored_at: str | None = None


class AnchorVerifyRequest(BaseModel):
    payload_hash: str = Field(..., min_length=64, max_length=64)


class AnchorVerifyResponse(BaseModel):
    payload_hash: str
    is_anchored: bool
    solana_tx_sig: str | None = None
    solana_verified: bool = False
    solana_status: dict[str, Any] | None = None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/hash", response_model=AnchorHashResponse, status_code=status.HTTP_201_CREATED)
async def submit_anchor(
    body: AnchorHashRequest,
    db: AsyncSession = Depends(get_db_session),
) -> AnchorHashResponse:
    """
    Submit a SHA-256 hash for anchoring on Solana via the Memo Program.
    The hash is enqueued for async processing by the ARQ worker.
    """
    repo = AnchorRequestRepository(db)

    # Idempotency: if the same hash from the same source already exists, return it
    existing = await repo.get_by_source(
        body.source_service, body.source_entity_type, body.source_entity_id
    )
    if existing:
        return AnchorHashResponse(
            id=str(existing.id),
            payload_hash=existing.payload_hash,
            anchor_status=existing.anchor_status,
            message="Anchor request already exists",
        )

    # Accept either UUID or slug — slug "default" is common from inventory-service.
    try:
        tenant_uuid = uuid.UUID(body.tenant_id)
    except ValueError:
        if body.tenant_id == "default":
            tenant_uuid = uuid.UUID("00000000-0000-0000-0000-000000000001")
        else:
            from app.db.models import Tenant
            from sqlalchemy import select
            res = await db.execute(select(Tenant).where(Tenant.slug == body.tenant_id))
            tenant = res.scalar_one_or_none()
            if tenant is None:
                raise HTTPException(status_code=404, detail=f"Tenant '{body.tenant_id}' not found")
            tenant_uuid = tenant.id

    ar = await repo.create(
        tenant_id=tenant_uuid,
        source_service=body.source_service,
        source_entity_type=body.source_entity_type,
        source_entity_id=body.source_entity_id,
        payload_hash=body.payload_hash,
        callback_url=body.callback_url,
        metadata=body.metadata,
    )
    await db.commit()

    # Enqueue for async Solana anchoring
    await enqueue_anchor_request(str(ar.id))

    log.info(
        "anchor_request_created",
        anchor_id=str(ar.id),
        source=body.source_service,
        entity=f"{body.source_entity_type}/{body.source_entity_id}",
    )

    return AnchorHashResponse(
        id=str(ar.id),
        payload_hash=ar.payload_hash,
        anchor_status=ar.anchor_status,
        message="Anchor request enqueued",
    )


@router.get("/{payload_hash}/status", response_model=AnchorStatusResponse)
async def get_anchor_status(
    payload_hash: str,
    db: AsyncSession = Depends(get_db_session),
) -> AnchorStatusResponse:
    """Get the anchoring status for a given payload hash."""
    repo = AnchorRequestRepository(db)
    ar = await repo.get_by_hash(payload_hash)
    if not ar:
        raise HTTPException(status_code=404, detail="Anchor request not found")

    return AnchorStatusResponse(
        id=str(ar.id),
        payload_hash=ar.payload_hash,
        anchor_status=ar.anchor_status,
        solana_tx_sig=ar.solana_tx_sig,
        attempts=ar.attempts,
        last_error=ar.last_error,
        created_at=ar.created_at.isoformat(),
        anchored_at=ar.anchored_at.isoformat() if ar.anchored_at else None,
    )


@router.post("/verify", response_model=AnchorVerifyResponse)
async def verify_anchor(
    body: AnchorVerifyRequest,
    db: AsyncSession = Depends(get_db_session),
) -> AnchorVerifyResponse:
    """
    Verify a hash is anchored on Solana.
    Checks DB status and optionally verifies the Solana transaction signature.
    """
    repo = AnchorRequestRepository(db)
    ar = await repo.get_by_hash(body.payload_hash)

    if not ar or ar.anchor_status != "anchored" or not ar.solana_tx_sig:
        return AnchorVerifyResponse(
            payload_hash=body.payload_hash,
            is_anchored=False,
        )

    # Verify on Solana
    from app.clients.solana_client import get_solana_client
    client = get_solana_client()
    solana_status = await client.get_signature_status(ar.solana_tx_sig)

    return AnchorVerifyResponse(
        payload_hash=body.payload_hash,
        is_anchored=True,
        solana_tx_sig=ar.solana_tx_sig,
        solana_verified=solana_status.get("err") is None,
        solana_status=solana_status,
    )


# ─── Helper ──────────────────────────────────────────────────────────────────

async def enqueue_anchor_request(anchor_request_id: str) -> None:
    """Enqueue an anchor_generic job for the ARQ worker."""
    try:
        from app.services.anchor_service import _get_arq_pool
        from app.core.settings import get_settings
        pool = await _get_arq_pool()
        await pool.enqueue_job(
            "anchor_generic",
            anchor_request_id,
            _queue_name=get_settings().ANCHOR_QUEUE_NAME,
        )
    except Exception as exc:
        log.warning("anchor_generic_enqueue_failed", anchor_id=anchor_request_id, exc=str(exc))
