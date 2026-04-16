"""Regression: AlertService.check_expiry_alerts doesn't crash on UnboundLocalError.

Bug: A local `from app.db.models.tracking import EntityBatch` inside
`check_expiry_alerts` made Python treat EntityBatch as a local name for the
whole function, shadowing the module-level import and raising
`UnboundLocalError: cannot access local variable 'EntityBatch'` on the
first usage (the select() on line 183).

Fix: drop the inner re-import — EntityBatch is already imported at module
scope. Without the inner rebind the function resolves the name normally.
"""
from __future__ import annotations

import pytest

from app.services.alert_service import AlertService


@pytest.mark.asyncio
async def test_check_expiry_alerts_empty_tenant_no_error(db) -> None:
    """Tenant with no batches → empty list, no crash."""
    svc = AlertService(db)
    result = await svc.check_expiry_alerts("tenant-no-batches")
    assert result == []


@pytest.mark.asyncio
async def test_check_and_generate_empty_tenant_no_error(db) -> None:
    """Tenant with no products/stock levels → empty list, no crash."""
    svc = AlertService(db)
    result = await svc.check_and_generate("tenant-no-products")
    assert result == []
