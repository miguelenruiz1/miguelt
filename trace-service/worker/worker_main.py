"""
ARQ worker — processes Solana anchor jobs with retries + exponential backoff.

Why ARQ over Celery?
- Natively async (no eventlet/gevent hacks).
- First-class asyncio support — shares the same event loop as the app.
- Simple Redis-backed queue, minimal overhead.
- Retry logic with exponential backoff is built-in.

Worker flow per job:
1. Fetch CustodyEvent from DB.
2. Call SolanaClient.send_memo(event_hash).
3. If successful: mark event as anchored + store tx_sig.
4. If error: increment anchor_attempts + store error message.
   ARQ's retry mechanism re-enqueues with exponential backoff.
"""
from __future__ import annotations

import asyncio
import math
import os
import urllib.parse
from datetime import datetime, timezone
from typing import Any

import structlog
from arq import cron  # type: ignore
from arq.connections import RedisSettings  # type: ignore

# ─── Logging ──────────────────────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

log = structlog.get_logger(__name__)


# ─── Job: anchor_event ────────────────────────────────────────────────────────

async def anchor_event(ctx: dict[str, Any], event_id: str) -> dict[str, Any]:
    """
    Anchor a single CustodyEvent on Solana via the Memo Program.

    ARQ passes `ctx` which contains resources initialized in startup().
    Returns a dict describing the outcome (logged by ARQ).
    """
    db_factory = ctx["db_factory"]
    solana_client = ctx["solana_client"]
    settings = ctx["settings"]

    log.info("anchor_job_started", event_id=event_id)

    async with db_factory() as session:
        from app.repositories.custody_repo import CustodyEventRepository
        import uuid as _uuid

        repo = CustodyEventRepository(session)
        eid = _uuid.UUID(event_id)
        event = await repo.get_by_id(eid)

        if event is None:
            log.warning("anchor_event_not_found", event_id=event_id)
            return {"status": "not_found", "event_id": event_id}

        if event.anchored:
            log.info("anchor_already_done", event_id=event_id, sig=event.solana_tx_sig)
            return {"status": "already_anchored", "sig": event.solana_tx_sig}

        try:
            tx_sig = await solana_client.send_memo(event.event_hash)
            await repo.mark_anchored(eid, tx_sig)
            await session.commit()
            log.info(
                "anchor_success",
                event_id=event_id,
                tx_sig=tx_sig,
                attempts=event.anchor_attempts + 1,
            )
            return {"status": "anchored", "sig": tx_sig}

        except Exception as exc:
            error_msg = str(exc)[:500]
            await repo.increment_anchor_attempt(eid, error=error_msg)
            await session.commit()
            log.error(
                "anchor_failed",
                event_id=event_id,
                attempts=event.anchor_attempts + 1,
                error=error_msg,
            )
            # Re-raise so ARQ applies retry policy
            raise


# ─── Job: anchor_generic (Anchoring-as-a-Service) ────────────────────────────

