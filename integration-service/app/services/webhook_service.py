"""Webhook subscription management and outbound event delivery."""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.integration import WebhookSubscription, WebhookDeliveryLog


# Retry backoff intervals (in minutes)
RETRY_BACKOFF = [1, 5, 30, 120, 1440]  # 1min, 5min, 30min, 2h, 24h


class WebhookService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Subscriptions CRUD ───────────────────────────────────────────────────

    async def list_subscriptions(self, tenant_id: str) -> list[WebhookSubscription]:
        result = await self.db.execute(
            select(WebhookSubscription)
            .where(WebhookSubscription.tenant_id == tenant_id)
            .order_by(WebhookSubscription.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_subscription(self, tenant_id: str, sub_id: str) -> WebhookSubscription | None:
        result = await self.db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.id == sub_id,
                WebhookSubscription.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_subscription(self, tenant_id: str, data: dict, created_by: str | None = None) -> WebhookSubscription:
        secret = data.get("secret") or hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:40]
        sub = WebhookSubscription(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=data["name"],
            target_url=data["target_url"],
            secret=secret,
            events=data.get("events", []),
            headers=data.get("headers", {}),
            is_active=data.get("is_active", True),
            retry_policy=data.get("retry_policy", "exponential"),
            max_retries=data.get("max_retries", 5),
            created_by=created_by,
        )
        self.db.add(sub)
        await self.db.flush()
        return sub

    async def update_subscription(self, tenant_id: str, sub_id: str, data: dict) -> WebhookSubscription | None:
        sub = await self.get_subscription(tenant_id, sub_id)
        if not sub:
            return None
        for k, v in data.items():
            if v is not None and hasattr(sub, k):
                setattr(sub, k, v)
        await self.db.flush()
        return sub

    async def delete_subscription(self, tenant_id: str, sub_id: str) -> bool:
        sub = await self.get_subscription(tenant_id, sub_id)
        if not sub:
            return False
        await self.db.delete(sub)
        await self.db.flush()
        return True

    # ── Event Dispatch ────────────────────────────────────────────────────────

    async def dispatch_event(self, tenant_id: str, event_type: str, payload: dict, source_service: str = "unknown"):
        """Find all active subscriptions matching this event and deliver."""
        subs = await self.db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.tenant_id == tenant_id,
                WebhookSubscription.is_active.is_(True),
            )
        )
        subscriptions = list(subs.scalars().all())

        results = []
        for sub in subscriptions:
            # Check if subscription listens to this event (empty = all events)
            events_list = sub.events if isinstance(sub.events, list) else []
            if events_list and event_type not in events_list:
                continue

            # Build full payload
            full_payload = {
                "event": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tenant_id": tenant_id,
                "source": source_service,
                "data": payload,
            }

            # Create delivery log
            delivery = WebhookDeliveryLog(
                id=str(uuid.uuid4()),
                subscription_id=sub.id,
                tenant_id=tenant_id,
                event_type=event_type,
                payload=full_payload,
                status="pending",
                attempts=0,
            )
            self.db.add(delivery)
            await self.db.flush()

            # Attempt delivery
            success = await self._deliver(sub, delivery, full_payload)
            results.append({"subscription_id": sub.id, "delivery_id": delivery.id, "success": success})

            # Update subscription last triggered
            sub.last_triggered_at = datetime.now(timezone.utc)

        await self.db.flush()
        return results

    async def _deliver(self, sub: WebhookSubscription, delivery: WebhookDeliveryLog, payload: dict) -> bool:
        """Send webhook to target URL with HMAC signature."""
        body = json.dumps(payload, default=str)

        # Sign payload
        signature = ""
        if sub.secret:
            signature = "sha256=" + hmac.new(
                sub.secret.encode(), body.encode(), hashlib.sha256
            ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Trace-Event": payload.get("event", ""),
            "X-Trace-Timestamp": payload.get("timestamp", ""),
            "X-Trace-Signature": signature,
            "X-Trace-Delivery-Id": delivery.id,
            "User-Agent": "Trace-Webhook/1.0",
        }
        # Add custom headers from subscription
        if isinstance(sub.headers, dict):
            headers.update(sub.headers)

        delivery.attempts += 1

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(sub.target_url, content=body, headers=headers)
                delivery.http_status = resp.status_code
                delivery.response_body = resp.text[:2000] if resp.text else None

                if 200 <= resp.status_code < 300:
                    delivery.status = "delivered"
                    delivery.delivered_at = datetime.now(timezone.utc)
                    return True
                else:
                    delivery.status = "failed"
                    self._schedule_retry(sub, delivery)
                    return False
        except Exception as exc:
            delivery.status = "failed"
            delivery.response_body = str(exc)[:2000]
            self._schedule_retry(sub, delivery)
            return False

    def _schedule_retry(self, sub: WebhookSubscription, delivery: WebhookDeliveryLog):
        """Schedule next retry with exponential backoff."""
        if sub.retry_policy == "none" or delivery.attempts >= sub.max_retries:
            delivery.status = "failed"
            return
        idx = min(delivery.attempts - 1, len(RETRY_BACKOFF) - 1)
        minutes = RETRY_BACKOFF[idx]
        delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        delivery.status = "pending"

    # ── Delivery History ──────────────────────────────────────────────────────

    async def list_deliveries(self, tenant_id: str, subscription_id: str | None = None,
                               status: str | None = None, offset: int = 0, limit: int = 50):
        q = select(WebhookDeliveryLog).where(WebhookDeliveryLog.tenant_id == tenant_id)
        if subscription_id:
            q = q.where(WebhookDeliveryLog.subscription_id == subscription_id)
        if status:
            q = q.where(WebhookDeliveryLog.status == status)
        q = q.order_by(WebhookDeliveryLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    # ── Test Delivery ─────────────────────────────────────────────────────────

    async def send_test(self, tenant_id: str, sub_id: str) -> dict:
        """Send a test event to a subscription."""
        sub = await self.get_subscription(tenant_id, sub_id)
        if not sub:
            return {"error": "Subscription not found"}

        test_payload = {
            "event": "test.ping",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "source": "integration-service",
            "data": {"message": "This is a test webhook from Trace", "subscription_id": sub.id},
        }

        delivery = WebhookDeliveryLog(
            id=str(uuid.uuid4()),
            subscription_id=sub.id,
            tenant_id=tenant_id,
            event_type="test.ping",
            payload=test_payload,
            status="pending",
            attempts=0,
        )
        self.db.add(delivery)
        await self.db.flush()

        success = await self._deliver(sub, delivery, test_payload)
        await self.db.flush()

        return {
            "delivery_id": delivery.id,
            "success": success,
            "http_status": delivery.http_status,
            "response": delivery.response_body,
        }
