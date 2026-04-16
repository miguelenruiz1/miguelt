"""Shared test fixtures for subscription-service.

- In-memory SQLite per test session (JSONB patched to JSON for SQLite compat).
- Rolling-back session per test.
- FastAPI test client with dependency overrides for auth + DB.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# Force test-safe settings BEFORE app imports.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("JWT_SECRET", "test-secret-key-32-chars-min-for-tests!")
os.environ.setdefault("ENV", "test")

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


# ─── JSONB → JSON for SQLite ──────────────────────────────────────────────────
# We patch the SQLite type compiler so `JSONB` columns compile to `JSON`.
def _patch_sqlite_jsonb() -> None:
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

    if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):
        SQLiteTypeCompiler.visit_JSONB = (  # type: ignore[attr-defined]
            lambda self, type_, **kw: self.visit_JSON(type_, **kw)
        )


_patch_sqlite_jsonb()


# ─── Event loop ───────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ─── Engine + session ─────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session")
async def engine():
    from app.db.base import Base
    import app.db.models  # noqa: F401 — register models

    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    # Tests must be isolated even when the code under test calls db.commit()
    # (dunning_service, invoice_service and others do). SQLite in-memory via
    # aiosqlite doesn't cooperate cleanly with the nested-transaction pattern,
    # so instead we truncate every table after each test. Session-scoped
    # engine stays warm; per-test data never leaks.
    from app.db.base import Base

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()

    async with engine.begin() as conn:
        # Wipe in reverse dependency order so FKs don't complain.
        for table in reversed(Base.metadata.sorted_tables):
            await conn.exec_driver_sql(f"DELETE FROM {table.name}")


# ─── Redis mock ───────────────────────────────────────────────────────────────


@pytest.fixture
def redis_mock():
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.set = AsyncMock()
    r.setex = AsyncMock()
    r.delete = AsyncMock(return_value=1)
    r.expire = AsyncMock()
    r.aclose = AsyncMock()
    return r


# ─── App + client ─────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def app(db, redis_mock):
    from app.main import create_app
    from app.db.session import get_db_session
    from app.api.deps import get_redis, get_current_user

    application = create_app()

    async def _override_db():
        yield db

    def _override_redis():
        return redis_mock

    async def _override_user():
        return {
            "id": "test-user-1",
            "email": "test@tracelog.co",
            "tenant_id": "test-tenant",
            "is_superuser": True,
            "permissions": [
                "subscription.view",
                "subscription.manage",
                "plans.view",
                "plans.manage",
                "licenses.view",
                "licenses.manage",
            ],
        }

    application.dependency_overrides[get_db_session] = _override_db
    application.dependency_overrides[get_redis] = _override_redis
    application.dependency_overrides[get_current_user] = _override_user

    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ─── Factories ────────────────────────────────────────────────────────────────


def _uid() -> str:
    return str(uuid.uuid4())


@pytest_asyncio.fixture
async def make_plan(db):
    """Factory that creates a Plan row."""
    from app.db.models import Plan

    async def _make(
        slug: str = "starter",
        price_monthly: Decimal = Decimal("49.00"),
        price_annual: Decimal | None = None,
    ) -> Plan:
        plan = Plan(
            id=_uid(),
            name=slug.title(),
            slug=slug,
            price_monthly=price_monthly,
            price_annual=price_annual,
            currency="USD",
            max_users=10,
            max_assets=1000,
            max_wallets=50,
            modules=[],
            features={},
            is_active=True,
            is_archived=False,
            sort_order=0,
        )
        db.add(plan)
        await db.flush()
        return plan

    return _make


@pytest_asyncio.fixture
async def make_subscription(db):
    from app.db.models import Subscription, SubscriptionStatus, BillingCycle

    async def _make(
        plan,
        tenant_id: str | None = None,
        status: SubscriptionStatus = SubscriptionStatus.active,
        billing_cycle: BillingCycle = BillingCycle.monthly,
    ):
        now = datetime.now(timezone.utc)
        sub = Subscription(
            id=_uid(),
            tenant_id=tenant_id or f"tenant-{_uid()[:8]}",
            plan_id=plan.id,
            status=status,
            billing_cycle=billing_cycle,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db.add(sub)
        await db.flush()
        return sub

    return _make
