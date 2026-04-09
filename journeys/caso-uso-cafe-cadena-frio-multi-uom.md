# 🧪 Caso de uso E2E — Tostador especialista de café con cadena de frío y multi-UoM

> **Industria:** café especial colombiano
> **Complejidad:** máxima — combina compras en toneladas → procesamiento en kilos → envasado en gramos, lotes con FEFO, QC obligatorio, cadena de frío con eventos de incidente, conteos cíclicos, cliente con precio negociado, MRP que dispara compras automáticas, backorders, devoluciones y facturación electrónica DIAN.
> **Tenant:** crear uno limpio o usar tu admin actual.
> **URL:** https://front-trace-e7ujx6tiba-rj.a.run.app
> **Versión validada:** commit `aa4e578` (Wave 7 desplegado en Cloud Run el 2026-04-07)

---

## 🎬 Escenario narrativo

`CafeOrigen S.A.S.` es un tostador colombiano especializado. Compra **café verde Excelso** a la finca *Hacienda La Esperanza* en **toneladas** (lotes que llegan en sacos de 70 kg). Lo recibe en una bodega refrigerada (cuarto frío 8–12 °C) donde pasa control de calidad. De ahí lo procesa en planta para tostarlo (transformación: **kg de verde → kg de tostado**, con merma del 18 % por agua y broca). Después lo muele y empaca en bolsas selladas de **250 g**, **500 g** y **1 kg** que van a la bodega de despacho.

Hoy llega un pedido grande de un cliente B2B existente — `Tiendas Juan Valdez Centro` — con tarifa negociada activa y umbral de aprobación. La orden mezcla las tres presentaciones, requiere despacho refrigerado, y una de las tres líneas se entrega corta (faltante → backorder automático). Después de entregada, el cliente devuelve 12 bolsas por defecto de empaque y ese stock devuelto debe re-entrar al inventario sin contaminar la valoración FIFO.

Mientras todo esto pasa: el almacenista descubre que un sensor del cuarto frío estuvo apagado 6 horas → evento de cadena de frío → 50 kg de café verde quedan en cuarentena. El conteo cíclico semanal detecta una discrepancia de 3 kg que el sistema arregla por ajuste con motivo. Y antes de despachar al Juan Valdez, el MRP detecta que la harina del próximo lote está bajo punto de reorden y crea automáticamente la OC al proveedor habitual.

Este journey toca **inventario + producción + recetas + UoM + lotes/FEFO + QC + eventos + conteos + multi-bodega + MRP + customer pricing + aprobaciones + picking + despacho + entregas + devoluciones + DIAN + multi-tenant + permisos**.

---

## ✅ Pre-requisitos

- Estar logueado como usuario con rol `administrador` (o equivalente con todos los permisos `inventory.*`, `production.*`, `purchase_orders.*`, `sales_orders.*`).
- Módulos activos en Marketplace (`/marketplace`):
  - **Logística** (sidebar muestra "Logística")
  - **Inventario** (sidebar muestra "Inventario")
  - **Producción** (sidebar muestra "Producción")
- Resolución DIAN configurada para emisión electrónica (sidebar `/facturacion-electronica`). Si no hay, las facturas quedarán en estado `Simulada` — el flujo igual funciona.

---

## FASE 0 — Setup base del tenant

> Si estás en un tenant que ya tiene el demo data cargado, salta a Fase 1. Aquí construimos todo desde cero.

### 0.1 Inicializar Unidades de Medida estándar

1. Sidebar → **Inventario** → **Unidades de Medida**
2. Si la lista está vacía → botón **"Inicializar UoM estándar"** (lado derecho del header)
3. Verificar que aparezcan al menos: `g` (Gramo, base), `kg` (Kilogramo, factor 1000), `ton` (Tonelada, factor 1 000 000), `lb`, `arroba`
4. Tab/sección **Conversiones** debe mostrar automáticamente:
   - `kg → g` factor `1000`
   - `ton → g` factor `1 000 000`
   - `lb → g` factor `500`
   - `arroba → g` factor `12 500`

### 0.2 Crear tasa de impuesto IVA 19 %

1. Sidebar → **Inventario** → **Configuración** → **Impuestos**
2. Botón **"Nueva tasa"**
3. Llenar: Nombre `IVA 19%`, Tipo `iva`, Tasa `19`, Activa ✔
4. **Guardar**
5. Repetir con: Nombre `Retención fuente 2.5%`, Tipo `retention`, Tasa `2.5`, Activa ✔

### 0.3 Crear bodegas multi-zona

1. Sidebar → **Logística** → **Bodegas**
2. **"Nueva bodega"** — repetir 4 veces:

| # | Nombre | Código | Tipo | Notas |
|---|---|---|---|---|
| 1 | Bodega Café Verde Refrigerada | `BCV-01` | `main` | área 200 m², capacidad 5000 kg |
| 2 | Planta de Tostado | `PT-01` | `secondary` | área 80 m² |
| 3 | Bodega Producto Terminado | `PT-FIN` | `secondary` | área 150 m² |
| 4 | Zona Despacho | `DESP-01` | `transit` | área 30 m² |

Para cada una llenar dirección y guardar.

### 0.4 Crear ubicaciones jerárquicas dentro de la bodega refrigerada

> El sistema soporta árbol de ubicaciones (`WarehouseLocation`) con padre/hijo, tipo libre y orden.

1. Volver a **Bodegas** → click en **Bodega Café Verde Refrigerada** → tab **Ubicaciones**
2. Botón **"+ Nueva ubicación"** — crear este árbol:

