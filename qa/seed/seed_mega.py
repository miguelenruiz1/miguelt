#!/usr/bin/env python3
"""
MEGA E2E seeder — Cacao Origen Colombia S.A.S. -> Barry Callebaut (EUDR).
Exercises inventory, production, logistics, compliance with maximum endpoint coverage.

Idempotent: reruns reuse state from seed_mega_state.json.
Log: seed_mega_run.jsonl. Bugs accumulated in S['bugs'].
"""
from __future__ import annotations
import json, os, sys, time, pathlib, datetime, traceback, uuid
from typing import Any

try:
    import requests
except ImportError:
    print("need requests", file=sys.stderr); sys.exit(1)

BASE = os.environ.get("TRACE_GATEWAY", "http://localhost:9000")
TENANT = "default"
HERE = pathlib.Path(__file__).parent
TOKEN_PATH = HERE / "token.txt"
LOG_PATH = HERE / "seed_mega_run.jsonl"
STATE_PATH = HERE / "seed_mega_state.json"

USER_ID = "f44952c4-8d1f-46d0-ae53-540dcf272843"


def _load_token() -> str:
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text().strip()
    return ""


def _login() -> str:
    print("  → re-login (token missing/expired)")
    r = requests.post(f"{BASE}/api/v1/auth/login",
                      json={"email": "seed-e2e@tracelog.io", "password": "SeedPass123!"},
                      timeout=15)
    r.raise_for_status()
    tok = r.json()["access_token"]
    TOKEN_PATH.write_text(tok)
    return tok


HEADERS: dict[str, str] = {}


def _set_headers(tok: str):
    HEADERS.clear()
    HEADERS.update({
        "Authorization": f"Bearer {tok}",
        "X-Tenant-Id": TENANT,
        "X-User-Id": USER_ID,
        "Content-Type": "application/json",
    })


S: dict[str, Any] = {
    "uom": {}, "uom_conv": {}, "tax_cat": {}, "tax_rate": {},
    "category": {}, "product_type": {}, "order_type": {},
    "custom_field": {}, "supplier_field": {}, "warehouse_field": {}, "movement_field": {},
    "warehouse_type": {}, "warehouse": {}, "location": {},
    "movement_type": {}, "supplier_type": {}, "customer_type": {},
    "supplier": {}, "customer": {}, "partner": {},
    "variant_attr": {}, "variant_opt": {}, "variant": {},
    "product": {}, "batch": {}, "serial": [], "quality_test": [],
    "customer_price": {}, "movement": [],
    "po": {}, "grn": [], "so": {}, "cycle_count": {},
    "shipment_doc": {}, "trade_doc": {},
    "resource": {}, "recipe": {}, "run": {}, "emission": [], "receipt": [],
    "custodian_type": {}, "organization": {}, "wallet": {}, "asset": {},
    "event": [], "event_config": {}, "wf_state": {}, "wf_event_type": {},
    "media_file": {}, "anchor": {},
    "activation": {}, "national_platform": {}, "integration": {},
    "plot": {}, "plot_doc": [], "plot_legal": [],
    "record": {}, "risk": {}, "node": [], "cert": {}, "certification": {},
    "bugs": [],
}


def _log(ev: dict):
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ev, default=str) + "\n")


def req(method: str, path: str, body: Any | None = None, params: dict | None = None,
        label: str = "", retries: int = 2, allow_codes: tuple = ()) -> tuple[int, Any]:
    url = BASE + path
    last_exc = None
    for attempt in range(retries + 1):
        try:
            r = requests.request(method, url, headers=HEADERS, json=body, params=params, timeout=40)
            try: data = r.json()
            except Exception: data = {"_raw": r.text[:400]}
            _log({"ts": datetime.datetime.utcnow().isoformat(), "label": label,
                  "method": method, "path": path, "status": r.status_code,
                  "body": body, "resp": data if r.status_code < 400 else data})
            if r.status_code == 401 and attempt == 0:
                # refresh token
                try:
                    tok = _login(); _set_headers(tok)
                    continue
                except Exception as e:
                    print(f"  [401→relogin failed] {e}")
            if r.status_code >= 500 and attempt < retries:
                time.sleep(1.5 * (attempt + 1)); continue
            if r.status_code >= 500:
                S["bugs"].append({"label": label, "method": method, "url": url,
                                  "status": r.status_code, "resp": data, "body": body})
                print(f"  [500] {label} {method} {path} -> {str(data)[:160]}")
            elif r.status_code >= 400 and r.status_code not in allow_codes:
                print(f"  [{r.status_code}] {label} {method} {path} -> {str(data)[:160]}")
            else:
                short = ""
                if isinstance(data, dict) and "id" in data: short = f"id={data['id'][:8]}"
                print(f"  [{r.status_code}] {label} {short}")
            return r.status_code, data
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1)); continue
            print(f"  [EXC] {label}: {exc}")
            _log({"ts": datetime.datetime.utcnow().isoformat(), "label": label,
                  "exc": str(exc), "url": url})
            S["bugs"].append({"label": label, "url": url, "exc": str(exc)})
            return 0, None
    return 0, None


DIRECT_PORTS = {
    "inventory": "http://localhost:9003",
    "trace": "http://localhost:8000",
    "compliance": "http://localhost:8004",
    "user": "http://localhost:9001",
}


def req_direct(svc: str, method: str, path: str, body: Any | None = None,
               params: dict | None = None, label: str = "",
               allow_codes: tuple = ()) -> tuple[int, Any]:
    base = DIRECT_PORTS.get(svc, "http://localhost:9003")
    url = base + path
    try:
        r = requests.request(method, url, headers=HEADERS, json=body, params=params, timeout=30)
        try: data = r.json()
        except Exception: data = {"_raw": r.text[:400]}
        _log({"ts": datetime.datetime.utcnow().isoformat(), "label": label + ".direct",
              "method": method, "path": path, "status": r.status_code, "body": body, "resp": data})
        if r.status_code >= 500:
            S["bugs"].append({"label": label, "method": method, "url": url,
                              "status": r.status_code, "resp": data, "body": body})
            print(f"  [500.direct] {label} -> {str(data)[:160]}")
        elif r.status_code >= 400 and r.status_code not in allow_codes:
            print(f"  [{r.status_code}.direct] {label} -> {str(data)[:160]}")
        else:
            short = ""
            if isinstance(data, dict) and "id" in data: short = f"id={str(data['id'])[:8]}"
            print(f"  [{r.status_code}.direct] {label} {short}")
        return r.status_code, data
    except Exception as exc:
        print(f"  [EXC.direct] {label}: {exc}")
        return 0, None


def _upload_media_file(filename: str, content: bytes, document_type: str = "general",
                       title: str = "") -> str | None:
    """Upload a file to trace media service via multipart. Returns media_id."""
    url = BASE + "/api/v1/media/files"
    headers = {k: v for k, v in HEADERS.items() if k != "Content-Type"}
    try:
        r = requests.post(
            url, headers=headers,
            files={"file": (filename, content, "application/pdf")},
            params={"category": "documents", "document_type": document_type, "title": title},
            timeout=30,
        )
        try: data = r.json()
        except Exception: data = {"_raw": r.text[:200]}
        _log({"ts": datetime.datetime.utcnow().isoformat(), "label": f"media.upload.{filename}",
              "method": "POST", "path": "/api/v1/media/files",
              "status": r.status_code, "resp": data})
        if r.status_code < 400:
            print(f"  [{r.status_code}] media.upload.{filename} id={str(data.get('id',''))[:8]}")
            return data.get("id")
        else:
            print(f"  [{r.status_code}] media.upload.{filename} -> {str(data)[:120]}")
            return None
    except Exception as exc:
        print(f"  [EXC] media.upload.{filename}: {exc}")
        return None


def save_state():
    STATE_PATH.write_text(json.dumps(S, indent=2, default=str))


def ok(sc): return sc in (200, 201)


def get_id(data, *keys):
    if not isinstance(data, dict): return None
    for k in keys:
        if k in data and data[k]: return data[k]
    return None


# ═══════════════════════════════════════════════════════════════════════
# PHASE 1: UoM + conversions
# ═══════════════════════════════════════════════════════════════════════
def phase_uom():
    print("\n=== PHASE 1: UoM ===")
    # Initialize (idempotent endpoint for standard units)
    req("POST", "/api/v1/uom/initialize", {}, label="uom.initialize")
    # Custom UoMs for cacao
    for body, key in [
        ({"name": "Kilogramo", "symbol": "kg", "category": "weight", "is_base": True}, "kg"),
        ({"name": "Tonelada", "symbol": "ton", "category": "weight", "is_base": False}, "ton"),
        ({"name": "Saco 60kg", "symbol": "sc60", "category": "weight", "is_base": False}, "sc60"),
        ({"name": "Saco 45kg", "symbol": "sc45", "category": "weight", "is_base": False}, "sc45"),
    ]:
        if S["uom"].get(key): continue
        sc, data = req("POST", "/api/v1/uom", body, label=f"uom.create.{key}", allow_codes=(409,))
        if ok(sc) and get_id(data, "id"): S["uom"][key] = data["id"]
        elif sc == 409:
            # Lookup existing
            _, lst = req("GET", "/api/v1/uom", label=f"uom.list.{key}")
            if isinstance(lst, list):
                for it in lst:
                    if it.get("symbol") == body["symbol"]:
                        S["uom"][key] = it["id"]; break
    # Conversions
    if S["uom"].get("kg") and S["uom"].get("ton") and not S["uom_conv"].get("ton_kg"):
        sc, d = req("POST", "/api/v1/uom/conversions",
            {"from_uom_id": S["uom"]["ton"], "to_uom_id": S["uom"]["kg"], "factor": "1000"},
            label="uom.conv.ton_kg", allow_codes=(409,))
        if ok(sc): S["uom_conv"]["ton_kg"] = d.get("id")
    if S["uom"].get("kg") and S["uom"].get("sc60") and not S["uom_conv"].get("sc60_kg"):
        sc, d = req("POST", "/api/v1/uom/conversions",
            {"from_uom_id": S["uom"]["sc60"], "to_uom_id": S["uom"]["kg"], "factor": "60"},
            label="uom.conv.sc60_kg", allow_codes=(409,))
        if ok(sc): S["uom_conv"]["sc60_kg"] = d.get("id")
    if S["uom"].get("kg") and S["uom"].get("sc45") and not S["uom_conv"].get("sc45_kg"):
        sc, d = req("POST", "/api/v1/uom/conversions",
            {"from_uom_id": S["uom"]["sc45"], "to_uom_id": S["uom"]["kg"], "factor": "45"},
            label="uom.conv.sc45_kg", allow_codes=(409,))
        if ok(sc): S["uom_conv"]["sc45_kg"] = d.get("id")
    # Convert query
    if S["uom"].get("kg") and S["uom"].get("ton"):
        req("POST", "/api/v1/uom/convert",
            {"from_uom_id": S["uom"]["ton"], "to_uom_id": S["uom"]["kg"], "quantity": "2.5"},
            label="uom.convert.test")
    # Catalog
    req("GET", "/api/v1/uom/catalog", label="uom.catalog")
    req("GET", "/api/v1/uom/conversions", label="uom.conv.list")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 2: Tax categories + tax rates
