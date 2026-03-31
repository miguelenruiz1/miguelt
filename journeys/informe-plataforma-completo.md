# Trace Platform — Informe Completo

**Fecha:** 30 de marzo de 2026
**Version:** 0.1.0

---

## 1. Vision General

Trace es una plataforma SaaS multi-tenant de trazabilidad, gestion de inventario, produccion y cumplimiento normativo. Permite a empresas rastrear activos fisicos a lo largo de cadenas de suministro, gestionar inventarios con costos y valorizacion, ejecutar corridas de produccion (BOM), cumplir normas internacionales (EUDR, USDA, FSSAI) y anclar eventos en blockchain (Solana).

La plataforma opera como un ecosistema de microservicios independientes, cada uno con su propia base de datos, conectados via APIs REST internas y un sistema de autenticacion centralizado con JWT.

---

## 2. Stack Tecnologico

### Backend
| Componente | Tecnologia |
|---|---|
| Lenguaje | Python 3.11 |
| Framework web | FastAPI (async) |
| ORM | SQLAlchemy 2.0 (asyncpg) |
| Migraciones | Alembic |
| Cache / Colas | Redis 7 |
| Base de datos | PostgreSQL 16 |
| Blockchain | Solana (cNFT via Helius API) |
| Workers | ARQ (async Redis queue) |
| Email | Resend API + SMTP (Mailhog dev) |
| IA | Anthropic Claude API |
| Facturacion electronica | MATIAS API (DIAN Colombia) |
| Validacion | Pydantic v2 |
| Serialization | ORJSON |

### Frontend
| Componente | Tecnologia |
|---|---|
| Framework | React 19 |
| Lenguaje | TypeScript |
| Build tool | Vite |
| State server | TanStack React Query |
| State client | Zustand (auth, settings) |
| Formularios | react-hook-form |
| Estilos | Tailwind CSS |
| Graficos | Recharts |
| Iconos | Lucide React |
| Router | React Router v6 |

### Infraestructura
| Componente | Tecnologia |
|---|---|
| Contenedores | Docker + Docker Compose |
| Red | Bridge network (trace-net) |
| Email dev | MailHog |
| DB admin | Adminer |
| Almacenamiento | Local filesystem / AWS S3 |

---

## 3. Arquitectura de Microservicios

### Regla Fundamental

- **inventory-service**: "QUE tengo, CUANTO vale y CON QUIEN comercio"
- **trace-service**: "DONDE esta, QUIEN lo tiene y QUE le paso"

### Servicios (8 microservicios + 1 worker)

| Servicio | Puerto | Base de datos | Redis DB | Responsabilidad |
|---|---|---|---|---|
| **trace-api** | 8000 | trace-postgres:5471 | 0-1 | Trazabilidad, custodia, blockchain, workflows |
| **trace-worker** | — | (compartida) | 1 | Anclaje Solana en background |
| **user-api** | 9001 | user-postgres:5472 | 2 | Autenticacion, RBAC, auditoria, email |
| **subscription-api** | 9002 | subscription-postgres:5473 | 3 | Planes, suscripciones, licencias, modulos |
| **inventory-api** | 9003 | inventory-postgres:5474 | 4 | Productos, stock, compras, ventas, produccion |
| **integration-api** | 9004 | integration-postgres:5475 | 5 | Facturacion electronica (DIAN), webhooks |
| **compliance-api** | 9005 | compliance-postgres:5476 | 6 | EUDR, parcelas, registros, certificados |
| **ai-api** | 9006 | ai-postgres:5477 | 7 | Analisis de rentabilidad con IA |
| **media-api** | 9007 | media-postgres:5478 | 8 | Almacenamiento centralizado de archivos |

### Comunicacion entre servicios

- **S2S (Service-to-Service):** Via HTTP interno con header `X-Service-Token`
- **Auth delegation:** Cada servicio decodifica JWT localmente (mismo `JWT_SECRET`), cachea usuario en Redis, fallback a `user-api /auth/me`
- **Event dispatch:** Servicios envian eventos a `integration-api /internal/events` para webhooks salientes

---

## 4. Catalogo de Modulos

Cada tenant puede activar/desactivar modulos desde el Marketplace:

| Modulo | Slug | Dependencias | Descripcion |
|---|---|---|---|
| **Logistica** | `logistics` | — | Cadena de custodia, tracking board, activos, wallets, organizaciones |
| **Inventario** | `inventory` | — | Productos, stock, bodegas, movimientos, compras, ventas, socios comerciales |
| **Produccion** | `production` | inventory | Recetas (BOM), corridas de produccion, emisiones, recibos, MRP, recursos |
| **Cumplimiento** | `compliance` | logistics | EUDR/USDA/FSSAI, parcelas, registros, certificados PDF verificables |
| **Facturacion Electronica** | `electronic-invoicing` | inventory | Facturas, notas credito/debito ante la DIAN via MATIAS |
| **Inteligencia Artificial** | `ai-analysis` | inventory | Analisis de rentabilidad, insights, alertas de margen |

