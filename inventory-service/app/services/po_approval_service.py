"""Purchase Order approval workflow service."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.db.models import POStatus, PurchaseOrder
from app.db.models.purchase_order import POApprovalLog


class POApprovalService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def requires_approval(self, po_total: Decimal, tenant_id: str) -> bool:
        """Check if the tenant requires PO approval and if the total exceeds threshold."""
        from app.db.models.config import TenantInventoryConfig
        result = await self.db.execute(
            select(TenantInventoryConfig).where(TenantInventoryConfig.tenant_id == tenant_id)
        )
        config = result.scalar_one_or_none()
        if not config or not config.require_po_approval:
            return False
        if config.po_approval_threshold and po_total < config.po_approval_threshold:
            return False
        return True

    async def submit_for_approval(
        self, po: PurchaseOrder, user_id: str, user_name: str | None = None,
    ) -> PurchaseOrder:
        """Submit PO for approval. Status: draft → pending_approval."""
        if po.status != POStatus.draft:
            raise ValidationError("Solo se pueden enviar a aprobación OCs en borrador")

        po.status = POStatus.pending_approval
        po.approval_required = True

        # Calculate total
        po_total = sum(line.line_total for line in po.lines) if po.lines else Decimal("0")

        log = POApprovalLog(
            id=str(uuid.uuid4()),
            tenant_id=po.tenant_id,
            purchase_order_id=po.id,
            action="submit",
            performed_by=user_id,
            performed_by_name=user_name,
            po_total=po_total,
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(po)
        return po

    async def approve(
        self, po: PurchaseOrder, user_id: str, user_name: str | None = None,
    ) -> PurchaseOrder:
        """Approve PO. Status: pending_approval → approved."""
        if po.status != POStatus.pending_approval:
            raise ValidationError("Solo se pueden aprobar OCs pendientes de aprobación")

        now = datetime.now(timezone.utc)
        po.status = POStatus.approved
        po.approved_by = user_id
        po.approved_at = now
        po.rejected_reason = None
        po.rejected_by = None
        po.rejected_at = None

        po_total = sum(line.line_total for line in po.lines) if po.lines else Decimal("0")

        log = POApprovalLog(
            id=str(uuid.uuid4()),
            tenant_id=po.tenant_id,
            purchase_order_id=po.id,
            action="approve",
            performed_by=user_id,
            performed_by_name=user_name,
            po_total=po_total,
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(po)
        return po

    async def reject(
        self, po: PurchaseOrder, user_id: str, reason: str, user_name: str | None = None,
    ) -> PurchaseOrder:
        """Reject PO. Status: pending_approval → draft (allows re-edit)."""
        if po.status != POStatus.pending_approval:
            raise ValidationError("Solo se pueden rechazar OCs pendientes de aprobación")

        now = datetime.now(timezone.utc)
        po.status = POStatus.draft
        po.rejected_reason = reason
        po.rejected_by = user_id
        po.rejected_at = now
        po.approved_by = None
        po.approved_at = None

        po_total = sum(line.line_total for line in po.lines) if po.lines else Decimal("0")

        log = POApprovalLog(
            id=str(uuid.uuid4()),
            tenant_id=po.tenant_id,
            purchase_order_id=po.id,
            action="reject",
            performed_by=user_id,
            performed_by_name=user_name,
            reason=reason,
            po_total=po_total,
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(po)
        return po

    async def get_approval_log(self, po_id: str, tenant_id: str) -> list[POApprovalLog]:
        """Get approval history for a PO."""
        result = await self.db.execute(
            select(POApprovalLog)
            .where(POApprovalLog.purchase_order_id == po_id, POApprovalLog.tenant_id == tenant_id)
            .order_by(POApprovalLog.created_at.desc())
        )
        return list(result.scalars().all())
