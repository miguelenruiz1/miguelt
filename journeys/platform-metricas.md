# Journey: Plataforma → Métricas (Dashboard, Analítica, Ventas)

> Scope: las 3 pantallas que usa el equipo interno de Trace (is_superuser)
> para monitorear el negocio SaaS. No son vistas para clientes finales.
>
> Archivos base:
> - Frontend: `front-trace/src/pages/platform/PlatformDashboardPage.tsx`,
>   `PlatformAnalyticsPage.tsx`, `PlatformSalesPage.tsx`.
> - Hooks: `front-trace/src/hooks/usePlatform.ts`.
> - API client: `front-trace/src/lib/platform-api.ts`.
> - Backend: `subscription-service/app/services/platform_service.py`.
> - Endpoints: `/api/v1/platform/{dashboard,analytics,sales}` vía gateway :9000.

---

## Persona principal

**Ana**, Ops Lead de Trace (rol `is_superuser=True`). Cada lunes 9am abre el
submenu "Plataforma" en el sidebar y recorre 3 pantallas en este orden:

1. `/platform` — "¿cómo arrancamos el mes? MRR, churn, nuevas empresas."
2. `/platform/analytics` — "¿es tendencia o ruido? 6 meses de data."
3. `/platform/ventas` — "¿a quién tengo que llamar hoy para cobrar?"

Cada pantalla responde a una pregunta distinta sobre los mismos datos: el
dashboard es el estado actual, analítica es la serie temporal, ventas es la
cola accionable.

---

## 1. Panel Ejecutivo — `/platform`

### Qué ve Ana al entrar

Orden real de bloques en `PlatformDashboardPage.tsx`:

| # | Bloque | Archivo:línea |
|---|--------|---------------|
| 1 | Breadcrumb "Plataforma → Panel Ejecutivo" | L80-86 |
| 2 | Header "Panel de Plataforma" + botones a `/platform/tenants` y `/platform/analytics` | L89-108 |
| 3 | **KPI fila 1** (4 cards): Empresas, MRR, Ingreso del Mes, Churn Rate | L111-140 |
| 4 | **KPI fila 2** (4 cards): Suscripciones Activas, En Prueba, Licencias Activas, Módulos Activados | L143-148 |
| 5 | Charts: pie **Distribución por Estado** + barras **Distribución por Plan** | L151-199 |
| 6 | **Adopción de Módulos** — grid 2×4 con conteo de empresas por módulo | L202-218 |
| 7 | Alerta amarilla "N empresas tienen pagos vencidos" (solo si `past_due > 0`) | L221-231 |

KPIs de la primera fila tienen subtext calculado en cliente:
- "Empresas": `total_tenants`, subtext `new_this_month nuevas este mes`.
- "MRR": formato `es-CO`, subtext `ARR: $X`.
- "Ingreso del Mes": subtext = `revDelta` calculado en L65-67
  (`(this - last) / last * 100`). Si `revenue_last_month == 0` → no muestra delta.
- "Churn Rate": icono cambia de `TrendingUp` (verde) a `TrendingDown` (rojo)
  cuando `churn_rate > 5` (threshold hardcoded L136-137).

### Cómo se calculan los números

`platform_service.py::get_dashboard` (L45-187):