---

## 5. Funcionalidades por Servicio

### 5.1 Trace Service — Trazabilidad y Custodia

**Modelos (17):** Tenant, Organization, RegistryWallet, Asset, CustodyEvent, Shipment, AnchorRequest, WorkflowState, WorkflowTransition, TenantMerkleTree, AnchorRule, etc.
**Migraciones:** 17

**Funcionalidades:**
- **Assets (cNFT):** Creacion de activos trazables con mint opcional en Solana (Merkle tree cNFT)
- **Cadena de custodia:** Eventos: handoff, arrived, loaded, qc, release, burn — con maquina de estados validada
- **Tracking board:** Kanban por estado del workflow, auto-refresh 30s, filtro por organizacion
- **Wallets (Custodios):** Registro de actores logisticos (farm, warehouse, truck, customs)
- **Organizaciones:** Entidades en la cadena logistica con tipos configurables
- **Workflow engine:** Estados y transiciones personalizables por tenant, presets por industria
- **Blockchain anchoring:** Worker ARQ para anclar hashes en Solana, verificacion publica
- **Shipments:** BL, AWB, carta de porte, guias terrestres, documentos de comercio exterior
- **Analytics:** Metricas de transporte y tiempos de custodia

### 5.2 User Service — Autenticacion y RBAC

**Modelos (10):** User, Role, Permission, UserRole, RolePermission, AuditLog, EmailTemplate, EmailConfig, EmailProvider, Notification
**Migraciones:** 14

**Funcionalidades:**
- **Auth:** Registro, login, JWT (access 8h + refresh 7d), logout con blacklist en Redis
- **RBAC:** 26+ permisos en 7+ modulos, roles configurables, rol "administrador" auto-seeded
- **Auditoria:** Log de todas las acciones administrativas
- **Email:** Templates con variables ($user_name, $link, etc.), Resend como proveedor a nivel plataforma, SMTP/Mailhog fallback
- **Onboarding:** Flujo paso a paso para nuevos usuarios
- **Notificaciones:** Sistema de notificaciones internas
- **Invitaciones:** Invitar usuarios por email con link de aceptacion

### 5.3 Subscription Service — Billing SaaS

**Modelos (13):** Plan, Subscription, Invoice, LicenseKey, SubscriptionEvent, TenantModuleActivation, PaymentGatewayConfig, etc.
**Migraciones:** 8

**Funcionalidades:**
- **Planes:** CRUD completo, precios mensual/anual, limites (usuarios, assets, wallets), modulos incluidos
- **Suscripciones:** Una por tenant (UNIQUE), estados: active/trialing/past_due/canceled/expired
- **Licencias:** Formato TRACE-XXXX-XXXX-XXXX-XXXX, validacion publica
- **Facturacion:** Numeracion INV-YYYY-NNNN, generacion automatica, estados open/paid/void
- **Modulos:** Activacion/desactivacion por tenant, catalogo con dependencias
- **Pasarela de pagos:** Soporte para 7 gateways colombianos (epayco, PayU, Wompi, MercadoPago, Bold, Kushki, Openpay)
- **Plataforma admin:** Dashboard KPIs (MRR, ARR, churn), onboarding de empresas, gestion de tenants
- **Expiracion automatica:** Loop horario que marca suscripciones vencidas

### 5.4 Inventory Service — Inventario y Comercio

**Modelos (69):** Product, Category, Warehouse, StockLevel, StockMovement, StockReservation, StockLayer, PurchaseOrder, SalesOrder, BusinessPartner, EntityBatch, EntitySerial, EntityRecipe, ProductionRun, ProductionEmission, ProductionReceipt, TaxRate, UoM, CycleCount, etc.
**Migraciones:** 72 (el mas grande)

**Funcionalidades:**

*Productos y stock:*
- Maestro de productos con SKU, categorias, imagenes, variantes
- Stock por producto + bodega + ubicacion
- Movimientos: compra, venta, traslado, ajuste, devolucion, merma
- Valorizacion: FIFO, FEFO, LIFO, promedio ponderado
- Kardex (historial valorizado)
- Alertas de stock bajo, sin stock, punto de reorden
- Auto-reorden configurable
- Clasificacion ABC

