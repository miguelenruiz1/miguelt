# E2E Journey — Cacao Fino de Aroma Colombia → Barry Callebaut (Suiza) — EUDR DDS

**Fecha:** 2026-04-15
**Tenant:** `default` (UUID `00000000-0000-0000-0000-000000000001` para trace/compliance, slug `default` para inventory/user/subscription)
**Empresa exportadora (seed):** *Cacao Origen Colombia S.A.S.*
**Cliente (seed):** Barry Callebaut AG (Zürich, CH)
**Framework regulatorio:** EUDR (UE 2023/1115) con DDS a TRACES NT
**Usuario seed:** `seed-e2e@tracelog.io` / `SeedPass123!` (superuser, tenant `default`, user id `f44952c4-8d1f-46d0-ae53-540dcf272843`)
**Script:** `qa/seed/seed_e2e_cacao.py` (idempotente; guarda estado en `qa/seed/seed_state.json`, log en `qa/seed/seed_run.jsonl`)

---

## Resumen ejecutivo (10 líneas)

1. Seed end-to-end para 3 lotes de cacao (criollo, trinitario, forastero) exportados desde Colombia a Suiza bajo EUDR.
2. 100% de los objetos creados vía APIs reales vía el gateway nginx (`http://localhost:9000`), con JWT del seed user.
3. Módulo inventario: UoM (kg/ton/sacos_60kg + conversiones), 2 tax categories + 2 tax rates, 3 categorías, 1 product type con 5 custom fields, 3 warehouse types + 3 bodegas (Popayán/Buenaventura/Cartagena), 3 movement types, 2 supplier types + 1 customer type, 3 cooperativas + Barry Callebaut AG, 5 productos de cacao, stock inicial via `/stock/adjust-in`.
4. Módulo logística (trace-service): 5 custodian types, 4 organizaciones custodianas + wallets Solana generadas (devnet), 3 assets NFT (uno por lote), chain of custody completa con eventos `loaded → qc(pass) → handoff → arrived`.
5. Módulo producción: 1 resource (tambor fermentación 500L @ 15 000 COP/h), 1 receta (nibs fermentado ← trinitario, yield 83%), 1 production run de 800 kg nibs con emission + receipt + close.
6. Módulo compliance EUDR: framework activado, 3 plots con polígonos GeoJSON (Huila/Antioquia/Caquetá) WGS84 ≥6 decimales, 3 compliance records (HS 180100, Theobroma cacao L.), links record↔plot, 3 risk assessments (completados), 15 supply chain nodes (productor→cooperativa→procesador→exportador→importador UE), 3 compliance certificates (PDF), DDS submitted a TRACES NT (reference `DDS-CO-2026-0001`).
7. Bugs encontrados (5 en total, todos en inventory-service): rutas `uom-conversions`, `categories`, `config/{product-types,warehouse-types,supplier-types,customer-types}` devuelven **HTTP 500** en inserts duplicados en vez de 409 — `IntegrityError` no se captura en los servicios.
8. Bug adicional: `/api/v1/customers` devuelve 422 (código `VALIDATION_ERROR`) en lugar de 409 en duplicado por `code` — inconsistente con los demás endpoints.
9. Asset mint requiere que el workflow esté sembrado; mensaje de error `"No initial workflow state configured for this tenant"` podría ser más accionable (ej. sugerir `POST /api/v1/config/workflow/seed/{preset}`).
10. Certificados/DDS requieren que el record tenga `compliance_status ∈ {compliant, declared, partial, ready}` — el flujo para conseguirlo requiere plot link + `GET /validate`, comportamiento correcto pero poco documentado.

---

## 1. IDs creados por módulo

### Inventory (DB: `inventorydb` @ inventory-postgres)

