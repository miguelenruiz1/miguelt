# Journey completo Trace — Cacao Colombia → UE (EUDR)

**Objetivo:** demoear end-to-end Trace para la reu con el especialista BID-cacao del 29/04/2026. Cubre marketplace → cumplimiento (parcela + screening satelital) → inventario (productor, producto, compra, lote) → producción (transformación opcional cacao → cacao seco fermentado) → logística (mint NFT + cadena de custodia) → venta → DDS EUDR firmado → certificado público QR.

Cada paso trae: **ruta URL**, **acción exacta**, **campos con los valores a poner en la demo**, y **qué verificar antes de seguir**. Los labels están copiados tal cual del código — si no coinciden con lo que ves en pantalla, avisame.

**Datos del caso (coherentes, usarlos siempre):**

| Campo | Valor demo |
|---|---|
| Tenant | `default` |
| Usuario | `miguelenruiz1@gmail.com` / `Pitch2026-Uniandes!` |
| Cooperativa proveedor | `Asocacao del Catatumbo` |
| Productor | `Fabián Moreno Ortiz` — CC `88123456` |
| Finca | `La Esperanza` — Teorama, Norte de Santander |
| Área parcela | `3.2 ha` |
| Coordenada centroide | `8.4387, -73.2891` |
| Lote cacao | `CACAO-NS-2026-001` — 500 kg cacao seco fermentado |
| Custodios logísticos | Finca / Camión Asocacao / Bodega Cartagena / Operador Aduana |
| Cliente UE | `Luker Chocolate Zwolle B.V.` — Países Bajos |
| HS Code | `1801.00.00` (cacao en grano) |

---

## 0. Pre-requisitos (una sola vez antes de arrancar la demo)

- Todos los servicios corriendo: `docker compose ps` → trace-api, inventory-api, user-api, subscription-api, compliance-api, gateway.
- Estar logueado con **miguelenruiz1@gmail.com** (es admin + superuser → ve Plataforma).
- Si la sesión no está: ir a `/login`, meter credenciales.
- Verificar que `HELIUS_API_KEY` está seteado en `trace-api` (ya lo está — `docker exec trace-api env | grep HELIUS`) → así los mints salen a **Solana devnet real**, no simulación.

---

## 1. Activar módulos en Marketplace

**Por qué:** las secciones "Inventario", "Producción", "Cumplimiento" del sidebar solo aparecen si el módulo está activo para el tenant. Si ya están activos, saltar este paso.

**Ruta:** `/marketplace`

**Acción:**
1. Sidebar → "Marketplace" (primer ítem top).
2. En el grid de módulos, dejar **ACTIVOS** (toggle a la derecha):
   - `logistics` — Logística
   - `inventory` — Inventario
   - `production` — Producción
   - `compliance` — Cumplimiento

**Verificar:** el sidebar muestra secciones **Logística, Inventario, Producción, Cumplimiento** colapsables. Si no aparecen → F5 (el hook `useIsModuleActive` cachea 5min).

> Si se abre popup `"¡Módulo habilitado!"` con botón `Completar suscripción`, cerrarlo con `Hacerlo después` — no hace falta pasar por checkout para la demo.

---

## 2. Activar la norma EUDR para cacao

**Ruta:** `/cumplimiento/frameworks`

**Acción:**
1. Sidebar → sección **Cumplimiento** → "Marcos Normativos".
2. Encontrar la tarjeta **EUDR** (Reglamento 2023/1115 UE).
3. Si dice `Activo` → ya está. Si no → click en **"Activar"**.
4. Ir a `/cumplimiento/activaciones` ("Mis Normas" en el sidebar).
5. En la fila `EUDR`, click **ícono lápiz** → se abre modal **"Editar destinos de exportacion"**.
6. Campo `Destinos de exportacion (separados por coma)` → poner: `EU`
7. Click **"Guardar"**.

**Verificar:** la fila EUDR en "Mis Normas" muestra `Destinos: EU` y estado `Activo`.

---

## 3. Configurar la integración GFW (Global Forest Watch)

**Ruta:** `/cumplimiento/integraciones`

**Por qué:** el screening satelital multi-fuente (GFW Alerts + Hansen + JRC) necesita la API key de GFW. Sin esto el screening devuelve `{not_configured: true}` y la parcela no puede marcarse deforestation-free.

