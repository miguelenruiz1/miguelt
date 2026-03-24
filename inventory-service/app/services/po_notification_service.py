"""Purchase Order notification service — fire-and-forget via user-service."""
from __future__ import annotations

import os
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-api:8001")


class PONotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _send(self, tenant_id: str, to_email: str, template_slug: str, context: dict) -> None:
        """Fire-and-forget notification via user-service."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{USER_SERVICE_URL}/api/v1/notifications/send",
                    json={"to": to_email, "template_slug": template_slug, "context": context},
                    headers={"X-Tenant-Id": tenant_id, "X-Service-Key": "internal"},
                )
        except Exception as e:
            logger.warning("Notification failed: %s", e)

    async def notify_margin_danger(
        self,
        tenant_id: str,
        product_name: str,
        product_sku: str,
        new_cost: float,
        actual_margin: float,
        minimum_margin: float,
        po_number: str,
    ) -> None:
        """Alert when a new purchase cost drops margin below minimum."""
        logger.warning(
            "MARGIN DANGER: %s (%s) — new cost $%.2f, margin %.1f%% < min %.1f%% (PO %s)",
            product_name, product_sku, new_cost, actual_margin, minimum_margin, po_number,
        )
        # Log as an audit entry too
        from app.services.audit_service import InventoryAuditService
        audit = InventoryAuditService(self.db)
        await audit.log(
            tenant_id=tenant_id,
            user={"id": "system", "email": "system@trace.app", "full_name": "Sistema"},
            action="inventory.margin.danger",
            resource_type="product",
            resource_id=product_sku,
            new_data={
                "product_name": product_name,
                "product_sku": product_sku,
                "new_cost": new_cost,
                "actual_margin_pct": actual_margin,
                "minimum_margin_pct": minimum_margin,
                "po_number": po_number,
                "message": f"Alerta: El nuevo costo de {product_name} (${new_cost:,.0f}) deja el margen en {actual_margin}%, por debajo del mínimo aceptable ({minimum_margin}%)",
            },
        )

    async def notify_po_sent(self, tenant_id: str, po_number: str, supplier_name: str, supplier_email: str) -> None:
        """Notify that a PO was sent to supplier."""
        logger.info("PO %s sent to %s (%s)", po_number, supplier_name, supplier_email)

    async def notify_po_approved(self, tenant_id: str, po_number: str, approved_by_name: str) -> None:
        """Notify that a PO was approved."""
        logger.info("PO %s approved by %s", po_number, approved_by_name)

    async def notify_po_rejected(self, tenant_id: str, po_number: str, rejected_by_name: str, reason: str) -> None:
        """Notify that a PO was rejected."""
        logger.info("PO %s rejected by %s: %s", po_number, rejected_by_name, reason)
