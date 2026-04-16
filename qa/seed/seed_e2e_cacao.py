#!/usr/bin/env python3
"""
E2E seeder: Cacao fino de aroma Colombia -> Switzerland (Barry Callebaut).
Exercises inventory + logistics (trace) + production + compliance (EUDR).

Designed to be idempotent where possible and fail-soft: records each API call
with its HTTP status + response body into a log so we can post-mortem bugs.

Auth: uses a JWT stored in qa/seed/token.txt (tenant = 'default', superuser).
"""
from __future__ import annotations
import json, os, sys, time, pathlib, datetime, decimal, traceback
from typing import Any

try:
    import requests
except ImportError:
    print("ERROR: need `requests`. pip install requests", file=sys.stderr)
    sys.exit(1)

BASE = os.environ.get("TRACE_GATEWAY", "http://localhost:9000")
TENANT = "default"
HERE = pathlib.Path(__file__).parent
TOKEN = (HERE / "token.txt").read_text().strip()

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "X-Tenant-Id": TENANT,
    "X-User-Id": "f44952c4-8d1f-46d0-ae53-540dcf272843",
    "Content-Type": "application/json",
}

LOG_PATH = HERE / "seed_run.jsonl"
STATE_PATH = HERE / "seed_state.json"

# In-memory state (IDs we created, keyed by logical name)
S: dict[str, Any] = {
    "uom": {}, "tax_rate": {}, "tax_category": {}, "category": {},
    "product_type": {}, "custom_field": {}, "warehouse_type": {},
    "warehouse": {}, "movement_type": {}, "supplier_type": {},
    "customer_type": {}, "supplier": {}, "customer": {}, "product": {},
    "custodian_type": {}, "organization": {}, "wallet": {}, "asset": {},
    "event": [], "plot": {}, "record": {}, "risk": {}, "node": [],
    "cert": {}, "recipe": {}, "resource": {}, "run": {}, "emission": {},
    "receipt": {}, "activation": {}, "bugs": [],
}


def _log(ev: dict) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ev, default=str) + "\n")


def req(method: str, path: str, body: Any | None = None, params: dict | None = None, label: str = "") -> tuple[int, Any]:
    url = BASE + path
    try:
        r = requests.request(method, url, headers=HEADERS, json=body, params=params, timeout=30)
        try:
            data = r.json()
        except Exception:
            data = {"_raw": r.text[:500]}
        _log({"ts": datetime.datetime.utcnow().isoformat(), "label": label, "method": method, "url": url,
              "status": r.status_code, "body": body, "resp": data if r.status_code < 400 else data})
        if r.status_code >= 500:
            S["bugs"].append({"label": label, "method": method, "url": url, "status": r.status_code, "resp": data, "body": body})
            print(f"  [500] {label} {method} {path} -> {data}")
        elif r.status_code >= 400:
            print(f"  [{r.status_code}] {label} {method} {path} -> {str(data)[:200]}")
        else:
            print(f"  [{r.status_code}] {label} ok")
        return r.status_code, data
    except Exception as exc:
        print(f"  [EXC] {label}: {exc}")
        _log({"ts": datetime.datetime.utcnow().isoformat(), "label": label, "exc": str(exc), "url": url})
        S["bugs"].append({"label": label, "url": url, "exc": str(exc)})
        return 0, None


def save_state():
    STATE_PATH.write_text(json.dumps(S, indent=2, default=str))


def find_existing(list_path: str, match_key: str, match_val: str, label: str, id_key: str = "id") -> str | None:
    """GET list endpoint, find item whose match_key == match_val, return its id."""
    sc, data = req("GET", list_path, label=f"lookup.{label}")
    if sc != 200:
        return None
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return None
    for it in items:
        if it.get(match_key) == match_val:
            return it.get(id_key)
    return None


# ══════════════════════════════════════════════════════════════════════════
# 1. UoM
# ══════════════════════════════════════════════════════════════════════════
def seed_uom():
    print("\n=== 1. UoM ===")
    for body, key in [
        ({"name": "Kilogramo", "symbol": "kg", "category": "weight", "is_base": True}, "kg"),
        ({"name": "Tonelada", "symbol": "ton", "category": "weight", "is_base": False}, "ton"),
        ({"name": "Saco de 60kg", "symbol": "sc60", "category": "weight", "is_base": False}, "sc60"),
    ]:
        sc, data = req("POST", "/api/v1/uom", body, label=f"uom.create.{key}")
        if sc == 201 or sc == 200:
            S["uom"][key] = data["id"]
    # Conversion ton -> kg (1 ton = 1000 kg), sc60 -> kg (1 sc60 = 60 kg)
    if "kg" in S["uom"] and "ton" in S["uom"]:
        req("POST", "/api/v1/uom/conversions",
            {"from_uom_id": S["uom"]["ton"], "to_uom_id": S["uom"]["kg"], "factor": "1000"},
            label="uom.conv.ton_kg")
    if "kg" in S["uom"] and "sc60" in S["uom"]:
        req("POST", "/api/v1/uom/conversions",
            {"from_uom_id": S["uom"]["sc60"], "to_uom_id": S["uom"]["kg"], "factor": "60"},
            label="uom.conv.sc60_kg")