```
ZONA-FRIO  (tipo: zona, raíz)
├── PASILLO-A  (tipo: pasillo, padre: ZONA-FRIO)
│   ├── EST-A1  (tipo: estante, padre: PASILLO-A)
│   └── EST-A2  (tipo: estante, padre: PASILLO-A)
└── PASILLO-B  (tipo: pasillo, padre: ZONA-FRIO)
    └── CUARENTENA  (tipo: bin, padre: PASILLO-B)
```

3. Para cada ubicación: Nombre, Código, Tipo (escribir libre — `zona`, `pasillo`, `estante`, `bin`), Ubicación padre (selector)
4. Verificar que el árbol se renderiza con indentación y botones expandir/colapsar

### 0.5 Crear tipos de producto con regla FEFO + QC

1. Sidebar → **Inventario** → **Configuración** → **Tipos de producto**
2. **"Nuevo tipo"** — crear los siguientes:

| Nombre | Color | Regla despacho | Requiere QC | Notas |
|---|---|---|---|---|
| Café Verde Crudo | rojo | `fefo` | ✅ Sí | "Materia prima refrigerada — vencimiento 12 meses" |
| Café Tostado a Granel | café | `fifo` | ❌ | "Producto en proceso, sin vencimiento corto" |
| Café Empacado Final | verde | `fefo` | ❌ | "Producto terminado, vencimiento 8 meses" |

3. En cada tipo, después de crearlo → click → tab **"Información"** → verificar que `dispatch_rule` quedó correcto y `requires_qc` está marcado donde corresponde

### 0.6 Crear categorías

1. Sidebar → **Inventario** → **Categorías**
2. Crear: `Materia Prima` → hijo `Café Verde`. Crear: `Producto Terminado` → hijo `Café Empacado`.

### 0.7 Inicializar configuración de eventos

> Si nunca usaste el módulo de Eventos, los tipos/severidades/estados deben existir.

1. Sidebar → **Inventario** → **Eventos**
2. Si los selectores aparecen vacíos al intentar crear, ir a **Inventario** → **Configuración** → **Tipos de movimiento** y crear allí. Para *Eventos* usa los slugs sembrados:
   - Tipos: `dano-almacen`, `robo-perdida`, `producto-vencido`, `error-conteo`, `devolucion-cliente`
   - Severidades: `baja`, `media`, `alta`, `critica`
   - Estados: `abierto`, `en-investigacion`, `resuelto`, `cerrado`

> Si no hay UI para sembrarlos directamente, usar **Importar demo** desde **Configuración** → "Cargar demo data" (industria *Pet Food* o *Café*) y luego eliminar lo que no sirva.

---

## FASE 1 — Catálogo multi-UoM

### 1.1 Crear el café verde (compra en kg, recibido por tonelada)

1. Sidebar → **Inventario** → **Productos**
2. Botón **"Nuevo producto"**
3. Selector de tipo → click en **"Café Verde Crudo"** (el de regla FEFO + QC)
4. Llenar:
   - SKU: `CV-EXCELSO-001`
   - Nombre: `Café verde Excelso EP — Hacienda La Esperanza`
   - Categoría: `Café Verde`
   - **Unidad de medida: `kg`** ⚠️ (la primaria; vamos a comprar en toneladas y convertir)
   - Punto de reorden: `200`
   - Cantidad de reorden: `500`
   - Tasa de IVA: `IVA 19%`
   - Retención: `2.5%`
5. **"Crear Café Verde Crudo"**
6. Confirmar en la lista que aparece con su tipo

### 1.2 Crear el café tostado a granel (intermedio)

1. **"Nuevo producto"** → tipo **"Café Tostado a Granel"**
2. SKU `CT-GRANEL-001`, Nombre `Café tostado medio — granel`, UoM `kg`, IVA `19%`
3. **"Crear Café Tostado a Granel"**

### 1.3 Crear las 3 presentaciones de producto terminado

> Cada presentación es un SKU diferente porque cada uno tiene su receta de empacado.

| SKU | Nombre | UoM | Punto reorden | Retención |
|---|---|---|---|---|
| `PT-CAFE-250` | Café molido Excelso 250 g | `g` | `2000` | `2.5%` |
| `PT-CAFE-500` | Café molido Excelso 500 g | `g` | `4000` | `2.5%` |
| `PT-CAFE-1000` | Café molido Excelso 1 kg | `g` | `5000` | `2.5%` |

Para cada uno: **"Nuevo producto"** → tipo **"Café Empacado Final"** → llenar → **"Crear Café Empacado Final"**.

> ⚠️ El UoM primario es `g` aunque la presentación nominal sea 250 g, 500 g o 1 kg, porque internamente vamos a manejar todo en gramos para que el FIFO/FEFO no confunda unidades.

### 1.4 Crear configuración de reorden para el café verde

1. Sidebar → **Inventario** → **Reorden**
2. Buscar `CV-EXCELSO-001` → botón **"Configurar"**
3. Llenar:
   - Min stock level: `100`
   - Reorder point: `200`
   - Reorder quantity: `500`
   - Preferred supplier: (lo asignamos en Fase 2 y volvemos)
   - Auto reorder: ✅
4. **Guardar** (lo terminamos en 2.x)

---

## FASE 2 — Socios comerciales (proveedor finca + cliente B2B)

### 2.1 Crear tipo de proveedor "Finca cafetera"

1. Sidebar → **Inventario** → **Configuración** → **Tipos de proveedor**
2. **"Nuevo tipo"** → Nombre `Finca cafetera`, color verde
3. **Guardar**

