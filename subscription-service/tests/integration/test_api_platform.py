"""Integration tests for /api/v1/platform (superuser-only endpoints)."""
from __future__ import annotations

from decimal import Decimal

import pytest


@pytest.mark.asyncio
async def test_get_dashboard_as_superuser_200(client, make_plan, make_subscription) -> None:
    """Default test user IS superuser → dashboard returns 200 with metrics."""
    plan = await make_plan(slug="pro", price_monthly=Decimal("99"))
    await make_subscription(plan, tenant_id="t-dash")

    resp = await client.get("/api/v1/platform/dashboard")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "mrr" in body
    assert "arr" in body


@pytest.mark.asyncio
async def test_get_dashboard_requires_superuser(app, client) -> None:
    """Non-superuser → 403."""
    from app.api.deps import get_current_user

    async def _non_super():
        return {
            "id": "u-2",
            "email": "regular@test",
            "tenant_id": "test-tenant",
            "is_superuser": False,
            "permissions": [],
        }

    app.dependency_overrides[get_current_user] = _non_super

    resp = await client.get("/api/v1/platform/dashboard")
    assert resp.status_code == 403, resp.text
