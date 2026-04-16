"""Integration test: POST /subscriptions/{tenant}/invoices/{id}/send (FASE2)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models import Invoice, InvoiceStatus, SubscriptionEvent


@pytest.mark.asyncio
async def test_send_invoice_email_persists_event(
    client, db, make_plan, make_subscription, monkeypatch
):
    plan = await make_plan(slug="p-send", price_monthly=Decimal("49000"))
    sub = await make_subscription(plan, tenant_id="test-tenant")
    now = datetime.now(timezone.utc)
    inv = Invoice(
        id="inv-send-1",
        subscription_id=sub.id,
        tenant_id="test-tenant",
        invoice_number="INV-2026-1000",
        status=InvoiceStatus.open,
        amount=Decimal("49000"),
        currency="COP",
        period_start=now,
        period_end=now + timedelta(days=30),
        line_items=[],
        invoice_type="standard",
    )
    db.add(inv)
    await db.flush()
    await db.commit()

    # Mock owner fetch + email client
    async def fake_owner(tenant_id):
        return {"email": "miguelenruiz1@gmail.com", "full_name": "Miguel"}

    monkeypatch.setattr(
        "app.services.invoice_service._fetch_tenant_owner", fake_owner
    )

    from app.services.email_client import EmailResult

    class _FC:
        async def send(self, **kw):
            return EmailResult(success=True, message_id="re_test_12345")

    monkeypatch.setattr(
        "app.services.invoice_service.get_email_client", lambda: _FC()
    )

    async def no_pdf(*a, **kw):
        raise RuntimeError("no pdf")

    monkeypatch.setattr(
        "app.services.invoice_service.render_invoice_pdf", no_pdf
    )

    resp = await client.post(
        "/api/v1/subscriptions/test-tenant/invoices/inv-send-1/send"
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["sent"] is True
    assert data["sent_to"] == "miguelenruiz1@gmail.com"
    assert data["message_id"] == "re_test_12345"

    # Event was persisted
    res = await db.execute(
        select(SubscriptionEvent).where(SubscriptionEvent.subscription_id == sub.id)
    )
    events = list(res.scalars().all())
    sent_events = [e for e in events if (e.data or {}).get("invoice_sent")]
    assert sent_events
    assert sent_events[0].data["method"] == "manual"
