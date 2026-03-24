# Trace Platform — Informe Completo

## Resumen Ejecutivo

Trace es una plataforma SaaS multi-tenant para trazabilidad de cadena de custodia, gestión de inventario, facturación electrónica y cumplimiento normativo. Compuesta por 6 microservicios backend (Python/FastAPI), 1 frontend (React/TypeScript), 6 bases de datos PostgreSQL y Redis.

**584 archivos totales** · **98 migraciones de BD** · **80+ rutas frontend** · **6 módulos activables**

---

## Arquitectura de Microservicios

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React/Vite)                       │
│                          localhost:5173                              │
│  React 19 · TypeScript 5.7 · Tailwind · React Query · Zustand      │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────┬───────┘
       │          │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼          ▼
┌──────────┐┌──────────┐┌──────────┐┌──────────┐┌──────────┐┌──────────┐
│  trace   ││  user    ││ subscr.  ││inventory ││integr.   ││compliance│
│ service  ││ service  ││ service  ││ service  ││ service  ││ service  │
│ :8000    ││ :9001    ││ :9002    ││ :9003    ││ :9004    ││ :9005    │
│          ││          ││          ││          ││          ││          │
│ Custody  ││ Auth     ││ Plans    ││ Products ││ E-Invoic ││ Normas   │
│ Assets   ││ RBAC     ││ Billing  ││ Stock    ││ Webhooks ││ Parcelas │
│ Wallets  ││ Audit    ││ Modules  ││ PO/SO    ││ DIAN     ││ Certific.│
│ Solana   ││ Email    ││ Payments ││ P&L + IA ││          ││          │
│ Taxonomy ││ Notific. ││ AI Sett. ││ Produc.  ││          ││          │
└────┬─────┘└────┬─────┘└────┬─────┘└────┬─────┘└────┬─────┘└────┬────┘
     │           │           │           │           │           │
     ▼           ▼           ▼           ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│trace-pg │ │user-pg  │ │sub-pg   │ │inv-pg   │ │int-pg   │ │cmp-pg   │
│ :5471   │ │ :5472   │ │ :5473   │ │ :5474   │ │ :5475   │ │ :5476   │
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘

                    ┌─────────────────────┐
                    │   Redis :6380       │
                    │ db0=trace db1=arq   │
                    │ db2=user  db3=sub   │
                    │ db4=inv   db5=int   │
                    └─────────────────────┘

              ┌───────────────────────────────┐
              │  Integraciones externas       │
              │  · Solana (Helius DAS API)    │
              │  · Wompi (Pagos)              │
              │  · Anthropic (IA/Claude)      │
              │  · SMTP (Email)               │
              │  · DIAN (Facturación)          │
              └───────────────────────────────┘
```

---

## Servicios en Detalle

### 1. trace-service (Logística y Custodia)
| Dato | Valor |
|------|-------|
| Puerto | 8000 |
| BD | trace-postgres:5471 |
| Redis | db=0, db=1 (ARQ worker) |
| Archivos | 49 |
| Migraciones | 7 |

**Función**: Cadena de custodia inmutable, trazabilidad de activos/NFTs, wallets Solana, taxonomía de organizaciones.

**Tablas principales**: tenants, assets, asset_events, registry_wallets, custodian_types, organizations, tenant_merkle_trees

**Máquina de estados de custodia**:
```
PENDING → IN_CUSTODY → IN_TRANSIT → ARRIVED → LOADED → QC → RELEASED
                    ↘                                  ↗
                     → BURNED (terminal)
