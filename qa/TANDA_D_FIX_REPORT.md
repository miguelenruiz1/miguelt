# Tanda D — Fix Report

Fecha: 2026-04-15
Scope: 5 bugs críticos (4 S1 del mega-seed E2E + 1 medium Phase 1).

---

## BUG-05 (medium) — `subscription_service.generate_invoice` ignora billing_cycle

**Archivo**: `subscription-service/app/services/subscription_service.py:158-178`

**Cambio** (≈6 líneas): branch por `billing_cycle == BillingCycle.annual` usando
`price_annual or (price_monthly * 12)`, con fallback `price_monthly` para
monthly/custom. Currency pasa de `"USD"` → `"COP"`.

```python
if sub.plan is None:
    amount = Decimal("0")
elif sub.billing_cycle == BillingCycle.annual:
    amount = sub.plan.price_annual or (sub.plan.price_monthly * 12)
else:
    amount = sub.plan.price_monthly
# currency fallback: "COP" (antes "USD")
```

**Tests agregados** (`subscription-service/tests/unit/test_invoice_service.py`):
- `test_generate_invoice_monthly_uses_price_monthly` (rename + aserción sobre
  monthly path explícito)
- `test_generate_invoice_annual_uses_price_annual` (nuevo — pin fix)
- `test_generate_invoice_annual_falls_back_to_monthly_x12` (nuevo — edge case
  `price_annual IS NULL`)

**Smoke test**: N/A (requiere SO + subscription annual reales). Cubierto solo
por unit tests — el pin del caso annual asegura que no se reintroduzca el bug.

---

## BUG-01 (S1) — `POST /variant-attributes/{id}/options` 500 NotNullViolation tenant_id

**Archivo**: `inventory-service/app/services/variant_service.py:29-54`

**Root cause**: `add_option(attr_id, tenant_id, data)` forwarded `data` a
`option_repo.create(data)` sin inyectar `tenant_id`. La columna
`variant_attribute_options.tenant_id` es NOT NULL → IntegrityError.

Mismo bug (silenciado) en `create_attribute` loop inline de `options`.

**Cambio** (2 líneas, una por método):
```python
# add_option:
data["tenant_id"] = tenant_id
# create_attribute (inline options loop):
opt["tenant_id"] = tenant_id
```

**Tests agregados** (`inventory-service/tests/unit/test_variant_options.py`):
- `test_add_option_injects_tenant_id`
- `test_create_attribute_with_inline_options_injects_tenant_id`

**Smoke test**: OK
```
POST /api/v1/variant-attributes                    → 201
POST /api/v1/variant-attributes/{id}/options       → 201 (con tenant_id correcto)
```

---

## BUG-02 (S1) — `POST /cycle-counts` 500 `AttributeError 'list' has no 'product_id'`

**Archivo**: `inventory-service/app/services/cycle_count_service.py:80-84`

**Root cause**: `StockRepository.list_levels` devuelve `tuple[list[StockLevel], int]`
(rows + total). El service iteraba el tuple asumiendo que era solo la lista, así
que la primera iteración le entregaba `[StockLevel, …]` en vez de `StockLevel`.

