"""Redis-backed idempotency helpers.

Flow:
1. Client sends POST with header ``Idempotency-Key: <uuid>``
2. Before processing, check Redis for key → if found, return cached response
3. After processing, store response in Redis with TTL
4. If same key arrives while processing (race), return 409 Conflict
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

import redis.asyncio as aioredis

from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)

_PROCESSING_SENTINEL = "__PROCESSING__"


class IdempotencyStore:
    """Thin async wrapper around Redis for idempotency key management."""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client
        self._ttl = get_settings().IDEMPOTENCY_TTL

    def _key(self, idempotency_key: str, namespace: str) -> str:
        # Namespace prevents key collisions across different endpoints
        combined = f"{namespace}:{idempotency_key}"
        return f"idem:{hashlib.sha256(combined.encode()).hexdigest()}"

    async def get_cached_response(
        self, idempotency_key: str, namespace: str
    ) -> dict[str, Any] | None:
        """Return cached response dict if it exists, else None."""
        raw = await self._redis.get(self._key(idempotency_key, namespace))
        if raw is None:
            return None
        if raw == _PROCESSING_SENTINEL.encode():
            # Still being processed by another worker
            return {"__processing__": True}
        return json.loads(raw)

    async def mark_processing(self, idempotency_key: str, namespace: str) -> bool:
        """
        Atomically mark this key as being processed (SET NX).
        Returns True if we acquired the lock, False if already taken.
        """
        key = self._key(idempotency_key, namespace)
        result = await self._redis.set(
            key, _PROCESSING_SENTINEL, ex=60, nx=True  # 60s processing window
        )
        return result is not None

    async def save_response(
        self, idempotency_key: str, namespace: str, response: dict[str, Any]
    ) -> None:
        """Persist the response so future duplicate requests return it."""
        key = self._key(idempotency_key, namespace)
        await self._redis.set(key, json.dumps(response), ex=self._ttl)
        log.debug("idempotency_response_cached", namespace=namespace, key=key)

    async def delete(self, idempotency_key: str, namespace: str) -> None:
        await self._redis.delete(self._key(idempotency_key, namespace))
