# Plan: Modulo de Produccion v2

Referencia: SAP Business One — Manufacturacion Ligera + Produccion por Proceso

---

## Resumen Ejecutivo

Refactorizar el modulo de produccion para seguir el flujo estandar de SAP B1, separado como modulo independiente activado por suscripcion. El flujo actual (todo en un solo paso al aprobar) se reemplaza por pasos discretos con documentos separados que afectan inventario y costos progresivamente.

---

## Flujo Actual vs Flujo Objetivo

### Actual (simplificado, todo en approve)
```
Receta → Orden (pending) → Ejecutar (solo valida) → Finalizar → Aprobar (mueve TODO el stock) → Cerrado
```

### Objetivo (SAP B1, pasos discretos con afectacion contable)
```
Lista Materiales (BOM) → Orden Fabricacion (planificada)
                              ↓
                         Liberar orden (reserva materiales)
                              ↓
                         Emision para produccion (saca componentes de inventario → WIP)
                              ↓
                         Recibo de produccion (entra producto terminado, WIP → inventario)
                              ↓
                         Cierre de orden (calcula variaciones, mermas)
```

---

## Modelo de Datos — Cambios Requeridos

### 1. ProductionRun (orden de fabricacion) — MODIFICAR

**Status actual:** `pending → in_progress → awaiting_approval → completed/rejected`

**Status nuevo:**
```
planned       → Orden creada, sin afectacion
released      → Liberada, componentes reservados (qty_reserved)
in_progress   → Emision realizada, componentes sacados de inventario
completed     → Recibo realizado, producto terminado en inventario
closed        → Cierre contable, variaciones calculadas
canceled      → Cancelada (desde planned o released, sin movimiento)
rejected      → Rechazada en aprobacion (si se usa workflow de aprobacion)
```

**Campos nuevos:**
```python
# Orden
order_type         # 'standard' | 'special' | 'disassembly'
priority           # 0-100 (prioridad de fabricacion)
planned_start_date # Fecha inicio planificada
planned_end_date   # Fecha fin planificada
actual_start_date  # Fecha real inicio (cuando se emite)
actual_end_date    # Fecha real fin (cuando se recibe)
linked_sales_order_id  # FK logica a sales_order (make-to-order)
linked_customer_id     # FK logica a customer

# Cantidades reales vs planificadas
planned_quantity       # Ya existe como recipe.output_quantity * multiplier
actual_output_quantity # Cantidad realmente producida (puede ser < planned, merma)

# Costos
total_component_cost   # Costo total de componentes consumidos
total_resource_cost    # Costo de recursos (mano de obra, maquinaria) — futuro
total_production_cost  # component + resource
unit_production_cost   # total / actual_output_quantity
variance_amount        # Diferencia vs costo estandar
```

### 2. ProductionEmission (NUEVO) — Documento de emision

Documento separado que registra la salida de componentes de inventario hacia WIP.

```python
class ProductionEmission:
    id
    tenant_id
    production_run_id    # FK → production_runs
    emission_number      # EM-YYYY-NNNN
    status               # 'draft' | 'posted'
    emission_date        # Fecha contable
    warehouse_id         # De donde salen los componentes
    notes
    performed_by
    created_at

class ProductionEmissionLine:
    id
    emission_id          # FK → production_emissions
    component_entity_id  # FK → entities (componente)
    planned_quantity     # Cantidad esperada segun BOM
    actual_quantity      # Cantidad realmente emitida
    unit_cost            # Costo unitario (FIFO)
    total_cost           # actual_quantity * unit_cost
    batch_id             # Lote de donde sale (opcional)
    warehouse_id         # Bodega especifica (override)
    variance_quantity    # actual - planned (positivo = consumio de mas)
```

**Efecto contable:**
- Inventario (credito) → WIP/Produccion en Proceso (debito)
- Crea movimientos tipo `production_out` por cada componente

### 3. ProductionReceipt (NUEVO) — Documento de recibo

Documento separado que registra la entrada de producto terminado desde WIP a inventario.

```python
class ProductionReceipt:
    id
    tenant_id
    production_run_id    # FK → production_runs
    receipt_number       # RC-YYYY-NNNN
    status               # 'draft' | 'posted'
    receipt_date         # Fecha contable
    output_warehouse_id  # A donde entra el producto terminado
    notes
    performed_by
    created_at

class ProductionReceiptLine:
    id
    receipt_id           # FK → production_receipts
    entity_id            # FK → entities (producto terminado)
    planned_quantity     # Cantidad esperada
    received_quantity    # Cantidad realmente recibida
    unit_cost            # Costo unitario calculado
    total_cost
    batch_id             # Lote asignado al producto terminado (NUEVO)
    is_complete          # true = orden cumplida, false = parcial
```

**Efecto contable:**
- WIP/Produccion en Proceso (credito) → Inventario (debito)
- Crea movimiento tipo `production_in` por producto terminado
- Crea StockLayer con el costo calculado
- Opcionalmente crea EntityBatch para el producto terminado

### 4. Lista de Materiales (BOM) — AMPLIAR EntityRecipe