### 2.2 Crear el proveedor finca

1. Sidebar → **Inventario** → **Socios** (Partners)
2. **"Nuevo socio"** → tab **Proveedor**
3. Llenar:
   - Tipo: `Proveedor`
   - Tipo de proveedor: `Finca cafetera`
   - Nombre: `Hacienda La Esperanza S.A.S.`
   - NIT: `900456789`, DV: `3`
   - Tipo documento: `NIT`, Régimen: `No responsable IVA` (régimen simple)
   - Email: `ventas@haciendalaesperanza.co`
   - Dirección: `Vereda El Tablazo`, Ciudad: `Manizales`, País: `Colombia`
4. **Guardar**

### 2.3 Volver a configuración de reorden

1. Sidebar → **Inventario** → **Reorden**
2. Buscar `CV-EXCELSO-001` → **Configurar**
3. Asignar **Preferred supplier: `Hacienda La Esperanza`**
4. **Guardar**

### 2.4 Crear el cliente B2B

1. Sidebar → **Inventario** → **Socios**
2. **"Nuevo socio"** → tab **Cliente**
3. Llenar:
   - Tipo: `Cliente`
   - Nombre: `Tiendas Juan Valdez Centro`
   - NIT: `860049921`, DV: `1`
   - Tipo documento: `NIT`, Régimen: `Responsable IVA`
   - Email: `compras.centro@juanvaldez.com`
   - Dirección: `Calle 73 #10-83`, Ciudad: `Bogotá`, Departamento: `Cundinamarca`
   - País: `Colombia`
4. Sección **Crédito**:
   - Límite de crédito: `50000000`
   - Días de crédito: `30`
5. **Guardar**

---

## FASE 3 — Recetas (cadena verde → tostado → empacado)

### 3.1 Receta 1: Tostado del café verde

> Esta receta convierte café verde a café tostado a granel con una merma del 18 %.

1. Sidebar → **Producción** → **Recetas**
2. **"Nueva receta"**
3. Llenar:
   - Nombre: `Tostado medio — Excelso`
   - Producto de salida: `Café tostado medio — granel`
   - Cantidad de salida: `82` (porque 100 kg de verde rinden 82 kg de tostado por la merma)
   - Tipo BOM: `Producción`
   - Costo estándar: `0`
   - Tamaño lote planificado: `100`
4. Componentes → **"+ Agregar"**:
   - Componente: `Café verde Excelso EP`
   - Cantidad: `100`
   - Merma %: `18`
5. **"Crear receta"**

### 3.2 Receta 2: Empacar 250 g

1. **"Nueva receta"**
2. Llenar:
   - Nombre: `Empaque bolsa 250 g`
   - Producto de salida: `Café molido Excelso 250 g`
   - Cantidad de salida: `40000` (40 000 g salen del molido = 160 bolsas × 250 g — esperá, recordar que el sistema usa cantidad como número de unidades del producto de salida, y nuestro PT está definido en `g`, así que cantidad de salida = `40000` representa 40 kg total empacado)
   - Tipo BOM: `Producción`
3. Componentes:
   - `Café tostado medio — granel`, cantidad `40` (kg, porque ese producto está en `kg`), merma `1`
4. **"Crear receta"**

### 3.3 Receta 3: Empacar 500 g

Repetir 3.2 con:
- Nombre: `Empaque bolsa 500 g`
- Salida: `Café molido Excelso 500 g`, cantidad `40000`
- Componentes: `Café tostado medio — granel` cantidad `40`, merma `1`

### 3.4 Receta 4: Empacar 1 kg

Repetir con:
- Nombre: `Empaque bolsa 1 kg`
- Salida: `Café molido Excelso 1 kg`, cantidad `40000`
- Componentes: `Café tostado medio — granel` cantidad `40`, merma `1`

### 3.5 Verificar que ninguna receta tiene componentes disponibles

1. Volver al listado de **Recetas**
2. Cada receta debe mostrar el badge **"sin stock"** (rojo, ícono triángulo) — esperado, no hay nada comprado todavía
3. Click en el ojo 👁 de **Tostado medio — Excelso** → debe mostrar:
   - Sección "Componentes sin stock suficiente" → `Café verde Excelso EP`
   - Sección "Bodegas con stock" → vacía

---

## FASE 4 — MRP: planeación que dispara compras automáticas

> Vamos a usar el módulo MRP para "explotar" la receta del 250 g por una producción de 100 kg de tostado y dejar que el sistema cree la OC borrador automáticamente.

### 4.1 Ejecutar MRP

1. Sidebar → **Producción** → **MRP**
2. Llenar:
   - Receta: `Tostado medio — Excelso`
   - Cantidad a producir: `1` (1 ejecución de la receta = 82 kg de tostado, requiere 100 kg de verde)
   - Bodega: `Bodega Café Verde Refrigerada`
   - ☑ **Auto-crear OC**
3. Botón **"Explotar BOM"**
4. Resultado esperado (panel inferior):
   - Costo estimado total: `0` (porque aún no tenemos `last_purchase_cost`)
   - Sugerencias de compra → `Café verde Excelso EP` cantidad `100 kg`
   - Banner verde: **"1 Orden de Compra creada en borrador"**

### 4.2 Verificar la OC borrador

1. Sidebar → **Inventario** → **Compras**
2. La OC más reciente debe estar en estado **Borrador** con número `PO-2026-NNNN`
3. Click → debe mostrar línea: `CV-EXCELSO-001` cant `100`, costo unit `0`