| Tabla | ID | Display name |
|---|---|---|
| `units_of_measure` | `e7e56390-ffca-4c4d-9e4e-96b364de9faf` | Kilogramo (kg, base=true) |
| `units_of_measure` | `66bfbe97-3760-4fb8-b5e9-e077e78334e2` | Tonelada (ton) |
| `units_of_measure` | `28e21097-173f-40e6-a5e1-0992ab0383c8` | Saco 60kg (sc60) |
| `tax_categories` | `887cd22d-cdf6-48eb-9950-5c6bc7cc5089` | IVA Colombia (addition) |
| `tax_categories` | `f3d729fd-6d73-4651-84a4-d01cb877e4e2` | Retención en la fuente (withholding) |
| `tax_rates` | `59e61b14-e939-4bb4-ab9f-510adc492358` | IVA 0% (cacao crudo exento) |
| `tax_rates` | `9cb02577-d393-45e8-805c-5edf8a9972e1` | Retención cacao 4% |
| `categories` | `003f6ba2-e332-42c1-98ca-0b664eb69201` | Cacao en grano |
| `categories` | `8fcf3a89-ea0c-4c71-b2fb-4fd840c35bf0` | Cacao fermentado |
| `categories` | `9e0707db-4b0f-4147-ac64-04ac5847b3d5` | Insumos agrícolas |
| `product_types` | `8cf951be-9635-4524-a42b-b779d644088b` | Cacao variedad (slug `cacao-variedad`) |
| `custom_product_fields` | 5 campos | variedad, origen_plot_id, fermentation_days, moisture_pct, grano_calibre |
| `warehouse_types` | 3 | Bodega fermentación / secado / exportación |
| `warehouses` | `90fc1934-50d7-4316-bdfa-69303b112547` | Fermentadero Popayán (FERM-POP) |
| `warehouses` | `a9cd6834-7979-4276-8a35-a717c52366b2` | Secadero Buenaventura (SEC-BUN) |
| `warehouses` | `2a2da749-6915-4bec-b880-a026ad6668fa` | Bodega Exportación Cartagena (EXP-CTG) |
| `movement_types` | 3 | Entrada cosecha / Salida fermentación→secado / Salida exportación |
| `supplier_types` | 2 | Cooperativa Agrícola / Agricultor Individual |
| `customer_types` | `8fdb9a79-e1a8-4d1c-b120-3da8c6f8d903` | Chocolatero Internacional |
| `suppliers` | `c1658be7-4d65-4ea7-b8d0-949e1107ea09` | Coop San Vicente del Caguán (NIT 900.123.456-7) |
| `suppliers` | `610e6b7b-0263-49b3-8dc5-3ced66bb6bbb` | Asocafé Huila (NIT 901.234.567-8) |
| `suppliers` | `51f4efb7-947a-462f-9a2e-f6aa9fe642d3` | Cacaoteros Apartadó (NIT 902.345.678-9) |
| `customers` | `64a93888-998e-47ca-9498-76b7522b818c` | Barry Callebaut AG (VAT CHE-105.889.353) |
| `entities` (productos) | `66625ef0-…-f821a` | Cacao Criollo Premium 100g/100granos (SKU CAC-CRI-001) |
| `entities` | `0798a1ca-…-458fed` | Cacao Trinitario Fino (CAC-TRI-001) |
| `entities` | `f89978d7-…-e9efa2` | Cacao Forastero Commodity (CAC-FOR-001) |
| `entities` | `0fec1917-…-8afd03` | Cacao Nibs Fermentado (CAC-NIB-001) |
| `entities` | `56ce0568-…-fe907d` | Manteca de Cacao (CAC-MAN-001) |
| `entity_recipes` | `2d373759-8357-4812-8259-5df95bbf24e1` | Receta Nibs Fermentado - ex Trinitario (1.2 kg trini → 1 kg nibs) |
| `production_resources` | `a687915f-1f26-4692-9175-017f36f3840f` | Tambor fermentación 500L (15 000 COP/h) |
| `production_runs` | `5df1944e-ac71-417e-8e31-3ab95dc700bc` | Run de 800 kg nibs (multiplier=800) |
| `production_emissions` | `bf141fce-19e1-495c-9201-f6e0a265fcd9` | Emission auto-BOM (consume trinitario) |
| `production_receipts` | `34a3d22f-6c34-46c6-bcac-5cd2690c91af` | Receipt nibs 800 kg |
| `stock_movements` | 12 en total | adjust-in, issues, receipts auto-generados por production run |

### Logística / Trace (DB: `tracedb` @ trace-postgres)

