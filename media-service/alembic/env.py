"""Alembic environment — async-compatible."""
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

from app.db.base import Base
from app.db.models import Tenant, MediaFile  # noqa: F401

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


def run_migrations_offline() -> None:
    url = get_async_url().replace("postgresql+asyncpg://", "postgresql://", 1)
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        {"sqlalchemy.url": get_async_url()}, prefix="sqlalchemy.", poolclass=pool.NullPool,
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