*Bodegas:*
- Tipos configurables, area, costo/m2, capacidad
- Ubicaciones jerarquicas (pasillo, estante, posicion)
- Conteo ciclico (CycleCount)
- Scanner de codigo de barras
- Picking de pedidos

*Comercio:*
- Socios comerciales (BusinessPartner) — proveedores y clientes
- Ordenes de compra (PO): draft->sent->confirmed->partial->received
- Ordenes de venta (SO): draft->confirmed->picking->shipped->delivered
- Remision fiscal, notas credito/debito
- Portal de cliente (/portal/:customerId)
- Precios especiales por cliente
- Aprobaciones por monto

*Produccion:*
- Recetas (BOM) con versiones y sub-ensambles recursivos
- Corridas de produccion: planned->released->in_progress->completed->closed
- Emisiones (consumo FIFO de componentes)
- Recibos (generacion de producto terminado con capas de costo)
- Recursos (maquinas, mano de obra) con capacidad y tarifas
- MRP: explosion recursiva de BOM, auto-generacion de OC
- Costeo por transformacion, varianza real vs estandar

*Configuracion:*
- Tipos configurables: producto, proveedor, bodega, movimiento, pedido
- Campos personalizados por tipo
- Tasas de impuesto (IVA, retencion, ICA) — seed Colombia
- Unidades de medida con conversiones

*Reportes:*
- CSV exportable: productos, stock, movimientos, proveedores
- P&L por producto, rotacion, ocupacion de bodegas

### 5.5 Integration Service — Integraciones Externas

**Modelos (7):** IntegrationConfig, InvoiceResolution, WebhookSubscription, WebhookDeliveryLog, etc.
**Migraciones:** 4

**Funcionalidades:**
- **Facturacion electronica:** Adaptador MATIAS para DIAN (facturas, notas credito, notas debito)
- **Resoluciones:** Numeracion autorizada por la DIAN con rangos y prefijos
- **Webhooks salientes:** Suscripciones por tenant + event type, HMAC-SHA256, retry exponencial
- **Internal events:** Endpoint S2S para recibir eventos de otros servicios y despachar a suscriptores

### 5.6 Compliance Service — Cumplimiento Normativo

**Modelos:** Framework, Activation, Plot, Record, Certificate, RiskAssessment, SupplyChainNode, DocumentLink
**Migraciones:** 11

**Funcionalidades:**
- **Frameworks:** EUDR, USDA Organic, FSSAI, con reglas de validacion
- **Activaciones:** Cada tenant activa los frameworks que necesita
- **Parcelas (Plots):** Gestion de parcelas con GeoJSON, area, coordenadas, integracion GFW
- **Registros (Records):** Declaraciones de cumplimiento por parcela, validacion automatica
- **Certificados:** Generacion PDF con HTML templates, verificacion publica por URL
- **Risk Assessment:** Evaluacion de riesgo por parcela/proveedor
- **Supply Chain:** Modelado de nodos de cadena de suministro
- **Deforestation check:** Integracion con Global Forest Watch API

### 5.7 AI Service — Inteligencia Artificial

**Migraciones:** 2

**Funcionalidades:**
- **Analisis de rentabilidad:** Consulta datos de inventario y genera insights con Claude API
- **Alertas de margen:** Identifica productos con margenes bajos
- **Oportunidades:** Sugiere acciones para mejorar rentabilidad
- **Memoria conversacional:** Contexto persistente por tenant
- **Configuracion:** API key y modelo configurable por plataforma

### 5.8 Media Service — Almacenamiento de Archivos

**Modelos (2):** MediaFile, MediaFolder
**Migraciones:** 2

**Funcionalidades:**
- **Upload centralizado:** Todos los servicios suben archivos via S2S
- **Categorias:** Organizacion por tipo (image, document, certificate, etc.)
- **Referencia cruzada:** Cada archivo registra que entidad lo usa (entity_type + entity_id)
- **Storage dual:** Local filesystem o AWS S3
- **MediaPickerModal:** Widget reutilizable en el frontend para buscar/subir archivos
- **Tenant isolation:** Cada tenant solo ve sus archivos

---

## 6. Frontend — 93 Paginas

### Estructura del Frontend

| Seccion | Paginas | Descripcion |
|---|---|---|
| **Root** | 36 | Auth, dashboard, assets, wallets, organizaciones, tracking, media, marketplace |
| **Inventario** | 45 | Productos, bodegas, movimientos, compras, ventas, produccion, config, reportes |
| **Produccion** | 6 | Dashboard, ordenes, recetas, recursos, MRP, emisiones, recibos |
| **Cumplimiento** | 8 | Frameworks, activaciones, parcelas, registros, certificados |
| **Plataforma** | 9 | Dashboard admin, tenants, analytics, ventas, planes, onboarding |
| **Logistica** | 1 | Analiticas de transporte |

