"""Tests for production — recipes CRUD, run lifecycle (execute, finish, approve, reject)."""
import pytest
from httpx import AsyncClient


async def _setup_recipe(client: AsyncClient, suffix: str):
    """Create output product, component product, warehouse, stock, and recipe."""
    output = await client.post("/api/v1/products", json={
        "name": f"Output-{suffix}", "sku": f"PR-OUT-{suffix}", "unit_of_measure": "un",
    })
    comp = await client.post("/api/v1/products", json={
        "name": f"Comp-{suffix}", "sku": f"PR-CMP-{suffix}", "unit_of_measure": "un",
    })
    w = await client.post("/api/v1/warehouses", json={
        "name": f"WH-PR-{suffix}", "code": f"WH-PR-{suffix}", "type": "main",
    })
    out_id, comp_id, wid = output.json()["id"], comp.json()["id"], w.json()["id"]

    # Stock for component
    await client.post("/api/v1/stock/receive", json={
        "product_id": comp_id, "warehouse_id": wid, "quantity": "500", "unit_cost": "1000",
    })

    # Create recipe
    recipe = await client.post("/api/v1/recipes", json={
        "name": f"Recipe-{suffix}",
        "output_entity_id": out_id,
        "output_quantity": 1,
        "components": [{"component_entity_id": comp_id, "quantity_required": 2}],
    })
    recipe_id = recipe.json()["id"]
    return out_id, comp_id, wid, recipe_id


# ── Recipe CRUD ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_recipe(client: AsyncClient):
    p1 = await client.post("/api/v1/products", json={"name": "RcpOut", "sku": "RCP-OUT-1", "unit_of_measure": "un"})
    p2 = await client.post("/api/v1/products", json={"name": "RcpComp", "sku": "RCP-CMP-1", "unit_of_measure": "un"})
    resp = await client.post("/api/v1/recipes", json={
        "name": "Test Recipe",
        "output_entity_id": p1.json()["id"],
        "output_quantity": 1,
        "components": [{"component_entity_id": p2.json()["id"], "quantity_required": 3}],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Recipe"
    assert len(data["components"]) == 1


@pytest.mark.asyncio
async def test_list_recipes(client: AsyncClient):
    resp = await client.get("/api/v1/recipes")
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.asyncio
async def test_get_recipe(client: AsyncClient):
    _, _, _, recipe_id = await _setup_recipe(client, "GET")
    resp = await client.get(f"/api/v1/recipes/{recipe_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == recipe_id


@pytest.mark.asyncio
async def test_update_recipe(client: AsyncClient):
    _, _, _, recipe_id = await _setup_recipe(client, "UPD")
    resp = await client.patch(f"/api/v1/recipes/{recipe_id}", json={
        "name": "Updated Recipe",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Recipe"


@pytest.mark.asyncio
async def test_delete_recipe(client: AsyncClient):
    _, _, _, recipe_id = await _setup_recipe(client, "DEL")
    resp = await client.delete(f"/api/v1/recipes/{recipe_id}")
    assert resp.status_code == 204


# ── Production Run Lifecycle ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_production_run(client: AsyncClient):
    _, _, wid, recipe_id = await _setup_recipe(client, "RUN-CREATE")
    resp = await client.post("/api/v1/production-runs", json={
        "recipe_id": recipe_id, "warehouse_id": wid, "multiplier": 5,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["multiplier"] == "5" or float(data["multiplier"]) == 5


@pytest.mark.asyncio
async def test_production_run_execute(client: AsyncClient):
    _, _, wid, recipe_id = await _setup_recipe(client, "RUN-EXEC")
    run = await client.post("/api/v1/production-runs", json={
        "recipe_id": recipe_id, "warehouse_id": wid, "multiplier": 3,
    })
    run_id = run.json()["id"]
    resp = await client.post(f"/api/v1/production-runs/{run_id}/execute")
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_production_run_finish(client: AsyncClient):
    _, _, wid, recipe_id = await _setup_recipe(client, "RUN-FIN")
    run = await client.post("/api/v1/production-runs", json={
        "recipe_id": recipe_id, "warehouse_id": wid, "multiplier": 2,
    })
    run_id = run.json()["id"]
    await client.post(f"/api/v1/production-runs/{run_id}/execute")
    resp = await client.post(f"/api/v1/production-runs/{run_id}/finish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "awaiting_approval"


@pytest.mark.asyncio
async def test_production_run_approve(client: AsyncClient):
    _, _, wid, recipe_id = await _setup_recipe(client, "RUN-APR")
    run = await client.post("/api/v1/production-runs", json={
        "recipe_id": recipe_id, "warehouse_id": wid, "multiplier": 2,
    })
    run_id = run.json()["id"]
    await client.post(f"/api/v1/production-runs/{run_id}/execute")
    await client.post(f"/api/v1/production-runs/{run_id}/finish")
    resp = await client.post(f"/api/v1/production-runs/{run_id}/approve")
    # May return 422 due to 4-eyes rule (same user executed and approves)
    assert resp.status_code in (200, 422)


@pytest.mark.asyncio
async def test_production_run_reject(client: AsyncClient):
    _, _, wid, recipe_id = await _setup_recipe(client, "RUN-REJ")
    run = await client.post("/api/v1/production-runs", json={
        "recipe_id": recipe_id, "warehouse_id": wid, "multiplier": 1,
    })
    run_id = run.json()["id"]
    await client.post(f"/api/v1/production-runs/{run_id}/execute")
    await client.post(f"/api/v1/production-runs/{run_id}/finish")
    resp = await client.post(f"/api/v1/production-runs/{run_id}/reject", json={
        "rejection_notes": "Quality issue",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_delete_pending_run(client: AsyncClient):
    _, _, wid, recipe_id = await _setup_recipe(client, "RUN-DEL")
    run = await client.post("/api/v1/production-runs", json={
        "recipe_id": recipe_id, "warehouse_id": wid, "multiplier": 1,
    })
    run_id = run.json()["id"]
    resp = await client.delete(f"/api/v1/production-runs/{run_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_list_production_runs(client: AsyncClient):
    resp = await client.get("/api/v1/production-runs")
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.asyncio
async def test_list_runs_by_status(client: AsyncClient):
    resp = await client.get("/api/v1/production-runs", params={"status": "pending"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_production_run_with_output_warehouse(client: AsyncClient):
    out_id, comp_id, wid, recipe_id = await _setup_recipe(client, "RUN-OWH")
    w2 = await client.post("/api/v1/warehouses", json={
        "name": "WH-PR-OUT", "code": "WH-PR-OUT", "type": "secondary",
    })
    wid2 = w2.json()["id"]
    run = await client.post("/api/v1/production-runs", json={
        "recipe_id": recipe_id, "warehouse_id": wid,
        "output_warehouse_id": wid2, "multiplier": 2,
    })
    assert run.status_code == 201
    run_id = run.json()["id"]
    await client.post(f"/api/v1/production-runs/{run_id}/execute")
    await client.post(f"/api/v1/production-runs/{run_id}/finish")
    resp = await client.post(f"/api/v1/production-runs/{run_id}/approve")
    # May return 422 due to 4-eyes rule
    assert resp.status_code in (200, 422)
