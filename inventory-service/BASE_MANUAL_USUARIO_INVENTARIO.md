# Manual de Usuario — Modulo de Inventario TraceLog

## Tabla de Contenidos

- [2.1 Catalogo — Productos](#21-catalogo--productos)
- [2.2 Catalogo — Bodegas](#22-catalogo--bodegas)
- [2.3 Catalogo — Proveedores y Clientes](#23-catalogo--proveedores-y-clientes)
- [2.4 Compras — Ordenes de Compra](#24-compras--ordenes-de-compra)
- [2.5 Ventas — Ordenes de Venta](#25-ventas--ordenes-de-venta)
- [2.6 Stock — Gestion de Inventario](#26-stock--gestion-de-inventario)
- [2.7 Configuracion — Impuestos](#27-configuracion--impuestos)
- [2.8 Configuracion — Facturacion Electronica](#28-configuracion--facturacion-electronica)
- [2.9 Configuracion — Aprobaciones](#29-configuracion--aprobaciones)
- [2.10 Reorden Automatico](#210-reorden-automatico)
- [2.11 Analiticas y Reportes](#211-analiticas-y-reportes)
- [Glosario Tecnico-Funcional](#glosario-tecnico-funcional)

---

## 2.1 Catalogo — Productos

**Que es:** El catalogo central donde se registran todos los productos que tu empresa compra, almacena, produce o vende. Cada producto tiene un codigo SKU unico, precios, impuestos y configuracion de seguimiento.

**Para que sirve:** Permite mantener una base de datos actualizada de todos los items que maneja tu negocio: materias primas, productos terminados, insumos, repuestos. Es la base para compras, ventas, control de stock y facturacion.

**Como acceder:** Menu lateral > Inventario > Productos (`/inventario/productos`)

### Funcionalidades

#### Crear un Producto

1. Haz clic en el boton "Nuevo Producto" en la esquina superior derecha
2. Completa los campos:

**Campos requeridos:**
- **SKU** — Codigo unico del producto (no se puede cambiar despues del primer movimiento de stock)
- **Nombre** — Nombre descriptivo del producto

**Campos opcionales recomendados:**
- **Codigo de barras** — EAN-13, UPC u otro codigo de barras
- **Descripcion** — Detalle largo para referencia interna
- **Categoria** — Clasifica el producto (ej: "Alimentos", "Maquinaria")
- **Tipo de producto** — Agrupa productos con configuracion similar (QC, lotes, reglas de despacho)
- **Precio de costo** — Precio de compra de referencia
- **Precio de venta** — Precio base de venta (puede ser sobreescrito por precios especiales de cliente)
- **Moneda** — Por defecto COP (peso colombiano)
- **Unidad de medida** — unidad, kg, litro, caja, etc.
- **Unidad secundaria** — UoM alternativa con factor de conversion
- **Proveedor preferido** — Para reorden automatico
- **Stock minimo** — Alerta cuando el stock baje de este nivel
- **Punto de reorden** — Cuando activar compra automatica
- **Cantidad de reorden** — Cuanto comprar automaticamente
- **Metodo de valoracion** — FIFO (primero en entrar, primero en salir), LIFO o promedio ponderado

3. Haz clic en "Guardar"

> Consejo: El SKU, la unidad de medida y la configuracion de lotes se bloquean despues del primer movimiento de stock para proteger la integridad de los datos historicos.

#### Imagenes de Producto

- Haz clic en un producto existente para abrir su detalle
- En la seccion de imagenes, usa "Subir imagen"
- Formatos permitidos: JPG, PNG, WebP, GIF
- Tamano maximo: 5 MB por imagen
- Puedes subir multiples imagenes por producto

#### Variantes de Producto

**Que son:** Versiones de un mismo producto que difieren en atributos como talla, color o presentacion. Cada variante tiene su propio SKU y stock independiente.

**Cuando usarlas:** Cuando vendes el mismo producto en diferentes presentaciones. Ejemplo: una camiseta que viene en S, M, L y en colores rojo, azul, negro.

**Como crearlas:**
1. Ve a Inventario > Variantes (`/inventario/variantes`)
2. Primero crea los **atributos** (ej: "Color", "Talla") y sus opciones ("Rojo", "Azul", "S", "M")
3. Luego, en la pagina de un producto, ve a la pestana "Variantes"
4. Haz clic en "Crear variante"
5. Asigna un SKU unico y selecciona los valores de cada atributo

> Consejo: Las variantes heredan el precio del producto padre, pero pueden tener precios especiales por cliente.

#### Impuestos por Producto

La configuracion de impuestos en cada producto determina como se calculan automaticamente en las ordenes de venta:

- **IVA 19%** — Tarifa general. Se aplica por defecto a la mayoria de productos.
- **IVA 5%** — Tarifa diferencial. Para ciertos alimentos procesados, dispositivos medicos, etc.
- **IVA 0% (Exento)** — Para alimentos basicos de la canasta familiar, exportaciones, libros.
- **Retencion en la fuente** — Porcentaje que el comprador retiene al pagar. Se configura en el campo "Tasa de retencion" del producto (ej: 2.5% o 3.5%).

**Como configurarlo:**
1. Al crear o editar un producto, busca la seccion "Tributacion"
2. Selecciona la tarifa IVA en el dropdown
3. Si el producto es exento, marca "Exento de IVA"
4. Si aplica retencion, ingresa el porcentaje

> Atencion: Los impuestos configurados en el producto se aplican automaticamente al agregar el producto a una orden de venta. El IVA aparece desglosado en la factura electronica.

#### Lotes y Seriales

**Lotes (Batches):**
Agrupan unidades del mismo producto que comparten fecha de fabricacion, vencimiento y origen. Utiles para trazabilidad alimentaria, farmaceutica o quimica.

- Acceder en: Inventario > Lotes (`/inventario/lotes`)
- Campos: codigo de lote, fecha fabricacion, fecha vencimiento, proveedor, costo, cantidad
- El sistema genera alertas automaticas cuando un lote esta proximo a vencer (30 dias por defecto)
- **Trazabilidad forward:** Desde un lote puedes ver a que clientes fue despachado
- **Trazabilidad backward:** Desde una orden de venta puedes ver que lotes se usaron
- **FEFO:** Si el tipo de producto tiene regla de despacho "FEFO", el sistema prioriza despachar primero los lotes que vencen mas pronto

**Seriales:**
Identificadores unicos por unidad individual. Para equipos, maquinaria o productos de alto valor.

- Acceder en: Inventario > Seriales (`/inventario/seriales`)
- Cada serial tiene su propio estado configurable (disponible, en uso, en reparacion, dado de baja)
- Se puede vincular a un lote, bodega y ubicacion especifica

#### Recetas y Produccion

**Que son:** Las recetas (tambien llamadas BOM — Bill of Materials) definen como fabricar un producto terminado a partir de materias primas o componentes.

**Cuando usar:**
- Cuando tu empresa transforma materias primas en productos terminados
- Ejemplo: una receta de "Concentrado para mascotas 20kg" que requiere 12kg harina, 5kg proteina, 2kg vitaminas, 1kg aceite

**Como funciona:**
1. **Crear receta:** Inventario > Recetas (`/inventario/recetas`)
   - Selecciona el producto de salida (lo que produces)
   - Agrega los componentes con cantidades
   - Define la cantidad de output y porcentaje de rendimiento

2. **Crear orden de produccion:** Inventario > Produccion (`/inventario/produccion`)
   - Selecciona la receta y bodega de produccion
   - Define multiplicador (cuantas veces la receta)
   - El sistema calcula automaticamente los insumos necesarios

3. **Ejecutar produccion:**
   - Estado: Pendiente → En Progreso (verifica stock de insumos)
   - Finalizar → Esperando Aprobacion
   - Aprobar: descuenta insumos del stock, agrega producto terminado (la persona que aprueba debe ser diferente a quien ejecuto — principio de 4 ojos)
   - El costo del producto se calcula como FIFO de los insumos consumidos

> Atencion: La aprobacion de una orden de produccion es irreversible. Una vez aprobada, los movimientos de stock quedan registrados.

#### Taxonomia (Clasificacion Avanzada)

Ademas de categorias, puedes crear vocabularios personalizados para clasificar productos:

- **Vocabularios:** Grupos de clasificacion (ej: "Origen", "Material", "Certificaciones")
- **Terminos:** Opciones dentro de cada vocabulario (ej: "Nacional", "Importado" dentro de "Origen")
- **Asignacion:** Cada producto puede tener multiples terminos de diferentes vocabularios
- Los vocabularios pueden estar vinculados a un tipo de producto especifico

Acceder en: Inventario > Taxonomias (`/inventario/taxonomias`)

#### Categorias

Sistema de clasificacion jerarquico para productos:

- Soporta categorias padre/hijo (ej: "Alimentos" > "Secos" > "Harinas")
- Cada producto pertenece a una sola categoria
- Acceder en: Inventario > Categorias (`/inventario/categorias`)

---

## 2.2 Catalogo — Bodegas

**Que es:** El registro de todas las ubicaciones fisicas o virtuales donde se almacena mercancia. Cada bodega tiene su propio stock, ubicaciones internas y configuracion.

**Para que sirve:** Controlar donde esta cada producto, gestionar transferencias entre sedes, y tener visibilidad del espacio disponible.

**Como acceder:** Menu lateral > Inventario > Bodegas (`/inventario/bodegas`)

### Funcionalidades

#### Crear una Bodega

1. Haz clic en "Nueva Bodega"
2. Completa los campos:
   - **Nombre** — Nombre de la bodega (ej: "Bodega Principal Bogota")
   - **Codigo** — Codigo corto unico (ej: "BOG-01")
   - **Tipo de bodega:**
     - **Principal** — Bodega de operacion principal
     - **Secundaria** — Bodegas auxiliares
     - **Virtual** — Para inventario en consignacion o sin ubicacion fisica
     - **Transito** — Para mercancia en camino entre bodegas
   - **Direccion y ciudad** — Ubicacion fisica
   - **Area total (m2)** — Para calcular costo de almacenamiento
   - **Costo por m2** — Para analisis de valuacion de almacenamiento
   - **Capacidad maxima** — Unidades maximas que puede almacenar

> Consejo: El codigo de bodega no se puede repetir. Usalo como referencia rapida en otros formularios.

#### Ubicaciones dentro de Bodega

Organiza tu bodega en zonas, pasillos, racks y bins:

1. Entra al detalle de una bodega (`/inventario/bodegas/{id}`)
2. En la seccion "Ubicaciones", haz clic en "Nueva ubicacion"
3. Define: codigo, nombre, tipo (rack, estante, bin, zona), ubicacion padre (jerarquia)

El stock se puede asignar a ubicaciones especificas para saber exactamente donde esta cada producto.

#### Tipos de Bodega Personalizados

Puedes crear tipos de bodega adicionales en: Inventario > Configuracion > Tipos de Bodega (`/inventario/configuracion/tipos-bodega`)

Cada tipo puede tener campos personalizados (ej: "Temperatura controlada", "Humedad maxima").

#### Transferencias entre Bodegas

El sistema soporta dos modalidades:

**Transferencia inmediata:**
1. Ve a Inventario > Stock
2. Selecciona "Transferir"
3. Elige producto, bodega origen, bodega destino y cantidad
4. El stock se mueve instantaneamente

**Transferencia en 2 fases (recomendada para sedes distantes):**
1. **Fase 1 — Iniciar:** El stock sale de la bodega origen y queda "en transito"
   - Bodega origen: qty_on_hand disminuye
   - Bodega destino: qty_in_transit aumenta
2. **Fase 2 — Completar:** Cuando la mercancia llega fisicamente
   - Bodega destino: qty_in_transit disminuye, qty_on_hand aumenta
   - Se registra fecha de completado

> Consejo: Usa transferencias en 2 fases cuando la mercancia tarda mas de un dia en llegar. Asi puedes rastrear que esta en camino.

#### Alertas de Stock por Bodega

El sistema genera alertas automaticas cuando:
- Un producto baja del stock minimo configurado
- Un producto se agota completamente
- Un lote esta proximo a vencer (30 dias)

Las alertas son visibles en: Inventario > Alertas (`/inventario/alertas`)

---

## 2.3 Catalogo — Proveedores y Clientes

### Proveedores

**Que es:** El directorio de empresas o personas que te venden mercancia o materias primas.

**Como acceder:** Menu lateral > Inventario > Proveedores (`/inventario/proveedores`)

**Crear proveedor:**
1. Haz clic en "Nuevo Proveedor"
2. Completa los campos:
   - **Nombre** (razon social)
   - **Codigo** — Codigo interno unico
   - **NIT / RUT** — Numero de identificacion tributaria
   - **Email, telefono, direccion** — Datos de contacto
   - **Nombre de contacto** — Persona de referencia
   - **Plazo de pago (dias)** — Para calculos de flujo de caja
   - **Tiempo de entrega (dias)** — Para calculos de reorden automatico
   - **Tipo de proveedor** — Clasificacion configurable (ej: "Nacional", "Internacional", "Maquila")
   - **Campos personalizados** — Segun el tipo de proveedor, pueden aparecer campos adicionales

> Atencion: No puedes eliminar un proveedor que tenga ordenes de compra activas. Primero debes cancelar o completar las ordenes.

### Clientes

**Que es:** El directorio de empresas o personas a quienes vendes mercancia.

**Como acceder:** Menu lateral > Inventario > Clientes (`/inventario/clientes`)

**Crear cliente:**
1. Haz clic en "Nuevo Cliente"
2. Completa los campos:
   - **Nombre** (razon social)
   - **Codigo** — Codigo unico
   - **NIT** — Para facturacion electronica
   - **Email, telefono, direccion**
   - **Nombre de contacto**
   - **Tipo de cliente** — Clasificacion (ej: "Mayorista", "Minorista", "Institucional")
   - **Lista de precios** — Asigna una lista de precios especifica
   - **Limite de credito** — Control financiero
   - **Descuento global (%)** — Se aplica automaticamente en ordenes de venta

### Precios Especiales por Cliente

**Que es:** Precios negociados individualmente entre tu empresa y un cliente para productos especificos. Tienen prioridad sobre la lista de precios y el precio base del producto.

**Para que sirve:** Cuando negocias condiciones comerciales diferentes con cada cliente. Ejemplo: un distribuidor mayorista tiene un precio diferente al de un minorista.

**Como configurarlo:**
1. Ve a Inventario > Precios de Clientes (`/inventario/precios-clientes`)
2. Haz clic en "Nuevo Precio Especial"
3. Selecciona: cliente, producto (y opcionalmente variante)
4. Define:
   - **Precio** — Precio unitario negociado
   - **Cantidad minima** — A partir de cuantas unidades aplica
   - **Vigencia** — Fecha desde / hasta
   - **Moneda** — COP por defecto
   - **Razon** — Por que se otorga este precio (referencia interna)

**Prioridad de precios al crear una orden de venta:**
1. Precio especial del cliente (si existe y esta vigente)
2. Lista de precios del cliente (si tiene una asignada)
3. Precio base del producto (fallback)

El sistema muestra visualmente que tipo de precio se aplico:
- Etiqueta azul: "Precio especial"
- Etiqueta gris: "Lista de precios"
- Sin etiqueta: Precio base

#### Historial de Precios

Cada vez que cambias un precio especial, el sistema guarda un registro historico con:
- Precio anterior y nuevo
- Quien hizo el cambio
- Fecha del cambio
- Razon del cambio

Accesible desde el detalle de cada precio especial.

### Listas de Precios

**Que son:** Tablas de precios por producto que puedes asignar a uno o varios clientes. Permiten manejar escalas de precios por cantidad minima y descuentos por producto.

**Como crear una lista:**
1. Ve a Inventario > Listas de Precios (`/inventario/listas-precios`)
2. Haz clic en "Nueva Lista"
3. Asigna nombre, moneda y estado (activa/inactiva)
4. Agrega items: producto, cantidad minima, precio unitario, descuento %

---

## 2.4 Compras — Ordenes de Compra

**Que es:** El registro de todas las compras de mercancia a proveedores. Cada orden de compra (OC) sigue un flujo de estados desde borrador hasta recibida.

**Para que sirve:** Controlar que se compro, a quien, por cuanto, y cuando llego. Es la base para ingresar mercancia al inventario de forma controlada.

**Como acceder:** Menu lateral > Inventario > Compras (`/inventario/compras`)

### Crear una Orden de Compra

1. Haz clic en "Nueva Orden de Compra"
2. Selecciona el **proveedor**
3. Opcionalmente selecciona: bodega destino, tipo de orden, fecha esperada
4. Agrega lineas:
   - Producto (y variante si aplica)
   - Cantidad ordenada
   - Costo unitario
   - Notas por linea
5. El sistema calcula automaticamente el total por linea y el total general
6. El numero de OC se genera automaticamente: `PO-2026-0001`

### Flujo Completo de una OC

```
Borrador (Draft) → Enviada (Sent) → Confirmada (Confirmed) → Recibida (Received)
                                                           → Parcial (Partial)
Desde cualquier estado (excepto Recibida): → Cancelada
```

1. **Borrador:** La OC se puede editar libremente. Puedes agregar/quitar lineas, cambiar cantidades y precios.

2. **Enviada:** Indica que la OC fue comunicada al proveedor. Ya no se puede editar el contenido, pero se puede cancelar.

3. **Confirmada:** El proveedor confirmo que puede despachar. A partir de aqui se puede recibir mercancia.

4. **Recepcion de mercancia:**
   - Haz clic en "Recibir" en la OC confirmada
   - Para cada linea, indica cuantas unidades llegaron
   - Si no llego todo, la OC pasa a estado "Parcial"
   - Puedes hacer multiples recepciones parciales
   - Al recibir el 100%, la OC pasa a "Recibida"
   - **El stock se actualiza automaticamente** al confirmar la recepcion

> Consejo: Si un producto tiene control de calidad (QC) configurado en su tipo de producto, la mercancia recibida quedara en estado "Pendiente QC" hasta que un responsable la apruebe.

### Consolidacion de Ordenes de Compra

**Que es:** Permite unir varias OC en borrador del mismo proveedor en una sola OC, optimizando costos de transporte y gestion.

**Cuando usarla:** Cuando varios departamentos o procesos generan OC al mismo proveedor por separado, y tiene sentido agruparlas en un solo envio.

**Paso a paso:**
1. Ve a la lista de OC y busca el indicador "Candidatos de consolidacion" (aparece cuando hay ≥2 borradores del mismo proveedor)
2. Selecciona las OC a consolidar
3. Haz clic en "Consolidar"
4. El sistema crea una nueva OC con:
   - Lineas combinadas (productos iguales se suman con costo promedio ponderado)
   - Las OC originales pasan a estado "Consolidada" (se conservan para referencia)
5. Si necesitas revertir: usa "Desconsolidar" en la OC consolidada

> Consejo: Solo puedes consolidar OC que esten en borrador y sean del mismo proveedor.

### Recepcion Parcial

Cuando un proveedor envia la mercancia en multiples entregas:
1. Al recibir la primera entrega, registra las cantidades que llegaron
2. La OC pasa a estado "Parcial"
3. Cuando llegue el resto, vuelve a hacer "Recibir" y registra las cantidades faltantes
4. Cuando todas las lineas esten completas, la OC pasa a "Recibida"

---

## 2.5 Ventas — Ordenes de Venta

**Que es:** El registro de todas las ventas de mercancia a clientes. Cada orden de venta (OV) pasa por un flujo completo desde borrador hasta entregada, con facturacion electronica automatica.

**Para que sirve:** Gestionar el ciclo comercial completo: cotizar, confirmar, despachar, entregar, facturar y manejar devoluciones.

**Como acceder:** Menu lateral > Inventario > Ventas (`/inventario/ventas`)

### Crear una Orden de Venta

1. Haz clic en "Nueva Orden de Venta"
2. Selecciona el **cliente** (esto determina los precios automaticamente)
3. Selecciona la **bodega** principal de despacho (opcional, puede ser por linea)
4. Agrega lineas de producto:
   - Al seleccionar un producto, el sistema busca automaticamente el mejor precio:
     1. Precio especial negociado con este cliente
     2. Precio de la lista de precios del cliente
     3. Precio base del producto
   - El tipo de precio se muestra con una etiqueta visual
   - Selecciona la tarifa IVA (0%, 5%, 19% o personalizada)
   - Opcionalmente aplica descuento por linea (%)
5. Aplica descuento global (%) si corresponde
6. Revisa el resumen de totales:
   - Subtotal
   - Descuento global
   - IVA (desglosado)
   - Retencion en la fuente
   - **Total a pagar** (total + IVA - retencion)
7. Haz clic en "Crear"

### Flujo Completo de una OV

```
Borrador → [Pendiente Aprobacion] → Confirmada → Picking → Despachada → Entregada
                                                                       → Devuelta
Desde estados no terminales: → Cancelada
```

### Confirmacion

Al confirmar una OV sucede automaticamente:

1. **Verificacion de aprobacion:** Si el total supera el umbral configurado por tu empresa, la OV pasa a "Pendiente de Aprobacion" en lugar de confirmarse directamente.

2. **Reserva de stock:** El sistema reserva la cantidad necesaria de cada producto en la bodega correspondiente. El stock reservado no esta disponible para otras ordenes.
   - Si no hay suficiente stock, el sistema ofrece dos opciones:
     - **Backorder:** Crear automaticamente una segunda OV con las cantidades faltantes, y confirmar parcialmente la OV original con lo que hay disponible
     - **Cancelar:** No confirmar hasta tener stock completo

3. **Facturacion electronica:** Si tienes el modulo de facturacion electronica activo, se emite automaticamente una factura (CUFE generado por la DIAN).

> Atencion: La reserva de stock es atomica. Si falta stock para cualquier linea, el sistema no reserva nada hasta que decidas como proceder (backorder o esperar).

### Aprobacion por Monto

Cuando una OV supera el umbral de aprobacion configurado:

1. La OV pasa a estado "Pendiente de Aprobacion"
2. Aparece en la cola de aprobaciones (`/inventario/aprobaciones`)
3. Un usuario con permiso `so.approve` debe:
   - **Aprobar:** La OV continua el flujo de confirmacion (reserva + facturacion)
   - **Rechazar:** La OV vuelve a borrador con una razon obligatoria (minimo 10 caracteres)
4. Si fue rechazada, el creador puede modificarla y reenviarla para aprobacion

> Atencion: La persona que aprueba debe ser diferente a quien creo la OV (principio de 4 ojos). Esto es un control automatico del sistema.

### Backorders (Pedidos Pendientes)

**Que son:** Cuando confirmas una OV pero no hay suficiente stock de todos los productos, el sistema puede dividir la orden automaticamente:

- **Orden original:** Se confirma con las cantidades disponibles
- **Backorder:** Se crea una nueva OV (numero: SO-2026-0005-BO1) con las cantidades faltantes

**Paso a paso:**
1. Al confirmar una OV con stock insuficiente, aparece un dialogo mostrando:
   - Productos con stock disponible y cuanto se puede despachar
   - Productos sin stock o con stock parcial
2. Haz clic en "Confirmar con Backorder"
3. El sistema crea las dos ordenes automaticamente
4. Cuando llegue mercancia para el backorder, puedes confirmarlo normalmente

### Despacho

Al despachar una OV:

1. Haz clic en "Despachar" en una OV confirmada
2. Opcionalmente indica:
   - **Informacion de envio:** Destinatario, direccion, transportadora, numero de guia
   - **Despacho por lote:** Si el producto tiene trazabilidad por lotes, indica que lote se despacha
3. El sistema automaticamente:
   - Genera un **numero de remision** (REM-2026-0001)
   - Consume las reservas de stock
   - Registra los movimientos de salida
   - Descuenta el stock fisico (qty_on_hand)

#### Remision de Entrega (PDF)

La remision es el documento que acompana la mercancia fisica. Contiene:
- Datos de la empresa (NIT, direccion)
- Datos del cliente destinatario
- Bodega de origen
- Tabla de productos: codigo, nombre, cantidad, unidad, lote/serial (si aplica)
- Espacios para firma: "Despachado por" y "Recibido por"
- Aviso legal: "Este documento no es una factura"

Puedes descargar la remision como PDF desde el detalle de la OV despachada.

### Facturacion Electronica

**Cuando se emite la factura:** Automaticamente al **confirmar** la OV (no al despachar ni al entregar).

**Sandbox vs Real:**
- **Sandbox:** Modo de pruebas. Las facturas se generan con un CUFE simulado y marca de agua "SIMULADO". No tienen validez ante la DIAN. Util para verificar que todo funciona antes de activar el modo real.
- **Real (MATIAS):** Facturas validas ante la DIAN. Requiere configurar la API key de MATIAS y una resolucion de facturacion vigente.

**Que hacer si falla la emision:**
1. En el detalle de la OV, aparece un indicador rojo "Factura: Fallida"
2. Haz clic en "Reintentar factura"
3. El sistema vuelve a intentar la emision
4. Si sigue fallando, verifica la configuracion en Facturacion Electronica

**CUFE:** Es el Codigo Unico de Factura Electronica. Es un hash alfanumerico que identifica cada factura de forma unica ante la DIAN. Se genera automaticamente y aparece en el detalle de la OV.

### Devoluciones

**Como procesar una devolucion:**
1. En una OV entregada o despachada, haz clic en "Devolver"
2. Confirma la devolucion
3. El sistema automaticamente:
   - Devuelve el stock al inventario (incrementa qty_on_hand)
   - Emite una **nota credito** automatica si la factura electronica ya habia sido generada
   - Registra la fecha de devolucion

**Nota credito:** Es un documento electronico que anula total o parcialmente una factura. Se genera automaticamente al procesar la devolucion y se envia a la DIAN si el modulo de facturacion real esta activo.

### Detalle de la Orden de Venta

La pagina de detalle de una OV muestra:
- **Encabezado:** Numero, estado, cliente, fechas, bodega
- **Totales desglosados:**
  - Subtotal
  - Descuento (% y monto)
  - IVA (monto)
  - Subtotal + IVA
  - Retencion en la fuente
  - **Total a pagar**
- **Tabla de lineas:** Producto, cantidad ordenada, cantidad despachada, precio unitario, descuento linea %, IVA, retencion %, retencion $, total linea
- **Facturacion:** CUFE, numero de factura, estado, PDF descargable
- **Nota credito:** CUFE, numero, estado (si aplica)
- **Remision:** Numero, fecha, PDF descargable (si despachada)
- **Historial de aprobaciones:** Quien solicito, quien aprobo/rechazo, razones
- **Trazabilidad de lotes:** Que lotes se usaron en esta orden

---

## 2.6 Stock — Gestion de Inventario

**Que es:** El modulo central para controlar las cantidades reales de cada producto en cada bodega.

**Para que sirve:** Saber en todo momento cuanto hay de cada producto, donde esta, cuanto esta reservado y cuanto esta disponible para vender.

**Como acceder:** Menu lateral > Inventario > Movimientos (`/inventario/movimientos`)

### Conceptos Clave de Stock

| Concepto | Significado |
|----------|-------------|
| **En mano (qty_on_hand)** | Cantidad fisica presente en la bodega |
| **Reservado (qty_reserved)** | Apartado para ordenes de venta confirmadas, aun no despachadas |
| **En transito (qty_in_transit)** | En camino desde otra bodega (transferencia en 2 fases) |
| **Disponible** | = En mano - Reservado. Lo que realmente puedes vender o transferir |

### Ajustes Manuales de Stock

Cuando necesitas corregir cantidades (perdida, robo, error de conteo, regalo):

**Ajuste a cantidad exacta:**
1. Producto + Bodega + Nueva cantidad = el sistema calcula la diferencia

**Ajuste positivo (entrada):**
1. Producto + Bodega + Cantidad a agregar + Razon

**Ajuste negativo (salida):**
1. Producto + Bodega + Cantidad a restar + Razon

**Merma/Desperdicio:**
1. Producto + Bodega + Cantidad perdida + Razon
2. Se registra como movimiento tipo "waste"

**Devolucion:**
1. Producto + Bodega + Cantidad devuelta + Referencia
2. Se registra como movimiento tipo "return"

> Consejo: Todos los ajustes quedan registrados en el historial de movimientos y en el log de auditoria. Siempre agrega una razon descriptiva.

### Control de Calidad (QC)

Si un tipo de producto tiene QC activado:
1. Al recibir mercancia, el stock queda en estado "Pendiente QC"
2. El stock pendiente QC no esta disponible para venta ni despacho
3. Un responsable debe:
   - **Aprobar QC:** El stock pasa a disponible
   - **Rechazar QC:** El stock queda marcado como rechazado

### Conteos Ciclicos

**Que son:** Verificaciones fisicas del inventario que se hacen periodicamente sin detener operaciones. A diferencia de un inventario completo, se cuentan grupos de productos en rotacion.

**Para que sirven:** Mantener la precision del inventario sin cerrar la bodega. El indicador IRA (Item Record Accuracy) mide que tan exacto es tu inventario.

**Como hacerlos:**
1. Ve a Inventario > Conteos (`/inventario/conteos`)
2. Haz clic en "Nuevo Conteo"
3. Configura:
   - **Bodega** — Cual bodega contar
   - **Productos** — Todos o seleccionar especificos
   - **Metodologia:** control_group, location_audit, random_selection, diminishing_population, product_category, abc
   - **Contadores asignados** — Cuantas personas contaran
   - **Minutos por conteo** — Estimado por item

4. **Iniciar conteo:** Genera la lista de items a contar
5. **Registrar conteos:** Para cada item, ingresa la cantidad fisica encontrada
6. **Reconteo:** Si hay discrepancias significativas, puedes pedir un reconteo con causa raiz
7. **Completar:** Cuando todos los items estan contados
8. **Aprobar:** Se aplican los ajustes de inventario

> Atencion: Los ajustes se aplican como DELTA (diferencia), no como valor absoluto. Si entre el momento del conteo y la aprobacion hubo movimientos legitimos, esos movimientos se conservan.

**IRA (Item Record Accuracy):**
- Se calcula automaticamente al aprobar un conteo
- Formula: (items sin discrepancia / total items) x 100
- Un IRA del 95% o superior se considera bueno
- Puedes ver la tendencia historica del IRA en la pagina de conteos

### Kardex

**Que es:** El libro de movimientos valorizado de un producto. Muestra cada entrada y salida con su costo unitario, costo promedio ponderado y saldo acumulado.

**Como acceder:** Inventario > Kardex (`/inventario/kardex`)
1. Selecciona un producto
2. Opcionalmente filtra por bodega
3. Veras una tabla con: fecha, tipo movimiento, cantidad, costo unitario, costo promedio, saldo, valor

---

## 2.7 Configuracion — Impuestos

**Que es:** La configuracion de las tarifas de impuestos que aplican a tus productos y ventas. Incluye IVA, retencion en la fuente y otros impuestos colombianos.

**Como acceder:** Menu lateral > Inventario > Configuracion > Impuestos (`/inventario/configuracion/impuestos`)

### Inicializar Tarifas Colombia

Si es la primera vez que usas el modulo:
1. Haz clic en el boton "Inicializar Colombia"
2. El sistema crea automaticamente las tarifas estandar:
   - **IVA 19%** — Tarifa general (marcada como default)
   - **IVA 5%** — Tarifa diferencial
   - **IVA 0% Exento** — Productos exentos
   - **Retencion 2.5%** — Servicios generales
   - **Retencion 3.5%** — Compras generales

### Crear Tarifas Personalizadas

Cuando necesites una tarifa que no esta en las predeterminadas:
1. Haz clic en "Nueva tarifa"
2. Completa:
   - **Nombre** — Descriptivo (ej: "IVA 8% Servicios")
   - **Tipo:** IVA, Retencion o ICA
   - **Tarifa (%)** — Porcentaje (ej: 8 para 8%)
   - **Codigo DIAN** — Si aplica, el codigo oficial
   - **Por defecto** — Si debe ser la tarifa predeterminada de su tipo
   - **Descripcion** — Nota de referencia

### Como Aparece el IVA en las Facturas

- Cada producto tiene asignada una tarifa IVA (o es exento)
- Al crear una OV, la tarifa se selecciona automaticamente segun el producto
- Puedes cambiarla manualmente por linea en el formulario de la OV
- En la factura electronica, el IVA aparece desglosado por tarifa
- La retencion se calcula sobre el subtotal de cada linea y se resta del total

---

## 2.8 Configuracion — Facturacion Electronica

**Que es:** La integracion con la DIAN (Direccion de Impuestos y Aduanas Nacionales) para emitir facturas electronicas validas en Colombia.

**Como acceder:** Menu lateral > Facturacion Electronica (`/facturacion-electronica`)

### Modo Sandbox (Pruebas)

**Para que sirve:** Probar que la facturacion funciona correctamente antes de activar el modo real. Las facturas generadas en sandbox no tienen validez legal.

**Como activarlo:**
1. Ve al Marketplace y activa el modulo "Facturacion Electronica — Sandbox"
2. En la pagina de Facturacion Electronica, las facturas se generaran con marca de agua "SIMULADO"
3. Puedes simular facturas manualmente desde la pagina de Sandbox (`/facturacion-electronica-sandbox`)

**Que puedes hacer en sandbox:**
- Confirmar ordenes de venta y ver la factura simulada generarse
- Verificar que los datos del cliente (NIT, razon social) aparecen correctamente
- Descargar PDFs de facturas simuladas
- Probar el flujo de notas credito
- Todo sin consecuencias legales ni tributarias

### Modo Real (MATIAS)

**Requisitos para activar:**
1. Tu empresa debe estar habilitada como facturador electronico ante la DIAN
2. Debes tener una cuenta con el proveedor MATIAS (API de facturacion)
3. Debes tener una resolucion de facturacion vigente

**Como configurar:**
1. Activa el modulo "Facturacion Electronica" en el Marketplace
2. En la pagina de Facturacion Electronica, haz clic en "Configurar"
3. Ingresa tu API Key de MATIAS
4. Opcionalmente activa el "Modo Simulacion" (usa MATIAS pero no envia a la DIAN)
5. Haz clic en "Probar conexion" para verificar

### Resolucion DIAN

**Que es:** Un documento emitido por la DIAN que autoriza a tu empresa a emitir facturas electronicas con un prefijo y rango de numeracion especifico. Ejemplo: Resolucion #18760000001, prefijo "FV", numeros del 1 al 5000.

**Como obtenerla:**
- Se tramita a traves del portal de la DIAN (www.dian.gov.co)
- La DIAN asigna un numero de resolucion, prefijo, rango y vigencia

**Como registrarla en TraceLog:**
1. Ve a Facturacion Electronica > Resolucion (`/facturacion-electronica/resolucion`)
2. Ingresa los datos de tu resolucion:
   - **Numero de resolucion** — El asignado por la DIAN
   - **Prefijo** — El prefijo para tus facturas (ej: "FV")
   - **Rango desde** — Primer numero del rango (ej: 1)
   - **Rango hasta** — Ultimo numero del rango (ej: 5000)
   - **Vigente desde** — Fecha de inicio de la resolucion
   - **Vigente hasta** — Fecha de vencimiento
3. Haz clic en "Guardar"

**Alertas de resolucion:**
- El sistema muestra cuantos numeros quedan disponibles
- Cuando quedan menos de 100 numeros, aparece una alerta de advertencia
- Cuando la resolucion esta vencida o agotada, aparece una alerta roja

**Que hacer cuando se agota el rango:**
1. Solicita una nueva resolucion a la DIAN
2. Registra la nueva resolucion en TraceLog (la anterior se desactiva automaticamente)
3. Las facturas nuevas usaran el nuevo prefijo y rango

---

## 2.9 Configuracion — Aprobaciones

**Que es:** Un flujo de autorizacion que requiere que un supervisor apruebe ordenes de venta que superen un monto determinado.

**Para que sirve:** Controlar ventas de alto valor, evitar errores en precios o descuentos excesivos, y mantener un registro de quien autorizo cada venta importante.

**Como acceder:**
- Configuracion: Inventario > Configuracion, pestana "Aprobaciones"
- Cola de aprobaciones: Inventario > Aprobaciones (`/inventario/aprobaciones`)

### Como Configurar el Umbral

1. Ve a Inventario > Configuracion
2. En la pestana "Aprobaciones", define el **umbral de aprobacion**
3. Ingresa el monto (en COP). Ejemplo: 5,000,000
4. Cualquier OV con total igual o superior a este monto requerira aprobacion
5. Si dejas el campo vacio, se desactiva la aprobacion por monto

### Quien Puede Aprobar

Solo usuarios con el permiso `so.approve` pueden aprobar o rechazar ordenes. Esto se configura en Administracion > Roles.

> Atencion: La persona que creo la OV no puede aprobarla. Debe ser un usuario diferente.

### Proceso de Aprobacion

1. Un vendedor crea una OV por $8,000,000 (supera el umbral de $5,000,000)
2. Al intentar confirmar, la OV pasa a estado "Pendiente de Aprobacion"
3. La OV aparece en la cola de aprobaciones con indicadores:
   - Nombre del solicitante
   - Monto total
   - Tiempo de espera
4. El supervisor revisa y decide:
   - **Aprobar:** La OV continua el flujo normal (reserva de stock + facturacion)
   - **Rechazar:** La OV vuelve a borrador. Se requiere una razon de minimo 10 caracteres.
5. Si fue rechazada, el vendedor puede:
   - Modificar la OV (ajustar precios, quitar lineas)
   - Reenviar para aprobacion

---

## 2.10 Reorden Automatico

**Que es:** Un mecanismo que genera ordenes de compra automaticamente cuando el stock de un producto cae por debajo de su punto de reorden (ROP).

**Para que sirve:** Evitar quiebres de stock. El sistema monitorea los niveles de inventario y crea borradores de OC que puedes revisar y enviar al proveedor.

### Como Configurarlo por Producto

1. Edita el producto en el catalogo
2. Configura:
   - **Punto de reorden (ROP)** — Cuando el stock disponible (en mano - reservado) caiga a este nivel, se activa el reorden. Ejemplo: 50 unidades.
   - **Cantidad de reorden** — Cuantas unidades comprar. Ejemplo: 200 unidades.
   - **Proveedor preferido** — A quien se le genera la OC automaticamente.
   - **Reorden automatico** — Activa/desactiva el mecanismo.

### Cuando se Generan las OC Automaticas

El sistema verifica los niveles de stock dos veces:
1. **Automaticamente:** Cada 24 horas, un proceso revisa todos los productos con reorden activo
2. **Manualmente:** En Inventario > Reorden (`/inventario/reorden`), puedes hacer clic en "Verificar ahora"

### Diferencia con OC Manuales

| Caracteristica | OC Automatica | OC Manual |
|---------------|---------------|-----------|
| Creada por | El sistema | Un usuario |
| Estado inicial | Borrador | Borrador |
| Se puede editar | Si | Si |
| Marcada como | "Auto-reorden" | Normal |
| Validacion duplicado | No crea si ya hay una OC abierta para ese producto | No valida |

> Consejo: Las OC automaticas se crean como borrador. Siempre revisalas antes de enviarlas al proveedor. Puedes ajustar cantidades o agregar productos adicionales.

### Ver Configuracion de Reorden

En Inventario > Reorden (`/inventario/reorden`) puedes ver:
- Todos los productos con reorden activo
- Stock actual vs punto de reorden
- Si estan por debajo del ROP
- Si ya hay una OC abierta para ese producto
- Proveedor preferido asignado

---

## 2.11 Analiticas y Reportes

**Que es:** Un conjunto de dashboards, indicadores y reportes descargables que te ayudan a tomar decisiones sobre tu inventario.

**Como acceder:** Menu lateral > Inventario > Dashboard (`/inventario`)

### Dashboard Principal

El dashboard muestra tarjetas con KPIs en tiempo real:

- **Total de SKUs** — Cuantos productos diferentes manejas
- **Valor total de inventario** — Suma del costo de todo el stock
- **Productos con stock bajo** — Por debajo del minimo configurado
- **Productos agotados** — Sin stock en ninguna bodega
- **OC pendientes** — Ordenes de compra sin recibir
- **Lotes por vencer** — En los proximos 30 dias
- **Produccion este mes** — Ordenes de produccion completadas
- **Ultimo IRA** — Precision del inventario del ultimo conteo

**Graficos:**
- **Tendencia de movimientos (30 dias)** — Grafico de linea mostrando actividad diaria
- **Movimientos por tipo** — Grafico circular (compras, ventas, transferencias, ajustes, etc.)
- **Distribucion por tipo de producto** — Barras
- **Distribucion por tipo de proveedor** — Barras

### Clasificacion ABC (Analisis de Pareto)

**Que mide:** Clasifica tus productos en tres categorias segun su contribucion al valor total de movimientos:

- **Clase A (≤80% del valor)** — Pocos productos, alto valor. Requieren control estrecho.
- **Clase B (80-95%)** — Productos de valor intermedio. Control moderado.
- **Clase C (95-100%)** — Muchos productos, bajo valor individual. Control basico.

**Como usarlo:** Ve a Dashboard > seccion ABC. Puedes ajustar el periodo de analisis (por defecto 12 meses). Los resultados te ayudan a priorizar conteos ciclicos y negociaciones con proveedores.

### EOQ (Cantidad Economica de Pedido)

**Que es:** Calcula la cantidad optima a comprar de cada producto para minimizar el costo total (costo de ordenar + costo de almacenar).

**Formula Wilson:** EOQ = √(2 × Demanda anual × Costo por orden / Costo de almacenamiento)

**Parametros ajustables:**
- Costo por orden (default: $50 por OC)
- Porcentaje de costo de almacenamiento (default: 25% anual del valor)

**Como usarlo:** Ve a Dashboard > seccion EOQ. El sistema calcula automaticamente para cada producto con historial de movimientos.

### IRA (Precision del Inventario)

**Que mide:** Que tan exacto es tu inventario comparado con la realidad fisica.

**Formula:** IRA = (Items sin discrepancia / Total items contados) × 100

**Meta recomendada:** 95% o superior.

**Como verlo:**
- En cada conteo ciclico aprobado, se calcula el IRA
- En Dashboard puedes ver la tendencia historica del IRA
- Si el IRA baja, indica problemas de control: hurto, errores de conteo, perdida no registrada

### Ocupacion de Bodegas

**Que muestra:** Que porcentaje de la capacidad de cada bodega esta siendo utilizada.

Dos modos de calculo:
- **Por ubicaciones:** Ubicaciones ocupadas / Total ubicaciones × 100
- **Por capacidad:** Stock actual / Capacidad maxima × 100

Incluye deteccion de **stock estancado**: productos sin movimiento en los ultimos 180 dias.

### Valuacion de Almacenamiento

**Que muestra:** Cuanto cuesta almacenar tu inventario en cada bodega.

Basado en: area (m2) × costo por m2 configurado en cada bodega.

### Reportes Descargables (CSV)

Disponibles en: Inventario > Reportes (`/inventario/reportes`)

| Reporte | Contenido |
|---------|-----------|
| Productos | SKU, nombre, tipo, precios, stock minimo, estado |
| Stock | Niveles por producto/bodega/lote |
| Movimientos | Historial con filtro de fechas |
| Proveedores | Directorio completo |
| Eventos | Incidentes con filtro de fechas |
| Seriales | Listado de seriales con estados |
| Lotes | Listado de lotes con vencimientos |
| Ordenes de compra | OC con filtro de fechas |

### Alertas Automaticas

El sistema genera alertas de tres tipos:

| Tipo | Cuando se genera | Como resolverla |
|------|-----------------|-----------------|
| **Stock bajo** | qty_on_hand < min_stock_level | Comprar mas (crear OC) |
| **Agotado** | qty_on_hand = 0 | Compra urgente |
| **Proximo a vencer** | Lote vence en < 30 dias | Despachar primero (FEFO) o ajustar |

Las alertas se ven en: Inventario > Alertas (`/inventario/alertas`). Puedes marcarlas como leidas o resueltas. El contador de alertas no leidas aparece en el menu lateral.

### Auditoria

Todo cambio en el modulo de inventario queda registrado con:
- Quien lo hizo (usuario)
- Que hizo (accion)
- Datos anteriores y nuevos
- Desde donde (IP)
- Cuando (timestamp)

Accesible en: Inventario > Auditoria (`/inventario/auditoria`)

---

## Glosario Tecnico-Funcional

| Termino | Explicacion |
|---------|-------------|
| **SKU** | Stock Keeping Unit. Codigo interno unico que identifica cada producto en tu inventario. Ejemplo: "CAFE-COL-500G". |
| **CUFE** | Codigo Unico de Factura Electronica. Identificador alfanumerico asignado por la DIAN a cada factura electronica emitida en Colombia. Permite verificar la autenticidad de la factura. |
| **DIAN** | Direccion de Impuestos y Aduanas Nacionales de Colombia. Entidad gubernamental que regula la facturacion electronica y los impuestos. |
| **NIT** | Numero de Identificacion Tributaria. Codigo fiscal de empresas y personas naturales en Colombia. |
| **IVA** | Impuesto al Valor Agregado. Impuesto al consumo con tarifas del 0%, 5% o 19% segun el producto en Colombia. |
| **Retencion en la fuente** | Porcentaje que el comprador retiene del pago al vendedor como anticipo de impuestos. Comun en transacciones B2B en Colombia. |
| **ICA** | Impuesto de Industria y Comercio. Impuesto municipal sobre actividades comerciales, industriales y de servicios. |
| **FEFO** | First Expired, First Out. Metodo de despacho que prioriza enviar primero los lotes con fecha de vencimiento mas proxima. Obligatorio en alimentos y farmaceuticos. |
| **FIFO** | First In, First Out. Metodo de costeo/despacho que asume que las primeras unidades en entrar son las primeras en salir. |
| **LIFO** | Last In, First Out. Metodo donde las ultimas unidades en entrar son las primeras en salir. Menos comun. |
| **ROP** | Reorder Point (Punto de Reorden). Nivel minimo de stock que al alcanzarse dispara una compra automatica o alerta. |
| **EOQ** | Economic Order Quantity (Cantidad Economica de Pedido). Formula matematica que calcula la cantidad optima a comprar para minimizar costos totales. |
| **IRA** | Item Record Accuracy (Precision del Registro de Items). Porcentaje que mide que tan exacto es tu inventario en sistema vs la realidad fisica. Meta: ≥95%. |
| **ABC** | Clasificacion de Pareto. Divide productos en A (alto valor, ~20% items = ~80% valor), B (medio) y C (bajo valor, ~50% items = ~5% valor). |
| **SO** | Sales Order (Orden de Venta). Documento que registra la venta de productos a un cliente. |
| **PO** | Purchase Order (Orden de Compra). Documento que registra la compra de productos a un proveedor. |
| **BO** | Backorder (Pedido Pendiente). Orden de venta generada automaticamente para las cantidades que no pudieron despacharse por falta de stock. |
| **OC** | Orden de Compra. Equivalente en espanol de PO. |
| **OV** | Orden de Venta. Equivalente en espanol de SO. |
| **BOM** | Bill of Materials (Lista de Materiales). En TraceLog se llaman "Recetas". Define los componentes necesarios para producir un producto terminado. |
| **QC** | Quality Control (Control de Calidad). Proceso de verificacion de mercancia recibida antes de habilitarla para venta. |
| **UoM** | Unit of Measure (Unidad de Medida). La unidad en que se cuenta un producto: unidad, kilogramo, litro, caja, etc. |
| **Kardex** | Libro de inventario valorizado. Registro de todos los movimientos de un producto con costos unitarios y saldo acumulado. |
| **Remision** | Documento de entrega que acompana la mercancia despachada. No es una factura; es un comprobante de lo que se envio fisicamente. |
| **Nota credito** | Documento electronico que anula total o parcialmente una factura. Se emite automaticamente al procesar una devolucion. |
| **Resolucion de facturacion** | Autorizacion de la DIAN para emitir facturas electronicas con un prefijo y rango de numeracion especifico. Tiene fecha de vigencia. |
| **MATIAS** | Proveedor de servicios de facturacion electronica. La API que TraceLog usa para emitir facturas validas ante la DIAN. |
| **Tenant** | Empresa u organizacion dentro de TraceLog. Cada tenant tiene sus propios datos aislados (productos, clientes, stock, facturas). |
| **Stock reservado** | Mercancia apartada para ordenes de venta confirmadas que aun no han sido despachadas. No se puede vender a otro cliente. |
| **Stock en transito** | Mercancia que salio de una bodega pero aun no llego a la bodega destino (en transferencia de 2 fases). |
| **Conteo ciclico** | Verificacion fisica parcial del inventario. Se cuentan grupos de productos en rotacion sin cerrar la bodega. |
| **Consolidacion de OC** | Unir varias ordenes de compra en borrador del mismo proveedor en una sola, para optimizar costos y logistica. |
| **Principio de 4 ojos** | Control de seguridad: la persona que crea o ejecuta una operacion no puede ser la misma que la aprueba. Aplicado en aprobaciones de OV y produccion. |
| **Fire-and-forget** | Patron tecnico: la facturacion electronica se dispara automaticamente pero no bloquea la operacion si falla. El usuario puede reintentar manualmente. |
| **Multi-tenant** | Arquitectura donde multiples empresas usan el mismo sistema, pero cada una solo ve y accede a sus propios datos. |
| **Modulo gate** | Verificacion que impide acceder al modulo de inventario si no esta activado para tu empresa en el Marketplace. |

---

*Documento base para manual de usuario — Modulo de Inventario TraceLog*
*Fecha: 2026-03-13*
*Basado en analisis del codigo fuente real del sistema*
