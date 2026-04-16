"""Sub-conftest for pure unit tests.

Overrides the parent conftest's `_clean_tables` autouse fixture so we don't
require a Postgres connection just to exercise in-process domain logic.
"""
from __future__ import annotations

import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    """No-op override. Unit tests don't touch the DB."""
    yield