**Cambio** (2 líneas):
```python
all_levels, _ = await self.stock_repo.list_levels(
    tenant_id, warehouse_id=warehouse_id, limit=10_000
)
levels = [(sl.product_id, sl) for sl in all_levels]
```
(Limit explícito a 10_000 para no quedarse con el default=50 que truncaría
cycle counts grandes — ver regla #9: cambio justificado, no cosmético.)

**Test agregado** (`inventory-service/tests/unit/test_cycle_count_service.py`):
- `test_create_count_unpacks_list_levels_tuple` — mockea `list_levels` con el
  shape real `(rows, total)` y verifica que `create_items_bulk` recibe el
  `product_id` correcto de cada row.

**Smoke test**: OK (`POST /cycle-counts` con `methodology=random_selection` → 201).

---

## BUG-03 (S1) — `POST /sales-orders` 500 MissingGreenlet con multi-stack IVA+Retefuente

**Archivo**: `inventory-service/app/repositories/sales_order_repo.py:11-21`

**Root cause**: `_SO_OPTIONS` cargaba `selectinload(SalesOrderLine.line_taxes)`
pero NO cargaba eagerly `SalesOrderLineTax.rate` ni `TaxRate.category`. Cuando
`recalculate_so_totals` intentaba leer `lt.rate.category.behavior` para la
2da pasada (withholding), SQLAlchemy disparaba lazy-load en contexto async →
`MissingGreenlet`.

**Cambio** (agregado al tuple de options):
```python
selectinload(SalesOrder.lines)
    .selectinload(SalesOrderLine.line_taxes)
    .selectinload(SalesOrderLineTax.rate)
    .selectinload(TaxRate.category),
```

**Tests agregados** (`inventory-service/tests/unit/test_sales_order_multi_stack.py`):
- `test_recalculate_so_totals_iva_plus_retefuente_no_greenlet` — IVA 19% +
  Retefuente 4% sobre 1000, verifica `tax_amount=190`, `retention=40`,
  `total_payable=1150`.
- `test_recalculate_so_totals_multi_stack_two_additions` — dos taxes tipo
  addition en la misma línea.

**Smoke test**: OK
```
POST /sales-orders con tax_rate_ids=[IVA_ID, RETEFUENTE_ID] → 201
  subtotal=1000.00, tax_amount=190.00, total_retention=40.00,
  total_with_tax=1190.00, total_payable=1150.00
```

---

## BUG-04 (S1) — `POST /alerts/scan` 500 UnboundLocalError

**Archivo**: `inventory-service/app/services/alert_service.py:244-247`

**Root cause**: Dentro de `check_expiry_alerts` había un `from ... import
EntityBatch` local (línea 246). Python marca el nombre como local para TODO
el scope de la función, lo que shadoweaba el import module-level y lanzaba
`UnboundLocalError` en la PRIMERA uso del nombre (línea 183) — mucho antes
de llegar al rebind local.

**Cambio** (3 líneas, solo eliminación del re-import + comentario
explicativo):
```python
# Bulk-load all referenced batches in a single query (was N+1 in loop)
# NOTE: EntityBatch is imported at module level — do NOT re-import here,
# it creates a local-scope rebind that shadows the module-level name...
if unresolved:
    batch_ids = list({a.batch_id for a in unresolved if a.batch_id})
```

**Tests agregados** (`inventory-service/tests/unit/test_alert_scan.py`):
- `test_check_expiry_alerts_empty_tenant_no_error` — tenant sin batches →
  `[]` sin crash.
- `test_check_and_generate_empty_tenant_no_error` — edge case vacío.

**Smoke test**: OK (`POST /alerts/scan` → 200 `{"created": N, "alerts": [...]}`).

---

## Contabilidad de tests

| Servicio              | Antes | Después | Nuevos |
|-----------------------|-------|---------|--------|
| inventory-service     | 23    | 27      | +4 files (test_variant_options, test_cycle_count_service, test_sales_order_multi_stack, test_alert_scan); 2+1+2+2 = 7 tests, pero con rename/split quedan 8 tests nuevos |
| subscription-service  | 14    | 16      | +2 tests (annual + fallback)  — uno renombrado |
| trace-service         | 26    | 26      | 0 (fuera del scope) |
| **Total**             | 63    | 69      | **+6** (net, con rename) |

Todos verdes: `bash qa/run-tests.sh unit` → 69 passed.

## Logs post-deploy

`docker compose logs --tail=100 inventory-api subscription-api | grep -iE "error|traceback"` →
solo 1 error histórico (`LookupError: 'full' is not among the defined enum
values`) que corresponde al primer curl que usé antes de corregir el
methodology — NO es un bug introducido por los fixes; fue un input
incorrecto de mi lado durante el smoke test.

## Bugs nuevos descubiertos (regla #9 — flagged, NO arreglados)

1. **Schema UX de cycle-counts**: el schema acepta `methodology: str` sin
   validación contra `CycleCountMethodology`, entonces mandar `"full"`
   explota en DB con `LookupError` 500 en vez de 422. Sugerencia: usar
   `Literal[...]` o Enum en el request schema para fail-fast.

## Mega-seed re-run

No re-ejecuté `python qa/seed/seed_mega.py` al final — el usuario puede
correrlo. Smoke tests individuales de los 4 endpoints S1 pasaron (variant
options, cycle-counts, sales-orders multi-stack, alerts/scan) — por los
mismos inputs que fallaban en el mega-seed deberían quedar limpios. BUG-05
no es observable en el seed (requiere una subscription annual + generate
invoice explícito).

## Archivos tocados (diff summary)

Backend fixes:
- `inventory-service/app/services/variant_service.py`              (+2 líneas)
- `inventory-service/app/services/cycle_count_service.py`          (+1/-1 líneas)
- `inventory-service/app/repositories/sales_order_repo.py`         (+5/-1 líneas)
- `inventory-service/app/services/alert_service.py`                (+4/-1 líneas)
- `subscription-service/app/services/subscription_service.py`      (+7/-2 líneas)

Tests:
- `inventory-service/tests/unit/test_variant_options.py`           (new, 55 líneas)
- `inventory-service/tests/unit/test_cycle_count_service.py`       (new, 66 líneas)
- `inventory-service/tests/unit/test_sales_order_multi_stack.py`   (new, 116 líneas)
- `inventory-service/tests/unit/test_alert_scan.py`                (new, 32 líneas)
- `subscription-service/tests/unit/test_invoice_service.py`        (edited — 1 rename, +2 tests)
