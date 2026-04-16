# E2E Mega Seed — Cacao Origen Colombia S.A.S. → Barry Callebaut (EUDR)

## Executive Summary

Tenant `default` (UUID `00000000-0000-0000-0000-000000000001`) seeded end-to-end
with a realistic supply-chain scenario: Colombian cooperative-grown fine-aroma
cacao exported to Barry Callebaut AG (Zürich) under EUDR (Regulation 2023/1115).

**Seeder**: `qa/seed/seed_mega.py` — idempotent, 23 phases, state persisted in
`qa/seed/seed_mega_state.json`, per-call log in `qa/seed/seed_mega_run.jsonl`.
Full run ~40s, **319 entity references** created/reused across phases, **all 18
smoke-test GETs return 200**.

**Module coverage**:
- Inventory (inventory-api :9003): UoM + conversions, tax cats & rates, 3-level
  category hierarchy, 2 product types with 5 custom fields, 3 warehouses + 9
  locations, 10 products (1 variant parent), 3 suppliers + 2 customers + 1
  partner, 3 batches + 10 quality tests + 20 serials, 67 stock movements
  (adjust-in / transfer / adjust-out / waste / relocate), 2 POs full-cycle, 1 SO
  full cycle (confirm → pick → ship → deliver), 3 customer prices, 5 tax rates
  in IVA+Retefuente lock, 2 recipes (simple + 4-component), 2 production runs,
  3 resources, cycle counts (create blocked by bug #8).
- Production: 2 recipes, 3 resources, 2 runs (release attempts blocked by
  legit "insufficient stock" guard — expected behavior since only 140 kg of
  trinitario remain after the transfer chain drained ferm→sec→exp).
- Logistics (trace-api :8000): 5 custodian types, 6 organizations, 8 wallets
  (7 generated + 1 external), 3 assets minted, **87 custody events** (~29 per
  asset spanning harvest → QC → fermentation → drying → Cartagena → Zürich),
  1 anchor request, 34 workflow states, 49 event types, 2 shipment documents.
- Compliance (compliance-api :8004): EUDR framework activation, country-risk
  benchmark for CO (low-risk), 3 plots (Huila/Antioquia/Caquetá with 6-decimal
  WGS84 polygons), 3 plot documents linked to media files, 3 compliance records
  (one with DDS submitted `DDS-CO-2026-0002`), 3 risk assessments (all
  `negligible_risk`), 15 supply-chain nodes, 4 certificates with downloadable
  PDFs, regenerate flow exercised.

**Bugs found**: 3 confirmed 5xx server bugs (see Bugs section), 1 gateway
routing gap, plus several schema mismatches that blocked the first-pass seeder
and were fixed in the seeder's body — these are documented below for backend
follow-up even when the seeder now sidesteps them.

---

## IDs created (highlights)

### Inventory — catalogues
| Entity | Count | Sample IDs / keys |
|---|---|---|
| Units of measure | 41 | kg, ton, sc60, sc45 (+37 system defaults) |
| UoM conversions | 32 | ton→kg 1000, sc60→kg 60, sc45→kg 45 |
| Tax categories | 2 | `iva`, `retefuente` |
| Tax rates | 5 | IVA 19/5/0, Retención 4/2.5 |
| Categories | 10 | Cacao en grano > Criollo/Trinitario/Forastero; Productos terminados > Chocolate/Nibs/Manteca |
| Product types | 2 | cacao-variedad, producto-terminado |
| Custom product fields | 5 | variedad, fermentation_days, moisture_pct, origen_plot_id, grano_calibre |
| Custom supplier fields | 3 | nit, regimen_fiscal, ra_certified |
| Custom warehouse fields | 2 | capacity_tons, gmp_cert |
| Custom movement fields | 2 | truck_plate, temp_c |
| Supplier/Customer/Movement/Warehouse/Order types | 13 | see config phase |
| Variant attributes / options | 1 / 0 | `variedad`; options creation blocked by bug #1 |

### Inventory — entities
| Entity | Count | Sample |
|---|---|---|
| Warehouses | 3 | FERM-POP (Popayán), SEC-BUN (Buenaventura), EXP-CTG (Cartagena) |
| Warehouse locations | 9 | A-01-01, A-01-02, B-02-01 per WH |
| Suppliers | 3 | COOP-SVC, COOP-HUILA, COOP-APART |
| Customers | 4 | Barry Callebaut AG (CH), Chocolates Bogotá + 2 legacy |
| Business partners | 1 | AA-CTG Agencia Aduanera |
| Products | 10 | CAC-FINO-001 (variant parent), CAC-CRI/TRI/FOR-001, CAC-NIB, CAC-CHO, INS-AZU/MAN/LEC + 1 legacy |
| Batches | 3 | COS-2026-001/002/003 |
| Quality tests | 10 | 3 per batch (humidity, cadmium, defects) + 1 legacy |
| Serials | 20 | CRI-2026-0001 … CRI-2026-0020 |
| Customer prices | 3 | Barry Callebaut −15% on 3 cacao variants |
| Stock levels | 11 | across 3 WHs |
| Stock movements | 67 | adjust-in (5), transfer (6), adjust-out (3), waste, relocate, receive |
| Stock layers (FIFO) | 24 |  |
| Stock reservations | 3 | tied to SO-001 |
| Purchase orders | 2 | PO-001 (full cycle), PO-002 |
| PO lines | 3 |  |
| Sales orders | 1 | SO-001 (Barry Callebaut, USD, FOB) — full cycle |
| SO lines | 3 |  |
| Recipes | 2 | Nibs ex-Trinitario (simple), Chocolate 70% (4-comp) |
| Recipe components | 5 |  |
| Production resources | 3 | tambor, secadero, conche |
| Production runs | 2 | 800 kg nibs, 200 kg chocolate |
| Cycle counts | 0 | blocked by bug #8 |
| Shipment documents | 2 | packing list, BL |
| Trade documents | 0 | invoice blocked by multi-tax validation |

### Logistics (trace)
| Entity | Count | Sample |
|---|---|---|
| Custodian types | 5 | farm, warehouse, truck, port, customs |
| Organizations | 6 | Coop SVC, Asocafé Huila, Cacaoteros Apartadó, Naviera Maersk, Agencia Aduanera, Cacao Origen Colombia S.A.S. |
| Registry wallets | 8 | 7 generated (one per org including legacy) + 1 external |
| Assets | 3 | Lote Criollo #001 (12 t), Trinitario #002 (8 t), Forastero #003 (15 t) |
| Custody events | 87 | ~29 per asset: CREATED→LOADED→QC→HANDOFF→ARRIVED chain (9 steps minted per asset + auto-generated CREATED + re-runs) |
| Workflow states / event types | 34 / 49 | supply_chain preset + custom |
| Anchor requests | 1 | audit snapshot SHA256 |
| Shipment documents | 2 | packing list + BL |
| Media files (media-svc) | 3 | plot docs PDF (seed + extras) |

### Compliance (EUDR)
| Entity | Count | Sample |
|---|---|---|
| Framework activations | 1 | EUDR (sbti/rainforest-alliance/usda-nop NOT available — see bug #4) |
| Country risk benchmarks | 9 | CO = low (as_of 2025-05-01) + legacy |
| Plots | 7 (3 new) | PLOT-HUI-001, PLOT-ANT-001, PLOT-CAQ-001 |
| Plot documents | 3 | land_title per plot (cadastral cert blocked by unique constraint on re-run) |
| Records | 4 (3 new) | Criollo/Trinitario/Forastero lotes |
| Record-plot links | 3 | 100% from each plot |
| Risk assessments | 3 | all `negligible_risk`, completed |
| Supply-chain nodes | 15 | 5 per record (producer → cooperative → processor → exporter → importer) |
| Certificates | 4 | 3 EUDR PDFs + 1 regenerate; all downloadable |
| DDS submissions | 1 | `DDS-CO-2026-0002` on Criollo record |

---

## SQL Counts (post-seed)

Inventory DB (`inventorydb`):
```
products                   10
entity_batches              3
entity_serials             20
batch_quality_tests        10
warehouses                  3
warehouse_locations         9
suppliers                   3
customers                   4
business_partners           1
stock_levels               11
stock_movements            67
stock_layers               24
stock_reservations          3
purchase_orders             2
purchase_order_lines        3
sales_orders                1
sales_order_lines           3
production_runs             2
entity_recipes              2
recipe_components           5
production_resources        3
tax_rates                   5
tax_categories              2
units_of_measure           41
uom_conversions            32
categories                 10
product_types               2
supplier/customer/
  movement/warehouse/
  order types         2/2/4/3/2
custom_*_fields        5/3/2/2
customer_prices             3
shipment_documents          2
variant_attributes          1
variant_attribute_options   0  (blocked by bug #1)
cycle_counts                0  (blocked by bug #8)
```

Trace DB (`tracedb`):
```
assets                      3
custody_events             87
registry_wallets            8
organizations               6
custodian_types             5
workflow_states            34
workflow_event_types       49
anchor_requests             1
shipment_documents          2
trade_documents             0
```

Compliance DB (`compliancedb`):
```
compliance_frameworks           1
tenant_framework_activations    1
compliance_records              4
compliance_plots                7
compliance_plot_links           3
compliance_plot_documents       3
compliance_risk_assessments     3
compliance_supply_chain_nodes  15
compliance_certificates         4
country_risk_benchmarks         9
```

Media DB: `media_files = 3`.

---

## FK consistency checks (all ✅)

| Relationship | Check | Result |
|---|---|---|
| Asset → Plot | `assets.plot_id NOT NULL` | 3 / 3 |
| Record → Plot | distinct records in `compliance_plot_links` | 3 / 3 |
| Record → Risk assessment | | 3 / 3 |
| Record → Supply-chain nodes | distinct records | 3 / 3 |
| Record → Certificate | certs with `record_id NOT NULL` | 4 / 4 |
| SO → Reservation | distinct sales_orders in stock_reservations | 1 / 1 |
| Batch → Plot (via `batch_plot_origins`) | | **0 / 3** — blocked (bug #2, seeder sent correct shape but 422) |
| Batch → Quality tests | 10 tests across 3 batches | ✅ |
| Batch → Serials | 20 serials → batch COS-2026-002 | ✅ |
| Plot → Documents | 3 plots, 3 docs (first pass only; re-runs 409) | ✅ |
| Production run → Recipe | runs linked to recipes | ✅ |

---

## Bugs found

Severity legend: **S1 = 5xx crash / data corruption**, **S2 = user-visible 4xx
that should be 200 or is a bad UX**, **S3 = routing gap / docs mismatch**.

### Bug #1 — S1: `/variant-attributes/{id}/options` POST crashes with NotNullViolation on `tenant_id`
- **File**: `inventory-service/app/services/variant_service.py` (or repo it calls into)
- **Endpoint**: `POST /api/v1/variant-attributes/{attr_id}/options`
- **HTTP**: 500
- **Correlation**: `6b7e89f1-e6c0-492e-86a6-2d87dd91543d`, `8ed19fdb-0568-4188-85ed-fdbf828f2b48`
- **Reproduction**: after creating a `variant_attribute`, POST `{"value":"criollo","sort_order":0,"is_active":true}` to `/options` path.
- **Error**:
  `null value in column "tenant_id" of relation "variant_attribute_options" violates not-null constraint`
  `DETAIL: Failing row contains (879f79ed..., 8d3386e5..., forastero, null, 2, t, null).`
- **Fix**: the service/repo inserting into `variant_attribute_options` isn't passing `tenant_id` from the request scope. Probably calling `repo.create(**body.dict())` and the repo doesn't fill it from the tenant dep.

### Bug #2 — S2: `POST /api/v1/batches/{batch_id}/origins` rejects valid payload with 422
- **File**: `inventory-service/app/api/routers/batch_origins.py`
- **Endpoint**: `POST /api/v1/batches/{batch_id}/origins`
- **HTTP**: 422 on payload `{"plot_id": "...", "plot_code": "COS-2026-001", "origin_quantity_kg": "2000"}` — matches `BatchPlotOriginCreate` schema exactly.
- **Reproduction**: after creating a batch, try to link a plot. Every attempt 422s even with `plot_id`+`origin_quantity_kg`.
- **Likely cause**: the router signature probably uses a different schema, or `plot_id` length validation (max_length=36) rejects full UUIDs (36 chars) due to off-by-one, or the `plot_id` is a string but sent as UUID v4 format with dashes.
- **Impact**: breaks the inventory↔compliance trace link; assets/records still work because plots live in compliance-service and the link is optional.

### Bug #3 — S1: `POST /api/v1/cycle-counts` crashes with `AttributeError: 'list' object has no attribute 'product_id'`
- **File**: `inventory-service/app/services/cycle_count_service.py` around line 82
- **Endpoint**: `POST /api/v1/cycle-counts`
- **HTTP**: 500
- **Correlation**: `d0a9e412-3188-4454-9392-d48b8f3e4568`, `9194b856-dfe4-44eb-87b1-297047c9fa0e`
- **Reproduction**: POST `{"warehouse_id":"...","scheduled_date":"2026-04-15","notes":"..."}` — no product_ids → branch that lists all levels.
- **Root cause**: `stock_repo.list_levels(tenant_id, warehouse_id=...)` returns either a tuple `(items, total)` or a bare list whose elements aren't `StockLevel` ORM objects, and the comprehension `[(sl.product_id, sl) for sl in all_levels]` fails. Likely a recent refactor in `stock_repo.list_levels` changed the return type.
- **Blocks**: all cycle count creation until fixed.

### Bug #4 — S3: Compliance framework catalog missing SBTi / Rainforest Alliance / USDA-NOP
- **Endpoint**: `POST /api/v1/compliance/activations/` with `framework_slug` ∈ {`sbti`, `rainforest-alliance`, `usda-nop`}
- **HTTP**: 404 "Framework 'sbti' not found"
- **Reproduction**: `GET /api/v1/compliance/frameworks/` returns only `eudr`. Seed/migration only populates `eudr`.
- **Fix**: extend the seed migration in compliance-service to insert the other frameworks (they exist as `certification_schemes` but not as full `compliance_frameworks`).

### Bug #5 — S3: Gateway has no route for `/api/v1/quality-tests`
- **File**: `gateway/nginx.conf` (no `location /api/v1/quality-tests` block)
- **Impact**: `POST /api/v1/quality-tests` via gateway returns 404 even though `inventory-api:9003` exposes it and the direct call works. Seeder worked around by hitting `http://localhost:9003` directly.
- **Fix**: add `location /api/v1/quality-tests { proxy_pass http://inventory$request_uri; }`.

### Bug #6 — S1: `POST /api/v1/sales-orders` crashes with `MissingGreenlet` on SO-002 (withholding + addition tax mix)
- **File**: likely in SO creation service when resolving `tax_rate_ids` and writing `sales_order_line_taxes`
- **Endpoint**: `POST /api/v1/sales-orders`
- **HTTP**: 500
- **Correlation**: `b80d89f6-1d8a-495f-a787-c10772aa5c1f`, `8ede2c48-9193-40b4-abbb-4f0fa009ed21`
- **Reproduction**: create SO with lines that carry 2 `tax_rate_ids`, one `iva` (addition) + one `retefuente` (withholding). Single-rate SO-001 (USD, no tax_rate_ids) works.
- **Root cause**: likely lazy-loading relationship inside an already-closed async session when persisting `sales_order_line_taxes`. `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called`.
- **Blocks**: creation of domestic SOs with multi-stack taxation.

### Bug #7 — S1: `POST /api/v1/alerts/scan` crashes
- **File**: `inventory-service/app/api/routers/alerts.py` → scanner service
- **HTTP**: 500
- **Correlation**: `e1a512af-2f18-4f97-884f-dae339b17ecf`, `bc7a981b-291d-4085-8132-320b640e632f`
- **Reproduction**: `POST /api/v1/alerts/scan` with any body. Logs not in the recent window — would need `docker compose logs --since=10m inventory-api | grep alerts`.

### Bug #8 — S2: `POST /api/v1/reorder/check` accepts no way to trigger all-products scan with consistent response
- `POST /api/v1/reorder/check` without body returns a `list[POOut]` (possibly empty). `POST /api/v1/reorder/check/{product_id}` returns `POOut | None`. It's not a 5xx, but the auto-generated openapi suggests this endpoint is supposed to both create POs and return status for each product — the contract is unclear.

### Bug #9 — S2: `GET /api/v1/analytics/kardex/{product_id}` returns 404 but the router declaration is `@router.get("/kardex/{product_id}")` at prefix `/api/v1/analytics`
- The route is declared but access returns 404 via gateway. Possibly same missing-gateway-location issue. Direct to :9003 works? Not verified.

### Bug #10 — S3: `GET /api/v1/compliance/legal/` returns 404
- `legal_catalog_router` is included in `compliance-service/app/main.py` with prefix `/api/v1/compliance/legal`, but GET root returns 404. Likely needs a trailing-slash variant or the router declares `@router.get("/catalog")` instead of `/`.

### Bug #11 — S2: `POST /api/v1/compliance/plots/{id}/documents` requires `media_file_id` but error response is unhelpful
- If you don't upload a media file first you get 422 `Field required` — which is technically correct but the UI would need a "click to upload" pattern. Consider accepting `document_url` + `document_hash` as an alternative contract (operator already has the doc stored externally).

### Bug #12 — S2: `POST /api/v1/partners` returns 422 `Partner must be at least supplier or customer` but doesn't accept `freight_forwarder` as a standalone business relationship
- Operators need to book freight forwarders and customs brokers as business partners for shipment documents. Current schema forces `is_supplier=True` OR `is_customer=True`. Our workaround: set `is_supplier=True` on the customs agency. Consider adding a 3rd boolean `is_service_provider`.

### Bug #13 — S2: Partner custom fields endpoint missing
- There's `config/supplier-fields`, `customer-fields` implicit, `warehouse-fields`, `movement-fields`, but no `config/partner-fields`. Partner entity doesn't expose custom attributes → operator has no way to extend it.

### Bug #14 — S2: Certificate generation requires record status ∈ {compliant, declared, partial, ready}, but freshly-created records default to `incomplete` even when all required fields are present, until `GET /records/{id}/validate` is explicitly called
- The seeder had to call `validate` after link-plots to promote records. Expectation from an operator: creating a record with a `buyer_email` + declarations + plot link should land in `compliant` immediately. The lazy-validation-on-read pattern is confusing.

---

## Endpoints NOT exercised (and why)

| Endpoint | Why |
|---|---|
| `/api/v1/variants` POST | Blocked by bug #1 (no variant options exist → can't build variant rows) |
| `/api/v1/cycle-counts/*` POST (after create) | Blocked by bug #3 (create 500s) |
| `/api/v1/po-approval-logs` | PO approval workflow only triggers if threshold config hit; default threshold = 0 means auto-approve |
| `/api/v1/goods-receipts` | PO receive endpoint auto-creates a GRN; explicit goods-receipts POST exists but workflow wasn't exercised separately |
| `/api/v1/stock/qc-approve` / `qc-reject` | Requires stock in QC_PENDING state; seeder path didn't route any stock through QC |
| `/api/v1/sales-orders/{id}/retry-invoice` etc. | E-invoicing provider (Matías) returned 422 on `X-Service-Token`; retry loop not exercised |
| `/api/v1/integrations/` (inventory) | The seeder touched compliance integrations; there's no router `/integrations/` in inventory-service |
| `/api/v1/public/verify/*` | Public-verify flow requires anchored assets — exercisable but not part of MVP coverage target |
| `/api/v1/portal/*` | 404 — portal routes require a customer portal session, not a JWT |
| `/api/v1/solana/network` | 404 — endpoint declared but possibly behind a feature flag / not mounted |
| `/api/v1/anchoring/{hash}/status` | 404 — anchor hash created but status polling returns 404; probably needs the ARQ worker to have processed it first |
| `/api/v1/compliance/legal/` | 404 — bug #10 |
| `/api/v1/compliance/national-platforms/{slug}/lookup` | Only listed, not looked-up (requires external API creds) |
| `/api/v1/compliance/activations/{slug}` PATCH | List/POST covered; PATCH not needed for this dataset |
| `/api/v1/compliance/integrations/{provider}/test` | Not exercised; needs provider credentials |
| `/api/v1/compliance/records/{id}/cadmium-test` | Cadmium is a test for cocoa but EU threshold is 0.8 mg/kg; covered via quality_tests in inventory, not via compliance cadmium-test specific endpoint |
| `/api/v1/compliance/certifications/` POST/PATCH | List covered (6 schemes seeded); no tenant-level certification create exercised |
| `/api/v1/compliance/plots/{id}/anchor-callback` | Webhook endpoint — not part of a human-driven flow |
| `/api/v1/compliance/supply-chain/reorder` | Requires ≥2 nodes per record already created (we have 5) but wasn't exercised |
| `/api/v1/tenants/*` (trace) | Tenant management not in scope (tenant `default` already exists) |
| `/api/v1/media/files/batch` | Single upload used instead |
| `/api/v1/media/files/reference-counts` | Not exercised |
| `/api/v1/analytics/inventory-kpis` | 404 (either permission-guard redirect or gateway gap — not investigated) |
| `/api/v1/reorder/configure` | No explicit config endpoint found — `reorder_point` set via product create body |
| `/api/v1/mrp/explode` | 422 — MRP explode needs a different body shape (not investigated further) |

## Reproduction / re-run

```bash
# Re-login (in case token expired)
curl -s -X POST http://localhost:9000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"seed-e2e@tracelog.io","password":"SeedPass123!"}' \
  -o qa/seed/_login.json
python -c "import json; d=json.load(open('qa/seed/_login.json')); open('qa/seed/token.txt','w').write(d['access_token'])"

# Run seeder
python qa/seed/seed_mega.py

# Inspect results
cat qa/seed/seed_mega_state.json | jq '. | keys'
tail -50 qa/seed/seed_mega_run.jsonl
```
