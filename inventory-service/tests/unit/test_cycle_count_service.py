"""Regression: CycleCountService.create_count unpacks StockRepository.list_levels correctly.

Bug: `list_levels` returns `tuple[list[StockLevel], int]` (rows, total). The
service was iterating the tuple as if it were a list of StockLevel rows,
then accessing `sl.product_id` on what was actually a list → AttributeError.

Fix: unpack `(levels, _total) = await self.stock_repo.list_levels(...)`.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.services.cycle_count_service import CycleCountService


@pytest.mark.asyncio
async def test_create_count_unpacks_list_levels_tuple(db) -> None:
    """When no product_ids are given, the service asks stock_repo for all
    levels. list_levels returns a 2-tuple — we must unpack it, not iterate it.
    """
    svc = CycleCountService(db)

    # Fake StockLevel-like objects (SimpleNamespace avoids needing real DB rows)
    from types import SimpleNamespace
    fake_levels = [
        SimpleNamespace(
            product_id="prod-1",
            location_id="loc-1",
            batch_id=None,
            qty_on_hand=Decimal("10"),
        ),
        SimpleNamespace(
            product_id="prod-2",
            location_id=None,
            batch_id="batch-x",
            qty_on_hand=Decimal("5"),
        ),
    ]

    # Patch stock_repo.list_levels to return the canonical (rows, total) tuple.
    svc.stock_repo.list_levels = AsyncMock(return_value=(fake_levels, 2))
    # Patch next_count_number and repo methods so we don't hit DB plumbing
    svc.repo.next_count_number = AsyncMock(return_value="CC-2026-0001")
    created_cc = SimpleNamespace(id="cc-abc")
    svc.repo.create = AsyncMock(return_value=created_cc)
    svc.repo.create_items_bulk = AsyncMock(return_value=None)
    # _get_count() re-fetches via repo.get_by_id at the end — return the same stub
    svc.repo.get_by_id = AsyncMock(return_value=created_cc)

    cc = await svc.create_count(
        tenant_id="test-tenant",
        warehouse_id="wh-main",
        product_ids=None,  # triggers list_levels path
    )

    assert cc is created_cc
    # Expect bulk create called with 2 item dicts, both product_ids preserved
    svc.repo.create_items_bulk.assert_awaited_once()
    items = svc.repo.create_items_bulk.await_args.args[0]
    assert len(items) == 2
    pids = {i["product_id"] for i in items}
    assert pids == {"prod-1", "prod-2"}
    # system_qty must come from level.qty_on_hand, not from misunpacking
    qtys = {i["product_id"]: i["system_qty"] for i in items}
    assert qtys["prod-1"] == Decimal("10")
    assert qtys["prod-2"] == Decimal("5")
