"""
Tests: allowlist enforcement.

- Creating an asset with a non-allowlisted wallet must fail.
- Handoff to a non-allowlisted wallet must fail.
- Handoff to an active wallet must succeed.
- Suspended/revoked wallets must be rejected.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import create_asset, create_wallet


@pytest.mark.asyncio
async def test_create_asset_requires_active_wallet(client: AsyncClient):
    """Asset creation fails when initial_custodian is not in allowlist."""
    resp = await client.post(
        "/api/v1/assets",
        json={
            "asset_mint": f"mint_{uuid.uuid4().hex}",
            "product_type": "test",
            "metadata": {},
            "initial_custodian_wallet": "wallet_not_registered_at_all",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "WALLET_NOT_ALLOWLISTED"


@pytest.mark.asyncio
async def test_handoff_to_unregistered_wallet_rejected(client: AsyncClient):
    wallet = await create_wallet(client)
    asset_data = await create_asset(client, wallet["wallet_pubkey"])
    asset_id = asset_data["asset"]["id"]

    resp = await client.post(
        f"/api/v1/assets/{asset_id}/events/handoff",
        json={"to_wallet": "unregistered_wallet_xyz"},
        headers={"X-User-Id": "1"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "WALLET_NOT_ALLOWLISTED"


@pytest.mark.asyncio
async def test_handoff_to_suspended_wallet_rejected(client: AsyncClient):
    owner = await create_wallet(client)
    suspended = await create_wallet(client, status="suspended")
    asset_data = await create_asset(client, owner["wallet_pubkey"])
    asset_id = asset_data["asset"]["id"]

    resp = await client.post(
        f"/api/v1/assets/{asset_id}/events/handoff",
        json={"to_wallet": suspended["wallet_pubkey"]},
        headers={"X-User-Id": "1"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "WALLET_NOT_ALLOWLISTED"


@pytest.mark.asyncio
async def test_handoff_to_revoked_wallet_rejected(client: AsyncClient):
    owner = await create_wallet(client)
    revoked = await create_wallet(client, status="revoked")
    asset_data = await create_asset(client, owner["wallet_pubkey"])
    asset_id = asset_data["asset"]["id"]

    resp = await client.post(
        f"/api/v1/assets/{asset_id}/events/handoff",
        json={"to_wallet": revoked["wallet_pubkey"]},
        headers={"X-User-Id": "1"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "WALLET_NOT_ALLOWLISTED"


@pytest.mark.asyncio
async def test_handoff_to_active_wallet_succeeds(client: AsyncClient):
    owner = await create_wallet(client)
    recipient = await create_wallet(client)
    asset_data = await create_asset(client, owner["wallet_pubkey"])
    asset_id = asset_data["asset"]["id"]

    resp = await client.post(
        f"/api/v1/assets/{asset_id}/events/handoff",
        json={"to_wallet": recipient["wallet_pubkey"]},
        headers={"X-User-Id": "1"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["asset"]["current_custodian_wallet"] == recipient["wallet_pubkey"]
    assert body["asset"]["state"] == "in_transit"


@pytest.mark.asyncio
async def test_wallet_suspend_then_reactivate(client: AsyncClient):
    """Suspended wallet cannot receive handoff; after reactivation it can."""
    owner = await create_wallet(client)
    target = await create_wallet(client)
    asset_data = await create_asset(client, owner["wallet_pubkey"])
    asset_id = asset_data["asset"]["id"]
    target_id = target["id"]

    # Suspend
    await client.patch(
        f"/api/v1/registry/wallets/{target_id}",
        json={"status": "suspended"},
    )

    # Handoff fails
    resp = await client.post(
        f"/api/v1/assets/{asset_id}/events/handoff",
        json={"to_wallet": target["wallet_pubkey"]},
        headers={"X-User-Id": "1"},
    )
    assert resp.status_code == 403

    # Reactivate
    await client.patch(
        f"/api/v1/registry/wallets/{target_id}",
        json={"status": "active"},
    )

    # Handoff now succeeds
    resp = await client.post(
        f"/api/v1/assets/{asset_id}/events/handoff",
        json={"to_wallet": target["wallet_pubkey"]},
        headers={"X-User-Id": "1"},
    )
    assert resp.status_code == 201
