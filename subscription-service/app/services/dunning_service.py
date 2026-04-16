"""Dunning (collections) service — FASE2 billing completeness.

Cron-driven: scan open invoices that are past due, send a reminder email
(soft/urgent/final) based on days overdue, and mark subscriptions past_due
after 8+ days.

Templates live in app/services/invoice_pdf/templates/dunning_*.html.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import httpx
import structlog
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.db.models import (
    EventType,
    Invoice,
    InvoiceStatus,
    Subscription,
    SubscriptionStatus,
)
from app.repositories.event_repo import EventRepository
from app.services.email_client import get_email_client
from app.services.invoice_pdf_service import (
    build_invoice_context,
    render_invoice_pdf,
    render_jinja,
    _fmt_money,
)

log = structlog.get_logger(__name__)


def _classify_overdue(days: int) -> str | None:
    """Return 'soft' | 'urgent' | 'final' or None if not due yet."""
    if days < 1:
        return None
    if days <= 3:
        return "soft"
    if days <= 7:
        return "urgent"
    return "final"


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


async def dunning_check(db: AsyncSession) -> dict[str, Any]:
    """Run one dunning pass. Returns a summary dict."""
    now = datetime.now(timezone.utc)
    today = now.date()
    three_days_ago = now - timedelta(days=3)

    # Select open invoices past due whose last_dunning was >3d ago or null.
    stmt = (
        select(Invoice)
        .where(
            Invoice.status == InvoiceStatus.open,
            Invoice.due_date.is_not(None),
            Invoice.due_date < today,
            or_(
                Invoice.last_dunning_at.is_(None),
                Invoice.last_dunning_at < three_days_ago,
            ),
        )
        .limit(500)
    )
    result = await db.execute(stmt)
    invoices = list(result.scalars().all())

    summary = {"scanned": len(invoices), "soft": 0, "urgent": 0, "final": 0, "skipped": 0, "errors": 0}

    email_client = get_email_client()
    event_repo = EventRepository(db)

    for inv in invoices:
        days_overdue = (today - inv.due_date).days
        kind = _classify_overdue(days_overdue)
        if kind is None:
            summary["skipped"] += 1
            continue

        owner = await _fetch_tenant_owner(inv.tenant_id)
        if not owner or not owner.get("email"):
            log.warning("dunning_no_owner_email", tenant_id=inv.tenant_id, invoice_id=inv.id)
            summary["skipped"] += 1
            continue

        customer_name = owner.get("full_name") or owner.get("email")
        total_fmt = _fmt_money(Decimal(str(inv.amount or 0)), inv.currency or "COP")
        settings = get_settings()
        pay_link = f"{settings.APP_URL}/checkout?invoice={inv.id}"

        tmpl_ctx = {
            "customer_name": customer_name,
            "invoice": {
                "invoice_number": inv.invoice_number,
                "total_fmt": total_fmt,
                "currency": inv.currency or "COP",
            },
            "days_overdue": days_overdue,
            "pay_link": pay_link,
        }
        template_name = f"dunning_{kind}.html"
        subject_map = {
            "soft": f"Recordatorio de pago — factura {inv.invoice_number}",
            "urgent": f"Factura {inv.invoice_number} vencida — acción requerida",
            "final": f"Suscripción suspendida — factura {inv.invoice_number}",
        }

        try:
            html_body = render_jinja(template_name, **tmpl_ctx)
        except Exception as exc:
            log.exception("dunning_render_failed", invoice_id=inv.id, error=str(exc))
            summary["errors"] += 1
            continue

        # Try to attach PDF (best-effort — don't fail dunning if PDF fails)
        attachments = []
        try:
            pdf_bytes = await render_invoice_pdf(db, inv.id, app_url=settings.APP_URL)
            attachments = [{"filename": f"{inv.invoice_number}.pdf", "content": pdf_bytes}]
        except Exception as exc:
            log.warning("dunning_pdf_skip", invoice_id=inv.id, error=str(exc))

        result = await email_client.send(
            tenant_id=inv.tenant_id,
            to=owner["email"],
            subject=subject_map[kind],
            html_body=html_body,
            attachments=attachments,
        )

        # Update invoice regardless of send result (avoid infinite retry spam)
        inv.last_dunning_at = now
        inv.dunning_count = (inv.dunning_count or 0) + 1

        # Final stage: flip to past_due
        if kind == "final":
            inv.status = InvoiceStatus.open  # invoice itself stays open, uncollectible could be set manually
            sub = await db.get(Subscription, inv.subscription_id)
            if sub and sub.status != SubscriptionStatus.past_due:
                sub.status = SubscriptionStatus.past_due
                await event_repo.create(
                    subscription_id=sub.id,
                    tenant_id=sub.tenant_id,
                    event_type=EventType.status_change,
                    data={"from": "active", "to": "past_due", "reason": "dunning_final"},
                    performed_by="dunning",
                )

        await event_repo.create(
            subscription_id=inv.subscription_id,
            tenant_id=inv.tenant_id,
            event_type=EventType.invoice_generated,  # reused; a dedicated enum could be added
            data={
                "dunning": kind,
                "invoice_number": inv.invoice_number,
                "days_overdue": days_overdue,
                "sent_to": owner["email"],
                "email_ok": result.success,
                "email_error": result.error_code,
            },
            performed_by="dunning",
        )
        await db.flush()
        summary[kind] += 1
        if not result.success:
            summary["errors"] += 1
            log.warning(
                "dunning_email_failed",
                invoice_id=inv.id,
                kind=kind,
                error=result.error_code,
            )

    await db.commit()
    log.info("dunning_run_complete", **summary)
    return summary


async def run_dunning_loop(interval_seconds: int = 3600) -> None:
    """Background loop: run dunning_check every `interval_seconds`."""
    import asyncio
    from app.db.session import get_session_factory

    factory = get_session_factory()
    while True:
        try:
            async with factory() as db:
                await dunning_check(db)
        except Exception:
            log.exception("dunning_loop_error")
        await asyncio.sleep(interval_seconds)