# ══════════════════════════════════════════════════════════════════════════
# 2. Tax rates
# ══════════════════════════════════════════════════════════════════════════
def seed_taxes():
    print("\n=== 2. Tax ===")
    # Tax categories
    for body, key in [
        ({"slug": "iva", "name": "IVA Colombia", "behavior": "addition", "base_kind": "subtotal"}, "iva"),
        ({"slug": "retefuente", "name": "Retención en la fuente", "behavior": "withholding", "base_kind": "subtotal"}, "retefuente"),
    ]:
        sc, data = req("POST", "/api/v1/tax-categories", body, label=f"taxcat.{key}")
        if sc in (200, 201):
            S["tax_category"][key] = data["id"]
        elif sc == 409:
            # Fetch existing
            sc2, lst = req("GET", "/api/v1/tax-categories", label=f"taxcat.list.{key}")
            if isinstance(lst, list):
                for it in lst:
                    if it.get("slug") == key:
                        S["tax_category"][key] = it["id"]
    # Tax rates
    for body, key in [
        ({"name": "IVA 0% (cacao crudo exento)", "rate": "0.0", "category_slug": "iva", "is_default": True, "dian_code": "01"}, "iva0"),
        ({"name": "Retención cacao 4%", "rate": "0.04", "category_slug": "retefuente", "is_default": True, "dian_code": "06"}, "reten4"),
    ]:
        sc, data = req("POST", "/api/v1/tax-rates", body, label=f"taxrate.{key}")
        if sc in (200, 201):
            S["tax_rate"][key] = data["id"]


# ══════════════════════════════════════════════════════════════════════════
# 3. Categories
# ══════════════════════════════════════════════════════════════════════════
def seed_categories():
    print("\n=== 3. Categories ===")
    for name in ["Cacao en grano", "Cacao fermentado", "Insumos agrícolas"]:
        sc, data = req("POST", "/api/v1/categories", {"name": name, "description": f"Categoría {name}"}, label=f"cat.{name}")
        if sc in (200, 201):
            S["category"][name] = data["id"]


# ══════════════════════════════════════════════════════════════════════════
# 4. Product type + custom fields
# ══════════════════════════════════════════════════════════════════════════
def seed_product_type():
    print("\n=== 4. Product types + custom fields ===")
    sc, data = req("POST", "/api/v1/config/product-types",
                   {"name": "Cacao variedad", "slug": "cacao-variedad", "description": "Variedad fina aroma Col",
                    "color": "#8B4513", "tracks_batches": True, "requires_qc": True, "sku_prefix": "CAC"},
                   label="pt.cacao")
    if sc in (200, 201):
        S["product_type"]["cacao"] = data["id"]
    pt_id = S["product_type"].get("cacao")
    if not pt_id:
        return
    fields = [
        {"label": "Variedad", "field_key": "variedad", "field_type": "select",
         "options": ["criollo", "trinitario", "forastero"], "required": True, "sort_order": 1, "product_type_id": pt_id},
        {"label": "Origen Plot ID", "field_key": "origen_plot_id", "field_type": "text", "sort_order": 2, "product_type_id": pt_id},
        {"label": "Días fermentación", "field_key": "fermentation_days", "field_type": "number", "sort_order": 3, "product_type_id": pt_id},
        {"label": "Humedad %", "field_key": "moisture_pct", "field_type": "number", "sort_order": 4, "product_type_id": pt_id},
        {"label": "Calibre (grs/100granos)", "field_key": "grano_calibre", "field_type": "number", "sort_order": 5, "product_type_id": pt_id},
    ]
    for f in fields:
        sc, data = req("POST", "/api/v1/config/custom-fields", f, label=f"pt.cf.{f['field_key']}")
        if sc in (200, 201):
            S["custom_field"][f["field_key"]] = data["id"]


