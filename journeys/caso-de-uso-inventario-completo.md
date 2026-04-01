# Caso de Uso: Inventario Completo — Distribuidora de Cafe "Finca Alta"

**Objetivo:** Recorrer TODAS las funcionalidades del modulo de inventario de TraceLog usando un caso real de una distribuidora de cafe colombiano que compra a fincas, procesa, empaca y vende a tiendas.

**Tiempo estimado:** 45-60 minutos siguiendo cada paso.

---

## PASO 0: Preparacion inicial

### 0.1 Configurar modulos
1. Ve a **Marketplace** en el sidebar
2. Activa el modulo **Inventario** (si no esta activo)
3. Verifica que aparezca la seccion "Inventario" en el sidebar

### 0.2 Activar todas las funcionalidades
1. Ve a **Inventario → Ajustes → Configuracion**
2. En la pestana **Funcionalidades**, activa TODAS:
   - Lotes ✓
   - Seriales ✓
   - Conteo ciclico ✓
   - Scanner ✓
   - Picking ✓
   - Precios por cliente ✓
   - Aprobaciones ✓
   - Kardex ✓
   - Eventos ✓
3. Guarda los cambios

---

## PASO 1: Configuracion base

### 1.1 Unidades de medida
1. Ve a **Inventario → Ajustes → Medidas**
2. Crea estas unidades:
   - **Kilogramo** (kg) — unidad base
   - **Gramo** (g) — conversion: 1000 g = 1 kg
   - **Libra** (lb) — conversion: 2.2046 lb = 1 kg
   - **Saco** (saco) — conversion: 1 saco = 70 kg
   - **Unidad** (und) — para productos empacados
3. Verifica que las conversiones funcionen correctamente

### 1.2 Impuestos
1. Ve a **Inventario → Ajustes → Impuestos**
2. Verifica que existan (o crea):
   - **IVA 19%** — tipo: IVA, tasa: 19%
   - **IVA 5%** — tipo: IVA, tasa: 5% (para cafe procesado)
   - **Retencion 2.5%** — tipo: retencion, tasa: 2.5%
   - **ICA 0.414%** — tipo: ICA, tasa: 0.414% (Bogota)

### 1.3 Tipos de producto
1. Ve a **Inventario → Ajustes → Configuracion → Tipos de producto**
2. Crea estos tipos:
   - **Materia Prima** — color verde, slug: materia-prima
   - **Producto Terminado** — color azul, slug: producto-terminado
   - **Insumo de Empaque** — color gris, slug: insumo-empaque
   - **Material de Consumo** — color naranja, slug: material-consumo

### 1.4 Tipos de proveedor
1. En la misma seccion de configuracion, ve a **Tipos de proveedor**
2. Crea:
   - **Caficultor** — proveedor de cafe en cereza/pergamino
   - **Proveedor de empaques** — bolsas, cajas, etiquetas
   - **Transportista** — servicios de flete

### 1.5 Tipos de bodega
1. Crea en **Tipos de bodega**:
   - **Almacen principal** — bodega de materia prima
   - **Bodega de producto terminado** — listos para venta
   - **Bodega de transito** — mercancia en camino

### 1.6 Tipos de movimiento
1. Crea en **Tipos de movimiento**:
   - **Compra** — entrada por orden de compra
   - **Venta** — salida por orden de venta
   - **Merma** — perdida por procesamiento
   - **Devolucion** — entrada por devolucion de cliente
   - **Traslado** — entre bodegas

---

## PASO 2: Categorias de producto

1. Ve a **Inventario → Productos → Categorias**
2. Crea la jerarquia:
   - **Cafe**
     - Cafe Pergamino
     - Cafe Tostado
     - Cafe Molido
   - **Insumos**
     - Empaques
     - Etiquetas
   - **Producto Terminado**
     - Bolsas 250g
     - Bolsas 500g
     - Bolsas 1kg

---

## PASO 3: Bodegas y ubicaciones

### 3.1 Crear bodegas
1. Ve a **Inventario → Bodega y Despacho → Bodegas**
2. Crea 3 bodegas:

**Bodega Materia Prima (BOD-MP)**
- Tipo: Almacen principal
- Area: 200 m2
- Capacidad maxima: 50,000 kg
- Direccion: Calle 80 #45-23, Bogota

**Bodega Producto Terminado (BOD-PT)**
- Tipo: Bodega de producto terminado
- Area: 100 m2
- Capacidad maxima: 20,000 kg

