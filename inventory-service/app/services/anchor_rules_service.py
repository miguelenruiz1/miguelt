"""Business logic for anchor rules evaluation and management.

Anchor rules define WHEN and WHAT gets anchored on blockchain.
Rules are evaluated against event context (entity data) to decide
whether to trigger anchoring — acting as pragmatic "smart contracts".
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.repositories.anchor_rule_repo import AnchorRuleRepository

log = get_logger(__name__)


class AnchorRulesService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AnchorRuleRepository(db)

    # ─── CRUD ────────────────────────────────────────────────────────────

    async def list_rules(self, tenant_id: str, entity_type: str | None = None):
        return await self.repo.list_for_tenant(tenant_id, entity_type, active_only=False)

    async def get_rule(self, rule_id: str, tenant_id: str):
        rule = await self.repo.get(rule_id, tenant_id)
        if not rule:
            raise NotFoundError("Regla de anclaje no encontrada")
        return rule

    async def create_rule(self, tenant_id: str, data: dict):
        return await self.repo.create(tenant_id, data)

    async def update_rule(self, rule_id: str, tenant_id: str, data: dict):
        rule = await self.get_rule(rule_id, tenant_id)
        return await self.repo.update(rule, data)

    async def delete_rule(self, rule_id: str, tenant_id: str):
        rule = await self.get_rule(rule_id, tenant_id)
        await self.repo.delete(rule)

    # ─── Rule Evaluation Engine ──────────────────────────────────────────

    async def should_anchor(
        self,
        tenant_id: str,
        entity_type: str,
        trigger_event: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Evaluate anchor rules for a given event.

        Returns:
            {"should_anchor": bool, "should_mint_cnft": bool, "matched_rule": str | None}

        Context dict should contain entity-specific data for condition evaluation:
        - For POs: {"total": Decimal, "supplier_id": str, "product_types": [...]}
        - For SOs: {"total": Decimal, "customer_id": str}
        - For batches: {"product_id": str, "product_type_id": str}
        """
        rules = await self.repo.get_matching_rules(tenant_id, entity_type, trigger_event)

        # If no rules exist, default to anchor everything (backward compatible)
        if not rules:
            return {"should_anchor": True, "should_mint_cnft": False, "matched_rule": None}

        # Evaluate rules in priority order; first match wins
        for rule in rules:
            if self._evaluate_conditions(rule.conditions, context):
                actions = rule.actions or {}
                log.info(
                    "anchor_rule_matched",
                    rule_id=rule.id,
                    rule_name=rule.name,
                    entity_type=entity_type,
                    trigger_event=trigger_event,
                )
                return {
                    "should_anchor": actions.get("anchor", True),
                    "should_mint_cnft": actions.get("mint_cnft", False),
                    "matched_rule": rule.id,
                }

        # No rule matched — don't anchor
        return {"should_anchor": False, "should_mint_cnft": False, "matched_rule": None}

    def _evaluate_conditions(self, conditions: dict, context: dict) -> bool:
        """
        Evaluate rule conditions against event context.

        Supported conditions:
        - min_value: total must be >= this value
        - max_value: total must be <= this value
        - product_types: list of product_type_ids that must match
        - supplier_ids: list of supplier_ids that must match
        - customer_ids: list of customer_ids that must match
        - always: if true, always matches (catch-all rule)
        """
        if not conditions:
            return True  # Empty conditions = always match

        if conditions.get("always"):
            return True

        # min_value check
        if "min_value" in conditions:
            total = context.get("total")
            if total is None:
                return False
            if Decimal(str(total)) < Decimal(str(conditions["min_value"])):
                return False

        # max_value check
        if "max_value" in conditions:
            total = context.get("total")
            if total is None:
                return False
            if Decimal(str(total)) > Decimal(str(conditions["max_value"])):
                return False

        # product_types check
        if "product_types" in conditions:
            allowed = set(conditions["product_types"])
            ctx_types = context.get("product_types") or context.get("product_type_id")
            if isinstance(ctx_types, str):
                ctx_types = [ctx_types]
            if not ctx_types or not set(ctx_types) & allowed:
                return False

        # supplier_ids check
        if "supplier_ids" in conditions:
            if context.get("supplier_id") not in conditions["supplier_ids"]:
                return False

        # customer_ids check
        if "customer_ids" in conditions:
            if context.get("customer_id") not in conditions["customer_ids"]:
                return False

        return True

    # ─── Seed default rules ─────────────────────────────────────────────

    async def seed_defaults(self, tenant_id: str) -> list:
        """Create default anchor rules for a new tenant."""
        existing = await self.repo.list_for_tenant(tenant_id, active_only=False)
        if existing:
            return []

        defaults = [
            {
                "name": "Anclar todas las recepciones de OC",
                "entity_type": "purchase_order",
                "trigger_event": "received",
                "conditions": {"always": True},
                "actions": {"anchor": True, "mint_cnft": False},
                "priority": 0,
            },
            {
                "name": "Anclar todas las entregas de pedidos",
                "entity_type": "sales_order",
                "trigger_event": "delivered",
                "conditions": {"always": True},
                "actions": {"anchor": True, "mint_cnft": False},
                "priority": 0,
            },
            {
                "name": "Anclar creacion de lotes",
                "entity_type": "batch",
                "trigger_event": "created",
                "conditions": {"always": True},
                "actions": {"anchor": True, "mint_cnft": False},
                "priority": 0,
            },
        ]

        created = []
        for d in defaults:
            rule = await self.repo.create(tenant_id, d)
            created.append(rule)
        return created