# ══════════════════════════════════════════════════════════════════════════
# 5. Warehouse types + warehouses
# ══════════════════════════════════════════════════════════════════════════
def seed_warehouses():
    print("\n=== 5. Warehouse types + warehouses ===")
    for name, slug in [("Bodega fermentación", "fermentacion"), ("Bodega secado", "secado"), ("Bodega exportación", "exportacion")]:
        sc, data = req("POST", "/api/v1/config/warehouse-types",
                       {"name": name, "slug": slug, "color": "#ca8a04"}, label=f"wht.{slug}")
        if sc in (200, 201):
            S["warehouse_type"][slug] = data["id"]
    wh_list = [
        ("Fermentadero Popayán", "FERM-POP", "fermentacion", {"street": "Vereda Caldono km 8", "city": "Popayán", "state": "Cauca", "country": "CO", "lat": 2.5, "lng": -76.6}),
        ("Secadero Buenaventura", "SEC-BUN", "secado", {"street": "Zona Franca Buenaventura", "city": "Buenaventura", "state": "Valle del Cauca", "country": "CO", "lat": 3.88, "lng": -77.03}),
        ("Bodega Exportación Cartagena", "EXP-CTG", "exportacion", {"street": "Mamonal km 5 Bodega 12", "city": "Cartagena", "state": "Bolívar", "country": "CO", "lat": 10.32, "lng": -75.5}),
    ]
    for name, code, wtslug, addr in wh_list:
        body = {"name": name, "code": code, "type": "main", "address": addr,
                "warehouse_type_id": S["warehouse_type"].get(wtslug)}
        sc, data = req("POST", "/api/v1/warehouses", body, label=f"wh.{code}")
        if sc in (200, 201):
            S["warehouse"][code] = data["id"]


# ══════════════════════════════════════════════════════════════════════════
# 6. Movement types
# ══════════════════════════════════════════════════════════════════════════
def seed_movement_types():
    print("\n=== 6. Movement types ===")
    for name, slug, direction in [
        ("Entrada cosecha", "entrada-cosecha", "in"),
        ("Salida fermentación→secado", "salida-ferm-secado", "transfer"),
        ("Salida exportación", "salida-exportacion", "out"),
    ]:
        sc, data = req("POST", "/api/v1/config/movement-types",
                       {"name": name, "slug": slug, "direction": direction, "affects_cost": True}, label=f"mt.{slug}")
        if sc in (200, 201):
            S["movement_type"][slug] = data["id"]


# ══════════════════════════════════════════════════════════════════════════
# 7. Supplier + customer types
# ══════════════════════════════════════════════════════════════════════════
def seed_partner_types():
    print("\n=== 7. Supplier + customer types ===")
    for name, slug in [("Cooperativa Agrícola", "cooperativa"), ("Agricultor Individual", "agricultor")]:
        sc, data = req("POST", "/api/v1/config/supplier-types",
                       {"name": name, "slug": slug, "color": "#16a34a"}, label=f"st.{slug}")
        if sc in (200, 201):
            S["supplier_type"][slug] = data["id"]
    sc, data = req("POST", "/api/v1/config/customer-types",
                   {"name": "Chocolatero Internacional", "slug": "chocolatero-intl", "color": "#7c2d12"},
                   label="ct.choco")
    if sc in (200, 201):
        S["customer_type"]["choco"] = data["id"]


# ══════════════════════════════════════════════════════════════════════════
# 8. Suppliers + customers
# ══════════════════════════════════════════════════════════════════════════
def seed_suppliers_customers():
    print("\n=== 8. Suppliers + customer ===")
    coop_type = S["supplier_type"].get("cooperativa")
    sups = [
        ("Cooperativa Agroindustrial San Vicente del Caguán", "COOP-SVC",
         "900.123.456-7", "Caquetá", {"street": "Calle 6 # 4-12", "city": "San Vicente del Caguán", "state": "Caquetá", "country": "CO"}),
        ("Asocafé Huila (Comité de Cacaoteros)", "COOP-HUILA",
         "901.234.567-8", "Huila", {"street": "Carrera 5 # 12-34", "city": "Neiva", "state": "Huila", "country": "CO"}),
        ("Cacaoteros de Apartadó", "COOP-APART",
         "902.345.678-9", "Antioquia", {"street": "Av. Principal 45-23", "city": "Apartadó", "state": "Antioquia", "country": "CO"}),
    ]
    for name, code, nit, region, addr in sups:
        body = {"name": name, "code": code, "supplier_type_id": coop_type,
                "contact_name": "Gerente Comercial", "email": f"contacto@{code.lower()}.co",
                "phone": "+57 300 1234567", "address": addr, "payment_terms_days": 30, "lead_time_days": 14,
                "custom_attributes": {"nit": nit, "region": region}}
        sc, data = req("POST", "/api/v1/suppliers", body, label=f"sup.{code}")
        if sc in (200, 201):
            S["supplier"][code] = data["id"]
    # Customer Barry Callebaut
    body = {"name": "Barry Callebaut AG", "code": "BC-CH", "customer_type_id": S["customer_type"].get("choco"),
            "tax_id": "CHE-105.889.353", "tax_id_type": "VAT",
            "contact_name": "Sophie Müller", "email": "procurement@barry-callebaut.ch",
            "phone": "+41 43 204 0404",
            "address": {"street": "Hardturmstrasse 181", "city": "Zürich", "country": "CH", "postal_code": "8005"},
            "shipping_address": {"street": "Hardturmstrasse 181", "city": "Zürich", "country": "CH", "postal_code": "8005"},
            "payment_terms_days": 60}
    sc, data = req("POST", "/api/v1/customers", body, label="cust.bc")
    if sc in (200, 201):
        S["customer"]["bc"] = data["id"]