**Bodega Transito (BOD-TR)**
- Tipo: Bodega de transito
- Area: 0 m2 (virtual)

### 3.2 Crear ubicaciones
1. Entra al detalle de **BOD-MP**
2. Crea ubicaciones:
   - **Pasillo A — Estante 1** (A-01) — capacidad: 5,000 kg
   - **Pasillo A — Estante 2** (A-02) — capacidad: 5,000 kg
   - **Pasillo B — Estante 1** (B-01) — capacidad: 10,000 kg
   - **Zona de recepcion** (REC) — capacidad: 2,000 kg

3. En **BOD-PT** crea:
   - **Estante 1** (PT-01) — capacidad: 5,000 kg
   - **Estante 2** (PT-02) — capacidad: 5,000 kg
   - **Zona de despacho** (DESP) — capacidad: 1,000 kg

---

## PASO 4: Socios comerciales (Proveedores y Clientes)

### 4.1 Crear proveedores
1. Ve a **Inventario → Compras y Ventas → Socios**
2. Crea estos proveedores:

**Finca La Esperanza**
- Tipo: Caficultor
- NIT: 900.123.456-7
- Contacto: Don Pedro Garcia
- Telefono: +57 310 234 5678
- Terminos de pago: 30 dias
- Lead time: 7 dias

**Finca El Paraiso**
- Tipo: Caficultor
- NIT: 900.234.567-8
- Contacto: Maria Lopez
- Terminos de pago: 15 dias
- Lead time: 5 dias

**Empaques Colombia SAS**
- Tipo: Proveedor de empaques
- NIT: 800.345.678-9
- Terminos de pago: 60 dias

### 4.2 Crear clientes
1. En la misma seccion de Socios, crea clientes:

**Tiendas Gourmet Bogota**
- Tipo: Distribuidor
- NIT: 900.456.789-0
- Limite de credito: $50,000,000 COP
- Descuento default: 5%

**Cafe Selecto — Cadena de tiendas**
- Tipo: Cadena retail
- NIT: 900.567.890-1
- Limite de credito: $100,000,000 COP
- Descuento default: 10%

**Juan Rodriguez — Tienda de barrio**
- Tipo: Minorista
- Limite de credito: $5,000,000 COP

---

## PASO 5: Productos

### 5.1 Crear productos de materia prima
1. Ve a **Inventario → Productos → Productos**
2. Crea:

**Cafe Pergamino Huila**
- SKU: MP-CAF-001
- Categoria: Cafe Pergamino
- Tipo: Materia Prima
- Unidad: Kilogramo
- Costo: $12,000 COP/kg
- Metodo de valorizacion: Promedio ponderado
- Punto de reorden: 500 kg
- Stock minimo: 200 kg
- Cantidad de reorden: 1,000 kg
- Proveedor preferido: Finca La Esperanza
- Track batches: SI (activar lotes)
- IVA: Exento (materia prima)

**Cafe Pergamino Narino**
- SKU: MP-CAF-002
- Categoria: Cafe Pergamino
- Tipo: Materia Prima
- Unidad: Kilogramo
- Costo: $14,000 COP/kg
- Metodo: FIFO
- Track batches: SI
- Proveedor preferido: Finca El Paraiso

**Bolsa Kraft 250g**
- SKU: INS-BOL-250
- Categoria: Empaques
- Tipo: Insumo de Empaque
- Unidad: Unidad
- Costo: $350 COP/und
- Punto de reorden: 5,000 und
- Proveedor preferido: Empaques Colombia

**Bolsa Kraft 500g**
- SKU: INS-BOL-500
- Categoria: Empaques
- Tipo: Insumo de Empaque
- Unidad: Unidad
- Costo: $500 COP/und

### 5.2 Crear productos terminados con variantes
1. Crea:

**Cafe Tostado Especial Finca Alta**
- SKU: PT-CAF-T01
- Categoria: Cafe Tostado
- Tipo: Producto Terminado
- Unidad: Unidad
- Precio de venta: $18,500 COP
- IVA: 5%
- Track batches: SI
- Track serials: NO

2. Ahora ve a **Inventario → Bodega y Despacho → Variantes** (o desde el detalle del producto)
3. Crea variantes:
   - **250g Molido** — SKU: PT-CAF-T01-250M, precio: $18,500
   - **250g Grano** — SKU: PT-CAF-T01-250G, precio: $19,500
   - **500g Molido** — SKU: PT-CAF-T01-500M, precio: $34,000
   - **500g Grano** — SKU: PT-CAF-T01-500G, precio: $36,000

