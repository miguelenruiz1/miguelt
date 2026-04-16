"""Tests for dunning service (FASE2)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.db.models import Invoice, InvoiceStatus, SubscriptionStatus
from app.services.dunning_service import _classify_overdue, dunning_check


def test_classify_overdue():
    assert _classify_overdue(0) is None
    assert _classify_overdue(1) == "soft"
    assert _classify_overdue(3) == "soft"
    assert _classify_overdue(4) == "urgent"
    assert _classify_overdue(7) == "urgent"
    assert _classify_overdue(8) == "final"
    assert _classify_overdue(30) == "final"


@pytest.mark.asyncio
async def test_dunning_sends_urgent_for_5_day_overdue(
    db, make_plan, make_subscription, monkeypatch
):
    plan = await make_plan(slug="p-dun", price_monthly=Decimal("49000"))
    sub = await make_subscription(plan, tenant_id="t-dun")
    now = datetime.now(timezone.utc)
    inv = Invoice(
        id="inv-dun-1",
        subscription_id=sub.id,
        tenant_id="t-dun",
        invoice_number="INV-2026-0010",
        status=InvoiceStatus.open,
        amount=Decimal("49000"),
        currency="COP",
        period_start=now - timedelta(days=35),
        period_end=now - timedelta(days=5),
        due_date=date.today() - timedelta(days=5),
        line_items=[],
        invoice_type="standard",
        dunning_count=0,
    )
    db.add(inv)
    await db.flush()

    # Mock owner fetch
    async def fake_owner(tenant_id):
        return {"email": "miguel@miguel.com", "full_name": "Miguel", "user_id": "u1"}

    monkeypatch.setattr(
        "app.services.dunning_service._fetch_tenant_owner", fake_owner
    )

    # Mock email client
    from app.services.email_client import EmailResult
    send_calls = []

    class _FakeClient:
        async def send(self, **kwargs):
            send_calls.append(kwargs)
            return EmailResult(success=True, message_id="m1")

    monkeypatch.setattr(
        "app.services.dunning_service.get_email_client", lambda: _FakeClient()
    )

    # Mock PDF (avoid weasyprint dep)
    async def fake_pdf(*a, **kw):
        raise RuntimeError("no weasyprint")

    monkeypatch.setattr(
        "app.services.dunning_service.render_invoice_pdf", fake_pdf
    )

    summary = await dunning_check(db)
    assert summary["scanned"] == 1
    assert summary["urgent"] == 1
    assert summary["soft"] == 0
    assert summary["final"] == 0

    # Invoice updated
    await db.refresh(inv)
    assert inv.dunning_count == 1
    assert inv.last_dunning_at is not None

    # Email was attempted
    assert len(send_calls) == 1
    assert send_calls[0]["to"] == "miguel@miguel.com"
    assert "INV-2026-0010" in send_calls[0]["subject"]


@pytest.mark.asyncio
async def test_dunning_final_marks_past_due(
    db, make_plan, make_subscription, monkeypatch
):
    plan = await make_plan(slug="p-dun2", price_monthly=Decimal("100000"))
    sub = await make_subscription(plan, tenant_id="t-dun2")
    now = datetime.now(timezone.utc)
    inv = Invoice(
        id="inv-dun-2",
        subscription_id=sub.id,
        tenant_id="t-dun2",
        invoice_number="INV-2026-0011",
        status=InvoiceStatus.open,
        amount=Decimal("100000"),
        currency="COP",
        period_start=now - timedelta(days=45),
        period_end=now - timedelta(days=15),
        due_date=date.today() - timedelta(days=12),
        line_items=[],
        invoice_type="standard",
        dunning_count=0,
    )
    db.add(inv)
    await db.flush()

    async def fake_owner(tid):
        return {"email": "a@b.co", "full_name": "A"}

    monkeypatch.setattr("app.services.dunning_service._fetch_tenant_owner", fake_owner)

    from app.services.email_client import EmailResult

    class _FC:
        async def send(self, **kw):
            return EmailResult(success=True)

    monkeypatch.setattr("app.services.dunning_service.get_email_client", lambda: _FC())

    async def fake_pdf(*a, **kw):
        raise RuntimeError("no pdf")

    monkeypatch.setattr("app.services.dunning_service.render_invoice_pdf", fake_pdf)

    summary = await dunning_check(db)
    assert summary["final"] == 1

    await db.refresh(sub)
    assert sub.status == SubscriptionStatus.past_due
