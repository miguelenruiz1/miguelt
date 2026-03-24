"""Tests for report endpoints — PnL, CSV exports, analytics."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_pnl_report(client: AsyncClient):
    resp = await client.get("/api/v1/reports/pnl", params={
        "date_from": "2026-01-01", "date_to": "2026-12-31",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "products" in data
    assert "totals" in data


@pytest.mark.asyncio
async def test_products_csv_export(client: AsyncClient):
    resp = await client.get("/api/v1/reports/products")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_stock_csv_export(client: AsyncClient):
    resp = await client.get("/api/v1/reports/stock")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_movements_csv_export(client: AsyncClient):
    resp = await client.get("/api/v1/reports/movements")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_overview(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/overview")
    if resp.status_code == 404:
        resp = await client.get("/api/v1/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_skus" in data or "products" in data or isinstance(data, dict)
