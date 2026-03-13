"""
Tests: full custody flow — asset creation through release.
Also verifies hash chaining.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import create_asset, create_wallet


@pytest.mark.asyncio
async def test_full_custody_flow(client: AsyncClient):
    """
    Full happy-path flow:
    create wallet → create asset → handoff → arrived → loaded → qc → release
    """
    # Setup
    owner = await create_wallet(client)
    carrier = await create_wallet(client)
    warehouse = await create_wallet(client)

    # Create asset
    asset_data = await create_asset(client, owner["wallet_pubkey"])
    asset = asset_data["asset"]
    genesis_event = asset_data["event"]

    assert asset["state"] == "in_custody"
    assert asset["current_custodian_wallet"] == owner["wallet_pubkey"]
    assert genesis_event["event_type"] == "CREATED"
    assert genesis_event["anchored"] is False
    assert genesis_event["event_hash"] is not None
    assert genesis_event["prev_event_hash"] is None  # genesis

    asset_id = asset["id"]

    # Handoff to carrier
    resp = await client.post(
        f"/api/v1/assets/{asset_id}/events/handoff",
        json={
            "to_wallet": carrier["wallet_pubkey"],
            "location": {"lat": 19.43, "lng": -99.13, "label": "CDMX"},
            "data": {"carrier_id": "DHL-001"},
        },
        headers={"X-User-Id": "1"},
    )
    assert resp.status_code == 201
    handoff_data = resp.json()
    handoff_event = handoff_data["event"]
    assert handoff_event["event_type"] == "HANDOFF"
    assert handoff_event["from_wallet"] == owner["wallet_pubkey"]
    assert handoff_event["to_wallet"] == carrier["wallet_pubkey"]
    assert handoff_event["prev_event_hash"] == genesis_event["event_hash"]
    assert handoff_data["asset"]["state"] == "in_transit"

    # Arrived at warehouse
    resp = await client.post(
        f"/api/v1/assets/{asset_id}/events/arrived",
        json={"location": {"label": "Warehouse A"}, "data": {}},
        headers={"X-User-Id": "1"},
    )
    assert resp.status_code == 201
    arrived_event = resp.json()["event"]
    assert arrived_event["event_type"] == "ARRIVED"
    assert arrived_event["prev_event_hash"] == handoff_event["event_hash"]

    # Handoff to warehouse
    resp = await client.post(
        f"/api/v1/assets/{asset_id}/events/handoff",
        json={"to_wallet": warehouse["wallet_pubkey"]},
        headers={"X-User-Id": "1"},
    )
    assert resp.status_code == 201

    # Loaded
    resp = await client.post(
        f"/api/v1/assets/{asset_id}/events/loaded",
        json={"data": {"batch": "BATCH-42"}},
        headers={"X-User-Id": "1"},
    )
    assert resp.status_code == 201
    assert resp.json()["asset"]["state"] == "loaded"

    # QC pass
    resp = await client.post(
        f"/api/v1/assets/{asset_id}/events/qc",
        json={"result": "pass", "notes": "All checks OK"},
        headers={"X-User-Id": "1"},
    )
    assert resp.status_code == 201
    assert resp.json()["asset"]["state"] == "qc_passed"

    # Release (admin)
    resp = await client.post(
        f"/api/v1/assets/{asset_id}/events/release",
        headers={"X-User-Id": "1", "X-Admin-Key": "test-admin-key"},
        json={"external_wallet": "external_buyer_wallet_123", "reason": "Sale completed"},
    )
    assert resp.status_code == 201
    final = resp.json()
    assert final["asset"]["state"] == "released"
    assert final["event"]["to_wallet"] == "external_buyer_wallet_123"


@pytest.mark.asyncio
async def test_hash_chain_integrity(client: AsyncClient):
    """Every event's prev_event_hash must equal the previous event's event_hash."""
    wallet_a = await create_wallet(client)
    wallet_b = await create_wallet(client)
    wallet_c = await create_wallet(client)

    asset_data = await create_asset(client, wallet_a["wallet_pubkey"])
    asset_id = asset_data["asset"]["id"]

    # Create several events
    await client.post(
        f"/api/v1/assets/{asset_id}/events/handoff",
        json={"to_wallet": wallet_b["wallet_pubkey"]},
        headers={"X-User-Id": "1"},
    )
    await client.post(
        f"/api/v1/assets/{asset_id}/events/arrived",
        json={"data": {}},
        headers={"X-User-Id": "1"},
    )
    await client.post(
        f"/api/v1/assets/{asset_id}/events/handoff",
        json={"to_wallet": wallet_c["wallet_pubkey"]},
        headers={"X-User-Id": "1"},
    )

    # Fetch all events (oldest first)
    resp = await client.get(f"/api/v1/assets/{asset_id}/events?limit=100")
    assert resp.status_code == 200
    events = sorted(resp.json()["items"], key=lambda e: e["created_at"])

    for i in range(1, len(events)):
        assert events[i]["prev_event_hash"] == events[i - 1]["event_hash"], (
            f"Chain broken at event index {i}: "
            f"{events[i]['prev_event_hash']} != {events[i-1]['event_hash']}"
        )


@pytest.mark.asyncio
async def test_release_without_admin_key_fails(client: AsyncClient):
    wallet = await create_wallet(client)
    asset_data = await create_asset(client, wallet["wallet_pubkey"])
    asset_id = asset_data["asset"]["id"]

    resp = await client.post(
        f"/api/v1/assets/{asset_id}/events/release",
        headers={"X-User-Id": "1", "X-Admin-Key": "wrong-key"},
        json={"external_wallet": "external_xyz", "reason": "unauthorized test"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_cannot_handoff_released_asset(client: AsyncClient):
    wallet_a = await create_wallet(client)
    wallet_b = await create_wallet(client)
    asset_data = await create_asset(client, wallet_a["wallet_pubkey"])
    asset_id = asset_data["asset"]["id"]

    # Release the asset
    await client.post(
        f"/api/v1/assets/{asset_id}/events/release",
        headers={"X-User-Id": "1", "X-Admin-Key": "test-admin-key"},
        json={"external_wallet": "ext_wallet", "reason": "Sale"},
    )

    # Try to handoff
    resp = await client.post(
        f"/api/v1/assets/{asset_id}/events/handoff",
        json={"to_wallet": wallet_b["wallet_pubkey"]},
        headers={"X-User-Id": "1"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_asset_mint_rejected(client: AsyncClient):
    wallet = await create_wallet(client)
    mint = f"mint_{uuid.uuid4().hex}"

    r1 = await client.post(
        "/api/v1/assets",
        json={
            "asset_mint": mint,
            "product_type": "electronics",
            "metadata": {},
            "initial_custodian_wallet": wallet["wallet_pubkey"],
        },
    )
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/assets",
        json={
            "asset_mint": mint,
            "product_type": "electronics",
            "metadata": {},
            "initial_custodian_wallet": wallet["wallet_pubkey"],
        },
    )
    assert r2.status_code == 409
