# Plan — Motor WM de Inventario (Odoo + SAP WM → Trace)

> Objetivo: llevar nuestro `inventory-service` al nivel de un **WMS real**, tomando
> los conceptos **ya probados** de Odoo Inventory y SAP WM. **No inventamos nada**:
> replicamos modelos consolidados, adaptados a nuestra arquitectura.
>
> Filosofía (de Odoo): **simple por defecto, potente cuando se activa**. Una bodega
> con 1 ubicación y recepción/entrega en 1 paso funciona out-of-the-box; el árbol de
> ubicaciones, los pasos múltiples, el putaway y las órdenes de transporte se prenden
> cuando la empresa los necesita.

---

## 1. Los dos modelos son el mismo (mapa conceptual unificado)

| Concepto | Odoo | SAP WM | En Trace (qué hacemos) |
|---|---|---|---|
| Almacén físico (complejo) | Warehouse | Número de almacén | `Warehouse` (ya existe) + `short_code` |
| Subdivisión por forma de almacenar | Location type | **Tipo de almacén** (rack/bloque/picking/lógico) | **NUEVO** `StorageType` |
| Agrupación por regla de negocio | (categoría) | **Área de almacenamiento** (alta/baja rotación) | **NUEVO** `StorageSection` |
| Ubicación física mínima | Location | **Ubicación / bin (nicho)** | `WarehouseLocation` (extender) |
| Stock lógico por material+lote en un bin | Quant | **Cuanto (quant)** | `StockLevel` (ya es esto) |
| Documento de todo movimiento | Stock Move + Picking | **Orden de transporte (TO)** + Necesidad de transporte | **NUEVO** `TransferOrder` (+ `TransferRequirement`) |
| Tipo de movimiento | Operation/Picking type | **Clase de movimiento** (101, 201…) | **NUEVO** `OperationType` (mapea `MovementType`) |
| Pasos del flujo | Rutas 1/2/3 (pick/pack/out) | Interim + TO en 2 confirmaciones | **NUEVO** `Route` + `RouteRule` |
| Zonas de tránsito | Input/Output/Pre-Post-prod | **Almacenes intermedios (9xx)**: recepción, despacho, producción, QA | ubicaciones lógicas auto-creadas |
| Dónde guardar | Putaway rules / storage categories | **Estrategia de ubicación** + áreas | **NUEVO** `PutawayRule` |
| De dónde sacar | Removal strategy (FIFO/FEFO) | **Estrategia de salida** (FIFO/LIFO/FEFO/bin fijo) | `RemovalStrategy` (enum + lógica) |
| Unidad de movimiento agrupada | Package / Package type | **Unidad de manipulación (HU)** / storage unit type (palet/caja) | **NUEVO** `HandlingUnit` + `PackageType` |
| Estado del stock | Quant state | **Tipo de stock**: disponible/calidad/bloqueado/consignación | campo `stock_type` en `StockLevel` |
| Atributos WM del producto | Inventory tab + routes | **Vistas Gestión de almacenes 1 y 2** | **NUEVO** `ProductWarehouseData` |

**Conclusión:** ya tenemos ~40% (bodegas, árbol de ubicaciones, quants vía `StockLevel`,
lotes/seriales, movimientos). Falta el **motor**: tipos de almacén, áreas, órdenes de
transporte, rutas multietapa, putaway/removal y atributos WM del material.

---

## 2. Modelo de datos nuevo (en `inventory-service`)

**Extender lo existente:**
- `Warehouse`: + `short_code` (prefijo de secuencias de documentos, estilo Odoo/SAP).
- `WarehouseLocation`: + `storage_type_id`, `storage_section_id`, `location_kind`
  (`physical | logical | interim`), `bin_type` (alto/ancho/dimensión), `max_weight`,
  `max_volume`, `height_m`, `is_fixed_bin`, `is_blocked`, `block_reason`, `barcode`.
- `StockLevel` (= quant): + `stock_type` (`available | quality | blocked | consignment`),
  `handling_unit_id` (opcional).
- `MovementType`: mapear a `OperationType` (no se borra; se enriquece).

**Entidades nuevas:**
- `StorageType` — tipo de almacén (rack, bloque, picking, interim/lógico). Reglas
  generales (¿controla capacidad? ¿maneja HU? estrategia de putaway/removal por defecto).
- `StorageSection` — área dentro de un tipo (alta/baja rotación, refrigerado, peligrosos…).
- `OperationType` — clase de movimiento (101 recepción compra, 201 consumo, 311 traslado…),
  con ubicación origen/destino por defecto y secuencia de documento.
- `Route` + `RouteRule` — define cómo fluye un producto (compra→stock; venta→pick→pack→out).
  Las reglas son pares (origen→destino) encadenados.
- `TransferRequirement` (necesidad de transporte) — provisional, planificable (puede venir
  de una OC, SO, orden de producción, o crearse manual).
- `TransferOrder` (orden de transporte) — documento central. Líneas con material, lote,
  cantidad, **bin origen + bin destino**, y **2 confirmaciones** (salida e ingreso).