```

### 2. user-service (Autenticación y RBAC)
| Dato | Valor |
|------|-------|
| Puerto | 8001 (ext: 9001) |
| BD | user-postgres:5472 |
| Redis | db=2 |
| Archivos | 44 |
| Migraciones | 14 |

**Función**: JWT auth (15min access + 7d refresh), 26 permisos en 7 módulos, audit trail, email/SMTP, onboarding.

**Tablas**: users, roles, permissions, user_roles, role_permissions, audit_logs, email_templates, email_configs

### 3. subscription-service (SaaS y Facturación)
| Dato | Valor |
|------|-------|
| Puerto | 8002 (ext: 9002) |
| BD | subscription-postgres:5473 |
| Redis | db=3 |
| Archivos | 51 |
| Migraciones | 8 |

**Función**: Planes (Free/Starter/Pro/Enterprise), suscripciones, licencias, módulos, pasarela Wompi, configuración IA, expiración automática.

**Tablas**: plans, subscriptions, invoices, license_keys, subscription_events, tenant_module_activations, payment_gateway_configs, platform_ai_settings

**Planes**:
| Plan | Precio | Usuarios | Activos | Wallets |
|------|--------|----------|---------|---------|
| Free | $0 | 3 | 100 | 5 |
| Starter | $49 | 15 | 2,000 | 20 |
| Professional | $149 | 50 | 20,000 | 100 |
| Enterprise | Custom | Ilimitado | Ilimitado | Ilimitado |

### 4. inventory-service (Inventario y Comercio)
| Dato | Valor |
|------|-------|
| Puerto | 8003 (ext: 9003) |
| BD | inventory-postgres:5474 |
| Redis | db=4 |
| Archivos | 159 (el más grande) |
| Migraciones | 59 |

**Función**: Productos, bodegas, stock, movimientos, OC, OV, producción, recetas, conteos cíclicos, análisis de rentabilidad con IA, alertas, costos, variantes, lotes, seriales.

**28 routers**: products, categories, warehouses, stock, movements, suppliers, purchase-orders, sales-orders, production, recipes, cycle-counts, variants, serials, batches, partners, customer-prices, events, analytics, reports, config, uom, tax-rates, reorder, alerts, audit, portal, pnl/analysis

**Motores especializados**:
- CostingEngine (FIFO/LIFO/promedio ponderado)
- PricingEngine (precio dinámico + override por cliente)
- AlertService (stock bajo, vencimiento, reorden)
- AiAnalysisService (Claude Haiku 4.5 para P&L)

### 5. integration-service (Facturación Electrónica)
| Dato | Valor |
|------|-------|
| Puerto | 8004 (ext: 9004) |
| BD | integration-postgres:5475 |
| Redis | db=5 |
| Archivos | 33 |
| Migraciones | 3 |

**Función**: Facturación electrónica DIAN (Colombia), resoluciones, webhooks, integraciones externas.

### 6. compliance-service (Cumplimiento Normativo)
| Dato | Valor |
|------|-------|
| Puerto | 8005 (ext: 9005) |
| BD | compliance-postgres:5476 |
| Redis | db=5 |
| Archivos | 48 |
| Migraciones | 5 |

**Función**: Marcos normativos (EUDR, USDA, FSSAI), parcelas/fincas, registros de auditoría, certificados PDF con QR.

---

## Módulos Activables (Marketplace)

| Módulo | Slug | Dependencia | Categoría |
|--------|------|-------------|-----------|
| Logística | `logistics` | — | core |
| Inventario | `inventory` | — | core |
| Facturación Electrónica | `electronic-invoicing` | inventory | compliance |
| Facturación Sandbox | `electronic-invoicing-sandbox` | inventory | compliance |
| Producción | `production` | inventory | operations |
| Cumplimiento Normativo | `compliance` | logistics | compliance |
| Inteligencia Artificial | `ai-analysis` | inventory | analytics |

---

## User Journeys

### Journey 1: Nuevo Tenant (Onboarding)

```
1. /register → Crear cuenta (email, empresa, contraseña)
   ↓
2. Auto-asigna rol "administrador" + plan "Free"
   ↓
3. /marketplace → Ver módulos disponibles
   ↓
4. Activar "Logística" (gratis) → Sidebar muestra sección Logística
   ↓
5. Activar "Inventario" → Sidebar muestra sección Inventario
   ↓
6. /checkout?module=inventory → Si requiere plan pago → pagar con Wompi
   ↓
7. Wompi redirige a /checkout/result → Suscripción activada
   ↓
8. /inventario → Dashboard de inventario operativo
```

### Journey 2: Gestión de Inventario Diaria

```
1. /inventario → Dashboard (KPIs: valor total, SKUs, stock bajo)
   ↓
2. /inventario/productos → Crear productos (SKU, nombre, tipo, UoM, precio)
   ↓
3. /inventario/bodegas → Configurar bodegas (principal, secundaria, tránsito)
   ↓
4. /inventario/compras → Crear OC al proveedor
   ↓
   4a. OC draft → Confirmar → Recibir mercancía
   4b. Stock se incrementa automáticamente
   ↓
5. /inventario/ventas → Crear OV al cliente
   ↓
   5a. OV draft → Confirmar (reserva stock)
   5b. → Picking → Enviar (remisión PDF)
   5c. → Entregar (descuenta stock, calcula COGS)
   ↓
6. /inventario/movimientos → Ver historial de movimientos
   ↓
7. /inventario/alertas → Ver alertas de stock bajo / vencimiento
```

### Journey 3: Análisis de Rentabilidad (P&L + IA)

```
1. /inventario/rentabilidad → Ver P&L del período
   ↓
2. KPIs: Ingresos, Costo ventas, Utilidad, Margen %
   ↓
3. Panel "Análisis IA" se carga automáticamente
   ↓
   3a. Backend: inventory-service → GET /pnl/analysis
   3b. → Lee config IA de subscription-service
   3c. → Arma prompt con contexto del tenant + datos P&L
   3d. → Llama Claude Haiku 4.5
   3e. → Cachea en Redis (1h)
   ↓
