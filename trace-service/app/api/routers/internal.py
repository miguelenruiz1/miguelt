"""Internal S2S endpoints — called by other services (inventory-service, etc.)

Auth: X-Service-Token header (shared secret, NOT user JWT).
These endpoints bypass tenant middleware since tenant_id comes in the request body.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_service_token
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.services.custody_service import CustodyService
from app.services.workflow_service import WorkflowService

log = get_logger(__name__)

router = APIRouter(prefix="/internal", tags=["internal-s2s"])


# ─── Schemas ────────────────────────────────────────────────────────────────

class POReceiptRequest(BaseModel):
    po_id: str
    entity_id: str
    batch_id: str | None = None
    warehouse_id: str
    tenant_id: str
    quantity: int = Field(..., gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class POReceiptResponse(BaseModel):
    asset_id: str
    state: str
    wallet: str
    event_hash: str


class SOHandoffRequest(BaseModel):
    so_id: str
    asset_ids: list[str] = Field(..., min_length=1)
    to_wallet_id: str
    tracking_number: str | None = None
    tenant_id: str


class SOHandoffResponse(BaseModel):
    handoffs: list[dict[str, str]]
    errors: list[dict[str, str]]


# ─── POST /internal/assets/from-po-receipt ──────────────────────────────────

@router.post(
    "/assets/from-po-receipt",
    response_model=POReceiptResponse,
    status_code=201,
    dependencies=[Depends(verify_service_token)],
)
async def create_asset_from_po_receipt(
    body: POReceiptRequest,
    db: AsyncSession = Depends(get_db_session),
) -> POReceiptResponse:
    """
    Called by inventory-service when a PO is received.
    Creates an Asset in trace-service with initial workflow state,
    custodian = the receiving warehouse's wallet.
    """
    tenant_id = uuid.UUID(body.tenant_id)

    # Find a wallet for the receiving warehouse.
    # Convention: wallet.tags should contain "warehouse:{warehouse_id}"
    # Fallback: first active wallet for this tenant.
    from app.repositories.registry_repo import RegistryRepository
    registry = RegistryRepository(db)
    wallet = await registry.find_by_tag(
        tenant_id, f"warehouse:{body.warehouse_id}"
    )
    if not wallet:
        # Fallback: use first active wallet for tenant
        wallets, _ = await registry.list(
            tenant_id=tenant_id, status="active", limit=1
        )
        wallet = wallets[0] if wallets else None
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No active wallet found for tenant '{body.tenant_id}'. "
                   f"Register a wallet first.",
        )

    # Build metadata for the asset
    asset_metadata: dict[str, Any] = {
        "source": "inventory-service",
        "po_id": body.po_id,
        "entity_id": body.entity_id,
        "quantity": body.quantity,
        "warehouse_id": body.warehouse_id,
        **body.metadata,
    }
    if body.batch_id:
        asset_metadata["batch_id"] = body.batch_id

    # Create asset via custody service (uses workflow engine for initial state)
    svc = CustodyService(db, tenant_id)
    placeholder_mint = f"inv_{body.entity_id}_{uuid.uuid4().hex[:8]}"

    asset, event = await svc.create_asset(
        asset_mint=placeholder_mint,
        product_type="inventory_product",
        metadata=asset_metadata,
        initial_custodian_wallet=wallet.wallet_pubkey,
    )
    await db.commit()

    log.info(
        "asset_created_from_po",
        asset_id=str(asset.id),
        po_id=body.po_id,
        entity_id=body.entity_id,
        tenant_id=body.tenant_id,
    )

    return POReceiptResponse(
        asset_id=str(asset.id),
        state=asset.state,
        wallet=wallet.wallet_pubkey,
        event_hash=event.event_hash,
    )


# ─── POST /internal/assets/handoff-from-so ─────────────────────────────────

@router.post(
    "/assets/handoff-from-so",
    response_model=SOHandoffResponse,
    dependencies=[Depends(verify_service_token)],
)
async def handoff_assets_from_so(
    body: SOHandoffRequest,
    db: AsyncSession = Depends(get_db_session),
) -> SOHandoffResponse:
    """
    Called by inventory-service when a SO is shipped.
    Performs handoff on each asset to the destination wallet.
    """
    from app.domain.schemas import HandoffRequest

    tenant_id = uuid.UUID(body.tenant_id)
    svc = CustodyService(db, tenant_id)

    handoffs: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for asset_id_str in body.asset_ids:
        try:
            asset_id = uuid.UUID(asset_id_str)
            req = HandoffRequest(
                to_wallet=body.to_wallet_id,
                data={
                    "source": "inventory-service",
                    "so_id": body.so_id,
                    "tracking_number": body.tracking_number,
                },
            )
            asset, event = await svc.handoff(asset_id, req)
            handoffs.append({
                "asset_id": asset_id_str,
                "new_state": asset.state,
                "event_hash": event.event_hash,
            })
        except Exception as exc:
            log.warning(
                "handoff_from_so_failed",
                asset_id=asset_id_str,
                so_id=body.so_id,
                error=str(exc),
            )
            errors.append({
                "asset_id": asset_id_str,
                "error": str(exc),
            })

    if handoffs:
        await db.commit()

    log.info(
        "handoff_from_so_complete",
        so_id=body.so_id,
        total=len(body.asset_ids),
        success=len(handoffs),
        errors=len(errors),
    )

    return SOHandoffResponse(handoffs=handoffs, errors=errors)