> Esa OC con costo cero la usamos como "trigger" — vamos a duplicar el flujo creando manualmente la OC real con costos verdaderos.

### 4.3 Cancelar la OC del MRP

1. Estando en el detalle de la OC del MRP → botón **"Cancelar"** → confirmar

---

## FASE 5 — Compra real con UoM converter (toneladas → kg)

### 5.1 Crear OC manual

1. **Inventario** → **Compras** → **"Nueva OC"**
2. Llenar:
   - Proveedor: `Hacienda La Esperanza S.A.S.`
   - Bodega destino: `Bodega Café Verde Refrigerada`
   - Fecha esperada: `+5 días`
3. Línea → **"+ Línea"**:
   - Producto: `Café verde Excelso EP`
   - **Cantidad: `500`** (500 kg = media tonelada — usamos kg porque el SKU lo está)
   - Costo unitario: `28000` COP/kg
4. **"Crear OC"**

> 💡 **Nota multi-UoM**: si quisieras comprar en toneladas y dejar que el sistema convierta, usar el conversor: Sidebar → **Inventario** → **Unidades de Medida** → tab **Convertir** → de `0.5 ton` a `kg` → resultado `500`. El UI de OC en el frontend actual sólo acepta la UoM primaria del producto, así que ya pre-convertimos.

### 5.2 Recorrer el workflow completo de la OC

Click en la OC recién creada (estado **Borrador**) → en el header de acciones:

1. **"Enviar al proveedor"** (azul, ícono Send) → estado pasa a **Enviada**
2. **"Confirmar recepción proveedor"** (cian) → estado pasa a **Confirmada**
3. **"Recibir mercancía"** (verde) → abre modal de recepción

### 5.3 Recepción con creación de lote (manufacture/expiration)

En el modal de recepción:

1. Línea `Café verde Excelso EP`:
   - Cantidad recibida: `500`
   - **Número de lote: `L-EXC-2026-04-001`**
   - **Fecha fabricación: `2026-03-01`**
   - **Fecha vencimiento: `2027-03-01`** (12 meses, café verde refrigerado)
2. **"Confirmar recepción"** → estado pasa a **Recibida**
3. Toast verde: *"OC recibida correctamente"*

### 5.4 Verificar lote y stock en pending_qc

1. Sidebar → **Inventario** → **Lotes**
2. Filtrar por producto `CV-EXCELSO-001` → debe aparecer `L-EXC-2026-04-001` con cantidad `500`, fab `2026-03-01`, exp `2027-03-01`
3. Sidebar → **Logística** → **Bodegas** → click en `Bodega Café Verde Refrigerada` → tab **Stock**
4. Debe aparecer el café verde con:
   - `qty_on_hand = 500`
   - **Badge ámbar `Pendiente QC`** (porque el tipo de producto tiene `requires_qc=true`)
   - Dos botones: **"Aprobar"** (verde) y **"Rechazar"** (rojo)

### 5.5 Intentar despachar antes de aprobar QC (caso de error esperado)

1. Sidebar → **Producción** → **Órdenes** → **"Nueva orden"**
2. Receta: `Tostado medio — Excelso`, bodega: `Bodega Café Verde Refrigerada`, multiplicador: `1`
3. **"Crear"** → estado **Planificada**
4. Click en la orden → drawer → botón **"Liberar"**
5. **Resultado esperado:** error toast rojo → *"Stock pendiente de QC, no se puede reservar para producción"*. Esto valida la regla de QC del Wave 6/7.

### 5.6 Aprobar QC

1. Sidebar → **Logística** → **Bodegas** → `Bodega Café Verde Refrigerada` → tab **Stock**
2. Línea de café verde → click **"Aprobar"** (verde)
3. Toast: *"QC aprobado"*. El badge cambia a `Aprobado` (verde)

---

## FASE 6 — Evento de cadena de frío e inventario en cuarentena

> Antes de procesar, simulamos que el almacenista detecta que el sensor del cuarto frío estuvo apagado durante 6 horas la noche anterior, y por protocolo HACCP debe poner 50 kg en cuarentena.

### 6.1 Crear evento de daño en almacén

1. Sidebar → **Inventario** → **Eventos**
2. Botón **"Nuevo evento"**
3. Llenar:
   - **Título**: `Sensor cuarto frío inactivo 6h — posible cadena de frío rota`
   - **Tipo de evento**: `Daño en almacén`
   - **Severidad**: `Alta`
   - **Estado**: `Abierto`
   - **Bodega**: `Bodega Café Verde Refrigerada`
   - **Fecha de ocurrencia**: ayer 22:00
   - **Descripción**: `Sensor TermoSense-04 desconectado por mantenimiento eléctrico no informado. Temperatura registrada al regresar: 18°C (rango normal 8-12°C). Tiempo estimado fuera: 6 horas. 50 kg del lote L-EXC-2026-04-001 quedan en cuarentena hasta inspección sensorial.`
4. Sección **Impactos** → **"+ Agregar impacto"**:
   - Producto: `Café verde Excelso EP`
   - Cantidad: `-50` (negativo = pérdida potencial)
   - Lote: `L-EXC-2026-04-001`
   - Notas: `Cuarentena temporal`
5. **"Crear evento"**
6. Verificar que aparece en la lista con badge `Alta` rojo

### 6.2 Mover stock a la ubicación de cuarentena

> Esto se hace con un movimiento manual (transferencia interna) a la ubicación `CUARENTENA` que creamos en 0.4.