# ═══════════════════════════════════════════════════════════════════════
def phase_taxes():
    print("\n=== PHASE 2: Taxes ===")
    # Tax categories (lock = iva + retefuente)
    for body, key in [
        ({"slug": "iva", "name": "IVA Colombia", "behavior": "addition", "base_kind": "subtotal"}, "iva"),
        ({"slug": "retefuente", "name": "Retención en la fuente", "behavior": "withholding", "base_kind": "subtotal"}, "retefuente"),
    ]:
        if S["tax_cat"].get(key): continue
        sc, d = req("POST", "/api/v1/tax-categories", body, label=f"taxcat.{key}", allow_codes=(409,))
        if ok(sc): S["tax_cat"][key] = d["id"]
        elif sc == 409:
            _, lst = req("GET", "/api/v1/tax-categories", label=f"taxcat.list.{key}")
            if isinstance(lst, list):
                for it in lst:
                    if it.get("slug") == key: S["tax_cat"][key] = it["id"]; break
    # Initialize default tax rates
    req("POST", "/api/v1/tax-rates/initialize", {}, label="taxrate.initialize")
    # Custom tax rates
    for body, key in [
        ({"name": "IVA 19% (general)", "rate": "0.19", "category_slug": "iva", "is_default": False, "dian_code": "01"}, "iva19"),
        ({"name": "IVA 5% (alimentos)", "rate": "0.05", "category_slug": "iva", "is_default": False, "dian_code": "02"}, "iva5"),
        ({"name": "IVA 0% (exento cacao crudo)", "rate": "0.0", "category_slug": "iva", "is_default": True, "dian_code": "03"}, "iva0"),
        ({"name": "Retención servicios 4%", "rate": "0.04", "category_slug": "retefuente", "is_default": False, "dian_code": "06"}, "ret4"),
        ({"name": "Retención compras 2.5%", "rate": "0.025", "category_slug": "retefuente", "is_default": False, "dian_code": "07"}, "ret25"),
    ]:
        if S["tax_rate"].get(key): continue
        sc, d = req("POST", "/api/v1/tax-rates", body, label=f"taxrate.{key}", allow_codes=(409,))
        if ok(sc): S["tax_rate"][key] = d["id"]
    req("GET", "/api/v1/tax-rates/summary", label="taxrate.summary")
    req("GET", "/api/v1/tax-rates", label="taxrate.list")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: Categories (jerarquía)
# ═══════════════════════════════════════════════════════════════════════
def phase_categories():
    print("\n=== PHASE 3: Categories ===")
    def create_cat(name, parent_id=None):
        if S["category"].get(name): return S["category"][name]
        body = {"name": name, "description": f"Categoría {name}"}
        if parent_id: body["parent_id"] = parent_id
        sc, d = req("POST", "/api/v1/categories", body, label=f"cat.{name}", allow_codes=(409,))
        if ok(sc) and get_id(d, "id"):
            S["category"][name] = d["id"]; return d["id"]
        return None
    root_grano = create_cat("Cacao en grano")
    create_cat("Criollo", root_grano)
    create_cat("Trinitario", root_grano)
    create_cat("Forastero", root_grano)
    root_pt = create_cat("Productos terminados")
    create_cat("Chocolate", root_pt)
    create_cat("Nibs", root_pt)
    create_cat("Manteca", root_pt)
    create_cat("Insumos agrícolas")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 4: Config — product types, order types, supplier types, movement types,
#                warehouse types, customer types, + custom fields (4 entity scopes)
# ═══════════════════════════════════════════════════════════════════════
def phase_config():
    print("\n=== PHASE 4: Config (types + custom fields) ===")
    # Product types
    pt_defs = [
        ("Cacao variedad", "cacao-variedad", "#8B4513", "CAC", True, True),
        ("Producto terminado", "producto-terminado", "#D97706", "PT", True, True),
    ]
    for name, slug, color, prefix, tracks, qc in pt_defs:
        if S["product_type"].get(slug): continue
        sc, d = req("POST", "/api/v1/config/product-types",
                    {"name": name, "slug": slug, "description": name, "color": color,
                     "tracks_batches": tracks, "requires_qc": qc, "sku_prefix": prefix},
                    label=f"pt.{slug}", allow_codes=(409,))
        if ok(sc): S["product_type"][slug] = d["id"]

    # Custom fields on product type "cacao-variedad"
    pt_id = S["product_type"].get("cacao-variedad")
    if pt_id:
        cf_defs = [
            ("Variedad", "variedad", "select", ["criollo", "trinitario", "forastero"], True, 1),
            ("Días fermentación", "fermentation_days", "number", None, False, 2),
            ("Humedad %", "moisture_pct", "number", None, False, 3),
            ("Origen Plot ID", "origen_plot_id", "text", None, False, 4),
            ("Calibre granos/100g", "grano_calibre", "number", None, False, 5),
        ]
        for label_, key, ftype, opts, req_, order in cf_defs:
            if S["custom_field"].get(key): continue
            body = {"label": label_, "field_key": key, "field_type": ftype,
                    "required": req_, "sort_order": order, "product_type_id": pt_id}
            if opts: body["options"] = opts
            sc, d = req("POST", "/api/v1/config/custom-fields", body,
                        label=f"pt.cf.{key}", allow_codes=(409,))
            if ok(sc): S["custom_field"][key] = d["id"]

    # Order types
    for name, slug, color in [
        ("Compra nacional", "compra-nacional", "#0ea5e9"),
        ("Export FOB", "export-fob", "#7c3aed"),
    ]:
        if S["order_type"].get(slug): continue
        sc, d = req("POST", "/api/v1/config/order-types",
                    {"name": name, "slug": slug, "color": color},
                    label=f"ot.{slug}", allow_codes=(409,))
        if ok(sc): S["order_type"][slug] = d["id"]

    # Supplier types
    for name, slug, color in [
        ("Cooperativa", "cooperativa", "#16a34a"),
        ("Productor individual", "productor", "#65a30d"),
    ]:
        if S["supplier_type"].get(slug): continue
        sc, d = req("POST", "/api/v1/config/supplier-types",
                    {"name": name, "slug": slug, "color": color},
                    label=f"st.{slug}", allow_codes=(409,))
        if ok(sc): S["supplier_type"][slug] = d["id"]

    # Customer types
    for name, slug, color in [
        ("Chocolatero Internacional", "choco-intl", "#7c2d12"),
        ("Distribuidor Nacional", "dist-nac", "#ca8a04"),
    ]:
        if S["customer_type"].get(slug): continue
        sc, d = req("POST", "/api/v1/config/customer-types",
                    {"name": name, "slug": slug, "color": color},
                    label=f"ct.{slug}", allow_codes=(409,))
        if ok(sc): S["customer_type"][slug] = d["id"]

    # Movement types
    for name, slug, direction in [
        ("Entrada cosecha", "entrada-cosecha", "in"),
        ("Transferencia ferm→secado", "ferm-secado", "transfer"),
        ("Salida exportación", "salida-export", "out"),
        ("Ajuste QC", "ajuste-qc", "adjustment"),
    ]:
        if S["movement_type"].get(slug): continue
        sc, d = req("POST", "/api/v1/config/movement-types",
                    {"name": name, "slug": slug, "direction": direction, "affects_cost": True},
                    label=f"mt.{slug}", allow_codes=(409,))
        if ok(sc): S["movement_type"][slug] = d["id"]

    # Warehouse types
    for name, slug, color in [
        ("Fermentadero", "fermentadero", "#ca8a04"),
        ("Secadero", "secadero", "#d97706"),
        ("Bodega exportación", "bodega-exp", "#b45309"),
    ]:
        if S["warehouse_type"].get(slug): continue
        sc, d = req("POST", "/api/v1/config/warehouse-types",
                    {"name": name, "slug": slug, "color": color},
                    label=f"wht.{slug}", allow_codes=(409,))
        if ok(sc): S["warehouse_type"][slug] = d["id"]

    # Supplier custom fields (FieldType = text|number|select|boolean|date|reference)
    sup_cf = [
        ("NIT + DV", "nit", "text", True, 1),
        ("Régimen fiscal", "regimen_fiscal", "select", False, 2, ["simplificado", "comun", "gran_contribuyente"]),
        ("Certificación Rainforest Alliance", "ra_certified", "boolean", False, 3),
    ]
    for tup in sup_cf:
        label_, key, ftype, req_, order, *opts = (*tup, None) if len(tup) == 5 else tup
        if S["supplier_field"].get(key): continue
        body = {"label": label_, "field_key": key, "field_type": ftype,
                "required": req_, "sort_order": order}
        if opts and opts[0]: body["options"] = opts[0]
        sc, d = req("POST", "/api/v1/config/supplier-fields", body,
                    label=f"sf.{key}", allow_codes=(409,))
        if ok(sc): S["supplier_field"][key] = d["id"]

    # Warehouse custom fields
    for label_, key, ftype, order in [
        ("Capacidad toneladas", "capacity_tons", "number", 1),
        ("Certificación GMP+", "gmp_cert", "boolean", 2),
    ]:
        if S["warehouse_field"].get(key): continue
        sc, d = req("POST", "/api/v1/config/warehouse-fields",
                    {"label": label_, "field_key": key, "field_type": ftype, "sort_order": order},
                    label=f"wf.{key}", allow_codes=(409,))
        if ok(sc): S["warehouse_field"][key] = d["id"]

    # Movement custom fields
    for label_, key, ftype, order in [
        ("Número de placa camión", "truck_plate", "text", 1),
        ("Temperatura °C", "temp_c", "number", 2),
    ]:
        if S["movement_field"].get(key): continue
        sc, d = req("POST", "/api/v1/config/movement-fields",
                    {"label": label_, "field_key": key, "field_type": ftype, "sort_order": order},
                    label=f"mf.{key}", allow_codes=(409,))
        if ok(sc): S["movement_field"][key] = d["id"]

    # Config: margins, features, SO approval threshold
    req("GET", "/api/v1/config/margins", label="cfg.margins.get")
    req("PATCH", "/api/v1/config/margins", {"min_margin_pct": "5", "target_margin_pct": "25"},
        label="cfg.margins.set")
    req("GET", "/api/v1/config/features", label="cfg.features.get")
    req("GET", "/api/v1/config/so-approval-threshold", label="cfg.sothresh.get")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 5: Warehouses + locations