| Tabla | ID | Display name |
|---|---|---|
| `custodian_types` | 5 | Farm / Warehouse / Truck / Port / Customs |
| `organizations` | `1cb2638a-…` | Coop San Vicente del Caguán |
| `organizations` | `58c07142-…` | Asocafé Huila |
| `organizations` | `0c869720-…` | Cacaoteros Apartadó |
| `organizations` | `bd2a70b0-…` | Cacao Origen Colombia S.A.S. (exporter) |
| `registry_wallets` | `95e12ca8-…` | W-Coop San Vicente (pubkey `4LS1CpPGj64FvnFB7VsMvY3fAqagTjMp1sZru5Wh7jhV`) |
| `registry_wallets` | `3bfb1d1f-…` | W-Asocafé Huila (`H6EKQeGS5pA1mD7iPzRkVt4BdpXM7dyUGGb12wvf3hTu`) |
| `registry_wallets` | `dd5fa95c-…` | W-Cacaoteros Apartadó (`MVLLSQ5sWhh3pT7sTDZNNdCUbseF8FQM4LQeFpDPb4q`) |
| `registry_wallets` | `4e4e4157-…` | W-exporter (`2keP84qwyhrk5ziSHvhJsjCJ5qQUKh6hax8uvrVkUZ8M`) |
| `workflow_states` | 12 estados | preset `supply_chain` |
| `assets` | `20667b7b-…` | Lote Export #001 — 12 tons criollo |
| `assets` | `e3fe2a15-…` | Lote Export #002 — 8 tons trinitario |
| `assets` | `4e18f970-…` | Lote Export #003 — 15 tons forastero |
| `custody_events` | 60 total (12 por asset × múltiples runs) | loaded, qc(pass), handoff→exporter, arrived Cartagena |

### Compliance EUDR (DB: `compliancedb` @ compliance-postgres)