**Acción:**
1. Sidebar → Cumplimiento → **"Integraciones"**.
2. En la card GFW → pegar la API key → Guardar.

**Verificar:** badge "Conectada" en verde. Si no tenés la key a mano, lo podés saltear — el screening devolverá "no configurado" pero el flujo sigue (solo que el flag `deforestation_free` queda en null y el DDS quedará con warning).

---

## 4. Crear organizaciones (custodios)

**Ruta:** `/organizations`

**Acción:** crear **4 organizaciones**, una por cada custodio de la cadena.

Para cada una:
1. Click botón **"+ Nueva Organización"** (arriba a la derecha).
2. Se abre modal **"Nueva Organización"**:
   - `Nombre *` →  ver tabla abajo
   - `Tipo de custodio *` → ver tabla abajo
   - `Descripción (opcional)` → lo que quieras
3. Click **"Crear"**.

| Org a crear | Tipo | Rol en el journey |
|---|---|---|
| Asocacao del Catatumbo | `farm` | Productor / cooperativa origen |
| Transportes Asocacao | `truck` | Transporte Catatumbo → Cartagena |
| Bodega Cartagena Export | `warehouse` | Consolidación en puerto |
| DIAN Aduana Cartagena | `customs` | Operador aduanero de salida |

**Verificar:** grid de `/organizations` muestra 4 cards, cada una con su badge de tipo.

---

## 5. Crear una wallet custodio para cada organización

**Ruta:** `/organizations/:id` (click sobre la card de cada org)

**Por qué:** cada evento de custodia on-chain se firma desde/hacia una wallet Solana. Necesitamos una wallet activa por custodio.

**Acción (repetir para las 4 orgs):**
1. Click card de la organización → va a `/organizations/:id`.
2. Tab **"Wallets"**.
3. Click **"+ Nueva Wallet"** → se abre modal **"Crear Wallet de Custodio"**.
4. Campos:
   - `Nombre de Wallet` → ej: `Wallet Asocacao Catatumbo`
   - `Organización` → la actual (preseleccionada)
   - `Etiquetas Adicionales` → `cacao, origen` (o `transporte`, `bodega`, `aduana` según)
   - `Estado Inicial` → `Activa`
5. Click **"Crear Wallet"**.

**Verificar:** aparece la wallet listada con su pubkey (formato `Abc123...XYZ`). En devnet se hace auto-airdrop de 0.1 SOL.

> Tip para el pitch: en `/wallets` se ven las 4 wallets. Mostrar que cada custodio tiene identidad criptográfica propia — **no hay wallet compartida**.

---

## 6. Registrar la parcela de producción + screening satelital

**Ruta:** `/cumplimiento/parcelas`

**Acción:**
1. Sidebar → Cumplimiento → **"Parcelas"**.
2. Click botón **"Nueva Parcela"** → va a `/cumplimiento/parcelas/nueva` (página completa, no modal).
3. Llenar el form **"Registrar Parcela"**:

**Sección PRODUCTOR:**
- `Nombre completo del productor *` → `Fabián Moreno Ortiz`
- `Tipo doc *` → `CC`
- `Numero *` → `88123456`
- `Cooperativa / asociacion / organizacion` → `Asocacao del Catatumbo`
- `Escala del productor *` → `Pequeño productor`

**Sección FINCA / PARCELA:**
- `Nombre de la finca *` → `La Esperanza`
- `Area total del lote (hectareas)` → `3.2`

**Sección UBICACIÓN:**
- `Departamento *` → `Norte de Santander`
- `Municipio *` → `Teorama`
- `Vereda` → `El Aserrío`
- `Frontera agricola (UPRA / CIPRA)` → `Dentro — sin condicionamiento`

**Sección GEOLOCALIZACIÓN:**
- Radio → `Punto GPS` (más simple para demo; el polígono se puede agregar después).
- `Latitud` → `8.4387`
- `Longitud` → `-73.2891`
- `Metodo de captura` → `GPS de mano / celular`
- `Fecha de captura` → hoy
- `Exactitud GPS (metros)` → `5`

**Sección CULTIVO:**
- `Cultivo principal *` → `Cacao`
- `Nombre cientifico` → (se autocompleta `Theobroma cacao`)
- `Fecha de siembra` → `2018-05-01`
- `Ultima cosecha` → `2026-03-15`