# ══════════════════════════════════════════════════════════════════════════
# 9. Products
# ══════════════════════════════════════════════════════════════════════════
def seed_products():
    print("\n=== 9. Products ===")
    cat_grano = S["category"].get("Cacao en grano")
    cat_ferm = S["category"].get("Cacao fermentado")
    pt_cacao = S["product_type"].get("cacao")
    prods = [
        ("CAC-CRI-001", "Cacao Criollo Premium 100g/100granos", "criollo", cat_grano, pt_cacao,
         {"variedad": "criollo", "fermentation_days": 6, "moisture_pct": 7.2, "grano_calibre": 110}),
        ("CAC-TRI-001", "Cacao Trinitario Fino", "trinitario", cat_grano, pt_cacao,
         {"variedad": "trinitario", "fermentation_days": 5, "moisture_pct": 7.5, "grano_calibre": 95}),
        ("CAC-FOR-001", "Cacao Forastero Commodity", "forastero", cat_grano, pt_cacao,
         {"variedad": "forastero", "fermentation_days": 4, "moisture_pct": 8.0, "grano_calibre": 80}),
        ("CAC-NIB-001", "Cacao Nibs Fermentado", "nibs", cat_ferm, pt_cacao,
         {"variedad": "trinitario", "fermentation_days": 7, "moisture_pct": 5.0}),
        ("CAC-MAN-001", "Manteca de Cacao", "manteca", cat_ferm, pt_cacao,
         {"variedad": "trinitario"}),
    ]
    for sku, name, key, cat_id, pt_id, attrs in prods:
        body = {"sku": sku, "name": name, "description": name,
                "product_type_id": pt_id, "category_id": cat_id,
                "unit_of_measure": "kg", "track_batches": True, "min_stock_level": 100,
                "reorder_point": 500, "reorder_quantity": 2000, "is_tax_exempt": True,
                "tax_rate_id": S["tax_rate"].get("iva0"),
                "preferred_currency": "COP", "commodity_type": "cacao",
                "attributes": attrs}
        sc, data = req("POST", "/api/v1/products", body, label=f"prod.{sku}")
        if sc in (200, 201):
            S["product"][key] = data["id"]


# ══════════════════════════════════════════════════════════════════════════
# 10-11. Trace: custodian types + organizations + wallets
# ══════════════════════════════════════════════════════════════════════════
def seed_trace():
    print("\n=== 10. Custodian types ===")
    for name, slug, icon in [("Farm", "farm", "sprout"), ("Warehouse", "warehouse", "warehouse"),
                              ("Truck", "truck", "truck"), ("Port", "port", "anchor"), ("Customs", "customs", "shield")]:
        sc, data = req("POST", "/api/v1/taxonomy/custodian-types",
                       {"name": name, "slug": slug, "color": "#6366f1", "icon": icon}, label=f"ct.{slug}")
        if sc in (200, 201):
            S["custodian_type"][slug] = data["id"]

    print("\n=== 11. Organizations ===")
    farm_type = S["custodian_type"].get("farm")
    if not farm_type:
        print("  WARN: no farm custodian type; organizations skipped")
        return
    for name, tags in [("Coop San Vicente del Caguán", ["caqueta", "cacao"]),
                        ("Asocafé Huila", ["huila", "cacao"]),
                        ("Cacaoteros Apartadó", ["antioquia", "cacao"])]:
        sc, data = req("POST", "/api/v1/taxonomy/organizations",
                       {"name": name, "custodian_type_id": farm_type, "description": name, "tags": tags},
                       label=f"org.{name[:15]}")
        if sc in (200, 201):
            S["organization"][name] = data["id"]

    # Exporter org (own)
    wh_type = S["custodian_type"].get("warehouse")
    if wh_type:
        sc, data = req("POST", "/api/v1/taxonomy/organizations",
                       {"name": "Cacao Origen Colombia S.A.S.", "custodian_type_id": wh_type,
                        "description": "Empresa exportadora principal", "tags": ["exporter", "own"]},
                       label="org.exporter")
        if sc in (200, 201):
            S["organization"]["exporter"] = data["id"]

    print("\n=== 15. Wallets (generate) ===")
    for org_name, logical in list(S["organization"].items()):
        sc, data = req("POST", "/api/v1/registry/wallets/generate",
                       {"tags": ["farm", "cacao"], "name": f"W-{org_name[:20]}", "organization_id": logical},
                       label=f"wallet.gen.{org_name[:15]}")
        if sc in (200, 201):
            S["wallet"][org_name] = {"id": data["id"], "pubkey": data["wallet_pubkey"]}


# ══════════════════════════════════════════════════════════════════════════
# 12-13. Compliance EUDR activation + plots
# ══════════════════════════════════════════════════════════════════════════
def seed_compliance_activation():
    print("\n=== 12. Activate EUDR framework ===")
    sc, data = req("POST", "/api/v1/compliance/activations/",
                   {"framework_slug": "eudr", "export_destination": ["CH", "EU"]},
                   label="compl.activate.eudr")
    if sc in (200, 201):
        S["activation"]["eudr"] = data.get("id")