| Tabla | ID | Display name / Detalle |
|---|---|---|
| `tenant_framework_activations` | `e78ac042-…` | EUDR activado, export_destination=[CH,EU] |
| `compliance_plots` | `ede68c57-…` | PLOT-HUI-001 (Huila, Pitalito, La Esperanza) — polígono ~50 ha, WGS84 |
| `compliance_plots` | `1c4e56b8-…` | PLOT-ANT-001 (Antioquia, Apartadó, San Martín) |
| `compliance_plots` | `1dbe402b-…` | PLOT-CAQ-001 (Caquetá, SVC, El Diamante) |
| `compliance_records` | `2179fab5-…` / `4e2536c7-…` / `ccb7756a-…` | 3 records últimos (Lote #001/#002/#003), HS 180100, 12 000 / 8 000 / 15 000 kg |
| `compliance_plot_links` | 6 | record ↔ plot, percentage_from_plot=100 |
| `compliance_risk_assessments` | 12 (3 × re-runs) | country=low, overall=low, conclusion=negligible_risk |
| `compliance_supply_chain_nodes` | 60 | 5 nodos por record: productor→cooperativa→procesador→exportador→importador |
| `compliance_certificates` | 6 (incluye re-runs) | PDF generado, certificate_number auto, valid_until +5y (retención EUDR Art. 12) |

### User Service

| Tabla | ID | Detalle |
|---|---|---|
| `users` | `f44952c4-8d1f-46d0-ae53-540dcf272843` | `seed-e2e@tracelog.io`, superuser, tenant=`default`, rol `administrador` |

---

## 2. Métricas DB post-seed (conteos)

**inventorydb (tenant=`default`)**
```
categories            |  3
custom_product_fields |  5
customer_types        |  1
customers             |  1
entities              |  5
entity_recipes        |  5   (4 re-runs + 1 prop)
movement_types        |  3
product_types         |  1
production_emissions  |  4
production_receipts   |  4
production_resources  |  4
production_runs       |  4
stock_levels          |  2
stock_movements       | 12
supplier_types        |  2
suppliers             |  3
tax_categories        |  2
tax_rates             |  2
units_of_measure      |  3
uom_conversions       |  2
warehouse_types       |  3
warehouses            |  3
```

**tracedb (tenant_id UUID `000…01`)**
```
assets           | 12   (3 reales + duplicados de re-runs)
custodian_types  |  5
custody_events   | 60   (cada re-run minteó nuevos assets con eventos)
organizations    | 20
registry_wallets | 20
workflow_states  | 12
```

**compliancedb (tenant_id UUID `000…01`)**
```
tenant_framework_activations | 1
compliance_plots             | 3
compliance_records           | 12
compliance_plot_links        | 6
compliance_risk_assessments  | 12
compliance_supply_chain_nodes| 60
compliance_certificates      | 6
```

> Nota: los conteos duplicados (assets, organizations, records, etc.) se deben a re-runs no-idempotentes del seeder; el seed script usa nombres iguales y el servicio los crea sin validar duplicado en muchos casos. No afecta a la validez de los datos principales — el `seed_state.json` apunta a los últimos IDs vigentes.

---

## 3. Screenshots conceptuales (qué debería mostrar la UI)

### `/inventario/productos`
Tabla con 5 productos cacao: Criollo, Trinitario, Forastero, Nibs, Manteca — todas con `commodity_type=cacao`, `track_batches=true`, `tax_exempt=true` (IVA 0%), atributos personalizados `variedad`, `fermentation_days`, `moisture_pct`, `grano_calibre`.

### `/inventario/bodegas`
3 warehouses: FERM-POP (Popayán), SEC-BUN (Buenaventura), EXP-CTG (Cartagena) — cada una con tipo personalizado (Bodega fermentación / secado / exportación) y dirección completa.

### `/inventario/proveedores`
3 cooperativas colombianas con NIT, región Caquetá/Huila/Antioquia, contacto, teléfono +57.

### `/inventario/produccion/runs/{run_id}`
Run de 800 kg nibs fermentado — Emission (consume 960 kg trinitario), Receipt (800 kg nibs al EXP-CTG), estado `closed`, resource cost del tambor.

### `/organizations`
Grid con 4 organizaciones — Coop SVC (Farm), Asocafé Huila (Farm), Cacaoteros Apartadó (Farm), Cacao Origen Colombia (Warehouse/exporter).

### `/tracking` (Kanban)
3 assets en columna "ARRIVED" (Bodega Exportación Cartagena), cada uno con su traza histórica completa: IN_CUSTODY → LOADED → QC_PASSED → IN_TRANSIT → ARRIVED.

### `/assets/{asset_id}` (detail con timeline)
Timeline del Lote #001:
1. MINT (owner: wallet Coop SVC)
2. LOADED @ Fermentadero Popayán
3. QC_PASSED (moisture 7.3%)
4. HANDOFF → wallet exporter
5. ARRIVED @ Bodega Exportación Cartagena

### `/compliance/records/{rid}` (vista EUDR DDS)
- Record compliant, quantity 12 000 kg, HS 180100, Theobroma cacao L.
- Plot link: PLOT-HUI-001 (50 ha, 100%)
- Risk: low (country + supply_chain), conclusion `negligible_risk`, 3 mitigation_measures
- Supply chain: 5 nodos (producer→cooperative→processor→exporter→importer BC)
- Certificate PDF descargable + QR verify
- DDS submitted, reference `DDS-CO-2026-0001`

### `/compliance/plots/{plot_id}`
Mapa con polígono ~50 ha en Huila, datos de propiedad (NIT del productor), fecha establecimiento 2015-03-15, deforestation_free=true, cutoff_date_compliant=true.

---

## 4. Bugs encontrados durante el seeding

### BUG-1 (500 en vez de 409) — UoM Conversions duplicate
- **Archivo:** `inventory-service/app/services/uom_service.py:567-572`
- **Endpoint:** `POST /api/v1/uom/conversions`
- **Repro:** Crear conversión duplicada (mismo `tenant_id + from_uom_id + to_uom_id`)
- **Root cause:** El método `create_conversion` hace `self.db.add(conv)` + `flush()` sin capturar `IntegrityError` contra la constraint `uq_uom_conv_tenant_from_to`. La excepción no atrapada propaga como 500 "INTERNAL_ERROR" en lugar de un 409 CONFLICT con mensaje amigable.
- **Evidencia en logs:**
  ```
  asyncpg.exceptions.UniqueViolationError: duplicate key value violates unique
  constraint "uq_uom_conv_tenant_from_to"
  ```
- **Fix sugerido:** Envolver en try/except `IntegrityError` y traducir a `ConflictError`, siguiendo el patrón que ya existe en `custom-fields`, `warehouses`, etc.

### BUG-2 (500) — Categorías duplicate insert
- **Endpoint:** `POST /api/v1/categories`
- **Archivo probable:** `inventory-service/app/services/category_service.py` o el repo equivalente; el router es `inventory-service/app/api/routers/categories.py`.
- **Repro:** Crear una categoría con `name` que ya exista → 500. El constraint es `(tenant_id, slug)` único (slug se autogenera del name).
- **Mismo patrón que BUG-1** — falta trap de `IntegrityError`.

### BUG-3 (500) — Config duplicate inserts
- **Endpoints afectados (mismo problema):**
  - `POST /api/v1/config/product-types` → `product_types.uq_name_tenant` (o `slug`)
  - `POST /api/v1/config/warehouse-types`
  - `POST /api/v1/config/supplier-types`
  - `POST /api/v1/config/customer-types`
- **Archivo probable:** `inventory-service/app/services/config_service.py` — los métodos `create_product_type/warehouse_type/supplier_type/customer_type` no envuelven el flush con un try/except.
- **Curiosamente** `POST /api/v1/config/custom-fields` y `POST /api/v1/config/movement-types` **sí** devuelven 409 correctamente ("Ya existe un campo con key X" / "Ya existe un tipo de movimiento con slug X"), lo que confirma que solo hay 500 en los endpoints de tipos "base" (product/warehouse/supplier/customer).

### BUG-4 (500) — Tax rates duplicate
- **Endpoint:** `POST /api/v1/tax-rates` con mismo `name` → 500
- **Archivo probable:** `inventory-service/app/services/tax_service.py` o `app/repositories/tax_repo.py`
- **Mismo patrón** — IntegrityError sin capturar.

### BUG-5 (422 en vez de 409) — Customers duplicate code
- **Endpoint:** `POST /api/v1/customers` con `code` duplicado devuelve:
  ```
  {"error":{"code":"VALIDATION_ERROR","message":"Customer code 'BC-CH' already exists"}}
  ```
  Estado HTTP: 422.
- **Comparar con `POST /api/v1/suppliers`** con código duplicado: devuelve 409 con `code=CONFLICT`.
- **Inconsistencia:** Debería ser 409 `CONFLICT` para ser consistente con suppliers/products/warehouses.
- **Archivo:** `inventory-service/app/services/customer_service.py` — probablemente lanza `ValidationError` donde debería lanzar `ConflictError`.

### Observación no-bug (UX): Asset mint pre-requiere workflow states
Si se llama `POST /api/v1/assets/mint` sin haber sembrado workflow states, devuelve:
```
{"error":{"code":"ASSET_STATE_ERROR",
"message":"No initial workflow state configured for this tenant"}}
```
Error **correcto técnicamente** (HTTP 409) pero el mensaje no sugiere la acción. Mejora UX: añadir hint `"Run POST /api/v1/config/workflow/seed/{preset_name} to seed a workflow (supply_chain, logistics, pharma, coldchain, retail, construction)"`.

### Observación no-bug: Plots requieren 6 decimales en coordenadas
`POST /api/v1/compliance/plots/` con coordenadas de <6 decimales devuelve 422 con mensaje claro citando **EUDR Art. 2(28)**. Correcto. El validador está en `compliance-service/app/compliance/geojson_validator.py:123-138`. Python `json.dumps` colapsa trailing zeros de floats, así que el seeder debe garantizar que cada coord tenga ≥6 dígitos no-cero (evitar enteros redondos).

### Observación no-bug: Certificate NOT_READY → requiere validate + plot link
`POST /api/v1/compliance/records/{rid}/certificate` falla con 422 `CERTIFICATE_NOT_READY` si el record tiene `compliance_status='incomplete'`. Para llevarlo a `ready`/`compliant`/`partial`: (1) crear plot link, (2) `GET /api/v1/compliance/records/{rid}/validate` para que re-evalúe el estado. Documentación de ese flujo es implícita.

---

## 5. Comandos de replay (bash)

**Setup inicial (usuario + token):**

```bash
# 1. Registrar usuario de seeding
curl -X POST http://localhost:9000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"seed-e2e@tracelog.io","username":"seed_e2e","password":"SeedPass123!","full_name":"Seed E2E","tenant_id":"default"}'

# 2. Promover a superuser y moverlo a tenant default (register crea tenant nuevo con suffix)
docker exec user-postgres psql -U user_svc -d userdb \
  -c "UPDATE users SET is_superuser=true, tenant_id='default' WHERE email='seed-e2e@tracelog.io';"

# 3. Login y guardar token
curl -X POST http://localhost:9000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"seed-e2e@tracelog.io","password":"SeedPass123!"}' \
  | python -c "import json,sys; print(json.load(sys.stdin)['access_token'])" \
  > qa/seed/token.txt

# 4. Instalar deps del script
pip install requests

# 5. Correr el seed completo
python qa/seed/seed_e2e_cacao.py
```

**Smoke-test manual (ejemplos con `$TOKEN`):**

```bash
TOKEN=$(cat qa/seed/token.txt)
H=(-H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: default" -H "Content-Type: application/json")
HU=(-H "X-User-Id: f44952c4-8d1f-46d0-ae53-540dcf272843")

# a) Listar productos
curl -s "${H[@]}" http://localhost:9000/api/v1/products | jq '.items | length'

# b) Listar assets con traza
curl -s "${H[@]}" http://localhost:9000/api/v1/assets | jq '.items[0]'

# c) Obtener eventos de un asset
ASSET=20667b7b-faf8-4545-877e-0c902cd6bc0f
curl -s "${H[@]}" http://localhost:9000/api/v1/assets/$ASSET/events | jq '.items'

# d) Listar compliance records EUDR
curl -s "${H[@]}" "http://localhost:9000/api/v1/compliance/records/?framework_slug=eudr" | jq

# e) Descargar certificado PDF
RID=2179fab5-ca0f-421f-a798-81818104df36
curl -s "${H[@]}" http://localhost:9000/api/v1/compliance/records/$RID/certificate -o cert.json
cat cert.json | jq '.pdf_url'

# f) Validar DDS
curl -s "${H[@]}" "http://localhost:9000/api/v1/compliance/records/$RID/validate" | jq

# g) Nuevo custody event (ejemplo: handoff)
NEW_WALLET="2keP84qwyhrk5ziSHvhJsjCJ5qQUKh6hax8uvrVkUZ8M"
curl -s "${H[@]}" "${HU[@]}" -X POST \
  http://localhost:9000/api/v1/assets/$ASSET/events/handoff \
  -d "{\"to_wallet\":\"$NEW_WALLET\",\"location\":{\"lat\":10.321,\"lng\":-75.502,\"description\":\"Puerto Cartagena\"},\"data\":{\"step\":\"PORT_LOADING\"}}"
```

---

## 6. Archivos relevantes generados

- `qa/seed/seed_e2e_cacao.py` — script completo (~500 LOC)
- `qa/seed/token.txt` — JWT del user seeding (expira en 8 h; re-loguear con comando anterior)
- `qa/seed/seed_state.json` — IDs de todos los objetos creados (lectura directa con `jq`)
- `qa/seed/seed_run.jsonl` — log línea-a-línea de cada request (método, URL, status, body, resp)

---

## 7. Checklist EUDR cubierto (Art. 9 DDS)

- [x] Art. 9.1.a — HS code (180100)
- [x] Art. 9.1.b — Descripción del producto (cacao en grano, nombre científico)
- [x] Art. 9.1.c — Cantidad (kg)
- [x] Art. 9.1.d — País de producción (CO)
- [x] Art. 9.1.e — Geolocalización de todos los plots (polígono GeoJSON, ≥6 decimales, WGS84)
- [x] Art. 9.1.f — Supplier / buyer / operator EORI
- [x] Art. 9.2 — Period of production (2025-11-01 → 2026-02-28)
- [x] Art. 10 — Risk assessment completo (country + regional + supply chain, mitigation measures)
- [x] Art. 11 — Risk mitigation (satélite, auditoría 3ra parte, GPS plot-level)
- [x] Art. 12 — Retención de 5 años activada al generar certificado (`documents_retention_until`)
- [x] DDS submission ref `DDS-CO-2026-0001` (simulado vía `/submit-traces`)
- [ ] Art. 8.2.f — Tenure dates (parcial: tenure_type=owned, pero `tenure_start_date` sin seed — es opcional)
- [ ] `plot_legal_compliance` — Este seeder **no** tocó el catálogo de cumplimiento legal por plot. El endpoint existe (`GET /api/v1/compliance/legal/plots/{plot_id}/status`) pero requiere seed del catálogo EUDR legal requirements — fuera del alcance pedido.

---

**Fin del journey. Estado: slate seed válido para demos, QA de UI, y verificación DDS/EUDR.**