### 5.3 Crear un producto con seriales
1. Crea:

**Maquina Moledora Manual**
- SKU: EQ-MOL-001
- Categoria: Producto Terminado
- Tipo: Producto Terminado
- Unidad: Unidad
- Precio: $450,000 COP
- Track serials: SI (activar seriales)
- IVA: 19%

---

## PASO 6: Precios especiales por cliente

1. Ve a **Inventario → Compras y Ventas → Precios por cliente**
2. Crea precios especiales:
   - **Cafe Selecto** compra "Cafe Tostado 250g Molido" a **$16,500** (en vez de $18,500)
   - **Cafe Selecto** compra "Cafe Tostado 500g Molido" a **$30,000** (en vez de $34,000)
   - **Tiendas Gourmet** compra "Cafe Tostado 250g Grano" a **$18,000** (en vez de $19,500)

---

## PASO 7: Ordenes de compra

### 7.1 Crear OC a Finca La Esperanza
1. Ve a **Inventario → Compras y Ventas → Compras**
2. Crea nueva orden de compra:
   - Proveedor: Finca La Esperanza
   - Lineas:
     - Cafe Pergamino Huila — 1,000 kg a $12,000/kg = $12,000,000
   - Notas: "Cosecha marzo 2026, finca lote 3"
3. Guarda como borrador
4. Haz clic en **Enviar** (cambia a estado "Enviada")

### 7.2 Crear OC a Empaques Colombia
1. Crea otra OC:
   - Proveedor: Empaques Colombia
   - Lineas:
     - Bolsa Kraft 250g — 10,000 und a $350 = $3,500,000
     - Bolsa Kraft 500g — 5,000 und a $500 = $2,500,000
2. Si el monto requiere aprobacion:
   - Ve a **Inventario → Compras y Ventas → Aprobaciones**
   - Aprueba la OC

### 7.3 Recibir mercancia con lotes
1. Entra al detalle de la OC de Finca La Esperanza
2. Haz clic en **Recibir**
3. Registra la recepcion:
   - Cantidad recibida: 1,000 kg
   - Bodega destino: BOD-MP
   - Ubicacion: Zona de recepcion (REC)
   - **Lote:** Crea nuevo lote:
     - Numero de lote: LOT-2026-03-001
     - Fecha de fabricacion: 2026-03-15
     - Fecha de vencimiento: 2027-03-15
     - Notas: "Huila, finca lote 3, pergamino seco"
4. Confirma la recepcion
5. Verifica que el stock de "Cafe Pergamino Huila" ahora muestra 1,000 kg en BOD-MP

---

## PASO 8: Verificar stock y movimientos

### 8.1 Stock actual
1. Ve a **Inventario → Productos → Productos**
2. Busca "Cafe Pergamino Huila"
3. Verifica: Stock = 1,000 kg en BOD-MP, ubicacion REC

### 8.2 Movimientos
1. Ve a **Inventario → Bodega y Despacho → Movimientos**
2. Filtra por producto "Cafe Pergamino Huila"
3. Deberia aparecer: Movimiento tipo "Compra", +1,000 kg, lote LOT-2026-03-001

### 8.3 Kardex
1. Ve a **Inventario → Informes → Kardex**
2. Busca "Cafe Pergamino Huila"
3. Verifica el registro valorizado: entrada de 1,000 kg a $12,000/kg = $12,000,000

---

## PASO 9: Traslado entre bodegas

1. Ve a **Inventario → Bodega y Despacho → Movimientos** o usa el endpoint de stock
2. Realiza un traslado:
   - Desde: BOD-MP, ubicacion REC
   - Hacia: BOD-MP, ubicacion A-01
   - Producto: Cafe Pergamino Huila
   - Cantidad: 800 kg
   - Lote: LOT-2026-03-001
3. Verifica que 800 kg estan en A-01 y 200 kg en REC

---

## PASO 10: Ajuste de inventario (merma)

1. Realiza un ajuste de salida:
   - Producto: Cafe Pergamino Huila
   - Cantidad: -15 kg (merma por humedad)
   - Bodega: BOD-MP, ubicacion A-01
   - Tipo: Merma
   - Notas: "Perdida por exceso de humedad en almacenamiento"
2. Verifica: Stock total ahora = 985 kg (1000 - 15)

---

## PASO 11: Registrar seriales

