# Caso de Uso: Inventario Completo — Distribuidora de Cafe "Los Andes"

**Objetivo:** Recorrer TODAS las funcionalidades del modulo de inventario de Trace usando un caso real de una distribuidora de cafe colombiano que compra a fincas, procesa (tostado y molido), empaca en distintas presentaciones y vende a tiendas y restaurantes.

**Requisitos previos:**
- Tener la aplicacion corriendo (frontend en http://localhost:3000)
- Haber iniciado sesion con un usuario que tenga el rol **administrador**
- Tener el modulo **Inventario** activado (se activa desde el Marketplace)

**Tiempo estimado:** 45-60 minutos siguiendo cada paso.

---

## Como navegar

La barra lateral izquierda (sidebar) tiene una seccion llamada **Inventario**. Al expandirla veras 5 grupos:

1. **Arriba:** Inicio, Rentabilidad, Alertas
2. **Mis Productos:** Productos, Categorias
3. **Bodega y Despacho:** Bodegas, Movimientos, Lotes, Seriales, Conteo, Escaner, Picking, Reorden
4. **Compras y Ventas:** Socios, Compras, Ventas, Precios, Aprobaciones
5. **Informes:** Reportes, Kardex, Eventos, Auditoria
6. **Ajustes:** Configuracion, Impuestos, Medidas, Ayuda

Cada grupo se puede expandir o colapsar haciendo click en su nombre.

> **Nota sobre funcionalidades opcionales:** Algunos items del menu solo aparecen si la funcionalidad esta activada. Si no ves "Lotes", "Seriales", "Conteo", "Kardex", "Eventos", "Precios" o "Aprobaciones", primero ve a **Ajustes → Configuracion → Funcionalidades** y activalos ahi.

---

## FASE 1 — Configuracion Inicial

Antes de crear productos o hacer compras, hay que configurar los datos base del sistema.

---

### 1.1 Activar todas las funcionalidades

1. En la barra lateral, busca el grupo **Ajustes** (al final de la seccion Inventario).
2. Haz click en **Configuracion**.
3. Veras una cuadricula con 13 tarjetas de configuracion. Haz click en la tarjeta **"Funcionalidades"**.
4. Activa TODOS los toggles: Lotes, Seriales, Conteo Ciclico, Kardex, Eventos, Precios por Cliente, Aprobaciones, Escaner, Picking.
5. Esto hara que todos los items del menu lateral aparezcan disponibles.

---

### 1.2 Inicializar Unidades de Medida

1. En la barra lateral, dentro del grupo **Ajustes**, haz click en **Medidas**.
   - Esto te lleva a la pagina **"Unidades de Medida"** (`/inventario/unidades-medida`).
2. La pagina estara vacia si es la primera vez. Haz click en el boton **"Inicializar"** (o "Inicializar UoM estandar").
   - El sistema creara automaticamente las unidades basicas: kg, g, lb, unidad, docena, litro, ml, etc.
3. Verifica que aparecieron las unidades en la tabla.
4. Ahora crea una conversion personalizada:
   - Busca el boton **"Nueva conversion"** (o "Agregar conversion").
   - Configura: **1 arroba = 12.5 kg** (la arroba es una unidad comun en el cafe colombiano).
   - Guarda la conversion.

---

### 1.3 Configurar Impuestos

1. En la barra lateral, dentro del grupo **Ajustes**, haz click en **Impuestos**.
   - Esto te lleva a la pagina **"Tarifas de Impuesto"** (`/inventario/configuracion/impuestos`).
2. Haz click en el boton **"Inicializar"** para cargar las tasas por defecto.
   - El sistema creara: IVA 19%, IVA 5%, Excluido (0%), Exento (0%).
3. Verifica que las 4 tasas aparecen en la tabla.
4. Ahora crea categorias de impuesto (esto agrupa los productos por regimen fiscal):
   - Desde la misma pagina o desde **Configuracion → Categorias de impuesto** (`/inventario/configuracion/categorias-impuesto`).
   - Crea la categoria: **"Alimentos procesados"** — descripcion: "Productos alimenticios con procesamiento industrial".
   - Crea la categoria: **"Materia prima agricola"** — descripcion: "Productos agricolas sin procesar".

---

### 1.4 Configurar Tipos de Producto

1. En la barra lateral, dentro del grupo **Ajustes**, haz click en **Configuracion**.
2. Haz click en la tarjeta **"Tipos de producto"**.
   - Esto te lleva a `/inventario/configuracion/tipos-producto`.
3. Crea 3 tipos de producto (usa el boton "Nuevo" o "Crear"):
   - **"Materia Prima"** — descripcion: "Insumos que se compran a proveedores"
   - **"Producto Terminado"** — descripcion: "Producto listo para la venta"
   - **"Empaque"** — descripcion: "Material de empaque y embalaje"

---

### 1.5 Configurar Tipos de Bodega

1. Regresa a **Ajustes → Configuracion** (barra lateral).
2. Haz click en la tarjeta **"Tipos de bodega"**.
   - Esto te lleva a `/inventario/configuracion/tipos-bodega`.
3. Crea 2 tipos:
   - **"Almacen seco"** — descripcion: "Almacenamiento a temperatura ambiente"
   - **"Bodega fria"** — descripcion: "Almacenamiento refrigerado"

---

### 1.6 Configurar Tipos de Proveedor

1. Regresa a **Ajustes → Configuracion**.
2. Haz click en la tarjeta **"Tipos de proveedor"**.
   - Esto te lleva a `/inventario/configuracion/tipos-proveedor`.
3. Crea 2 tipos:
   - **"Finca cafetera"** — descripcion: "Productor directo de cafe"
   - **"Proveedor de empaques"** — descripcion: "Suministra material de empaque"

---

### 1.7 Configurar Tipos de Cliente

1. Regresa a **Ajustes → Configuracion**.
2. Haz click en la tarjeta **"Tipos de Cliente"**.
   - Esto te lleva a `/inventario/configuracion/customer-types`.
3. Crea 3 tipos:
   - **"Tienda"** — descripcion: "Tienda de barrio o especializada"
   - **"Restaurante"** — descripcion: "Restaurante, cafeteria o hotel"
   - **"Mayorista"** — descripcion: "Distribuidor que compra en volumen"

---

### 1.8 Configurar Tipos de Orden

1. Regresa a **Ajustes → Configuracion**.
2. Haz click en la tarjeta **"Tipos de orden"**.
   - Esto te lleva a `/inventario/configuracion/tipos-orden`.
3. Crea 2 tipos:
   - **"Pedido estandar"** — descripcion: "Orden de compra normal con plazo regular"
   - **"Pedido urgente"** — descripcion: "Orden prioritaria con entrega acelerada"

---

### 1.9 Crear Bodegas

1. En la barra lateral, dentro del grupo **Bodega y Despacho**, haz click en **Bodegas**.
   - Esto te lleva a la pagina **"Bodegas"** (`/inventario/bodegas`).
2. Haz click en el boton para crear una nueva bodega. Crea 3 bodegas:

   **Bodega 1:**
   - Nombre: **"Bodega Principal"**
   - Tipo: Almacen seco
   - Direccion: Calle 80 #45-12, Bogota
   - Guardar.

   **Bodega 2:**
   - Nombre: **"Bodega Producto Terminado"**
   - Tipo: Almacen seco
   - Guardar.

   **Bodega 3:**
   - Nombre: **"Bodega Transito"**
   - Tipo: (dejar como virtual o transit si la opcion existe)
   - Guardar.

3. Verifica que las 3 bodegas aparecen en la lista.

---

### 1.10 Crear Ubicaciones dentro de la Bodega Principal

1. En la lista de bodegas, haz click en **"Bodega Principal"** para entrar a su detalle.
   - Esto te lleva a `/inventario/bodegas/{id}`.
2. Busca la seccion de **Ubicaciones** dentro del detalle.
3. Crea 3 ubicaciones:
   - **A-01** — descripcion: "Zona de cafe verde"
   - **A-02** — descripcion: "Zona de empaques"
   - **B-01** — descripcion: "Zona de cafe tostado"
4. Regresa a la lista de bodegas haciendo click en **Bodegas** en la barra lateral.

---

## FASE 2 — Maestros (Productos, Proveedores, Clientes)

Ahora vamos a crear los datos maestros: los productos que manejamos, a quien le compramos y a quien le vendemos.

---

### 2.1 Crear Categorias de Producto

1. En la barra lateral, dentro del grupo **Mis Productos**, haz click en **Categorias**.
   - Esto te lleva a la pagina **"Categorias de producto"** (`/inventario/categorias`).
2. Crea la categoria padre:
   - Nombre: **"Cafe"**
   - Sin padre (es categoria raiz).
   - Guardar.
3. Crea 3 subcategorias (seleccionando "Cafe" como padre):
   - **"Cafe Verde"** — padre: Cafe
   - **"Cafe Tostado"** — padre: Cafe
   - **"Cafe Molido"** — padre: Cafe
4. Crea una categoria independiente:
   - **"Empaques"** — sin padre.

Deberias ver la jerarquia asi:
```
Cafe
  ├── Cafe Verde
  ├── Cafe Tostado
  └── Cafe Molido
Empaques
```

---

### 2.2 Crear Productos

1. En la barra lateral, dentro del grupo **Mis Productos**, haz click en **Productos**.
   - Esto te lleva a la pagina **"Productos"** (`/inventario/productos`).
2. Haz click en el boton para crear un nuevo producto. Crea estos 6 productos uno por uno:

   **Producto 1 — Materia prima:**
   - Nombre: **Cafe Verde Huila**
   - SKU: **CV-HUILA**
   - Tipo de producto: Materia Prima
   - Categoria: Cafe Verde
   - Unidad de medida: kg
   - Costo: **18000**
   - Precio de venta: (dejar vacio, no se vende directo)
   - Impuesto: Excluido
   - Guardar.

   **Producto 2 — Materia prima:**
   - Nombre: **Cafe Verde Narino**
   - SKU: **CV-NAR**
   - Tipo de producto: Materia Prima
   - Categoria: Cafe Verde
   - Unidad de medida: kg
   - Costo: **22000**
   - Impuesto: Excluido
   - Guardar.

   **Producto 3 — Producto terminado:**
   - Nombre: **Cafe Tostado Origen Huila 500g**
   - SKU: **CT-HUILA-500**
   - Tipo de producto: Producto Terminado
   - Categoria: Cafe Tostado
   - Unidad de medida: unidad
   - Costo: (dejar vacio, se calculara con la receta)
   - Precio de venta: **32000**
   - Impuesto: IVA 5%
   - Guardar.

   **Producto 4 — Producto terminado:**
   - Nombre: **Cafe Molido Blend 250g**
   - SKU: **CM-BLEND-250**
   - Tipo de producto: Producto Terminado
   - Categoria: Cafe Molido
   - Unidad de medida: unidad
   - Precio de venta: **18500**
   - Impuesto: IVA 5%
   - Guardar.

   **Producto 5 — Empaque:**
   - Nombre: **Bolsa kraft 500g**
   - SKU: **EMP-KRAFT-500**
   - Tipo de producto: Empaque
   - Categoria: Empaques
   - Unidad de medida: unidad
   - Costo: **800**
   - Impuesto: IVA 19%
   - Guardar.

   **Producto 6 — Empaque:**
   - Nombre: **Bolsa kraft 250g**
   - SKU: **EMP-KRAFT-250**
   - Tipo de producto: Empaque
   - Categoria: Empaques
   - Unidad de medida: unidad
   - Costo: **600**
   - Impuesto: IVA 19%
   - Guardar.

3. Verifica que los 6 productos aparecen en la tabla de productos.

---

### 2.3 Crear Variantes (para el Cafe Tostado)

Las variantes permiten tener distintas versiones de un mismo producto (por ejemplo, distintos niveles de tostion).

1. En la barra lateral, NO hay un link directo a variantes en el menu principal. Ve a la URL directamente: **`/inventario/variantes`**.
   - Veras la pagina **"Atributos de Variante"**.
2. Crea un atributo:
   - Nombre: **"Nivel de Tostion"**
   - Guardar.
3. Agrega opciones al atributo:
   - **Media**
   - **Oscura**
   - **Especial**
4. Ahora crea variantes para el producto CT-HUILA-500:
   - Variante 1: SKU **CT-HUILA-500-MED**, atributo: Nivel de Tostion = Media
   - Variante 2: SKU **CT-HUILA-500-OSC**, atributo: Nivel de Tostion = Oscura

---

### 2.4 Crear Proveedores (Socios Comerciales)

1. En la barra lateral, dentro del grupo **Compras y Ventas**, haz click en **Socios**.
   - Esto te lleva a la pagina **"Socios Comerciales"** (`/inventario/socios`).
2. Crea 3 proveedores:

   **Proveedor 1:**
   - Nombre: **Finca El Paraiso**
   - Tipo: Finca cafetera
   - Contacto: Juan Perez
   - Telefono: 311-555-0001
   - Email: finca.paraiso@test.com
   - Guardar.

   **Proveedor 2:**
   - Nombre: **Finca La Esperanza**
   - Tipo: Finca cafetera
   - Guardar.

   **Proveedor 3:**
   - Nombre: **Empaques del Valle**
   - Tipo: Proveedor de empaques
   - Guardar.

---

### 2.5 Crear Clientes

En la misma pagina de **Socios Comerciales**, tambien puedes crear clientes (o puede haber un tab/filtro para diferenciar proveedores de clientes).

1. Crea 3 clientes:

   **Cliente 1:**
   - Nombre: **Tienda Cafe & Co**
   - Tipo: Tienda
   - NIT/Documento: 900.123.456-7
   - Guardar.

   **Cliente 2:**
   - Nombre: **Restaurante El Fogon**
   - Tipo: Restaurante
   - Guardar.

   **Cliente 3:**
   - Nombre: **Distribuidora Central**
   - Tipo: Mayorista
   - Guardar.

---

### 2.6 Configurar Precios Especiales por Cliente

1. En la barra lateral, dentro del grupo **Compras y Ventas**, haz click en **Precios**.
   - Esto te lleva a la pagina **"Precios Especiales por Cliente"** (`/inventario/precios-clientes`).
2. Crea 2 reglas de precio:

   **Regla 1 — Descuento mayorista:**
   - Cliente: Distribuidora Central
   - Producto: Cafe Tostado Origen Huila 500g (CT-HUILA-500)
   - Tipo: Descuento porcentual **10%**
   - Guardar.

   **Regla 2 — Precio fijo restaurante:**
   - Cliente: Restaurante El Fogon
   - Producto: Cafe Tostado Origen Huila 500g (CT-HUILA-500)
   - Tipo: Precio fijo **30000**
   - Guardar.

---

## FASE 3 — Compras (Ordenes de Compra)

Ahora vamos a simular la compra de materia prima a los proveedores.

---

### 3.1 Crear Orden de Compra de Cafe Verde

1. En la barra lateral, dentro del grupo **Compras y Ventas**, haz click en **Compras**.
   - Esto te lleva a la pagina **"Ordenes de Compra"** (`/inventario/compras`).
2. Haz click en el boton para crear una nueva orden de compra.
3. Llena los datos:
   - Proveedor: **Finca El Paraiso**
   - Tipo de orden: Pedido estandar
   - Agrega una linea:
     - Producto: **Cafe Verde Huila**
     - Cantidad: **50** (kg)
     - Precio unitario: **18000**
     - Subtotal: $900,000
4. **Guarda** la orden. Veras que queda en estado **Borrador** y se le asigna un numero como PO-2026-0001.

---

### 3.2 Enviar y Confirmar la Orden de Compra

1. Haz click en la orden que acabas de crear para ver su detalle.
   - Esto te lleva a `/inventario/compras/{id}`.
2. Haz click en el boton **"Enviar"**. El estado cambia a **Enviada**.
   - (Esto simula que le enviaste la orden al proveedor.)
3. Haz click en el boton **"Confirmar"**. El estado cambia a **Confirmada**.
   - (El proveedor acepto la orden.)

---

### 3.3 Recibir la Mercancia

1. Estando en el detalle de la PO, haz click en el boton **"Recibir"**.
   - El estado cambia a **Recibida**.
   - El sistema automaticamente crea un movimiento de stock tipo `purchase` y agrega 50 kg de Cafe Verde Huila a la Bodega Principal.
2. **Verificar el stock:**
   - Ve a la barra lateral → grupo **Bodega y Despacho** → **Movimientos** (`/inventario/movimientos`).
   - Busca el movimiento mas reciente. Debe decir: tipo `purchase`, producto Cafe Verde Huila, cantidad 50 kg.
3. **Verificar en Productos:**
   - Ve a **Mis Productos → Productos** y haz click en Cafe Verde Huila.
   - Debe mostrar stock disponible: **50 kg**.

---

### 3.4 Crear segunda Orden de Compra (Empaques)

1. Regresa a **Compras y Ventas → Compras**.
2. Crea una nueva PO:
   - Proveedor: **Empaques del Valle**
   - Linea 1: Bolsa kraft 500g — 200 unidades x $800 = $160,000
   - Linea 2: Bolsa kraft 250g — 300 unidades x $600 = $180,000
   - Total: $340,000
3. Guarda → Enviar → Confirmar → Recibir.
4. Verifica el stock:
   - Bolsa kraft 500g: **200 unidades**
   - Bolsa kraft 250g: **300 unidades**

---

## FASE 4 — Produccion (Recetas y Ordenes de Produccion)

El cafe verde se tuesta y se empaca. Para esto usamos recetas (Bill of Materials) y ordenes de produccion.

---

### 4.1 Crear una Receta (Bill of Materials)

1. Ve directamente a la URL **`/inventario/recetas`** (no hay link en el sidebar por defecto, pero la pagina existe).
   - Si no carga, verifica que la ruta este habilitada.
2. Crea una nueva receta:
   - Nombre: **"Cafe Tostado Huila 500g"**
   - Producto resultado: Cafe Tostado Origen Huila 500g (CT-HUILA-500)
   - Ingredientes (inputs):
     - **0.6 kg** de Cafe Verde Huila (se pierde ~17% de peso en el tostado, por eso 600g → 500g)
     - **1 unidad** de Bolsa kraft 500g
   - Cantidad de salida: **1 unidad** de CT-HUILA-500
3. Guardar la receta.

---

### 4.2 Crear una Orden de Produccion

1. Ve directamente a la URL **`/inventario/produccion`** (puede aparecer como "Produccion" si se agrego al menu).
2. Crea una nueva orden de produccion:
   - Receta: **Cafe Tostado Huila 500g**
   - Cantidad a producir: **30 unidades**
   - El sistema debe calcular automaticamente los materiales necesarios:
     - 30 x 0.6 kg = **18 kg** de Cafe Verde Huila
     - 30 x 1 = **30 unidades** de Bolsa kraft 500g
3. Guarda la orden (queda en estado Borrador/Pendiente).
4. Haz click en **"Liberar"** para iniciar la produccion.

---

### 4.3 Emitir Materiales (Consumir insumos)

1. Dentro del detalle de la orden de produccion, busca la seccion de **Emisiones** (materiales consumidos).
2. Crea una emision:
   - Producto: Cafe Verde Huila — Cantidad: **18 kg** — Desde: Bodega Principal
3. Crea otra emision:
   - Producto: Bolsa kraft 500g — Cantidad: **30 unidades** — Desde: Bodega Principal
4. Verifica que el stock cambio:
   - Cafe Verde Huila: 50 - 18 = **32 kg**
   - Bolsa kraft 500g: 200 - 30 = **170 unidades**

---

### 4.4 Recibir Producto Terminado

1. Dentro del detalle de la orden de produccion, busca la seccion de **Recibos** (producto terminado).
2. Crea un recibo:
   - Producto: Cafe Tostado Origen Huila 500g — Cantidad: **30 unidades** — Hacia: Bodega Producto Terminado
3. Haz click en **"Cerrar"** la orden de produccion.
4. Verifica stock:
   - CT-HUILA-500 en Bodega Producto Terminado = **30 unidades**

---

### 4.5 Crear un Lote (Trazabilidad)

Los lotes permiten rastrear cuando se produjo cada tanda y cuando vence.

1. En la barra lateral, dentro del grupo **Bodega y Despacho**, haz click en **Lotes**.
   - Esto te lleva a la pagina **"Lotes"** (`/inventario/lotes`).
2. Crea un nuevo lote:
   - Numero de lote: **LOT-2026-04-001**
   - Producto: Cafe Tostado Origen Huila 500g (CT-HUILA-500)
   - Fecha de produccion: **2026-04-09** (hoy)
   - Fecha de vencimiento: **2026-10-09** (6 meses)
   - Cantidad: **30**
3. Guardar.

---

## FASE 5 — Ventas (Ordenes de Venta)

Ahora vamos a vender el cafe tostado a nuestros clientes.

---

### 5.1 Crear una Orden de Venta

1. En la barra lateral, dentro del grupo **Compras y Ventas**, haz click en **Ventas**.
   - Esto te lleva a la pagina **"Ordenes de Venta"** (`/inventario/ventas`).
2. Haz click en el boton para crear una nueva orden.
3. Llena los datos:
   - Cliente: **Tienda Cafe & Co**
   - Agrega una linea:
     - Producto: **Cafe Tostado Origen Huila 500g** (CT-HUILA-500)
     - Cantidad: **10 unidades**
     - Precio unitario: **32000** (precio base)
     - Subtotal: $320,000
     - Impuesto IVA 5%: $16,000
     - **Total: $336,000**
4. **Guarda** la orden. Queda en estado **Borrador**.

---

### 5.2 Verificar Disponibilidad de Stock

1. Dentro del detalle de la orden de venta (`/inventario/ventas/{id}`), busca el boton **"Verificar Stock"**.
2. Haz click. El sistema verifica:
   - Stock disponible de CT-HUILA-500: 30 unidades
   - Cantidad solicitada: 10 unidades
   - Resultado: **Disponible** ✓

---

### 5.3 Confirmar la Orden (Reserva de Stock)

1. Haz click en el boton **"Confirmar"**.
2. El estado cambia a **Confirmada**.
3. El sistema automaticamente **reserva** 10 unidades del stock.
4. Si vas a verificar el stock del producto, veras:
   - En mano (on_hand): 30
   - Reservado: 10
   - Disponible: 20

---

### 5.4 Picking (Preparar el pedido)

1. Haz click en el boton **"Picking"** (o ve a la pagina de picking desde **Bodega y Despacho → Picking**).
2. Selecciona las 10 unidades del lote **LOT-2026-04-001**.
3. Esto confirma de que lote salen las unidades (trazabilidad completa).

---

### 5.5 Despachar

1. Haz click en el boton **"Despachar"** (Ship).
2. El estado cambia a **Despachada**.
3. El stock on_hand baja de 30 a **20 unidades**.

---

### 5.6 Entregar

1. Haz click en el boton **"Entregar"** (Deliver).
2. El estado cambia a **Entregada**. La venta esta completa.

---

### 5.7 Crear segunda venta — Mayorista con descuento

1. Regresa a **Compras y Ventas → Ventas** y crea otra orden:
   - Cliente: **Distribuidora Central**
   - Producto: CT-HUILA-500 — 15 unidades
   - Verifica que el **precio especial** aplica automaticamente: 10% descuento sobre $32,000 = **$28,800** por unidad
   - Total: 15 x $28,800 = $432,000 + IVA 5%
2. Sigue el flujo completo: **Confirmar → Picking → Despachar → Entregar**.
3. Stock final de CT-HUILA-500: 30 - 10 - 15 = **5 unidades**.

---

## FASE 6 — Transferencias y Ajustes de Stock

---

### 6.1 Transferencia entre Bodegas

1. Ve a **Bodega y Despacho → Bodegas** en la barra lateral.
2. Desde la pagina de stock o desde la pagina de bodegas, busca la opcion para **Transferir**.
3. Configura la transferencia:
   - Producto: Cafe Verde Huila
   - Cantidad: **10 kg**
   - Origen: **Bodega Principal**
   - Destino: **Bodega Transito**
4. Inicia la transferencia. Queda en estado "En transito".
5. Luego, completa la transferencia (simula que llego al destino).
6. Verifica:
   - Bodega Principal: 32 - 10 = **22 kg** de Cafe Verde Huila
   - La transferencia queda completada.

---

### 6.2 Registrar Merma (Desperdicio)

1. Desde la pagina de stock o movimientos, busca la opcion para registrar **merma/waste**.
2. Registra:
   - Producto: Cafe Verde Huila
   - Cantidad: **2 kg**
   - Razon: "Cafe danado por humedad en transporte"
   - Bodega: Bodega Principal
3. Verifica: Bodega Principal ahora tiene 22 - 2 = **20 kg** de Cafe Verde Huila.

---

### 6.3 Ajuste de Entrada (Sobrante encontrado)

1. Busca la opcion para hacer un **ajuste de entrada** (adjust-in).
2. Registra:
   - Producto: Bolsa kraft 500g
   - Cantidad: **3 unidades**
   - Razon: "Sobrante encontrado en conteo fisico"
   - Bodega: Bodega Principal
3. Verifica: Bolsas kraft 500g ahora son 170 + 3 = **173 unidades**.

---

## FASE 7 — Conteo Ciclico (Auditoria de Inventario)

El conteo ciclico permite comparar el stock del sistema contra lo que realmente hay en la bodega.

---

### 7.1 Crear un Conteo Ciclico

1. En la barra lateral, dentro del grupo **Bodega y Despacho**, haz click en **Conteo**.
   - Esto te lleva a la pagina **"Conteo Ciclico"** (`/inventario/conteos`).
2. Crea un nuevo conteo:
   - Bodega: **Bodega Principal**
   - Productos: Todos (o selecciona los que quieras contar)
3. Haz click en **"Iniciar"** el conteo.

---

### 7.2 Registrar los Conteos Fisicos

1. Entra al detalle del conteo (`/inventario/conteos/{id}`).
2. Para cada producto, registra la cantidad real que contaste fisicamente:
   - Cafe Verde Huila: el sistema dice **20 kg**, tu contaste **19.5 kg** → registra 19.5
   - Bolsa kraft 500g: el sistema dice **173**, tu contaste **173** → registra 173 (coincide, OK)
   - Bolsa kraft 250g: el sistema dice **300**, tu contaste **298** → registra 298

---

### 7.3 Completar y Aprobar el Conteo

1. Haz click en **"Completar"** el conteo.
2. El sistema muestra las discrepancias:
   - Cafe Verde Huila: -0.5 kg (faltante)
   - Bolsa kraft 250g: -2 unidades (faltante)
3. Haz click en **"Aprobar"**. El sistema genera automaticamente los ajustes de stock.
4. Verifica el IRA (Inventory Record Accuracy) — debe estar cerca del 98-99%.
5. El stock queda corregido:
   - Cafe Verde Huila: **19.5 kg**
   - Bolsa kraft 250g: **298 unidades**

---

## FASE 8 — Alertas, Kardex y Eventos

---

### 8.1 Verificar Alertas de Stock Bajo

1. En la barra lateral, en la parte superior de la seccion Inventario, haz click en **Alertas**.
   - Esto te lleva a la pagina **"Alertas de Stock"** (`/inventario/alertas`).
2. Si configuraste un punto de reorden para CT-HUILA-500 (reorder point = 10 unidades) y el stock actual es 5, deberia aparecer una alerta de stock bajo.
3. Si no ves alertas, haz click en **"Escanear"** (o "Scan") para forzar un escaneo manual.
4. Revisa la alerta: debe indicar que CT-HUILA-500 esta por debajo del minimo.

---

### 8.2 Consultar el Kardex de un Producto

El Kardex es el libro de movimientos de un producto — muestra toda su historia: entradas, salidas, saldos.

1. En la barra lateral, dentro del grupo **Informes**, haz click en **Kardex**.
   - Esto te lleva a la pagina **"Kardex"** (`/inventario/kardex`).
2. Selecciona el producto: **Cafe Verde Huila**.
3. Deberias ver la siguiente historia (cronologica):

   | # | Movimiento | Entrada | Salida | Saldo |
   |---|-----------|---------|--------|-------|
   | 1 | Compra PO-2026-0001 | +50 kg | — | 50 kg |
   | 2 | Emision produccion | — | -18 kg | 32 kg |
   | 3 | Transferencia a Bodega Transito | — | -10 kg | 22 kg |
   | 4 | Merma (humedad) | — | -2 kg | 20 kg |
   | 5 | Ajuste conteo ciclico | — | -0.5 kg | 19.5 kg |

---

### 8.3 Registrar un Evento / Incidente

1. En la barra lateral, dentro del grupo **Informes**, haz click en **Eventos**.
   - Esto te lleva a la pagina **"Eventos"** (`/inventario/eventos`).
2. Antes de crear un evento, necesitas tener configurados los tipos de evento y severidades. Si no lo hiciste:
   - Ve a **Ajustes → Configuracion → Tipos de evento** y crea: "Dano en almacen", "Robo", "Vencimiento"
   - Ve a **Ajustes → Configuracion → Severidades** y crea: "Baja", "Media", "Alta", "Critica"
   - Ve a **Ajustes → Configuracion → Estados de evento** y crea: "Abierto", "En investigacion", "Cerrado"
3. Ahora crea un evento:
   - Tipo: **Dano en almacen**
   - Severidad: **Media**
   - Descripcion: "Goteras en zona A-01 afectaron 2 kg de cafe verde"
4. Agrega un impacto al evento:
   - Producto afectado: Cafe Verde Huila
   - Cantidad afectada: 2 kg

---

## FASE 9 — Reportes y Analitica

---

### 9.1 Revisar el Dashboard

1. En la barra lateral, haz click en **Inicio** (el primer item de la seccion Inventario).
   - Esto te lleva al **"Dashboard de Inventario"** (`/inventario`).
2. Revisa los KPIs que aparecen:
   - Total de SKUs activos (deberia ser 6)
   - Valor total del inventario
   - Alertas activas
   - Graficas de tendencia de movimientos

---

### 9.2 Revisar Rentabilidad (P&L)

1. En la barra lateral, haz click en **Rentabilidad** (segundo item en la parte superior).
   - Esto te lleva a la pagina **"Rentabilidad"** (`/inventario/rentabilidad`).
2. Revisa:
   - Ingresos por ventas (las 2 ordenes de venta)
   - Costos de materia prima (las 2 ordenes de compra)
   - Margen bruto
3. Descarga el reporte en PDF si la opcion esta disponible.

---

### 9.3 Exportar Reportes en CSV

1. En la barra lateral, dentro del grupo **Informes**, haz click en **Reportes**.
   - Esto te lleva a la pagina **"Reportes"** (`/inventario/reportes`).
2. Descarga estos reportes:
   - **Productos** — listado completo de los 6 productos con sus datos.
   - **Movimientos** — filtra por abril 2026 y descarga. Debe incluir todos los movimientos que hicimos.
   - **Ordenes de Compra** — las 2 POs que creamos.
   - **Lotes** — el lote LOT-2026-04-001.

---

### 9.4 Consultar Auditoria

1. En la barra lateral, dentro del grupo **Informes**, haz click en **Auditoria**.
   - Esto te lleva a la pagina **"Auditoria de Inventario"** (`/inventario/auditoria`).
2. Revisa el log de todas las acciones realizadas: creaciones, modificaciones, confirmaciones, etc.

---

## FASE 10 — Auto-Reorder y Verificacion Publica

---

### 10.1 Configurar y Ejecutar Auto-Reorden

1. En la barra lateral, dentro del grupo **Bodega y Despacho**, haz click en **Reorden**.
   - Esto te lleva a la pagina **"Reorden Automatico"** (`/inventario/reorden`).
2. Configura el producto CT-HUILA-500:
   - Punto de reorden: **10 unidades** (cuando el stock baje de 10, disparar alerta/reorden)
   - Cantidad a pedir: **20 unidades**
3. Como el stock actual es **5 unidades** (por debajo de 10), el sistema deberia sugerir crear una orden de compra o marcar el producto como pendiente de reorden.

---

### 10.2 Verificacion Publica de Lote (sin login)

1. Abre una ventana de incognito en el navegador (o un navegador diferente donde NO hayas iniciado sesion).
2. Navega a: **`http://localhost:9003/api/v1/batch/LOT-2026-04-001/verify`**
3. Deberia devolver un JSON con la informacion publica del lote:
   - Producto, fecha de produccion, fecha de vencimiento.
   - Este endpoint es **publico** (no requiere autenticacion) y esta pensado para que el consumidor final pueda verificar la trazabilidad escaneando un codigo QR.

---

## Resumen de Funcionalidades Cubiertas

| # | Modulo | Funcionalidades | Donde se hace |
|---|--------|----------------|---------------|
| 1 | Funcionalidades | Activar/desactivar features | Ajustes → Configuracion → Funcionalidades |
| 2 | UoM | Inicializacion, conversiones | Ajustes → Medidas |
| 3 | Impuestos | Tasas y categorias fiscales | Ajustes → Impuestos |
| 4 | Tipos | Producto, bodega, proveedor, cliente, orden | Ajustes → Configuracion → (cada tarjeta) |
| 5 | Bodegas | CRUD + ubicaciones | Bodega y Despacho → Bodegas |
| 6 | Categorias | Jerarquicas (padre-hijo) | Mis Productos → Categorias |
| 7 | Productos | CRUD con SKU, costos, precios, tipos | Mis Productos → Productos |
| 8 | Variantes | Atributos + opciones + variantes | /inventario/variantes |
| 9 | Proveedores | CRUD con tipos | Compras y Ventas → Socios |
| 10 | Clientes | CRUD con tipos | Compras y Ventas → Socios |
| 11 | Precios por cliente | Descuento % y precio fijo | Compras y Ventas → Precios |
| 12 | Ordenes de compra | Borrador → Enviar → Confirmar → Recibir | Compras y Ventas → Compras |
| 13 | Stock | Recepcion automatica al recibir PO | (automatico) |
| 14 | Produccion | Recetas/BOM + emisiones + recibos | /inventario/recetas y /inventario/produccion |
| 15 | Lotes | Trazabilidad con vencimiento | Bodega y Despacho → Lotes |
| 16 | Ordenes de venta | Borrador → Confirmar → Pick → Despachar → Entregar | Compras y Ventas → Ventas |
| 17 | Reservas de stock | Automaticas al confirmar OV | (automatico al confirmar) |
| 18 | Transferencias | Iniciar → completar entre bodegas | Bodega y Despacho → Bodegas |
| 19 | Ajustes | Merma, entrada, salida | Bodega y Despacho → Movimientos |
| 20 | Conteo ciclico | Crear → contar → completar → aprobar + IRA | Bodega y Despacho → Conteo |
| 21 | Alertas | Stock bajo + scan manual | Alertas (barra lateral superior) |
| 22 | Kardex | Historia completa por producto | Informes → Kardex |
| 23 | Eventos | Incidentes con severidad e impactos | Informes → Eventos |
| 24 | Dashboard | KPIs y graficas | Inicio (barra lateral superior) |
| 25 | Rentabilidad | P&L + PDF | Rentabilidad (barra lateral superior) |
| 26 | Reportes CSV | Productos, stock, movimientos, POs, lotes | Informes → Reportes |
| 27 | Auditoria | Log de acciones | Informes → Auditoria |
| 28 | Auto-reorden | Punto de reorden + sugerencias | Bodega y Despacho → Reorden |
| 29 | Verificacion publica | Lote verificable sin login | URL directa al API |