| KPI | Fuente |
|-----|--------|
| `total_tenants` | suma de `subscriptions` agrupadas por status (L51-62). NO cuenta tenants sin suscripción. |
| `active / trialing / past_due / canceled / expired` | `status_counts` por enum `SubscriptionStatus` (L57-61). |
| `mrr` | `SUM(plans.price_monthly)` JOIN subscriptions WHERE `status == active` AND `price_monthly > 0` (L65-73). **No incluye `trialing`** — es solo ingreso realmente cobrable. |
| `arr` | `mrr * 12` (L177). Plano, sin considerar descuentos anuales. |
| `revenue_this_month` | `SUM(invoices.amount)` WHERE `status=paid` AND `paid_at >= month_start` (L76-79). |
| `revenue_last_month` | mismo filtro para mes anterior (L82-89). |
| `new_this_month` | `COUNT(subscriptions)` WHERE `created_at >= month_start` (L92-95). Cuenta TODAS las creaciones, incluyendo las ya canceladas. |
| `canceled_this_month` | `COUNT` WHERE `canceled_at >= month_start` AND `status=canceled` (L98-104). |
| `churn_rate` | `canceled_this_month / (active + canceled_this_month) * 100`, redondeado a 2 decimales (L107-108). |
| `active_licenses` | `COUNT(license_keys)` WHERE `status=active` (L111-114). |
| `active_modules` | `COUNT(tenant_module_activations)` WHERE `is_active=true` (L117-120). Suma todas las activaciones, no distintas por módulo. |
| `plan_breakdown` | GROUP BY Plan para suscripciones `active ∪ trialing`, devuelve `{slug, name, count, mrr}` (L123-146). |
| `module_adoption` | GROUP BY `module_slug` para activaciones `is_active=true` cuyo tenant **tiene suscripción** (subquery L157-159). |

### Bugs / limitaciones

- **`churn_rate` denominador débil** (`platform_service.py:107-108`): usa
  `active + canceled_this_month`. Definición estándar de churn mensual es
  `canceled_this_month / active_at_start_of_month`. Con esta fórmula, cualquier
  mes con altas netas altas subestima el churn.
- **`new_this_month` no filtra status** (L92-95): cuenta altas aun si ya se
  cancelaron en el mismo mes → puede contradecir "canceladas este mes" en
  dashboards parciales.
- **`arr = mrr * 12`** (L177): ignora suscripciones anuales, no pondera
  `price_annual` del Plan.
- **Threshold de churn hardcoded a 5%** (`PlatformDashboardPage.tsx:136-137`):
  no es configurable.
- **`STATUS_LABELS` declarado pero no usado en dashboard** (L17-23) — el pie
  chart usa labels hardcoded en L70-74. Duplicación.
- **`active_modules` cuenta filas, no módulos distintos** (L117-120): si el
  catálogo tiene 2 módulos (logistics, inventory) y 50 tenants los activan a
  ambos, devuelve 100. El label "Módulos Activados" puede leerse como "cuántos
  módulos" y confundir.
- **Alerta de "pagos vencidos" usa `past_due` count** (L221) pero la pantalla
  de Ventas calcula overdue con otro criterio (`period_end < now` y status
  `active` O `past_due`) — los 2 números pueden no coincidir.

---

## 2. Analítica — `/platform/analytics`

### Qué ve Ana al entrar

Orden real en `PlatformAnalyticsPage.tsx`:

| # | Bloque | Archivo:línea |
|---|--------|---------------|
| 1 | Header con back-link a `/platform` + selector de rango (3/6/12 meses) | L49-67 |
| 2 | **Crecimiento de Suscripciones** — LineChart de `total_subscriptions` por mes | L70-90 |
| 3 | **Ingresos Mensuales** — BarChart de `revenue` por mes (verde) | L93-106 |
| 4 | Fila: **Distribución por Estado** (pie) + **Adopción de Módulos** (progress bars con %) | L109-173 |
| 5 | **Eventos Recientes** — lista de 20 últimos `subscription_events` con link al tenant | L176-208 |

Selector `months` → hook `usePlatformAnalytics(months)` (L30) → querystring
`?months=N` al endpoint (`platform-api.ts:53`).

### Cómo se calculan los números

`platform_service.py::get_analytics(months)` (L407-498):

| Campo | Fuente |
|-------|--------|
| `subscription_growth` | Loop de N meses (L411-425). Por cada mes: `COUNT(subscriptions)` WHERE `created_at <= month_end`. **Es acumulado** (conteo total histórico en ese punto), no altas mensuales. |
| `revenue_trend` | Loop de N meses (L427-445). Por cada mes: `SUM(invoices.amount)` WHERE `status=paid` AND `paid_at ∈ [m_start, next_month)`. |
| `status_distribution` | GROUP BY `subscriptions.status` (L447-454). Snapshot, **no** filtrado por rango. |
| `module_adoption` | GROUP BY `module_slug` (L457-473). Devuelve `{slug, active, total}`. Frontend calcula `pct = active/total*100`. **No usa el rango `months`** — es snapshot. |
| `recent_events` | últimos 20 `subscription_events` DESC (L476-480). |

