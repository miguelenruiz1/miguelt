"""Anchor rules CRUD — configure what gets anchored on blockchain."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.db.session import get_db_session
from app.services.anchor_rules_service import AnchorRulesService

router = APIRouter(prefix="/api/v1/anchor-rules", tags=["anchor-rules"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class AnchorRuleCreate(BaseModel):
    name: str = Field(..., max_length=150)
    entity_type: str = Field(..., description="purchase_order | sales_order | batch | movement")
    trigger_event: str = Field(..., description="received | delivered | created | transferred")
    conditions: dict[str, Any] = Field(default_factory=dict)
    actions: dict[str, Any] = Field(default_factory=lambda: {"anchor": True})
    is_active: bool = True
    priority: int = 0


class AnchorRuleUpdate(BaseModel):
    name: str | None = None
    conditions: dict[str, Any] | None = None
    actions: dict[str, Any] | None = None
    is_active: bool | None = None
    priority: int | None = None


class AnchorRuleOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    entity_type: str
    trigger_event: str
    conditions: dict[str, Any]
    actions: dict[str, Any]
    is_active: bool
    priority: int
    created_by: str | None = None

    class Config:
        from_attributes = True


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("", response_model=list[AnchorRuleOut])
async def list_rules(
    user: ModuleUser,
    entity_type: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    svc = AnchorRulesService(db)
    rules = await svc.list_rules(user["tenant_id"], entity_type)
    return rules


@router.post("", response_model=AnchorRuleOut, status_code=201)
async def create_rule(
    body: AnchorRuleCreate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    svc = AnchorRulesService(db)
    rule = await svc.create_rule(user["tenant_id"], {
        "name": body.name,
        "entity_type": body.entity_type,
        "trigger_event": body.trigger_event,
        "conditions": body.conditions,
        "actions": body.actions,
        "is_active": body.is_active,
        "priority": body.priority,
        "created_by": user.get("user_id"),
    })
    await db.commit()
    return rule


@router.get("/{rule_id}", response_model=AnchorRuleOut)
async def get_rule(
    rule_id: str,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    svc = AnchorRulesService(db)
    return await svc.get_rule(rule_id, user["tenant_id"])


@router.patch("/{rule_id}", response_model=AnchorRuleOut)
async def update_rule(
    rule_id: str,
    body: AnchorRuleUpdate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    svc = AnchorRulesService(db)
    rule = await svc.update_rule(
        rule_id, user["tenant_id"],
        body.model_dump(exclude_none=True),
    )
    await db.commit()
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: str,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    svc = AnchorRulesService(db)
    await svc.delete_rule(rule_id, user["tenant_id"])
    await db.commit()


@router.post("/seed-defaults", response_model=list[AnchorRuleOut], status_code=201)
async def seed_default_rules(
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Seed default anchor rules for the tenant (idempotent)."""
    svc = AnchorRulesService(db)
    rules = await svc.seed_defaults(user["tenant_id"])
    await db.commit()
    return rules