1. Sidebar → **Inventario** → **Movimientos**
2. **"Nuevo movimiento"** (botón superior derecho) → selector tipo:
   - Tipo: `Ajuste salida` (ya que las ubicaciones internas no son una transferencia entre bodegas, registramos un ajuste con motivo)
   - Producto: `Café verde Excelso EP`
   - Bodega origen: `Bodega Café Verde Refrigerada`
   - Cantidad: `50`
   - Motivo: `Cuarentena por evento EVT-XXXX — sensor cuarto frío`
3. **"Crear movimiento"**

> Esto deja `qty_on_hand = 450` en BCV-01.

### 6.3 Cambiar estado del evento

1. Volver a **Eventos** → click en el evento creado
2. Botón cambiar estado → **`En investigación`**
3. Agregar nota en el log: `Inspección sensorial programada con jefe de calidad`

---

## FASE 7 — Conteo cíclico que detecta discrepancia

### 7.1 Crear conteo

1. Sidebar → **Inventario** → **Conteos**
2. **"Nuevo conteo cíclico"**
3. Llenar:
   - Bodega: `Bodega Café Verde Refrigerada`
   - Productos: ✔ `Café verde Excelso EP` (sólo este)
   - Metodología: `Conteo selectivo post-incidente cadena de frío`
   - Contadores asignados: `2`
   - Minutos por conteo: `5`
   - Fecha programada: hoy
   - Notas: `Verificación post-cuarentena`
4. **"Crear"** → estado **Programado**

### 7.2 Iniciar y contar

1. Click en el conteo recién creado → botón **"Iniciar conteo"** → estado pasa a **En progreso**
2. Tabla de líneas → línea de `Café verde Excelso EP`:
   - **Cantidad esperada (sistema)**: `450`
   - **Cantidad contada**: `447` (escribir manualmente — discrepancia de -3 kg, simulando merma natural por humedad)
3. Botón **"Confirmar conteo"** → marca la línea como contada
4. Botón superior **"Aprobar conteo"** (verde) → estado **Aprobado**
5. **Resultado esperado:** el sistema crea automáticamente un **ajuste** por -3 kg en BCV-01 con motivo `Conteo cíclico CC-XXXX — discrepancia` y deja `qty_on_hand = 447`

### 7.3 Verificar trazabilidad del ajuste

1. Sidebar → **Inventario** → **Movimientos**
2. Filtrar por bodega `Bodega Café Verde Refrigerada`, últimas 24h
3. Debe haber un movimiento `adjustment_out` de `3` kg con la referencia al conteo

---

## FASE 8 — Producción etapa 1: tostado (consumo FEFO)

### 8.1 Crear y liberar orden de tostado

1. Sidebar → **Producción** → **Órdenes** → **"Nueva orden"**
2. Llenar:
   - Receta: `Tostado medio — Excelso`
   - **Bodega componentes: `Bodega Café Verde Refrigerada`**
   - **Bodega salida: `Planta de Tostado`**
   - Tipo: `Estándar`
   - Multiplicador: `4` (4 × 100 kg verde = 400 kg verde → 328 kg tostado)
   - Prioridad: `90`
   - Notas: `Lote para pedido Juan Valdez`
3. **"Crear"** → estado **Planificada**
4. Click → drawer → tab **General** muestra "Componentes (BOM)" con `Café verde Excelso EP` cantidad `100 × 4 = 400`
5. Botón **"Liberar"** (azul)
6. Toast: *"Orden liberada — componentes reservados"*
7. Estado pasa a **Liberada**
8. Verificar reserva: **Bodegas** → `Bodega Café Verde Refrigerada` → tab Stock → café verde debe mostrar `qty_reserved = 400`

### 8.2 Emitir componentes (consume desde el lote por FEFO)

1. Mismo drawer → botón **"Emitir componentes"** (ámbar)
2. Toast: *"Emisión creada — componentes sacados de inventario"*
3. Estado pasa a **En producción**
4. Tab **Emisiones** → debe haber 1 emisión con número `EMI-XXXX`
5. Click en la emisión → debe mostrar que se consumió del lote `L-EXC-2026-04-001` (FEFO eligió el único lote activo)
6. Verificar stock: `Café verde Excelso EP` en BCV-01 debe quedar en `qty_on_hand = 47` (447 - 400) y `qty_reserved = 0`

### 8.3 Recibir el producto tostado

1. Mismo drawer → botón **"Recibir producto"** (verde)
2. Toast: *"Recibo creado — producto terminado en inventario"*
3. Estado pasa a **Completada**
4. Tab **Recibos** → 1 recibo con `328 kg` de `Café tostado medio — granel` en `Planta de Tostado`
5. Verificar: **Productos** → `CT-GRANEL-001` → tab Stock: `qty_on_hand = 328` en `Planta de Tostado`

### 8.4 Cerrar orden y revisar costos

1. Drawer → botón **"Cerrar orden"** (gris)
2. Estado pasa a **Cerrada**
3. Tab **Costos** → debe mostrar:
   - Costo estimado vs costo real
   - Variación (al ser primera receta, las cifras dependen del costo del lote consumido = `28000 COP/kg × 400 kg = 11 200 000`)

---

## FASE 9 — Producción etapa 2: empacado de las 3 presentaciones

> Ahora hacemos 3 órdenes de producción adicionales — una por presentación. Cada una consume del mismo `Café tostado medio — granel` que está en `Planta de Tostado`.

### 9.1 Empaque 250 g