# ═══════════════════════════════════════════════════════════════════════
def phase_warehouses():
    print("\n=== PHASE 5: Warehouses + locations ===")
    wh_list = [
        ("Fermentadero Popayán", "FERM-POP", "fermentadero", "main",
         {"street": "Vereda Caldono km 8", "city": "Popayán", "state": "Cauca", "country": "CO", "lat": 2.5, "lng": -76.6}),
        ("Secadero Buenaventura", "SEC-BUN", "secadero", "main",
         {"street": "Zona Franca Buenaventura", "city": "Buenaventura", "state": "Valle del Cauca", "country": "CO", "lat": 3.88, "lng": -77.03}),
        ("Bodega Exportación Cartagena", "EXP-CTG", "bodega-exp", "main",
         {"street": "Mamonal km 5 Bodega 12", "city": "Cartagena", "state": "Bolívar", "country": "CO", "lat": 10.32, "lng": -75.5}),
    ]
    for name, code, wtslug, wtype, addr in wh_list:
        if S["warehouse"].get(code): continue
        body = {"name": name, "code": code, "type": wtype, "address": addr,
                "warehouse_type_id": S["warehouse_type"].get(wtslug)}
        sc, d = req("POST", "/api/v1/warehouses", body, label=f"wh.{code}", allow_codes=(409,))
        if ok(sc): S["warehouse"][code] = d["id"]

    # Locations (3 per warehouse)
    loc_codes = ["A-01-01", "A-01-02", "B-02-01"]
    for wh_code, wh_id in S["warehouse"].items():
        for i, loc_code in enumerate(loc_codes):
            key = f"{wh_code}:{loc_code}"
            if S["location"].get(key): continue
            body = {
                "warehouse_id": wh_id, "code": f"{wh_code}-{loc_code}", "name": f"Loc {loc_code}",
                "aisle": loc_code.split("-")[0], "rack": loc_code.split("-")[1],
                "bin": loc_code.split("-")[2], "is_active": True,
            }
            sc, d = req("POST", "/api/v1/config/locations", body,
                        label=f"loc.{wh_code}.{loc_code}", allow_codes=(409,))
            if ok(sc): S["location"][key] = d["id"]


# ═══════════════════════════════════════════════════════════════════════
# PHASE 6: Variant attributes + options
# ═══════════════════════════════════════════════════════════════════════
def phase_variants():
    print("\n=== PHASE 6: Variant attributes + options ===")
    if not S["variant_attr"].get("variedad"):
        sc, d = req("POST", "/api/v1/variant-attributes",
                    {"name": "Variedad", "slug": "variedad", "display_order": 1},
                    label="va.variedad", allow_codes=(409,))
        if ok(sc): S["variant_attr"]["variedad"] = d["id"]
    attr_id = S["variant_attr"].get("variedad")
    if attr_id:
        for i, opt in enumerate(["criollo", "trinitario", "forastero"]):
            key = f"variedad:{opt}"
            if S["variant_opt"].get(key): continue
            sc, d = req("POST", f"/api/v1/variant-attributes/{attr_id}/options",
                        {"value": opt, "sort_order": i, "is_active": True},
                        label=f"vo.{opt}", allow_codes=(409, 422, 500))
            if ok(sc): S["variant_opt"][key] = d["id"]
    req("GET", "/api/v1/variant-attributes", label="va.list")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 7: Suppliers + Customers + Partners
# ═══════════════════════════════════════════════════════════════════════
def phase_partners():
    print("\n=== PHASE 7: Suppliers + Customers + Partners ===")
    coop_type = S["supplier_type"].get("cooperativa")
    sups = [
        ("Cooperativa Agroindustrial San Vicente del Caguán", "COOP-SVC", "900.123.456-7",
         {"street": "Calle 6 # 4-12", "city": "San Vicente del Caguán", "state": "Caquetá", "country": "CO"}),
        ("Asocafé Huila Comité de Cacaoteros", "COOP-HUILA", "901.234.567-8",
         {"street": "Carrera 5 # 12-34", "city": "Neiva", "state": "Huila", "country": "CO"}),
        ("Cacaoteros de Apartadó", "COOP-APART", "902.345.678-9",
         {"street": "Av. Principal 45-23", "city": "Apartadó", "state": "Antioquia", "country": "CO"}),
    ]
    for name, code, nit, addr in sups:
        if S["supplier"].get(code): continue
        body = {"name": name, "code": code, "supplier_type_id": coop_type,
                "contact_name": "Gerente Comercial", "email": f"contacto@{code.lower()}.co",
                "phone": "+57 300 1234567", "address": addr, "payment_terms_days": 30,
                "lead_time_days": 14,
                "custom_attributes": {"nit": nit, "regimen_fiscal": "comun", "ra_certified": True}}
        sc, d = req("POST", "/api/v1/suppliers", body, label=f"sup.{code}", allow_codes=(409,))
        if ok(sc): S["supplier"][code] = d["id"]

    # Customers
    ct_int = S["customer_type"].get("choco-intl")
    ct_nac = S["customer_type"].get("dist-nac")
    if not S["customer"].get("bc"):
        sc, d = req("POST", "/api/v1/customers", {
            "name": "Barry Callebaut AG", "code": "BC-CH", "customer_type_id": ct_int,
            "tax_id": "CHE-105.889.353", "tax_id_type": "VAT",
            "contact_name": "Sophie Müller", "email": "procurement@barry-callebaut.ch",
            "phone": "+41 43 204 0404",
            "address": {"street": "Hardturmstrasse 181", "city": "Zürich", "country": "CH", "postal_code": "8005"},
            "shipping_address": {"street": "Hardturmstrasse 181", "city": "Zürich", "country": "CH", "postal_code": "8005"},
            "payment_terms_days": 60,
        }, label="cust.bc", allow_codes=(409,))
        if ok(sc): S["customer"]["bc"] = d["id"]
    if not S["customer"].get("choc-bog"):
        sc, d = req("POST", "/api/v1/customers", {
            "name": "Chocolates Artesanales Bogotá S.A.S.", "code": "CHOC-BOG",
            "customer_type_id": ct_nac, "tax_id": "901.500.600-7", "tax_id_type": "NIT",
            "contact_name": "Laura Gómez", "email": "ventas@chocolates-bogota.co",
            "phone": "+57 310 7654321",
            "address": {"street": "Calle 100 # 15-20", "city": "Bogotá", "country": "CO", "postal_code": "110111"},
            "payment_terms_days": 30,
        }, label="cust.choc-bog", allow_codes=(409,))
        if ok(sc): S["customer"]["choc-bog"] = d["id"]

    # Partner (freight forwarder) — must be either supplier or customer
    if not S["partner"].get("aduanera"):
        sc, d = req("POST", "/api/v1/partners", {
            "name": "Agencia Aduanera Cartagena Ltda.", "code": "AA-CTG",
            "partner_type": "freight_forwarder",
            "is_supplier": True, "is_customer": False,
            "contact_name": "Carlos Pérez", "email": "operaciones@aa-ctg.co",
            "phone": "+57 5 6785432",
            "address": {"street": "Av. Pedro de Heredia 45", "city": "Cartagena", "country": "CO"},
        }, label="partner.aduanera", allow_codes=(409, 422))
        if ok(sc): S["partner"]["aduanera"] = d["id"]


# ═══════════════════════════════════════════════════════════════════════
# PHASE 8: Products (with variants, tax rates, reorder points)
# ═══════════════════════════════════════════════════════════════════════
def phase_products():
    print("\n=== PHASE 8: Products ===")
    cat_grano = S["category"].get("Cacao en grano")
    cat_nibs = S["category"].get("Nibs")
    cat_manteca = S["category"].get("Manteca")
    pt_cacao = S["product_type"].get("cacao-variedad")
    pt_final = S["product_type"].get("producto-terminado")
    iva0 = S["tax_rate"].get("iva0")
    iva19 = S["tax_rate"].get("iva19")

    prods = [
        ("CAC-FINO-001", "Cacao Fino de Aroma Colombia (base)", "cacao-fino", cat_grano, pt_cacao, iva0,
         {"variedad": "trinitario", "fermentation_days": 6, "moisture_pct": 7.3}, True),
        ("CAC-CRI-001", "Cacao Criollo Premium 110g/100granos", "criollo", cat_grano, pt_cacao, iva0,
         {"variedad": "criollo", "fermentation_days": 6, "moisture_pct": 7.2, "grano_calibre": 110}, False),
        ("CAC-TRI-001", "Cacao Trinitario Fino", "trinitario", cat_grano, pt_cacao, iva0,
         {"variedad": "trinitario", "fermentation_days": 5, "moisture_pct": 7.5, "grano_calibre": 95}, False),
        ("CAC-FOR-001", "Cacao Forastero Commodity", "forastero", cat_grano, pt_cacao, iva0,
         {"variedad": "forastero", "fermentation_days": 4, "moisture_pct": 8.0, "grano_calibre": 80}, False),
        ("CAC-NIB-001", "Nibs Fermentado Tostado", "nibs", cat_nibs, pt_final, iva19,
         {"variedad": "trinitario", "fermentation_days": 7, "moisture_pct": 5.0}, False),
        ("CAC-CHO-001", "Chocolate Artesanal 70% cacao", "chocolate-70", cat_nibs, pt_final, iva19, {}, False),
        ("INS-AZU-001", "Azúcar blanco refinado", "azucar", None, pt_final, iva19, {}, False),
        ("INS-MAN-001", "Manteca de cacao premium", "manteca", cat_manteca, pt_final, iva19, {}, False),
        ("INS-LEC-001", "Lecitina de soja", "lecitina", None, pt_final, iva19, {}, False),
    ]
    for sku, name, key, cat_id, pt_id, tax_id, attrs, is_variant_parent in prods:
        if S["product"].get(key): continue
        body = {"sku": sku, "name": name, "description": name,
                "product_type_id": pt_id, "category_id": cat_id,
                "unit_of_measure": "kg", "track_batches": True,
                "min_stock_level": 100, "reorder_point": 500, "reorder_quantity": 2000,
                "tax_rate_id": tax_id,
                "preferred_currency": "COP", "commodity_type": "cacao" if "CAC" in sku else None,
                "attributes": attrs, "has_variants": is_variant_parent,
                "unit_price": "15000" if "CAC" in sku else "8000",
                "unit_cost": "10000" if "CAC" in sku else "5000"}
        sc, d = req("POST", "/api/v1/products", body, label=f"prod.{sku}", allow_codes=(409,))
        if ok(sc): S["product"][key] = d["id"]

    # Create variants for "cacao-fino"
    parent = S["product"].get("cacao-fino")
    attr_id = S["variant_attr"].get("variedad")
    if parent and attr_id:
        for opt_key, opt_id in S["variant_opt"].items():
            variety = opt_key.split(":")[1]
            vkey = f"cacao-fino:{variety}"
            if S["variant"].get(vkey): continue
            body = {
                "product_id": parent,
                "sku": f"CAC-FINO-{variety[:3].upper()}",
                "name": f"Cacao Fino {variety.capitalize()}",
                "option_ids": [opt_id],
                "unit_price": "15500", "unit_cost": "10500",
            }
            sc, d = req("POST", "/api/v1/variants", body, label=f"variant.{variety}",
                        allow_codes=(409, 422))
            if ok(sc): S["variant"][vkey] = d["id"]

    # Configure reorder
    if S["product"].get("trinitario"):
        req("POST", "/api/v1/reorder/check/" + S["product"]["trinitario"], {},
            label="reorder.check.trini")

    req("GET", "/api/v1/products", label="products.list")
    # /reorder/check is POST only
    req("POST", "/api/v1/reorder/check", {}, label="reorder.check.all", allow_codes=(400, 422))


