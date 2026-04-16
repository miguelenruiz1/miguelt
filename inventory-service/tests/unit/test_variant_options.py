"""Regression: variant attribute options must carry tenant_id.

Bug: POST /variant-attributes/{id}/options returned 500 NotNullViolation on
`variant_attribute_options.tenant_id` because `VariantService.add_option`
forwarded the raw request body to the repo without injecting the caller's
tenant_id.

Fix: `variant_service.add_option` and `create_attribute`'s inline option
loop now both set `data["tenant_id"] = tenant_id` before repo.create.
"""
from __future__ import annotations

import pytest

from app.services.variant_service import VariantService


@pytest.mark.asyncio
async def test_add_option_injects_tenant_id(db) -> None:
    """add_option must tag the new option with the caller's tenant_id."""
    svc = VariantService(db)
    tenant = "tenant-vo-test"

    attr = await svc.create_attribute(tenant, {"name": "Color", "slug": "color"})
    assert attr.tenant_id == tenant

    opt = await svc.add_option(attr.id, tenant, {"value": "Red", "color_hex": "#FF0000"})
    assert opt.tenant_id == tenant
    assert opt.attribute_id == attr.id
    assert opt.value == "Red"


@pytest.mark.asyncio
async def test_create_attribute_with_inline_options_injects_tenant_id(db) -> None:
    """Creating an attribute with inline options → every option gets tenant_id."""
    from sqlalchemy import select
    from app.db.models.variant import VariantAttributeOption

    svc = VariantService(db)
    tenant = "tenant-vo-inline"

    attr = await svc.create_attribute(
        tenant,
        {"name": "Size", "slug": "size"},
        options=[{"value": "S"}, {"value": "M"}, {"value": "L"}],
    )
    assert attr.tenant_id == tenant

    # Query options directly (avoids relationship-load edge cases in SQLite tests).
    rows = (await db.execute(
        select(VariantAttributeOption).where(VariantAttributeOption.attribute_id == attr.id)
    )).scalars().all()
    assert len(rows) == 3
    for opt in rows:
        assert opt.tenant_id == tenant