1. **Producción** → **Órdenes** → **"Nueva orden"**
2. Receta: `Empaque bolsa 250 g`, bodega componentes: `Planta de Tostado`, bodega salida: `Bodega Producto Terminado`
3. Multiplicador: `2` (2 × 40 kg = 80 kg → 320 bolsas de 250 g)
4. **"Crear"** → liberar → emitir → recibir → cerrar (igual que 8.1–8.4)

### 9.2 Empaque 500 g

Repetir 9.1 con receta `Empaque bolsa 500 g`, multiplicador `3` (3 × 40 = 120 kg → 240 bolsas de 500 g)

### 9.3 Empaque 1 kg

Repetir con receta `Empaque bolsa 1 kg`, multiplicador `2` (2 × 40 = 80 kg → 80 bolsas de 1 kg)

### 9.4 Verificar stock final en PT-FIN

1. **Logística** → **Bodegas** → `Bodega Producto Terminado` → tab Stock
2. Debe mostrar:
   - `Café molido Excelso 250 g`: **80 000 g** (320 bolsas × 250)
   - `Café molido Excelso 500 g`: **120 000 g** (240 × 500)
   - `Café molido Excelso 1 kg`: **80 000 g** (80 × 1000)
3. Verificar `Café tostado medio — granel` en `Planta de Tostado`: `328 - (80+120+80) = 48 kg` restantes

---

## FASE 10 — Precio negociado del cliente

### 10.1 Crear precio especial para Juan Valdez

1. Sidebar → **Inventario** → **Precios clientes**
2. Botón **"Nuevo precio"** — repetir 3 veces:

| Cliente | Producto | Precio | Cant. mín | Vigente desde | Vigente hasta |
|---|---|---|---|---|---|
| Tiendas Juan Valdez Centro | `PT-CAFE-250` | `12500` | `1` | hoy | +6 meses |
| Tiendas Juan Valdez Centro | `PT-CAFE-500` | `23000` | `1` | hoy | +6 meses |
| Tiendas Juan Valdez Centro | `PT-CAFE-1000` | `42000` | `1` | hoy | +6 meses |

3. **"Crear"** en cada uno
4. Verificar que aparecen 3 precios activos con badge verde

### 10.2 Probar lookup de precio

1. Mismo página → opción **"Calcular precio"** o tab **Lookup**
2. Cliente: `Tiendas Juan Valdez Centro`, Producto: `Café molido Excelso 250 g`
3. Debe responder:
   - **Precio**: `12500`
   - **Source**: `customer_special`
   - **Original price**: precio sugerido del producto (si existe)

---

## FASE 11 — Venta con aprobación, picking, despacho corto + backorder

### 11.1 Crear orden de venta

1. Sidebar → **Inventario** → **Ventas** → **"Nueva OV"**
2. Llenar:
   - Cliente: `Tiendas Juan Valdez Centro`
   - **Bodega origen: `Bodega Producto Terminado`**
   - Fecha esperada: `+3 días`
3. Líneas → **"+ Línea"** (3 veces):

| Producto | Cant | Precio (debe auto-llenarse del cust price) |
|---|---|---|
| `Café molido Excelso 250 g` | `200` | `12500` (aparece automáticamente) |
| `Café molido Excelso 500 g` | `150` | `23000` |
| `Café molido Excelso 1 kg` | `60` | `42000` |

> Total esperado pre-IVA: `200×12500 + 150×23000 + 60×42000 = 2 500 000 + 3 450 000 + 2 520 000 = 8 470 000`. Con IVA 19%: `10 079 300`. Con retención 2.5%: `9 867 550`.

4. **"Crear OV"** → estado **Borrador**

### 11.2 Confirmar (debe pasar a aprobación si supera umbral)

1. Click en la OV → botón **"Confirmar"** (azul)
2. Si el monto supera el umbral configurado → estado pasa a **Pendiente aprobación**, banner amarillo arriba
3. Logueate como otro usuario con permiso `sales_orders.approve`, o como admin si tenés el permiso → en la misma OV → botón **"Aprobar"** (verde)
4. Estado pasa a **Confirmada**, stock se reserva:
   - `PT-CAFE-250`: `qty_reserved = 50000` (200 × 250 g)
   - `PT-CAFE-500`: `qty_reserved = 75000` (150 × 500 g)
   - `PT-CAFE-1000`: `qty_reserved = 60000` (60 × 1000 g)
5. Banner muestra "Aprobada por <usuario>"

### 11.3 Ir a la cola de picking

1. Sidebar → **Inventario** → **Picking**
2. La OV recién confirmada debe aparecer en la columna "Confirmadas"
3. Click en **"Iniciar picking"**
4. Estado pasa a **En picking** y entrás a la vista activa de picking
5. La lista debe mostrar las 3 líneas con las cantidades a recoger

### 11.4 Marcar las líneas como recogidas

1. Para cada línea: click en el círculo (○ → ✓) o el botón "Marcar"
2. Cuando todas estén ✓ → botón **"Confirmar picking"** (o equivalente)

### 11.5 Despacho corto (¡aquí entra el backorder automático!)

1. Volver al detalle de la OV (estado debe ser **En picking**) → botón **"Enviar"** (azul, ícono camión)
2. En el modal de despacho:
   - Dirección: `Calle 73 #10-83`, Ciudad `Bogotá`, Departamento `Cundinamarca`, País `Colombia`
   - Foto: opcional (subir cualquier imagen)
   - **Cantidades por línea**:
     - `PT-CAFE-250`: `200` ✅ completo
     - `PT-CAFE-500`: `150` ✅ completo
     - `PT-CAFE-1000`: **`50`** ⚠️ corto (faltan 10 unidades)
