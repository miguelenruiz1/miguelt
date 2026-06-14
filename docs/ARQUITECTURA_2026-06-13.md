# Trace — Arquitectura de la plataforma (2026-06-13)

> Estado **post-eliminación del módulo Cumplimiento/EUDR**. Refleja lo que corre
> hoy en producción (Hetzner, rama `develop`). No quedan referencias vivas a
> compliance/EUDR.

---

## 1. Qué es Trace

Plataforma **SaaS multi-tenant y modular** para trazabilidad de cadena de
suministro + gestión operativa (inventario, producción, facturación). Cada
tenant activa los **módulos** que necesita desde un marketplace; el cobro y el
gating se manejan por suscripción.

Pilares:
- **Trazabilidad anclada en blockchain** (Solana real, devnet vía Helius) — cada
  evento de custodia se puede anclar on-chain y verificar públicamente sin login.
- **Modularidad** — logística, inventario, producción, facturación electrónica e
  IA se activan/desactivan por tenant.
- **Multi-tenant estricto** — usuarios, roles, permisos, datos y blockchain
  aislados por `tenant_id`.

---

## 2. Topología (microservicios)

Todo entra por un **gateway nginx** (`trace-gateway`) que rutea por path a cada
servicio. El frontend es un contenedor aparte servido en el puerto 80.

```
                         ┌──────────────────────────────┐
        Navegador  ─────▶│  front-trace (nginx :80)      │  React/Vite SPA
                         └──────────────┬───────────────┘
                                        │ /api/v1/*
                         ┌──────────────▼───────────────┐
                         │  trace-gateway (nginx :9000)  │  rutea por path
                         └──┬───┬───┬───┬───┬───┬───┬────┘
        ┌───────────────────┘   │   │   │   │   │   └──────────────┐
        ▼            ▼           ▼   ▼   ▼   ▼   ▼                  ▼
   trace-api    user-api   subscription inventory integration  ai-api   media-api
    :8000        :8001      -api :8002  -api :8003  -api :8004   :8006    :8007
   custodia/     auth/RBAC/  billing/    stock/POs/  webhooks/   insights  archivos
   blockchain    audit       módulos     producción  e-invoice   IA        media
        │            │           │           │           │         │         │
   trace-postgres  user-pg   subscription-pg inventory-pg integ-pg  ai-pg   media-pg
        │
   trace-redis (compartido: idempotencia, cache de módulos, ARQ worker, blacklist JWT)
   trace-worker (ARQ — anclaje Solana asíncrono)
   trace-mailhog → mailpit (SMTP dev/captura de correos)
```

**Puertos internos / contenedor:**

| Servicio (compose) | Contenedor | Puerto | DB | Rol |
|---|---|---|---|---|
| `api` | trace-api | 8000 | trace-postgres | Custodia, assets, anclaje Solana |
| `worker` | trace-worker | — | (usa trace-pg/redis) | Worker ARQ de anclaje |
| `user-api` | user-api | 8001 | user-postgres | Auth, RBAC, auditoría, correo |
| `subscription-api` | subscription-api | 8002 | subscription-postgres | Planes, suscripciones, módulos, facturas, licencias |
| `inventory-api` | inventory-api | 8003 | inventory-postgres | Inventario, compras/ventas, producción |
| `integration-api` | integration-api | 8004 | integration-postgres | Webhooks, sync ERP, e-invoice DIAN |
| `ai-api` | ai-api | 8006 | ai-postgres | Análisis con Claude (P&L, insights) |
| `media-api` | media-api | 8007 | media-postgres | Almacenamiento de archivos |
| `gateway` | trace-gateway | 9000 | — | nginx, rutea por path |
| `front-trace` | front-trace | 80→8080 | — | SPA React/Vite |

---

## 3. Despliegue en producción (Hetzner)

> ⚠️ GCP está apagado (migración terminó abril 2026). **Producción solo en Hetzner.**