# ═══════════════════════════════════════════════════════════════════════
# PHASE 9: Customer prices (tier pricing)
# ═══════════════════════════════════════════════════════════════════════
def phase_customer_prices():
    print("\n=== PHASE 9: Customer prices ===")
    cust_bc = S["customer"].get("bc")
    if not cust_bc: return
    for pkey in ("criollo", "trinitario", "forastero"):
        pid = S["product"].get(pkey)
        if not pid: continue
        tkey = f"bc:{pkey}"
        if S["customer_price"].get(tkey): continue
        # 15% discount on volume
        body = {"customer_id": cust_bc, "product_id": pid,
                "price": "12750",  # 15000 * 0.85
                "min_quantity": "5000", "currency": "COP",
                "valid_from": "2026-01-01", "valid_until": "2026-12-31",
                "notes": "Volume tier -15% for Barry Callebaut"}
        sc, d = req("POST", "/api/v1/customer-prices", body,
                    label=f"cp.bc.{pkey}", allow_codes=(409,))
        if ok(sc): S["customer_price"][tkey] = d["id"]
    req("GET", "/api/v1/customer-prices/metrics", label="cp.metrics")
    req("GET", "/api/v1/customer-prices/history", label="cp.history")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 10: Compliance - activations, plots, frameworks
# ═══════════════════════════════════════════════════════════════════════
def _poly(cx, cy):
    d1 = 0.006543; d2 = 0.006547
    pts = [(cx - d1, cy - d2), (cx + d2, cy - d1), (cx + d1, cy + d2), (cx - d2, cy + d1), (cx - d1, cy - d2)]
    ring = [[round(x, 6), round(y, 6)] for x, y in pts]
    return {"type": "Polygon", "coordinates": [ring]}


def phase_compliance_setup():
    print("\n=== PHASE 10a: Frameworks list + activate multiple ===")
    req("GET", "/api/v1/compliance/frameworks/", label="framework.list")
    for slug in ("eudr", "sbti", "rainforest-alliance", "usda-nop"):
        if S["activation"].get(slug): continue
        sc, d = req("POST", "/api/v1/compliance/activations/",
                    {"framework_slug": slug, "export_destination": ["CH", "EU", "US"]},
                    label=f"activate.{slug}", allow_codes=(404, 409))
        if ok(sc): S["activation"][slug] = d.get("id") or slug
    # Country risk
    req("GET", "/api/v1/compliance/country-risk/CO", label="country.CO")
    req("POST", "/api/v1/compliance/country-risk/CO",
        {"risk_level": "low", "source": "EU Commission benchmarking 2025",
         "as_of_date": "2025-05-01",
         "notes": "Colombia moved to low-risk by EU benchmarking 2025"},
        label="country.CO.set", allow_codes=(404, 405, 409))
    # National platforms
    req("GET", "/api/v1/compliance/national-platforms/", label="natplat.list")
    # Legal catalog
    req("GET", "/api/v1/compliance/legal/", label="legal.catalog")
    # Integrations
    req("GET", "/api/v1/compliance/integrations/", label="integrations.list")

    print("\n=== PHASE 10b: Plots ===")
    plots = [
        ("PLOT-HUI-001", "Huila", "Pitalito", "La Esperanza", 2.5, -75.5, "Finca El Paraíso", "900.111.222-3", "50.0"),
        ("PLOT-ANT-001", "Antioquia", "Apartadó", "San Martín", 7.8, -75.9, "Finca Las Palmeras", "900.222.333-4", "65.0"),
        ("PLOT-CAQ-001", "Caquetá", "San Vicente del Caguán", "El Diamante", 2.0, -74.7, "Finca La Selva", "900.333.444-5", "45.0"),
    ]
    for code, region, muni, vereda, lat, lng, owner, nit, area in plots:
        if S["plot"].get(code): continue
        body = {
            "plot_code": code, "plot_area_ha": area,
            "geolocation_type": "polygon", "lat": str(lat), "lng": str(lng),
            "geojson_data": _poly(lng, lat),
            "country_code": "CO", "region": region, "municipality": muni, "vereda": vereda,
            "commodity_type": "cacao", "crop_type": "Cacao Fino de Aroma",
            "scientific_name": "Theobroma cacao L.",
            "establishment_date": "2015-03-15", "last_harvest_date": "2026-02-10",
            "deforestation_free": True, "cutoff_date_compliant": True, "legal_land_use": True,
            "risk_level": "standard",
            "owner_name": owner, "owner_id_type": "NIT", "owner_id_number": nit,
            "producer_name": owner, "producer_id_type": "NIT", "producer_id_number": nit,
            "tenure_type": "owned", "producer_scale": "smallholder",
            "capture_method": "handheld_gps", "gps_accuracy_m": "3.5",
            "capture_date": "2026-01-20", "coordinate_system_datum": "WGS84",
        }
        sc, d = req("POST", "/api/v1/compliance/plots/", body, label=f"plot.{code}", allow_codes=(409,))
        if ok(sc): S["plot"][code] = d["id"]

    # Plot documents (require media_file_id → upload dummy file first)
    media_id = _upload_media_file("escritura-sample.pdf", b"%PDF-1.4\nSample plot document seed\n%%EOF",
                                  "plot_document", "plot document seeded for E2E")
    if media_id: S["media_file"]["plot-doc"] = media_id
    for code, pid in list(S["plot"].items()):
        if not media_id: break
        for dtype, name in [("land_title", "Escritura pública"), ("cadastral_cert", "Certificado catastral")]:
            sc, d = req("POST", f"/api/v1/compliance/plots/{pid}/documents",
                        {"document_type": dtype, "document_name": name,
                         "document_reference": f"{code}-{dtype}-2026",
                         "issue_date": "2024-01-15",
                         "media_file_id": media_id},
                        label=f"plot.doc.{code}.{dtype}", allow_codes=(409, 422))
            if ok(sc): S["plot_doc"].append({"plot": code, "type": dtype, "id": d.get("id")})
        # Deforestation screening
        req("POST", f"/api/v1/compliance/plots/{pid}/screen-deforestation", {},
            label=f"plot.defor.{code}", allow_codes=(404, 422, 500))
        # Risk decision
        req("POST", f"/api/v1/compliance/plots/{pid}/risk-decision",
            {"decision": "negligible", "notes": "Plot verified deforestation-free"},
            label=f"plot.risk.{code}", allow_codes=(404, 422))

    # Certifications scheme
    req("GET", "/api/v1/compliance/certifications/", label="cert.schemes.list")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 11: Batches + serials + quality tests + batch_origins
# ═══════════════════════════════════════════════════════════════════════
def phase_batches():
    print("\n=== PHASE 11: Batches + serials + quality tests + batch origins ===")
    prod_trini = S["product"].get("trinitario")
    prod_cri = S["product"].get("criollo")
    prod_for = S["product"].get("forastero")
    plot_hui = S["plot"].get("PLOT-HUI-001")
    plot_ant = S["plot"].get("PLOT-ANT-001")
    plot_caq = S["plot"].get("PLOT-CAQ-001")

    batch_specs = [
        ("COS-2026-001", "trinitario", prod_trini, plot_hui, "2026-02-10", "2027-02-10"),
        ("COS-2026-002", "criollo",    prod_cri,   plot_ant, "2026-02-12", "2027-02-12"),
        ("COS-2026-003", "forastero",  prod_for,   plot_caq, "2026-02-15", "2027-02-15"),
    ]
    for bnum, key, pid, plot_id, prod_date, exp_date in batch_specs:
        if not pid: continue
        if S["batch"].get(bnum): continue
        body = {
            "batch_number": bnum, "entity_id": pid,
            "manufacture_date": prod_date, "expiration_date": exp_date,
            "quantity": "2000", "is_active": True,
            "metadata": {"variedad": key, "plot_code": bnum},
        }
        sc, d = req("POST", "/api/v1/batches", body, label=f"batch.{bnum}",
                    allow_codes=(409, 422))
        if ok(sc): S["batch"][bnum] = d["id"]

        # Link to plot via batch_origins
        if S["batch"].get(bnum) and plot_id:
            req("POST", "/api/v1/batches/" + S["batch"][bnum] + "/origins",
                {"plot_id": plot_id, "plot_code": bnum, "origin_quantity_kg": "2000"},
                label=f"batch.origin.{bnum}", allow_codes=(404, 409, 422))

    # Serials for criollo premium (20 serials) — require status_id
    criollo_batch = S["batch"].get("COS-2026-002")
    status_id = None
    sc, sl = req("GET", "/api/v1/config/serial-statuses", label="serial-statuses.list")
    if isinstance(sl, dict):
        items = sl.get("items") or []
        if items: status_id = items[0].get("id")
    if not status_id:
        # Create one
        sc, d = req("POST", "/api/v1/config/serial-statuses",
                    {"name": "Disponible", "slug": "available", "color": "#10b981"},
                    label="serial-status.create", allow_codes=(409, 422))
        if ok(sc): status_id = d.get("id")
    if prod_cri and criollo_batch and status_id and len(S["serial"]) < 20:
        for i in range(1, 21):
            sn = f"CRI-2026-{i:04d}"
            body = {
                "serial_number": sn, "entity_id": prod_cri,
                "batch_id": criollo_batch, "status_id": status_id,
            }
            sc, d = req("POST", "/api/v1/serials", body,
                        label=f"serial.{sn}", allow_codes=(409, 422))
            if ok(sc):
                S["serial"].append({"sn": sn, "id": d["id"]})

    # Quality tests (3 per batch = 9 total) — types: humidity|defects|cadmium|ffa|iv|...
    for bnum, bid in list(S["batch"].items()):
        for test_type, val, unit, tmin, tmax in [
            ("humidity", "7.2", "pct", None, "8.0"),
            ("cadmium", "0.35", "mg_kg", None, "0.8"),
            ("defects", "2.5", "pct", None, "5.0"),
        ]:
            body = {
                "batch_id": bid, "test_type": test_type,
                "value": val, "unit": unit,
                "threshold_max": tmax, "threshold_min": tmin,
                "lab": "QC Lab Cartagena",
                "test_date": "2026-02-20",
                "notes": f"{test_type}={val}{unit}",
            }
            # NOTE: gateway has no route for /api/v1/quality-tests → use direct port 9003
            sc, d = req_direct("inventory", "POST", "/api/v1/quality-tests",
                               body, label=f"qt.{bnum}.{test_type}", allow_codes=(409, 422))
            if ok(sc): S["quality_test"].append({"batch": bnum, "type": test_type, "id": d.get("id")})

    req("GET", "/api/v1/batches", label="batches.list")
    req("GET", "/api/v1/batches/expiring", label="batches.expiring")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 12: Stock movements (adjust-in, transfer, adjust-out, reserve)
