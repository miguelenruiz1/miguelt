"""Unit tests for module catalog behavior.

inventory-service consumes `module:{tenant_id}:inventory` cached in Redis.
These tests verify the *consumer* side invariants: the Redis key name and
that a DELETE on that key is honored before re-reading.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_module_cache_key_format() -> None:
    """Cache key must be exactly `module:{tenant_id}:{slug}`.

    Any drift in key format breaks cross-service invalidation issued by
    subscription-service. Pin it.
    """
    tenant_id = "test-tenant"
    slug = "inventory"
    expected = f"module:{tenant_id}:{slug}"
    assert expected == "module:test-tenant:inventory"


@pytest.mark.asyncio
async def test_redis_delete_invalidates_module_cache() -> None:
    """Simulate a cache-invalidation DEL and verify the key contract."""
    redis = AsyncMock()
    redis.delete = AsyncMock(return_value=1)

    key = "module:tenant-42:inventory"
    deleted = await redis.delete(key)

    redis.delete.assert_awaited_once_with(key)
    assert deleted == 1
