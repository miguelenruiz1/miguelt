"""
Test configuration and fixtures.

Uses the real Postgres test DB (via TEST_DATABASE_URL env var).
Redis is the real Redis on port 6380. arq enqueue is mocked.

Run with:
    TEST_DATABASE_URL="postgresql+asyncpg://trace:tracepass@localhost:5437/trace_test" pytest tests/
"""
from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# ─── Test DB URL ──────────────────────────────────────────────────────────────

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://trace:tracepass@localhost:5437/trace_test",
)

# ─── Override settings for tests ──────────────────────────────────────────────
# These must be set BEFORE importing any app module.

os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/15")
os.environ.setdefault("ARQ_REDIS_URL", "redis://localhost:6380/14")
os.environ.setdefault("SOLANA_SIMULATION", "true")
os.environ.setdefault("TRACE_ADMIN_KEY", "test-admin-key")
os.environ.setdefault("SOLANA_RPC_URL", "https://api.devnet.solana.com")


# ─── Schema setup (once per session) ─────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="session")
async def _setup_schema():
    """Drop and recreate all tables once per test session."""
    from app.db.base import Base
    from app.db.models import RegistryWallet, Asset, CustodyEvent  # noqa: F401

    eng = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield eng

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables(_setup_schema):
    """Truncate all data tables before each test for full isolation."""
    eng = _setup_schema
    async with eng.begin() as conn:
        from sqlalchemy import text
        # Truncate in correct order to respect FK constraints
        await conn.execute(text("TRUNCATE TABLE custody_events, assets, registry_wallets RESTART IDENTITY CASCADE"))


# ─── HTTP client fixture ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(_setup_schema) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP test client backed by the real FastAPI app.
    - Uses the real test DB (DATABASE_URL env var is set above).
    - Mocks arq enqueue so tests don't need the ARQ worker.
    """
    from app.main import create_app

    app = create_app()

    with patch("app.services.anchor_service.enqueue_anchor", new_callable=AsyncMock):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac


# ─── Helper factories ─────────────────────────────────────────────────────────

async def create_wallet(
    client: AsyncClient,
    pubkey: str | None = None,
    tags: list[str] | None = None,
    status: str = "active",
) -> dict[str, Any]:
    # uuid4().hex is 32 hex chars; prepend "wallet_" → 39 chars → slice to 44 is fine
    pubkey = pubkey or ("wallet_" + uuid.uuid4().hex)[:44]
    resp = await client.post(
        "/api/v1/registry/wallets",
        json={"wallet_pubkey": pubkey, "tags": tags or [], "status": status},
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


async def create_asset(
    client: AsyncClient,
    custodian_pubkey: str,
    mint: str | None = None,
) -> dict[str, Any]:
    mint = mint or f"mint_{uuid.uuid4().hex}"
    resp = await client.post(
        "/api/v1/assets",
        json={
            "asset_mint": mint,
            "product_type": "electronics",
            "metadata": {"sku": "TEST-001"},
            "initial_custodian_wallet": custodian_pubkey,
        },
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()