# ═══════════════════════════════════════════════════════════════════════
def phase_stock():
    print("\n=== PHASE 12: Stock movements ===")
    wh_ferm = S["warehouse"].get("FERM-POP")
    wh_sec = S["warehouse"].get("SEC-BUN")
    wh_exp = S["warehouse"].get("EXP-CTG")
    prod_trini = S["product"].get("trinitario")
    prod_cri = S["product"].get("criollo")
    prod_for = S["product"].get("forastero")
    prod_azucar = S["product"].get("azucar")
    prod_manteca = S["product"].get("manteca")
    batch_trini = S["batch"].get("COS-2026-001")
    batch_cri = S["batch"].get("COS-2026-002")
    batch_for = S["batch"].get("COS-2026-003")

    # 5 adjust-in (cosecha)
    ins = [
        (prod_trini, wh_ferm, batch_trini, "2000", "10000", "Cosecha trinitario Huila"),
        (prod_cri, wh_ferm, batch_cri, "1500", "14000", "Cosecha criollo Antioquia"),
        (prod_for, wh_ferm, batch_for, "2500", "8500", "Cosecha forastero Caquetá"),
        (prod_azucar, wh_exp, None, "500", "3500", "Compra azúcar"),
        (prod_manteca, wh_exp, None, "200", "45000", "Compra manteca cacao"),
    ]
    for pid, wid, bid, qty, cost, reason in ins:
        if not (pid and wid): continue
        body = {"product_id": pid, "warehouse_id": wid, "quantity": qty,
                "unit_cost": cost, "reason": reason}
        if bid: body["batch_id"] = bid
        sc, d = req("POST", "/api/v1/stock/adjust-in", body,
                    label=f"stock.in.{reason[:18]}", allow_codes=(409, 422))
        if ok(sc) and get_id(d, "id"):
            S["movement"].append({"type": "in", "id": d["id"]})

    # Transfers: ferm → secado
    for pid, qty in [(prod_trini, "1800"), (prod_cri, "1400"), (prod_for, "2300")]:
        if not (pid and wh_ferm and wh_sec): continue
        body = {"product_id": pid, "from_warehouse_id": wh_ferm,
                "to_warehouse_id": wh_sec, "quantity": qty,
                "reason": "Traslado fermentadero → secado"}
        sc, d = req("POST", "/api/v1/stock/transfer", body,
                    label=f"stock.transfer.{qty}", allow_codes=(409, 422))
        if ok(sc) and get_id(d, "id"):
            S["movement"].append({"type": "transfer", "id": d["id"]})

    # Transfers: secado → export
    for pid, qty in [(prod_trini, "1700"), (prod_cri, "1350"), (prod_for, "2200")]:
        if not (pid and wh_sec and wh_exp): continue
        body = {"product_id": pid, "from_warehouse_id": wh_sec,
                "to_warehouse_id": wh_exp, "quantity": qty,
                "reason": "Traslado secado → exportación"}
        req("POST", "/api/v1/stock/transfer", body,
            label=f"stock.trans2.{qty}", allow_codes=(409, 422))

    # Adjust-out: merma 3% fermentación
    for pid, qty in [(prod_trini, "60"), (prod_cri, "45"), (prod_for, "75")]:
        if not (pid and wh_ferm): continue
        body = {"product_id": pid, "warehouse_id": wh_ferm,
                "quantity": qty, "reason": "Merma fermentación 3%"}
        req("POST", "/api/v1/stock/adjust-out", body,
            label=f"stock.out.{qty}", allow_codes=(409, 422))

    # Waste
    if prod_for and wh_ferm:
        req("POST", "/api/v1/stock/waste",
            {"product_id": prod_for, "warehouse_id": wh_ferm, "quantity": "10",
             "reason": "Mohos detectados QC"},
            label="stock.waste", allow_codes=(409, 422))

    # Relocate (rack change)
    if prod_trini and wh_exp:
        req("POST", "/api/v1/stock/relocate",
            {"product_id": prod_trini, "warehouse_id": wh_exp,
             "quantity": "100", "notes": "Relocate a rack B-02"},
            label="stock.relocate", allow_codes=(409, 422, 400))

    # Receive (manual inbound)
    if prod_azucar and wh_exp:
        req("POST", "/api/v1/stock/receive",
            {"product_id": prod_azucar, "warehouse_id": wh_exp,
             "quantity": "100", "unit_cost": "3600"},
            label="stock.receive", allow_codes=(409, 422, 400))

    # Queries
    req("GET", "/api/v1/stock", label="stock.levels")
    req("GET", "/api/v1/stock/reservations", label="stock.reservations")
    if prod_trini:
        req("GET", f"/api/v1/stock/availability/{prod_trini}", label="stock.availability.trini")
        req("GET", f"/api/v1/analytics/kardex/{prod_trini}", label="analytics.kardex.trini")
    req("GET", "/api/v1/movements", label="movements.list")

    # Alerts
    req("POST", "/api/v1/alerts/scan", {}, label="alerts.scan")
    req("GET", "/api/v1/alerts", label="alerts.list")
    req("GET", "/api/v1/alerts/unread-count", label="alerts.unread")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 13: Purchase Orders + GRN
# ═══════════════════════════════════════════════════════════════════════
def phase_purchase_orders():
    print("\n=== PHASE 13: Purchase Orders ===")
    sup = S["supplier"].get("COOP-SVC")
    wh = S["warehouse"].get("FERM-POP")
    ot = S["order_type"].get("compra-nacional")
    prod_trini = S["product"].get("trinitario")
    prod_for = S["product"].get("forastero")
    if not (sup and wh and prod_trini): return

    for po_key, items in [
        ("PO-001", [(prod_trini, "1000", "10500"), (prod_for, "500", "8500")]),
        ("PO-002", [(prod_trini, "2000", "10000")]),
    ]:
        if S["po"].get(po_key): continue
        lines = [{"product_id": p, "qty_ordered": q, "unit_cost": c,
                  "uom": "primary", "notes": f"Compra {q}kg"} for p, q, c in items]
        body = {
            "supplier_id": sup, "warehouse_id": wh,
            "expected_date": "2026-03-15",
            "notes": f"PO E2E {po_key}",
            "lines": lines,
        }
        sc, d = req("POST", "/api/v1/purchase-orders", body,
                    label=f"po.create.{po_key}", allow_codes=(409, 422))
        if ok(sc): S["po"][po_key] = d["id"]

    # Workflow: PO-001 full cycle
    po1 = S["po"].get("PO-001")
    if po1:
        req("POST", f"/api/v1/purchase-orders/{po1}/send", {}, label="po.001.send", allow_codes=(400, 409))
        req("POST", f"/api/v1/purchase-orders/{po1}/confirm", {}, label="po.001.confirm", allow_codes=(400, 409))
        req("POST", f"/api/v1/purchase-orders/{po1}/receive",
            {"lines": [{"line_index": 0, "quantity_received": "950", "quantity_rejected": "50",
                        "rejection_reason": "Humedad >9% en 50kg"}]},
            label="po.001.partial_recv", allow_codes=(400, 409, 422))
        req("GET", f"/api/v1/purchase-orders/{po1}/approval-log", label="po.001.approvals")
    # PO-002 to cancel
    po2 = S["po"].get("PO-002")
    if po2:
        req("POST", f"/api/v1/purchase-orders/{po2}/send", {}, label="po.002.send", allow_codes=(400, 409))
        req("POST", f"/api/v1/purchase-orders/{po2}/cancel", {"reason": "Cliente retiró orden"},
            label="po.002.cancel", allow_codes=(400, 409))

    req("GET", "/api/v1/purchase-orders", label="po.list")
    req("GET", "/api/v1/purchase-orders/consolidation-candidates", label="po.consolidation")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 14: Sales Orders full cycle
# ═══════════════════════════════════════════════════════════════════════
def phase_sales_orders():
    print("\n=== PHASE 14: Sales Orders ===")
    cust_bc = S["customer"].get("bc")
    cust_bog = S["customer"].get("choc-bog")
    wh_exp = S["warehouse"].get("EXP-CTG")
    prod_trini = S["product"].get("trinitario")
    prod_cri = S["product"].get("criollo")
    prod_for = S["product"].get("forastero")
    iva19 = S["tax_rate"].get("iva19")
    ret4 = S["tax_rate"].get("ret4")
    ot_exp = S["order_type"].get("export-fob")

    if not (cust_bc and wh_exp and prod_trini): return

    for so_key, customer_id, currency, incoterm, dest, items in [
        ("SO-001", cust_bc, "USD", "FOB", "CH",
         [(prod_trini, 1500, 3.5), (prod_cri, 800, 4.2), (prod_for, 2000, 2.8)]),
        ("SO-002", cust_bog, "COP", "EXW", "CO",
         [(prod_trini, 100, 16500)]),
    ]:
        if S["so"].get(so_key) or not customer_id: continue
        lines = []
        for p, q, price in items:
            tax_ids = []
            if currency == "COP":
                if iva19: tax_ids.append(iva19)
                if ret4: tax_ids.append(ret4)
            lines.append({
                "product_id": p, "qty_ordered": q, "unit_price": price,
                "warehouse_id": wh_exp, "uom": "primary",
                "tax_rate_ids": tax_ids,
                "notes": f"Export {q}kg",
            })
        body = {
            "customer_id": customer_id, "warehouse_id": wh_exp,
            "currency": currency, "incoterm": incoterm,
            "origin_country": "CO", "destination_country": dest,
            "commodity_type": "cacao",
            "shipping_address": {"street": "Hardturmstrasse 181", "city": "Zürich", "country": "CH"}
                if currency == "USD" else {"street": "Calle 100", "city": "Bogotá", "country": "CO"},
            "notes": f"SO mega seeder {so_key}",
            "lines": lines,
        }
        sc, d = req("POST", "/api/v1/sales-orders", body,
                    label=f"so.create.{so_key}", allow_codes=(409, 422))
        if ok(sc): S["so"][so_key] = d["id"]

    # Full cycle SO-001
    so1 = S["so"].get("SO-001")
    if so1:
        req("GET", f"/api/v1/sales-orders/{so1}/stock-check", label="so.001.stockcheck")
        req("POST", f"/api/v1/sales-orders/{so1}/confirm", {}, label="so.001.confirm",
            allow_codes=(400, 409, 422))
        req("GET", f"/api/v1/sales-orders/{so1}/reservations", label="so.001.reservations")
        req("POST", f"/api/v1/sales-orders/{so1}/pick", {}, label="so.001.pick",
            allow_codes=(400, 409, 422))
        req("POST", f"/api/v1/sales-orders/{so1}/ship",
            {"tracking_number": "MAERSK-CO-CH-2026-001", "carrier": "Maersk Line",
             "shipped_at": "2026-04-10T08:00:00Z"},
            label="so.001.ship", allow_codes=(400, 409, 422))
        req("POST", f"/api/v1/sales-orders/{so1}/deliver", {}, label="so.001.deliver",
            allow_codes=(400, 409, 422))
        req("GET", f"/api/v1/sales-orders/{so1}/remission", label="so.001.remission")
        req("GET", f"/api/v1/sales-orders/{so1}/batches", label="so.001.batches")
        req("GET", f"/api/v1/sales-orders/{so1}/approval-log", label="so.001.approvals")

    # SO-002 will cancel
    so2 = S["so"].get("SO-002")
    if so2:
        req("POST", f"/api/v1/sales-orders/{so2}/confirm", {}, label="so.002.confirm",
            allow_codes=(400, 409))
        req("POST", f"/api/v1/sales-orders/{so2}/cancel",
            {"reason": "Cliente canceló por cambio precio"},
            label="so.002.cancel", allow_codes=(400, 409))

    req("GET", "/api/v1/sales-orders", label="so.list")
    req("GET", "/api/v1/sales-orders/summary", label="so.summary")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 15: Shipment + Trade documents
