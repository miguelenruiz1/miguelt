"""Tests for Wompi reconciliation webhook (FASE2)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models import Invoice, InvoiceStatus, SubscriptionStatus
from app.api.routers.webhooks import process_successful_payment


@pytest.mark.asyncio
async def test_reconciliation_marks_invoice_paid_and_reactivates(
    db, make_plan, make_subscription, redis_mock, monkeypatch
):
    from app.db.models import SubscriptionStatus as S
    plan = await make_plan(slug="p-rec", price_monthly=Decimal("49000"))
    sub = await make_subscription(plan, tenant_id="t-rec", status=S.past_due)
    now = datetime.now(timezone.utc)
    inv = Invoice(
        id="inv-rec-1",
        subscription_id=sub.id,
        tenant_id="t-rec",
        invoice_number="INV-2026-0777",
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

    http_client = MagicMock()
    http_client.post = AsyncMock(return_value=MagicMock(status_code=200))
    http_client.get = AsyncMock(return_value=MagicMock(status_code=404, json=lambda: {}))

    # Avoid PDF/email calls blowing up
    async def no_pdf(*a, **kw):
        raise RuntimeError("no weasyprint")
    monkeypatch.setattr("app.services.invoice_pdf_service.render_invoice_pdf", no_pdf)

    await process_successful_payment(
        db=db,
        invoice_id="inv-rec-1",
        gateway_slug="wompi",
        gateway_tx_id="tx_ABC",
        redis=redis_mock,
        http_client=http_client,
    )

    await db.refresh(inv)
    await db.refresh(sub)
    assert inv.status == InvoiceStatus.paid
    assert inv.gateway_tx_id == "tx_ABC"
    assert inv.gateway_slug == "wompi"
    assert sub.status == SubscriptionStatus.active


@pytest.mark.asyncio
async def test_reconciliation_unmatched_payment_recorded(
    db, redis_mock, monkeypatch
):
    """If no invoice matches, we log to unmatched_payments ledger."""
    http_client = MagicMock()
    http_client.post = AsyncMock()
    http_client.get = AsyncMock(return_value=MagicMock(status_code=404))

    await process_successful_payment(
        db=db,
        invoice_id="does-not-exist",
        gateway_slug="wompi",
        gateway_tx_id="tx_orphan",
        redis=redis_mock,
        http_client=http_client,
    )

    from sqlalchemy import select
    from app.db.models import UnmatchedPayment
    res = await db.execute(
        select(UnmatchedPayment).where(UnmatchedPayment.gateway_tx_id == "tx_orphan")
    )
    row = res.scalar_one_or_none()
    assert row is not None
    assert row.gateway_slug == "wompi"


@pytest.mark.asyncio
async def test_reconciliation_idempotent_on_already_paid(
    db, make_plan, make_subscription, redis_mock
):
    plan = await make_plan(slug="p-rec2", price_monthly=Decimal("100"))
    sub = await make_subscription(plan, tenant_id="t-rec2")
    now = datetime.now(timezone.utc)
    inv = Invoice(
        id="inv-rec-2",
        subscription_id=sub.id,
        tenant_id="t-rec2",
        invoice_number="INV-2026-0778",
        status=InvoiceStatus.paid,
        amount=Decimal("100"),
        currency="COP",
        period_start=now,
        period_end=now + timedelta(days=30),
        paid_at=now,
        gateway_tx_id="tx_first",
        line_items=[],
        invoice_type="standard",
    )
    db.add(inv)
    await db.flush()

    http_client = MagicMock()
    http_client.post = AsyncMock()
    http_client.get = AsyncMock()

    # Should return without mutating anything
    await process_successful_payment(
        db=db,
        invoice_id="inv-rec-2",
        gateway_slug="wompi",
        gateway_tx_id="tx_duplicate",
        redis=redis_mock,
        http_client=http_client,
    )
    await db.refresh(inv)
    assert inv.gateway_tx_id == "tx_first"  # unchanged
