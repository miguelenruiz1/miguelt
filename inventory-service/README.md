# Trace Inventory Service

Microservicio de gestion de inventario empresarial para la plataforma **Trace**. Controla productos, bodegas, stock, movimientos, proveedores, compras, ventas, produccion, seriales, lotes, conteo ciclico, alertas, analitica avanzada y mas.

---

## Tabla de Contenidos

1. [Tecnologia](#tecnologia)
2. [Arquitectura](#arquitectura)
3. [Modelos de Datos](#modelos-de-datos)
4. [Enums](#enums)
5. [API Endpoints (210+)](#api-endpoints-210)
6. [Funcionalidades Clave](#funcionalidades-clave)
7. [Journey del Usuario](#journey-del-usuario)
8. [Migraciones](#migraciones)
9. [Variables de Entorno](#variables-de-entorno)
10. [Ejecucion](#ejecucion)

---

## Tecnologia

| Componente | Tecnologia |
|---|---|
| Lenguaje | Python 3.11 |
| Framework | FastAPI (async) |
| ORM | SQLAlchemy 2.0 (async, asyncpg) |
| Base de datos | PostgreSQL 15 |
| Cache | Redis (hiredis, db=4) |
| Migraciones | Alembic |
| Serializacion | Pydantic v2, orjson |
| HTTP Client | httpx (async) |
| Auth | JWT (python-jose), delegado a user-service |
| Contenedor | Docker (python:3.11-slim, 2 workers Uvicorn) |
| Puerto | 8003 (externo 9003) |

**Dependencias principales:** fastapi, uvicorn, uvloop, httptools, pydantic, pydantic-settings, orjson, sqlalchemy[asyncio], asyncpg, alembic, redis[hiredis], python-jose[cryptography], httpx, structlog, python-multipart.

---

## Arquitectura

```
inventory-service/
  app/
    main.py                 # FastAPI factory, lifespan, 23 routers
    api/
      deps.py               # Auth, permisos, module gating
      routers/              # 23 routers (210+ endpoints)
    db/
      base.py               # Declarative base
      session.py            # Async engine + session factory
      models/               # 17 archivos, 27+ tablas
    domain/
      schemas/              # Pydantic request/response schemas
    services/               # 25 servicios de logica de negocio
    repositories/           # 22 repositorios de acceso a datos
  alembic/
    versions/               # 21 migraciones
  Dockerfile
  requirements.txt
```

### Multi-Tenancy

Todas las tablas tienen `tenant_id`. Todas las queries estan scoped por tenant. El tenant se resuelve desde el JWT del usuario autenticado.

### Autenticacion y Permisos

- JWT Bearer token validado contra user-service (cache 60s en Redis)
- Module gating: verifica que el modulo `inventory` este activo para el tenant via subscription-service (cache 300s)
- Permisos: `inventory.view`, `inventory.manage`, `inventory.admin`, `reports.view`
- Superuser override en todos los endpoints

### Lifespan (startup)

1. DB connection pool warmup
2. Redis ping
3. HTTP client initialization (para user-service y subscription-service)

---

## Modelos de Datos

### Entidades Principales

| Modelo | Tabla | Descripcion |
|---|---|---|
| **Product** | `entities` | Catalogo maestro: SKU (unico/tenant), barcode, nombre, precios (cost/sale), UoM, atributos JSONB, imagenes JSONB, tipo de producto FK, metodo de valuacion, stock minimo, punto de reorden, cantidad de reorden |
| **Warehouse** | `warehouses` | Bodegas: codigo (unico/tenant), tipo (main/secondary/virtual/transit), tipo dinamico FK, direccion JSONB, costo por m², area total m², is_default |
| **WarehouseLocation** | `warehouse_locations` | Ubicaciones jerarquicas: parent FK (self-referencing), tipo (configurable), codigo, descripcion, sort_order |
| **StockLevel** | `stock_levels` | Nivel por producto/bodega/ubicacion/lote/variante: qty_on_hand, qty_reserved, qty_in_transit, qc_status (approved/pending_qc/rejected), weighted_avg_cost, last_count_at |
| **StockMovement** | `stock_movements` | Registro de movimiento: tipo (enum), producto, bodega origen/destino, cantidad, costo unitario, referencia, notas, variante, lote, performed_by |
| **Supplier** | `suppliers` | Proveedores: codigo, tipo FK, contacto, direccion JSONB, payment_terms_days, lead_time_days, custom_attributes JSONB |
| **PurchaseOrder** | `purchase_orders` | OC: po_number auto (PO-YYYY-NNNN), proveedor FK, bodega FK, tipo FK, estado (enum), fecha esperada/recibida |
| **PurchaseOrderLine** | `purchase_order_lines` | Lineas de OC: producto, variante, qty_ordered, qty_received, unit_cost |
| **Customer** | `customers` | Clientes: codigo, tipo FK, tax_id, contacto, direcciones JSONB, payment_terms, credit_limit, discount_percent, price_list FK, custom_attributes JSONB |
| **SalesOrder** | `sales_orders` | OV: order_number auto (SO-YYYY-NNNN), cliente FK, bodega FK, estado (enum), subtotal/tax/discount/total auto-calculados, metadata JSONB |
| **SalesOrderLine** | `sales_order_lines` | Lineas de OV: producto, variante, qty_ordered, qty_shipped, unit_price, discount_pct, tax_rate |
| **ProductVariant** | `product_variants` | Variantes: parent FK, SKU, barcode, precios, peso, option_values JSONB, imagenes JSONB |
| **EntityBatch** | `entity_batches` | Lotes: batch_number (unico/producto), fecha fabricacion, fecha vencimiento, costo, cantidad, metadata JSONB |
| **EntitySerial** | `entity_serials` | Seriales: serial_number (unico/producto), estado FK, bodega FK, ubicacion FK, lote FK, metadata JSONB |
| **EntityRecipe** | `entity_recipes` | Recetas/BOM: producto de salida FK, cantidad de salida, componentes (via RecipeComponent) |
| **RecipeComponent** | `recipe_components` | Componente de receta: producto FK, cantidad requerida |
| **ProductionRun** | `production_runs` | Corrida: receta FK, bodega FK, run_number auto, multiplicador, estado, aprobacion (by/at/notes) |
| **StockLayer** | `stock_layers` | Capas de costo FIFO: producto, bodega, movimiento FK, qty_initial, qty_remaining, unit_cost, lote FK |
| **CycleCount** | `cycle_counts` | Conteo ciclico: count_number, bodega, estado (enum), metodologia (enum), fecha programada, assigned_counters, minutes_per_count |
| **CycleCountItem** | `cycle_count_items` | Item de conteo: producto, ubicacion, lote, system_qty, counted_qty, discrepancia, recount_qty, root_cause, movement FK |
| **IRASnapshot** | `ira_snapshots` | Snapshot IRA: total_items, accurate_items, ira_percentage, total_system_value, total_counted_value, value_accuracy |
| **StockAlert** | `stock_alerts` | Alertas: producto, bodega, tipo, mensaje, current_qty, threshold_qty, is_read, is_resolved |
| **InventoryEvent** | `inventory_events` | Eventos: tipo FK, severidad FK, estado FK, bodega FK, descripcion, impact_details JSONB |
| **InventoryAuditLog** | `inventory_audit_logs` | Auditoria: user_id, email, name, accion, recurso tipo/id, old_data/new_data JSONB, descripcion, IP, user_agent |

### Configuracion Dinamica

| Modelo | Tabla | Campos clave |
|---|---|---|
| **ProductType** | `product_types` | nombre, slug, color, tracks_serials, tracks_batches, requires_qc, entry_rule_location_id, dispatch_rule (fifo/fefo/lifo), rotation_target_months |
| **OrderType** | `order_types` | nombre, slug, color |
| **DynamicMovementType** | `movement_types` | nombre, slug, direction (in/out), affects_cost, requires_reference, is_system |
| **DynamicWarehouseType** | `warehouse_types` | nombre, slug, color, is_system |
| **SupplierType** | `supplier_types` | nombre, slug, color |
| **CustomerType** | `customer_types` | nombre, slug, color |
| **SerialStatus** | `serial_statuses` | nombre, slug, color (ej: available, reserved, sold, damaged) |
| **EventType** | `event_types` | nombre, slug, color, auto_generate_movement_type_id |
| **EventSeverity** | `event_severities` | nombre, slug, weight, color |
| **EventStatus** | `event_statuses` | nombre, slug, is_final, color, sort_order |
| **PriceList** | `price_lists` | nombre, codigo, moneda, valid_from, valid_until, is_default |
| **PriceListItem** | `price_list_items` | producto FK, variante FK, unit_price, min_quantity, discount_pct |

### Campos Custom (extensibles por tipo)

| Tabla | Scoped a | Tipos de campo |
|---|---|---|
| `custom_product_fields` | `product_type_id` | text, number, date, boolean, select, url, email, reference |
| `custom_supplier_fields` | `supplier_type_id` | idem |
| `custom_warehouse_fields` | `warehouse_type_id` | idem |
| `custom_movement_fields` | `movement_type_id` | idem |

Los valores se almacenan en `custom_attributes` (JSONB) de la entidad correspondiente.

### Taxonomias (clasificacion flexible)

- **TaxonomyVocabulary** — Vocabulario por tipo de producto (ej: "Colores", "Tallas"), allow_multiple, is_required
- **TaxonomyTerm** — Terminos jerarquicos con parent FK, color, sort_order
- **ProductTermAssignment** — Many-to-many producto <-> termino

---

## Enums

```
WarehouseType:          main | secondary | virtual | transit
MovementType:           purchase | sale | transfer | adjustment_in | adjustment_out | return | waste | production_in | production_out
POStatus:               draft | sent | confirmed | partial | received | canceled
SalesOrderStatus:       draft | confirmed | picking | shipped | delivered | returned | canceled
CycleCountStatus:       draft | in_progress | completed | approved | canceled
CycleCountMethodology:  control_group | location_audit | random_selection | diminishing_population | product_category | abc
QCStatus:               approved | pending_qc | rejected
```

---

## API Endpoints (210+)

### Salud

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/health` | Status del servicio |
| GET | `/ready` | Verifica DB + Redis |

### Productos (`/api/v1/products`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Listar productos (paginado, filtro por tipo, estado, busqueda) |
| POST | `/` | Crear producto (SKU unico por tenant) |
| GET | `/{id}` | Detalle con terminos y flag `has_movements` |
| PATCH | `/{id}` | Actualizar producto |
| DELETE | `/{id}` | Eliminar (soft delete, auditado) |

### Bodegas (`/api/v1/warehouses`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Listar bodegas activas |
| POST | `/` | Crear bodega (codigo unico) |
| GET | `/{id}` | Detalle de bodega |
| PATCH | `/{id}` | Actualizar (incluye cost_per_sqm, total_area_sqm) |
| DELETE | `/{id}` | Eliminar (verifica no haya producciones activas) |

### Stock (`/api/v1/stock`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Niveles de stock (filtro por producto, bodega, variante) |
| POST | `/receive` | Recibir stock (auto-QC si tipo requiere, auto-ubicacion por regla de entrada) |
| POST | `/issue` | Despachar (bloqueo QC, regla FIFO/FEFO/LIFO segun tipo) |
| POST | `/transfer` | Transferir entre bodegas (genera 2 movimientos: salida + entrada) |
| POST | `/adjust` | Ajuste absoluto (establece cantidad exacta) |
| POST | `/adjust-in` | Ajuste de entrada (sobrante encontrado) |
| POST | `/adjust-out` | Ajuste de salida (faltante o merma) |
| POST | `/return` | Devolucion de cliente o proveedor |
| POST | `/waste` | Desperdicio/baja (producto danado, vencido) |
| POST | `/qc-approve` | Aprobar stock pendiente de QC |
| POST | `/qc-reject` | Rechazar stock por calidad |

### Ordenes de Compra (`/api/v1/purchase-orders`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Listar OC (filtro por estado, proveedor) |
| POST | `/` | Crear OC (numero auto: `PO-YYYY-NNNN`) |
| GET | `/{id}` | Detalle con lineas |
| PATCH | `/{id}` | Actualizar lineas (solo antes de enviar) |
| DELETE | `/{id}` | Eliminar borrador |
| POST | `/{id}/send` | Marcar como enviada |
| POST | `/{id}/confirm` | Confirmar |
| POST | `/{id}/cancel` | Cancelar (revierte movimientos) |
| POST | `/{id}/receive` | Recepcion parcial o total (actualiza stock automaticamente) |

### Ordenes de Venta (`/api/v1/sales-orders`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Listar OV (filtro por estado, cliente, bodega) |
| GET | `/summary` | KPIs por estado (draft, confirmed, picking, shipped...) |
| POST | `/` | Crear OV (numero auto: `SO-YYYY-NNNN`, totales auto-calculados) |
| GET | `/{id}` | Detalle con lineas |
| PATCH | `/{id}` | Actualizar (recalcula totales) |
| DELETE | `/{id}` | Eliminar borrador |
| POST | `/{id}/confirm` | Confirmar y reservar stock (qty_reserved) |
| POST | `/{id}/pick` | Iniciar picking |
| POST | `/{id}/ship` | Despachar (reduce qty_on_hand, genera movimientos de salida) |
| POST | `/{id}/deliver` | Marcar entregada |
| POST | `/{id}/return` | Devolucion (genera movimientos de entrada) |
| POST | `/{id}/cancel` | Cancelar (libera reserva de stock) |

### Proveedores (`/api/v1/suppliers`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Listar (busqueda, filtro activos) |
| POST | `/` | Crear (nombre, codigo, tipo, contacto, lead time, payment terms, custom_attributes) |
| GET | `/{id}` | Detalle |
| PATCH | `/{id}` | Actualizar |
| DELETE | `/{id}` | Eliminar |

### Clientes (`/api/v1/customers`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET/POST/PATCH/DELETE | `/config/customer-types` | CRUD tipos de cliente |
| GET | `/customers` | Listar clientes (busqueda, filtro activos) |
| POST | `/customers` | Crear (tipo, credito, descuento, lista de precios, custom_attributes) |
| GET | `/customers/{id}` | Detalle |
| PATCH | `/customers/{id}` | Actualizar |
| DELETE | `/customers/{id}` | Eliminar |
| GET | `/customers/{id}/prices` | Lista de precios aplicable |
| GET/POST | `/price-lists` | Listar/crear listas de precios |
| GET/PATCH/DELETE | `/price-lists/{id}` | Detalle/actualizar/eliminar |
| PUT | `/price-lists/{id}/items` | Reemplazar items de la lista (bulk) |

### Variantes (`/api/v1/variants`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET/POST/PATCH/DELETE | `/variant-attributes` | CRUD atributos (talla, color, etc.) |
| POST | `/variant-attributes/{id}/options` | Agregar opciones al atributo |
| PATCH/DELETE | `/variant-options/{id}` | Actualizar/eliminar opcion |
| GET | `/variants` | Listar variantes (busqueda, filtro por producto) |
| GET | `/products/{product_id}/variants` | Variantes de un producto |
| GET | `/variants/{id}` | Detalle |
| POST | `/variants` | Crear variante (parent_id, sku, option_values JSONB, precios) |
| PATCH | `/variants/{id}` | Actualizar |
| DELETE | `/variants/{id}` | Eliminar |

### Lotes (`/api/v1/batches`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Listar lotes (busqueda, filtro por producto) |
| POST | `/` | Crear lote (numero, fabricacion, vencimiento, costo, cantidad, metadata) |
| GET | `/{id}` | Detalle |
| PATCH | `/{id}` | Actualizar |
| DELETE | `/{id}` | Eliminar (si no tiene seriales/stock) |

### Seriales (`/api/v1/serials`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Listar seriales (busqueda, filtro por producto, estado, bodega) |
| POST | `/` | Crear serial (producto, numero unico, estado, ubicacion, lote) |
| GET | `/{id}` | Detalle |
| PATCH | `/{id}` | Actualizar estado/ubicacion |
| DELETE | `/{id}` | Eliminar |

### Recetas/BOM (`/api/v1/recipes`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Listar recetas |
| POST | `/` | Crear (producto salida, cantidad, componentes[{producto, qty}]) |
| GET | `/{id}` | Detalle con componentes |
| PATCH | `/{id}` | Actualizar receta y componentes |
| DELETE | `/{id}` | Eliminar |

### Produccion (`/api/v1/production`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Listar corridas (filtro por estado, receta, bodega) |
| POST | `/` | Crear corrida (receta, bodega, multiplicador) |
| GET | `/{id}` | Detalle |
| POST | `/{id}/execute` | Iniciar (crea capas de costo FIFO, consume componentes) |
| POST | `/{id}/finish` | Finalizar (genera producto terminado via FIFO layers) |
| POST | `/{id}/approve` | Aprobar |
| POST | `/{id}/reject` | Rechazar (revierte movimientos, guarda notas) |

### Conteo Ciclico (`/api/v1/cycle-counts`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Listar conteos (filtro por estado, bodega, metodologia) |
| POST | `/` | Crear conteo (bodega, metodologia, fecha, assigned_counters) |
| GET | `/analytics/ira-trend` | Tendencia de IRA en el tiempo |
| GET | `/analytics/product-history/{id}` | Historial de exactitud por producto |
| GET | `/{id}` | Detalle con items |
| POST | `/{id}/start` | Iniciar (genera items desde stock_levels actual) |
| POST | `/{id}/items/{item_id}/count` | Registrar conteo (system_qty auto, calcula discrepancia) |
| POST | `/{id}/items/{item_id}/recount` | Reconteo con segunda medicion |
| POST | `/{id}/complete` | Completar (genera IRASnapshot automaticamente) |
| POST | `/{id}/approve` | Aprobar (crea ajustes de stock por discrepancias) |
| POST | `/{id}/cancel` | Cancelar |
| GET | `/{id}/ira` | Calcular IRA (Inventory Record Accuracy %) |

### Eventos de Inventario (`/api/v1/events`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Listar eventos (filtro por tipo, severidad, estado, bodega) |
| POST | `/` | Crear evento (tipo, severidad, descripcion, impactos JSONB) |
| GET | `/{id}` | Detalle |
| POST | `/{id}/status` | Cambiar estado (si no es final) |
| POST | `/{id}/impacts` | Agregar impacto |

### Alertas y Kardex (`/api/v1/alerts`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/alerts` | Listar alertas (filtro por tipo, resueltas, leidas, bodega) |
| GET | `/alerts/unread-count` | Contador de no leidas |
| POST | `/alerts/{id}/read` | Marcar como leida |
| POST | `/alerts/{id}/resolve` | Marcar como resuelta |
| POST | `/alerts/scan` | Escanear stock y generar alertas (reorder_point, max_stock) |
| GET | `/kardex/{product_id}` | Historial valorizado de movimientos por producto |

### Analitica (`/api/v1/analytics`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/overview` | Dashboard KPIs: SKUs, valor total, bajo stock, sin stock, POs pendientes, top productos (30d), tendencia movimientos, breakdown por tipo producto/proveedor, IRA, conteos pendientes, lotes por vencer, produccion del mes |
| GET | `/occupation` | Ocupacion de bodegas: total/ocupadas/libres, %, por tipo ubicacion, por bodega, stock estancado (180+ dias) |
| GET | `/abc?months=12` | Clasificacion ABC: A (80% valor, ~20% items), B (15%), C (5%). Calculo por valor de movimiento acumulado |
| GET | `/eoq?ordering_cost=50&holding_cost_pct=25` | EOQ por producto: formula de Wilson sqrt(2DS/H), demanda anual, costo total optimo, ordenes/ano |
| GET | `/stock-policy` | Politica de rotacion: meses en mano vs objetivo por tipo de producto (ok/excess/no_data) |
| GET | `/storage-valuation` | Costo de almacenamiento: costo mensual por bodega ($/m² x area), costo/ubicacion, ratio almacenamiento/valor |

### Configuracion (`/api/v1/config`)

CRUD completo para:

| Recurso | Ruta base |
|---|---|
| Tipos de movimiento | `/movement-types` |
| Tipos de bodega | `/warehouse-types` |
| Ubicaciones | `/locations` |
| Tipos de producto | `/product-types` |
| Tipos de orden | `/order-types` |
| Campos custom producto | `/custom-fields` |
| Tipos de proveedor | `/supplier-types` |
| Campos custom proveedor | `/supplier-fields` |
| Campos custom bodega | `/warehouse-fields` |
| Campos custom movimiento | `/movement-fields` |
| Tipos de evento | `/event-types` |
| Severidades de evento | `/event-severities` |
| Estados de evento | `/event-statuses` |
| Estados de serial | `/serial-statuses` |

### Taxonomias (`/api/v1/taxonomy`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET/POST | `/vocabularies` | Listar/crear vocabularios (por tipo de producto) |
| GET/PATCH/DELETE | `/vocabularies/{id}` | Detalle/actualizar/eliminar |
| POST | `/terms` | Crear termino jerarquico (vocabulario, padre, nombre, color) |
| PATCH/DELETE | `/terms/{id}` | Actualizar/eliminar termino |
| GET | `/products/{id}/terms` | Terminos asignados a un producto |
| PUT | `/products/{id}/terms` | Asignar terminos (bulk replace) |

### Auditoria (`/api/v1/audit`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Log de auditoria (filtro por accion, recurso, usuario, fechas) |
| GET | `/entity/{type}/{id}` | Timeline de actividad de una entidad especifica |

### Importacion (`/api/v1/imports`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| POST | `/products` | Importacion masiva CSV (multipart file) |
| GET | `/templates/{name}` | Descargar plantilla CSV (basic, pet_food, technology, cleaning) |
| POST | `/demo` | Cargar datos demo por industria (pet_food, technology, cleaning) |
| DELETE | `/demo` | Eliminar datos demo |

### Reportes (`/api/v1/reports`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/products` | Exportar productos CSV |
| GET | `/stock` | Exportar niveles de stock CSV |
| GET | `/movements` | Exportar movimientos CSV (filtro por fechas) |
| GET | `/suppliers` | Exportar proveedores CSV |

### Portal de Cliente (`/api/v1/portal`)

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/stock?customer_id={id}` | Stock disponible para el cliente |
| GET | `/orders?customer_id={id}` | Ordenes del cliente (filtro por estado) |
| GET | `/orders/{order_id}` | Detalle de orden con lineas, totales, envio |

---

## Funcionalidades Clave

### 1. Control de Calidad (QC)

Cuando `ProductType.requires_qc = true`:
- Todo stock recibido entra como `pending_qc`
- Stock pendiente de QC **no puede ser despachado**
- Se aprueba o rechaza desde `/stock/qc-approve` y `/stock/qc-reject`
- Botones de aprobacion/rechazo visibles en la tabla de stock de cada bodega

### 2. Reglas de Despacho (FIFO / FEFO / LIFO)

Configurado por `ProductType.dispatch_rule`:
- **FIFO** (default): Consume primero el stock mas antiguo por fecha de ingreso
- **FEFO**: Consume primero el lote con fecha de vencimiento mas cercana (perecederos, farmaceuticos)
- **LIFO**: Consume primero el stock mas reciente

### 3. Regla de Entrada Automatica

Si `ProductType.entry_rule_location_id` esta configurado, al recibir stock de ese tipo se ubica automaticamente en la ubicacion indicada sin necesidad de seleccion manual.

### 4. Clasificacion ABC

Calculo automatico basado en el principio de Pareto:
- **A** (~20% productos, ~80% valor): Control estricto, conteo mensual, negociacion prioritaria
- **B** (~30% productos, ~15% valor): Control moderado, conteo trimestral
- **C** (~50% productos, ~5% valor): Control ligero, conteo semestral

### 5. EOQ (Cantidad Optima de Pedido)

Formula de Wilson: `EOQ = sqrt(2 * D * S / H)`
- D = Demanda anual (calculada de movimientos ultimos 12 meses)
- S = Costo por pedido (parametro configurable, default $50)
- H = Costo mantenimiento por unidad/ano (precio * % holding, default 25%)

### 6. Politica de Rotacion

Cada tipo de producto define `rotation_target_months` (meses objetivo de inventario).
El sistema compara stock actual / consumo mensual promedio vs el objetivo:
- `ok`: Dentro del rango
- `excess`: Sobre-stock (se muestra el exceso en meses)
- `no_data`: Sin consumo registrado

### 7. Costo de Almacenamiento

Cada bodega puede configurar `cost_per_sqm` y `total_area_sqm`:
- Costo mensual = $/m² x area
- Costo por ubicacion = costo mensual / # ubicaciones
- Ratio almacenamiento/valor = costo mensual / valor del stock

### 8. Ocupacion de Bodegas

KPIs en tiempo real:
- Ubicaciones totales, ocupadas, libres
- % de ocupacion (global y por bodega)
- Desglose por tipo de ubicacion
- Stock estancado (180+ dias sin movimiento)

### 9. Conteo Ciclico con IRA

6 metodologias: control_group, location_audit, random_selection, diminishing_population, product_category, abc

Flujo: `draft → in_progress → completed → approved`
- Al completar: genera IRASnapshot automatico
- Al aprobar: crea ajustes de stock por cada discrepancia
- IRA = items exactos / items totales * 100

### 10. Produccion / BOM

Flujo: `pending → in_progress → completed → approved` (o `rejected`)
- Recetas con lista de componentes y cantidades
- Corridas con multiplicador (ej: multiplicador 5 = 5x la receta)
- Capas de costo FIFO para valuacion exacta
- Aprobacion opcional con notas de rechazo

### 11. Portal de Cliente

Vista de solo lectura para clientes:
- Stock disponible de sus productos
- Estado de sus pedidos (ordenes de venta)
- Detalle de cada orden con lineas

### 12. Auditoria Completa

Todas las mutaciones (create/update/delete) generan un audit log con:
- Usuario (id, nombre, email)
- Accion ejecutada
- Recurso afectado (tipo + id)
- Datos antes y despues (diff JSONB)
- Descripcion legible en espanol
- IP y user agent
- Timeline por entidad en paginas de detalle

### 13. Campos Custom Extensibles

Los formularios de productos, proveedores, bodegas y movimientos son extensibles con campos custom por tipo. Los valores se almacenan en JSONB (`custom_attributes`).

### 14. Taxonomias (clasificacion flexible)

Sistema inspirado en Drupal: vocabularios con terminos jerarquicos asignables a productos. Permite clasificaciones multiples (ej: "Color: Rojo" + "Talla: M" + "Material: Algodon").

---

## Journey del Usuario

### Fase 1: Configuracion Inicial

1. **Activar modulo** en el Marketplace del tenant
2. **Crear tipos de producto** (ej: "Perecederos" con FEFO + QC, "Electronicos" con seriales)
3. **Crear bodegas** con codigo, tipo, costo/m² y area
4. **Crear ubicaciones** jerarquicas: Zona > Pasillo > Rack > Bin
5. **Configurar tipos** de proveedor, cliente, movimiento, bodega
6. **Agregar campos custom** especificos por tipo
7. **Opcionalmente cargar datos demo** por industria

### Fase 2: Catalogo de Productos

1. Crear productos con SKU, precios, tipo, UoM, stock minimo
2. Asignar taxonomias (vocabularios y terminos)
3. Crear variantes (talla, color, presentacion)
4. Importar masivamente via CSV

### Fase 3: Abastecimiento (Compras)

1. Registrar proveedores con contacto y lead time
2. Crear orden de compra → Enviar → Confirmar
3. Recibir mercaderia (parcial o total)
4. Stock pasa por QC automatico si el tipo lo requiere
5. Stock se ubica automaticamente si hay regla de entrada

### Fase 4: Almacenamiento y Control

1. Monitorear ocupacion en dashboard
2. Controlar vencimientos de lotes
3. Tracking de seriales con estados
4. Conteos ciclicos periodicos (6 metodologias)
5. Clasificacion ABC para priorizar control
6. Alertas automaticas de stock bajo/exceso

### Fase 5: Despacho (Ventas)

1. Registrar clientes con tipo, credito y lista de precios
2. Crear orden de venta → Confirmar (reserva stock)
3. Picking → Despachar (FIFO/FEFO/LIFO segun tipo) → Entregar
4. Devoluciones si aplica

### Fase 6: Produccion

1. Crear recetas (BOM) con componentes
2. Crear corridas con multiplicador
3. Ejecutar → Finalizar → Aprobar
4. Capas de costo FIFO para valuacion exacta

### Fase 7: Analitica Avanzada

1. Dashboard con KPIs en tiempo real
2. Clasificacion ABC para identificar productos criticos
3. EOQ para optimizar cantidades de pedido
4. Politica de rotacion para detectar sobre-stock
5. Costo de almacenamiento para evaluar eficiencia
6. Kardex para historial valorizado

### Fase 8: Operacion Continua

1. Reportes CSV descargables
2. Auditoria completa de acciones
3. Eventos de inventario para incidentes
4. Portal de cliente para autoservicio

---

## Migraciones

| # | Archivo | Descripcion |
|---|---|---|
| 001 | `001_initial.py` | Tablas base: productos, bodegas, stock, proveedores, OC, movimientos. Seed: 1 bodega MAIN + 4 categorias |
| 002 | `002_custom_types.py` | ProductType, OrderType, CustomProductFields |
| 003 | `003_supplier_types.py` | SupplierType, CustomSupplierFields |
| 004 | `004_entity_engine.py` | Eventos, tracking (seriales/lotes), produccion (recetas, corridas), taxonomia base |
| 005 | `005_field_api.py` | Field API (bundles, storages, instances) |
| 006 | `006_custom_field_product_type.py` | Scope custom fields a product_type_id |
| 007 | `007_taxonomy_system.py` | TaxonomyVocabulary, TaxonomyTerm, ProductTermAssignment |
| 008 | `008_reference_field_type.py` | Tipo de campo "reference" |
| 009 | `009_type_scoped_custom_fields.py` | CustomWarehouseFields, CustomMovementFields, supplier_type_id FK |
| 010 | `010_cycle_counts.py` | CycleCount, CycleCountItem, IRASnapshot |
| 011 | `011_audit_trail.py` | InventoryAuditLog, created_by/updated_by en todas las tablas |
| 012 | `012_production_movement_types.py` | Enum production_in/production_out |
| 013 | `013_stock_batch_constraint.py` | Unique constraint con batch_id en stock_levels |
| 014 | `014_cycle_count_columns.py` | Metodologia, assigned_counters, minutes_per_count |
| 015 | `015_production_approval.py` | Columnas de aprobacion en production_runs |
| 016 | `016_audit_description.py` | Descripcion legible y user_name en audit logs |
| 017 | `017_customers_sales_variants_alerts.py` | Clientes, OV, variantes, alertas, listas de precios |
| 018 | `018_enterprise_features.py` | valuation_method, secondary_uom, stock indexes |
| 019 | `019_variant_integration.py` | variant_id FK en stock, movimientos, OC; unique con COALESCE |
| 020 | `020_qc_and_features.py` | QC blocking (qc_status), dispatch rules, entry rules |
| 021 | `021_abc_eoq_storage.py` | cost_per_sqm, total_area_sqm en warehouses; rotation_target_months en product_types |

---

## Variables de Entorno

| Variable | Descripcion | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL async URL | `postgresql+asyncpg://inv_svc:invpass@inventory-postgres:5432/inventorydb` |
| `REDIS_URL` | Redis URL | `redis://redis:6379/4` |
| `USER_SERVICE_URL` | URL del user-service para auth | `http://user-api:8001` |
| `SUBSCRIPTION_SERVICE_URL` | URL del subscription-service para module gating | `http://subscription-api:8002` |
| `APP_VERSION` | Version del servicio | `1.0.0` |
| `MODULE_SLUG` | Slug del modulo | `inventory` |
| `USER_CACHE_TTL` | TTL cache de usuario JWT (segundos) | `60` |
| `MODULE_CACHE_TTL` | TTL cache de activacion de modulo (segundos) | `300` |
| `DB_POOL_SIZE` | Pool de conexiones DB | `5` |
| `DB_MAX_OVERFLOW` | Overflow del pool | `10` |
| `DB_POOL_TIMEOUT` | Timeout del pool (segundos) | `30` |
| `DB_POOL_RECYCLE` | Reciclaje de conexiones (segundos) | `1800` |

---

## Ejecucion

### Con Docker Compose (desde la raiz del proyecto)

```bash
docker-compose up inventory-service
```

### Desarrollo local

```bash
cd inventory-service
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

### Verificar servicio

```bash
curl http://localhost:9003/health
# {"status": "ok", "service": "inventory-service"}

curl http://localhost:9003/ready
# {"status": "ready", "db": true, "redis": true}
```

### Ejecutar migraciones

```bash
cd inventory-service
alembic upgrade head
```