- **Host:** `root@62.238.5.1` (Hetzner CAX11 ARM64, Helsinki). Repo en `/opt/trace`.
- **URL pública:** http://62.238.5.1 (front-trace en :80; gateway en :9000).
- **Composición real:** corre con `docker compose` usando
  **`docker-compose.yml` + `docker-compose.override.yml`** (NO el
  `deploy/docker-compose.production.yml`, que está sin uso).
  - El `override.yml` (solo en el VM, fuera de git) define `front-trace`
    (build de `./front-trace` con `VITE_API_URL=http://62.238.5.1:9000`) y
    reemplaza mailhog por **mailpit** (compatible ARM).
- **Flujo de deploy seguro:** ver el skill `.claude/skills/deploy-seguro/SKILL.md`
  (checkout de la rama → `docker compose up -d --build --remove-orphans <servicios> front-trace`
  → `restart gateway` → smoke test). Migraciones alembic corren solas al arrancar
  cada contenedor (`alembic upgrade head` en su `command`).

---

## 4. Servicios y su funcionalidad

### 4.1 trace-service (:8000) — Custodia + blockchain
Núcleo de trazabilidad. Cadena de custodia inmutable con anclaje en Solana.

- **Entidades:** `Asset` (con state machine), `CustodyEvent` (log inmutable),
  `RegistryWallet` (allowlist de custodios), `TenantMerkleTree` (árbol cNFT por
  tenant), `ShipmentDocument`/`TradeDocument`, `AnchorRequest`/`AnchorRule`.
- **State machine de assets:** `IN_CUSTODY, IN_TRANSIT, LOADED, QC_PASSED/FAILED,
  RELEASED, BURNED, CUSTOMS_HOLD, DELIVERED, SEALED, RETURNED…` con transiciones
  válidas forzadas (`VALID_FROM_STATES`).
- **Eventos:** custodia (HANDOFF, ARRIVED, LOADED, GATE_IN/OUT, DEPARTED…),
  calidad (QC, INSPECTION, TEMPERATURE_CHECK), aduana (CUSTOMS_HOLD/CLEARED),
  terminales (RELEASED, BURN, DELIVERED) e informativos (NOTE, CONSOLIDATED,
  COMPLIANCE_VERIFIED). `custody_mode`: identity_preserved | segregated |
  mass_balance.
- **Routers:** `/api/v1/assets`, `/registry`, `/config/custody`,
  `/config/event-config`, `/config/workflow`, `/anchoring`, `/solana`,
  `/taxonomy`, `/shipments`, `/analytics`, `/uploads`.
- **Destacado:** worker ARQ para anclaje asíncrono (Memo Program + cNFT
  comprimidos vía Helius); motor de **workflow** configurable por tenant;
  requisitos de documentos por tipo de evento; idempotencia con Redis.

### 4.2 user-service (:8001) — Auth + RBAC + auditoría
- **Entidades:** `User` (con TOTP 2FA, invitaciones, onboarding FSM), `Role`
  (por tenant, `is_system`), `Permission` (por módulo), `UserRole`,
  `RolePermission`, `UserSession`, `AuditLog`, `EmailTemplate`/`EmailConfig`,
  `Notification`.
- **Routers:** `/api/v1/auth` (login, register, 2FA, refresh, logout),
  `/users`, `/roles`, `/permissions`, `/audit`, `/email-templates`,
  `/email-config`, `/email-providers`, `/notifications`, `/onboarding`.
- **Destacado:** JWT + TOTP con códigos de recuperación; RBAC estricto por
  tenant; auditoría con IP + old/new data; rate limiting en login/2FA;
  flujo de invitación y onboarding (welcome→profile→modules→done).
- **Nota:** los permisos `compliance.*` fueron eliminados.

