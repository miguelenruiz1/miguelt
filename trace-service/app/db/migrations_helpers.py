"""Helpers for running Alembic migrations programmatically."""
import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config


def get_alembic_config(dsn: str | None = None) -> Config:
    base_dir = Path(__file__).parent.parent.parent
    cfg = Config(str(base_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(base_dir / "alembic"))
    if dsn:
        # Convert async DSN to sync for Alembic
        sync_dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
        cfg.set_main_option("sqlalchemy.url", sync_dsn)
    return cfg


def run_migrations_sync(dsn: str | None = None) -> None:
    """Run Alembic upgrade head synchronously (used in scripts)."""
    cfg = get_alembic_config(dsn)
    command.upgrade(cfg, "head")


async def run_migrations_async(dsn: str | None = None) -> None:
    """Run Alembic migrations in a thread to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_migrations_sync, dsn)
