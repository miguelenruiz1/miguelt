"""Alembic environment — async-compatible using run_sync."""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Alembic Config
config = context.config

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models so Alembic can detect changes
from app.db.base import Base  # noqa: E402
from app.db.models import RegistryWallet, Asset, CustodyEvent  # noqa: F401, E402

target_metadata = Base.metadata


def get_async_url() -> str:
    """
    Return the async URL (postgresql+asyncpg://) for use with async_engine_from_config.
    Reads DATABASE_URL env var first; falls back to alembic.ini.
    """
    url = os.environ.get("DATABASE_URL", "")
    if url:
        # Ensure async driver — env var might already be asyncpg or plain postgresql
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    # alembic.ini has a sync URL — upgrade it to async
    ini_url = config.get_main_option("sqlalchemy.url", "")
    if ini_url.startswith("postgresql://"):
        ini_url = ini_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return ini_url


def get_sync_url() -> str:
    """
    Return a sync URL (postgresql://) for offline mode (no real connection needed).
    """
    return get_async_url().replace("postgresql+asyncpg://", "postgresql://", 1)


def run_migrations_offline() -> None:
    """Generate SQL without connecting — uses sync URL for literal binds."""
    url = get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Connect with asyncpg and run migrations via run_sync."""
    url = get_async_url()
    connectable = async_engine_from_config(
        {"sqlalchemy.url": url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
