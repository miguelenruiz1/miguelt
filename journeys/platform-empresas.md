# Journey: Plataforma → Empresas

> Superuser admin console para gestionar tenants (empresas clientes) de la
> plataforma SaaS Trace. Cubre listado, detalle (5 tabs) y onboarding.
> Fecha de análisis: 2026-04-15. Basado en lectura directa del código,
> no en documentación previa.

## Contexto

La sección **Empresas** (`/platform/tenants`) es el CRM interno que usa el
equipo de Trace para operar la plataforma: dar de alta clientes nuevos,
revisar quién está al día con el pago, cambiar planes, generar facturas y
links de cobro, y cancelar/reactivar suscripciones. **No** es una sección
que vea el cliente final — es exclusivamente para usuarios con
`is_superuser=true`.

Las rutas viven todas bajo `<ProtectedRoute superuserOnly>` (ver
`front-trace/src/App.tsx:304-347` y
`front-trace/src/components/auth/ProtectedRoute.tsx:40`), de modo que un
admin de tenant normal no puede acceder aunque conozca la URL.

El backend que atiende esta sección vive en **subscription-service** bajo
`/api/v1/platform/*` (router
`subscription-service/app/api/routers/platform.py`, servicio
`subscription-service/app/services/platform_service.py`). La autorización
se hace con un dep custom `_require_superuser` (`platform.py:19`) que lee
`current_user["is_superuser"]` resuelto vía JWT decode + cache Redis
(`app/api/deps.py:get_current_user`).

## Personas

- **Ana — Ops Manager de Trace (superuser).** Vive en esta sección. Todos
  los días revisa mora, onboardea clientes nuevos salidos de demo, genera
  links de pago para cerrar trials, y cuando un cliente pide cambio de plan
  lo ejecuta desde aquí.
- **Diego — CFO de Trace (superuser).** Usa principalmente el tab
  **Facturas** para conciliar ingresos y el **Resumen** para ver MRR por
  tenant. No toca acciones destructivas.
- **Sofía — Customer Success (superuser "lite", teóricamente).** Hoy, con
  los permisos actuales, ve exactamente lo mismo que Ana. No hay un rol
  intermedio "read-only platform" — o sos superuser, o no ves nada.

## Flujos principales

### 1. Onboardear un nuevo cliente

**Disparador**: cliente firmó contrato / terminó demo y toca darlo de alta.

1. Ana entra al sidebar → sección "Plataforma" (`Sidebar.tsx:507`,
   `NavItem to="/platform/tenants"` → label "Empresas").
2. En `PlatformTenantsPage` click botón **"Nueva empresa"**
   (`PlatformTenantsPage.tsx:38-43`, `Link to="/platform/onboard"`).
3. Completa el wizard (`PlatformOnboardPage.tsx`):
   - **Datos de la empresa** (`:93-135`): nombre visible, tenant_id slug
     (auto-derivado del nombre con `slugify()` en `:309-317` — lowercase,
     sin acentos, sólo `[a-z0-9-]`, max 50 chars), notas libres.
   - **Usuario administrador** (`:138-196`): nombre completo, email,
     password (min 6 chars, validado solo en frontend con `minLength={6}`).
     El `username` se deriva de `email.split('@')[0]` al llamar al backend
     (lo hace `platform_service.py:632`), **el wizard no lo muestra**.
   - **Plan de suscripción** (`:199-250`): grid 2×2 con los planes que
     devuelve `subscriptionApi.plans.list()` filtrados por
     `is_active && !is_archived` (`:42`). Default: `free`. Ciclo de
     facturación: `monthly` | `annual`.
   - **Módulos a activar** (`:253-279`): chips de 5 slugs:
     `logistics, inventory, compliance, production, ai-analysis`
     (constante `AVAILABLE_MODULES` en `:11`).
