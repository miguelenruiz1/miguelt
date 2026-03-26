"""Repository for AnchorRule CRUD."""
from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.anchor_rule import AnchorRule


class AnchorRuleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_for_tenant(
        self, tenant_id: str, entity_type: str | None = None, active_only: bool = True,
    ) -> Sequence[AnchorRule]:
        q = select(AnchorRule).where(AnchorRule.tenant_id == tenant_id)
        if entity_type:
            q = q.where(AnchorRule.entity_type == entity_type)
        if active_only:
            q = q.where(AnchorRule.is_active == True)
        q = q.order_by(AnchorRule.priority.desc(), AnchorRule.created_at)
        result = await self._db.execute(q)
        return result.scalars().all()

    async def get(self, rule_id: str, tenant_id: str) -> AnchorRule | None:
        q = select(AnchorRule).where(
            AnchorRule.id == rule_id, AnchorRule.tenant_id == tenant_id
        )
        result = await self._db.execute(q)
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> AnchorRule:
        rule = AnchorRule(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            **data,
        )
        self._db.add(rule)
        await self._db.flush()
        return rule

    async def update(self, rule: AnchorRule, data: dict) -> AnchorRule:
        for k, v in data.items():
            if v is not None and hasattr(rule, k):
                setattr(rule, k, v)
        await self._db.flush()
        return rule

    async def delete(self, rule: AnchorRule) -> None:
        await self._db.delete(rule)
        await self._db.flush()

    async def get_matching_rules(
        self, tenant_id: str, entity_type: str, trigger_event: str,
    ) -> Sequence[AnchorRule]:
        """Get active rules matching entity_type and trigger_event, ordered by priority."""
        q = (
            select(AnchorRule)
            .where(
                AnchorRule.tenant_id == tenant_id,
                AnchorRule.entity_type == entity_type,
                AnchorRule.trigger_event == trigger_event,
                AnchorRule.is_active == True,
            )
            .order_by(AnchorRule.priority.desc())
        )
        result = await self._db.execute(q)
        return result.scalars().all()