1. Ve a **Inventario → Bodega y Despacho → Seriales**
2. Crea 3 seriales para "Maquina Moledora Manual":
   - MOL-2026-001 — estado: Disponible
   - MOL-2026-002 — estado: Disponible
   - MOL-2026-003 — estado: En reparacion
3. Verifica que el stock de "Maquina Moledora Manual" refleje las unidades disponibles

---

## PASO 12: Lotes — verificar trazabilidad

1. Ve a **Inventario → Bodega y Despacho → Lotes**
2. Busca LOT-2026-03-001
3. Verifica:
   - Producto: Cafe Pergamino Huila
   - Cantidad original: 1,000 kg
   - Vencimiento: 2027-03-15
   - Estado: Activo
4. Usa "Traza hacia adelante" para ver a que clientes se ha vendido (aun vacio)

---

## PASO 13: Orden de venta

### 13.1 Crear orden de venta
1. Ve a **Inventario → Compras y Ventas → Ventas**
2. Crea nueva OV:
   - Cliente: Tiendas Gourmet Bogota
   - Lineas:
     - Cafe Tostado 250g Grano — 200 und a $18,000 (precio especial) = $3,600,000
     - Maquina Moledora Manual — 1 und a $450,000 = $450,000
   - Subtotal: $4,050,000
   - IVA 5% (cafe): $180,000
   - IVA 19% (moledora): $85,500
   - Total: $4,315,500

### 13.2 Confirmar y verificar stock
1. Haz clic en **Confirmar**
2. Haz clic en **Verificar Stock** — el sistema revisa si hay disponibilidad
3. Haz clic en **Reservar Stock** — se crean reservas en la bodega

### 13.3 Picking
1. Haz clic en **Picking** o ve a **Inventario → Bodega y Despacho → Picking**
2. El sistema genera la lista de picking:
   - Ir a BOD-PT, ubicacion PT-01: recoger 200 bolsas de 250g grano
   - Ir a BOD-PT, ubicacion PT-01: recoger 1 moledora (serial MOL-2026-001)
3. Marca cada item como "Recogido"

### 13.4 Despachar
1. Haz clic en **Despachar**
2. Registra el despacho:
   - Transportista: (opcional)
   - Guia: GU-2026-0001
3. El estado cambia a "Despachada"

### 13.5 Entregar
1. Cuando el cliente confirme recepcion, haz clic en **Entregar**
2. El estado cambia a "Entregada"

---

## PASO 14: Alertas de stock

1. Ve a **Inventario → Alertas**
2. Verifica si hay alertas:
   - "Cafe Pergamino Huila" deberia estar cerca del punto de reorden (985 kg, punto de reorden 500 kg — aun no)
   - Si tienes productos con stock bajo, aparecen aqui
3. Configura alertas manuales si es necesario

---

## PASO 15: Auto-reorden

1. Ve a **Inventario → Bodega y Despacho → Reorden**
2. Haz clic en **Generar sugerencias**
3. El sistema analiza todos los productos con punto de reorden configurado
4. Si algun producto esta por debajo, sugiere crear OC automaticamente
5. Haz clic en **Crear OC** para generar la orden de compra sugerida

---

## PASO 16: Conteo ciclico

### 16.1 Crear conteo
1. Ve a **Inventario → Bodega y Despacho → Conteo ciclico**
2. Crea nuevo conteo:
   - Bodega: BOD-MP
   - Tipo: Completo
   - Asignado a: (tu nombre)
3. El sistema genera la lista de items a contar

### 16.2 Ejecutar conteo
1. Haz clic en **Iniciar conteo**
2. Para cada item, registra la cantidad contada:
   - Cafe Pergamino Huila, A-01: contaste 795 kg (sistema dice 800, hay discrepancia de -5 kg)
   - Cafe Pergamino Huila, REC: contaste 200 kg (sistema dice 200, OK)
3. Si hay discrepancia, el sistema te pide un reconteo

### 16.3 Aprobar conteo
1. Haz clic en **Completar**
2. Si tienes permiso, haz clic en **Aprobar**
3. El sistema ajusta automaticamente el inventario segun las discrepancias
4. Verifica el IRA (Inventory Record Accuracy): deberia mostrar ~99.5%

---

## PASO 17: Eventos de inventario

1. Ve a **Inventario → Informes → Eventos**
2. Crea un nuevo evento:
   - Tipo: Dano de mercancia
   - Severidad: Media
   - Producto: Cafe Pergamino Huila
   - Descripcion: "Se encontro bolsa rota en estante A-02, 5 kg de cafe contaminado"
   - Impacto: 5 kg perdidos, $60,000 COP
