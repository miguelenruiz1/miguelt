"""Tests for the central platform audit logger (FASE4)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from app.db.models import PlatformAuditLog
from app.services.platform_audit import log_superuser_action


@pytest.mark.asyncio
async def test_log_superuser_action_inserts_row(db):
    req = MagicMock()
    req.headers = {"User-Agent": "pytest", "X-Forwarded-For": "1.2.3.4"}
    req.client = None

    user = {"id": "u1", "email": "ops@trace.app", "is_superuser": True}

    await log_superuser_action(
        db,
        user=user,
        request=req,
        action="platform.tenant.change_plan_unique_A",
        target_tenant_id="acme",
        target_entity_type="subscription",
        metadata={"plan_slug": "professional"},
    )
    await db.flush()

    res = await db.execute(
        select(PlatformAuditLog).where(
            PlatformAuditLog.action == "platform.tenant.change_plan_unique_A"
        )
    )
    rows = res.scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.superuser_id == "u1"
    assert row.superuser_email == "ops@trace.app"
    assert row.target_tenant_id == "acme"
    assert row.target_entity_type == "subscription"
    assert row.event_metadata == {"plan_slug": "professional"}
    assert row.ip_address == "1.2.3.4"
    assert row.user_agent == "pytest"


@pytest.mark.asyncio
async def test_log_superuser_action_without_request_no_crash(db):
    user = {"id": "u1", "email": "ops@trace.app"}
    await log_superuser_action(
        db,
        user=user,
        request=None,
        action="platform.manual_unique_B",
    )
    await db.flush()
    res = await db.execute(
        select(PlatformAuditLog).where(PlatformAuditLog.action == "platform.manual_unique_B")
    )
    rows = res.scalars().all()
    assert len(rows) == 1
    assert rows[0].ip_address is None
    assert rows[0].user_agent is None


@pytest.mark.asyncio
async def test_log_superuser_action_captures_correlation_id(db):
    req = MagicMock()
    req.headers = {"User-Agent": "ua", "X-Correlation-Id": "abc-123"}
    req.client = None
    user = {"id": "u1", "email": "x@y.com"}

    await log_superuser_action(
        db, user=user, request=req, action="platform.onboard_unique_C",
        target_tenant_id="t1",
    )
    await db.flush()
    row = (await db.execute(
        select(PlatformAuditLog).where(PlatformAuditLog.action == "platform.onboard_unique_C")
    )).scalar_one()
    assert row.correlation_id == "abc-123"