3. **"Confirmar envío"**
4. **Resultado esperado** (Wave 7 fix):
   - Estado pasa a **Enviada**
   - Se genera `remission_number = REM-2026-NNNN`
   - **Se crea automáticamente un backorder**: `SO-XXXX-BO1` con `PT-CAFE-1000` cant `10`
   - Toast verde
5. Verificar el backorder: en el detalle de la OV → sección/tab **Backorders** → debe listar el SO hijo
6. Click en el backorder → debe estar en estado **Borrador** con `is_backorder = true`

### 11.6 Entregar la OV principal

1. Volver a la OV principal (no el backorder) → estado **Enviada**
2. Botón **"Entregar"** (verde)
3. Estado pasa a **Entregada**
4. Stock físico se descuenta:
   - `PT-CAFE-250`: `qty_on_hand = 30000` (80000 - 50000)
   - `PT-CAFE-500`: `qty_on_hand = 45000` (120000 - 75000)
   - `PT-CAFE-1000`: `qty_on_hand = 30000` (80000 - 50000) — sólo se descontaron las 50 que se enviaron, no las 60 originales

---

## FASE 12 — Devolución parcial

> El cliente devuelve 12 bolsas de 500 g por defecto en el sello.

### 12.1 Procesar devolución

1. En la OV principal entregada → botón **"Devolver"** (naranja, ícono undo)
2. **Resultado esperado:**
   - Toast: *"Devolución creada"*
   - Stock restaurado: `PT-CAFE-500` `qty_on_hand` aumenta
   - Movimiento de tipo `return` con referencia a la OV
   - Capa FIFO creada (Wave 7 fix) con costo efectivo = WAC actual

> ⚠️ Limitación: el botón actual de devolver hace **devolución total**. Si querés devolución parcial, tenés que usar Movimientos → "Nueva devolución" y seleccionar manualmente la cantidad.

### 12.2 Verificar la capa FIFO de la devolución

1. Sidebar → **Inventario** → **Kardex**
2. Filtrar por `Café molido Excelso 500 g`
3. Debe aparecer una entrada de tipo `return` con la cantidad devuelta y su costo unitario

---

## FASE 13 — Facturación electrónica DIAN

### 13.1 Verificar emisión automática

1. En la OV principal entregada → tab/sección **"Factura electrónica"**
2. Estado debe ser **Pendiente** → en pocos minutos pasa a **Simulada** o **Emitida** (depende del provider DIAN configurado)
3. Si está **Failed** → revisar **Integraciones** → resolución no configurada o credenciales Matias

### 13.2 Verificaciones críticas (Wave 7 fixes)

Click en el número de factura para abrir el detalle:

| Campo | Valor esperado |
|---|---|
| **CUFE** | presente, longitud 96 caracteres |
| **Subtotal** | `8 470 000` (sin IVA, calculado sólo sobre lo entregado) |
| **IVA 19%** | `1 609 300` ⚠️ **NO `16 093` ni `160 930`** — el bug del `tax_rate_pct ÷ 100` doble está fixeado |
| **Retención 2.5%** | `211 750` |
| **Total con IVA** | `10 079 300` |
| **Total a pagar** | `9 867 550` |
| **Cliente** | NIT `860049921-1`, régimen `Responsable IVA`, dirección completa, municipio Bogotá |
| **Líneas** | cada una con tasa 19% (no hardcoded), tax aggregation por tasa |
| **Timezone** | fechas en zona Colombia (`America/Bogota`) |

### 13.3 Re-emitir si está en Simulada

Si el provider de producción DIAN está activo y querés re-emitir:
1. Tab Factura → botón **"Re-emitir"**
2. Verificar que el `invoice_number` queda dentro del `range_from..range_to` de la resolución activa (Wave 7 fix: el counter se inicializa a `range_from - 1`)

---

## FASE 14 — Reorden automático del backorder

### 14.1 Confirmar el backorder

> Cuando llegue stock nuevo (en producción real esto vendría de otra producción), confirmamos el backorder.

1. Sidebar → **Inventario** → **Ventas** → filtrar por estado **Borrador** o por número que termina en `-BO1`
2. Click en el backorder → botón **"Confirmar"**
3. Si hay stock suficiente → estado pasa a **Confirmada**
4. Sigue picking → enviar → entregar igual que en Fase 11

> Si querés generar más stock primero: repetir la receta `Empaque bolsa 1 kg` con multiplicador `1` para producir 40 bolsas más.

---

## FASE 15 — Verificaciones cruzadas Wave 7

### 15.1 Kardex y P&L

1. Sidebar → **Inventario** → **Kardex** → filtrar por `Café molido Excelso 250 g`
2. Debe mostrar línea por línea:
   - Recibo de producción (entrada, qty 80000, costo unit calculado)
   - Salida de venta (qty 50000, costo unit consumido por FEFO/FIFO)
3. Sidebar → **Inventario** → **Rentabilidad** (P&L)
4. Buscar `Café molido Excelso 250 g`:
   - **Margen** debe ser realista (no inflado por COGS sub-reportado, fix Wave 7)
   - Sección "Compras" en gramos base
   - Sección "Ventas" en gramos base
   - Stock por bodega

### 15.2 Eventos abiertos

1. Sidebar → **Inventario** → **Eventos**
2. El evento de cadena de frío debe seguir abierto en estado `En investigación`
3. Click → cambiar a **`Resuelto`** y agregar nota: `Inspección sensorial OK, los 50 kg en cuarentena se aprueban para producción`
4. Mover los 50 kg de vuelta con un ajuste manual (Movimientos → Ajuste entrada → motivo `Liberación cuarentena post-evento`)

