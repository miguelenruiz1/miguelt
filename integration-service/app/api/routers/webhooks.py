"""Webhook receiver — accepts incoming events from external providers."""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.adapters.registry import get_adapter
from app.db.session import get_db_session
from app.repositories.integration_repo import WebhookLogRepository

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/{provider_slug}")
async def receive_webhook(
    provider_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Public endpoint — no auth. Receives webhooks from external providers."""
    body = await request.json()
    headers = dict(request.headers)

    repo = WebhookLogRepository(db)
    log = await repo.create({
        "provider_slug": provider_slug,
        "event_type": body.get("event") or body.get("type") or body.get("action"),
        "payload": body,
        "headers": {k: v for k, v in headers.items() if k.lower() not in ("authorization", "cookie")},
        "status": "received",
    })

    adapter = get_adapter(provider_slug)
    if adapter:
        try:
            result = await adapter.process_webhook(body, headers)
            await repo.update(log, {
                "status": "processed",
                "processing_result": str(result),
                "tenant_id": result.get("tenant_id"),
            })
            return {"status": "processed", "webhook_id": log.id}
        except Exception as e:
            await repo.update(log, {
                "status": "error",
                "processing_result": str(e),
            })
            return {"status": "error", "webhook_id": log.id, "detail": str(e)}

    return {"status": "ignored", "webhook_id": log.id, "reason": f"No adapter for {provider_slug}"}