4. Submit → `POST /api/v1/platform/tenants/onboard` → `onboard_tenant()`
   en `platform_service.py:598-725`. La tx hace en orden:
   1. **Check duplicado**: `sub_repo.get_by_tenant(tenant_id)` → si ya
      tiene suscripción, lanza `ValueError` → el router lo traduce a
      `HTTP 409 Conflict` (`platform.py:147-148`).
   2. **Registrar admin en user-service**: `POST
      {USER_SERVICE_URL}/api/v1/auth/register` con
      `X-Tenant-Id: <tenant_id>`. Si `201` → usuario creado; si `409` o
      "already exists" en body → **continúa sin error** (log info,
      `platform_service.py:642-643`); cualquier otro status → aborta con
      `ValueError`.
   3. **Crear Subscription** local: status=`active`, period_start=now,
      period_end=now+30d (o +365d si annual), `plan_id` resuelto por slug.
      Si el plan no existe → 404.
   4. **Emitir SubscriptionEvent** `created` con `source=platform_onboard`
      y `admin_email`, `company_name` en `data`.
   5. **Activar módulos**: upsert en `tenant_module_activations` (reactiva
      si ya existía desactivado).
5. Respuesta 201 → el hook `useOnboardTenant` hace
   `invalidateQueries(['platform'])` (`usePlatform.ts:60`) → navegar a
   `/platform/tenants/:id` (`PlatformOnboardPage.tsx:72`).