def _poly(cx, cy, delta=0.01):
    """Square polygon ~50 ha around (cx, cy). EUDR Art. 2(28) requires >= 6 decimals.

    Note: Python's JSON encoder will strip trailing zeros from floats, so we use
    format strings to force exactly 6 decimals, and parse back to float. Small
    prime offsets ensure the value truly has 6 non-zero decimals.
    """
    # Use non-trailing-zero values by adding tiny irrational-ish offsets
    # Use offsets that guarantee exactly 6 non-zero decimals regardless of center.
    # E.g., 0.006543 and 0.006547 never produce trailing zeros when added/subtracted
    # from values with at most 1 decimal like 2.5, 7.8, 2.0.
    d1 = 0.006543
    d2 = 0.006547
    pts = [
        (cx - d1, cy - d2), (cx + d2, cy - d1),
        (cx + d1, cy + d2), (cx - d2, cy + d1),
        (cx - d1, cy - d2),
    ]
    # Force 6-decimal strings → floats via string round-trip
    ring = [[float(f"{p[0]:.6f}"), float(f"{p[1]:.6f}")] for p in pts]
    # Ensure each coord literally has 6 decimals in JSON by using Decimal semantics;
    # JSON encoding of floats in Python defaults to repr which drops trailing zeros.
    # The validator inspects the raw JSON number; to guarantee 6-decimal literal,
    # keep digits non-zero.
    return {"type": "Polygon", "coordinates": [[[round(x, 6), round(y, 6)] for x, y in ring]]}


def seed_plots():
    print("\n=== 13. Plots ===")
    plots = [
        ("PLOT-HUI-001", "Huila", "Pitalito", "La Esperanza", 2.5, -75.5, "Finca El Paraíso", "900.111.222-3"),
        ("PLOT-ANT-001", "Antioquia", "Apartadó", "San Martín", 7.8, -75.9, "Finca Las Palmeras", "900.222.333-4"),
        ("PLOT-CAQ-001", "Caquetá", "San Vicente del Caguán", "El Diamante", 2.0, -74.7, "Finca La Selva", "900.333.444-5"),
    ]
    for code, region, municipality, vereda, lat, lng, owner, nit in plots:
        body = {
            "plot_code": code, "plot_area_ha": "50.0",
            "geolocation_type": "polygon", "lat": str(lat), "lng": str(lng),
            "geojson_data": _poly(lng, lat),
            "country_code": "CO", "region": region, "municipality": municipality, "vereda": vereda,
            "commodity_type": "cacao", "crop_type": "Cacao Fino de Aroma",
            "scientific_name": "Theobroma cacao L.",
            "establishment_date": "2015-03-15",
            "last_harvest_date": "2026-02-10",
            "deforestation_free": True, "cutoff_date_compliant": True, "legal_land_use": True,
            "risk_level": "standard",
            "owner_name": owner, "owner_id_type": "NIT", "owner_id_number": nit,
            "producer_name": owner, "producer_id_type": "NIT", "producer_id_number": nit,
            "tenure_type": "owned", "producer_scale": "smallholder",
            "capture_method": "handheld_gps", "gps_accuracy_m": "3.5",
            "capture_date": "2026-01-20",
            "coordinate_system_datum": "WGS84",
        }
        sc, data = req("POST", "/api/v1/compliance/plots/", body, label=f"plot.{code}")
        if sc in (200, 201):
            S["plot"][code] = data["id"]


# ══════════════════════════════════════════════════════════════════════════
# 16-17. Assets (NFTs) + custody events
# ══════════════════════════════════════════════════════════════════════════
def seed_workflow_preset():
    print("\n=== 15.5 Seed workflow preset (required for asset mint) ===")
    # Check if states already exist
    sc, lst = req("GET", "/api/v1/config/workflow/states", label="wf.list")
    if isinstance(lst, list) and len(lst) > 0:
        print(f"  workflow already has {len(lst)} states; skipping seed")
        return
    req("POST", "/api/v1/config/workflow/seed/supply_chain", {}, label="wf.seed.supply_chain")


