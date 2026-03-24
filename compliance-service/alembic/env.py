"""Alembic environment — async-compatible using run_sync."""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.db.base import Base  # noqa: E402
from app.models.framework import ComplianceFramework  # noqa: F401, E402
from app.models.activation import TenantFrameworkActivation  # noqa: F401, E402
from app.models.plot import CompliancePlot  # noqa: F401, E402
from app.models.record import ComplianceRecord  # noqa: F401, E402
from app.models.plot_link import CompliancePlotLink  # noqa: F401, E402

target_metadata = Base.metadata


def get_async_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if url:
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    ini_url = config.get_main_option("sqlalchemy.url", "")
    if ini_url.startswith("postgresql://"):
        ini_url = ini_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return ini_url


def get_sync_url() -> str:
    return get_async_url().replace("postgresql+asyncpg://", "postgresql://", 1)


def run_migrations_offline() -> None:
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
