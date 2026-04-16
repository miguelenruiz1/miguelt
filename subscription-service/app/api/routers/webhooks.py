"""Payment webhook endpoints — PUBLIC (verified by signature)."""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx
import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_http_client, get_redis
from app.core.settings import get_settings
from app.db.models import (
    EventType,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.db.session import get_db_session
from app.repositories.event_repo import EventRepository
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.payment_repo import PaymentGatewayRepository
from app.repositories.subscription_repo import SubscriptionRepository

router = APIRouter(prefix="/api/v1/payments/webhooks", tags=["webhooks"])
log = structlog.get_logger(__name__)


# ─── Shared helper ────────────────────────────────────────────────────────────

async def process_successful_payment(
    db: AsyncSession,
    invoice_id: str,
    gateway_slug: str,
    gateway_tx_id: str,
    redis: aioredis.Redis,
    http_client: httpx.AsyncClient,
) -> None:
    """
    Shared logic for a successful payment:
    1. Mark invoice as paid (with gateway_tx_id, gateway_slug)
    2. Activate / renew subscription
    3. Invalidate Redis cache
    4. Enqueue confirmation email via HTTP to user-service
    """
    settings = get_settings()
    invoice_repo = InvoiceRepository(db)
    sub_repo = SubscriptionRepository(db)
    event_repo = EventRepository(db)

    invoice = None
    if invoice_id:
        invoice = await invoice_repo.get_by_id(invoice_id)

    if not invoice:
        # Try match by gateway_tx_id (idempotent replay against existing paid invoice)
        from sqlalchemy import select
        from app.db.models import Invoice
        res = await db.execute(
            select(Invoice).where(Invoice.gateway_tx_id == gateway_tx_id)
        )
        invoice = res.scalar_one_or_none()

    if not invoice:
        # Record in unmatched ledger for manual reconciliation
        from app.repositories.unmatched_payment_repo import UnmatchedPaymentRepository
        um_repo = UnmatchedPaymentRepository(db)
        await um_repo.record(
            gateway_slug=gateway_slug,
            gateway_tx_id=gateway_tx_id,
            reference=invoice_id,
            amount=None,
            currency=None,
            raw_payload=None,
            notes="Webhook received but no matching invoice",
        )
        log.warning("webhook_invoice_not_found", invoice_id=invoice_id, gateway=gateway_slug, tx_id=gateway_tx_id)
        return

    # Idempotency: already paid with same gateway_tx_id
    if invoice.status == InvoiceStatus.paid:
        log.info("webhook_invoice_already_paid", invoice_id=invoice.id, gateway_tx_id=gateway_tx_id)
        return

    # Mark invoice paid
    now = datetime.now(timezone.utc)
    update_data: dict[str, Any] = {
        "status": InvoiceStatus.paid,
        "paid_at": now,
        "gateway_tx_id": gateway_tx_id,
        "gateway_slug": gateway_slug,
    }
    await invoice_repo.update(invoice, update_data)

    # Activate / renew subscription
    sub = await sub_repo.get_by_id(invoice.subscription_id)
    was_past_due = bool(sub and sub.status == SubscriptionStatus.past_due)
    if sub:
        new_period_start = now
        new_period_end = now + timedelta(days=30)
        await sub_repo.update(sub, {
            "status": SubscriptionStatus.active,
            "current_period_start": new_period_start,
            "current_period_end": new_period_end,
        })
        if was_past_due:
            log.info("subscription_reactivated_from_past_due", tenant_id=sub.tenant_id)

        await event_repo.create(
            subscription_id=sub.id,
            tenant_id=sub.tenant_id,
            event_type=EventType.payment_received,
            data={
                "invoice_id": invoice_id,
                "invoice_number": invoice.invoice_number,
                "amount": float(invoice.amount),
                "gateway": gateway_slug,
                "gateway_tx_id": gateway_tx_id,
            },
            performed_by="webhook",
        )

        # Invalidate Redis cache
        cache_keys = [
            f"sub_svc:me:{sub.tenant_id}",
            f"module:{sub.tenant_id}:*",
        ]
        for key in cache_keys:
            try:
                if "*" in key:
                    async for k in redis.scan_iter(match=key):
                        await redis.delete(k)
                else:
                    await redis.delete(key)
            except Exception as exc:
                log.warning("redis_cache_invalidation_failed", key=key, error=str(exc))

        # Send confirmation email via user-service (best-effort)
        try:
            await http_client.post(
                f"{settings.USER_SERVICE_URL}/api/v1/notifications/email",
                json={
                    "tenant_id": sub.tenant_id,
                    "template": "payment_confirmation",
                    "data": {
                        "invoice_number": invoice.invoice_number,
                        "amount": float(invoice.amount),
                        "currency": invoice.currency,
                        "gateway": gateway_slug,
                        "paid_at": now.isoformat(),
                    },
                },
                timeout=5.0,
            )
        except httpx.RequestError as exc:
            log.warning("email_notification_failed", tenant_id=sub.tenant_id, error=str(exc))

        # FASE2: Send receipt PDF via Resend (best effort)
        try:
            from decimal import Decimal as _Dec
            from app.services.email_client import get_email_client
            from app.services.invoice_pdf_service import (
                _fmt_money,
                render_invoice_pdf,
                render_jinja,
            )

            # Resolve owner email via user-service S2S
            owner_email = None
            owner_name = None
            try:
                resp = await http_client.get(
                    f"{settings.USER_SERVICE_URL}/api/v1/internal/tenant-owner-email/{sub.tenant_id}",
                    headers={"X-Service-Token": settings.S2S_SERVICE_TOKEN},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    owner_email = data.get("email")
                    owner_name = data.get("full_name") or owner_email
            except httpx.RequestError:
                pass

            if owner_email:
                try:
                    pdf_bytes = await render_invoice_pdf(db, invoice.id, app_url=settings.APP_URL)
                except Exception:
                    pdf_bytes = None
                total_fmt = _fmt_money(_Dec(str(invoice.amount or 0)), invoice.currency or "COP")
                html = render_jinja(
                    "receipt.html",
                    customer_name=owner_name or owner_email,
                    invoice={
                        "invoice_number": invoice.invoice_number,
                        "total_fmt": total_fmt,
                        "currency": invoice.currency or "COP",
                    },
                    gateway_tx_id=gateway_tx_id,
                )
                client = get_email_client()
                await client.send(
                    tenant_id=sub.tenant_id,
                    to=owner_email,
                    subject=f"Recibo de pago — {invoice.invoice_number}",
                    html_body=html,
                    attachments=(
                        [{"filename": f"{invoice.invoice_number}.pdf", "content": pdf_bytes}]
                        if pdf_bytes else []
                    ),
                )
        except Exception:
            log.exception("receipt_email_failed", invoice_id=invoice.id)

    log.info(
        "payment_processed",
        invoice_id=invoice_id,
        gateway=gateway_slug,
        gateway_tx_id=gateway_tx_id,
    )


# ─── Wompi webhook ───────────────────────────────────────────────────────────

@router.post("/wompi", summary="Wompi payment notification")
async def wompi_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis),
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> dict:
    """
    Wompi sends JSON events. Verify SHA256 signature using events_secret.
    """
    body = await request.json()
    event_type = body.get("event", "")
    signature_header = request.headers.get("X-Event-Checksum", "")

    data = body.get("data", {})
    transaction = data.get("transaction", {})
    tx_id = str(transaction.get("id", ""))
    tx_status = str(transaction.get("status", ""))
    tx_amount = transaction.get("amount_in_cents", 0)
    tx_reference = str(transaction.get("reference", ""))
    tx_currency = str(transaction.get("currency", ""))

    # Reference format: "{tenant_id}:{invoice_id}"
    parts = tx_reference.split(":", 1)
    if len(parts) != 2:
        log.warning("wompi_invalid_reference", reference=tx_reference)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reference format")

    tenant_id, invoice_id = parts

    # Verify signature
    payment_repo = PaymentGatewayRepository(db)
    gateway_config = await payment_repo.get(tenant_id, "wompi")
    if not gateway_config:
        log.warning("wompi_webhook_no_config", tenant_id=tenant_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wompi not configured")

    events_secret = gateway_config.credentials.get("events_secret", "")

    # Wompi signature: SHA256(concat of tx properties + timestamp + events_secret)
    timestamp = str(body.get("timestamp", ""))
    checksum_string = f"{tx_id}{tx_status}{tx_amount}{tx_reference}{tx_currency}{timestamp}{events_secret}"
    expected_checksum = hashlib.sha256(checksum_string.encode("utf-8")).hexdigest()

    # CRITICAL: signature is REQUIRED. Previously the check was
    # `if signature_header and not hmac.compare_digest(...)` which let an
    # attacker bypass the signature by simply omitting the X-Event-Checksum
    # header — they could then mark any invoice as paid.
    if not signature_header or not hmac.compare_digest(expected_checksum, signature_header):
        log.warning("wompi_invalid_signature", tenant_id=tenant_id, tx_id=tx_id, has_header=bool(signature_header))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing signature")

    log.info(
        "wompi_webhook_received",
        event=event_type,
        tx_id=tx_id,
        tx_status=tx_status,
        invoice_id=invoice_id,
        tenant_id=tenant_id,
    )

    if event_type == "transaction.updated" and tx_status == "APPROVED":
        await process_successful_payment(
            db=db,
            invoice_id=invoice_id,
            gateway_slug="wompi",
            gateway_tx_id=tx_id,
            redis=redis,
            http_client=http_client,
        )

    return {"status": "ok", "tx_id": tx_id}