**Sección TENENCIA:**
- `Tipo de tenencia` → `Propietario`
- `Cedula catastral (IGAC)` → `54-800-00-00-0000-0123-000` (ejemplo)

**Sección DECLARACIONES EUDR:**
- ✅ Marcar checkbox `Libre de deforestacion (Art. 3.a)`
- ✅ Marcar checkbox `Libre de degradacion forestal (Art. 2.7)`

4. Click **"Crear parcela"** (botón sticky del footer).

**Verificar:** redirige a `/cumplimiento/parcelas`, se ve una fila nueva con badge commodity `Cacao` y badge `Punto` (geolocalización).

---

### 6.b Ejecutar screening satelital multi-fuente

1. En la fila de la parcela, click **ícono satélite** (el botón Satellite a la derecha).
2. Toast esperado: `"La Esperanza: Libre de deforestacion (0 alertas)"` → endpoint real `/api/v1/compliance/plots/{id}/screen-deforestation` contra GFW.
3. Click sobre el código de la parcela → `/cumplimiento/parcelas/:plotId`.
4. Bajar hasta la sección **"Screening Multi-Fuente EUDR"**.
5. Correr también el endpoint full: ejecutar `screen-deforestation-full` (si la UI tiene botón para ello) o desde la misma fila vía otro click satélite extendido — verifica contra **JRC 2020, GFW Alerts, Hansen/UMD** a la vez.

**Verificar:** badges verdes para `Libre de deforestacion`, `Sin degradacion`, `Cumple fecha de corte`, `Uso legal del suelo`. El campo `satellite_verified_at` queda con timestamp.

> **Línea para el pitch:** *"Esta parcela acaba de ser validada contra tres datasets satelitales independientes — JRC del Joint Research Centre europeo, GFW del World Resources Institute, y Hansen/UMD. Las tres dieron cero alertas post-diciembre 2020, que es el cutoff EUDR. El timestamp de la validación queda anclado al predio."*

---

## 7. Crear el proveedor en Inventario

**Ruta:** `/inventario/socios`

**Por qué:** para emitir Orden de Compra al productor hay que tenerlo como Socio comercial con rol `Proveedor`.

**Acción:**
1. Sidebar → Inventario → **Compras y Ventas** → **"Socios"**.
2. Click **"Nuevo socio"** → modal `Nuevo socio comercial`.
3. Campos clave:
   - `Nombre *` → `Asocacao del Catatumbo`
   - `Código *` → `ASOC-NS-001`
   - `Tipo documento` → `NIT`
   - `NIT/Nº Documento *` → `900123456`
   - `DV` → `7`
   - Checkbox **"Es proveedor"** → ✅
   - `Nombre contacto` → `Fabián Moreno`
   - `Email` → `asocacao@demo.trace.co`
   - `Teléfono` → `+57 310 555 0123`
   - `Plazo pago (días)` → `30`
   - `Ciudad *` → `Teorama`
   - `Depto/Estado` → `Norte de Santander`
   - `País` → `CO`
4. Click **"Guardar"**.

**Verificar:** aparece en la tab `Proveedores` con estado `Activo`.

> Repetir el mismo paso para crear el **Cliente UE** (paso 13), pero con checkbox "Es cliente" y país `NL`.

---

## 8. Crear bodega de origen (si no existe)

**Ruta:** `/inventario/bodegas`

**Acción:**
1. Sidebar → Inventario → **Bodega y Despacho** → **"Bodegas"**.
2. Si ya existe `MAIN` (bodega principal), saltar. Si no, click **"Nueva bodega"**:
   - `Nombre *` → `Bodega Finca La Esperanza`
   - `Código *` → `FLA-001`
   - `Tipo de bodega` → seleccionar el que aplique (ej: `Secondary`)
   - `Ciudad/Municipio` → `Teorama`
   - `País (ISO 2)` → `CO`
   - ✅ `Activa`
3. Click **"Guardar"**.

---

## 9. Crear el producto "Cacao seco fermentado"

**Ruta:** `/inventario/productos`

