"""Approval workflow for sales orders that exceed a tenant-configured threshold."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.db.models.sales_order import SOApprovalLog, SalesOrder, TenantInventoryConfig


class ApprovalService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_tenant_config(self, tenant_id: str) -> TenantInventoryConfig | None:
        result = await self.db.execute(
            select(TenantInventoryConfig).where(TenantInventoryConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_config(self, tenant_id: str) -> TenantInventoryConfig:
        config = await self.get_tenant_config(tenant_id)
        if not config:
            config = TenantInventoryConfig(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
            )
            self.db.add(config)
            await self.db.flush()
        return config

    async def requires_approval(self, so_total: Decimal, tenant_id: str) -> bool:
        config = await self.get_tenant_config(tenant_id)
        if config is None or config.so_approval_threshold is None:
            return False
        return so_total >= config.so_approval_threshold

    async def request_approval(
        self, so: SalesOrder, requested_by: str, requested_by_name: str | None = None,
    ) -> None:
        from app.db.models.enums import SalesOrderStatus
        so.status = SalesOrderStatus.pending_approval
        so.approval_required = True
        so.approval_requested_at = datetime.now(timezone.utc)
        self.db.add(SOApprovalLog(
            id=str(uuid.uuid4()),
            tenant_id=so.tenant_id,
            sales_order_id=so.id,
            action="requested",
            performed_by=requested_by,
            performed_by_name=requested_by_name,
            so_total_at_action=so.total,
        ))
        await self.db.flush()

    async def approve(
        self, so: SalesOrder, approved_by: str, approved_by_name: str | None = None,
    ) -> None:
        from app.db.models.enums import SalesOrderStatus
        if so.status != SalesOrderStatus.pending_approval:
            raise ValidationError("El SO no está pendiente de aprobación")
        if so.created_by and so.created_by == approved_by:
            raise ValidationError("No puedes aprobar tu propio SO")

        so.approved_by = approved_by
        so.approved_at = datetime.now(timezone.utc)
        self.db.add(SOApprovalLog(
            id=str(uuid.uuid4()),
            tenant_id=so.tenant_id,
            sales_order_id=so.id,
            action="approved",
            performed_by=approved_by,
            performed_by_name=approved_by_name,
            so_total_at_action=so.total,
        ))
        await self.db.flush()

    async def reject(
        self, so: SalesOrder, rejected_by: str, reason: str,
        rejected_by_name: str | None = None,
    ) -> None:
        from app.db.models.enums import SalesOrderStatus
        if so.status != SalesOrderStatus.pending_approval:
            raise ValidationError("El SO no está pendiente de aprobación")
        if not reason or len(reason.strip()) < 10:
            raise ValidationError("El motivo de rechazo debe tener al menos 10 caracteres")

        so.status = SalesOrderStatus.rejected
        so.rejected_by = rejected_by
        so.rejected_at = datetime.now(timezone.utc)
        so.rejection_reason = reason.strip()
        self.db.add(SOApprovalLog(
            id=str(uuid.uuid4()),
            tenant_id=so.tenant_id,
            sales_order_id=so.id,
            action="rejected",
            performed_by=rejected_by,
            performed_by_name=rejected_by_name,
            reason=reason.strip(),
            so_total_at_action=so.total,
        ))
        await self.db.flush()

    async def resubmit(self, so: SalesOrder, resubmitted_by: str, resubmitted_by_name: str | None = None) -> None:
        from app.db.models.enums import SalesOrderStatus
        if so.status != SalesOrderStatus.rejected:
            raise ValidationError("Solo se pueden re-enviar SOs rechazados")

        so.status = SalesOrderStatus.pending_approval
        so.rejection_reason = None
        so.rejected_by = None
        so.rejected_at = None
        so.approval_requested_at = datetime.now(timezone.utc)
        self.db.add(SOApprovalLog(
            id=str(uuid.uuid4()),
            tenant_id=so.tenant_id,
            sales_order_id=so.id,
            action="resubmitted",
            performed_by=resubmitted_by,
            performed_by_name=resubmitted_by_name,
            so_total_at_action=so.total,
        ))
        await self.db.flush()

    async def get_approval_log(self, so_id: str) -> list[SOApprovalLog]:
        result = await self.db.execute(
            select(SOApprovalLog)
            .where(SOApprovalLog.sales_order_id == so_id)
            .order_by(SOApprovalLog.created_at.asc())
        )
        return list(result.scalars().all())

    async def set_threshold(self, tenant_id: str, threshold: Decimal | None) -> TenantInventoryConfig:
        config = await self.get_or_create_config(tenant_id)
        config.so_approval_threshold = threshold
        config.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return config