**Campos nuevos en EntityRecipe:**
```python
bom_type              # 'production' | 'assembly' | 'sales' | 'model'
standard_cost         # Costo estandar calculado (sum componentes + recursos)
planned_production_size  # Tamano de produccion promedio planificado
```

**Campos nuevos en RecipeComponent:**
```python
issue_method          # 'manual' | 'backflush' (backflush = automatico al recibir)
scrap_percentage      # % de merma esperada por componente
lead_time_offset_days # Dias de anticipacion para tener el componente
```

### 5. Desmontaje (Disassembly)

Tipo de orden `disassembly` que invierte el proceso:
- **Emision:** Saca el producto terminado de inventario
- **Recibo:** Regresa los componentes a inventario
- Util para desarmar productos defectuosos y recuperar componentes

---

## Endpoints API — Nuevos y Modificados

### Orden de Fabricacion (production_runs)
```
POST   /production-runs                    # Crear orden (status: planned)
GET    /production-runs                    # Listar con filtros
GET    /production-runs/{id}               # Detalle
PATCH  /production-runs/{id}               # Editar (solo planned)
POST   /production-runs/{id}/release       # planned → released (reserva stock)
POST   /production-runs/{id}/cancel        # planned|released → canceled (libera reservas)
DELETE /production-runs/{id}               # Solo planned
```

### Emision para Produccion (NUEVO)
```
POST   /production-runs/{id}/emissions     # Crear emision (saca componentes)
GET    /production-runs/{id}/emissions     # Listar emisiones de la orden
GET    /production-emissions/{id}          # Detalle de emision
```

### Recibo de Produccion (NUEVO)
```
POST   /production-runs/{id}/receipts      # Crear recibo (entra producto terminado)
GET    /production-runs/{id}/receipts      # Listar recibos de la orden
GET    /production-receipts/{id}           # Detalle de recibo
```

### Cierre de Orden
```
POST   /production-runs/{id}/close         # Cierre contable (calcula variaciones)
```

### Reportes
```
GET    /production/reports/open-orders     # Ordenes abiertas por status
GET    /production/reports/bom-list        # Lista de materiales con costos
GET    /production/reports/cost-variance   # Variaciones de costo
GET    /production/reports/production-log  # Log de produccion por periodo
```

---

## Frontend — Paginas

### Paginas Existentes (MODIFICAR)

**RecipesPage** — Agregar:
- Campo `bom_type` (produccion/conjunto/venta/modelo)
- Campo `planned_production_size`
- Costo estandar calculado visible
- Merma % por componente

**ProductionPage** — Reescribir completamente:
- Tabla de ordenes con filtro por status (planned/released/in_progress/completed/closed)
- Modal de crear orden con:
  - Tipo (estandar/especial/desmontaje)
  - Receta, bodega componentes, bodega salida
  - Cantidad planificada, multiplicador
  - Prioridad, fechas planificadas
  - Vinculo a OV (make-to-order) — opcional
- Detalle de orden con tabs:
  - **General**: info basica, status, fechas, prioridad
  - **Componentes**: lista con disponibilidad, cantidades planificadas vs reales
  - **Emisiones**: documentos de emision creados
  - **Recibos**: documentos de recibo creados
  - **Costos**: desglose componentes + recursos + variaciones
  - **Documentos**: adjuntos via MediaPickerModal

### Botones de Accion por Status

| Status | Acciones disponibles |
|--------|---------------------|
| planned | Editar, Liberar, Cancelar, Eliminar |
| released | Emitir Componentes, Cancelar |
| in_progress | Recibir Producto, ver emisiones |
| completed | Cerrar Orden |
| closed | Solo lectura, ver reportes |
| canceled | Solo lectura |

### Pagina Nueva: Dashboard de Produccion

KPIs:
- Ordenes planificadas vs liberadas vs en progreso
- Costo promedio de produccion por receta
- Tasa de rendimiento (actual_output / planned_quantity)
- Tiempo promedio de produccion (actual_start → actual_end)
- Top recetas por volumen
- Variaciones de costo acumuladas

---

## Integracion con Otros Modulos

### Con Inventario
- **Reserva al liberar**: `qty_reserved` se incrementa en stock_levels por cada componente
- **Emision**: crea movimientos `production_out`, consume FIFO layers, decrementa `qty_on_hand`
- **Recibo**: crea movimiento `production_in`, crea FIFO layer para producto terminado
- **Lotes**: opcionalmente crea EntityBatch para producto terminado
- **Alertas**: alerta cuando stock de componentes es insuficiente para ordenes planificadas

### Con Media
- Adjuntar documentos a ordenes de produccion (instrucciones, fotos, reportes QC)
- Cada emision y recibo puede tener documentos adjuntos
- Usar MediaPickerModal para todos los adjuntos

### Con Ventas (make-to-order)
- `linked_sales_order_id` vincula la orden de produccion a una OV
- Al completar la produccion, la OV puede avanzar a despacho

### Con Trazabilidad (trace-service)
- Al completar el recibo, opcionalmente crea Asset en trace-service via S2S
- El batch_id del producto terminado se referencia en el asset

---

## Migraciones de Base de Datos