**Acción:**
1. Sidebar → Inventario → **Mis Productos** → **"Productos"**.
2. Click **"+ Nuevo producto"**.
3. Campos:
   - `Nombre *` → `Cacao seco fermentado — grano premium`
   - `SKU *` → `CACAO-SF-PREM`
   - `Categoría` → `Agrícola` (o la que exista)
   - `Unidad base` → `kg`
   - `Tipo de producto` → `Materia prima` o el que aplique
   - `Código HS` → `1801.00.00`
   - `Costo estándar` → `14000` (COP/kg referencia)
   - `Precio venta` → `22000`
4. Guardar.

**Verificar:** aparece en `/inventario/productos` con SKU `CACAO-SF-PREM`, stock 0.

---

## 10. Crear Orden de Compra al productor

**Ruta:** `/inventario/compras`

**Acción:**
1. Sidebar → Inventario → **Compras y Ventas** → **"Compras"**.
2. Click **"Nueva OC"** → modal `Nueva Orden de Compra`.
3. Campos:
   - `Proveedor *` → `Asocacao del Catatumbo`
   - `Bodega destino *` → `Bodega Finca La Esperanza` (o MAIN)
   - `Fecha esperada` → hoy + 2 días
   - `Notas` → `Compra cacao seco fermentado cosecha 2026-Q1 — finca La Esperanza (plot code XYZ)`
   - Línea:
     - `Producto` → `Cacao seco fermentado — grano premium`
     - `Cantidad` → `500`
     - `Costo` → `14000`
4. Click **"Guardar"** → queda en estado `Borrador`.
5. Entrar a la OC (click en el número, ej. `OC-2026-001`) → botón **"Enviar al proveedor"**.
6. Luego → **"Confirmar recepción proveedor"**.
7. Luego → **"Recibir mercancía"**. En el modal:
   - Productos a recibir → `500 kg` (todo)
   - `N° Factura` → `FV-ASOC-2026-0042`
   - `Fecha factura` → hoy
   - `Total factura` → `7000000`
   - `Términos de pago` → `30 días`
   - Opcional: **"Adjuntar documento"** (subir imagen/PDF de la factura si tenés)
8. Click **"Confirmar recepción"**.

**Verificar:**
- OC pasa a estado `Recibida`.
- Stock del producto sube a 500 kg en la bodega.
- En `/inventario/movimientos` aparece una fila tipo **"Entrada"** con cantidad 500.

---

## 11. Crear lote trazable del producto recibido

**Ruta:** `/inventario/lotes`

**Por qué:** el lote es el anclaje único de trazabilidad. EUDR exige poder rastrear por lote, no por producto genérico.

**Acción:**
1. Sidebar → Inventario → **Bodega y Despacho** → **"Lotes"**.
2. Click **"Nuevo lote"** → modal `Nuevo Lote`.
3. Campos:
   - `Producto *` → `Cacao seco fermentado — grano premium`
   - `Número de lote *` → `CACAO-NS-2026-001`
   - `Cantidad *` → `500`
   - `Costo` → `14000`
   - `Fabricación` → hoy (o fecha cosecha)
   - `Expiración` → hoy + 18 meses
   - ✅ `Activo`
4. Guardar.

**Verificar:** fila `CACAO-NS-2026-001` visible en `/inventario/lotes`.

---

## 12. (Opcional — solo si querés mostrar producción) Transformación con receta

**Por qué:** si el caso de demo es "exportamos cacao en grano" no hace falta. Si querés demoear el módulo Producción también, haz una receta simple **Cacao húmedo → Cacao seco fermentado** con merma 40% (así sale bonito el data).

**Rutas:** `/produccion/recetas` → `/produccion/ordenes` → `/produccion/mrp`.

**Flujo corto:**
1. `/produccion/recetas` → **"+ Nueva receta"**:
   - `Nombre *` → `Fermentación + secado cacao`
   - `Producto de salida *` → `Cacao seco fermentado — grano premium`
   - `Cantidad salida *` → `60` (kg)
   - `Tipo BOM` → `Produccion`
   - Componentes → **"+ Agregar"** → (requiere crear un producto "Cacao en baba / húmedo" antes) — cantidad `100 kg` por cada 60 de salida (merma 40%).
2. `/produccion/ordenes` → **"+ Nueva orden"** → elegir la receta, bodega, multiplicador `8.33` (para 500 kg salida) → **"Crear"**.
3. Estados: `Planificada` → **"Liberar"** → `Liberada` → **"Emitir componentes"** → **"Recibir producto"** → **"Cerrar orden"**.
4. `/produccion/mrp` → botón **"Explotar BOM"** para mostrar la gráfica de sugerencias de compra si faltan componentes.