async def anchor_generic(ctx: dict[str, Any], anchor_request_id: str) -> dict[str, Any]:
    """
    Anchor a generic AnchorRequest on Solana via the Memo Program.
    Called by other microservices through the /api/v1/anchoring/hash endpoint.
    """
    db_factory = ctx["db_factory"]
    solana_client = ctx["solana_client"]
    settings = ctx["settings"]

    log.info("anchor_generic_started", anchor_request_id=anchor_request_id)

    async with db_factory() as session:
        from app.repositories.anchor_repo import AnchorRequestRepository
        import uuid as _uuid

        repo = AnchorRequestRepository(session)
        ar = await repo.get_by_id(_uuid.UUID(anchor_request_id))

        if ar is None:
            log.warning("anchor_generic_not_found", anchor_request_id=anchor_request_id)
            return {"status": "not_found", "id": anchor_request_id}

        if ar.anchor_status == "anchored":
            log.info("anchor_generic_already_done", id=anchor_request_id, sig=ar.solana_tx_sig)
            return {"status": "already_anchored", "sig": ar.solana_tx_sig}

        try:
            tx_sig = await solana_client.send_memo(ar.payload_hash)
            await repo.mark_anchored(ar.id, tx_sig)
            await session.commit()
            log.info(
                "anchor_generic_success",
                anchor_request_id=anchor_request_id,
                tx_sig=tx_sig,
                attempts=ar.attempts + 1,
            )

            # Fire callback if configured
            if ar.callback_url:
                await _fire_callback(ar.callback_url, ar.payload_hash, tx_sig)

            return {"status": "anchored", "sig": tx_sig}

        except Exception as exc:
            error_msg = str(exc)[:500]
            await repo.increment_attempt(ar.id, error=error_msg)
            await session.commit()
            log.error(
                "anchor_generic_failed",
                anchor_request_id=anchor_request_id,
                attempts=ar.attempts + 1,
                error=error_msg,
            )
            raise