### Migration 068: production_v2
```sql
-- Nuevas tablas
CREATE TABLE production_emissions (...)
CREATE TABLE production_emission_lines (...)
CREATE TABLE production_receipts (...)
CREATE TABLE production_receipt_lines (...)

-- Modificar production_runs
ALTER TABLE production_runs ADD COLUMN order_type VARCHAR(20) DEFAULT 'standard';
ALTER TABLE production_runs ADD COLUMN priority INTEGER DEFAULT 50;
ALTER TABLE production_runs ADD COLUMN planned_start_date TIMESTAMP;
ALTER TABLE production_runs ADD COLUMN planned_end_date TIMESTAMP;
ALTER TABLE production_runs ADD COLUMN actual_start_date TIMESTAMP;
ALTER TABLE production_runs ADD COLUMN actual_end_date TIMESTAMP;
ALTER TABLE production_runs ADD COLUMN actual_output_quantity NUMERIC(12,4);
ALTER TABLE production_runs ADD COLUMN total_component_cost NUMERIC(14,2);
ALTER TABLE production_runs ADD COLUMN total_production_cost NUMERIC(14,2);
ALTER TABLE production_runs ADD COLUMN unit_production_cost NUMERIC(14,6);
ALTER TABLE production_runs ADD COLUMN variance_amount NUMERIC(14,2);
ALTER TABLE production_runs ADD COLUMN linked_sales_order_id VARCHAR(36);
ALTER TABLE production_runs ADD COLUMN linked_customer_id VARCHAR(36);

-- Modificar entity_recipes
ALTER TABLE entity_recipes ADD COLUMN bom_type VARCHAR(20) DEFAULT 'production';
ALTER TABLE entity_recipes ADD COLUMN standard_cost NUMERIC(14,2) DEFAULT 0;
ALTER TABLE entity_recipes ADD COLUMN planned_production_size INTEGER DEFAULT 1;

-- Modificar recipe_components
ALTER TABLE recipe_components ADD COLUMN issue_method VARCHAR(20) DEFAULT 'manual';
ALTER TABLE recipe_components ADD COLUMN scrap_percentage NUMERIC(5,2) DEFAULT 0;
ALTER TABLE recipe_components ADD COLUMN lead_time_offset_days INTEGER DEFAULT 0;

-- Mapear status existentes
UPDATE production_runs SET status = 'planned' WHERE status = 'pending';
UPDATE production_runs SET status = 'closed' WHERE status = 'completed';
```

---

## Separacion del Modulo

El modulo de produccion se activa con `production` en el sistema de modulos de suscripcion (igual que logistics, compliance, etc.).

### Gating existente (ya funciona):
- Sidebar: seccion "Produccion" solo visible cuando `isProductionActive` es true
- Backend: `require_production_module` dependency en los endpoints
- Frontend: rutas protegidas con `ModuleGuard`

### Permisos:
- `production.view` — ver recetas y ordenes
- `production.manage` — crear, editar, emitir, recibir
- `production.approve` — aprobar/cerrar ordenes
- `production.admin` — configuracion del modulo

---

## Orden de Implementacion

### Fase 1 — Modelo de datos (backend)
1. Migration 068 con nuevas tablas y campos
2. Modelos SQLAlchemy para ProductionEmission, ProductionReceipt + lines
3. Repositorios para emisiones y recibos
4. Actualizar ProductionRun model con nuevos campos

### Fase 2 — Logica de negocio (backend)
1. Refactorizar ProductionService con nuevos estados
2. Implementar `release()` con reserva de stock
3. Implementar `create_emission()` con consumo FIFO
4. Implementar `create_receipt()` con creacion de producto + layer + batch
5. Implementar `close()` con calculo de variaciones
6. Implementar `cancel()` con liberacion de reservas
7. Soporte para desmontaje (order_type=disassembly)

### Fase 3 — API endpoints (backend)
1. Nuevos endpoints de emision y recibo
2. Endpoint de cierre
3. Endpoint de cancelacion
4. Modificar endpoints existentes para nuevos estados
5. Reportes

### Fase 4 — Frontend
1. Reescribir ProductionPage con tabs y nuevo flujo
2. Actualizar RecipesPage con campos nuevos
3. Dashboard de produccion con KPIs
4. Integracion con MediaPickerModal
5. Actualizar journey exportacion-eudr-completa.md

---

## Validaciones Importantes

1. **No se puede emitir sin liberar** — orden debe estar en `released`
2. **No se puede recibir sin emitir** — orden debe estar en `in_progress`
3. **No se puede cerrar sin recibir** — orden debe estar en `completed`
4. **Cancelar libera reservas** — si hay reservas, se devuelven
5. **Cancelar no se puede si ya hubo emision** — una vez emitido, solo cerrar
6. **4 ojos en aprobacion** — si se usa workflow, el que aprueba != el que ejecuta
7. **Stock re-validado** — al emitir, se re-valida disponibilidad (pudo cambiar desde release)
8. **Cantidad recibida <= planificada** — no se puede recibir mas de lo planificado
9. **Merma = planificada - recibida** — la diferencia se registra como variacion