**Verificar:** en la orden de producción, tab **"Recibos"**, se registró entrada del producto final. El movimiento aparece en `/inventario/movimientos` como tipo `Producción`.

---

## 13. Crear el cliente UE y la Orden de Venta

**Ruta:** `/inventario/socios` → **"Nuevo socio"** (como paso 7 pero cliente).

- `Nombre *` → `Luker Chocolate Zwolle B.V.`
- `Código *` → `LUKER-NL-001`
- `Tipo documento` → `NIT` (o "Otro" si el dropdown lo tiene)
- `NIT/Nº Documento *` → `NL860123456B01` (VAT EU)
- ✅ Checkbox `Es cliente`
- `Ciudad *` → `Zwolle`
- `País` → `NL`
- Guardar.

**Luego crear la Orden de Venta:**

**Ruta:** `/inventario/ventas`

1. Sidebar → Inventario → **Compras y Ventas** → **"Ventas"**.
2. Click **"Nueva Orden"** → modal `Nueva Orden de Venta`.
3. Campos:
   - `Cliente *` → `Luker Chocolate Zwolle B.V.`
   - `Fecha esperada` → hoy + 30 días
   - `Forma de pago` → `Crédito`
   - `Medio de pago` → `Consignación`
   - `Commodity` → `Cacao`
   - `Moneda` → `USD`
   - `Incoterm` → `CIF`
   - `País destino` → `NL`
   - Línea:
     - `Producto` → `Cacao seco fermentado — grano premium`
     - `Bodega` → Bodega Finca La Esperanza
     - `Cantidad` → `500`
     - `Precio` → `5.50` (USD/kg)
4. Guardar → estado `Borrador`.
5. Abrir la OV → **"Confirmar"** → **"Picking"** → **"Enviar"** → **"Entregar"**.

**Verificar:** stock baja a 0, en `/inventario/movimientos` aparece salida de 500 kg.

---

## 14. Mintear el lote en Solana como cNFT + custodia real

**Ruta:** `/assets`

**Por qué:** acá es donde el pitch se vuelve **visualmente fuerte** — el lote se convierte en NFT on-chain con historial inmutable.

**Acción:**
1. Sidebar → Logística → **"Cargas"**.
2. Click botón **"Registrar Carga"** (el primario con Sparkles) → modal **"Registrar nueva carga"**.
3. Campos:
   - `Tipo de producto *` → chip **`Cacao`**
   - `Nombre de la carga` → `Cacao Catatumbo — Lote CACAO-NS-2026-001`
   - `Organización / Finca` → `Asocacao del Catatumbo`
   - `Wallet custodio inicial *` → `Wallet Asocacao Catatumbo`
   - `Parcela de origen (opcional)` → `La Esperanza` ← **importante, esto vincula el NFT a la parcela validada**
   - `Peso / Cantidad` → `500`
   - `Unidad` → `kg`
   - `Calidad / Grado` → `Grano premium fermentado — humedad 7%`
   - `Origen` → `Teorama, Norte de Santander, Colombia`
   - `Descripción` → `Lote CACAO-NS-2026-001 — cosecha 2026-Q1 — destino Luker Chocolate NL`
4. Click **"Registrar Carga"**.

**Verificar:**
- Toast éxito.
- Se ve la carga en la tabla con:
  - Estado `in_custody`
  - Blockchain dot **verde "Confirmado"** (Helius respondió OK).
- Click sobre la carga → `/assets/:id`:
  - Sección Blockchain → link **"Ver transaccion en Solana Explorer"** → abre Solscan devnet con la tx real.
  - Link **"Ver NFT en XRAY"** → muestra el cNFT con imagen y metadata.
  - Campo `Ultimo hash` visible → es el hash encadenado del primer evento `CREATED`.

> **Línea de pitch:** *"En este momento el lote existe como un NFT compresso en Solana mainnet-beta — el `mint address` es inmutable, firmado con la wallet de Asocacao del Catatumbo. Nadie, ni siquiera nosotros, puede reescribir ese evento."*

---

## 15. Cadena de custodia — eventos on-chain

**Ruta:** `/assets/:id` (el detail de la carga recién minteada)