### Bugs / limitaciones

- **`month_dt = now - timedelta(days=30*i)`** (L413): aritmética de 30 días
  por mes es imprecisa para rangos largos (12 meses ≈ 360 días, desalinea
  cuando hay años bisiestos o meses de 31 días). Los labels `%Y-%m` pueden
  repetirse o saltarse mes cuando cae en frontera.
- **Label del mes actual mezcla estrategias** (L415-419): para `i>0` toma el
  primer día del mes (`month_end`), para `i==0` usa `now`. El dato del mes
  actual es parcial pero aparece como si fuera completo en la misma serie.
- **`subscription_growth` es acumulado, no mensual** (L421-424). Un usuario
  puede leerlo como "altas por mes" cuando es "suscripciones totales al
  corte". Falta un chart separado de altas netas.
- **`status_distribution` y `module_adoption` ignoran el filtro `months`**
  (L447+, L457+): el selector del header solo afecta 2 de los 4 bloques. La
  UX sugiere filtrado global.
- **`total` en `module_adoption`** (L464) cuenta filas incluyendo desactivadas
  históricamente → `pct` puede ser engañoso si hubo muchas bajas.
- **Sin export CSV ni drill-down por empresa** desde los charts.

---

## 3. Ventas — `/platform/ventas`

Pantalla crítica para cobranza. Es la única de las 3 con `refetchInterval:
30_000` (`usePlatform.ts:49`) — se refresca automática cada 30s.

### Qué ve Ana al entrar

Orden real en `PlatformSalesPage.tsx`:

| # | Bloque | Archivo:línea |
|---|--------|---------------|
| 1 | Header con back-link + título "Ventas & Cobros" | L40-48 |
| 2 | **4 KPIs**: Renovaciones Próximas, Vencidas, Facturado Pendiente, Bajas Este Mes | L51-80 |
| 3 | **Renovaciones Próximas (30 días)** — lista con días restantes (rojo si ≤7) | L83-127 |
| 4 | **Vencidas — Acción Requerida** (card rojo, solo si `overdue.length > 0`) — días vencidos, link al tenant | L130-164 |
| 5 | **Facturas Pendientes** — tabla con invoice_number, empresa, monto, fecha | L167-206 |
| 6 | **Bajas Recientes** (solo si `recently_canceled.length > 0`) — incluye `cancellation_reason` | L209-237 |

KPIs:
- "Renovaciones Próximas" (L52-58): count de subs con `period_end` en los
  próximos 30 días.
- "Vencidas" (L60-65): count de subs con período ya vencido. Color cambia
  (`red-500` si >0, `emerald-500` si 0).
- "Facturado Pendiente" (L66-72): `total_open_amount` formateado `es-CO` +
  conteo de facturas abiertas.
- "Bajas Este Mes" (L74-79): `canceled_this_month_count` + subtext con
  `paid_this_month_count`.

Cálculos en cliente:
- `daysLeft` (L94-96): `ceil((period_end - Date.now()) / 86_400_000)`.
  Threshold rojo: `daysLeft <= 7` (L111).
- `daysOverdue` (L139-141): simétrico, `Date.now() - period_end`.

### Cómo se calculan los números

`platform_service.py::get_sales_metrics` (L502-594):