- `PutawayRule` — propone bin de almacenamiento por tipo/sección/peso/volumen/capacidad.
- `HandlingUnit` + `PackageType` — palet/caja con id, peso, dimensiones; agrupa stock.
- `ProductWarehouseData` — atributos WM por producto×almacén (estrategia ingreso/salida,
  bin fijo, tipo de almacén de picking, unidad de medida WM, control lote/serie, hazmat,
  paletización: unidad de almacenamiento + cantidad por palet).

**Migración:** una sola serie alembic (088…) que crea las tablas nuevas y agrega columnas.
Todo **nullable / con default** → no rompe la operación actual; el WM "avanzado" queda
opt-in por almacén.

---

## 3. Flujos (todo movimiento físico = una Orden de Transporte)

Regla SAP que adoptamos: **ningún movimiento sin documento**. Toda entrada, salida o
traslado genera (o consume) una `TransferOrder` con confirmación.

- **Recepción de compra** → `OperationType 101` → TO de zona de recepción (interim 902)
  → *putaway* propone bin → confirmación de ingreso → quant en bin destino.
  Con QA: pasa primero a interim de **calidad**; release/reject decide si va a stock o se
  bloquea.
- **Entrega de venta** (Odoo 1/2/3 pasos) → genera `pick` (estrategia de salida FEFO/FIFO
  elige el bin) → `pack` (HU) → `out` (interim de despacho 916) → confirmación de salida.
- **Traslado interno** → TO bin→bin dentro del almacén (re-slotting, reabastecimiento de
  picking).
- **Producción** → consumo de componentes (interim pre-producción 901) + ingreso de
  terminado (interim post-producción 902) → putaway. Integra con el módulo producción.
- **Inventario / conteo cíclico WM** → a nivel **bin**, con bloqueo de ubicación, cálculo
  de varianza, ajuste por TO, y métrica **ERI** (exactitud de registro de inventario,
  meta ≥98%). Reporte de **ubicaciones vacías** (capacidad).

---

## 4. Fases de implementación (incremental, sin romper nada)

**Fase 0 — Fundaciones (modelo)**
`StorageType`, `StorageSection`, extensión de `WarehouseLocation` y `StockLevel`,
creación masiva de ubicaciones (estilo SAP LS10: patrón con rango+incremento) y reporte
de bins vacíos. *Comportamiento actual intacto.*

**Fase 1 — Órdenes de transporte + tipos de operación**
`OperationType`, `TransferRequirement`, `TransferOrder` con doble confirmación; ubicaciones
interim (recepción/despacho/QA/producción) auto-creadas. Recepción de OC y despacho de SO
pasan a generar TOs (con flag por almacén; default = 1 paso, comportamiento igual al de hoy).

**Fase 2 — Rutas multietapa (Odoo)**
Config por almacén: recepción 1/2/3, entrega 1/2/3 (pick/pack/out), fabricación 1/2/3. Al
guardar, auto-genera `Route` + `RouteRule` + `OperationType` + interim. Una venta dispara
la cadena pick→pack→out.

**Fase 3 — Putaway + estrategias de salida**
`PutawayRule` (propone bin por tipo/sección/peso/volumen/capacidad) y estrategias de salida
(FIFO/**FEFO**/LIFO/bin-fijo). Chequeo de capacidad (peso/volumen por bin), paletización y
`HandlingUnit`/`PackageType`. Bin fijo por material.

**Fase 4 — Estados de stock + inventario WM**
`stock_type` (disponible/calidad/bloqueado/consignación), gate de calidad en recepción,
conteo cíclico a nivel bin + ERI + reporte de vacías + ubicaciones bloqueadas.

**Fase 5 — Material master WM + extras**
`ProductWarehouseData` (estrategias, bin fijo, UoM WM, lote/serie, hazmat, GS1-128),
landed costs, y preparación para lectura por **código de barras / RF** (ya tenemos
`ScannerPage` en el front).

---

## 5. Frontend (por fase, sobre lo que ya existe)
- Config de almacén: pasos de recepción/entrega/fabricación + árbol de ubicaciones (UI).
- Pantalla de **Órdenes de transporte** (cola de trabajo / work queue estilo SAP).
- Putaway/estrategias en config; atributos WM en la ficha de producto (pestaña "Almacén").
- Conteo cíclico a nivel bin + reporte de ubicaciones vacías + tablero de capacidad.
- Flujos de escáner (recepción/picking) reutilizando `ScannerPage`.

## 6. Qué NO entra en este plan (scope control)
- Nada de CRM, contabilidad, marketing, web, RRHH (fuera del foco inventario/logística/producción).
- Equipos de radiofrecuencia físicos (solo dejamos el modelo listo para escaneo).
- Optimización automática de layout 3D (solo putaway por reglas, no solver geométrico).

## 7. Resultado esperado
Un inventario que hace lo que un WMS real (Odoo/SAP WM) necesita: ubicaciones a nivel bin,
órdenes de transporte con trazabilidad de quién/cuándo/de dónde/a dónde, putaway y picking
por estrategia, estados de stock, conteo cíclico con ERI, y atributos WM por material —
manteniendo la simplicidad para la PYME que solo quiere "1 bodega, 1 paso".

---

### Orden propuesto para construir: **Fase 0 → 1 → 2 → 3 → 4 → 5**
Cada fase es desplegable y no rompe la anterior. Apruebas el plan y arranco por la **Fase 0**
(con su diseño de tablas/migración al detalle antes de codear).