### 4.3 subscription-service (:8002) — Billing + módulos
- **Entidades:** `Plan`, `Subscription` (1 por tenant), `Invoice` (con metadata
  e-factura DIAN: cufe, einvoice_*), `LicenseKey`, `TenantModuleActivation`,
  `SubscriptionEvent`, `PaymentGatewayConfig`.
- **Catálogo de módulos actual (`MODULE_CATALOG`):**
  `logistics`, `inventory`, `electronic-invoicing` (requiere inventory),
  `production` (requiere inventory), `ai-analysis` (requiere inventory).
  **(compliance eliminado.)**
- **Routers:** `/api/v1/plans`, `/subscriptions`, `/licenses`, `/modules`
  (catálogo público + activar/desactivar), `/payments`, `/admin`, `/platform`,
  `/usage`, `/webhooks`, `/checkout`.
- **Destacado:** activación de módulos cacheada en Redis por servicio consumidor
  (se invalida al togglear); loops horarios de expiración y **dunning**; medición
  de uso (assets, usuarios, API); e-invoicing vía MATIAS/DIAN.

### 4.4 inventory-service (:8003) — Inventario + producción
El módulo operativo más grande.
- **Entidades:** `Product` (Entity), `StockLevel`, `StockMovement`, `Warehouse`/
  `WarehouseLocation`, `EntityBatch`, `ProductVariant`, `Supplier`,
  `PurchaseOrder`/`Line` (con aprobación y **consolidación**), `SalesOrder`/`Line`,
  `EntityRecipe` (BOM), `RecipeComponent`, `ProductionRun`, `CycleCount`, `Alert`,
  `CostHistory`, `TaxRate`/`TaxCategory`, `Customer`.
- **Routers:** `/api/v1/products`, `/categories`, `/warehouses`, `/stock`,
  `/movements`, `/suppliers`, `/purchase-orders`, `/sales-orders`, `/recipes`,
  `/production`, `/batches`, `/serials`, `/cycle-counts`, `/analytics`,
  `/reports`, `/alerts`, `/customers`, `/customer-prices`, `/portal`,
  `/variants`, `/tax-rates`, `/uom`, `/audit`, `/public-verify`.
- **Destacado:** motores de costeo (promedio ponderado / FIFO / estándar) con
  `cost_history`; pricing dinámico (margen objetivo vs. último costo);
  **consolidación de OC** (varias OC → una al proveedor); workflow de aprobación;
  **auto-reorden** diario; alertas de vencimiento de lotes; **portal de clientes**
  self-service; verificación pública de lote/serial (`/public-verify`).
- **Nota:** migración `087` eliminó `origin_plot_id/code` (eran punteros EUDR).
  `commodity_type` (coffee/cacao/palma) y `tax_id_type` se conservan (genéricos).

### 4.5 integration-service (:8004) — Integraciones + e-invoice
- **Entidades:** `IntegrationConfig` (credenciales cifradas), `SyncJob`,
  `SyncLog`, `WebhookLog`, `InvoiceResolution` (numeración DIAN).
- **Routers:** `/api/v1/integrations` (+ `/catalog` público, `/test`, `/sync`,
  `/sync/pause|resume`, `/invoice`), `/resolutions`, `/webhooks`.
- **Destacado:** credenciales cifradas; sync bidireccional (push/pull) con
  captura de error por registro; e-invoicing DIAN (resolución + numeración
  auto-incremental); verificación de firma de webhooks por proveedor.

### 4.6 ai-service (:8006) — Insights con IA
- **Entidad:** `PlatformAISettings` (singleton): API key cifrada, modelos
  (`claude-haiku-4-5` análisis / `claude-sonnet-4-6` premium), límites por plan,
  cache TTL, tracking de costo mensual.
- **Routers:** `/api/v1/analyze/pnl` (análisis de rentabilidad), `/settings`
  (superuser), `/memory` (plantillas de prompt), `/metrics`.
- **Destacado:** integración Claude API (Haiku barato / Sonnet premium); límites
  de llamadas por plan; cache Redis de resultados; tracking de gasto con alertas.

