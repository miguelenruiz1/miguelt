"""Unit tests for PlatformService — MRR / ARR math + change_plan guards."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.db.models import BillingCycle, SubscriptionStatus
from app.services.platform_service import PlatformService


# ── MRR / ARR ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mrr_monthly_cycle(db, make_plan, make_subscription) -> None:
    """3 active monthly subs @ $100 → MRR=300, ARR=3600."""
    plan = await make_plan(slug="m100", price_monthly=Decimal("100.00"))
    for i in range(3):
        await make_subscription(plan, tenant_id=f"t-{i}", billing_cycle=BillingCycle.monthly)

    svc = PlatformService(db)
    dash = await svc.get_dashboard()

    assert float(dash["mrr"]) == pytest.approx(300.0, abs=0.01)
    assert float(dash["arr"]) == pytest.approx(3600.0, abs=0.01)


@pytest.mark.asyncio
async def test_mrr_annual_cycle_uses_price_annual(db, make_plan, make_subscription) -> None:
    """2 annual subs with price_annual=1000 → MRR≈166.67, ARR=2000."""
    plan = await make_plan(
        slug="annual-1000",
        price_monthly=Decimal("100.00"),     # should be ignored for annual cycle
        price_annual=Decimal("1000.00"),
    )
    await make_subscription(plan, tenant_id="t-a1", billing_cycle=BillingCycle.annual)
    await make_subscription(plan, tenant_id="t-a2", billing_cycle=BillingCycle.annual)

    svc = PlatformService(db)
    dash = await svc.get_dashboard()

    assert float(dash["mrr"]) == pytest.approx(2000.0 / 12.0, abs=0.01)
    assert float(dash["arr"]) == pytest.approx(2000.0, abs=0.01)


@pytest.mark.asyncio
async def test_canceled_subs_do_not_contribute_to_mrr(db, make_plan, make_subscription) -> None:
    plan = await make_plan(slug="s50", price_monthly=Decimal("50.00"))
    await make_subscription(plan, tenant_id="t-c", status=SubscriptionStatus.canceled)

    svc = PlatformService(db)
    dash = await svc.get_dashboard()

    assert float(dash["mrr"]) == pytest.approx(0.0, abs=0.01)


# ── change_tenant_plan guard ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_change_plan_rejects_canceled(db, make_plan, make_subscription) -> None:
    """Canceled sub → raises ValueError telling the caller to reactivate first."""
    plan_a = await make_plan(slug="plan-a", price_monthly=Decimal("10"))
    plan_b = await make_plan(slug="plan-b", price_monthly=Decimal("20"))
    await make_subscription(plan_a, tenant_id="canceled-tenant", status=SubscriptionStatus.canceled)

    svc = PlatformService(db)
    with pytest.raises(ValueError, match="[Rr]eactiv"):
        await svc.change_tenant_plan(tenant_id="canceled-tenant", plan_slug="plan-b")


@pytest.mark.asyncio
async def test_change_plan_unknown_plan_raises(db, make_plan, make_subscription) -> None:
    plan = await make_plan(slug="plan-x", price_monthly=Decimal("10"))
    await make_subscription(plan, tenant_id="t-x")

    svc = PlatformService(db)
    with pytest.raises(ValueError, match="not found"):
        await svc.change_tenant_plan(tenant_id="t-x", plan_slug="nonexistent-plan")