**Por qué:** cada transferencia física queda como evento firmado y encadenado por hash.

**Acción:** simular la ruta real **Finca → Camión → Bodega Cartagena → Aduana → Envío UE**. Para cada evento, ir al card lateral **"Siguiente paso"** y click en el botón propuesto por el workflow (se va habilitando según el estado).

### 15.1 HANDOFF: Finca → Camión Asocacao

1. Click botón **"Entregar"** (o el label literal de handoff que muestra la UI) en card "Siguiente paso".
2. Se abre modal de workflow event:
   - `Nuevo custodio *` → `Wallet Transportes Asocacao`
   - `Ubicación` → `Vereda El Aserrío, Teorama`
   - `Notas` → `Carga entregada a camión placa TSA-123`
3. Click **"Confirmar"**.

**Verificar:** estado pasa a `in_transit`. Hash del evento queda anclado a `prev_event_hash` del CREATED.

### 15.2 ARRIVED: llegada a Bodega Cartagena

1. Botón **"Marcar llegada"** (o equivalente `arrived`).
2. Modal:
   - `Ubicación` → `Bodega Cartagena Export — Muelle 3`
   - `Notas` → `Arrival inspection OK`
3. **"Confirmar"**.

### 15.3 HANDOFF: Camión → Bodega Cartagena

1. Botón **"Entregar"**.
2. `Nuevo custodio *` → `Wallet Bodega Cartagena Export`.
3. **"Confirmar"**.

### 15.4 LOADED: consolidación en contenedor

1. Botón **"Cargar"** (loaded).
2. `Ubicación` → `Contenedor MSCU-1234567, precinto 00123`.
3. **"Confirmar"**.

### 15.5 QC: control de calidad previo embarque

1. Botón **"Control de Calidad"**.
2. Modal:
   - `Resultado *` → **`Aprobado (Pass)`**
   - `Notas` → `Humedad 7.1%, sin granos rotos, fermentación OK`
3. **"Confirmar"**.

### 15.6 HANDOFF: Bodega → Aduana

1. Botón **"Entregar"**.
2. `Nuevo custodio *` → `Wallet DIAN Aduana Cartagena`.
3. **"Confirmar"**.

### 15.7 RELEASED: liberación al buque

1. Botón **"Liberar"** (released — estado terminal).
2. `Ubicación` → `Puerto Cartagena — Buque MSC Ariane → Rotterdam`.
3. **"Confirmar"**.

**Verificar — esto es lo más importante del pitch:**
- En `/assets/:id`, sección **"Historial de Movimientos"** aparecen **7 eventos** en orden cronológico: `CREATED → HANDOFF → ARRIVED → HANDOFF → LOADED → QC_PASSED → HANDOFF → RELEASED`.
- Cada evento tiene su propio hash + prev_hash (chain-of-custody criptográfica).
- Cada evento que requirió cambio de wallet está firmado por el custodio correspondiente.
- Estado final `released` (terminal).

> **Línea de pitch:** *"Cada transferencia quedó firmada por el custodio que tenía la posesión física en ese momento. No es un log editable — es una cadena criptográfica. Si mañana alguien quisiera decir 'ese cacao pasó por otra parcela', el hash del CREATED no coincidiría. La única forma de cambiar la historia es mintear otro lote."*

**También ver:**
- Ruta `/tracking` → Panel de Seguimiento → el lote fue apareciendo en cada columna del kanban a medida que cambiaba de estado.

---

## 16. Crear el Registro de Cumplimiento EUDR y vincular parcela

**Ruta:** desde el asset detail `/assets/:id`, bajar a sección **"Cumplimiento Normativo"** → click **"Crear registro EUDR"**.

O manualmente:

**Ruta:** `/cumplimiento/registros`

1. Click **"Nuevo Registro"** → modal `Nuevo Registro de Cumplimiento`.
2. Campos:
   - `Carga *` → `Cacao Catatumbo — Lote CACAO-NS-2026-001` (la que acabamos de mintear)
   - `Framework *` → `EUDR`
   - `Commodity` → `Cacao`
   - `Cantidad (kg)` → `500`
   - `Pais de produccion` → `CO`
3. Click **"Crear registro"** → redirige a `/cumplimiento/registros/:id`.

### 16.b Llenar el detalle del registro

En `/cumplimiento/registros/:id`:

**Tab `Producto`:**
- `Codigo HS` → `1801.00.00`
- `Commodity` → `Cacao`
- `Descripcion del producto` → `Cacao seco fermentado, grano entero premium, humedad <8%`
- `Nombre cientifico` → `Theobroma cacao`
- `Cantidad` / `Unidad` → `500` / `kg`
- `Pais de produccion` → `CO`
- Periodo → `2026-01-01` a hoy
- `Proveedor` → Asocacao del Catatumbo / email / dirección
- `Comprador` → Luker Chocolate Zwolle B.V. / email / Países Bajos
- `EORI del operador` → `NL860123456B01`
- `Tipo de actividad` → `Exportacion`
- Firma: `Nombre del firmante` → `Miguel Ruiz`, `Cargo` → `CEO Trace`, `Fecha` → hoy.
- ✅ `Declaracion libre de deforestacion`
- ✅ `Declaracion de cumplimiento legal`
- **"Guardar cambios"**.

**Card Cacao (🧪 Test de Cadmio):**
- `Valor mg/kg *` → `0.28`
- `Fecha *` → hoy
- `Laboratorio` → `Lab AnalizaQuim Bogotá — Res. ONAC 20-LAB-035`
- Click **"Registrar resultado"**.
- Verifica badge verde: `EU compliant ≤ 0.60 mg/kg`.

**Tab `Parcelas`:**
1. Click **"Vincular Parcela"**.
2. Modal:
   - `Parcela *` → `La Esperanza` (Fabián Moreno Ortiz)
   - `Cantidad (kg)` → `500`
   - `Porcentaje (%)` → `100`
3. Click **"Vincular"**.
4. Verificar: aparece la parcela listada con badges verdes `DF / Legal / Cutoff`.

**Tab `Cadena`:** aparece automáticamente la cadena de custodia del asset vinculado — los 7 eventos.

**Tab `Documentos`:** subir (opcional para demo) factura, certificado cadmio, póliza transporte.

**Tab `Validacion`:**
- Click **"Validar ahora"**.
- Resultado esperado: **"Registro valido"** (sin campos faltantes, sin advertencias).

---

## 17. Emitir el DDS EUDR y enviarlo a TRACES NT

**Ruta:** mismo `/cumplimiento/registros/:id`, tab **`DDS`**.

**Acción:**
1. Campos:
   - `Referencia de declaracion` → `DDS-2026-0001`
   - `Fecha de envio` → hoy
   - `Estado de la declaracion` → `Listo para enviar`
2. Click **"Guardar declaracion"**.
3. Sección **TRACES NT — Sistema de Informacion UE**:
   - Click **"Exportar DDS (JSON)"** → descarga el archivo EUDR XML/JSON según especificación (Anexo II).
   - Click **"Enviar a TRACES NT"** → llama al endpoint real TRACES si las credenciales están configuradas; si no, queda en estado `Draft/Listo` con el JSON listo.
4. Estado badge pasa a `Enviada (en validacion)` → `Aceptada` (si TRACES responde OK).
5. Click **"Ver certificado DDS"** cuando esté aceptada.

**Verificar:**
- El JSON descargado contiene: referencia, EORI, geometryGeojson (en base64), declaraciones, firma.
- Badge en Estado pasa de Borrador a Aceptada.

---

## 18. Generar el Certificado EUDR firmado con QR

**Ruta:** mismo registro, tab **`Certificado`**.

**Acción:**
1. Si no existe certificado → click **"Generar Certificado"**.
2. Se genera PDF con:
   - Número de certificado
   - QR que apunta a `/verificar/:batchNumber` (público, sin auth)
   - cNFT + TX de Solana embebidos (anclaje on-chain del certificado)
3. Click **"Descargar PDF"** → tenerlo abierto.
4. Click **"Copiar URL de verificacion"**.

---

## 19. Verificación pública (como si fuera el comprador UE)

**Ruta:** `/verificar/CACAO-NS-2026-001` (pública, sin login)

**Acción:**
1. Abrir **en ventana incógnita** (para mostrar que no requiere auth).
2. Se ve:
   - Nombre del lote, productor, finca, cooperativa.
   - Mapa con el punto GPS de la parcela.
   - Badges DF / Legal / Cutoff en verde.
   - Cadena de custodia completa con 7 eventos y enlaces a Solscan.
   - Link al certificado PDF firmado.
   - Test de cadmio: 0.28 mg/kg ✓ EU compliant.

