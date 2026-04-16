# Journey: Plataforma — Operaciones (Team, Users, CMS, AI, Marketplace, Pagos, Checkout)

> Journey de las páginas "de operación" del panel de Plataforma SaaS de Trace
> más los flujos públicos que las tocan (Marketplace + Checkout con Wompi).
> Tras la limpieza reciente el backend de pagos soporta **solo Wompi** y se
> eliminó la feature de "webhooks por empresa" (integration-service).

## Personas

- **Ana** — Superuser ops de Trace (`is_superuser = true`). Administra Team,
  Users, CMS, AI Settings y la pasarela de cobro. Vive en el tenant interno
  `platform`.
- **Bruno** — Admin de un tenant cliente (`is_superuser = false`, rol
  `administrador` con `subscription.manage`). Entra a `/marketplace` para
  activar módulos y al `/checkout` para pagarlos.
- **Carla** — Operadora dentro del tenant de Bruno (rol de negocio, sin
  `subscription.manage`). No ve Marketplace como togglable y jamás ve
  /platform/*.

---

## 1. Gestión del equipo interno de Trace

### 1.1 Team — `/platform/team`

**Archivo**: `front-trace/src/pages/platform/PlatformTeamPage.tsx`

Flujo de Ana:
1. Entra vía sidebar "Plataforma → Equipo".
2. Frontend llama `userApi.users.list({ limit: 200 })` — GET
   `user-service /api/v1/users?limit=200` scopeado al tenant del JWT de
   Ana (`platform`). Se muestran hasta 200 usuarios.
3. Split visual: tabla "Operadores de Plataforma (Superusuarios)" arriba y
   "Usuarios Regulares" abajo, filtrables por el input de búsqueda
   (`PlatformTeamPage.tsx:39-44`, split `:46-47`).
4. Por cada fila:
   - Toggle **"Hacer/Quitar Superusuario"** → `userApi.users.update(id, { is_superuser })`
     → PATCH `user-service /api/v1/users/{id}`
     (`PlatformTeamPage.tsx:26-30`). Deshabilitado para su propia fila
     (`:202-213`).
   - Toggle **"Desactivar/Reactivar"** → POST
     `/api/v1/users/{id}/deactivate` o `/reactivate`
     (`PlatformTeamPage.tsx:32-36`, backend
     `user-service/app/api/routers/users.py:183,196`).

Permisos reales en el backend: el endpoint `GET /api/v1/users` exige
`require_permission("admin.users")` (scopeado al tenant), pero promover a
superusuario se hace con un simple PATCH que acepta `is_superuser` — el
frontend asume que solo Ana accede a esta página, pero el backend **no
tiene un chequeo `_require_superuser` específico** para mutar
`is_superuser`. Ver bugs §6.

### 1.2 Users — `/platform/users`

**Archivo**: `front-trace/src/pages/platform/PlatformUsersPage.tsx`

Flujo de Ana:
1. "Plataforma → Usuarios" en sidebar.
2. Hook `usePlatformUsers({ search, tenant_id, offset, limit: 25 })`
   (`front-trace/src/hooks/usePlatform.ts:128`).
3. Hook llega al gateway → subscription-service
   `/api/v1/platform/users` (superuser-only,
   `subscription-service/app/api/routers/platform.py:250-283`), que **proxy**
   a user-service `/api/v1/users/all` con el bearer token de Ana.
4. user-service
   `user-service/app/api/routers/users.py:93-106` exige `_require_superuser`
   y devuelve `PaginatedResponse[UserResponse]` con búsqueda opcional y
   filtro por `tenant_id`.
5. Desktop muestra tabla (usuario, email, tenant, roles, activo, super,
   creado); móvil renderiza cards; paginación numérica si
   `total > limit` (`PlatformUsersPage.tsx:199-220`).

**Diferencia con Team**: Team permite mutar (toggle super/activo). Users es
**read-only** — no hay acciones por fila, por diseño (auditoría visual
cross-tenant).

---

## 2. CMS de landing pages

### 2.1 Listado — `/platform/cms`

**Archivos**:
- Frontend: `front-trace/src/pages/platform/PlatformCmsPage.tsx`
- Backend: `subscription-service/app/api/routers/cms.py`
- Service: `subscription-service/app/services/cms_service.py`
- Migración: `subscription-service/alembic/versions/010_cms_module.py`

Modelos (`subscription-service/app/db/models.py`):
- `CmsPage` — title, slug UNIQUE, lang, status (`draft|published|archived`),
  `navbar_config`, `footer_config`, SEO fields (`seo_title`,
  `seo_description`, `seo_keywords`, `og_image`, `canonical_url`, `robots`),
  `created_by`, `updated_by`, `published_at`.
- `CmsSection` — FK a page, `block_type`, `config` (JSONB), `position`,
  `anchor_id`, `css_class`, `is_visible`.
- `CmsScript` — tags `<script>` globales o por página (src, inline_code,
  placement `head|body_start|body_end`, load_strategy
  `async|defer|blocking`, is_active).

Flujo de Ana:
1. GET `/api/v1/cms/pages` — lista paginada (superuser-only,
   `cms.py:45-52`). El hook `useCmsPages` setea estado de carga con skeleton.
2. Botón **"Nueva página"** abre modal (`PlatformCmsPage.tsx:205-263`):
   - Inputs: título, slug (auto-slugify del título,
     `:215, :12-18`), idioma (es/en/pt).
   - `useCreateCmsPage` → POST `/api/v1/cms/pages` (`cms.py:55`), redirige a
     `/platform/cms/{id}` con `navigate(…)`
     (`PlatformCmsPage.tsx:51`).
3. Fila con menú 3-puntos → Editar · Ver pública (si published) · Publicar /
   Despublicar · Duplicar · **Eliminar** (con `confirm()` JS —
   `PlatformCmsPage.tsx:181-184`). Ver bugs §6 sobre el click-outside del
   menú.

### 2.2 Editor — `/platform/cms/:pageId`

**Archivo**: `front-trace/src/pages/platform/PlatformCmsEditorPage.tsx`

Tabs (`:426-445`):

**Contenido** (`:448-529`):
- Card de metadatos de la página (título, slug, `navbar_config` como JSON
  textarea, `footer_config` idem). Save → PATCH
  `/api/v1/cms/pages/{id}` con `updatePage.mutate`.
  - **Validación frágil**: parsea navbar/footer con `JSON.parse` envuelto en
    try/catch → `alert('JSON inválido')` (`:328-331`). Un error tipográfico
    descarta **todo** el guardado, incluyendo título y slug.
- Lista de secciones ordenada por `position`
  (`:372`). Cada `SectionEditor` expandible muestra:
  - `GripVertical` visual (sin handler de drag, ver bugs §6).
  - Toggle visibilidad (`is_visible`).
  - Anchor ID, CSS class, y config JSON completo en textarea.
  - Eliminar (con confirm).
- Botón "Agregar sección" abre `AddSectionDialog` con grid de los 11 bloques
  (`HeroBlock`, `FeaturesBlock`, `PricingBlock`, `FaqBlock`,
  `TestimonialsBlock`, `CtaBlock`, `StatsBlock`, `ImageTextBlock`,
  `CountdownBlock`, `LogosBlock`, `CustomHtmlBlock` — de
  `front-trace/src/components/cms/BlockRenderer.tsx` y su carpeta
  `blocks/`). Click en bloque → POST
  `/api/v1/cms/pages/{pageId}/sections` con `config: {}`
  (`PlatformCmsEditorPage.tsx:135-138`, backend `cms.py:142`).

**SEO** (`:532-565`): PATCH a la misma página con SEO fields. Sin preview de
cómo se verá en Google / OG.

**Scripts** (`:567-624`): CRUD simple de `CmsScript`. Backend
`cms.py:204-237`.

**Vista previa** (`:626-634`): `<iframe src="/p/{slug}">`. Solo funciona si
la página está `published`, porque `/p/{slug}` renderiza desde
`CmsPublicPage.tsx` que consume
`subscription-service/app/api/routers/pages_public.py:24-36` — que solo
sirve páginas cuyo status es `published`. **Previsualizar un draft no
muestra nada útil** (404). Ver bugs §6.

Estados: `draft → published → archived`. Transitan con POST
`/api/v1/cms/pages/{id}/publish` y `/unpublish` (`cms.py:104, 116`). No
hay endpoint para pasar a `archived` (no expuesto en UI).

### 2.3 Renderizado público

Route: `/p/:slug` en `front-trace/src/pages/CmsPublicPage.tsx`. GET
`/api/v1/pages/{slug}` (subscription-service `pages_public.py`). La
respuesta incluye sections + scripts activos; `BlockRenderer` mapea
`block_type → componente React`. Scripts con `placement = head|body_*`
se inyectan vía `useEffect` / helmet en `CmsPublicPage`.

---

## 3. AI Settings — `/platform/ai`

**Archivo**: `front-trace/src/pages/platform/PlatformAiSettingsPage.tsx`
**Backend**:
- `subscription-service/app/api/routers/ai_settings.py` (GET `/api/v1/settings`
  via el gateway → monta ai-service prefix, ver abajo).

**Importante**: el frontend llama con
`VITE_API_URL/api/v1/settings` (`PlatformAiSettingsPage.tsx:11-26`) pero el
router real vive en `ai-service/app/api/routers/settings.py` y en
`subscription-service/app/api/routers/ai_settings.py` tiene prefix
`/api/v1/platform/ai`. El `subRequest` apunta al gateway `/api/v1/settings`
lo que implica que **el gateway está mapeando** `/api/v1/settings*` a
ai-service. Ver bugs §6 (potencial mismatch si no existe la ruta).

Tabs:

### 3.1 Configuración (`ConfigTab`, `:109-331`)

Todo lee/escribe contra endpoints del proveedor de IA:
- **Provider card** (solo Anthropic Claude hoy). API key masked, botón
  **Probar** → POST `/api/v1/settings/test` devuelve
  `{ ok, latency_ms, model }`. Guardar api key → PATCH
  `/api/v1/settings/api-key`.
- **Modelo**: dropdown con `claude-haiku-4-5-20251001` (recomendado) o
  `claude-sonnet-4-6` (`:227-228`). Hardcoded en frontend.
- **Max tokens**: 500-4000.
- Toggle global `anthropic_enabled`.
- Toggle `pnl_analysis_enabled` (módulo "Análisis de Rentabilidad").
- **Límites diarios por plan** (free/starter/professional/enterprise),
  `-1 = ilimitado`.
- **Cache**: `cache_enabled`, `cache_ttl_minutes` (5-1440), botón
  "Limpiar cache global" → DELETE `/api/v1/metrics/cache` con body
  `{ confirm: true }`.
- **Alerta de costo** mensual en USD.

Save all → POST `/api/v1/settings` con diff.

### 3.2 Métricas (`MetricsTab`, `:335-422`)

GET `/api/v1/metrics` (staleTime 30s):
- KPIs: llamadas/mes, costo estimado, costo proyectado, tenants activos.
- Banner rojo si `alert_triggered`.
- Tabla de uso por tenant.
- Gráfico de barras primitivo de llamadas por día (CSS, no recharts).

### 3.3 Auditoría (`AuditTab`, `:435-526`)

Compliance con Ley 1581/2012 Colombia (Habeas Data): cada vez que un
superuser accede a datos de IA de otro tenant queda un registro.
- GET `/api/v1/settings/audit/cross-tenant?month=YYYY-MM&limit=200`.
- Tabla: timestamp, superusuario (email), tenant consultado, acción
  (`ai.analyze_pnl`, `ai.memory.read`, `ai.memory.delete`,
  `ai.memory.delete_last`), recurso.
- `TenantMemoryInspector` permite consultar memoria IA de cualquier tenant
  por `tenant_id` — GET `/api/v1/memory/{tenant_id}`. Muestra industria
  detectada, total análisis, productos estrella, alertas recurrentes,
  patrones. Botones "Borrar memoria" (DELETE `/api/v1/memory/{id}`) y
  "Borrar último análisis" (DELETE `/api/v1/memory/{id}/last`). **Cada
  consulta queda auditada automáticamente** (backend ai-service).

---

## 4. Marketplace — `/marketplace` (Bruno, admin de tenant)

**Archivo**: `front-trace/src/pages/MarketplacePage.tsx`
**Backend**: `subscription-service/app/api/routers/modules.py`
**Service**: `subscription-service/app/services/module_service.py`
**Módulos reales**
(`module_service.py:42-84`): `logistics`, `inventory`,
`electronic-invoicing` (requires `inventory`), `production` (deps
`inventory`), `compliance` (deps `logistics`), `ai-analysis`
(deps `inventory`). El catálogo "real" en el backend tiene **6 módulos**
hoy — la memoria CLAUDE.md que dice "solo logistics + inventory" está
desactualizada.

Flujo de Bruno:
1. Login como admin → tenant `tenant-X`. Navega a `/marketplace`.
2. Frontend: `useTenantModules(tenantId)` → GET
   `/api/v1/modules/{tenant_id}` (público, `modules.py:26-30`) — devuelve el
   catálogo con flag `is_active` por tenant.
3. Grid 2-3 columnas con cards por módulo. Como Bruno tiene
   `subscription.manage`, ve el `<Toggle>` (`MarketplacePage.tsx:156-163`).
   Carla vería el texto "Contacta a un administrador" (`:195-199`).
4. Si un módulo requiere otro que no está activo, el toggle queda
   **deshabilitado** con tooltip "Activa {dep} primero"
   (`:140-144, :160`). Ej.: activar `compliance` sin `logistics` no deja.
5. Bruno clickea el toggle de `inventory` (inactivo):
   - `activateMut.mutateAsync({ tenantId, slug: 'inventory' })` → POST
     `/api/v1/modules/{tenantId}/inventory/activate`
     (`modules.py:52-62`). Requiere permiso `subscription.manage` +
     `_enforce_tenant` (no cross-tenant sin superuser, `:43-49`).
   - Backend inserta/actualiza fila en `tenant_module_activations`
     (`is_active=True`, `activated_at=now`). Loggea quién activó.
6. Success → aparece **modal de post-activación** (`:207-244`):
   - "¡Módulo habilitado! [Inventario] está listo. Completa el pago de tu
     suscripción para mantener el acceso."
   - Dos botones: **"Completar suscripción"** (navega a
     `/checkout?module=inventory`) o "Hacerlo después" (cierra).

**Pregunta crítica**: ¿la activación del módulo ya bloquea algo si Bruno no
paga? Leyendo el código: **NO**. `module_service.activate` solo escribe la
fila y no verifica suscripción/plan. La regla de negocio documentada en
memoria CLAUDE.md dice: "rol administrador puede activar/desactivar módulos
libremente sin restricción de plan ni suscripción. Implementar paywall
cuando haya pasarela de pago". El paywall **aún no existe** — Bruno puede
simplemente cerrar el popup y seguir usando el módulo gratis.

---

## 5. Pasarela de Cobro — `/platform/payments` (alias `/pagos`)

**Archivo**: `front-trace/src/pages/PaymentsPage.tsx`
**Backend**:
- `subscription-service/app/api/routers/payments.py` (CRUD superuser-only).
- `subscription-service/app/services/payment_service.py` (catálogo
  hardcoded: **solo Wompi**, `payment_service.py:14-27`).
- `subscription-service/app/api/routers/webhooks.py` (webhook Wompi).

Ruta:
- `/pagos` → redirect a `/platform/payments` (`App.tsx:261`).
- `/platform/payments` → `<PaymentsPage />` gateada por
  `ProtectedRoute superuserOnly` (`App.tsx:384-389`).

Flujo de Ana:
1. GET `/api/v1/payments/{tenantId}` (`payments.py:47-53`, superuser-only).
   Devuelve el catálogo (1 entrada: Wompi) con credenciales enmascaradas
   (`payment_service.py:45-67`).
2. UI muestra card de Wompi con:
   - Banner verde si ya está `configured && is_active`
     (`PaymentsPage.tsx:98-103`).
   - Toggle **Modo Sandbox / Producción** (default: sandbox / test).
   - 4 campos: `public_key` (req), `private_key` (req, password),
     `integrity_key` (req, password), `events_secret` (opcional, para
     validar webhooks). Definidos en `PaymentsPage.tsx:13-18` y
     espejados en el backend `payment_service.py:20-25`.
3. Save → POST `/api/v1/payments/{tenantId}/wompi` con `{ credentials,
   is_test_mode }` + POST `/api/v1/payments/{tenantId}/wompi/activate`
   en secuencia (`PaymentsPage.tsx:63-71`, backend `payments.py:56-85`).
4. Tras guardar, muestra "Llaves configuradas" con los valores
   enmascarados (`••••••`) y timestamp `updated_at`.

**Tenant sobre el que se guarda**: el hook usa
`useAuthStore.s.user?.tenant_id`, que para Ana es `platform`
(`PaymentsPage.tsx:21`). El checkout de Bruno buscará
`gateway_config = payment_repo.get(tenant_id, 'wompi')` y hace
**fallback a `'platform'`** (`checkout.py:107-110`), así que Ana solo
necesita configurar Wompi una vez en el tenant `platform` y todos los
tenants lo usan. Esto coincide con la arquitectura "Trace cobra a sus
clientes" documentada en CLAUDE.md / MEMORY.md.

---

## 6. Flujo checkout completo — Bruno paga con Wompi

**Archivos**:
- `front-trace/src/pages/CheckoutPage.tsx`
- `front-trace/src/pages/CheckoutResultPage.tsx`
- `subscription-service/app/api/routers/checkout.py` (build URL)
- `subscription-service/app/api/routers/webhooks.py` (confirmación)

Secuencia:

1. Bruno llega a `/checkout?module=inventory` desde el popup del Marketplace.
2. `CheckoutPage`:
   - `usePlans()` → GET `/api/v1/plans` (todos los planes).
   - `useActiveGateway(userTenantId)` → GET
     `/api/v1/payments/{tenantId}/active` (`payments.py:39`, público
     inter-service). Devuelve la pasarela activa del tenant; si no hay,
     cae a `platform`.
   - Filtra planes que incluyen `modules.includes('inventory')` y los
     ordena por `PLAN_SORT` (free 0, starter 1, professional 2, enterprise
     3). Default: el más barato no-gratis.
3. Bruno ve 3 cards (Starter / Professional / Enterprise — `inventory`
   empieza en starter según `MODULE_MIN_PLAN` del frontend,
   `CheckoutPage.tsx:31-36`). Selecciona **Starter** ($49).
4. Resumen lateral muestra total/mes + Wompi como método (badge sandbox o
   prod según gateway). Click **"Pagar con Wompi"**:
   - `useCheckout().mutateAsync({ plan_slug: 'starter', tenant_id })` →
     POST `/api/v1/payments/checkout` con permiso
     `subscription.manage` (`checkout.py:43-45`).
   - Backend: resuelve plan, crea/actualiza suscripción (`get_or_create`),
     crea **invoice en status `open`** con `INV-YYYY-NNNN`, arma
     `reference = "{tenant_id}:{invoice_id}"`, calcula firma SHA256
     (`reference + amount_cents + currency + integrity_key`) y arma URL
     hacia `https://checkout.wompi.co/p/` (prod) o
     `https://sandbox.wompi.co/p/` (test) con `redirect-url = {APP_URL}/checkout/result?ref={reference}` (`checkout.py:116-141`).
   - Responde `{ checkout_url, invoice_id }`.
5. Frontend hace `window.location.href = checkout_url`. Bruno es sacado a
   Wompi.
6. En sandbox, Bruno paga con tarjeta `4242 4242 4242 4242`. Wompi
   redirige a `{APP_URL}/checkout/result?ref=tenant-X:inv-uuid&id=wompi-tx-123`.
7. `CheckoutResultPage`:
   - Lee `ref` e `id`.
   - **Si `id` está presente**: muestra "Pago procesado — Wompi confirmará
     el pago y tu suscripción se activará automáticamente"
     (`CheckoutResultPage.tsx:18-41`). **Esto es optimista** — NO consulta
     el backend; solo el webhook puede marcar la invoice como `paid`.
   - **Si `id` vacío**: muestra "Procesando pago" con spinner
     (`:43-62`). No hay polling; Bruno tiene que refrescar Marketplace /
     Billing manualmente.
8. Paralelamente Wompi llama `POST /api/v1/payments/webhooks/wompi`:
   - Valida firma `X-Event-Checksum` con `events_secret` del tenant
     (`webhooks.py:174-194`). Signature **obligatoria** — el bug previo
     que permitía bypass omitiendo el header fue arreglado
     (`webhooks.py:188-194`, comentario explícito).
   - Solo en `event == 'transaction.updated' && status == 'APPROVED'`
     dispara `process_successful_payment`:
     - Marca invoice `paid` con `paid_at`, `gateway_tx_id`, `gateway_slug`.
     - Renueva suscripción: `status=active`,
       `current_period_end = now + 30 días`.
     - Invalida cache Redis: `sub_svc:me:{tenant_id}` +
       `module:{tenant_id}:*`.
     - POST best-effort a user-service
       `/api/v1/notifications/email` con template
       `payment_confirmation`.

### Respuestas a las preguntas planteadas

- **¿El cambio de plan es inmediato o espera el webhook?** Mixto. La
  activación del **módulo** en `/marketplace` es inmediata y
  **no requiere pagar** (no hay paywall, confirmado en `module_service`).
  La **suscripción** como concepto (status `active`, `period_end` renovado,
  invoice `paid`) solo se actualiza cuando llega el webhook
  (`webhooks.py:73-97`). Mientras tanto la invoice queda `open`.

- **¿Qué pasa si el pago falla?** El webhook **solo procesa APPROVED**
  (`webhooks.py:205`). Pagos declinados/cancelados no se procesan →
  invoice queda `open` indefinidamente. No hay lógica de "past_due" o
  reintento automático visibles. El redirect a `/checkout/result` con
  `?id=X` igualmente muestra "Pago procesado" aunque la tx haya sido
  DECLINED — solo mira si `id` está presente
  (`CheckoutResultPage.tsx:13`). **Bug real**, ver §7.

- **¿Qué pasa si el pago queda pending y Bruno cierra la ventana?**
  Igual: la invoice queda `open`. Si el webhook llega más tarde (Wompi
  reintenta), se procesa retroactivamente con idempotencia
  (`webhooks.py:60-62`). Si el webhook jamás llega o el
  `events_secret` está mal configurado, la invoice **nunca** se marca
  pagada y la suscripción no se activa — no hay UI para reconciliar
  manualmente ni reintentar.

---

## 7. Bugs detectados

### Críticos

1. **`/checkout/result` marca "Pago procesado" con solo ver `?id=`,
   ignorando el status real** —
   `front-trace/src/pages/CheckoutResultPage.tsx:13,18`. Un usuario con
   tx DECLINED/VOIDED que vuelve al redirect ve "éxito" cuando en realidad
   no pagó nada. Debería llamar `GET /api/v1/subscriptions/invoices/{id}`
   o un endpoint `/tx-status` antes de mostrar verde.

2. **Promover a superuser no está protegido por superuser en backend** —
   `PlatformTeamPage.tsx:26-30` llama PATCH `/api/v1/users/{id}` con
   `is_superuser: true`. En `user-service/app/api/routers/users.py:157`
   (`@router.patch("/{user_id}")`) la verificación es `admin.users`, un
   permiso del rol administrador normal. Cualquier admin de cualquier
   tenant podría, vía curl directo, hacerse superuser si sabe el endpoint.
   Verificar en users.py qué chequeo real aplica para `is_superuser` —
   si no lo hay, es escalación de privilegios.

3. **El iframe de preview en el editor CMS sirve solo si la página está
   published** — `PlatformCmsEditorPage.tsx:626-634` hace
   `<iframe src="/p/{slug}">`, pero `pages_public.py:24-36` solo devuelve
   páginas `published`. Un editor que quiere previsualizar su draft ve
   404. Debería usar un endpoint `/preview/{id}` autenticado que
   renderice draft.

### Medios

4. **Save metadatos del CMS descarta TODO si el JSON de navbar/footer es
   inválido** — `PlatformCmsEditorPage.tsx:323-331`. Un typo en
   `navbar_config` bota el título y el slug también. Debería validar
   campo por campo.

5. **Dead state en PlatformTeamPage**: `showInvite`/`setShowInvite`
   declarado `PlatformTeamPage.tsx:15` y `UserPlus` importado
   `PlatformTeamPage.tsx:4` — ninguno se usa. No hay modal de invitar
   usuarios a pesar del hint visual.

6. **`GripVertical` en secciones CMS sin drag-and-drop real** —
   `PlatformCmsEditorPage.tsx:54`. Ícono puesto como affordance pero
   `useReorderCmsSections` (importado en `:9`) no se wirea a ningún
   handler. Existe el endpoint
   `PUT /api/v1/cms/pages/{id}/sections/reorder` (`cms.py:157`) que queda
   inaccesible desde UI.

7. **AI Settings apunta al gateway con paths que no tienen prefix
   `/platform/ai`** — `PlatformAiSettingsPage.tsx:11-26` llama
   `{VITE_API_URL}/api/v1/settings` mientras
   `subscription-service/app/api/routers/ai_settings.py:15` declara
   `prefix="/api/v1/platform/ai"`. O hay un rewrite en nginx mapeando
   `/api/v1/settings*` a ai-service, o la UI está efectivamente rota.
   Verificar `gateway/nginx.conf`.

8. **Activar módulo NO exige pago ni valida el plan** —
   `module_service.py activate()` solo inserta en
   `tenant_module_activations`. Bruno puede activar `analytics` sin tener
   plan `professional`. El popup de checkout es cosmético. El mismo
   CLAUDE.md lo admite como pre-payment-gateway.

9. **El catálogo de módulos del backend tiene 6 entradas, pero la UI de
   Marketplace no siempre refleja dependencias correctamente en cascada** —
   `MarketplacePage.tsx:141-144` solo chequea `requires`
   (singular, un slug). Módulos del backend declaran `dependencies`
   (plural, array, `module_service.py:66,73,81`). Si `compliance` depende
   de `logistics`, el frontend no parsea ese array — depende del campo
   `requires` que el backend no siempre emite.

### Menores

10. **Duplicado de routing `/pagos` y `/platform/payments`** — solo
    redirect, ok. Pero el breadcrumb en `PaymentsPage.tsx:78-84` dice
    "Plataforma → Pasarela de Cobro", coherente.

11. **PlatformUsersPage no expone búsqueda por email específicamente** —
    el input busca por "nombre o email" (`:39`), pero el backend
    user-service `users.py:104` recibe el parámetro como `search` genérico.
    OK funcionalmente pero sin hints de qué campos matchea.

12. **Sin paginación en Team** — hardcoded a `limit: 200`
    (`PlatformTeamPage.tsx:22`). Si Trace supera 200 empleados en total
    (improbable a corto plazo pero real) la lista se corta silenciosamente.

---

## 8. Gaps enterprise

- **Refunds**: no hay endpoint ni UI para emitir reembolsos. Si Bruno paga y
  luego cancela, solo queda la cancelación de subscription pero el pago ya
  está cobrado. `invoice.status` no tiene valor `refunded` en los enums
  visibles.

- **Múltiples gateways**: el catálogo está hardcoded a 1 entrada
  (`payment_service.py:14-27`). Expansiones a PSE directo, Mercado Pago,
  Stripe implican tocar código (no es data-driven). La memoria CLAUDE.md
  todavía menciona 7 gateways; está obsoleta.

- **Paywall real**: activar módulo sin plan adecuado no bloquea nada. Falta
  un middleware que, al llamar `is_active` de un módulo, verifique que la
  suscripción del tenant tenga ese módulo en `plan.modules` y esté
  `active` (no `past_due` / `canceled`).

- **Dunning / past_due**: sin lógica automática de pasar a `past_due`,
  suspender acceso tras N días de impago ni emails de recordatorio. El
  expiration_service corre cada hora (endpoint manual en
  `platform.py:291-299`) pero no hay visibilidad de su lógica desde este
  journey.

- **Auditoría de cambios en Team** (promociones a superuser, desactivar
  usuarios) — no es evidente que user-service loggee en `audit_logs` las
  operaciones hechas desde `/platform/team`. Compliance enterprise lo
  exige.

- **Re-intentar webhooks perdidos / reconciliar** — si un webhook Wompi se
  pierde (secret mal configurado en un momento, bug transitorio), la
  invoice queda `open` para siempre. Falta cron que, para invoices `open`
  de más de X horas, haga pull a Wompi
  (`GET transactions?reference=…`) y reconcilie.

- **Editor CMS sin history / drafts múltiples / rollback** — cada save
  sobrescribe `CmsPage` en lugar de versionar. Si Ana rompe la página
  pública y apreta "Publicar", no hay "Revert to last published".

- **Preview de scripts y config JSON sin sandbox** — `custom_html` y
  scripts inline se renderizan directo en la página pública. Un superuser
  hostil puede meter JS malicioso. Asumiendo Ana es confiable es
  aceptable, pero no hay CSP visible.