# ═══════════════════════════════════════════════════════════════════════
def phase_shipments():
    print("\n=== PHASE 15: Shipment docs + trade docs ===")
    so1 = S["so"].get("SO-001")
    cust_bc = S["customer"].get("bc")
    if not so1: return

    # Shipment (guía de remisión + packing list)
    for dtype, doc_num, meta in [
        ("packing_list", "PL-2026-001", {"total_packages": 100, "total_weight_kg": 4300}),
        ("bill_of_lading", "BL-MAERSK-2026-001",
         {"carrier": "Maersk Line", "vessel": "Maersk Alabama", "origin": "Cartagena (COCTG)",
          "destination": "Zürich via Hamburg (CHZRH)"}),
    ]:
        key = f"{so1}:{dtype}"
        if S["shipment_doc"].get(key): continue
        body = {
            "document_type": dtype, "document_number": doc_num,
            "order_id": so1, "order_type": "sales_order",
            "issue_date": "2026-04-10",
            "metadata": meta, "status": "issued",
        }
        sc, d = req("POST", "/api/v1/shipments", body,
                    label=f"shipdoc.{dtype}", allow_codes=(409, 422))
        if ok(sc): S["shipment_doc"][key] = d.get("id")

    # Trade docs (commercial invoice)
    key = f"{so1}:commercial_invoice"
    if not S["trade_doc"].get(key):
        body = {
            "document_type": "commercial_invoice",
            "document_number": "INV-EXP-2026-001",
            "order_id": so1, "customer_id": cust_bc,
            "issue_date": "2026-04-10", "currency": "USD",
            "total_amount": "15450.00", "incoterm": "FOB",
            "port_of_origin": "Cartagena (COCTG)",
            "port_of_destination": "Zürich (CHZRH)",
            "status": "approved",
        }
        sc, d = req("POST", "/api/v1/trade-documents", body,
                    label="tradedoc.invoice", allow_codes=(409, 422))
        if ok(sc):
            tid = d.get("id")
            S["trade_doc"][key] = tid
            if tid:
                req("POST", f"/api/v1/trade-documents/{tid}/approve", {},
                    label="tradedoc.approve", allow_codes=(400, 409))

    req("GET", "/api/v1/shipments", label="shipments.list")
    req("GET", "/api/v1/trade-documents", label="tradedocs.list")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 16: Cycle counts
# ═══════════════════════════════════════════════════════════════════════
def phase_cycle_counts():
    print("\n=== PHASE 16: Cycle counts ===")
    wh = S["warehouse"].get("EXP-CTG")
    if not wh: return
    if S["cycle_count"].get("CC-001"): return
    body = {
        "warehouse_id": wh, "scheduled_date": "2026-04-15",
        "notes": "Conteo físico trimestral Bodega Cartagena",
    }
    sc, d = req("POST", "/api/v1/cycle-counts", body, label="cc.create", allow_codes=(409, 422))
    if ok(sc):
        cc_id = d.get("id")
        S["cycle_count"]["CC-001"] = cc_id
        # Start
        req("POST", f"/api/v1/cycle-counts/{cc_id}/start", {},
            label="cc.start", allow_codes=(400, 409))
        # IRA
        req("GET", f"/api/v1/cycle-counts/{cc_id}/ira", label="cc.ira", allow_codes=(400, 404))
        # Cancel (to keep simple)
        req("POST", f"/api/v1/cycle-counts/{cc_id}/cancel",
            {"reason": "seed test"}, label="cc.cancel", allow_codes=(400, 409))
    req("GET", "/api/v1/cycle-counts", label="cc.list")
    req("GET", "/api/v1/cycle-counts/analytics/ira-trend", label="cc.ira-trend")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 17: Production (resources + recipes + runs)
# ═══════════════════════════════════════════════════════════════════════
def phase_production():
    print("\n=== PHASE 17: Production ===")
    # Resources
    res_defs = [
        ("tambor", "Tambor fermentación 500L", "equipment", "15000", "24", "85"),
        ("secadero", "Secadero solar", "equipment", "2000", "12", "90"),
        ("conche", "Conche refinadora", "equipment", "45000", "16", "80"),
    ]
    for key, name, rtype, cost_h, cap_d, eff in res_defs:
        if S["resource"].get(key): continue
        sc, d = req("POST", "/api/v1/production-resources",
                    {"name": name, "resource_type": rtype,
                     "cost_per_hour": cost_h, "capacity_hours_per_day": cap_d,
                     "efficiency_pct": eff},
                    label=f"res.{key}", allow_codes=(409,))
        if ok(sc): S["resource"][key] = d["id"]

    trini = S["product"].get("trinitario")
    nibs = S["product"].get("nibs")
    azucar = S["product"].get("azucar")
    manteca = S["product"].get("manteca")
    lecitina = S["product"].get("lecitina")
    choco = S["product"].get("chocolate-70")

    # Recipe 1: simple
    if not S["recipe"].get("nibs") and trini and nibs:
        sc, d = req("POST", "/api/v1/recipes", {
            "name": "Receta Nibs ex-Trinitario",
            "output_entity_id": nibs, "output_quantity": "1",
            "description": "1 kg nibs = 1.2 kg trinitario (yield 83%)",
            "bom_type": "production", "standard_cost": "18000",
            "components": [{"component_entity_id": trini, "quantity_required": "1.2",
                            "issue_method": "manual"}],
        }, label="recipe.nibs", allow_codes=(409,))
        if ok(sc): S["recipe"]["nibs"] = d["id"]

    # Recipe 2: multi-component
    if not S["recipe"].get("chocolate") and nibs and choco:
        comps = []
        if nibs: comps.append({"component_entity_id": nibs, "quantity_required": "0.60", "issue_method": "manual"})
        if azucar: comps.append({"component_entity_id": azucar, "quantity_required": "0.30", "issue_method": "manual"})
        if manteca: comps.append({"component_entity_id": manteca, "quantity_required": "0.08", "issue_method": "manual"})
        if lecitina: comps.append({"component_entity_id": lecitina, "quantity_required": "0.02", "issue_method": "manual"})
        if len(comps) >= 2:
            sc, d = req("POST", "/api/v1/recipes", {
                "name": "Receta Chocolate 70%",
                "output_entity_id": choco, "output_quantity": "1",
                "description": "Chocolate 70% = 60% nibs + 30% azúcar + 8% manteca + 2% lecitina",
                "bom_type": "production", "standard_cost": "35000",
                "components": comps,
            }, label="recipe.chocolate", allow_codes=(409,))
            if ok(sc): S["recipe"]["chocolate"] = d["id"]

    wh_ferm = S["warehouse"].get("FERM-POP")
    wh_exp = S["warehouse"].get("EXP-CTG")

    # Run 1: 800 kg nibs
    recipe_nibs = S["recipe"].get("nibs")
    if recipe_nibs and wh_ferm and not S["run"].get("run1"):
        sc, d = req("POST", "/api/v1/production-runs",
                    {"recipe_id": recipe_nibs, "warehouse_id": wh_ferm,
                     "output_warehouse_id": wh_exp or wh_ferm,
                     "multiplier": "800",
                     "notes": "Corrida nibs 800 kg", "priority": 70},
                    label="run.nibs.create", allow_codes=(409, 422))
        if ok(sc):
            run_id = d["id"]
            S["run"]["run1"] = run_id
            req("POST", f"/api/v1/production-runs/{run_id}/release", {}, label="run.nibs.release",
                allow_codes=(400, 409))
            sc2, em = req("POST", f"/api/v1/production-runs/{run_id}/emissions",
                          {"notes": "Consumo trinitario"}, label="run.nibs.emission",
                          allow_codes=(400, 409, 422))
            if ok(sc2): S["emission"].append({"run": "run1", "id": em.get("id")})
            sc3, rc = req("POST", f"/api/v1/production-runs/{run_id}/receipts",
                          {"notes": "Recepción 800 kg nibs"}, label="run.nibs.receipt",
                          allow_codes=(400, 409, 422))
            if ok(sc3): S["receipt"].append({"run": "run1", "id": rc.get("id")})
            req("POST", f"/api/v1/production-runs/{run_id}/close", {}, label="run.nibs.close",
                allow_codes=(400, 409))
            req("GET", f"/api/v1/production-runs/{run_id}/emissions", label="run.nibs.emis.list")
            req("GET", f"/api/v1/production-runs/{run_id}/receipts", label="run.nibs.rec.list")

    # Run 2: 200 kg chocolate (multi-component)
    recipe_choco = S["recipe"].get("chocolate")
    if recipe_choco and wh_exp and not S["run"].get("run2"):
        sc, d = req("POST", "/api/v1/production-runs",
                    {"recipe_id": recipe_choco, "warehouse_id": wh_exp,
                     "output_warehouse_id": wh_exp,
                     "multiplier": "200",
                     "notes": "Corrida chocolate 200 kg", "priority": 60},
                    label="run.choco.create", allow_codes=(409, 422))
        if ok(sc):
            run_id = d["id"]
            S["run"]["run2"] = run_id
            req("POST", f"/api/v1/production-runs/{run_id}/release", {}, label="run.choco.release",
                allow_codes=(400, 409))
            req("POST", f"/api/v1/production-runs/{run_id}/emissions", {}, label="run.choco.emission",
                allow_codes=(400, 409, 422))
            req("POST", f"/api/v1/production-runs/{run_id}/receipts", {}, label="run.choco.receipt",
                allow_codes=(400, 409, 422))
            req("POST", f"/api/v1/production-runs/{run_id}/close", {}, label="run.choco.close",
                allow_codes=(400, 409))

    # MRP
    if trini:
        req("POST", "/api/v1/production-runs/mrp/explode",
            {"items": [{"product_id": trini, "quantity": "1000"}]},
            label="mrp.explode", allow_codes=(400, 404, 422))

    req("GET", "/api/v1/production-runs", label="runs.list")
    req("GET", "/api/v1/recipes", label="recipes.list")
    req("GET", "/api/v1/production-resources", label="resources.list")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 18: Logistics/Trace — custodian types, orgs, wallets, workflow