> **Línea de pitch — la más fuerte:** *"Un comprador en Zwolle, Países Bajos, escanea este QR desde su celular, sin registrarse, sin descargar nada. Ve en tiempo real la parcela de origen validada por satélite contra EUDR, los 7 custodios que tocaron el lote con sus firmas en blockchain, el test de cadmio bajo el límite UE, y el DDS aceptado por TRACES NT. Todo verificable independientemente — no tiene que confiar en nosotros, tiene que confiar en Solana y GFW."*

---

## 20. Rentabilidad con IA (cierre)

**Ruta:** `/inventario/rentabilidad`

**Acción:**
1. Sidebar → Inventario → **"Rentabilidad"** (ítem top).
2. Preset rango fechas → `Mes`.
3. Ver KPIs: **Ingresos** (USD 2,750), **Costo** (COP 7M → ~USD 1,800), **Utilidad**, **Margen**.
4. Sección **"Análisis IA"** (Powered by Claude Haiku):
   - Si sale `"API key de Anthropic no configurada"` (es lo que mostró hoy), el CEO superuser la configura desde `/platform/ai` antes del 29.
   - Si está configurada → muestra 5 secciones: Resumen, Alertas, Oportunidades, Productos Estrella, Recomendaciones.

**Verificar:** el análisis menciona el producto `Cacao seco fermentado — grano premium` y referencia el precio de venta.

---

## Orden del pitch en vivo (versión 8 minutos)

Si tenés que demoear **todo** en 8 min de ventana, hacé este orden (no el orden completo de arriba):

1. (30s) Landing `/eudr` + explicar problema EUDR Colombia cacao.
2. (1m) Paso 6: **parcela con screening satelital en vivo** — es el wow #1.
3. (1m) Paso 14: **mint del lote** — el Solscan en vivo es el wow #2.
4. (2m) Paso 15 rápido: recorrer los 7 eventos de custodia en el tracking board.
5. (2m) Paso 16–17: llenar el registro EUDR y mostrar el DDS JSON generado.
6. (1m) Paso 19: abrir `/verificar/...` en incógnito. **Ese es el cierre**.
7. (30s) Mencionar rentabilidad IA como extensión de valor.

---

## Anexo A — qué probar antes de la reu del 29

Una pasada completa con datos reales (no los seed que vienen por defecto), desde `/login` hasta `/verificar/...`. Si algo rompe:

- **AI rentabilidad 501** → configurar Anthropic API key en `/platform/ai` (superuser).
- **Mint 502 Bad Gateway** → `docker compose restart gateway` (nginx cachea IP del upstream).
- **Login 429** → borrar rate limit: `docker exec trace-redis redis-cli -n 2 DEL rl:login:<ip>`.
- **Screening no configured** → agregar GFW API key en `/cumplimiento/integraciones`.
- **Mint 422 product_type faltante** → el modal debe tener chip `Cacao` seleccionado antes de submit.

---

## Anexo B — preguntas que va a hacer el especialista BID (preparar respuestas)

1. **"¿Cuánto le cuesta al cacaotero de Teorama?"** → modelo pensado: SaaS por tonelada trazada (USD 0.05–0.10/kg de cacao certificado EUDR), o freemium donde paga el exportador/cooperativa, no el productor.
2. **"¿Cómo lo usa sin internet en la finca?"** → la app PWA funciona offline, sincroniza cuando vuelve señal. El mint se difiere; el hash local del evento se firma apenas hay internet.
3. **"¿Quién asume el fee de Solana?"** → cNFT (compressed NFT) → **~USD 0.00005 por mint** gracias a state compression. Lo paga la plataforma.
4. **"¿Piloto con qué cooperativa?"** → hoy: en conversación con X (hay que tener uno mínimo en curso para el 29).
5. **"¿Cómo se integra con Aurelia/SIPSA/otros sistemas agrícolas?"** → endpoints REST + webhooks EUDR-compliant; TRACES NT ya integrado.

---

Listo. Este documento está pensado para **ejecutarlo con el navegador abierto al lado** y seguirlo clic por clic. Si algún label literal no coincide con lo que ves, decime cuál y lo corrijo en este archivo — es frecuente que el copy cambie entre deploys.
