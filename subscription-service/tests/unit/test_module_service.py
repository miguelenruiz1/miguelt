"""Unit tests for ModuleService: catalog + activation + cache invalidation."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.module_service import ModuleService, MODULE_CATALOG


# ── Catalog ─────────────────────────────────────────────────────────────────


def test_module_catalog_contains_expected_modules() -> None:
    slugs = {m["slug"] for m in MODULE_CATALOG}
    assert "logistics" in slugs
    assert "inventory" in slugs
    assert "production" in slugs
    assert "compliance" in slugs


def test_module_catalog_all_entries_have_name_and_description() -> None:
    for m in MODULE_CATALOG:
        assert m.get("slug"), m
        assert m.get("name"), m
        assert m.get("description"), m


# ── list_tenant_modules merges catalog + DB activations ─────────────────────


@pytest.mark.asyncio
async def test_list_tenant_modules_merges_catalog_with_activations(db, make_plan) -> None:
    """Modules NOT activated must still appear in the response with is_active=False.

    This is the contract the frontend relies on to show the marketplace grid.
    """
    from app.db.models import TenantModuleActivation

    # Activate ONE module for tenant 't-1'
    db.add(TenantModuleActivation(
        id="act-1",
        tenant_id="t-1",
        module_slug="inventory",
        is_active=True,
    ))
    await db.flush()

    svc = ModuleService(db)
    result = await svc.list_tenant_modules("t-1")

    by_slug = {m["slug"]: m for m in result}
    # Every catalog module present
    for mod in MODULE_CATALOG:
        assert mod["slug"] in by_slug, f"missing {mod['slug']}"
    # inventory ON, logistics OFF
    assert by_slug["inventory"]["is_active"] is True
    assert by_slug["logistics"]["is_active"] is False


# ── activate() invalidates cache ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_activate_module_invalidates_cache(db) -> None:
    """After activate(), _invalidate_module_cache must be called with key contract.

    We patch `_invalidate_module_cache` to capture the call.
    """
    svc = ModuleService(db)

    with patch(
        "app.services.module_service._invalidate_module_cache",
        new=AsyncMock(return_value=None),
    ) as invalidate:
        record = await svc.activate(tenant_id="t-42", slug="inventory", performed_by="tester")
        invalidate.assert_awaited_once_with("t-42", "inventory")

    assert record is not None
    assert record.tenant_id == "t-42"
    assert record.module_slug == "inventory"
    assert record.is_active is True