def seed_assets_and_events():
    print("\n=== 16. Assets (mint) ===")
    # Pick wallets
    wallets = list(S["wallet"].values())
    if len(wallets) < 4:
        print("  WARN: not enough wallets")
        return
    # Map first 3 org wallets as initial custodians, 4th is exporter
    org_wallet_list = list(S["wallet"].items())  # (org_name, {id, pubkey})
    # Pull plot ids by index
    plot_vals = list(S["plot"].values())
    lot_plans = [
        ("Lote Export #001 — 12 tons criollo", "cacao-criollo", 12000, "criollo"),
        ("Lote Export #002 — 8 tons trinitario", "cacao-trinitario", 8000, "trinitario"),
        ("Lote Export #003 — 15 tons forastero", "cacao-forastero", 15000, "forastero"),
    ]
    for i, (name, ptype, qty, variety) in enumerate(lot_plans):
        org_name, wallet = org_wallet_list[i]
        plot_id = plot_vals[i] if i < len(plot_vals) else None
        body = {
            "product_type": ptype,
            "metadata": {
                "name": name, "description": name,
                "quantity_kg": qty, "weight_kg": qty, "commodity_type": "cacao",
                "variedad": variety, "country": "CO", "country_of_production": "CO",
                "origin_plot_id": str(plot_id) if plot_id else None,
                "destination": "CH", "buyer": "Barry Callebaut AG",
            },
            "initial_custodian_wallet": wallet["pubkey"],
            "plot_id": str(plot_id) if plot_id else None,
        }
        sc, data = req("POST", "/api/v1/assets/mint", body, label=f"asset.mint.{i+1}")
        if sc in (200, 201) and data:
            asset = data.get("asset", {})
            S["asset"][name] = asset.get("id")
            print(f"    asset[{i+1}] id={asset.get('id')} state={asset.get('state')}")

    print("\n=== 17. Custody events ===")
    exporter_wallet = org_wallet_list[-1][1]["pubkey"] if org_wallet_list else None
    for lot_idx, (name, _, _, _) in enumerate(lot_plans):
        asset_id = S["asset"].get(name)
        if not asset_id:
            continue
        # Loaded (IN_CUSTODY -> LOADED)
        req("POST", f"/api/v1/assets/{asset_id}/events/loaded",
            {"location": {"lat": 2.5, "lng": -75.5, "description": "Fermentadero Popayán"},
             "data": {"step": "FERMENTATION"}}, label=f"evt.loaded.{lot_idx}")
        # QC pass (LOADED -> QC_PASSED)
        req("POST", f"/api/v1/assets/{asset_id}/events/qc",
            {"result": "pass", "notes": "Muestra cumple moisture<8% y fermentation_days>=5",
             "data": {"moisture_pct": 7.3}}, label=f"evt.qc.{lot_idx}")
        # Handoff to exporter
        if exporter_wallet:
            req("POST", f"/api/v1/assets/{asset_id}/events/handoff",
                {"to_wallet": exporter_wallet,
                 "location": {"lat": 3.88, "lng": -77.03, "description": "Secadero Buenaventura"},
                 "data": {"step": "DRYING_HANDOFF"}}, label=f"evt.handoff1.{lot_idx}")
            # Arrived in Cartagena
            req("POST", f"/api/v1/assets/{asset_id}/events/arrived",
                {"location": {"lat": 10.32, "lng": -75.5, "description": "Bodega Exportación Cartagena"},
                 "data": {"step": "ARRIVED_CARTAGENA"}}, label=f"evt.arrived.{lot_idx}")


# ══════════════════════════════════════════════════════════════════════════
# 18-20. Production (recipe, resource, run)
# ══════════════════════════════════════════════════════════════════════════
def seed_production():
    print("\n=== 18-19. Recipe + resource ===")
    trini = S["product"].get("trinitario")
    nibs = S["product"].get("nibs")
    if not (trini and nibs):
        print("  WARN: missing products for recipe")
        return

    # Resource
    sc, data = req("POST", "/api/v1/production-resources",
                   {"name": "Tambor de fermentación 500L", "resource_type": "equipment",
                    "cost_per_hour": "15000", "capacity_hours_per_day": "24", "efficiency_pct": "85"},
                   label="res.tambor")
    if sc in (200, 201):
        S["resource"]["tambor"] = data["id"]

    # Recipe: 1 kg of nibs needs 1.2 kg trinitario (yield 83%)
    body = {
        "name": "Receta Nibs Fermentado - ex Trinitario",
        "output_entity_id": nibs, "output_quantity": "1",
        "description": "1 kg nibs fermentado = 1.2 kg trinitario (yield 83%)",
        "bom_type": "production", "standard_cost": "18000",
        "components": [{"component_entity_id": trini, "quantity_required": "1.2", "issue_method": "manual"}],
    }
    sc, data = req("POST", "/api/v1/recipes", body, label="recipe.nibs")
    if sc in (200, 201):
        S["recipe"]["nibs"] = data["id"]

    print("\n=== 20. Production run + emission + receipt ===")
    # Need stock of trinitario first; inject via a movement (purchase/adj_in)
    wh_ferm = S["warehouse"].get("FERM-POP")
    wh_exp = S["warehouse"].get("EXP-CTG")
    if wh_ferm and trini:
        # Stock in for trinitario (so emission can consume it). Use /stock/adjust-in
        req("POST", "/api/v1/stock/adjust-in",
            {"product_id": trini, "warehouse_id": wh_ferm,
             "quantity": "1500", "unit_cost": "14500",
             "reason": "Seed initial stock for production run"},
            label="stock.seed.trinitario")

    recipe_id = S["recipe"].get("nibs")
    if not recipe_id or not wh_ferm:
        print("  WARN: cannot create run (missing recipe/warehouse)")
        return

    sc, data = req("POST", "/api/v1/production-runs",
                   {"recipe_id": recipe_id, "warehouse_id": wh_ferm,
                    "output_warehouse_id": wh_exp or wh_ferm,
                    "multiplier": "800",
                    "notes": "Corrida de 800 kg nibs fermentado (consume ~960 kg trinitario)",
                    "priority": 70},
                   label="run.create")
    if sc in (200, 201):
        S["run"]["run1"] = data["id"]
        run_id = data["id"]
        # Release (some services use /release to transition draft -> in progress)
        req("POST", f"/api/v1/production-runs/{run_id}/release", {}, label="run.release")
        # Create emission (auto from BOM)
        sc2, em = req("POST", f"/api/v1/production-runs/{run_id}/emissions",
                       {"notes": "Material issue - consume trinitario"}, label="run.emission")
        if sc2 in (200, 201):
            S["emission"]["em1"] = em.get("id")
        # Create receipt (auto finished goods)
        sc3, rc = req("POST", f"/api/v1/production-runs/{run_id}/receipts",
                      {"notes": "Receipt nibs - 800 kg"}, label="run.receipt")
        if sc3 in (200, 201):
            S["receipt"]["rc1"] = rc.get("id")
        # Close run
        req("POST", f"/api/v1/production-runs/{run_id}/close", {}, label="run.close")