### 15.3 Auditoría

1. Sidebar → **Inventario** → **Auditoría** (`/inventario/auditoria`)
2. Debe haber registros de cada acción crítica: creación de OC, recepción, aprobación QC, conteo cíclico, evento, ajustes, OV, picking, envío, entrega, devolución, emisión DIAN

### 15.4 Multi-tenant: probar el fix de login

1. Logout
2. Si tenés un segundo tenant con un usuario que tenga el **mismo email** que un usuario del primer tenant → login con ese email + contraseña + header `X-Tenant-Id` correcto debe funcionar
3. Antes del fix Wave 7 esto fallaba con `MultipleResultsFound` 500

### 15.5 Portal IDOR

1. Como admin del tenant 1 → ir a `/inventario/portal/<id-de-cliente-de-otro-tenant>`
2. Debe responder **403** (no leer datos)

---

## ✅ Criterios de éxito globales

| # | Verificación | Pasa si |
|---|---|---|
| 1 | UoM inicializadas (g, kg, ton, lb, arroba) | hay >= 5 entradas en Unidades de Medida |
| 2 | Bodega refrigerada con 4 ubicaciones jerárquicas | el árbol muestra ZONA-FRIO con padre/hijo |
| 3 | 3 tipos de producto creados con regla FEFO/FIFO | aparecen en `/inventario/configuracion/tipos-producto` |
| 4 | OC `received` con lote vivo | tabla Lotes muestra `L-EXC-2026-04-001` con exp 2027-03-01 |
| 5 | QC bloquea producción | intentar liberar antes de aprobar lanza error |
| 6 | Evento de cadena de frío con impacto | aparece en `/inventario/eventos` |
| 7 | Conteo aprobado crea ajuste automático | hay movimiento `adjustment_out` con ref CC-XXXX |
| 8 | 4 órdenes de producción cerradas | una de tostado + 3 de empacado |
| 9 | Stock en gramos en PT-FIN | 80000+120000+80000 g iniciales, post-venta 30000+45000+30000 |
| 10 | Customer price aplicado en OV | precios `12500/23000/42000` sin que el usuario los escriba |
| 11 | Backorder automático en despacho corto | aparece SO hijo `-BO1` con qty `10` |
| 12 | DIAN: IVA = `1 609 300` (no `16 093`) | factura emitida/simulada con totales correctos |
| 13 | Devolución crea capa FIFO | Kardex muestra entrada `return` con costo |
| 14 | Auditoría completa | log con todas las acciones |

---

## 🐛 Troubleshooting

| Problema | Causa probable | Solución |
|---|---|---|
| El botón **"Liberar"** lanza error de stock pendiente QC | Tipo de producto tiene `requires_qc=true` y no aprobaste | Aprobar QC en `/logistica/bodegas/:id` tab Stock |
| MRP no crea OC | Producto no tiene `preferred_supplier_id` | Configurar en Reorden |
| Customer price no se aplica | `valid_from > hoy` o cliente equivocado | Revisar fechas en Precios clientes |
| Backorder no se crea | Estás despachando un backorder (no se anidan) o `qty_shipped >= qty_ordered` | Despachar la OV principal con cantidad menor a lo ordenado |
| Factura DIAN en `failed` | Resolución expirada o credenciales Matias erróneas | `/facturacion-electronica` |
| 401 al subir foto en despacho | Bearer token no se está enviando a media-service | Recargar la página, fix Wave 7 |
| 403 en `/inventario/portal/...` | El user no está bound a un customer_id | Esperado, fix IDOR Wave 7 |
| Conteo cíclico no aparece | Módulo `conteo` no activo | Activar feature en `/inventario/configuracion` |

---

## 🎯 Cobertura del journey

Este caso ejecuta **todas** las funcionalidades críticas del MVP:

- ✅ Multi-UoM con conversiones (`g/kg/ton`, sistema de conversión real)
- ✅ Bodegas multi-zona con árbol jerárquico de ubicaciones
- ✅ Tipos de producto con reglas de despacho FIFO/FEFO/LIFO
- ✅ QC obligatorio bloqueante con flujo aprobar/rechazar
- ✅ Lotes con fecha de fabricación y vencimiento
- ✅ Eventos de inventario con impactos, severidades y workflow de estados
- ✅ Conteos cíclicos con ajuste automático
- ✅ Reorder automático con preferred supplier
- ✅ MRP con explosión de BOM y creación automática de OC
- ✅ Recetas multi-etapa (verde → tostado → empacado en 3 SKU)
- ✅ Producción completa: planificada → liberada → emisión → recibo → cerrada
- ✅ Multi-bodega: refrigerada → planta → terminado → despacho
- ✅ Customer pricing con vigencias
- ✅ Aprobación de OV por umbral de monto
- ✅ Picking con cola y vista activa
- ✅ Despacho con shipping_info, foto y backorder automático
- ✅ Devolución que crea capa FIFO
- ✅ Facturación DIAN con tax aggregation correcto
- ✅ Auditoría inmutable con bypass GUC
- ✅ Multi-tenant isolation
- ✅ Wave 7: 60+ bugs cerrados validados en flujo real

---

**Tiempo estimado total**: 90–120 minutos para un usuario familiarizado con el sistema.
**Datos a registrar para presentar al inversionista**: número de OC, número de OV, CUFE de la factura, screenshots del Kardex y P&L.
