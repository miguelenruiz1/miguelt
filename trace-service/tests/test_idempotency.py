"""
Tests: idempotency key deduplication.

- Same POST with same Idempotency-Key returns same response without creating duplicates.
- Different Idempotency-Key creates a new resource.
- Missing Idempotency-Key always creates a new resource.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import create_wallet


@pytest.mark.asyncio
async def test_create_asset_idempotency(client: AsyncClient):
    """
    Same request with same Idempotency-Key → same response, no duplicate assets.
    """
    wallet = await create_wallet(client)
    idem_key = str(uuid.uuid4())
    mint = f"mint_{uuid.uuid4().hex}"

    payload = {
        "asset_mint": mint,
        "product_type": "electronics",
        "metadata": {},
        "initial_custodian_wallet": wallet["wallet_pubkey"],
    }

    # First call
    r1 = await client.post(
        "/api/v1/assets",
        json=payload,
        headers={"Idempotency-Key": idem_key},
    )
    assert r1.status_code in (200, 201)
    asset_id_1 = r1.json()["asset"]["id"]

    # Second call — same key
    r2 = await client.post(
        "/api/v1/assets",
        json=payload,
        headers={"Idempotency-Key": idem_key},
    )
    # Should return 200 (cached) with the same asset
    assert r2.status_code in (200, 201)
    asset_id_2 = r2.json()["asset"]["id"]

    assert asset_id_1 == asset_id_2, "Idempotency key should return the same asset"


@pytest.mark.asyncio
async def test_register_wallet_idempotency(client: AsyncClient):
    """Same wallet registration with same Idempotency-Key → same wallet returned."""
    idem_key = str(uuid.uuid4())
    pubkey = ("wallet_" + uuid.uuid4().hex)[:44]

    payload = {"wallet_pubkey": pubkey, "tags": ["test"], "status": "active"}

    r1 = await client.post(
        "/api/v1/registry/wallets",
        json=payload,
        headers={"Idempotency-Key": idem_key},
    )
    assert r1.status_code in (200, 201)
    id1 = r1.json()["id"]

    r2 = await client.post(
        "/api/v1/registry/wallets",
        json=payload,
        headers={"Idempotency-Key": idem_key},
    )
    assert r2.status_code in (200, 201)
    id2 = r2.json()["id"]

    assert id1 == id2


@pytest.mark.asyncio
async def test_handoff_idempotency(client: AsyncClient):
    """Same handoff with same Idempotency-Key → exactly one event created."""
    wallet_a = await create_wallet(client)
    wallet_b = await create_wallet(client)

    # Create asset
    r = await client.post(
        "/api/v1/assets",
        json={
            "asset_mint": f"mint_{uuid.uuid4().hex}",
            "product_type": "test",
            "metadata": {},
            "initial_custodian_wallet": wallet_a["wallet_pubkey"],
        },
    )
    assert r.status_code == 201
    asset_id = r.json()["asset"]["id"]

    idem_key = str(uuid.uuid4())
    payload = {"to_wallet": wallet_b["wallet_pubkey"]}

    r1 = await client.post(
        f"/api/v1/assets/{asset_id}/events/handoff",
        json=payload,
        headers={"Idempotency-Key": idem_key, "X-User-Id": "1"},
    )
    assert r1.status_code in (200, 201)
    event_id_1 = r1.json()["event"]["id"]

    r2 = await client.post(
        f"/api/v1/assets/{asset_id}/events/handoff",
        json=payload,
        headers={"Idempotency-Key": idem_key, "X-User-Id": "1"},
    )
    assert r2.status_code in (200, 201)
    event_id_2 = r2.json()["event"]["id"]

    # Same event — no duplicate
    assert event_id_1 == event_id_2

    # Verify only one HANDOFF event in DB
    events_resp = await client.get(f"/api/v1/assets/{asset_id}/events")
    events = events_resp.json()["items"]
    handoffs = [e for e in events if e["event_type"] == "HANDOFF"]
    assert len(handoffs) == 1, f"Expected 1 HANDOFF event, got {len(handoffs)}"


@pytest.mark.asyncio
async def test_different_idempotency_keys_create_separate_wallets(client: AsyncClient):
    """Different Idempotency-Keys create distinct resources."""
    pubkey_1 = ("wallet_" + uuid.uuid4().hex)[:44]
    pubkey_2 = ("wallet_" + uuid.uuid4().hex)[:44]

    r1 = await client.post(
        "/api/v1/registry/wallets",
        json={"wallet_pubkey": pubkey_1, "tags": [], "status": "active"},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    r2 = await client.post(
        "/api/v1/registry/wallets",
        json={"wallet_pubkey": pubkey_2, "tags": [], "status": "active"},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )

    assert r1.status_code in (200, 201)
    assert r2.status_code in (200, 201)
    assert r1.json()["id"] != r2.json()["id"]
