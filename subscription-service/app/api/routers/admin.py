"""Admin/metrics router."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.session import get_db_session
from app.domain.schemas import OverviewMetrics
from app.repositories.unmatched_payment_repo import UnmatchedPaymentRepository
from app.services.dunning_service import dunning_check
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _require_superuser(current_user: CurrentUser) -> dict:
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return current_user


def _svc(db: Annotated[AsyncSession, Depends(get_db_session)]) -> MetricsService:
    return MetricsService(db)


@router.get("/metrics/overview", response_model=OverviewMetrics)
async def get_overview(
    _: Annotated[dict, Depends(_require_superuser)],
    svc: MetricsService = Depends(_svc),
):
    return await svc.get_overview()


# ─── FASE2: Dunning manual trigger ───────────────────────────────────────────

@router.post("/dunning/run", summary="Trigger dunning pass now (superuser)")
async def trigger_dunning_run(
    _: Annotated[dict, Depends(_require_superuser)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    return await dunning_check(db)


# ─── FASE2: Webhook replay for debugging ─────────────────────────────────────

class WebhookReplayRequest(BaseModel):
    transaction_id: str
    reference: str
    tenant_id: str
    invoice_id: str
    amount_in_cents: int = 0
    status_code: str = "APPROVED"


@router.post("/webhooks/wompi/replay", summary="Simulate a Wompi APPROVED event (superuser)")
async def replay_wompi_webhook(
    body: WebhookReplayRequest,
    _: Annotated[dict, Depends(_require_superuser)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Bypass signature verification — for debugging reconciliation only."""
    from app.api.deps import get_redis, get_http_client
    from app.api.routers.webhooks import process_successful_payment

    if body.status_code.upper() != "APPROVED":
        return {"skipped": True, "reason": f"status={body.status_code}"}

    redis = get_redis()
    http = get_http_client()
    await process_successful_payment(
        db=db,
        invoice_id=body.invoice_id,
        gateway_slug="wompi",
        gateway_tx_id=body.transaction_id,
        redis=redis,
        http_client=http,
    )
    return {"replayed": True, "invoice_id": body.invoice_id, "tx_id": body.transaction_id}


# ─── FASE2: Unmatched payments ledger ────────────────────────────────────────

@router.get("/unmatched-payments", summary="List unresolved unmatched payments")
async def list_unmatched_payments(
    _: Annotated[dict, Depends(_require_superuser)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = 100,
) -> list[dict]:
    repo = UnmatchedPaymentRepository(db)
    rows = await repo.list_unresolved(limit=limit)
    return [
        {
            "id": r.id,
            "gateway_slug": r.gateway_slug,
            "gateway_tx_id": r.gateway_tx_id,
            "reference": r.reference,
            "amount": float(r.amount) if r.amount is not None else None,
            "currency": r.currency,
            "received_at": r.received_at.isoformat() if r.received_at else None,
            "notes": r.notes,
        }
        for r in rows
    ]
