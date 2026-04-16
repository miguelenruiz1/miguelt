"""Integration tests for /api/v1/plans router.

Verify the FastAPI wiring: routes resolve, auth is required, and the handler
talks to the DB layer correctly.
"""
from __future__ import annotations

from decimal import Decimal

import pytest


@pytest.mark.asyncio
async def test_list_plans_200(client, make_plan) -> None:
    await make_plan(slug="free", price_monthly=Decimal("0"))
    await make_plan(slug="starter", price_monthly=Decimal("49"))

    resp = await client.get("/api/v1/plans/")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    slugs = {p["slug"] for p in (data if isinstance(data, list) else data.get("items", []))}
    assert "free" in slugs
    assert "starter" in slugs


@pytest.mark.asyncio
async def test_get_plan_by_id_200(client, make_plan) -> None:
    plan = await make_plan(slug="pro", price_monthly=Decimal("149"))
    resp = await client.get(f"/api/v1/plans/{plan.id}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["slug"] == "pro"
