"""Shared test fixtures — in-memory SQLite + async test client."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base

# ── Async event loop ──────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── In-memory SQLite engine ───────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def engine():
    # Patch JSONB → JSON for SQLite compatibility
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy import JSON, event as sa_event

    original_compile = None

    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Register JSONB as JSON for SQLite
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
    if not hasattr(SQLiteTypeCompiler, 'visit_JSONB'):
        SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: self.visit_JSON(type_, **kw)

    # Also handle Enum(native_enum=False) with String
    import app.db.models  # noqa: F401
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


# ── Redis mock ────────────────────────────────────────────────────────────────

@pytest.fixture
def redis_mock():
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.set = AsyncMock()
    r.setex = AsyncMock()
    r.delete = AsyncMock(return_value=1)
    r.incr = AsyncMock()
    r.expire = AsyncMock()
    r.pipeline = MagicMock()
    pipe = AsyncMock()
    pipe.incr = MagicMock()
    pipe.expire = MagicMock()
    pipe.execute = AsyncMock()
    r.pipeline.return_value = pipe
    r.scan_iter = AsyncMock(return_value=iter([]))
    return r


# ── Test app + client ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def app(db, redis_mock):
    """Create FastAPI app with overridden deps."""
    from app.main import create_app
    from app.db.session import get_db_session
    from app.api.deps import get_redis, get_current_user, require_inventory_module, require_production_module

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
            "permissions": ["inventory.view", "inventory.manage", "inventory.admin", "inventory.config", "reports.view"],
        }

    async def _override_module():
        return {
            "id": "test-user-1", "email": "test@tracelog.co",
            "tenant_id": "test-tenant", "is_superuser": True,
            "permissions": ["inventory.view", "inventory.manage", "inventory.admin", "inventory.config", "reports.view", "production.view", "production.manage"],
        }

    application.dependency_overrides[get_db_session] = _override_db
    application.dependency_overrides[get_redis] = _override_redis
    application.dependency_overrides[get_current_user] = _override_user
    application.dependency_overrides[require_inventory_module] = _override_module
    application.dependency_overrides[require_production_module] = _override_module

    yield application


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Helpers ───────────────────────────────────────────────────────────────────

def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)