# ══════════════════════════════════════════════════════════════════════════
# 21-28. Compliance: records + risk + supply chain + docs + certs + DDS
# ══════════════════════════════════════════════════════════════════════════
def seed_compliance_records():
    print("\n=== 21. Compliance records per lot ===")
    asset_ids = list(S["asset"].values())
    plot_ids = list(S["plot"].values())
    lot_names = list(S["asset"].keys())
    for i, aid in enumerate(asset_ids):
        body = {
            "asset_id": aid,
            "framework_slug": "eudr",
            "hs_code": "180100",  # Cocoa beans
            "commodity_type": "cacao",
            "product_description": lot_names[i],
            "scientific_name": "Theobroma cacao L.",
            "quantity_kg": str([12000, 8000, 15000][i]) if i < 3 else "5000",
            "quantity_unit": "kg",
            "country_of_production": "CO",
            "production_period_start": "2025-11-01",
            "production_period_end": "2026-02-28",
            "supplier_name": list(S["supplier"].keys())[i] if i < len(S["supplier"]) else "Coop default",
            "supplier_address": "Colombia",
            "buyer_name": "Barry Callebaut AG",
            "buyer_address": "Hardturmstrasse 181, 8005 Zürich, Switzerland",
            "buyer_email": "procurement@barry-callebaut.ch",
            "operator_eori": "CHE105889353",
            "activity_type": "export",
            "deforestation_free_declaration": True,
            "legal_compliance_declaration": True,
            "signatory_name": "Miguel Ruiz",
            "signatory_role": "Compliance Officer",
            "signatory_date": "2026-04-15",
        }
        sc, data = req("POST", "/api/v1/compliance/records/", body, label=f"rec.{i+1}")
        if sc in (200, 201):
            S["record"][lot_names[i]] = data["id"]

    # Link each record to its plot
    rec_ids = list(S["record"].values())
    for i, rid in enumerate(rec_ids):
        if i < len(plot_ids):
            req("POST", f"/api/v1/compliance/records/{rid}/plots",
                {"plot_id": plot_ids[i], "percentage_from_plot": "100"},
                label=f"rec.plotlink.{i+1}")
        # Validate the record to re-evaluate compliance_status
        req("GET", f"/api/v1/compliance/records/{rid}/validate", label=f"rec.validate.{i+1}")

    print("\n=== 22. Risk assessments ===")
    for i, rid in enumerate(rec_ids):
        body = {
            "record_id": rid,
            "country_risk_level": "low",  # CO was recently moved to low-risk by EU; treat accordingly
            "country_risk_notes": "Colombia clasificado bajo riesgo por la Comisión Europea (mayo 2025)",
            "country_benchmarking_source": "EU Commission benchmarking 2025",
            "supply_chain_risk_level": "medium",
            "supply_chain_notes": "Cooperativas con trazabilidad plot-level verificada",
            "supplier_verification_status": "verified",
            "traceability_confidence": "high",
            "regional_risk_level": "low",
            "deforestation_prevalence": "low",
            "indigenous_rights_risk": False,
            "corruption_index_note": "Transparency Int'l CPI 2024 score 39/100",
            "mitigation_measures": [
                {"type": "satellite_monitoring", "description": "Monitoreo satelital trimestral via PRODES/JAXA"},
                {"type": "third_party_audit", "description": "Auditoría Rainforest Alliance anual"},
                {"type": "plot_geolocation", "description": "100% plots con GPS handheld validado"},
            ],
            "additional_info_requested": False,
            "independent_audit_required": False,
            "overall_risk_level": "low",
            "conclusion": "negligible_risk",
            "conclusion_notes": "Tras el risk assessment EUDR Art. 10, concluimos que el riesgo de deforestación/degradación asociado al lote es despreciable.",
        }
        sc, data = req("POST", "/api/v1/compliance/risk-assessments/", body, label=f"risk.{i+1}")
        if sc in (200, 201):
            S["risk"][f"risk{i+1}"] = data["id"]
            # Complete it
            req("POST", f"/api/v1/compliance/risk-assessments/{data['id']}/complete", {}, label=f"risk.complete.{i+1}")

    print("\n=== 23. Supply chain nodes ===")
    for i, rid in enumerate(rec_ids):
        sup_name = list(S["supplier"].keys())[i] if i < len(S["supplier"]) else "Unknown"
        nodes = [
            {"sequence_order": 1, "role": "producer", "actor_name": sup_name,
             "actor_address": "Colombia", "actor_country": "CO", "actor_tax_id": "900.111.222-3",
             "handoff_date": "2026-02-15", "verification_status": "verified"},
            {"sequence_order": 2, "role": "cooperative", "actor_name": sup_name,
             "actor_address": "Colombia", "actor_country": "CO", "handoff_date": "2026-02-20",
             "verification_status": "verified"},
            {"sequence_order": 3, "role": "processor", "actor_name": "Extractora Colombia S.A.",
             "actor_address": "Cartagena, Colombia", "actor_country": "CO",
             "handoff_date": "2026-03-05", "verification_status": "verified"},
            {"sequence_order": 4, "role": "exporter", "actor_name": "Cacao Origen Colombia S.A.S.",
             "actor_address": "Cartagena, Colombia", "actor_country": "CO",
             "handoff_date": "2026-03-20", "verification_status": "verified"},
            {"sequence_order": 5, "role": "importer", "actor_name": "Barry Callebaut AG",
             "actor_address": "Zürich, Switzerland", "actor_country": "CH",
             "actor_tax_id": "CHE-105.889.353", "actor_eori": "CHE105889353",
             "handoff_date": "2026-04-05", "verification_status": "verified"},
        ]
        for n in nodes:
            sc, data = req("POST", f"/api/v1/compliance/records/{rid}/supply-chain/", n,
                           label=f"node.{i+1}.{n['sequence_order']}")
            if sc in (200, 201):
                S["node"].append({"record": rid, "seq": n["sequence_order"], "id": data["id"]})

    print("\n=== 24. Certificates (generate PDF) ===")
    for i, rid in enumerate(rec_ids):
        sc, data = req("POST", f"/api/v1/compliance/records/{rid}/certificate",
                       {}, label=f"cert.{i+1}")
        if sc in (200, 201):
            S["cert"][f"cert{i+1}"] = data.get("id")

    print("\n=== 25. Submit DDS (mark first record as submitted to TRACES NT) ===")
    if rec_ids:
        rid = rec_ids[0]
        sc, data = req("POST", f"/api/v1/compliance/records/{rid}/submit-traces",
                       {"reference_number": "DDS-CO-2026-0001",
                        "simulate": True},
                       label="dds.submit.1")
        # PATCH declaration just in case
        req("PATCH", f"/api/v1/compliance/records/{rid}/declaration",
            {"declaration_reference": "DDS-CO-2026-0001",
             "declaration_status": "submitted",
             "declaration_submission_date": "2026-04-15"},
            label="dds.patch.1")


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════
def load_prev():
    if STATE_PATH.exists():
        try:
            prev = json.loads(STATE_PATH.read_text())
            for k, v in prev.items():
                if k in S and not S[k]:
                    S[k] = v
            print(f"  loaded previous state from {STATE_PATH.name}")
        except Exception as exc:
            print(f"  could not load previous state: {exc}")


def main():
    load_prev()
    LOG_PATH.write_text("")  # reset log
    start = time.time()
    steps = [
        seed_uom, seed_taxes, seed_categories, seed_product_type,
        seed_warehouses, seed_movement_types, seed_partner_types,
        seed_suppliers_customers, seed_products,
        seed_trace, seed_workflow_preset, seed_compliance_activation, seed_plots,
        seed_assets_and_events, seed_production, seed_compliance_records,
    ]
    for fn in steps:
        try:
            fn()
            save_state()
        except Exception as exc:
            print(f"  [FATAL] {fn.__name__}: {exc}")
            traceback.print_exc()
            S["bugs"].append({"step": fn.__name__, "exc": str(exc), "tb": traceback.format_exc()})
            save_state()
    print(f"\n=== DONE in {time.time()-start:.1f}s ===")
    print(f"  bugs: {len(S['bugs'])}")
    print(f"  log: {LOG_PATH}")
    print(f"  state: {STATE_PATH}")


if __name__ == "__main__":
    main()