# ═══════════════════════════════════════════════════════════════════════
def phase_trace_setup():
    print("\n=== PHASE 18a: Custodian types ===")
    ctypes = [("Farm", "farm", "sprout"), ("Warehouse", "warehouse", "warehouse"),
              ("Truck", "truck", "truck"), ("Port", "port", "anchor"),
              ("Customs", "customs", "shield")]
    for name, slug, icon in ctypes:
        if S["custodian_type"].get(slug): continue
        sc, d = req("POST", "/api/v1/taxonomy/custodian-types",
                    {"name": name, "slug": slug, "color": "#6366f1", "icon": icon},
                    label=f"ct.{slug}", allow_codes=(409,))
        if ok(sc): S["custodian_type"][slug] = d["id"]

    print("\n=== PHASE 18b: Organizations (5: 3 cooperativas + naviera + aduana) ===")
    farm = S["custodian_type"].get("farm")
    port = S["custodian_type"].get("port")
    customs = S["custodian_type"].get("customs")
    wh = S["custodian_type"].get("warehouse")

    orgs = [
        ("Coop San Vicente del Caguán", farm, ["caqueta", "cacao", "cooperativa"]),
        ("Asocafé Huila", farm, ["huila", "cacao", "cooperativa"]),
        ("Cacaoteros Apartadó", farm, ["antioquia", "cacao", "cooperativa"]),
        ("Naviera Maersk Cartagena", port, ["naviera", "maersk"]),
        ("Agencia Aduanera Cartagena", customs, ["aduana", "ca"]),
        ("Cacao Origen Colombia S.A.S.", wh, ["exporter", "own"]),
    ]
    for name, ctype, tags in orgs:
        if S["organization"].get(name) or not ctype: continue
        sc, d = req("POST", "/api/v1/taxonomy/organizations",
                    {"name": name, "custodian_type_id": ctype, "description": name, "tags": tags},
                    label=f"org.{name[:15]}", allow_codes=(409,))
        if ok(sc): S["organization"][name] = d["id"]

    print("\n=== PHASE 18c: Wallets (generate 5 + register 1) ===")
    for org_name, org_id in list(S["organization"].items()):
        if S["wallet"].get(org_name): continue
        sc, d = req("POST", "/api/v1/registry/wallets/generate",
                    {"tags": ["cacao"], "name": f"W-{org_name[:20]}", "organization_id": org_id},
                    label=f"wallet.gen.{org_name[:15]}", allow_codes=(409,))
        if ok(sc):
            S["wallet"][org_name] = {"id": d["id"], "pubkey": d["wallet_pubkey"]}

    # Register external wallet (manual pubkey)
    if not S["wallet"].get("_external"):
        sc, d = req("POST", "/api/v1/registry/wallets",
                    {"wallet_pubkey": "ExT3RnaLWa11et1111111111111111111111111111",
                     "name": "W-External-Test", "tags": ["external"]},
                    label="wallet.register.ext", allow_codes=(400, 409, 422))
        if ok(sc): S["wallet"]["_external"] = {"id": d.get("id")}

    print("\n=== PHASE 18d: Workflow (states + event types) ===")
    sc, states = req("GET", "/api/v1/config/workflow/states", label="wf.states.list")
    if isinstance(states, list) and len(states) > 0:
        for st in states:
            S["wf_state"][st.get("slug") or st.get("name")] = st.get("id")
    else:
        req("POST", "/api/v1/config/workflow/seed/supply_chain", {}, label="wf.seed.supply_chain",
            allow_codes=(400, 409))
        sc, states = req("GET", "/api/v1/config/workflow/states", label="wf.states.relist")
        if isinstance(states, list):
            for st in states:
                S["wf_state"][st.get("slug") or st.get("name")] = st.get("id")

    req("GET", "/api/v1/config/workflow/transitions", label="wf.transitions")
    sc, et_list = req("GET", "/api/v1/config/workflow/event-types", label="wf.event-types")
    if isinstance(et_list, list):
        for et in et_list:
            S["wf_event_type"][et.get("slug") or et.get("name")] = et.get("id")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 19: Assets + 9 custody events per asset
# ═══════════════════════════════════════════════════════════════════════
def phase_assets_and_events():
    print("\n=== PHASE 19a: Assets (mint 3) ===")
    org_wallets = list(S["wallet"].items())
    if len(org_wallets) < 2: return
    wallets_coops = [(k, v) for k, v in org_wallets if "Coop" in k or "Asocafé" in k or "Cacaoteros" in k][:3]
    wallet_exporter = None
    for k, v in org_wallets:
        if "Cacao Origen" in k: wallet_exporter = v
    wallet_naviera = None
    for k, v in org_wallets:
        if "Naviera" in k: wallet_naviera = v

    batch_ids = list(S["batch"].values())

    lot_plans = [
        ("Lote Export Criollo #001", "cacao-criollo", 12000, "criollo",
         S["batch"].get("COS-2026-002"), S["plot"].get("PLOT-ANT-001")),
        ("Lote Export Trinitario #002", "cacao-trinitario", 8000, "trinitario",
         S["batch"].get("COS-2026-001"), S["plot"].get("PLOT-HUI-001")),
        ("Lote Export Forastero #003", "cacao-forastero", 15000, "forastero",
         S["batch"].get("COS-2026-003"), S["plot"].get("PLOT-CAQ-001")),
    ]
    for i, (name, ptype, qty, variety, batch_id, plot_id) in enumerate(lot_plans):
        if S["asset"].get(name): continue
        if i >= len(wallets_coops): continue
        org_name, wallet = wallets_coops[i]
        body = {
            "product_type": ptype,
            "metadata": {
                "name": name, "description": name,
                "quantity_kg": qty, "weight_kg": qty, "commodity_type": "cacao",
                "variedad": variety, "country": "CO", "country_of_production": "CO",
                "origin_plot_id": str(plot_id) if plot_id else None,
                "batch_id": str(batch_id) if batch_id else None,
                "destination": "CH", "buyer": "Barry Callebaut AG",
            },
            "initial_custodian_wallet": wallet["pubkey"],
            "plot_id": str(plot_id) if plot_id else None,
            "batch_id": str(batch_id) if batch_id else None,
        }
        sc, d = req("POST", "/api/v1/assets/mint", body, label=f"asset.mint.{i+1}",
                    allow_codes=(400, 409, 422))
        if ok(sc):
            asset = d.get("asset", {}) if isinstance(d, dict) else {}
            aid = asset.get("id") or (d.get("id") if isinstance(d, dict) else None)
            if aid: S["asset"][name] = aid

    print("\n=== PHASE 19b: Custody events (9 per asset = 27 total) ===")
    # Event chain:
    # 1. loaded (IN_CUSTODY → LOADED) at cooperativa/farm
    # 2. qc (LOADED → QC_PASSED) at farm
    # 3. handoff → warehouse ferm (to exporter)
    # 4. arrived in fermentadero Popayán
    # 5. loaded (transfer-ready)
    # 6. handoff → secadero
    # 7. arrived in Cartagena
    # 8. handoff → naviera
    # 9. arrived Zurich
    locations = [
        {"lat": 2.043, "lng": -74.763, "description": "Finca origen Caquetá"},
        {"lat": 2.043, "lng": -74.763, "description": "QC field Caquetá"},
        {"lat": 2.5, "lng": -76.6, "description": "Handoff → Popayán"},
        {"lat": 2.5, "lng": -76.6, "description": "Fermentadero Popayán"},
        {"lat": 2.5, "lng": -76.6, "description": "Loaded → secadero"},
        {"lat": 3.88, "lng": -77.03, "description": "Handoff → Buenaventura"},
        {"lat": 10.32, "lng": -75.5, "description": "Arrived Cartagena"},
        {"lat": 10.32, "lng": -75.5, "description": "Handoff → Naviera"},
        {"lat": 47.37, "lng": 8.55, "description": "Arrived Zürich (Barry Callebaut)"},
    ]
    for lot_idx, (name, _, _, variety, batch_id, _) in enumerate(lot_plans):
        asset_id = S["asset"].get(name)
        if not asset_id: continue
        coop_wallet = wallets_coops[lot_idx][1]["pubkey"] if lot_idx < len(wallets_coops) else None
        exp_wallet = wallet_exporter["pubkey"] if wallet_exporter else None
        nav_wallet = wallet_naviera["pubkey"] if wallet_naviera else None

        def ev(ep, body, label):
            sc, d = req("POST", f"/api/v1/assets/{asset_id}/events/{ep}",
                        body, label=label, allow_codes=(400, 409, 422))
            if ok(sc) and isinstance(d, dict):
                S["event"].append({"asset": name, "type": ep, "id": d.get("id")})

        base_data = {"batch_id": str(batch_id) if batch_id else None,
                     "commodity": "cacao", "variety": variety}
        # 1. loaded at farm
        ev("loaded", {"location": locations[0], "data": {**base_data, "step": "HARVEST_LOADED"}},
           f"evt.{lot_idx}.01.loaded_farm")
        # 2. qc
        ev("qc", {"result": "pass", "notes": "Muestra cumple moisture<8%, fermentation>=5d",
                  "data": {**base_data, "moisture_pct": 7.3, "fermentation_days": 6},
                  "location": locations[1]},
           f"evt.{lot_idx}.02.qc")
        # 3. handoff → exp
        if exp_wallet:
            ev("handoff",
               {"to_wallet": exp_wallet, "location": locations[2],
                "data": {**base_data, "step": "HANDOFF_COLLECTION"}},
               f"evt.{lot_idx}.03.handoff_exp")
            # 4. arrived
            ev("arrived", {"location": locations[3], "data": {**base_data, "step": "FERM_ARRIVED"}},
               f"evt.{lot_idx}.04.arrived_ferm")
            # 5. loaded again (ferm → drying)
            ev("loaded", {"location": locations[4], "data": {**base_data, "step": "DRYING_LOADED"}},
               f"evt.{lot_idx}.05.loaded_drying")
            # 6. handoff (same exp → drying site — re-use exp wallet target to simulate)
            ev("arrived", {"location": locations[5], "data": {**base_data, "step": "DRYING_ARRIVED"}},
               f"evt.{lot_idx}.06.arrived_drying")
            # 7. arrived Cartagena
            ev("arrived", {"location": locations[6], "data": {**base_data, "step": "CTG_ARRIVED"}},
               f"evt.{lot_idx}.07.arrived_ctg")
        # 8. handoff → naviera
        if nav_wallet:
            ev("handoff",
               {"to_wallet": nav_wallet, "location": locations[7],
                "data": {**base_data, "step": "HANDOFF_NAVIERA"}},
               f"evt.{lot_idx}.08.handoff_nav")
            # 9. arrived Zurich
            ev("arrived", {"location": locations[8], "data": {**base_data, "step": "ZURICH_ARRIVED"}},
               f"evt.{lot_idx}.09.arrived_zurich")

        # List events
        req("GET", f"/api/v1/assets/{asset_id}/events", label=f"asset.events.list.{lot_idx}")

    req("GET", "/api/v1/assets", label="assets.list")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 20: Anchoring + Solana + analytics
# ═══════════════════════════════════════════════════════════════════════
def phase_trace_extras():
    print("\n=== PHASE 20: Trace extras (anchoring, solana, analytics) ===")
    # Anchoring: hash a test payload
    import hashlib
    payload_hash = hashlib.sha256(b"cacao-seed-mega-2026-04-15").hexdigest()
    first_asset = next(iter(S["asset"].values()), None) or "00000000-0000-0000-0000-000000000001"
    sc, d = req("POST", "/api/v1/anchoring/hash",
                {"tenant_id": "00000000-0000-0000-0000-000000000001",
                 "source_service": "inventory-service",
                 "source_entity_type": "audit_snapshot",
                 "source_entity_id": str(first_asset),
                 "payload_hash": payload_hash,
                 "metadata": {"note": "seed_mega snapshot"}},
                label="anchor.hash", allow_codes=(400, 409, 422))
    if ok(sc): S["anchor"]["test"] = d.get("id") or payload_hash
    req("GET", f"/api/v1/anchoring/{payload_hash}/status", label="anchor.status",
        allow_codes=(404,))

    # Solana queries
    req("GET", "/api/v1/solana/network", label="solana.network", allow_codes=(404,))

    # Analytics
    req("GET", "/api/v1/analytics/transport", label="trace.analytics.transport",
        allow_codes=(400, 404))

    # Shipment anchor rules
    req("GET", "/api/v1/anchor-rules", label="anchor.rules", allow_codes=(404,))
    req("POST", "/api/v1/anchor-rules/seed-defaults", {}, label="anchor.rules.seed",
        allow_codes=(400, 404, 409))


