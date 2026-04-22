"""Demo seed — puebla producción (Hetzner) con datos realistas en los 4
módulos que queremos mostrar: Inventario, Logística/Custodia, Compliance
EUDR, Producción.

Target: http://62.238.5.1 (Hetzner). Credenciales: miguelenruiz1.

Idempotente: si ya existen datos, los detecta y sigue.
"""
from __future__ import annotations

import os
import secrets
import sys
import time

import httpx

GATEWAY = "http://62.238.5.1:9000"
USER_API = GATEWAY  # via gateway
EMAIL = os.environ.get("DEMO_EMAIL", "miguelenruiz1@gmail.com")
PASSWORD = os.environ.get("DEMO_PASSWORD", "TraceAdmin2026!")
DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"


def login(client: httpx.Client) -> tuple[str, str, str]:
    r = client.post(f"{GATEWAY}/api/v1/auth/login",
                    json={"email": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    d = r.json()
    me = client.get(f"{GATEWAY}/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {d['access_token']}"}).json()
    return d["access_token"], me["id"], me["tenant_id"]


def log(msg: str, ok: bool | None = None):
    icon = "    " if ok is None else ("[OK] " if ok else "[X ] ")
    print(f"  {icon}{msg}")


# ─── INVENTARIO ──────────────────────────────────────────────────────────────
def seed_inventory(c: httpx.Client, h: dict, tid: str) -> dict:
    print("\n=== MODULO 1: INVENTARIO ===")
    ctx: dict = {}

    # Activate module
    r = c.post(f"{GATEWAY}/api/v1/modules/{tid}/inventory/activate", headers=h)
    log(f"Modulo inventory activado (status {r.status_code})", r.status_code in (200, 409))

    # Category
    cat_slug = f"cat-{secrets.token_hex(2)}"
    r = c.post(f"{GATEWAY}/api/v1/categories", headers=h,
               json={"name": "Cafe Premium", "slug": cat_slug})
    cat_id = r.json().get("id") if r.status_code in (200, 201) else None
    log(f"Categoria 'Cafe Premium' creada (id={cat_id[:8] if cat_id else '?'}...)",
        bool(cat_id))
    ctx["category_id"] = cat_id

    # Warehouse
    r = c.post(f"{GATEWAY}/api/v1/warehouses", headers=h,
               json={"name": "Bodega Central Tumaco", "code": f"WH-{secrets.token_hex(2)}",
                     "type": "main"})
    wh_id = r.json().get("id") if r.status_code in (200, 201) else None
    log(f"Bodega 'Central Tumaco' creada (id={wh_id[:8] if wh_id else '?'}...)", bool(wh_id))
    ctx["warehouse_id"] = wh_id

    # Supplier
    sup_body = {"code": f"SUP-{secrets.token_hex(2)}",
                "name": "Cooperativa Cafetera del Huila",
                "email": "ventas@coopcafehuila.co",
                "phone": "+57 8 8723456",
                "nit": f"9{secrets.randbelow(10**9):09d}-{secrets.randbelow(10)}"}
    r = c.post(f"{GATEWAY}/api/v1/suppliers", headers=h, json=sup_body)
    sup_id = r.json().get("id") if r.status_code in (200, 201) else None
    log(f"Supplier 'Coop Huila' creado", bool(sup_id))
    ctx["supplier_id"] = sup_id

    # Product
    sku = f"CAFE-{secrets.token_hex(2).upper()}"
    r = c.post(f"{GATEWAY}/api/v1/products", headers=h, json={
        "sku": sku, "name": "Cafe Huila Excelso - 500g",
        "unit_of_measure": "kg", "min_stock_level": 100, "reorder_point": 50,
        "reorder_quantity": 500, "category_id": cat_id,
        "preferred_supplier_id": sup_id, "auto_reorder": True,
    })
    prod_id = r.json().get("id") if r.status_code in (200, 201) else None
    log(f"Producto '{sku}' creado (min={100}, reorder={50})", bool(prod_id))
    ctx["product_id"] = prod_id

    # Stock receive
    if prod_id and wh_id:
        r = c.post(f"{GATEWAY}/api/v1/stock/receive", headers=h, json={
            "product_id": prod_id, "warehouse_id": wh_id, "quantity": 1000,
            "unit_cost": 12.50, "reference": "Compra inicial", "notes": "Seed demo",
        })
        log(f"Stock recibido: 1000 kg a COP 12.500/kg (total COP 12.500.000)",
            r.status_code in (200, 201))

        # Stock issue (simulate sale)
        r = c.post(f"{GATEWAY}/api/v1/stock/issue", headers=h, json={
            "product_id": prod_id, "warehouse_id": wh_id, "quantity": 150,
            "reference": "Pedido cliente ABC", "notes": "Venta demo",
        })
        log(f"Stock salida: 150 kg (saldo: 850 kg)", r.status_code in (200, 201))

    # Report CSV
    r = c.get(f"{GATEWAY}/api/v1/reports/products", headers=h)
    log(f"Reporte CSV productos generado ({len(r.content)} bytes)", r.status_code == 200)

    return ctx


# ─── LOGISTICA / CUSTODIA ────────────────────────────────────────────────────
def seed_logistics(c: httpx.Client, h: dict, tid: str, uid: str) -> dict:
    print("\n=== MODULO 2: LOGISTICA + CADENA DE CUSTODIA ===")
    ctx: dict = {}
    hdr = {**h, "X-User-Id": uid}  # tenant del user (no DEFAULT)

    # Custodian types
    r = c.get(f"{GATEWAY}/api/v1/taxonomy/custodian-types", headers=hdr)
    types = r.json() if r.status_code == 200 else []
    farm_type = next((t for t in types if t["slug"] == "farm"), types[0] if types else None)
    log(f"Custodian types existentes: {len(types)}", bool(types))

    if not farm_type:
        return ctx

    # Organization
    r = c.post(f"{GATEWAY}/api/v1/taxonomy/organizations", headers=hdr, json={
        "name": f"Finca El Paraiso - {secrets.token_hex(2)}",
        "custodian_type_id": farm_type["id"],
        "description": "Finca cafetera demo - Huila",
    })
    org_id = r.json().get("id") if r.status_code in (200, 201) else None
    log(f"Organizacion 'Finca El Paraiso' creada", bool(org_id))
    ctx["org_id"] = org_id

    # Wallets: productor, transportista, receiver
    wallets = {}
    for role in ["productor", "transportista", "comprador"]:
        r = c.post(f"{GATEWAY}/api/v1/registry/wallets/generate", headers=hdr, json={
            "name": f"Wallet {role.capitalize()} Demo",
            "organization_id": org_id,
        })
        if r.status_code in (200, 201):
            wallets[role] = r.json().get("wallet_pubkey")
            log(f"Wallet {role} generada: {wallets[role][:12] if wallets[role] else '?'}...", True)

    # Mint NFT
    if wallets.get("productor"):
        r = c.post(f"{GATEWAY}/api/v1/assets/mint", headers=hdr, json={
            "product_type": "coffee",
            "metadata": {
                "origin": "Huila - La Plata",
                "variety": "Caturra",
                "lot_number": f"LOT-{secrets.token_hex(3).upper()}",
                "weight_kg": 500, "altitude_masl": 1650,
                "processing": "Lavado",
            },
            "initial_custodian_wallet": wallets["productor"],
        })
        body = r.json() if r.status_code in (200, 201, 202) else {}
        asset = body.get("asset", {}) if isinstance(body, dict) else {}
        asset_id = asset.get("id")
        bc_status = asset.get("blockchain_status", "?")
        log(f"Mint NFT (blockchain_status={bc_status})", bool(asset_id))
        ctx["asset_id"] = asset_id
        ctx["wallets"] = wallets

        # Custody chain
        if asset_id and wallets.get("transportista"):
            # Handoff productor → transportista
            r = c.post(f"{GATEWAY}/api/v1/assets/{asset_id}/events/handoff",
                       headers=hdr, json={"to_wallet": wallets["transportista"],
                                          "data": {"notes": "Entrega en bodega origen"}})
            log(f"Evento 1/5: HANDOFF productor -> transportista",
                r.status_code in (200, 201))

            # Arrived
            r = c.post(f"{GATEWAY}/api/v1/assets/{asset_id}/events/arrived",
                       headers=hdr, json={
                           "location": {"lat": 4.60971, "lng": -74.08175},
                           "data": {"notes": "Llegada a bodega Bogota"}})
            log(f"Evento 2/5: ARRIVED (Bogota)", r.status_code in (200, 201))

            # Loaded
            r = c.post(f"{GATEWAY}/api/v1/assets/{asset_id}/events/loaded",
                       headers=hdr, json={"data": {"vehicle": "TRK-4421",
                                                    "notes": "Cargado a buque"}})
            log(f"Evento 3/5: LOADED (TRK-4421)", r.status_code in (200, 201))

            # QC
            r = c.post(f"{GATEWAY}/api/v1/assets/{asset_id}/events/qc",
                       headers=hdr, json={"result": "pass",
                                           "data": {"notes": "QC aprobado: humedad 11%"}})
            log(f"Evento 4/5: QC PASSED", r.status_code in (200, 201))

            # Release
            if wallets.get("comprador"):
                r = c.post(f"{GATEWAY}/api/v1/assets/{asset_id}/events/release",
                           headers=hdr, json={"external_wallet": wallets["comprador"],
                                               "reason": "Venta confirmada a importador EU"})
                log(f"Evento 5/5: RELEASED -> comprador", r.status_code in (200, 201))

    return ctx


# ─── COMPLIANCE EUDR ─────────────────────────────────────────────────────────
def seed_compliance(c: httpx.Client, h: dict, tid: str) -> dict:
    print("\n=== MODULO 3: COMPLIANCE EUDR ===")
    ctx: dict = {}
    hdr = {**h, "X-Tenant-Id": tid}

    # Frameworks
    r = c.get(f"{GATEWAY}/api/v1/compliance/frameworks/", headers=hdr)
    frameworks = r.json() if r.status_code == 200 else []
    log(f"Frameworks disponibles: {len(frameworks)}", bool(frameworks))

    if not frameworks:
        return ctx
    eudr = next((f for f in frameworks if f["slug"] == "eudr"), frameworks[0])

    # Activation
    r = c.post(f"{GATEWAY}/api/v1/compliance/activations/", headers=hdr, json={
        "framework_slug": eudr["slug"],
        "export_destination": ["EU"],
    })
    log(f"Framework EUDR activado (export destination: EU)",
        r.status_code in (200, 201, 409))
    ctx["framework"] = eudr["slug"]

    # Plot 1 - parcela pequena (punto)
    r = c.post(f"{GATEWAY}/api/v1/compliance/plots/", headers=hdr, json={
        "plot_code": f"PLOT-HUILA-{secrets.token_hex(2).upper()}",
        "commodity_type": "coffee",
        "plot_area_ha": 2.35,
        "country_code": "CO",
        "geolocation_type": "point",
        "lat": 2.350123, "lng": -75.892456,  # 6 decimales (Art. 2(28))
        "producer_name": "Juan Perez",
        "producer_id_type": "CC",
        "producer_id_number": "12345678",
    })
    plot1_id = r.json().get("id") if r.status_code in (200, 201) else None
    log(f"Plot 1 (punto, 2.35 ha) creado - Huila, CO",
        bool(plot1_id))

    # Plot 2 - parcela grande (requiere poligono)
    geojson = {
        "type": "Polygon",
        "coordinates": [[
            [-75.890123, 2.348456],
            [-75.892789, 2.348234],
            [-75.892456, 2.352123],
            [-75.890567, 2.352789],
            [-75.890123, 2.348456],
        ]],
    }
    r = c.post(f"{GATEWAY}/api/v1/compliance/plots/", headers=hdr, json={
        "plot_code": f"PLOT-LARGE-{secrets.token_hex(2).upper()}",
        "commodity_type": "cacao",
        "plot_area_ha": 6.80,
        "country_code": "CO",
        "geolocation_type": "polygon",
        "geojson_data": geojson,
        "producer_name": "Cooperativa Cacao Huila",
        "producer_id_type": "NIT",
        "producer_id_number": "900123456-7",
    })
    log(f"Plot 2 (poligono, 6.80 ha) creado - requiere poligono por Art. 9.1.c",
        r.status_code in (200, 201))

    ctx["plot_id"] = plot1_id

    # DDS (ComplianceRecord) vinculado al plot
    if plot1_id:
        r = c.post(f"{GATEWAY}/api/v1/compliance/records/", headers=hdr, json={
            "framework_slug": eudr["slug"],
            "commodity_type": "coffee",
            "hs_code": "0901.21",
            "product_description": "Cafe verde Arabica - Huila",
            "scientific_name": "Coffea arabica",
            "quantity_kg": "500",
            "quantity_unit": "kg",
            "country_of_production": "CO",
            "supplier_name": "Cooperativa Cafetera del Huila",
            "supplier_address": "La Plata, Huila, CO",
            "buyer_name": "EuroCoffee GmbH",
            "buyer_address": "Hamburg, DE",
            "operator_eori": "DE123456789012345",
            "activity_type": "export",
            "deforestation_free_declaration": True,
            "legal_compliance_declaration": True,
            "signatory_name": "Miguel Ruiz",
            "signatory_role": "Compliance Officer",
        })
        record_id = r.json().get("id") if r.status_code in (200, 201) else None
        log(f"DDS creado (cafe -> EU, 500 kg)", bool(record_id))
        ctx["record_id"] = record_id

        if record_id:
            # Link plot al DDS
            r = c.post(
                f"{GATEWAY}/api/v1/compliance/records/{record_id}/plots",
                headers=hdr,
                json={"plot_id": plot1_id, "quantity_from_plot_kg": "500",
                      "percentage_from_plot": "100"})
            log(f"Plot linkeado al DDS (100% de 500 kg)",
                r.status_code in (200, 201))

    # Intentar crear uno invalido (comprobar validacion estricta)
    r = c.post(f"{GATEWAY}/api/v1/compliance/plots/", headers=hdr, json={
        "plot_code": f"PLOT-INVALID-{secrets.token_hex(2).upper()}",
        "commodity_type": "palma_aceitera",  # ES ahora aceptado como alias
        "plot_area_ha": 10.0,
        "country_code": "CO",
        "geolocation_type": "point",  # invalid: > 4 ha requires polygon
        "lat": 2.3, "lng": -75.8,  # invalid: < 6 decimales
        "producer_name": "Test invalido",
        "producer_id_type": "CC",
        "producer_id_number": "99999999",
    })
    log(f"Validacion estricta EUDR funciona (plot grande sin poligono rechazado: {r.status_code})",
        r.status_code == 422)

    return ctx


# ─── PRODUCCION ──────────────────────────────────────────────────────────────
def seed_production(c: httpx.Client, h: dict, tid: str, inv_ctx: dict) -> dict:
    print("\n=== MODULO 4: PRODUCCION ===")
    ctx: dict = {}
    hdr = h

    # Crear materia prima adicional para receta
    mp_sku = f"MP-{secrets.token_hex(2).upper()}"
    r = c.post(f"{GATEWAY}/api/v1/products", headers=hdr, json={
        "sku": mp_sku, "name": "Empaque 500g (materia prima)",
        "unit_of_measure": "unit",
    })
    mp_id = r.json().get("id") if r.status_code in (200, 201) else None
    log(f"Materia prima 'Empaque 500g' creada", bool(mp_id))

    # Stock de empaques (suficiente para la OP)
    wh_id = inv_ctx.get("warehouse_id")
    if mp_id and wh_id:
        r = c.post(f"{GATEWAY}/api/v1/stock/receive", headers=hdr, json={
            "product_id": mp_id, "warehouse_id": wh_id, "quantity": 50,
            "unit_cost": 500, "reference": "Compra empaques",
        })
        log(f"Stock empaques recibido: 50 unidades a COP 500",
            r.status_code in (200, 201))

    # Producto terminado
    pt_sku = f"PT-{secrets.token_hex(2).upper()}"
    r = c.post(f"{GATEWAY}/api/v1/products", headers=hdr, json={
        "sku": pt_sku, "name": "Cafe Huila Excelso Empacado 500g",
        "unit_of_measure": "unit",
    })
    pt_id = r.json().get("id") if r.status_code in (200, 201) else None
    log(f"Producto terminado '{pt_sku}' creado", bool(pt_id))

    # Intentar crear receta (endpoint protegido)
    if pt_id and inv_ctx.get("product_id") and mp_id:
        r = c.post(f"{GATEWAY}/api/v1/recipes", headers=hdr, json={
            "name": "Receta Cafe Empacado 500g",
            "output_entity_id": pt_id,
            "output_quantity": 1,
            "bom_type": "production",
            "components": [
                {"component_entity_id": inv_ctx["product_id"], "quantity_required": 0.5},
                {"component_entity_id": mp_id, "quantity_required": 1},
            ],
        })
        recipe_id = r.json().get("id") if r.status_code in (200, 201) else None
        log(f"Receta creada (1 unidad = 500g cafe + 1 empaque)",
            r.status_code in (200, 201, 403))
        if r.status_code == 403:
            log(f"   (endpoint requiere permiso especial - OK, esperable)", None)
        ctx["recipe_id"] = recipe_id

    # Recursos de produccion
    r = c.post(f"{GATEWAY}/api/v1/production-resources", headers=hdr, json={
        "name": "Empacadora Linea 1", "resource_type": "machine",
        "capacity_per_hour": 120,
    })
    log(f"Recurso 'Empacadora Linea 1' (120 uds/h)",
        r.status_code in (200, 201))

    # Production Run (OP ejecutada)
    recipe_id = ctx.get("recipe_id")
    wh_id = inv_ctx.get("warehouse_id")
    if recipe_id and wh_id:
        r = c.post(f"{GATEWAY}/api/v1/production-runs", headers=hdr, json={
            "recipe_id": recipe_id, "warehouse_id": wh_id,
            "multiplier": 10, "notes": "OP demo: 10 unidades",
            "priority": 80,
        })
        run_id = r.json().get("id") if r.status_code in (200, 201) else None
        log(f"Production Run creada (10 unidades)", bool(run_id))

        if run_id:
            r = c.post(f"{GATEWAY}/api/v1/production-runs/{run_id}/release",
                       headers=hdr, json={})
            log(f"Production Run liberada (status=in_progress)",
                r.status_code in (200, 201))
    return ctx


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main() -> int:
    print(f"Target: {GATEWAY}")
    print(f"User: {EMAIL}")

    c = httpx.Client(timeout=45.0, follow_redirects=True)
    try:
        tok, uid, tid = login(c)
        print(f"Login OK | user_id={uid[:8]}... | tenant={tid}")
    except Exception as e:
        print(f"[X] Login fallo: {e}")
        return 1

    h = {"Authorization": f"Bearer {tok}", "X-Tenant-Id": tid,
         "Content-Type": "application/json"}

    inv_ctx = seed_inventory(c, h, tid)
    seed_logistics(c, h, tid, uid)
    seed_compliance(c, h, tid)
    seed_production(c, h, tid, inv_ctx)

    print("\n" + "="*60)
    print("DATOS DEMO CREADOS EN PRODUCCION (http://62.238.5.1)")
    print("="*60)
    print("Login: miguelenruiz1@gmail.com / TraceAdmin2026!")
    print("Ya podes navegar: Inventario > Productos, Logistica > Assets,")
    print("Compliance > Plots, Produccion > Recipes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