| Campo | Fuente |
|-------|--------|
| `upcoming_renewals` | `status=active` AND `period_end ∈ (now, now+30d]`, ORDER `period_end ASC` (L507-516). |
| `overdue` | `status ∈ {active, past_due}` AND `period_end < now`, ORDER `period_end ASC` (L519-527). Incluye `active` — es el corazón del flow: facturaste, venció y seguís activo sin cobrar. |
| `recently_canceled` | `status=canceled` AND `canceled_at >= month_start` (L530-538). |
| `open_invoices` | `invoice.status=open` DESC, LIMIT 50 (L541-546). |
| `paid_this_month_count` | `COUNT(invoices)` `status=paid` AND `paid_at >= month_start` (L549-552). |
| `total_open_amount` | `SUM(invoices.amount)` `status=open` (L554-557). |
| `upcoming_renewal_count / overdue_count / canceled_this_month_count` | `len(...)` del array (L591-593). |

### Bugs / limitaciones

- **"Bajas Este Mes" filtrado desde `month_start`** (L535) pero el label UI
  dice "Este Mes" — OK. Pero el KPI del Dashboard usa el mismo denominador y
  puede diferir si la query corre en zonas horarias distintas (ambos usan
  `datetime.now(timezone.utc).replace(day=1)`, así que consistente en UTC —
  el usuario en GMT-5 verá el cambio a medianoche UTC, no local).
- **`overdue` devuelve subs `active` con `period_end < now`** (L523-525):
  depende de un job externo (no visible en este repo) que transicione a
  `past_due` automáticamente. Si ese job no existe o falla, `overdue` se
  infla — y el KPI "past_due" del dashboard queda en 0 mientras esta pantalla
  muestra 20 vencidas. Inconsistencia potencial entre pantallas.
- **`open_invoices` tiene LIMIT 50** (L545) pero `total_open_amount` suma
  todo (L554-557). El KPI puede decir "$X total" y la tabla mostrar solo 50
  filas que suman menos. No hay paginación.
- **Sin acción "Enviar recordatorio" ni "Marcar pagada"** desde esta
  pantalla. Ana ve la lista pero tiene que ir a `/platform/tenants/{id}`
  para actuar. El prop existente `useGeneratePaymentLink` (`usePlatform.ts:98`)
  no está conectado en esta UI.
- **`daysOverdue` en cliente** (L139-141): si el server-clock y el
  browser-clock están desincronizados, los días vencidos pueden mostrar 1 día
  de diferencia entre usuarios.
- **Orden de "Bajas Recientes" por `canceled_at DESC`** OK, pero no limita
  — si un mes hay 200 bajas, renderiza todas.

---

## Conexión entre las 3 pantallas

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  /platform      │     │  /analytics     │     │  /ventas        │
│  (estado hoy)   │────▶│  (tendencia)    │────▶│  (accionable)   │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ MRR: $X         │     │ Revenue trend   │     │ Open invoices:  │
│                 │     │ 6 meses         │     │ facturas no     │
│                 │     │                 │     │ cobradas        │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ Churn: N%       │     │ Growth curve    │     │ Recently        │
│                 │     │ + status dist   │     │ canceled list   │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ past_due: N     │     │ Status pie      │     │ Overdue list    │
│ (alerta)        │     │ (snapshot)      │     │ (quién llamar)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         └───── drill-down ──────┴────── drill-down ─────┘
                                 ▼
                   /platform/tenants/{tenant_id}