6. Edge cases detectados:
   - **Email ya existe en user-service** (`platform_service.py:642`): el
     código lo silencia asumiendo idempotencia, pero NO valida que el
     usuario existente sea del mismo tenant. Si un email está registrado en
     otro tenant, el onboarding igual crea la subscription al nuevo
     tenant_id, y ese admin queda huérfano: la suscripción nueva no tiene
     usuario. **[BUG-A, severidad alta]**.
   - **Fallo de user-service tras éxito parcial**: si register devuelve
     `201` pero el commit local falla (constraint, network), queda un user
     en user-service sin subscription. No hay compensación/rollback
     (`platform_service.py:626-667`). **[BUG-B, severidad media]**.
   - **Plan inexistente**: 404 con body en español ("Plan 'xxx' no
     encontrado"), pero la UI solo renderiza `(onboard.error as
     Error).message` (`PlatformOnboardPage.tsx:296`) — el mensaje del
     backend se pierde si el cliente http no lo propaga (ver
     `platform-api.ts`).
   - **Slug duplicado**: si el tenant ya tiene subscription → 409 con
     detail "Tenant 'x' ya tiene una suscripción activa"
     (`platform_service.py:621`).
   - **Módulos inválidos**: NO hay validación. `compliance`, `production`,
     `ai-analysis` se insertan felizmente en `tenant_module_activations`
     pero ningún servicio backend los consulta. Son filas muertas.
     **[BUG-C, severidad media — sección "Qué NO soporta aún"]**.

### 2. Revisar cobros atrasados

**No se hace directamente desde `/platform/tenants`**, sino desde
`/platform/sales` (`PlatformSalesPage.tsx`), que llama a `GET
/api/v1/platform/sales` → `get_sales_metrics()`
(`platform_service.py:502-594`). El servicio devuelve 5 buckets:
`upcoming_renewals`, `overdue` (period_end < now y status
active|past_due), `recently_canceled`, `open_invoices` y totales.

Desde `PlatformTenantsPage` sí se puede filtrar por `status=past_due` en
el `<select>` (`PlatformTenantsPage.tsx:66`), pero el listado NO muestra
la columna period_end; Ana tiene que abrir el detalle para ver cuándo
venció.

Flujo típico:
1. Ana filtra por estado = **En mora** (`PlatformTenantsPage.tsx:66`).
2. Entra al detalle del tenant con más días de mora.
3. Tab **Acciones** → **"Generar Link de Pago"**
   (`PlatformTenantDetailPage.tsx:281-289`).
4. Copia el link al clipboard (`:304`) y lo pega en un WhatsApp/email
   manual al contacto del cliente.

**Gaps**:
- No hay columna "days overdue" ni orden por mora más vieja en el listado.
- No hay acción bulk (seleccionar 10 tenants y mandar 10 links de una).
- `PlatformSalesPage` muestra el bucket pero no tiene botón "generar link"
  desde ahí — hay que entrar uno por uno.

### 3. Cambiar plan a un tenant

1. `/platform/tenants/:id` → tab **Acciones**
   (`PlatformTenantDetailPage.tsx:208-236`).
2. La UI renderiza un chip por cada plan activo de `useQuery(['plans'])`
   (`:65-69`) — mismo endpoint público que usa el onboard.
3. Click en un plan distinto al actual → `changePlan.mutate(p.slug)` →
   `POST /api/v1/platform/tenants/:id/change-plan`.
4. Backend `change_tenant_plan()` (`platform_service.py:729-761`):
   - Resuelve sub actual, resuelve plan nuevo por slug.
   - `update(sub, {plan_id, status=ACTIVE})` → **esto fuerza status a
     active** siempre, aunque el tenant estuviera `past_due`, `canceled`
     o `expired`. **[BUG-D, severidad alta]**: cambiar plan revive cuentas
     canceladas sin cobrar nada y sin emitir event `reactivated`, solo
     `plan_changed`.
   - No hay proration, no hay invoice diferencia.
   - No valida que el plan destino esté activo (`is_active && !is_archived`);
     solo el frontend filtra (`PlatformTenantDetailPage.tsx:89`).
5. onSuccess invalida `['platform','tenant',id]` y `['platform','dashboard']`
   (`usePlatform.ts:70-71`). La UI muestra "Plan cambiado" en verde 2s
   (`PlatformTenantDetailPage.tsx:233-235`).

### 4. Suspender / reactivar una suscripción

**Suspender no existe** — solo `cancel`. El botón "Cancelar Suscripción"
(`PlatformTenantDetailPage.tsx:356-362`) abre un textarea inline con un
botón "Confirmar Cancelación" que requiere `reason.trim().length >= 10`
(validación solo frontend `:343`).

Flujo:
1. Tab **Acciones** → scroll al último card.
2. Si `sub.status !== 'canceled'` muestra botón rojo; si `=== 'canceled'`
   muestra botón verde **Reactivar**.
3. Click Cancelar → `showCancelConfirm=true` → textarea inline con mín.
   10 chars (`:333-339`).
4. Confirm → `cancelSub.mutate(reason)` → `POST
   /api/v1/platform/tenants/:id/cancel` con body
   `{reason: string|null}`. Backend NO valida longitud del reason
   (`platform.py:60-61` — `reason: str | None = None`) — **solo el
   frontend impone los 10 chars**. Desde curl se puede mandar string
   vacío.
5. `cancel_tenant_subscription()` (`platform_service.py:851-874`):
   - status=`canceled`, `canceled_at=now`, `cancellation_reason=reason`.
   - Event `canceled` con `source=platform_admin`.
   - **No corta acceso inmediatamente.** `trace-service`,
     `inventory-service`, etc. siguen respondiendo hasta que se ejecute el
     hourly `check_expirations` o el cache TTL expire. Los chequeos de
     módulo (`require_inventory_module`) leen
     `module:{tenant}:inventory` en Redis con TTL 300s.
6. Reactivar (`reactivate_tenant_subscription`, `:878-902`):
   - status=`active`, `canceled_at=None`, `cancellation_reason=None`.
   - **`current_period_end = now + 30d` siempre**, sin importar que el
     ciclo original fuera `annual`. **[BUG-E, severidad media]**.
   - Event `reactivated`.
   - No genera factura nueva.

### 5. Generar factura manual

1. Tab **Acciones** → card "Facturación"
   (`PlatformTenantDetailPage.tsx:268-295`) → botón **Generar Factura**.
2. `generateInvoice.mutate()` → `POST
   /api/v1/platform/tenants/:id/generate-invoice`.
3. Backend `generate_tenant_invoice()` (`platform_service.py:805-847`):
   - Toma `sub.plan.price_monthly` como amount — **incluso si
     `billing_cycle = annual`**. No multiplica por 12, no aplica
     `plan.price_annual`. **[BUG-F, severidad alta para clientes
     anuales]**.
   - Invoice number `INV-YYYY-NNNN` vía `invoice_repo.next_invoice_number()`.
   - `status=open`, `period_start/end` copiados de la sub.
   - `line_items=[{description: "{plan.name} — {cycle}", qty:1,
     unit_price, amount}]`.
   - Emite event `invoice_generated` con `invoice_number` y `amount`.
4. UI muestra "Factura INV-2026-0042 generada" en verde
   (`PlatformTenantDetailPage.tsx:291-294`).
5. La factura aparece en el tab **Facturas**. No hay descarga PDF, no hay
   envío por email. Solo existe como row en DB.

### 6. Generar link de pago para cobrar trial / mora

1. Tab **Acciones** → botón **Generar Link de Pago**
   (`PlatformTenantDetailPage.tsx:280-290`).
2. `generatePaymentLinkMut.mutateAsync()` → `POST
   /api/v1/platform/tenants/:id/generate-payment-link`.
3. Backend `generate_payment_link()` (`platform_service.py:906-954`):
   - Genera `token = secrets.token_urlsafe(32)`.
   - Busca invoice `open` más reciente; si no hay, crea una nueva con
     `generate_tenant_invoice()` (misma función que flujo 5 → hereda
     **BUG-F**).
   - **Persiste `{tenant_id, invoice_number, amount}` en Redis con key
     `payment_link:{token}` y TTL 24h — SOLO SI `self.redis` está
     disponible** (`:939-944`, `if self.redis:`). Si Redis está caído, el
     endpoint igual responde 200 con un link que **no va a validar** al
     abrirse. **[BUG-G, severidad alta, silent half-failure]**.
   - Devuelve `{token, invoice_number, amount, currency, plan_name, link}`
     donde `link = /checkout?token={token}&tenant={tenant_id}`.
4. UI (`PlatformTenantDetailPage.tsx:296-314`) muestra el link con prefijo
   `window.location.origin`, botón "Copiar" al clipboard, y metadata
   (plan, monto, factura).
5. El cliente abre el link → `CheckoutPage.tsx` valida token contra el
   endpoint público que lee Redis, y dispara pago por la pasarela activa
   (`active_gateway` en el tab Resumen).

### 7. Activar / desactivar módulo específico

1. Tab **Acciones** → card "Módulos"
   (`PlatformTenantDetailPage.tsx:239-265`).
2. La UI hardcodea `ALL_MODULES = ['logistics', 'inventory']`
   (`PlatformTenantDetailPage.tsx:42`) — inconsistente con los 5 del
   wizard de onboarding. Si un tenant fue onboardeado con
   `compliance`, `production` o `ai-analysis`, **desde aquí Ana no los ve
   ni los puede apagar**. **[BUG-H, severidad media]**.
3. Click un toggle → `toggleModule.mutate({slug, active: !isActive})` →
   `POST /api/v1/platform/tenants/:id/modules/:slug` body `{active: bool}`.
4. Backend `toggle_tenant_module()` (`platform_service.py:765-801`):
   - Upsert en `tenant_module_activations` (crea si no existe, si existe
     toggles `is_active` + timestamps).
   - **NO emite SubscriptionEvent**, a diferencia de cancel/reactivate/
     change-plan. **[BUG-I, severidad baja]**: el tab Eventos nunca
     muestra toggles de módulos, dificulta auditoría.
   - No invalida el cache Redis `module:{tenant}:inventory` (TTL 300s) —
     hasta 5 min de ventana donde el servicio sigue respondiendo con el
     estado viejo. Documentado en memory bajo inventory-service gating.

### 8. Navegación transversal desde listado

- Click en fila desktop (`PlatformTenantsPage.tsx:212-217`) o card mobile
  (`:93-142`) → `/platform/tenants/:tenantId` con `encodeURIComponent`.
- Click en "Empresas" back-link desde detalle
  (`PlatformTenantDetailPage.tsx:96`) → vuelve al listado, pero los
  filtros NO se persisten (están en `useState` local) → se pierden al
  volver. **[BUG-J, severidad baja UX]**.
- `PlatformAnalyticsPage.tsx:193` linkea a `/platform/tenants/:id` desde
  eventos recientes.

## Estados esperados por columna / badge

Fuente: `front-trace/src/lib/status-badges.ts` (export
`SUBSCRIPTION_STATUS_BADGE`) usado en
`PlatformTenantsPage.tsx:7,91,163` y `PlatformTenantDetailPage.tsx:20,88`.

| status | label UI | color |
|---|---|---|
| `active` | Activa | verde |
| `trialing` | Prueba | azul |
| `past_due` | En mora | amber |
| `canceled` | Cancelada | rojo |
| `expired` | Expirada | gris |
| fallback | Expirada | gris (`?? STATUS_BADGE.expired`) |

Badges de **factura** (`PlatformTenantDetailPage.tsx:23-29`):

| invoice.status | color |
|---|---|
| `paid` | verde |
| `open` | azul |
| `draft` | gris |
| `void` | rojo |
| `uncollectible` | amber |

Badges de **licencia** (`PlatformTenantDetailPage.tsx:434-438`):
- `active` → verde, cualquier otro → rojo (binario, no distingue
  `revoked`/`expired`).

Badges de **módulos** en listado (`PlatformTenantsPage.tsx:9-12`):

| module | color |
|---|---|
| `logistics` | primary (verde-trace) |
| `inventory` | naranja |
| otro | gris (fallback) |

## Qué NO soporta aún

- **Suspend real**: solo existe `cancel`. No hay un estado intermedio
  "suspended/pausado" con pausa de billing pero conservando datos.
- **Hard delete / export GDPR**: no hay endpoint DELETE ni "export all
  tenant data". Cancelar deja las filas en DB indefinidamente.
- **Impersonation**: no hay ruta `/platform/tenants/:id/impersonate` ni
  token de impersonación. Si Ana necesita debuggear lo que ve un cliente,
  tiene que pedir credenciales.
- **Búsqueda por nombre de empresa**: el backend solo filtra por
  `tenant_id ilike` (`platform_service.py:209`). `company_name` y `notes`
  se guardan solo en `auth_service/users.company` y `Subscription.notes`,
  nunca se indexan ni se exponen en el listado.
- **Columna "company name"** en el listado: la tabla solo muestra
  tenant_id slug (`PlatformTenantsPage.tsx:172`). Tenants con slugs poco
  descriptivos (`cliente-42`) son opacos.
- **Proration / credit notes** al cambiar plan.
- **Invoice PDF / envío por email**: `generate_tenant_invoice` solo
  inserta row en DB.
- **Bulk actions**: no hay multi-select.
- **Debounce en búsqueda**: cada keystroke dispara query
  (`PlatformTenantsPage.tsx:54`).
- **Módulos fuera de logistics/inventory** (compliance, production,
  ai-analysis): el wizard permite activarlos pero el backend no los
  consume y el detalle no los muestra (ver **BUG-C** y **BUG-H**).
- **Auditoría de toggles de módulos**: no hay events (BUG-I).
- **Vista de `cancellation_reason` destacada**: se guarda pero solo
  aparece escondido en `SubscriptionEvent.data.reason` y
  `sub.cancellation_reason` del detalle (que la UI no muestra — leí los
  4 `dl.space-y-3` del tab Resumen, `PlatformTenantDetailPage.tsx:139-157`
  y `cancellation_reason` no está).
- **Expiración automática de trial**: `/platform/check-expirations`
  existe (`platform.py:291-299`) y corre hourly en background, pero no hay
  botón visible en `/platform/tenants/:id` para ejecutarlo ad-hoc.
- **Role-based access dentro de platform**: todo es superuser o nada. No
  hay "platform-read-only" para Customer Success.

## Bugs encontrados durante el journey

| ID | Severidad | Ubicación | Descripción |
|---|---|---|---|
| BUG-A | Alta | `platform_service.py:642-643` | Onboarding silencia 409 de user-service sin verificar que el user existente pertenezca al tenant → subscription huérfana si el email ya está en otro tenant. |
| BUG-B | Media | `platform_service.py:626-667` | Sin rollback de user-service si la creación local de Subscription falla tras register exitoso. |
| BUG-C | Media | `PlatformOnboardPage.tsx:11` vs `PlatformTenantDetailPage.tsx:42` | Wizard ofrece 5 módulos, detalle solo conoce 2. Los 3 extras se guardan como filas muertas. |
| BUG-D | Alta | `platform_service.py:744-747` | `change_tenant_plan` fuerza `status=active`, reviviendo suscripciones canceladas sin cobrar ni emitir evento `reactivated`. |
| BUG-E | Media | `platform_service.py:888-893` | Reactivar siempre setea `current_period_end = now + 30d` aunque el ciclo fuera `annual`. |
| BUG-F | Alta | `platform_service.py:815,826-830` | `generate_tenant_invoice` cobra `price_monthly` aun para `billing_cycle=annual`. No usa `plan.price_annual`. |
| BUG-G | Alta | `platform_service.py:939-944` | `generate_payment_link` solo persiste el token en Redis si `self.redis` truthy. Si Redis falla, el 200 devuelve un link no-validable. Silent half-failure. |
| BUG-H | Media | `PlatformTenantDetailPage.tsx:42` | `ALL_MODULES` hardcoded a 2; módulos compliance/production/ai-analysis no se pueden apagar desde el detalle. |
| BUG-I | Baja | `platform_service.py:765-801` | `toggle_tenant_module` no emite SubscriptionEvent → tab Eventos nunca muestra toggles, dificulta auditoría. |
| BUG-J | Baja UX | `PlatformTenantsPage.tsx:15-25` | Filtros search/status/page en `useState` local → se pierden al navegar a detalle y volver. |
| BUG-K | Baja | `PlatformTenantDetailPage.tsx:336-339` vs `platform.py:60` | Validación `reason.length >= 10` solo en frontend; backend acepta null/empty. Curl bypass trivial. |
| BUG-L | Baja | `PlatformTenantDetailPage.tsx:139-157` | Tab Resumen nunca muestra `sub.cancellation_reason` aunque el backend lo devuelve (`platform_service.py:340`). |
| BUG-M | Media | `platform_service.py:785,791` | Toggle módulo no invalida cache Redis `module:{tenant}:{slug}` (TTL 300s) → hasta 5 min de ventana donde el servicio responde con estado viejo. |
| BUG-N | Baja | `PlatformTenantsPage.tsx:50-56` | Search sin debounce: una query por keystroke. |
| BUG-O | Baja | `PlatformOnboardPage.tsx:183` | Password `minLength=6` solo en HTML; no hay política (mayúsculas, dígitos, longitud mínima razonable). Backend user-service define el mínimo real. |

## Archivos clave (paths absolutos)

Backend:
- `C:\Users\me.ruiz42\Desktop\Trace\subscription-service\app\api\routers\platform.py`
- `C:\Users\me.ruiz42\Desktop\Trace\subscription-service\app\services\platform_service.py`
- `C:\Users\me.ruiz42\Desktop\Trace\subscription-service\app\repositories\subscription_repo.py`
- `C:\Users\me.ruiz42\Desktop\Trace\subscription-service\app\repositories\invoice_repo.py`
- `C:\Users\me.ruiz42\Desktop\Trace\subscription-service\app\repositories\event_repo.py`
- `C:\Users\me.ruiz42\Desktop\Trace\subscription-service\app\api\deps.py` (get_current_user, superuser dep)

Frontend:
- `C:\Users\me.ruiz42\Desktop\Trace\front-trace\src\pages\platform\PlatformTenantsPage.tsx`
- `C:\Users\me.ruiz42\Desktop\Trace\front-trace\src\pages\platform\PlatformTenantDetailPage.tsx`
- `C:\Users\me.ruiz42\Desktop\Trace\front-trace\src\pages\platform\PlatformOnboardPage.tsx`
- `C:\Users\me.ruiz42\Desktop\Trace\front-trace\src\hooks\usePlatform.ts`
- `C:\Users\me.ruiz42\Desktop\Trace\front-trace\src\lib\platform-api.ts`
- `C:\Users\me.ruiz42\Desktop\Trace\front-trace\src\types\platform.ts`
- `C:\Users\me.ruiz42\Desktop\Trace\front-trace\src\components\auth\ProtectedRoute.tsx`
- `C:\Users\me.ruiz42\Desktop\Trace\front-trace\src\components\layout\Sidebar.tsx` (sección "Plataforma")
- `C:\Users\me.ruiz42\Desktop\Trace\front-trace\src\App.tsx:304-347` (rutas `<ProtectedRoute superuserOnly>`)
- `C:\Users\me.ruiz42\Desktop\Trace\front-trace\src\lib\status-badges.ts` (SUBSCRIPTION_STATUS_BADGE)