### Sidebar (Navegacion)

**Siempre visible:** Marketplace, Dashboard, Media

**Logistica** (si modulo activo): Seguimiento, Cargas, Custodios, Organizaciones, Analiticas, Flujo de trabajo

**Inventario** (si modulo activo): Dashboard, Rentabilidad, Alertas + 5 subsecciones (Productos, Bodega, Compras/Ventas, Informes, Ajustes)

**Produccion** (si modulo activo): Dashboard, Ordenes, Recetas, Recursos, MRP, Emisiones, Recibos, Reportes

**Cumplimiento** (si modulo activo): Marcos Normativos, Mis Normas, Parcelas, Registros, Certificados

**Equipo** (permisos admin): Usuarios, Roles, Auditoria

**Empresa** (permisos suscripcion): Suscripcion, Facturacion, Webhooks

**Plataforma** (superuser): Panel, Sistema, Empresas, Analitica, Ventas, Planes, Suscripciones, Usuarios, Equipo, Onboarding, Pagos, IA, Facturacion Electronica, Correo

### Componentes Reutilizables (54)

- **Layout:** Layout, Sidebar, Topbar
- **UI:** 24 componentes base (Badge, Button, Dialog, DataTable, Toast, etc.)
- **Assets:** AssetCard, CreateAssetModal, MintNFTModal
- **Auth:** ProtectedRoute, BlockchainAnimation
- **Compliance:** ComplianceGuard, DocumentUploader, MediaPickerModal, PlotMap, RiskAssessmentForm, SupplyChainEditor
- **Inventory:** ModuleGuard, FeatureGuard, ActivityTimeline, BlockchainPanel, CopyableId, VariantPicker
- **Events:** EventTimeline, WorkflowEventModal
- **Wallets:** GenerateWalletModal, RegisterWalletModal, WalletTable

---

## 7. Seguridad

| Capa | Mecanismo |
|---|---|
| Autenticacion | JWT (HS256), access token 8h, refresh token 7d |
| Autorizacion | RBAC con 26+ permisos, superuser bypass |
| Multi-tenancy | Header `X-Tenant-Id` en toda request, aislamiento por tenant_id en BD |
| S2S | Header `X-Service-Token` con secreto compartido |
| Blockchain | Anclaje de hashes en Solana para inmutabilidad |
| Audit | Log de acciones administrativas en user-service |
| Encriptacion | Credenciales de integraciones cifradas en BD |
| CORS | Configurado por servicio, origenes permitidos |
| Rate limiting | Redis-based (configurable) |

---

## 8. Estadisticas Globales

| Metrica | Cantidad |
|---|---|
| Microservicios | 8 (+1 worker) |
| Bases de datos PostgreSQL | 8 |
| Redis databases | 8 (1 instancia) |
| Modelos de BD (total) | ~117 |
| Migraciones Alembic (total) | ~130 |
| Endpoints API (total) | ~110+ |
| Paginas frontend | 93 |
| Hooks React | 24 |
| Componentes | 54 |
| Clientes API (frontend) | 15 |
| Modulos activables | 6 |
| Permisos RBAC | 26+ |
| Volumenes Docker | 13 |

---

## 9. Flujos de Negocio Documentados

Los siguientes flujos estan documentados en `/journeys/`:

1. **Exportacion EUDR completa** — Desde parcela hasta certificado verificable
2. **Logistica de exportacion de cafe** — Supply chain internacional
3. **Logistica de construccion nacional** — Cadena domestica
4. **Plan de produccion v2** — BOM, emisiones, recibos, MRP (SAP B1 parity)
5. **Plan de integraciones y webhooks** — Eventos salientes para terceros
6. **Arquitectura completa** — Fronteras canonicas entre servicios

---

## 10. Roadmap de Infraestructura Pendiente

| Item | Estado | Notas |
|---|---|---|
| Pasarela de pago activa | Configurado, sin gateway real | 7 adaptadores listos (epayco, Wompi, etc.) |
| Connectors externos | Webhooks listos | SAP, Siigo, etc. son integraciones futuras |
| Modulo contable | No planificado | Demasiado complejo, mejor integrar con terceros |
| CI/CD | Pendiente | Docker images listas para registry |
| Monitoreo (Grafana/Prometheus) | Pendiente | Correlation IDs ya implementados |
| S3 produccion | Configurado | Media service soporta S3, usando local en dev |
