# INVENTARIO TECNOLOGICO — Modulo de Inventario TraceLog

## Tabla de Contenidos

- [1.1 Resumen Ejecutivo Tecnico](#11-resumen-ejecutivo-tecnico)
- [1.2 Arquitectura y Estructura](#12-arquitectura-y-estructura)
- [1.3 Modelos de Datos](#13-modelos-de-datos)
- [1.4 Endpoints REST](#14-endpoints-rest)
- [1.5 Servicios y Logica de Negocio](#15-servicios-y-logica-de-negocio)
- [1.6 Dependencias entre Servicios](#16-dependencias-entre-servicios)
- [1.7 Flujos Criticos](#17-flujos-criticos)
- [1.8 Seguridad y Autenticacion](#18-seguridad-y-autenticacion)
- [1.9 Performance y Escalabilidad](#19-performance-y-escalabilidad)

---

## 1.1 Resumen Ejecutivo Tecnico

### Stack Tecnologico

| Capa | Tecnologia | Version |
|------|------------|---------|
| Backend Framework | FastAPI | >=0.111.0, <0.112.0 |
| Lenguaje | Python | 3.11+ (async/await) |
| ORM | SQLAlchemy (async) | >=2.0.30, <3.0.0 |
| Validacion | Pydantic | >=2.7.0, <3.0.0 |
| Settings | pydantic-settings | >=2.3.0, <3.0.0 |
| Migraciones | Alembic | >=1.13.0, <2.0.0 |
| Base de datos | PostgreSQL (asyncpg) | >=0.29.0 |
| Cache | Redis (hiredis) | >=5.0.4, <6.0.0 |
| HTTP Client | httpx (inter-servicio) | >=0.27.0 |
| JSON | orjson | >=3.10.0 |
| Auth | python-jose (JWT HS256) | >=3.3.0, <4.0.0 |
| Logging | structlog | >=24.1.0 |
| ASGI Server | uvicorn + uvloop + httptools | >=0.30.0 |
| Frontend Framework | React | 19.0.0 |
| Frontend Build | Vite | 6.2.0 |
| Frontend CSS | TailwindCSS | 3.4.17 |
| Frontend Routing | React Router | 7.2.0 |
| Data Fetching | @tanstack/react-query | 5.67.0 |
| Forms | react-hook-form | 7.54.2 |
| State Management | Zustand | 5.0.0 |
| Charts | Recharts | 3.7.0 |
| Icons | lucide-react | 0.475.0 |
| PDF Generation | jsPDF + jspdf-autotable | 4.2.0 / 5.0.7 |
| Schema Validation (FE) | Zod | 3.24.2 |
| Testing (backend) | No framework presente | — |
| Testing (frontend) | No framework presente | — |

### Metricas del Modulo

| Metrica | Valor |
|---------|-------|
| **Backend: archivos Python** | 143 |
| **Backend: lineas de codigo (app/)** | 23,974 |
| **— Servicios (app/services/)** | 9,037 lineas / 31 archivos |
| **— Repositorios (app/repositories/)** | 3,044 lineas / 25 archivos |
| **— Routers (app/api/routers/)** | 6,060 lineas / 29 archivos |
| **— Modelos (app/db/models/)** | 2,302 lineas / 21 archivos |
| **— Schemas (app/domain/schemas/)** | 2,758 lineas / 24 archivos |
| **Migraciones Alembic** | 48 archivos / 3,604 lineas |
| **Frontend: paginas inventory/** | 46 archivos / 22,115 lineas |
| **Frontend: paginas e-invoicing** | 3 archivos / 959 lineas |
| **Frontend: hooks (useInventory.ts)** | 2,061 lineas |
| **Frontend: API client (inventory-api.ts)** | 965 lineas |
| **Frontend: tipos (inventory.ts)** | 1,413 lineas |
| **Frontend: utilidades PDF** | 543 lineas |
| **Endpoints REST** | ~200+ (28 routers) |
| **Modelos SQLAlchemy** | ~55 tablas |
| **Servicios Python** | 29 clases de servicio |
| **Paginas React** | 49 (46 inventory + 3 e-invoicing) |
| **Hooks React (useInventory)** | ~140 hooks |
| **Funciones API (inventory-api.ts)** | 32 namespaces, ~180 funciones |

---

## 1.2 Arquitectura y Estructura

### Arbol de Carpetas — Backend

```
inventory-service/
├── alembic/
│   ├── versions/                    # 48 migraciones (001-047 + env)
│   └── env.py
├── app/
│   ├── api/
│   │   ├── deps.py                  # Dependencias: auth, module gates, Redis, HTTP client
│   │   └── routers/                 # 29 archivos de endpoints
│   │       ├── alerts.py            # Alertas de stock + Kardex
│   │       ├── analytics.py         # Dashboard KPIs, ABC, EOQ, ocupacion
│   │       ├── audit.py             # Logs de auditoria
│   │       ├── batches.py           # Lotes (trazabilidad forward)
│   │       ├── categories.py        # Categorias jerarquicas
│   │       ├── config.py            # Config dinamica (tipos, campos custom) ~1097 lineas
│   │       ├── customers.py         # Clientes + tipos + listas de precios
│   │       ├── customer_prices.py   # Precios especiales por cliente
│   │       ├── cycle_counts.py      # Conteos ciclicos + IRA
│   │       ├── events.py            # Eventos/incidentes de inventario
│   │       ├── health.py            # /health, /ready (K8s probes)
│   │       ├── imports.py           # Importacion CSV + demo data
│   │       ├── movements.py         # Historial de movimientos
│   │       ├── portal.py            # Portal de autoservicio para clientes
│   │       ├── production.py        # Ordenes de produccion (BOM)
│   │       ├── products.py          # Productos + imagenes
│   │       ├── purchase_orders.py   # OC + consolidacion + recepcion
│   │       ├── recipes.py           # Recetas/formulas (BOM)
│   │       ├── reorder.py           # Reorden automatico
│   │       ├── reports.py           # Exportacion CSV
│   │       ├── sales_orders.py      # OV + aprobacion + backorders
│   │       ├── serials.py           # Seriales individuales
│   │       ├── stock.py             # Recepcion/despacho/transferencias/ajustes/QC
│   │       ├── suppliers.py         # Proveedores
│   │       ├── tax_rates.py         # Tarifas IVA/retencion
│   │       ├── taxonomy.py          # Vocabularios y terminos (tags)
│   │       └── variants.py          # Atributos de variante + variantes
│   ├── core/
│   │   └── config.py                # Settings (Pydantic BaseSettings)
│   ├── db/
│   │   ├── base.py                  # DeclarativeBase
│   │   ├── session.py               # AsyncSession factory
│   │   └── models/                  # 21 archivos de modelos
│   │       ├── enums.py             # 6 enums (WarehouseType, MovementType, POStatus, etc.)
│   │       ├── alert.py             # StockAlert
│   │       ├── audit.py             # InventoryAuditLog
│   │       ├── batch.py             # EntityBatch
│   │       ├── category.py          # Category
│   │       ├── config.py            # ProductType, OrderType, CustomProductField, etc.
│   │       ├── cost.py              # EntityCost (FIFO layers)
│   │       ├── customer.py          # Customer, CustomerType, PriceList, PriceListItem
│   │       ├── customer_price.py    # CustomerPrice, CustomerPriceHistory
│   │       ├── cycle_count.py       # CycleCount, CycleCountItem, IRASnapshot
│   │       ├── event.py             # InventoryEvent, EventImpact, EventStatusLog, EventType/Severity/Status
│   │       ├── product.py           # Product (entities), StockIndex, EntityDepreciation
│   │       ├── production.py        # ProductionRun, Recipe, RecipeComponent
│   │       ├── purchase_order.py    # PurchaseOrder, PurchaseOrderLine
│   │       ├── reservation.py       # StockReservation
│   │       ├── sales_order.py       # SalesOrder, SalesOrderLine, SOApprovalLog, TenantInventoryConfig
│   │       ├── serial.py            # EntitySerial, SerialStatus
│   │       ├── stock.py             # StockLevel, StockMovement
│   │       ├── taxonomy.py          # TaxonomyVocabulary, VocabularyTerm, ProductTerm
│   │       ├── tax.py               # TaxRate
│   │       ├── variant.py           # ProductVariant, VariantAttribute, VariantAttributeOption
│   │       └── warehouse.py         # Warehouse, WarehouseLocation
│   ├── domain/
│   │   └── schemas/                 # 24 archivos Pydantic v2
│   ├── repositories/                # 25 archivos (data access layer)
│   └── services/                    # 31 archivos (logica de negocio)
│       ├── alert_service.py         # Generacion alertas + Kardex
│       ├── analytics_service.py     # KPIs, ABC, EOQ, ocupacion, valuacion
│       ├── approval_service.py      # Flujo aprobacion SO
│       ├── audit_service.py         # Logging de auditoria
│       ├── backorder_service.py     # Split automatico de SO
│       ├── batch_service.py         # Lotes + trazabilidad forward
│       ├── config_service.py        # Config dinamica (tipos, campos)
│       ├── cost_service.py          # Capas de costo FIFO
│       ├── customer_price_service.py# Precios especiales por cliente
│       ├── customer_service.py      # Clientes + tipos + listas precios
│       ├── cycle_count_service.py   # Conteos ciclicos + IRA
│       ├── dynamic_config_service.py# Tipos movimiento/bodega/evento/serial
│       ├── event_service.py         # Eventos/incidentes con impactos
│       ├── import_service.py        # Importacion CSV + demo seeding
│       ├── po_consolidation_service.py # Consolidacion de OC
│       ├── po_service.py            # Ciclo de vida OC
│       ├── portal_service.py        # Portal autoservicio clientes
│       ├── product_service.py       # CRUD productos + bloqueo campos
│       ├── production_service.py    # Produccion BOM + aprobacion 4-ojos
│       ├── reorder_service.py       # Reorden automatico
│       ├── reports_service.py       # Exportacion CSV
│       ├── reservation_service.py   # Reservas de stock para SO
│       ├── sales_order_service.py   # Ciclo de vida SO completo
│       ├── serial_service.py        # Seriales individuales
│       ├── stock_service.py         # Movimientos core de stock
│       ├── supplier_service.py      # CRUD proveedores
│       ├── tax_service.py           # Impuestos colombianos (IVA/retencion)
│       ├── taxonomy_service.py      # Vocabularios y terminos
│       └── variant_service.py       # Variantes de producto
├── main.py
└── requirements.txt
```

### Arbol de Carpetas — Frontend

```
front-trace/src/
├── pages/
│   ├── inventory/                   # 46 paginas
│   │   ├── InventoryDashboardPage.tsx    # Dashboard con recharts
│   │   ├── ProductsPage.tsx              # Catalogo de productos
│   │   ├── WarehousesPage.tsx            # Gestion de bodegas
│   │   ├── WarehouseDetailPage.tsx       # Detalle bodega + ubicaciones
│   │   ├── MovementsPage.tsx             # Historial movimientos
│   │   ├── SuppliersPage.tsx             # Proveedores
│   │   ├── PurchaseOrdersPage.tsx        # Ordenes de compra
│   │   ├── PurchaseOrderDetailPage.tsx   # Detalle OC + consolidacion
│   │   ├── SalesOrdersPage.tsx           # Ordenes de venta
│   │   ├── SalesOrderDetailPage.tsx      # Detalle OV completo
│   │   ├── CustomersPage.tsx             # Clientes
│   │   ├── CustomerDetailPage.tsx        # Detalle cliente + precios
│   │   ├── CustomerPortalPage.tsx        # Portal autoservicio
│   │   ├── CustomerPricesPage.tsx        # Precios especiales
│   │   ├── PriceListsPage.tsx            # Listas de precios
│   │   ├── PriceListDetailPage.tsx       # Items de lista
│   │   ├── CategoriesPage.tsx            # Categorias jerarquicas
│   │   ├── TaxonomyPage.tsx              # Vocabularios/terminos
│   │   ├── TaxRatesPage.tsx              # Tarifas IVA/retencion
│   │   ├── BatchesPage.tsx               # Lotes
│   │   ├── SerialsPage.tsx               # Seriales
│   │   ├── RecipesPage.tsx               # Recetas/formulas
│   │   ├── ProductionPage.tsx            # Ordenes de produccion
│   │   ├── CycleCountsPage.tsx           # Conteos ciclicos
│   │   ├── CycleCountDetailPage.tsx      # Detalle conteo + IRA
│   │   ├── EventsPage.tsx                # Eventos/incidentes
│   │   ├── AlertsPage.tsx                # Alertas de stock
│   │   ├── KardexPage.tsx                # Libro de inventario
│   │   ├── VariantsPage.tsx              # Variantes de producto
│   │   ├── ReorderConfigPage.tsx         # Config reorden automatico
│   │   ├── PendingApprovalsPage.tsx      # Cola de aprobaciones
│   │   ├── PickingPage.tsx               # Picking de SO
│   │   ├── ScannerPage.tsx               # Escaneo codigo barras
│   │   ├── InventoryConfigPage.tsx       # Config general
│   │   ├── ProductTypeListPage.tsx       # Tipos de producto
│   │   ├── ProductTypeDetailPage.tsx     # Detalle tipo + campos
│   │   ├── SupplierTypeListPage.tsx      # Tipos de proveedor
│   │   ├── SupplierTypeDetailPage.tsx    # Detalle tipo proveedor
│   │   ├── WarehouseTypeListPage.tsx     # Tipos de bodega
│   │   ├── WarehouseTypeDetailPage.tsx   # Detalle tipo bodega
│   │   ├── MovementTypeListPage.tsx      # Tipos de movimiento
│   │   ├── MovementTypeDetailPage.tsx    # Detalle tipo movimiento
│   │   ├── InventoryReportsPage.tsx      # Descarga CSV
│   │   ├── InventoryAuditPage.tsx        # Logs de auditoria
│   │   └── InventoryHelpPage.tsx         # Centro de ayuda
│   ├── EInvoicingPage.tsx                # Facturacion electronica DIAN
│   ├── EInvoicingSandboxPage.tsx         # Sandbox facturacion
│   └── EInvoicingResolutionPage.tsx      # Resoluciones DIAN
├── hooks/
│   └── useInventory.ts              # ~140 hooks React Query
├── lib/
│   └── inventory-api.ts             # 32 namespaces API, ~180 funciones
├── types/
│   └── inventory.ts                 # Todas las interfaces TypeScript
├── utils/
│   ├── generateRemissionPDF.ts      # PDF remision de entrega
│   └── generateSandboxInvoicePDF.ts # PDF factura sandbox
└── components/
    └── inventory/
        ├── ModuleGuard.tsx          # Gate: requiere modulo activo
        ├── ActivityTimeline.tsx      # Timeline de actividad
        ├── CopyableId.tsx           # Campo ID copiable
        └── VariantPicker.tsx        # Selector de variantes
```

### Patrones de Arquitectura

| Patron | Implementacion |
|--------|---------------|
| **Repository Pattern** | 25 repositorios en `app/repositories/`. Cada uno encapsula acceso a BD via SQLAlchemy async. Tupla `(list, count)` para paginacion. |
| **Service Layer** | 29 servicios en `app/services/`. Logica de negocio, validaciones, orquestacion. No acceden a BD directamente (usan repos). |
| **Dependency Injection** | FastAPI `Depends()`. Deps principales: `get_db_session`, `get_current_user`, `require_inventory_module`, `require_permission(slug)`. |
| **Module Gating** | `require_inventory_module` verifica activacion en Redis → fallback a subscription-service HTTP. Fail-closed (403). |
| **Background Tasks** | 2 scanners en `main.py` lifespan: alerta de expiracion (24h) y reorden automatico (24h). Graceful shutdown. |
| **Fire-and-Forget** | Facturacion electronica y notas credito: `_try_einvoice()` / `_try_credit_note()` nunca lanzan excepciones. |
| **Optimistic Locking** | `stock_repo.reserve()`: `UPDATE stock_levels SET qty_reserved = qty_reserved + :qty WHERE qty_on_hand - qty_reserved >= :qty RETURNING *`. Previene race conditions. |
| **FIFO Cost Layers** | `EntityCost` model + `cost_service.consume_fifo()` para costeo de produccion y despacho. |
| **Atomic Upsert** | `stock_repo.upsert_level()`: INSERT ON CONFLICT UPDATE para stock levels. |
| **Audit Trail** | `InventoryAuditService.log()` en toda mutacion. Registra user, action, old_data, new_data, IP. |
| **Soft Delete** | Productos, proveedores, bodegas, lotes usan `is_active = false`. |
| **Multi-Tenant** | `tenant_id` en TODAS las tablas. Filtrado en TODOS los queries. |

---

## 1.3 Modelos de Datos

### Enums

```
WarehouseType:       main | secondary | virtual | transit
MovementType:        purchase | sale | transfer | adjustment_in | adjustment_out
                     | return_ | waste | production_in | production_out
POStatus:            draft | sent | confirmed | partial | received | canceled | consolidated
SalesOrderStatus:    draft | pending_approval | confirmed | picking | shipped
                     | delivered | returned | canceled | rejected
CycleCountStatus:    draft | in_progress | completed | approved | canceled
CycleCountMethodology: control_group | location_audit | random_selection
                     | diminishing_population | product_category | abc
```

### Tablas Principales

---

#### TABLA: `entities` (Product)

**Descripcion:** Producto del catalogo de inventario.
**Migracion:** 001 (base), extendida en 017, 018, 019, 040, 046, 047.

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant owner |
| sku | String(100) | req | Codigo unico por tenant |
| barcode | String(100) | opt | Codigo de barras |
| name | String(255) | req | Nombre del producto |
| description | Text | opt | Descripcion larga |
| unit_of_measure | String(50) | req | UoM primaria (default: "unidad") |
| secondary_uom | String(50) | opt | UoM secundaria |
| uom_conversion_factor | Numeric(12,4) | opt | Factor de conversion |
| cost_price | Numeric(12,4) | req | Precio de costo (default: 0) |
| sale_price | Numeric(12,4) | req | Precio de venta (default: 0) |
| currency | String(3) | req | Moneda (default: "COP") |
| category_id | String(36) FK | opt | Categoria padre |
| product_type_id | String(36) FK | opt | Tipo de producto |
| min_stock_level | Integer | req | Stock minimo (default: 0) |
| reorder_point | Integer | req | Punto de reorden (default: 0) |
| reorder_quantity | Integer | req | Cantidad a reordenar (default: 0) |
| preferred_supplier_id | String(36) FK | opt | Proveedor preferido |
| auto_reorder | Boolean | req | Reorden automatico (default: false) |
| track_batches | Boolean | req | Rastrear por lotes (default: false) |
| valuation_method | String(20) | opt | fifo / lifo / average |
| is_active | Boolean | req | Activo (default: true) |
| images | JSONB | req | Array de URLs (default: []) |
| attributes | JSONB | req | Atributos custom (default: {}) |
| tax_rate_id | String(36) FK | opt | Tarifa IVA aplicable |
| is_tax_exempt | Boolean | req | Exento de IVA (default: false) |
| retention_rate | Numeric(5,4) | opt | Tasa retencion en la fuente |
| reciprocal_product_id | String(36) FK | opt | Producto reciproco (residuo) |
| created_at | DateTime(tz) | auto | Timestamp creacion |
| updated_at | DateTime(tz) | auto | Timestamp actualizacion |
| created_by | String(255) | opt | Usuario creador |
| updated_by | String(255) | opt | Ultimo editor |

**Relaciones:** category (Category), product_type (ProductType), preferred_supplier (Supplier), tax_rate (TaxRate), variants (ProductVariant[])
**Indices:** ix_entities_tenant_id, ix_entities_sku, ix_entities_product_type_id, uq_entity_tenant_sku UNIQUE(tenant_id, sku)

---

#### TABLA: `warehouses`

**Descripcion:** Bodega fisica o virtual para almacenamiento.
**Migracion:** 001 (base), 023 (max_stock_capacity).

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| name | String(255) | req | Nombre |
| code | String(50) | req | Codigo unico por tenant |
| warehouse_type | Enum(WarehouseType) | req | main/secondary/virtual/transit |
| warehouse_type_id | String(36) FK | opt | Tipo dinamico |
| address | Text | opt | Direccion |
| city | String(100) | opt | Ciudad |
| total_area_sqm | Numeric(10,2) | opt | Area total m2 |
| cost_per_sqm | Numeric(10,2) | opt | Costo por m2 |
| max_stock_capacity | Integer | opt | Capacidad maxima |
| is_active | Boolean | req | Activo (default: true) |
| created_at/updated_at | DateTime(tz) | auto | Timestamps |

**Relaciones:** locations (WarehouseLocation[])
**Indices:** ix_warehouses_tenant_id, uq_warehouse_tenant_code UNIQUE(tenant_id, code)

---

#### TABLA: `warehouse_locations`

**Descripcion:** Ubicacion fisica dentro de una bodega (estante, rack, bin).
**Migracion:** 001.

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| warehouse_id | String(36) FK | req | Bodega padre |
| code | String(50) | req | Codigo ubicacion |
| name | String(255) | req | Nombre |
| location_type | String(50) | opt | Tipo (rack, shelf, bin) |
| parent_location_id | String(36) FK | opt | Jerarquia de ubicaciones |
| is_active | Boolean | req | Activo |

**Indices:** uq_location_tenant_warehouse_code UNIQUE(tenant_id, warehouse_id, code)

---

#### TABLA: `stock_levels`

**Descripcion:** Cantidad actual de stock por producto/bodega/variante/lote.
**Migracion:** 001 (base), 013 (batch constraint), 019 (variant_id), 020 (qc_status), 029 (created_at).

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| product_id | String(36) FK | req | Producto |
| warehouse_id | String(36) FK | req | Bodega |
| variant_id | String(36) FK | opt | Variante |
| batch_id | String(36) FK | opt | Lote |
| location_id | String(36) FK | opt | Ubicacion |
| qty_on_hand | Integer | req | Cantidad en mano (default: 0) |
| qty_reserved | Integer | req | Reservado para OV (default: 0) |
| qty_in_transit | Integer | req | En transito (default: 0) |
| qc_status | String(20) | opt | pending_qc / approved / rejected |
| reorder_point | Integer | req | Override punto reorden |
| last_count_at | DateTime(tz) | opt | Ultimo conteo ciclico |
| created_at | DateTime(tz) | auto | Timestamp creacion |

**Indices:** uq_stock_level UNIQUE(tenant_id, product_id, warehouse_id, batch_id), ix_stock_levels_tenant_product_warehouse, ix_stock_levels_composite (30)

---

#### TABLA: `stock_movements`

**Descripcion:** Registro historico de cada movimiento de inventario.
**Migracion:** 001, 024 (status), 026 (uom), 028 (batch_id).

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| product_id | String(36) FK | req | Producto |
| warehouse_id | String(36) FK | req | Bodega origen/destino |
| variant_id | String(36) FK | opt | Variante |
| batch_id | String(36) FK | opt | Lote trazable |
| movement_type | Enum(MovementType) | req | Tipo de movimiento |
| quantity | Integer | req | Cantidad |
| secondary_qty | Numeric(12,4) | opt | Cantidad en UoM secundaria |
| uom | String(20) | opt | UoM usado |
| unit_cost | Numeric(12,4) | opt | Costo unitario |
| total_cost | Numeric(14,4) | opt | Costo total |
| reference | String(255) | opt | Referencia (PO, SO, etc.) |
| notes | Text | opt | Notas |
| to_warehouse_id | String(36) FK | opt | Bodega destino (transferencias) |
| location_id | String(36) FK | opt | Ubicacion |
| to_location_id | String(36) FK | opt | Ubicacion destino |
| status | String(20) | opt | pending / completed (transferencias 2 fases) |
| completed_at | DateTime(tz) | opt | Fecha completado |
| performed_by | String(255) | opt | Usuario |
| created_at | DateTime(tz) | auto | Timestamp |

**Indices:** ix_movements_tenant_id, ix_movements_product_id, ix_movements_type, ix_movements_created_at, ix_movements_batch (28, 30, 45)

---

#### TABLA: `stock_reservations`

**Descripcion:** Reservas de stock vinculadas a Sales Orders.
**Migracion:** 039.

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| sales_order_id | String(36) FK | req | Orden de venta |
| sales_order_line_id | String(36) FK | opt | Linea de OV |
| product_id | String(36) FK | req | Producto reservado |
| variant_id | String(36) FK | opt | Variante |
| warehouse_id | String(36) FK | req | Bodega |
| quantity | Numeric(12,4) | req | Cantidad reservada |
| status | String(20) | req | active / released / consumed |
| reserved_at | DateTime(tz) | auto | Fecha reserva |
| released_at | DateTime(tz) | opt | Fecha liberacion |
| released_reason | String(255) | opt | Razon de liberacion |

**Indices:** ix_reservations_so_id, ix_reservations_product_warehouse

---

#### TABLA: `suppliers`

**Descripcion:** Proveedor de mercancia.
**Migracion:** 001, 003 (supplier_type_id, custom_attributes).

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| name | String(255) | req | Razon social |
| code | String(50) | opt | Codigo interno |
| tax_id | String(50) | opt | NIT / RUT |
| email | String(255) | opt | Correo |
| phone | String(50) | opt | Telefono |
| address | Text | opt | Direccion |
| contact_name | String(255) | opt | Nombre contacto |
| payment_terms_days | Integer | opt | Plazo de pago |
| lead_time_days | Integer | opt | Tiempo de entrega |
| supplier_type_id | String(36) FK | opt | Tipo de proveedor |
| custom_attributes | JSONB | req | Campos custom (default: {}) |
| is_active | Boolean | req | Activo |

---

#### TABLA: `customers`

**Descripcion:** Cliente final (empresa compradora).
**Migracion:** 017.

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| name | String(255) | req | Razon social |
| code | String(50) | opt | Codigo unico |
| tax_id | String(50) | opt | NIT |
| email / phone / address | varios | opt | Contacto |
| contact_name | String(255) | opt | Persona contacto |
| customer_type_id | String(36) FK | opt | Tipo de cliente |
| price_list_id | String(36) FK | opt | Lista de precios asignada |
| credit_limit | Numeric(14,2) | opt | Limite de credito |
| discount_pct | Numeric(5,2) | req | Descuento global (default: 0) |
| custom_attributes | JSONB | req | Campos custom |
| is_active | Boolean | req | Activo |

---

#### TABLA: `purchase_orders`

**Descripcion:** Orden de compra a proveedor.
**Migracion:** 001, 002 (order_type_id), 040 (auto_reorder), 044 (consolidacion).

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| order_number | String(50) | req | Formato PO-YYYY-NNNN |
| supplier_id | String(36) FK | req | Proveedor |
| status | Enum(POStatus) | req | Estado (default: draft) |
| warehouse_id | String(36) FK | opt | Bodega destino |
| order_type_id | String(36) FK | opt | Tipo de orden |
| expected_date | Date | opt | Fecha esperada |
| received_date | Date | opt | Fecha recepcion |
| subtotal / tax_amount / total | Numeric(14,2) | req | Totales |
| notes | Text | opt | Notas |
| is_auto_reorder | Boolean | req | Generada por reorden |
| is_consolidated | Boolean | req | Resultado de consolidacion |
| consolidated_from_ids | JSONB | opt | IDs OC originales |
| parent_consolidated_id | String(36) FK | opt | OC consolidada padre |
| consolidated_at / consolidated_by | varios | opt | Metadata consolidacion |

**Indices:** uq_po_tenant_number UNIQUE(tenant_id, order_number), ix_po_status

---

#### TABLA: `purchase_order_lines`

**Descripcion:** Linea de una orden de compra.
**Migracion:** 001, 019 (variant_id).

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| order_id | String(36) FK | req | OC padre |
| product_id | String(36) FK | req | Producto |
| variant_id | String(36) FK | opt | Variante |
| warehouse_id | String(36) FK | opt | Bodega destino |
| location_id | String(36) FK | opt | Ubicacion destino |
| qty_ordered | Numeric(12,4) | req | Cantidad pedida |
| qty_received | Numeric(12,4) | req | Cantidad recibida (default: 0) |
| unit_cost | Numeric(12,4) | req | Costo unitario |
| line_total | Numeric(14,4) | req | Total linea |
| notes | Text | opt | Notas |
| uom | String(50) | opt | Unidad de medida |

---

#### TABLA: `sales_orders`

**Descripcion:** Orden de venta a cliente.
**Migracion:** 017 (base), 031-038 (facturacion, backorders, descuentos), 041 (remision), 042 (aprobacion), 047 (impuestos).

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| order_number | String(50) | req | Formato SO-YYYY-NNNN |
| customer_id | String(36) FK | req | Cliente |
| status | Enum(SalesOrderStatus) | req | Estado (default: draft) |
| warehouse_id | String(36) FK | opt | Bodega principal |
| shipping_address | JSONB | opt | Direccion de envio |
| expected_date | DateTime(tz) | opt | Fecha esperada |
| confirmed_at | DateTime(tz) | opt | Fecha confirmacion |
| shipped_date | DateTime(tz) | opt | Fecha despacho |
| delivered_date | DateTime(tz) | opt | Fecha entrega |
| subtotal | Numeric(14,2) | req | Subtotal antes descuento |
| tax_amount | Numeric(14,2) | req | IVA total |
| discount_pct | Numeric(5,2) | req | Descuento global % |
| discount_amount | Numeric(14,2) | req | Monto descuento |
| discount_reason | String(255) | opt | Razon descuento |
| total | Numeric(14,2) | req | Total |
| total_retention | Numeric(14,2) | req | Retencion total |
| total_with_tax | Numeric(14,2) | req | Subtotal + IVA |
| total_payable | Numeric(14,2) | req | Total a pagar (total - retencion) |
| currency | String(3) | req | Moneda (default: COP) |
| cufe | String(255) | opt | CUFE factura electronica |
| invoice_number | String(50) | opt | Numero factura |
| invoice_pdf_url | String(500) | opt | URL PDF factura |
| invoice_status | String(50) | opt | issued/simulated/failed |
| invoice_remote_id | String(255) | opt | ID en proveedor |
| invoice_provider | String(50) | opt | matias/sandbox |
| credit_note_cufe | String(255) | opt | CUFE nota credito |
| credit_note_number | String(50) | opt | Numero nota credito |
| credit_note_remote_id | String(255) | opt | ID NC en proveedor |
| credit_note_status | String(50) | opt | Estado nota credito |
| returned_at | DateTime(tz) | opt | Fecha devolucion |
| is_backorder | Boolean | req | Es backorder (default: false) |
| parent_so_id | String(36) FK | opt | OV padre (backorder) |
| backorder_number | Integer | req | Numero de backorder |
| remission_number | String(50) | opt | Numero remision |
| remission_generated_at | DateTime(tz) | opt | Fecha generacion remision |
| approval_required | Boolean | req | Requiere aprobacion |
| approved_by / approved_at | varios | opt | Aprobador |
| rejected_by / rejected_at / rejection_reason | varios | opt | Rechazo |
| approval_requested_at | DateTime(tz) | opt | Fecha solicitud |
| notes | Text | opt | Notas |
| extra_data | JSONB | req | Datos extra |

**Relaciones:** customer, warehouse, lines[], parent_so, backorders[]
**Indices:** uq_so_tenant_number, ix_so_tenant_id, ix_so_customer_id, ix_so_status, ix_so_tenant_status, ix_so_parent_so_id

---

#### TABLA: `sales_order_lines`

**Descripcion:** Linea de una orden de venta.
**Migracion:** 017, 019, 028, 036-038, 043, 047.

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| order_id | String(36) FK | req | OV padre |
| product_id | String(36) FK | req | Producto |
| variant_id | String(36) FK | opt | Variante |
| batch_id | String(36) FK | opt | Lote asignado |
| warehouse_id | String(36) FK | opt | Bodega especifica |
| qty_ordered | Numeric(12,4) | req | Cantidad pedida |
| qty_shipped | Numeric(12,4) | req | Cantidad despachada |
| original_quantity | Numeric(12,4) | opt | Qty pre-backorder |
| unit_price | Numeric(12,4) | req | Precio unitario |
| discount_pct | Numeric(5,2) | req | Descuento linea % |
| discount_amount | Numeric(12,4) | req | Monto descuento |
| line_subtotal | Numeric(12,4) | req | Subtotal linea |
| tax_rate | Numeric(5,2) | req | Tasa IVA % (legacy) |
| tax_rate_id | String(36) FK | opt | Referencia a tax_rates |
| tax_rate_pct | Numeric(5,4) | opt | Tasa IVA decimal |
| tax_amount | Numeric(14,4) | req | Monto IVA |
| retention_pct | Numeric(5,4) | opt | Tasa retencion |
| retention_amount | Numeric(14,4) | req | Monto retencion |
| line_total_with_tax | Numeric(14,4) | req | Total con IVA |
| line_total | Numeric(14,2) | req | Total linea |
| price_source | String(20) | opt | customer_special/price_list/product_base |
| customer_price_id | String(36) FK | opt | Referencia precio especial |
| backorder_line_id | String(36) FK | opt | Linea padre backorder |

---

#### TABLA: `tax_rates`

**Descripcion:** Tarifas de impuestos (IVA, retencion, ICA).
**Migracion:** 047.

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| name | String(100) | req | Nombre (IVA 19%, etc.) |
| tax_type | String(20) | req | iva / retention / ica |
| rate | Numeric(5,4) | req | Tasa decimal (0.19 = 19%) |
| dian_code | String(20) | opt | Codigo DIAN |
| is_default | Boolean | req | Default por tipo |
| is_active | Boolean | req | Activo |
| description | Text | opt | Descripcion |

**Indices:** ix_tax_rates_tenant_id, ix_tax_rates_tenant_type

---

#### TABLA: `customer_prices`

**Descripcion:** Precios especiales negociados por cliente/producto.
**Migracion:** 043.

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| customer_id | String(36) FK | req | Cliente |
| product_id | String(36) FK | req | Producto |
| variant_id | String(36) FK | opt | Variante |
| price | Numeric(12,4) | req | Precio negociado |
| min_quantity | Numeric(12,4) | req | Cantidad minima |
| currency | String(3) | req | Moneda |
| valid_from | Date | opt | Desde |
| valid_to | Date | opt | Hasta |
| reason | String(500) | opt | Razon del precio |
| is_active | Boolean | req | Activo |
| created_by / created_by_name | String | opt | Creador |

**Indices:** ix_customer_prices_customer, ix_customer_prices_product, uq_customer_price (tenant_id, customer_id, product_id, variant_id, min_quantity)

---

#### TABLA: `entity_batches`

**Descripcion:** Lotes de producto para trazabilidad.
**Migracion:** 004.

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| entity_id | String(36) FK | req | Producto |
| batch_code | String(100) | req | Codigo de lote |
| manufacture_date | Date | opt | Fecha fabricacion |
| expiration_date | Date | opt | Fecha vencimiento |
| supplier_id | String(36) FK | opt | Proveedor origen |
| cost | Numeric(12,4) | opt | Costo del lote |
| quantity | Integer | opt | Cantidad original |
| is_active | Boolean | req | Activo |

---

#### TABLA: `entity_serials`

**Descripcion:** Seriales individuales por unidad.
**Migracion:** 004.

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| entity_id | String(36) FK | req | Producto |
| serial_number | String(100) | req | Numero serial |
| batch_id | String(36) FK | opt | Lote asociado |
| warehouse_id | String(36) FK | opt | Bodega actual |
| location_id | String(36) FK | opt | Ubicacion |
| status_id | String(36) FK | opt | Estado dinamico |

---

#### TABLA: `cycle_counts`

**Descripcion:** Conteo ciclico de inventario.
**Migracion:** 010, 014.

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| tenant_id | String(255) | req | Tenant |
| warehouse_id | String(36) FK | req | Bodega |
| status | Enum(CycleCountStatus) | req | draft/in_progress/completed/approved/canceled |
| methodology | Enum(CycleCountMethodology) | opt | Metodologia |
| assigned_counters | Integer | opt | Contadores asignados |
| minutes_per_count | Integer | opt | Minutos por conteo |
| scheduled_date | Date | opt | Fecha programada |
| completed_at / approved_at | DateTime(tz) | opt | Timestamps |
| approved_by / created_by | String | opt | Usuarios |
| ira_qty / ira_value | Numeric(6,2) | opt | IRA calculado |
| notes | Text | opt | Notas |

**Relaciones:** items (CycleCountItem[])

---

#### TABLA: `recipes` + `recipe_components`

**Descripcion:** Recetas de produccion (BOM).
**Migracion:** 004.

| Columna (recipes) | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| name | String(255) | req | Nombre receta |
| output_product_id | String(36) FK | req | Producto producido |
| output_quantity | Numeric(12,4) | req | Cantidad output |
| yield_percentage | Numeric(5,2) | opt | Rendimiento % |
| is_active | Boolean | req | Activa |

| Columna (components) | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| recipe_id | String(36) FK | req | Receta padre |
| product_id | String(36) FK | req | Insumo |
| quantity | Numeric(12,4) | req | Cantidad por unidad |
| uom | String(50) | opt | Unidad |

---

#### TABLA: `production_runs`

**Descripcion:** Ordenes de produccion.
**Migracion:** 004, 015 (aprobacion).

| Columna | Tipo | Req | Descripcion |
|---------|------|-----|-------------|
| id | String(36) | PK | UUID |
| run_number | String(50) | req | Numero orden |
| recipe_id | String(36) FK | req | Receta base |
| warehouse_id | String(36) FK | req | Bodega produccion |
| status | String(20) | req | pending/in_progress/awaiting_approval/completed/rejected |
| scheduled_qty | Numeric(12,4) | req | Cantidad planificada |
| actual_qty | Numeric(12,4) | opt | Cantidad producida |
| total_cost | Numeric(14,4) | opt | Costo total |
| approved_by / rejected_by | String | opt | Aprobador |
| rejection_reason | Text | opt | Razon rechazo |
| performed_by | String(255) | opt | Ejecutor |

---

#### Tablas Adicionales

| Tabla | Descripcion | Migracion |
|-------|-------------|-----------|
| `product_categories` | Categorias jerarquicas de productos | 001, 046 |
| `product_types` | Tipos de producto con config QC, dispatch, lotes | 002 |
| `order_types` | Tipos de orden de compra | 002 |
| `supplier_types` | Tipos de proveedor | 003 |
| `customer_types` | Tipos de cliente | 017 |
| `price_lists` | Listas de precios multi-producto | 017 |
| `price_list_items` | Items de lista (producto, min_qty, precio) | 017 |
| `customer_price_history` | Historial cambios de precio por cliente | 043 |
| `product_variants` | Variantes (talla, color) con SKU propio | 017, 019 |
| `variant_attributes` | Atributos de variante (Color, Talla) | 017 |
| `variant_attribute_options` | Opciones (Rojo, Azul, S, M, L) | 017 |
| `entity_costs` | Capas de costo FIFO/LIFO | 004 |
| `entity_depreciation` | Depreciacion de activos | 018 |
| `stock_indexes` | MSI (Manufacturing Stock Index) | 018 |
| `stock_alerts` | Alertas de stock bajo/agotado/expirando | 017, 027 |
| `so_approval_logs` | Log de aprobaciones/rechazos de SO | 042 |
| `tenant_inventory_configs` | Config por tenant (umbral aprobacion) | 042 |
| `inventory_audit_logs` | Logs de auditoria de todo el modulo | 011, 016 |
| `inventory_events` | Eventos/incidentes de inventario | 004 |
| `event_impacts` | Impactos de eventos en entidades | 004 |
| `event_status_logs` | Transiciones de estado de eventos | 022 |
| `event_types` | Tipos de evento configurables | 004 |
| `event_severities` | Severidades de evento | 004 |
| `event_statuses` | Estados de evento | 004 |
| `serial_statuses` | Estados de serial configurables | 004 |
| `movement_types` | Tipos de movimiento custom | 004 |
| `warehouse_types` | Tipos de bodega custom | 004 |
| `custom_product_fields` | Campos custom por tipo de producto | 002, 006 |
| `custom_supplier_fields` | Campos custom por tipo proveedor | 003, 009 |
| `custom_warehouse_fields` | Campos custom por tipo bodega | 009 |
| `custom_movement_fields` | Campos custom por tipo movimiento | 009 |
| `taxonomy_vocabularies` | Vocabularios de clasificacion | 007 |
| `vocabulary_terms` | Terminos (tags) jerarquicos | 007 |
| `product_terms` | Asignacion producto-termino | 007 |
| `ira_snapshots` | Snapshots IRA por conteo ciclico | 010 |
| `cycle_count_items` | Items individuales de conteo | 010 |

### Diagrama de Relaciones

```
categories ──< entities (products)
                  ├──< product_variants
                  ├──< stock_levels
                  ├──< stock_movements
                  ├──< entity_batches
                  ├──< entity_serials
                  ├──< entity_costs (FIFO layers)
                  ├──< customer_prices
                  ├──> product_types
                  ├──> tax_rates
                  └──> preferred_supplier (suppliers)

warehouses ──< warehouse_locations
            ├──< stock_levels
            └──< stock_movements

suppliers ──< purchase_orders ──< purchase_order_lines ──> entities
                                                       ──> product_variants

customers ──< sales_orders ──< sales_order_lines ──> entities
          ├──> customer_types                     ──> product_variants
          ├──> price_lists ──< price_list_items   ──> entity_batches
          └──< customer_prices ──< customer_price_history

sales_orders ──< stock_reservations ──> stock_levels
             ├──< so_approval_logs
             ├──> parent_so (self-ref: backorders)
             └──> warehouses

recipes ──< recipe_components ──> entities
        ──< production_runs ──> warehouses

cycle_counts ──< cycle_count_items ──> entities
             ──< ira_snapshots

inventory_events ──< event_impacts
                 ──< event_status_logs
                 ──> event_types
                 ──> event_severities
                 ──> event_statuses

taxonomy_vocabularies ──< vocabulary_terms
                           ──< product_terms ──> entities
```

---

## 1.4 Endpoints REST

### Resumen por Router

| # | Router | Prefix | Endpoints | Permisos |
|---|--------|--------|-----------|----------|
| 1 | health | / | 2 | Ninguno |
| 2 | categories | /api/v1/categories | 5 | inventory.view/.manage |
| 3 | products | /api/v1/products | 8 | inventory.view/.manage |
| 4 | warehouses | /api/v1/warehouses | 5 | inventory.view/.manage |
| 5 | stock | /api/v1/stock | 14 | inventory.manage |
| 6 | movements | /api/v1/movements | 1 | inventory.view |
| 7 | suppliers | /api/v1/suppliers | 5 | inventory.view/.manage |
| 8 | purchase_orders | /api/v1/purchase-orders | 13 | inventory.view/.manage |
| 9 | sales_orders | /api/v1/sales-orders | 16+ | inventory.view/.manage/so.approve |
| 10 | customers | /api/v1/customers | 9 | inventory.view/.manage |
| 11 | customer_prices | /api/v1/customer-prices | 8+ | inventory.view/pricing.manage |
| 12 | tax_rates | /api/v1/tax-rates | 6 | inventory.view/.manage |
| 13 | analytics | /api/v1/analytics | 6 | reports.view |
| 14 | config | /api/v1/config | ~50 | inventory.config |
| 15 | reports | /api/v1/reports | 8 | reports.view |
| 16 | events | /api/v1/events | 5 | inventory.view/.manage |
| 17 | serials | /api/v1/serials | 5 | inventory.view/.manage |
| 18 | batches | /api/v1/batches | 8 | inventory.view/.manage |
| 19 | recipes | /api/v1/recipes | 5 | inventory.view/.manage |
| 20 | production | /api/v1/production-runs | 7 | inventory.view/.manage |
| 21 | cycle_counts | /api/v1/cycle-counts | 10+ | inventory.view/.manage |
| 22 | taxonomy | /api/v1/taxonomy | 10 | inventory.view/.manage |
| 23 | variants | /api/v1 (mixed) | 11 | inventory.view/.manage |
| 24 | alerts | /api/v1 (mixed) | 6 | inventory.view/.manage |
| 25 | audit | /api/v1/audit | 2 | admin.audit |
| 26 | imports | /api/v1/imports | 4 | inventory.manage/.config |
| 27 | portal | /api/v1/portal | 3 | inventory.view |
| 28 | reorder | /api/v1/reorder | 3 | inventory.manage |

**Total estimado: ~200+ endpoints**

### Detalle por Router

#### Products `/api/v1/products`

| Metodo | Path | Descripcion | Auth |
|--------|------|-------------|------|
| GET | / | Lista paginada (filtros: type, active, search, stock_status) | inventory.view |
| POST | / | Crear producto (auto-asigna taxonomia) | inventory.manage |
| GET | /{id} | Detalle producto (terms, has_movements) | inventory.view |
| PATCH | /{id} | Actualizar (bloquea SKU/UoM si tiene movimientos) | inventory.manage |
| DELETE | /{id} | Soft delete (valida no PO/recetas activas) | inventory.manage |
| POST | /{id}/images | Upload imagen (jpg/png/webp/gif, max 5MB) | inventory.manage |
| DELETE | /{id}/images | Eliminar imagen por URL | inventory.manage |
| GET | /{id}/customer-prices | Precios especiales del producto | inventory.view |

#### Stock `/api/v1/stock`

| Metodo | Path | Descripcion | Auth |
|--------|------|-------------|------|
| GET | / | Niveles de stock (filtros: product, warehouse, variant, location) | inventory.view |
| PATCH | /levels/{id}/location | Asignar ubicacion a nivel de stock | inventory.manage |
| POST | /receive | Recibir mercancia (crea movimiento purchase) | inventory.manage |
| POST | /issue | Despachar (crea movimiento sale) | inventory.manage |
| POST | /transfer | Transferencia inmediata entre bodegas | inventory.manage |
| POST | /transfer/initiate | Transferencia 2 fases: iniciar (PENDING) | inventory.manage |
| POST | /transfer/{id}/complete | Transferencia 2 fases: completar | inventory.manage |
| POST | /adjust | Ajuste a cantidad exacta | inventory.manage |
| POST | /adjust-in | Ajuste positivo (entrada) | inventory.manage |
| POST | /adjust-out | Ajuste negativo (salida) | inventory.manage |
| POST | /return | Devolucion de mercancia | inventory.manage |
| POST | /waste | Registrar merma/desperdicio | inventory.manage |
| POST | /qc-approve | Aprobar QC de lote | inventory.manage |
| POST | /qc-reject | Rechazar QC de lote | inventory.manage |

#### Purchase Orders `/api/v1/purchase-orders`

| Metodo | Path | Descripcion | Auth |
|--------|------|-------------|------|
| GET | / | Lista paginada (filtros: status, supplier) | inventory.view |
| POST | / | Crear borrador (auto-calcula totales) | inventory.manage |
| POST | /consolidate | Consolidar multiples OC draft al mismo proveedor | inventory.manage |
| GET | /consolidation-candidates | Oportunidades de consolidacion | inventory.view |
| GET | /{id} | Detalle OC | inventory.view |
| PATCH | /{id} | Actualizar (no received/canceled/consolidated) | inventory.manage |
| DELETE | /{id} | Eliminar (solo draft) | inventory.manage |
| POST | /{id}/send | draft → sent | inventory.manage |
| POST | /{id}/confirm | sent → confirmed | inventory.manage |
| POST | /{id}/cancel | Cancelar | inventory.manage |
| POST | /{id}/receive | Recibir lineas (partial o total, crea stock) | inventory.manage |
| GET | /{id}/consolidation-info | Info de consolidacion de esta OC | inventory.view |
| POST | /{id}/deconsolidate | Revertir consolidacion | inventory.manage |

#### Sales Orders `/api/v1/sales-orders`

| Metodo | Path | Descripcion | Auth |
|--------|------|-------------|------|
| GET | / | Lista paginada (filtros: status, customer) | inventory.view |
| GET | /summary | Conteo por estado | inventory.view |
| GET | /pending-approval | Cola de aprobacion | so.approve |
| POST | / | Crear OV (resolucion de precios 3 niveles) | inventory.manage |
| GET | /{id} | Detalle OV completo | inventory.view |
| PATCH | /{id} | Actualizar campos | inventory.manage |
| POST | /{id}/approve | Aprobar OV pendiente | so.approve |
| POST | /{id}/reject | Rechazar OV (reason requerida) | so.approve |
| POST | /{id}/ship | Despachar (genera remision, consume reservas) | inventory.manage |
| POST | /{id}/confirm-with-backorder | Confirmar con split de backorder | inventory.manage |
| GET | /{id}/stock-check | Verificar disponibilidad antes de confirmar | inventory.view |
| POST | /{id}/reserve | Reservar stock manualmente | inventory.manage |
| GET | /{id}/approvals | Historial de aprobaciones | inventory.view |
| GET | /{id}/batches | Trazabilidad: lotes usados en esta OV | inventory.view |
| PATCH | /{id}/lines/{line_id}/warehouse | Cambiar bodega de linea | inventory.manage |
| PATCH | /{id}/discount | Aplicar descuento global | inventory.manage |

#### Analytics `/api/v1/analytics`

| Metodo | Path | Descripcion | Auth |
|--------|------|-------------|------|
| GET | /overview | KPIs dashboard (SKUs, valor, tendencias, eventos) | reports.view |
| GET | /occupation | Ocupacion de bodegas (por ubicacion o capacidad) | reports.view |
| GET | /abc | Clasificacion ABC Pareto (A≤80%, B≤95%, C≤100%) | reports.view |
| GET | /eoq | EOQ Wilson formula por producto | reports.view |
| GET | /stock-policy | Rotacion vs target por tipo producto | reports.view |
| GET | /storage-valuation | Valuacion de almacenamiento por bodega | reports.view |

#### Reports `/api/v1/reports`

| Metodo | Path | Descripcion | Auth |
|--------|------|-------------|------|
| GET | /products | CSV productos | reports.view |
| GET | /stock | CSV niveles de stock | reports.view |
| GET | /suppliers | CSV proveedores | reports.view |
| GET | /movements | CSV movimientos (filtro fecha) | reports.view |
| GET | /events | CSV eventos (filtro fecha) | reports.view |
| GET | /serials | CSV seriales | reports.view |
| GET | /batches | CSV lotes | reports.view |
| GET | /purchase-orders | CSV ordenes de compra (filtro fecha) | reports.view |

---

## 1.5 Servicios y Logica de Negocio

### SalesOrderService (`sales_order_service.py`)

**Proposito:** Ciclo de vida completo de ordenes de venta.

| Funcion | Descripcion |
|---------|-------------|
| `list(tenant_id, **kwargs)` | Lista paginada con filtros |
| `get(order_id, tenant_id)` | Detalle con eager loading |
| `create(tenant_id, data, user)` | Crea OV. Resolucion de precios 3 niveles: customer_special → price_list → product_base. Calcula impuestos por linea. |
| `confirm(order_id, tenant_id, user)` | **Flujo critico**: Verifica aprobacion → reserva stock atomica → dispara facturacion electronica (fire-and-forget). Si stock insuficiente: lanza InsufficientStockError. |
| `ship(order_id, tenant_id, data, user)` | Genera remission_number, consume reservas, asigna lotes, actualiza qty_shipped, crea movimientos sale. Background: nada. |
| `deliver(order_id, tenant_id)` | shipped → delivered. Sin efectos secundarios. |
| `return_order(order_id, tenant_id)` | delivered → returned. Libera stock (incrementa qty_on_hand), dispara _try_credit_note (fire-and-forget). |
| `cancel(order_id, tenant_id)` | Libera reservas si existen, marca cancelado. |
| `_try_einvoice(order, tenant_id)` | **Fire-and-forget**: Selecciona provider (matias → sandbox → skip). POST integration-service. Nunca lanza excepciones. |
| `_try_credit_note(order, tenant_id)` | **Fire-and-forget**: Misma logica que _try_einvoice para notas credito. |
| `recalculate_so_totals(so)` | Recalcula todos los totales: subtotal, descuento, IVA, retencion, total payable. |

### ReservationService (`reservation_service.py`)

**Proposito:** Reservas atomicas de stock vinculadas a Sales Orders.

| Funcion | Descripcion |
|---------|-------------|
| `reserve_for_so(so, tenant_id)` | Para cada linea: valida bodega efectiva, ejecuta UPDATE atomico (qty_reserved += qty WHERE available >= qty), crea StockReservation(active). Lanza InsufficientStockError si falla. |
| `release_for_so(so_id, tenant_id, reason)` | Decrementa qty_reserved, marca status=released. Usado en cancelacion. |
| `consume_for_so(so, tenant_id)` | Decrementa qty_reserved, marca status=consumed. Usado en despacho. |
| `get_so_reservations(so_id)` | Lista reservas con eager loading. |

### ApprovalService (`approval_service.py`)

**Proposito:** Flujo de aprobacion de OV por monto.

| Funcion | Descripcion |
|---------|-------------|
| `requires_approval(so_total, tenant_id)` | True si total >= umbral del tenant |
| `request_approval(so, user)` | status → pending_approval, crea log |
| `approve(so, user)` | Valida creador ≠ aprobador (4 ojos), status → confirmed |
| `reject(so, user, reason)` | Valida reason >= 10 chars, status → rejected |
| `resubmit(so, user)` | rejected → pending_approval |
| `set_threshold(tenant_id, value)` | Configura umbral (null = desactivado) |

### BackorderService (`backorder_service.py`)

**Proposito:** Split automatico de OV cuando hay stock parcial.

| Funcion | Descripcion |
|---------|-------------|
| `analyze_and_split(so, tenant_id, user)` | Analiza disponibilidad por linea. Retorna {needs_backorder, confirmable_lines, backorder_lines, preview}. |
| `create_backorder(parent, backorder_lines, confirmable_lines, tenant_id, user)` | Crea SO hijo con sufijo -BO{N}. Ajusta cantidades de padre. Recalcula totales de ambos. |

### TaxService (`tax_service.py`)

**Proposito:** Sistema tributario colombiano.

| Funcion | Descripcion |
|---------|-------------|
| `initialize_tenant_rates(tenant_id)` | Idempotente: crea IVA 19%, 5%, 0% exento, retenciones 2.5%, 3.5% |
| `calculate_line_taxes(subtotal, tax_rate, retention)` | Calcula IVA + retencion por linea |
| `recalculate_so_taxes(so)` | Recalcula todas las lineas + totales del SO |
| `get_default_iva_rate(tenant_id)` | Retorna tarifa IVA por defecto (is_default=True) |

### StockService (`stock_service.py`)

**Proposito:** Core de movimientos de inventario.

| Funcion | Descripcion |
|---------|-------------|
| `receive(...)` | Incrementa qty_on_hand, crea movimiento purchase. Si QC requerido: qc_status=pending_qc. Asigna ubicacion. |
| `issue(...)` | Decrementa qty_on_hand. Aplica FEFO/LIFO si configurado en product_type. Valida no en QC. |
| `transfer_initiate(...)` | Decrementa origen, incrementa qty_in_transit destino. Status=pending. |
| `transfer_complete(id)` | Decrementa qty_in_transit destino, incrementa qty_on_hand. Status=completed. |
| `adjust(...)` | Calcula delta, ajusta a cantidad exacta. |
| `adjust_in/adjust_out(...)` | Ajustes directos positivos/negativos. |
| `waste(...)` | Decrementa como merma. |
| `qc_approve/qc_reject(...)` | Cambia qc_status de pending_qc. |

### POConsolidationService (`po_consolidation_service.py`)

**Proposito:** Consolidar multiples OC draft del mismo proveedor.

| Funcion | Descripcion |
|---------|-------------|
| `validate_consolidation(po_ids, tenant_id)` | Valida ≥2, todas draft, mismo proveedor |
| `consolidate(po_ids, tenant_id, user)` | Merge lineas por (product, variant, location, warehouse), costo promedio ponderado. Marca originales como consolidated. |
| `deconsolidate(po_id, tenant_id)` | Revierte: restaura originales a draft. |
| `get_consolidation_candidates(tenant_id)` | Proveedores con ≥2 draft POs. |

### AnalyticsService (`analytics_service.py`)

**Proposito:** KPIs y analisis avanzados.

| Funcion | Descripcion |
|---------|-------------|
| `overview(tenant_id)` | Dashboard: SKUs, valor, tendencias 30d, top 10 productos, alertas |
| `occupation(tenant_id, wh_id)` | Modo A: por ubicaciones. Modo B: por capacidad. Detecta stock estancado (180d). |
| `abc_classification(tenant_id, months)` | Pareto por valor de movimientos: A≤80%, B≤95%, C≤100% |
| `eoq(tenant_id, ordering_cost, holding_pct)` | Wilson: sqrt(2×D×S/H) por producto |
| `stock_policy(tenant_id)` | Meses en mano vs target de rotacion por tipo |
| `storage_valuation(tenant_id)` | Costo almacenamiento = area × costo/m2 por bodega |

### CycleCountService (`cycle_count_service.py`)

**Proposito:** Conteos ciclicos con IRA.

| Funcion | Descripcion |
|---------|-------------|
| `create_count(...)` | Crea snapshot de items del warehouse |
| `record_item_count(...)` | Registra conteo, calcula discrepancia |
| `recount_item(...)` | Segundo conteo con root_cause |
| `approve_count(...)` | **Aplica ajustes**: delta = counted - system, aplica a stock ACTUAL (no sobreescribe). Calcula IRA. |
| `compute_ira(...)` | accurate_items / total × 100. value_accuracy = (1 - abs_diff/system_value) × 100. |

### Otros Servicios

| Servicio | Proposito |
|----------|-----------|
| `ProductionService` | BOM: recetas + runs con aprobacion 4-ojos. Consume FIFO, produce output. |
| `ProductService` | CRUD. Bloquea SKU/UoM post-movimientos. Propaga ROP a stock_levels. |
| `ReorderService` | Scheduler 24h: productos con auto_reorder + stock < ROP → crea draft PO. |
| `ImportService` | CSV parse + demo seeding por industria (pet_food, technology, cleaning). |
| `AlertService` | Genera alertas low_stock/out_of_stock/expiring. Kardex con costo promedio ponderado. |
| `CustomerPriceService` | Lookup 3 niveles: customer_special → price_list → product_base. Historial. |
| `PortalService` | Vista cliente: stock visible, ordenes, detalle orden. |
| `CostService` | Capas FIFO: create_layer, consume_fifo, weighted_average_cost. |
| `ReportsService` | Exportacion CSV de cada entidad. |
| `BatchService` | Trazabilidad forward: lote → movimientos despacho → OV → clientes. |
| `AuditService` | Log con descripcion auto-generada. ~40 action codes cubiertos. |

---

## 1.6 Dependencias entre Servicios

### Comunicacion Inter-Servicio

```
inventory-service ──→ subscription-service (http://subscription-api:8002)
   │  GET /api/v1/modules/{tenant_id}/inventory
   │  Cache Redis: module:{tenant_id}:inventory TTL=300s
   │  Fail-closed: 403 si no responde
   │
   ├──→ integration-service (http://integration-api:8004)
   │  POST /api/v1/internal/invoices/{provider_slug}
   │  POST /api/v1/internal/credit-notes/{provider_slug}
   │  Header: X-Tenant-Id
   │  Timeout: 15s (httpx)
   │  Retry: NO (fire-and-forget, fallo silencioso)
   │
   └──→ user-service (http://user-api:8001)
      GET /api/v1/auth/me (validacion JWT)
      Cache Redis: inv_svc:me:{user_id} TTL=60s
      Fail: 503 Service Unavailable
```

### Variables de Entorno

| Variable | Default | Descripcion |
|----------|---------|-------------|
| DATABASE_URL | postgresql+asyncpg://inv_svc:invpass@inventory-postgres:5432/inventorydb | Conexion BD |
| REDIS_URL | redis://redis:6379/4 | Cache y module gates |
| USER_SERVICE_URL | http://user-api:8001 | Validacion JWT/usuario |
| SUBSCRIPTION_SERVICE_URL | http://subscription-api:8002 | Module gates |
| INTEGRATION_SERVICE_URL | http://integration-api:8004 | Facturacion electronica |
| JWT_SECRET | change-me-in-production-min-32-chars!! | Clave JWT HS256 |
| JWT_ALGORITHM | HS256 | Algoritmo JWT |
| USER_CACHE_TTL | 60 | Cache usuario (segundos) |
| MODULE_CACHE_TTL | 300 | Cache modulo (segundos) |
| MODULE_SLUG | inventory | Slug del modulo |
| UPLOAD_DIR | /app/uploads | Directorio imagenes |
| MAX_IMAGE_SIZE | 5242880 | Max imagen 5MB |
| DB_POOL_SIZE | 10 | Pool conexiones BD |
| DB_MAX_OVERFLOW | 20 | Overflow pool BD |
| DB_POOL_TIMEOUT | 30 | Timeout pool (s) |
| DB_POOL_RECYCLE | 1800 | Reciclar pool (s) |
| LOG_LEVEL | INFO | Nivel de logging |

---

## 1.7 Flujos Criticos

### Flujo: Confirmar Sales Order

```
1. Router: POST /api/v1/sales-orders/{id}/confirm
   → sales_orders.py → verify tenant ownership

2. ApprovalService.requires_approval(so.total, tenant_id)
   → Consulta TenantInventoryConfig.so_approval_threshold
   → Si total >= threshold:
     → ApprovalService.request_approval(so, user)
     → so.status = pending_approval
     → Crea SOApprovalLog(action="request")
     → Return 202 (needs approval)

3. Si no requiere aprobacion:
   → ReservationService.reserve_for_so(so, tenant_id)
   → Para cada linea:
     → warehouse = line.warehouse_id OR so.warehouse_id
     → stock_repo.reserve(product_id, warehouse_id, qty)
       → UPDATE stock_levels
         SET qty_reserved = qty_reserved + :qty
         WHERE tenant_id = :tid
           AND product_id = :pid
           AND warehouse_id = :wid
           AND (qty_on_hand - qty_reserved) >= :qty
         RETURNING *
     → Si 0 rows: raise InsufficientStockError
     → Crea StockReservation(status="active")

4. Si InsufficientStockError:
   → BackorderService.analyze_and_split(so, tenant_id)
   → Si hay lineas confirmables:
     → create_backorder(parent, backorder_lines, confirmable_lines)
     → Return {original_so, backorder_so, preview}
   → Si nada confirmable: Return 422

5. so.status = confirmed
   so.confirmed_at = utcnow()

6. Background (fire-and-forget):
   → SalesOrderService._try_einvoice(so, tenant_id)
     → Determina provider: matias (si modulo activo) → sandbox → skip
     → POST http://integration-api:8004/api/v1/internal/invoices/{provider}
       Body: {customer, lines, totals, tax_info}
       Header: X-Tenant-Id
       Timeout: 15s
     → integration-service:
       → ResolutionService.ensure_sandbox_resolution() (si sandbox)
       → ResolutionService.get_next_number() [UPDATE atomico]
       → Adapter.create_invoice(credentials, payload)
     → Response: {cufe, invoice_number, pdf_url, remote_id, status}
     → so.cufe, so.invoice_number, so.invoice_status = response
     → Si error: so.invoice_status = "failed" (silencioso)
```

### Flujo: Despachar (Ship) Sales Order

```
1. Router: POST /api/v1/sales-orders/{id}/ship
   Body: {line_shipments?, shipping_info?}

2. Valida: status == confirmed OR picking

3. Genera remission_number: "REM-{YYYY}-{SEQ:04d}"
   so.remission_number = generado
   so.remission_generated_at = utcnow()

4. Para cada linea:
   → Actualiza qty_shipped += qty
   → Si batch_id proporcionado: asigna lote a linea
   → Crea StockMovement(type=sale, qty, warehouse, batch)
   → Decrementa stock_level.qty_on_hand

5. ReservationService.consume_for_so(so, tenant_id)
   → Marca reservas como consumed
   → Decrementa qty_reserved

6. so.status = shipped
   so.shipped_date = utcnow()
   Si shipping_info: so.extra_data["shipping_info"] = data
```

### Flujo: Devolver (Return) Sales Order

```
1. Router: POST /api/v1/sales-orders/{id}/return
2. Valida: status == delivered OR shipped

3. Para cada linea despachada:
   → StockService.return_stock(product, warehouse, qty)
   → Incrementa stock_level.qty_on_hand
   → Crea StockMovement(type=return_)

4. so.status = returned
   so.returned_at = utcnow()

5. Background (fire-and-forget):
   → SalesOrderService._try_credit_note(so, tenant_id)
   → Requiere so.cufe existente (factura original)
   → POST http://integration-api:8004/api/v1/internal/credit-notes/{provider}
   → so.credit_note_cufe, so.credit_note_number, so.credit_note_status
```

### Flujo: Aprobar Sales Order

```
1. Router: POST /api/v1/sales-orders/{id}/approve
   → Requiere permiso: so.approve

2. ApprovalService.approve(so, user)
   → Valida so.status == pending_approval
   → Valida user != so.created_by (principio 4 ojos)
   → so.approved_by = user.id
   → so.approved_at = utcnow()
   → Crea SOApprovalLog(action="approve")

3. Continua flujo de confirmacion normal (reservas, facturacion)
```

### Flujo: Recibir Purchase Order

```
1. Router: POST /api/v1/purchase-orders/{id}/receive
   Body: {lines: [{line_id, qty_received, uom?}]}

2. Valida: status in (confirmed, partial)

3. Para cada recepcion:
   → Valida qty <= (qty_ordered - qty_received_actual)
   → StockService.receive(product, warehouse, qty, cost)
     → Upsert stock_level (qty_on_hand += qty)
     → Si product_type.requires_qc: qc_status = pending_qc
     → Asigna ubicacion (entry_rule_location_id)
     → Crea StockMovement(type=purchase)
   → line.qty_received += qty

4. Evalua estado:
   → Todas lineas 100% recibidas → po.status = received, received_date = today
   → Al menos una parcial → po.status = partial
```

### Flujo: Transferencia 2 Fases

```
Fase 1 — Iniciar:
  POST /api/v1/stock/transfer/initiate
  → stock_level_origen.qty_on_hand -= qty
  → stock_level_destino.qty_in_transit += qty
  → Crea StockMovement(status="pending", to_warehouse_id)

Fase 2 — Completar:
  POST /api/v1/stock/transfer/{movement_id}/complete
  → stock_level_destino.qty_in_transit -= qty
  → stock_level_destino.qty_on_hand += qty
  → movement.status = "completed"
  → movement.completed_at = utcnow()
```

---

## 1.8 Seguridad y Autenticacion

### Mecanismo de Autenticacion

```
JWT HS256 Token → HTTPBearer extraction
  → python-jose decode(token, JWT_SECRET, algorithms=["HS256"])
  → Valida token_type == "access"
  → Cache Redis: inv_svc:me:{user_id} (TTL 60s)
  → Fallback: GET user-service /api/v1/auth/me
  → Retorna: {id, email, tenant_id, permissions[], is_superuser}
```

### Module Gates

| Gate | Verifica | Cache Key | TTL | Comportamiento |
|------|----------|-----------|-----|----------------|
| `require_inventory_module` | Modulo inventory activo | `module:{tenant_id}:inventory` | 300s | Fail-closed: 403 |
| `is_einvoicing_active()` | Modulo electronic-invoicing | `module:{tenant_id}:electronic-invoicing` | 300s | Best-effort: False si falla |
| `is_einvoicing_sandbox_active()` | Modulo electronic-invoicing-sandbox | `module:{tenant_id}:electronic-invoicing-sandbox` | 300s | Best-effort: False si falla |

### Aislamiento Multi-Tenant

- **tenant_id** presente en TODAS las tablas principales (~55 tablas)
- **Filtrado**: Todos los queries en repositorios incluyen `WHERE tenant_id = :tid`
- **Extraction**: `current_user["tenant_id"]` del JWT decodificado
- **Endpoints sin filtro tenant**: Solo `/health` y `/ready` (probes K8s)

### Permisos Requeridos

| Permiso | Endpoints |
|---------|-----------|
| `inventory.view` | Todas las lecturas (GET) |
| `inventory.manage` | Todas las mutaciones (POST/PATCH/DELETE) |
| `inventory.config` | Config dinamica (/config/*) |
| `so.approve` | Aprobar/rechazar Sales Orders |
| `pricing.manage` | Crear/modificar precios especiales |
| `reports.view` | Analytics + reportes CSV |
| `admin.audit` | Logs de auditoria |

### Validaciones de Input

- **Pydantic v2**: Validacion automatica de tipos, required/optional
- **Limites de paginacion**: `limit: int = Query(le=200)` o `le=500` en warehouses
- **Regex validation**: `stock_status: str = Query(pattern="^(low|out)$")`
- **File upload**: Validacion MIME type (image/jpeg, image/png, image/webp, image/gif) + max 5MB
- **Field locking**: SKU, UoM, track_batches inmutables post-movimientos

---

## 1.9 Performance y Escalabilidad

### Indices de Base de Datos

| Tipo | Cantidad | Ejemplos |
|------|----------|----------|
| **Primary Key** | ~55 | Uno por tabla |
| **FK Index** | ~40 | ix_entities_product_type_id, ix_po_lines_order_id |
| **Lookup** | ~20 | ix_entities_sku, ix_movements_type, ix_so_status |
| **Compuesto** | ~15 | ix_stock_levels_tenant_product_warehouse, ix_so_tenant_status |
| **Unique** | ~10 | uq_entity_tenant_sku, uq_po_tenant_number, uq_stock_level |
| **Performance (045)** | ~5 | Indices de trazabilidad batch → movements → SO |

### Queries Criticas

| Query | Indice | Frecuencia |
|-------|--------|-----------|
| stock_levels por tenant+product+warehouse | uq_stock_level (UNIQUE) | Muy alta |
| sales_orders por tenant+status | ix_so_tenant_status (compuesto) | Alta |
| movements por tenant+product | ix_movements_product_id | Alta |
| reservations por SO | ix_reservations_so_id | Media |
| batches por entity_id | ix_batches_entity_id | Media |

### Paginacion

| Patron | Endpoints | Limite |
|--------|-----------|--------|
| `offset + limit` | Todos los listados | Default 50, max 200 |
| Sin paginacion | /analytics/*, /tax-rates, /variant-attributes | Lista completa |
| Warehouses | GET /api/v1/warehouses | Max 500 |

### Background Tasks

| Task | Frecuencia | Patron |
|------|-----------|--------|
| Expiry Alert Scanner | Cada 24h | Loop infinito en lifespan, asyncio.sleep(86400) |
| Auto-Reorder Scanner | Cada 24h | Loop infinito en lifespan, asyncio.sleep(86400) |
| E-invoicing trigger | Por evento (confirm SO) | Fire-and-forget, sin retry, silent catch |
| Credit note trigger | Por evento (return SO) | Fire-and-forget, sin retry, silent catch |

### Redis Cache

| Key Pattern | TTL | Proposito |
|-------------|-----|-----------|
| `module:{tenant_id}:inventory` | 300s | Module gate |
| `module:{tenant_id}:electronic-invoicing` | 300s | E-invoicing gate |
| `module:{tenant_id}:electronic-invoicing-sandbox` | 300s | Sandbox gate |
| `inv_svc:me:{user_id}` | 60s | Cache datos usuario |

**Estrategia de invalidacion:** TTL-based. No hay invalidacion activa. Los caches expiran naturalmente.

### Connection Pool

| Parametro | Valor |
|-----------|-------|
| DB_POOL_SIZE | 10 |
| DB_MAX_OVERFLOW | 20 |
| DB_POOL_TIMEOUT | 30s |
| DB_POOL_RECYCLE | 1800s (30min) |
| httpx timeout | 10s (global), 15s (integration-service) |

---

*Documento generado automaticamente basado en analisis del codigo fuente del modulo de inventario de TraceLog.*
*Fecha: 2026-03-13*