3. Cambia el estado a "En investigacion"
4. Luego cambialo a "Resuelto"

---

## PASO 18: Reportes

### 18.1 Dashboard
1. Ve a **Inventario → Inicio**
2. Revisa:
   - Valor total del inventario
   - Numero de productos activos
   - Ordenes pendientes
   - Grafico de movimientos de la semana

### 18.2 Rentabilidad
1. Ve a **Inventario → Rentabilidad**
2. Revisa el margen por producto
3. Identifica los productos mas y menos rentables

### 18.3 Reportes descargables
1. Ve a **Inventario → Informes → Reportes**
2. Descarga:
   - Reporte de productos (CSV)
   - Reporte de stock actual (CSV)
   - Reporte de movimientos del mes (CSV)

### 18.4 Auditoria
1. Ve a **Inventario → Informes → Auditoria**
2. Revisa el historial de acciones:
   - Quien creo cada producto
   - Quien aprobo cada OC
   - Quien hizo cada ajuste de inventario

---

## PASO 19: Scanner (opcional)

1. Ve a **Inventario → Bodega y Despacho → Scanner**
2. Usa la camara del celular o un lector de codigos de barras
3. Escanea un SKU de producto (ej: MP-CAF-001)
4. El sistema muestra el producto con su stock actual
5. Desde ahi puedes hacer ajustes rapidos de stock

---

## PASO 20: Portal del cliente (opcional)

1. Ve a la URL del portal: `/inventario/portal/{id_del_cliente}`
2. El cliente puede ver:
   - Sus ordenes de venta activas
   - Estado de cada pedido
   - Historial de compras
   - Facturas pendientes

---

## Resumen de lo que probaste

| # | Funcionalidad | Seccion |
|---|---|---|
| 1 | Unidades de medida con conversiones | Ajustes |
| 2 | Impuestos (IVA, retencion, ICA) | Ajustes |
| 3 | Tipos de producto | Configuracion |
| 4 | Tipos de proveedor | Configuracion |
| 5 | Tipos de bodega | Configuracion |
| 6 | Tipos de movimiento | Configuracion |
| 7 | Categorias con jerarquia | Productos |
| 8 | Bodegas con ubicaciones | Bodega |
| 9 | Proveedores y clientes | Socios |
| 10 | Productos con lotes activados | Productos |
| 11 | Productos con seriales activados | Productos |
| 12 | Variantes de producto (tamano, tipo) | Productos |
| 13 | Precios especiales por cliente | Precios |
| 14 | Orden de compra (crear, enviar, aprobar) | Compras |
| 15 | Recepcion con creacion de lote | Compras |
| 16 | Stock en tiempo real | Stock |
| 17 | Movimientos y kardex valorizado | Informes |
| 18 | Traslado entre ubicaciones | Bodega |
| 19 | Ajuste de inventario (merma) | Stock |
| 20 | Seriales individuales | Seriales |
| 21 | Trazabilidad de lotes | Lotes |
| 22 | Orden de venta (crear, confirmar, reservar) | Ventas |
| 23 | Picking de pedidos | Picking |
| 24 | Despacho y entrega | Ventas |
| 25 | Alertas de stock bajo | Alertas |
| 26 | Auto-reorden | Reorden |
| 27 | Conteo ciclico con IRA | Conteo |
| 28 | Eventos de inventario | Eventos |
| 29 | Dashboard con KPIs | Dashboard |
| 30 | Rentabilidad por producto | P&L |
| 31 | Reportes descargables CSV | Reportes |
| 32 | Auditoria de acciones | Auditoria |
| 33 | Scanner de codigo de barras | Scanner |
| 34 | Portal del cliente | Portal |
| 35 | Aprobaciones de OC/OV | Aprobaciones |

---

## Datos finales esperados

Despues de completar este caso de uso, tu sistema deberia tener:

- **4 tipos de producto** configurados
- **3 categorias** con subcategorias
- **3 bodegas** con 7 ubicaciones
- **3 proveedores** y **3 clientes**
- **5 productos** (2 materia prima, 2 insumos, 1 terminado con variantes)
- **4 variantes** de producto
- **3 seriales** registrados
- **1 lote** con trazabilidad
- **2 ordenes de compra** (1 recibida)
- **1 orden de venta** (despachada)
- **1 conteo ciclico** (completado)
- **1 evento** de inventario
- **Multiples movimientos** de stock registrados
- **Precios especiales** para 2 clientes
- **Kardex** con historial valorizado completo