async def _fire_callback(url: str, payload_hash: str, tx_sig: str) -> None:
    """Best-effort POST to the callback URL when anchoring completes."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={
                "payload_hash": payload_hash,
                "solana_tx_sig": tx_sig,
                "anchor_status": "anchored",
            })
        log.info("anchor_callback_sent", url=url, hash=payload_hash[:16])
    except Exception as exc:
        log.warning("anchor_callback_failed", url=url, exc=str(exc))


# ─── Cron: sweep unanchored events ───────────────────────────────────────────

async def retry_blockchain_mint(ctx: dict[str, Any], asset_id_str: str) -> None:
    """
    Retry minting a cNFT for an asset with blockchain_status = FAILED.
    Executed by the ARQ worker with exponential backoff.
    """
    import uuid as _uuid

    db_factory = ctx["db_factory"]
    log.info("blockchain_retry_started", asset_id=asset_id_str)

    async with db_factory() as session:
        from app.repositories.custody_repo import AssetRepository
        from app.repositories.tenant_repo import TenantRepository
        from app.services.blockchain_service import BlockchainService
        from app.clients.provider_factory import get_blockchain_provider

        asset_repo = AssetRepository(session)
        asset = await asset_repo.get_by_id(_uuid.UUID(asset_id_str))

        if not asset:
            log.warning("blockchain_retry_asset_not_found", asset_id=asset_id_str)
            return

        if asset.blockchain_status in ("CONFIRMED", "SIMULATED"):
            log.info("blockchain_retry_already_done", asset_id=asset_id_str, status=asset.blockchain_status)
            return

        tenant_repo = TenantRepository(session)
        tree = await tenant_repo.get_merkle_tree(asset.tenant_id)
        if not tree:
            log.warning("blockchain_retry_no_tree", asset_id=asset_id_str)
            return

        svc = BlockchainService(session, get_blockchain_provider())
        await svc.mint_asset_onchain(
            asset_id=asset.id,
            tenant_id=asset.tenant_id,
            product_type=asset.product_type,
            metadata=asset.metadata_,
            owner_pubkey=asset.current_custodian_wallet,
        )
        await session.commit()

    log.info("blockchain_retry_completed", asset_id=asset_id_str)


async def sweep_pending_anchors(ctx: dict[str, Any]) -> None:
    """
    Periodic sweep for events that never got enqueued or whose jobs were lost.
    Runs every 5 minutes.
    """
    db_factory = ctx["db_factory"]
    settings = ctx["settings"]
    arq_pool = ctx["arq_pool"]

    async with db_factory() as session:
        from app.repositories.custody_repo import CustodyEventRepository

        repo = CustodyEventRepository(session)
        pending = await repo.get_pending_anchor(limit=100)

        enqueued = 0
        for event in pending:
            if event.anchor_attempts >= settings.ANCHOR_MAX_RETRIES:
                continue  # Give up after max retries
            try:
                await arq_pool.enqueue_job(
                    "anchor_event",
                    str(event.id),
                    _queue_name=settings.ANCHOR_QUEUE_NAME,
                )
                enqueued += 1
            except Exception as exc:
                log.warning("sweep_enqueue_failed", event_id=str(event.id), exc=str(exc))

    if enqueued:
        log.info("sweep_enqueued_pending", count=enqueued)

    # Also sweep pending AnchorRequests (Anchoring-as-a-Service)
    async with db_factory() as session:
        from app.repositories.anchor_repo import AnchorRequestRepository

        ar_repo = AnchorRequestRepository(session)
        pending_anchors = await ar_repo.get_pending(limit=100)

        ar_enqueued = 0
        for ar in pending_anchors:
            if ar.attempts >= settings.ANCHOR_MAX_RETRIES:
                continue
            try:
                await arq_pool.enqueue_job(
                    "anchor_generic",
                    str(ar.id),
                    _queue_name=settings.ANCHOR_QUEUE_NAME,
                )
                ar_enqueued += 1
            except Exception as exc:
                log.warning("sweep_ar_enqueue_failed", anchor_id=str(ar.id), exc=str(exc))

    if ar_enqueued:
        log.info("sweep_enqueued_anchor_requests", count=ar_enqueued)


# ─── Lifecycle ────────────────────────────────────────────────────────────────

async def startup(ctx: dict[str, Any]) -> None:
    """Initialize shared resources for the worker."""
    import sys
    sys.path.insert(0, "/app")

    # Force load settings from env
    from app.core.settings import get_settings
    from app.core.logging import configure_logging
    configure_logging()

    settings = get_settings()
    ctx["settings"] = settings

    # DB session factory
    from app.db.session import get_session_factory
    ctx["db_factory"] = get_session_factory()

    # Solana client
    from app.clients.solana_client import get_solana_client
    ctx["solana_client"] = get_solana_client()

    # ARQ pool (for sweep to re-enqueue)
    from arq import create_pool  # type: ignore
    parsed = urllib.parse.urlparse(settings.ARQ_REDIS_URL)
    host = parsed.hostname or "redis"
    port = parsed.port or 6379
    db_num = int(parsed.path.lstrip("/") or "1")
    ctx["arq_pool"] = await create_pool(RedisSettings(host=host, port=port, database=db_num))

    log.info("worker_started", simulation=settings.SOLANA_SIMULATION)


async def shutdown(ctx: dict[str, Any]) -> None:
    """Clean up resources."""
    from app.db.session import close_engine
    from app.clients.solana_client import close_solana_client

    await close_engine()
    await close_solana_client()

    arq_pool = ctx.get("arq_pool")
    if arq_pool:
        await arq_pool.close()

    log.info("worker_stopped")


# ─── Worker Settings ──────────────────────────────────────────────────────────

def _redis_settings() -> RedisSettings:
    url = os.environ.get("ARQ_REDIS_URL", "redis://redis:6379/1")
    parsed = urllib.parse.urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "redis",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or "1"),
    )


class WorkerSettings:
    functions = [anchor_event, retry_blockchain_mint, anchor_generic]
    cron_jobs = [
        cron(sweep_pending_anchors, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55})
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings()
    queue_name = os.environ.get("ANCHOR_QUEUE_NAME", "anchor")
    max_jobs = 20
    job_timeout = 300  # 5 minutes per job
    max_tries = int(os.environ.get("ANCHOR_MAX_RETRIES", "5"))
    keep_result = 3600  # keep result 1h
    retry_jobs = True

    @staticmethod
    def job_retry_delay(attempt: int) -> int:
        """Exponential backoff with jitter: 2^attempt seconds, max 5 minutes."""
        import random
        base = min(2 ** attempt, 300)
        jitter = random.uniform(0, base * 0.2)
        return int(base + jitter)


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/app")

    from arq import run_worker  # type: ignore
    run_worker(WorkerSettings)