4. Panel muestra:
   · Resumen ejecutivo (3-4 oraciones)
   · Alertas (márgenes negativos, variación de precios)
   · Oportunidades (subir precios, consolidar proveedores)
   · Productos estrella (mejor relación margen × volumen)
   · Recomendaciones accionables con prioridad y plazo
   ↓
5. Expandir producto → Ver detalle: compras, ventas, stock por bodega
   ↓
6. Descargar PDF / CSV del reporte
```

### Journey 4: Cadena de Custodia (Trazabilidad)

```
1. /organizations → Crear organizaciones (fincas, bodegas, transporte)
   ↓
2. /wallets → Generar wallets Solana para cada custodio
   ↓
3. /assets → Crear carga / Mintear NFT on-chain
   ↓
4. Registrar eventos de custodia:
   · HANDOFF: Finca entrega a Transporte
   · IN_TRANSIT: En camino
   · ARRIVED: Llegó a bodega
   · LOADED: Descargado en bodega
   · QC: Control de calidad (pass/fail)
   · RELEASED: Liberado para venta
   ↓
5. /tracking → Tablero Kanban (7 columnas por estado)
   ↓
6. /assets/:id → Timeline completa de custodia
   ↓
7. Cada evento se ancla opcionalmente en Solana (cNFT)
```

### Journey 5: Administración de la Plataforma (Superuser)

```
1. /platform → Dashboard ejecutivo (MRR, ARR, churn, tenants)
   ↓
2. /platform/tenants → Ver/gestionar todas las empresas
   ↓
3. /platform/onboard → Onboarding de nuevo tenant
   ↓
4. /platform/plans → Editar planes y precios
   ↓
5. /platform/payments → Configurar Wompi (llaves, modo test/prod)
   ↓
6. /platform/ai → Configurar IA:
   · API key de Anthropic
   · Modelo (Haiku/Sonnet)
   · Límites por plan (Free=0, Starter=10, Pro=50, Enterprise=ilimitado)
   · Cache y alertas de costo
   ↓
7. /platform/analytics → Métricas SaaS (crecimiento, revenue, churn)
   ↓
8. /platform/subscriptions → Gestionar suscripciones por tenant
```

### Journey 6: Cumplimiento Normativo

```
1. /marketplace → Activar módulo "Cumplimiento Normativo"
   ↓
2. /cumplimiento/frameworks → Ver marcos disponibles (EUDR, USDA, FSSAI)
   ↓
3. /cumplimiento/activaciones → Activar marcos para mi empresa
   ↓
4. /cumplimiento/parcelas → Registrar fincas/parcelas con geolocalización
   ↓
5. /cumplimiento/registros → Crear registros de auditoría por parcela
   ↓
6. /cumplimiento/certificados → Generar certificado PDF con QR verificable
   ↓
7. /verify/:numero → Cualquier persona verifica el certificado (público)
```

### Journey 7: Facturación Electrónica

```
1. /marketplace → Activar módulo "Facturación Electrónica"
   ↓
2. /facturacion-electronica/resolucion → Configurar resolución DIAN
   ↓
3. /inventario/ventas → Crear OV → Confirmar
   ↓
4. Al confirmar, se genera factura electrónica automáticamente
   ↓
5. /facturacion-electronica → Ver facturas emitidas, estado DIAN
   ↓
   (Sandbox disponible para pruebas sin DIAN real)
```

---

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | React 19, TypeScript 5.7, Vite 6.2, Tailwind 3.4 |
| State | React Query 5.67 (server), Zustand 5.0 (client) |
| UI | Shadcn/ui, Lucide icons, Recharts, Sonner |
| Backend | FastAPI 0.111+, Python 3.11+, Pydantic 2.7+ |
| ORM | SQLAlchemy 2.0+ (async), Alembic |
| BD | PostgreSQL 16 (6 instancias) |
| Cache | Redis 7 (6 databases) |
| Auth | JWT (HS256), 26 permisos, RBAC |
| Blockchain | Solana, Helius DAS API |
| Pagos | Wompi (checkout hosted + webhooks) |
| IA | Anthropic Claude Haiku 4.5 |
| Email | aiosmtplib, Mailhog (dev) |
| PDF | jsPDF, ReportLab, WeasyPrint |
| Deploy | Docker Compose (dev), Kubernetes-ready (prod) |

---

## Seguridad

- JWT compartido entre servicios (JWT_SECRET)
- Credenciales encriptadas en BD (API keys, passwords)
- RBAC con 26 permisos granulares
- Rate limiting por tenant en IA (Redis)
- Webhook signatures verificadas (HMAC-SHA256 para Wompi)
- CORS configurado por servicio
- Audit trail completo (quién hizo qué, cuándo)
- Module gating (Redis → HTTP fallback)
- Expiración automática de suscripciones (background task hourly)
- Plan enforcement: límite de usuarios por plan (402 Payment Required)

---

*Generado: 2026-03-24 · 584 archivos · 6 microservicios · 98 migraciones*