### 4.7 media-service (:8007) — Archivos
- **Entidad:** `MediaFile` (hash SHA-256 para dedupe, backend local/S3,
  category, document_type, tags, metadata).
- **Routers:** `/api/v1/media/files` (upload/list/get/patch/delete), `/search`,
  `/uploads/*` (servido estático), `/internal/*` (S2S).
- **Destacado:** deduplicación por hash; multi-backend (local/S3); cuotas por
  tenant; enriquecimiento por categoría/tipo/tags.

---

## 5. Frontend (front-trace — React/Vite/TS)

SPA con React Query + Zustand. Servida como contenedor nginx en :80.

- **Auth/RBAC:** store Zustand persistido (`trace-auth`); `ProtectedRoute`
  (chequea token + permiso + superuser); permisos como slugs (`inventory.view`,
  `admin.users`, etc.); superuser bypassa.
- **Gating de módulos:** `useIsModuleActive(slug)` consulta `/api/v1/modules/...`;
  `ModuleGuard` envuelve páginas de módulo; `FeatureGuard` gatea features finos
  dentro de inventario (lotes, seriales, conteo, escáner, picking, kardex, etc.).
- **Secciones del sidebar** (rediseño estilo Siigo: hover full-width, iconos por
  sección, colapsadas por defecto): **Logística** (Truck), **Inventario** (Boxes),
  **Producción** (Factory), **Equipo** (UsersRound), **Empresa** (Building2),
  **Plataforma** (Crown, solo superuser).
- **Áreas principales:**
  - **Logística:** Dashboard, Cargas (`/assets`), Custodios (`/wallets`),
    Organizaciones (`/organizations`), Seguimiento kanban (`/tracking`),
    Flujo de trabajo, Analíticas de transporte.
  - **Inventario:** dashboard, productos, categorías, bodegas, movimientos,
    compras/ventas, socios, portal de clientes, lotes/seriales, conteos, kardex,
    reportes, configuración (tipos, impuestos, medidas, reorden).
  - **Producción:** órdenes, recetas (BOM), recursos, MRP, emisiones, recibos,
    reportes.
  - **Equipo:** usuarios, roles, auditoría. **Empresa:** suscripción, facturación,
    correo. **Plataforma:** tenants, planes, suscripciones, pagos, IA, blockchain.
  - **Marketplace** (`/marketplace`): activar/desactivar módulos.
- **Trazabilidad pública:** `generateTraceabilityPDF.ts` (PDF con narrativa +
  anclaje blockchain + QR); `PublicVerifyPage` (`/verificar/:batch`) — verificación
  de lote sin login, con proof-chain on-chain.

---

## 6. Temas transversales

- **Multi-tenancy:** todo lleva `tenant_id`; header `X-Tenant-Id` resuelto en el
  gateway/deps. Tenant default: `00000000-0000-0000-0000-000000000001` (slug
  `default`).
- **Blockchain real siempre:** sin provider simulado; `HeliusProvider` único.
  Requiere `HELIUS_API_KEY` + `SOLANA_KEYPAIR` en todo ambiente o falla al
  arrancar. `SOLANA_NETWORK=devnet` por default.
- **Auth S2S:** llamadas entre servicios usan `X-Service-Token` (`S2S_SERVICE_TOKEN`).
- **Cache de módulos:** Redis por servicio consumidor; toggle invalida.
- **Gateway:** nginx cachea IP de upstream → **siempre `restart gateway`** tras
  recrear un backend (evita 502).

## 7. Stack
FastAPI (async, SQLAlchemy 2, asyncpg, Pydantic v2) · PostgreSQL 16 · Redis 7 ·
ARQ · Solana/Helius · React 18 + Vite 6 + TS + React Query + Zustand + Tailwind ·
nginx · Docker Compose · Anthropic Claude API.