```

- **Dashboard** responde "¿cómo estamos ahora?" con KPIs agregados.
- **Analítica** responde "¿va bien la tendencia?" con series de N meses.
- **Ventas** responde "¿qué hago hoy?" con colas accionables (renovaciones,
  vencidos, facturas abiertas, bajas).

Todas linkean a `/platform/tenants/{tenant_id}` para el drill-down. Dashboard
además tiene botón directo a `/platform/analytics` (L101-106 dashboard).

---

## Gaps vs. enterprise-grade

| Métrica / Feature | Estado | Nota |
|-------------------|--------|------|
| LTV (Lifetime Value) | ✗ | No hay cálculo; requiere promedio de permanencia. |
| CAC (Customer Acquisition Cost) | ✗ | No se trackea inversión en marketing. |
| Payback Period | ✗ | Derivado de CAC, no calculable hoy. |
| Cohorts (retention por mes de alta) | ✗ | Faltante. Es estándar en SaaS metrics. |
| Net Revenue Retention (NRR) | ✗ | Requiere trackear expansiones/contracciones de plan. |
| Quick Ratio | ✗ | `(new MRR + expansion) / (churn + contraction)`. |
| Export CSV de cualquier KPI | ✗ | `InventoryReportsPage` tiene el patrón; acá no. |
| Drill-down tenant desde KPI | ⚠ parcial | Vía links a `/platform/tenants` pero no clickeando el KPI en sí. |
| Filtro por rango en Dashboard | ✗ | Solo en Analytics. Dashboard siempre muestra "hoy". |
| Comparativa YoY en Analytics | ✗ | Solo últimos N meses, sin overlay año anterior. |
| Alertas proactivas (email/slack) | ✗ | La card de `past_due > 0` es solo visual. |
| `is_superuser` check | ✓ | En `ProtectedRoute` con `superuserOnly` (sidebar solo muestra si superuser). |
| Refetch auto en Ventas | ✓ | 30s polling (`usePlatform.ts:49`). |
| Refetch auto en Dashboard | ⚠ | Solo `staleTime: 30s`, no polling — hay que recargar. |
| MRR por plan (breakdown) | ✓ | `plan_breakdown[].mrr` calculado backend. |
| Trialing contribuye a MRR | ✗ | Decisión explícita L69: solo `active`. Correcto pero hay que saberlo. |
| Gestión de cobro desde UI | ✗ | Sin botón "enviar recordatorio" o "marcar pagada" en Ventas. |
| Paginación de listas largas | ✗ | `open_invoices` hard-limit 50, el resto sin límite. |
| Auditoría de quién revisó el dashboard | ✗ | No hay `audit_log` de vistas en `/platform`. |

---

## Smoke test manual sugerido

Prerequisitos: tener un usuario `is_superuser=True` y su `access_token` JWT.

```bash
# 1. Exportar token (reemplazar con un JWT real de superuser)
TOKEN="eyJhbGciOi..."

# 2. Dashboard — debe devolver 200 con 12+ campos numéricos
docker exec trace-gateway curl -s -w "\nHTTP %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:9000/api/v1/platform/dashboard | head -100

# 3. Analytics (6 meses default) — debe devolver 4 arrays no vacíos
docker exec trace-gateway curl -s -w "\nHTTP %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost:9000/api/v1/platform/analytics?months=6" | head -100

# 4. Sales — debe devolver upcoming_renewals, overdue, open_invoices arrays
docker exec trace-gateway curl -s -w "\nHTTP %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:9000/api/v1/platform/sales | head -100
```

**Verificaciones esperadas**:
- Los 3 endpoints devuelven `HTTP 200`.
- Dashboard: `total_tenants == active + trialing + past_due + canceled + expired`
  (chequeo de consistencia — la suma debe cuadrar porque backend la calcula
  así, L62).
- Dashboard: `arr == mrr * 12` (exacto, L177).
- Sales: `upcoming_renewal_count == upcoming_renewals.length` (L591,
  redundante con el array; ambos deben coincidir).
- Analytics con `months=3` vs `months=12`: los arrays `subscription_growth`
  y `revenue_trend` deben tener length 3 y 12 respectivamente; los de
  `status_distribution` y `module_adoption` son iguales en ambos (bug
  documentado arriba).

**Smoke test UI** (en browser logueado como superuser):
1. Ir a `/platform` — verificar que los 8 KPI cards cargan sin `NaN`.
2. Alternar `/platform/analytics` selector de 3→6→12 y ver que los charts
   de crecimiento/ingresos cambian (si los otros 2 no cambian → confirmar
   bug documentado).
3. Ir a `/platform/ventas` — si hay `overdue > 0` y `past_due == 0` en
   dashboard, hay desincronía (job de transición de status no corre).
4. Click en tenant_id desde cualquier lista → debe abrir
   `/platform/tenants/{id}` sin 404.
