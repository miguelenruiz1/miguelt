"""Orchestration: enqueue anchor jobs to the ARQ worker."""
from __future__ import annotations

import uuid

import redis.asyncio as aioredis
from arq import create_pool  # type: ignore
from arq.connections import RedisSettings  # type: ignore

from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)

_arq_pool = None


async def _get_arq_pool():
    global _arq_pool
    if _arq_pool is None:
        settings = get_settings()
        url = settings.ARQ_REDIS_URL
        # Parse redis url
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or "redis"
        port = parsed.port or 6379
        db = int(parsed.path.lstrip("/") or "1")
        _arq_pool = await create_pool(RedisSettings(host=host, port=port, database=db))
    return _arq_pool


async def enqueue_anchor(event_id: uuid.UUID) -> None:
    """Enqueue an anchor_event job for the given event_id.

    Best-effort: if Redis is down or the pool fails we only log. Safety net
    is the `sweep_pending_anchors` cron which scans CustodyEvent rows that
    never reached CONFIRMED every 5 minutes and re-enqueues them. Job-level
    retries (max_tries=5, exponential backoff) live in WorkerSettings.

    We pass `_job_id=f"anchor:{event_id}"` for dedup: if the caller and the
    sweeper race to enqueue the same event, only one job lands in the queue.
    """
    try:
        pool = await _get_arq_pool()
        job = await pool.enqueue_job(
            "anchor_event",
            str(event_id),
            _job_id=f"anchor:{event_id}",
            _queue_name=get_settings().ANCHOR_QUEUE_NAME,
        )
        log.info("anchor_job_enqueued", event_id=str(event_id), job_id=getattr(job, "job_id", None))
    except Exception as exc:
        # Non-fatal: the sweeper + worker retries guarantee eventual anchoring.
        log.warning("anchor_enqueue_failed", event_id=str(event_id), exc=str(exc))


async def close_arq_pool() -> None:
    global _arq_pool
    if _arq_pool is not None:
        await _arq_pool.close()
        _arq_pool = None