# ═══════════════════════════════════════════════════════════════════════
# PHASE 21: Compliance records + risk + supply chain + certificates
# ═══════════════════════════════════════════════════════════════════════
def phase_compliance_records():
    print("\n=== PHASE 21: Compliance records + risks + nodes + certs ===")
    asset_ids = list(S["asset"].values())
    plot_ids = list(S["plot"].values())
    lot_names = list(S["asset"].keys())
    so1 = S["so"].get("SO-001")

    for i, aid in enumerate(asset_ids):
        if S["record"].get(lot_names[i]): continue
        body = {
            "asset_id": aid,
            "framework_slug": "eudr",
            "hs_code": "180100", "commodity_type": "cacao",
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
            "linked_sales_order_id": str(so1) if so1 else None,
        }
        sc, d = req("POST", "/api/v1/compliance/records/", body,
                    label=f"rec.{i+1}", allow_codes=(409, 422))
        if ok(sc): S["record"][lot_names[i]] = d["id"]

    rec_ids = list(S["record"].values())
    for i, rid in enumerate(rec_ids):
        if i < len(plot_ids):
            req("POST", f"/api/v1/compliance/records/{rid}/plots",
                {"plot_id": plot_ids[i], "percentage_from_plot": "100"},
                label=f"rec.plotlink.{i+1}", allow_codes=(409, 422))
        # Validate to transition status based on completeness
        req("GET", f"/api/v1/compliance/records/{rid}/validate",
            label=f"rec.validate.{i+1}")

    # Risks
    for i, rid in enumerate(rec_ids):
        if S["risk"].get(f"risk{i+1}"): continue
        body = {
            "record_id": rid,
            "country_risk_level": "low",
            "country_risk_notes": "Colombia clasificado bajo riesgo por EU benchmarking 2025",
            "country_benchmarking_source": "EU Commission benchmarking 2025",
            "supply_chain_risk_level": "medium",
            "supply_chain_notes": "Cooperativas con trazabilidad plot-level",
            "supplier_verification_status": "verified",
            "traceability_confidence": "high",
            "regional_risk_level": "low",
            "deforestation_prevalence": "low",
            "indigenous_rights_risk": False,
            "corruption_index_note": "CPI 2024 score 39/100",
            "mitigation_measures": [
                {"type": "satellite_monitoring", "description": "Monitoreo satelital trimestral PRODES"},
                {"type": "third_party_audit", "description": "Auditoría Rainforest Alliance anual"},
                {"type": "plot_geolocation", "description": "100% plots con GPS handheld"},
            ],
            "additional_info_requested": False,
            "independent_audit_required": False,
            "overall_risk_level": "low",
            "conclusion": "negligible_risk",
            "conclusion_notes": "Riesgo EUDR Art. 10 despreciable.",
        }
        sc, d = req("POST", "/api/v1/compliance/risk-assessments/", body,
                    label=f"risk.{i+1}", allow_codes=(409, 422))
        if ok(sc):
            S["risk"][f"risk{i+1}"] = d["id"]
            req("POST", f"/api/v1/compliance/risk-assessments/{d['id']}/complete", {},
                label=f"risk.complete.{i+1}", allow_codes=(400, 409))

    # Supply chain nodes (5 per record)
    for i, rid in enumerate(rec_ids):
        sup_name = list(S["supplier"].keys())[i] if i < len(S["supplier"]) else "Unknown"
        sup_id = list(S["supplier"].values())[i] if i < len(S["supplier"]) else None
        nodes = [
            {"sequence_order": 1, "role": "producer", "actor_name": sup_name,
             "actor_address": "Colombia", "actor_country": "CO",
             "actor_tax_id": "900.111.222-3", "handoff_date": "2026-02-15",
             "verification_status": "verified", "linked_entity_id": str(sup_id) if sup_id else None},
            {"sequence_order": 2, "role": "cooperative", "actor_name": sup_name,
             "actor_address": "Colombia", "actor_country": "CO",
             "handoff_date": "2026-02-20", "verification_status": "verified"},
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
            sc, d = req("POST", f"/api/v1/compliance/records/{rid}/supply-chain/",
                        n, label=f"node.{i+1}.{n['sequence_order']}", allow_codes=(409, 422))
            if ok(sc):
                S["node"].append({"record": rid, "seq": n["sequence_order"], "id": d.get("id")})

    # Certificates (generate)
    for i, rid in enumerate(rec_ids):
        ckey = f"cert{i+1}"
        if S["cert"].get(ckey): continue
        sc, d = req("POST", f"/api/v1/compliance/records/{rid}/certificate", {},
                    label=f"cert.{i+1}", allow_codes=(400, 409, 422))
        if ok(sc):
            cid = d.get("id") if isinstance(d, dict) else None
            S["cert"][ckey] = cid
            if cid:
                req("GET", f"/api/v1/compliance/certificates/{cid}/download",
                    label=f"cert.download.{i+1}", allow_codes=(404,))
        # Regenerate first cert
        if i == 0 and S["cert"].get(ckey):
            req("POST", f"/api/v1/compliance/certificates/{S['cert'][ckey]}/regenerate", {},
                label="cert.regen", allow_codes=(400, 404, 422))

    # DDS submission (record 0)
    if rec_ids:
        rid = rec_ids[0]
        req("POST", f"/api/v1/compliance/records/{rid}/submit-traces",
            {"reference_number": "DDS-CO-2026-0002", "simulate": True},
            label="dds.submit", allow_codes=(400, 409, 422))
        req("PATCH", f"/api/v1/compliance/records/{rid}/declaration",
            {"declaration_reference": "DDS-CO-2026-0002",
             "declaration_status": "submitted",
             "declaration_submission_date": "2026-04-15"},
            label="dds.patch", allow_codes=(400, 422))
        req("POST", f"/api/v1/compliance/records/{rid}/export-dds", {},
            label="dds.export", allow_codes=(400, 404, 422))

    # Certification (Rainforest) — link scheme to a plot if endpoint exists
    req("GET", "/api/v1/compliance/certifications/", label="certifs.list")

    # List
    req("GET", "/api/v1/compliance/records/", label="rec.list")
    req("GET", "/api/v1/compliance/certificates/", label="certs.list")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 22: Reports (CSV) + analytics
# ═══════════════════════════════════════════════════════════════════════
def phase_reports():
    print("\n=== PHASE 22: Reports + analytics ===")
    for r in ("products", "stock", "suppliers", "movements"):
        req("GET", f"/api/v1/reports/{r}", label=f"report.{r}", allow_codes=(400, 404))
    # With date range
    req("GET", "/api/v1/reports/movements",
        params={"date_from": "2026-01-01", "date_to": "2026-04-15"},
        label="report.movements.range", allow_codes=(400, 404))

    for a in ("overview", "occupation", "abc", "eoq", "stock-policy",
              "storage-valuation", "committed-stock", "inventory-kpis"):
        req("GET", f"/api/v1/analytics/{a}", label=f"analytics.{a}", allow_codes=(400, 404))

    req("GET", "/api/v1/audit", label="audit.list")

    # Portal
    req("GET", "/api/v1/portal/config", label="portal.config", allow_codes=(401, 403, 404))
    req("GET", "/api/v1/portal/products", label="portal.products", allow_codes=(401, 403, 404))


# ═══════════════════════════════════════════════════════════════════════
# PHASE 23: Smoke-test reads (verify)
# ═══════════════════════════════════════════════════════════════════════
def phase_verify():
    print("\n=== PHASE 23: Smoke verify ===")
    checks = [
        ("/api/v1/products", "products"),
        ("/api/v1/warehouses", "warehouses"),
        ("/api/v1/suppliers", "suppliers"),
        ("/api/v1/customers", "customers"),
        ("/api/v1/batches", "batches"),
        ("/api/v1/stock", "stock.levels"),
        ("/api/v1/movements", "movements"),
        ("/api/v1/purchase-orders", "pos"),
        ("/api/v1/sales-orders", "sos"),
        ("/api/v1/production-runs", "runs"),
        ("/api/v1/recipes", "recipes"),
        ("/api/v1/cycle-counts", "cycle-counts"),
        ("/api/v1/assets", "assets"),
        ("/api/v1/taxonomy/organizations", "trace.orgs"),
        ("/api/v1/registry/wallets", "wallets"),
        ("/api/v1/compliance/records/", "compliance.records"),
        ("/api/v1/compliance/plots/", "compliance.plots"),
        ("/api/v1/compliance/certificates/", "compliance.certs"),
    ]
    summary = {}
    for path, lbl in checks:
        sc, d = req("GET", path, label=f"verify.{lbl}")
        count = 0
        if isinstance(d, list): count = len(d)
        elif isinstance(d, dict):
            items = d.get("items") or d.get("results") or []
            count = len(items) if isinstance(items, list) else (d.get("total", 0))
        summary[lbl] = {"status": sc, "count": count}
    print("\n  Verify summary:")
    for k, v in summary.items():
        print(f"    {k:30s} status={v['status']} count={v['count']}")
    return summary


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════
def load_prev():
    if STATE_PATH.exists():
        try:
            prev = json.loads(STATE_PATH.read_text())
            for k, v in prev.items():
                if k in S:
                    # only fill if empty
                    if not S[k]:
                        S[k] = v
            print(f"  loaded previous state ({sum(len(v) if hasattr(v, '__len__') else 0 for v in prev.values())} items)")
        except Exception as exc:
            print(f"  load prev failed: {exc}")


PHASES = [
    ("uom", phase_uom),
    ("taxes", phase_taxes),
    ("categories", phase_categories),
    ("config", phase_config),
    ("warehouses", phase_warehouses),
    ("variants", phase_variants),
    ("partners", phase_partners),
    ("products", phase_products),
    ("customer_prices", phase_customer_prices),
    ("compliance_setup", phase_compliance_setup),
    ("batches", phase_batches),
    ("stock", phase_stock),
    ("purchase_orders", phase_purchase_orders),
    ("sales_orders", phase_sales_orders),
    ("shipments", phase_shipments),
    ("cycle_counts", phase_cycle_counts),
    ("production", phase_production),
    ("trace_setup", phase_trace_setup),
    ("assets_events", phase_assets_and_events),
    ("trace_extras", phase_trace_extras),
    ("compliance_records", phase_compliance_records),
    ("reports", phase_reports),
    ("verify", phase_verify),
]


def main():
    tok = _load_token() or _login()
    _set_headers(tok)
    LOG_PATH.write_text("")
    load_prev()
    start = time.time()
    verify_summary = None
    for name, fn in PHASES:
        try:
            result = fn()
            if name == "verify":
                verify_summary = result
            save_state()
        except Exception as exc:
            print(f"  [FATAL phase={name}] {exc}")
            traceback.print_exc()
            S["bugs"].append({"phase": name, "exc": str(exc), "tb": traceback.format_exc()})
            save_state()
    elapsed = time.time() - start
    print(f"\n=== DONE in {elapsed:.1f}s ===")
    print(f"  bugs: {len(S['bugs'])}")
    print(f"  log:   {LOG_PATH}")
    print(f"  state: {STATE_PATH}")
    total_entities = 0
    for k, v in S.items():
        if k == "bugs": continue
        if isinstance(v, dict): total_entities += len(v)
        elif isinstance(v, list): total_entities += len(v)
    print(f"  total entity refs: {total_entities}")


if __name__ == "__main__":
    main()
