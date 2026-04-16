"""Invoice-level operations for FASE2 billing completeness.

- send_invoice: generate PDF + email to tenant owner via Resend.
- issue_credit_note: create refund credit_note row (negative amount) and
  optionally void the original invoice.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.db.models import (
    EventType,
    Invoice,
    InvoiceStatus,
)
from app.repositories.event_repo import EventRepository
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.subscription_repo import SubscriptionRepository
from app.services.email_client import get_email_client
from app.services.invoice_pdf_service import (
    _fmt_money,
    build_invoice_context,
    render_invoice_pdf,
    render_jinja,
)

log = structlog.get_logger(__name__)


async def _fetch_tenant_owner(tenant_id: str) -> dict | None:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            resp = await c.get(
                f"{settings.USER_SERVICE_URL}/api/v1/internal/tenant-owner-email/{tenant_id}",
                headers={"X-Service-Token": settings.S2S_SERVICE_TOKEN},
            )
            if resp.status_code == 200:
                return resp.json()
    except httpx.RequestError as exc:
        log.warning("tenant_owner_fetch_failed", tenant_id=tenant_id, error=str(exc))
    return None


async def send_invoice(
    db: AsyncSession,
    tenant_id: str,
    invoice_id: str,
    performed_by: str,
    method: str = "manual",
) -> dict[str, Any]:
    """Render PDF + email invoice to tenant owner. Persists 'invoice_sent' event."""
    invoice_repo = InvoiceRepository(db)
    event_repo = EventRepository(db)

    inv = await invoice_repo.get_by_id(invoice_id)
    if inv is None or inv.tenant_id != tenant_id:
        raise ValueError(f"Invoice {invoice_id!r} not found for tenant {tenant_id!r}")

    owner = await _fetch_tenant_owner(tenant_id)
    if not owner or not owner.get("email"):
        raise ValueError(f"No owner email for tenant {tenant_id!r}")

    settings = get_settings()
    try:
        pdf_bytes = await render_invoice_pdf(db, invoice_id, app_url=settings.APP_URL)
    except RuntimeError as exc:
        log.warning("invoice_send_pdf_unavailable", invoice_id=invoice_id, error=str(exc))
        pdf_bytes = None
    except Exception:
        log.exception("invoice_send_pdf_failed", invoice_id=invoice_id)
        pdf_bytes = None

    total_fmt = _fmt_money(Decimal(str(inv.amount or 0)), inv.currency or "COP")
    ctx = await build_invoice_context(db, inv, app_url=settings.APP_URL)
    body_html = render_jinja(
        "invoice_email.html",
        customer_name=owner.get("full_name") or owner.get("email"),
        invoice={
            "invoice_number": inv.invoice_number,
            "total_fmt": total_fmt,
            "currency": inv.currency or "COP",
            "period_start": ctx.invoice["period_start"],
            "period_end": ctx.invoice["period_end"],
            "due_date": ctx.invoice.get("due_date"),
        },
        pay_link=f"{settings.APP_URL}/checkout?invoice={inv.id}",
    )

    attachments = []
    if pdf_bytes:
        attachments = [
            {"filename": f"{inv.invoice_number}.pdf", "content": pdf_bytes}
        ]

    email_client = get_email_client()
    subject_prefix = "[Resend] " if method == "resend_manual" else ""
    subject = f"{subject_prefix}Factura {inv.invoice_number}"
    result = await email_client.send(
        tenant_id=tenant_id,
        to=owner["email"],
        subject=subject,
        html_body=body_html,
        attachments=attachments,
    )

    await event_repo.create(
        subscription_id=inv.subscription_id,
        tenant_id=tenant_id,
        event_type=EventType.invoice_generated,  # reuse; or add dedicated enum
        data={
            "invoice_sent": True,
            "method": method,
            "invoice_number": inv.invoice_number,
            "sent_to": owner["email"],
            "email_ok": result.success,
            "email_error": result.error_code,
            "message_id": result.message_id,
            "had_pdf": bool(pdf_bytes),
        },
        performed_by=performed_by,
    )
    await db.commit()

    return {
        "sent": result.success,
        "sent_to": owner["email"],
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "method": method,
        "message_id": result.message_id,
        "error": result.error_code,
        "had_pdf_attachment": bool(pdf_bytes),
    }


async def issue_credit_note(
    db: AsyncSession,
    tenant_id: str,
    invoice_id: str,
    reason: str,
    partial_amount: float | None,
    performed_by: str,
) -> dict[str, Any]:
    """Create a credit_note (negative-amount) invoice related to invoice_id."""
    invoice_repo = InvoiceRepository(db)
    event_repo = EventRepository(db)

    parent = await invoice_repo.get_by_id(invoice_id)
    if parent is None or parent.tenant_id != tenant_id:
        raise LookupError(f"Invoice {invoice_id!r} not found")

    if parent.invoice_type == "credit_note":
        raise ValueError("Cannot refund a credit note")

    parent_amount = Decimal(str(parent.amount or 0))
    if partial_amount is not None:
        if Decimal(str(partial_amount)) > parent_amount:
            raise ValueError("partial_amount exceeds invoice amount")
        refund_amt = Decimal(str(partial_amount))
    else:
        refund_amt = parent_amount

    now = datetime.now(timezone.utc)
    year = now.year

    # Atomic counter via UPSERT. Postgres & SQLite 3.24+ both support the
    # unqualified `excluded`-style upsert below.
    from sqlalchemy import text
    scope = f"credit-note-{year}"
    try:
        bind = db.get_bind()
        dialect = bind.dialect.name if bind is not None else "postgresql"
    except Exception:
        dialect = "postgresql"
    if dialect == "sqlite":
        # SAVEPOINT for the "exists" check (regla #2)
        async with db.begin_nested():
            res = await db.execute(
                text("SELECT value FROM sequence_counters WHERE scope = :scope"),
                {"scope": scope},
            )
            row = res.first()
            if row is None:
                await db.execute(
                    text(
                        "INSERT INTO sequence_counters (scope, value, updated_at) "
                        "VALUES (:scope, 1, CURRENT_TIMESTAMP)"
                    ),
                    {"scope": scope},
                )
                seq = 1
            else:
                seq = int(row[0]) + 1
                await db.execute(
                    text(
                        "UPDATE sequence_counters SET value = :v, "
                        "updated_at = CURRENT_TIMESTAMP WHERE scope = :scope"
                    ),
                    {"v": seq, "scope": scope},
                )
    else:
        res = await db.execute(
            text(
                """
                INSERT INTO sequence_counters (scope, value, updated_at)
                VALUES (:scope, 1, NOW())
                ON CONFLICT (scope) DO UPDATE
                  SET value = sequence_counters.value + 1, updated_at = NOW()
                RETURNING value
                """
            ),
            {"scope": scope},
        )
        seq = int(res.scalar_one())
    nc_number = f"NC-{year}-{seq:04d}"

    cn = Invoice(
        id=str(uuid.uuid4()),
        subscription_id=parent.subscription_id,
        tenant_id=tenant_id,
        invoice_number=nc_number,
        status=InvoiceStatus.paid,  # credit notes are issued already-settled
        amount=-refund_amt,
        currency=parent.currency,
        period_start=parent.period_start,
        period_end=parent.period_end,
        due_date=parent.due_date,
        paid_at=now,
        line_items=[
            {
                "description": f"Nota crédito — factura {parent.invoice_number} — {reason}",
                "quantity": 1,
                "unit_price": float(-refund_amt),
                "amount": float(-refund_amt),
            }
        ],
        gateway_slug=parent.gateway_slug,
        notes=f"Refund for {parent.invoice_number}: {reason}",
        parent_invoice_id=parent.id,
        invoice_type="credit_note",
    )
    db.add(cn)
    await db.flush()

    # Void parent if full refund
    is_full = refund_amt >= parent_amount
    if is_full:
        parent.status = InvoiceStatus.void
        await db.flush()

    await event_repo.create(
        subscription_id=parent.subscription_id,
        tenant_id=tenant_id,
        event_type=EventType.status_change,
        data={
            "action": "refund_issued",
            "credit_note_number": nc_number,
            "parent_invoice_number": parent.invoice_number,
            "amount": float(refund_amt),
            "full": is_full,
            "reason": reason,
        },
        performed_by=performed_by,
    )
    await db.commit()

    # Best-effort: email receipt of the credit note
    try:
        owner = await _fetch_tenant_owner(tenant_id)
        if owner and owner.get("email"):
            settings = get_settings()
            try:
                pdf_bytes = await render_invoice_pdf(db, cn.id, app_url=settings.APP_URL)
            except Exception:
                pdf_bytes = None
            total_fmt = _fmt_money(Decimal(str(refund_amt)), parent.currency or "COP")
            html = render_jinja(
                "receipt.html",
                customer_name=owner.get("full_name") or owner["email"],
                invoice={
                    "invoice_number": nc_number,
                    "total_fmt": total_fmt,
                    "currency": parent.currency or "COP",
                },
                gateway_tx_id=f"NC/{parent.invoice_number}",
            )
            client = get_email_client()
            await client.send(
                tenant_id=tenant_id,
                to=owner["email"],
                subject=f"Nota crédito {nc_number} — {parent.invoice_number}",
                html_body=html,
                attachments=(
                    [{"filename": f"{nc_number}.pdf", "content": pdf_bytes}]
                    if pdf_bytes else []
                ),
            )
    except Exception:
        log.exception("credit_note_email_failed", credit_note_id=cn.id)

    return {
        "credit_note_id": cn.id,
        "credit_note_number": nc_number,
        "parent_invoice_id": parent.id,
        "parent_invoice_number": parent.invoice_number,
        "amount": float(refund_amt),
        "full_refund": is_full,
        "parent_voided": is_full,
    }
