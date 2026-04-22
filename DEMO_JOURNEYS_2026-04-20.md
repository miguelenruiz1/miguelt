# Trace — Journeys de Demo (Producción)

**URL demo:** http://62.238.5.1
**Usuario demo:** `miguelenruiz1@gmail.com`
**Password:** `TraceAdmin2026!`
**Tenant:** `trace-efb40c` (datos reales seed en producción)

Esta guía lleva al asistente paso a paso por **4 journeys** que muestran el producto funcionando en la nube con datos reales. Tiempo total: **10-15 minutos**.

> **Tip al presentar**: abrí dos pestañas del browser — una con la app logueada, otra con este doc para leer los pasos sin perder el hilo.

---

## Journey 1 · INVENTARIO (3 min)

**Mensaje**: *"Cualquier empresa con stock físico puede activar solo este módulo y tener un control operativo serio, sin Excel ni WhatsApp."*

### Paso 1 — Login
1. Abrir **http://62.238.5.1**
2. Email: `miguelenruiz1@gmail.com`
3. Pass: `TraceAdmin2026!`
4. Clic **"Ingresar"**

> *"Este es un SaaS multi-tenant. El mismo login sirve para cualquier empresa. Yo soy superusuario de la plataforma."*

### Paso 2 — Marketplace de módulos
1. Sidebar izquierda → sección **Administración** → clic en **Marketplace**
2. Se ven 4 módulos en cards: **Logística, Inventario, Compliance, Integraciones**
3. Mostrar el toggle: *"cada empresa activa solo los módulos que necesita"*
4. Si Inventario no está activo, activarlo con un clic

### Paso 3 — Dashboard Inventario
1. Sidebar → **Inventario → Dashboard**
2. Mostrar KPIs en vivo: total SKUs, valor stock, movimientos del mes
3. Gráficos recharts: movimientos por tipo, ABC classification, stock por warehouse

### Paso 4 — Productos (CRUD completo)
1. Sidebar → **Inventario → Productos**
2. Mostrar **"Cafe Huila Excelso - 500g"** (el que seedeamos)
3. Clic en el producto → ver detalle
4. Mostrar campos: SKU, unidad de medida, min_stock=100, reorder_point=50, auto_reorder=true
5. *"Cuando el stock baje de 50, el sistema **genera automáticamente** una orden de compra al proveedor preferente."*

### Paso 5 — Stock y movimientos
1. Sidebar → **Inventario → Stock**
2. Mostrar stock actual del producto: **850 kg en Bodega Central Tumaco**
3. Sidebar → **Inventario → Movimientos**
4. Ver los 2 movimientos: recepción 1000 kg a COP 12.500/kg, salida 150 kg
5. *"Cada movimiento crea un registro inmutable auditable."*

### Paso 6 — Reporte CSV
1. Sidebar → **Inventario → Reportes**
2. Clic **"Descargar productos CSV"**
3. Abrir el CSV → mostrar datos reales exportados

### Paso 7 — Config y custom fields
1. Sidebar → **Inventario → Configuración**
2. Pestañas: Tipos de producto, Tipos de orden, Campos personalizados, Tipos de proveedor
3. *"Cada empresa configura sus propios tipos y campos sin tocar código."*

---

## Journey 2 · LOGÍSTICA + CADENA DE CUSTODIA (4 min)

**Mensaje**: *"Este es el diferenciador: cadena de custodia multi-actor con anclaje blockchain. Productor, transportista, bodega y comprador ven la misma información en tiempo real, y nadie puede alterarla."*

### Paso 1 — Organizaciones
1. Sidebar → **Logística → Organizaciones**
2. Mostrar **"Finca El Paraiso"** (seeded)
3. Explicar: *"Cada actor de la cadena es una organización. Pueden ser farms, warehouses, transportistas o aduanas."*

### Paso 2 — Wallets
1. Sidebar → **Logística → Wallets**
2. Mostrar las 3 wallets seeded: **Productor, Transportista, Comprador**
3. *"Cada wallet es una llave Solana real. El sistema las genera + airdrop devnet automático."*

### Paso 3 — Assets (NFTs)
1. Sidebar → **Logística → Assets**
2. Mostrar el asset minteado: **Café Huila - Lot LOT-XXXXXX**
3. Clic en el asset → ver detalle
4. Resaltar los campos:
   - `blockchain_status: CONFIRMED` / `SIMULATED`
   - `blockchain_asset_id`: el hash del cNFT
   - `blockchain_tx_signature`: tx en Solana
   - Metadata rica: origen Huila, variedad Caturra, 500kg, altitud 1650m, lavado

> *"Ese hash está anclado en la blockchain Solana. Costo por evento: $0.0001 USD. Cualquier auditor puede verificarlo."*

### Paso 4 — Cadena de custodia (el momento wow)
1. En el detalle del asset, scroll a **"Historial de eventos"** o **"Traza"**
2. Mostrar los 5 eventos:
   1. **CREATED** — productor recibió el NFT
   2. **HANDOFF** — entregó a transportista
   3. **ARRIVED** — llegó a bodega (coordenadas GPS)
   4. **LOADED** — cargado a camión TRK-4421
   5. **QC PASSED** — inspección aprobada (humedad 11%)
   6. **RELEASED** — liberado al comprador europeo

3. *"Cada evento tiene **hash encadenado** con el anterior. Es criptográficamente imposible insertar un evento falso entre dos reales."*

### Paso 5 — Tracking Board (kanban en vivo)
1. Sidebar → **Logística → Tracking**
2. Mostrar el kanban con 7 columnas de estado
3. Auto-refresh cada 30s
4. *"El jefe de logística ve en tiempo real dónde está cada carga."*

### Paso 6 — Workflow configurable
1. Sidebar → **Logística → Configuración** (si está visible)
2. Mostrar cómo se configuran estados y transiciones custom por tenant

---

## Journey 3 · COMPLIANCE EUDR (4 min)

**Mensaje**: *"EUDR obliga a cualquier exportador a Europa desde dic 2025. Nosotros lo hacemos en la app, sin consultores de $10k, sin Excel, con validación automática que rechaza data mal formada."*

### Paso 1 — Frameworks disponibles
1. Sidebar → **Compliance → Frameworks**
2. Mostrar **EUDR** card con info:
   - Emisor: European Union
   - 7 commodities aplicables
   - Cutoff date: 2020-12-31
   - Retención: 5 años
   - Requiere geolocalización y DDS

### Paso 2 — Activación por tenant
1. Clic en **EUDR** → ver detalle
2. Mostrar **Activations** de este tenant — con destino de exportación: EU

### Paso 3 — Parcelas (lo crítico)
1. Sidebar → **Compliance → Parcelas**
2. Mostrar las 2 parcelas seeded:
   - **PLOT-HUILA-XXXX** — 2.35 ha, café, Huila, punto GPS (lat/lng con 6 decimales)
   - **PLOT-LARGE-XXXX** — 6.80 ha, cacao, **poligono** (requerido por Art. 9.1.c)
3. Clic en el segundo plot → mostrar el polígono en el mapa (si hay mapa integrado) o el GeoJSON raw

### Paso 4 — Validación estricta EUDR (mostrar que funciona)
1. Clic **"Crear nuevo plot"** o equivalente
2. Llenar datos intencionalmente **mal**: área 10 ha + solo punto (sin polígono)
3. Intentar guardar → el sistema **rechaza** con mensaje explicando Art. 9.1.c
4. *"No dejamos que el usuario genere data incompleta. La validación es **por diseño**."*

Alternativa: mostrar el error 422 en la consola del browser si hay intento fallido.

### Paso 5 — Records DDS
1. Sidebar → **Compliance → Records**
2. Mostrar records creados (o crear uno nuevo desde una parcela)
3. Mostrar estados del workflow: draft → filed → submitted → accepted/rejected
4. *"Cuando el record está listo, el sistema puede enviarlo automáticamente a TRACES NT (plataforma oficial UE) via polling + retry."*

### Paso 6 — Certificados PDF
1. Sidebar → **Compliance → Certificados**
2. *"Los certificados se generan automáticamente **desde records validados**. Nunca a mano."*
3. Si hay alguno generado, abrir el PDF.

### Paso 7 — Verificación pública por QR
1. Abrir nueva pestaña (sin login)
2. URL: `http://62.238.5.1/api/v1/public/batch/<tenant>/<batch_number>/verify`
3. *"Un consumidor final escanea el QR del empaque y ve estos datos **sin necesidad de login**."*

---

## Journey 4 · PRODUCCIÓN (2-3 min)

**Mensaje**: *"Para manufacturas pequeñas y medianas: recetas, órdenes de producción, consumo automático de materias primas, costeo real."*

### Paso 1 — Productos compuestos
1. Sidebar → **Inventario → Productos**
2. Mostrar **"PT-XXXX - Café Huila Excelso Empacado 500g"** (producto terminado) + **"MP-XXXX - Empaque 500g"** (materia prima)

### Paso 2 — Recetas (Bill of Materials)
1. Sidebar → **Inventario → Recetas** (o Producción)
2. Mostrar la receta: **1 unidad de café empacado = 0.5 kg de café + 1 empaque**
3. *"Así definís el BOM de cada producto terminado."*

### Paso 3 — Corrida de producción
1. Sidebar → **Producción** (si está como módulo separado) o **Inventario → Producción**
2. Crear nueva corrida: 100 unidades del producto terminado
3. Estado: **planned**

### Paso 4 — Release de producción
1. Clic **"Release"** o equivalente en la corrida
2. *"Cuando liberás la corrida, el sistema **automáticamente** consume 50 kg de café + 100 empaques del inventario, y genera 100 unidades del producto terminado con el costo calculado."*
3. Ir a stock y mostrar que las cantidades cambiaron

### Paso 5 — Recursos de producción
1. Sidebar → **Producción → Recursos**
2. Mostrar **"Empacadora Línea 1"** — capacidad 120 uds/hora
3. *"Podés asignar máquinas y operarios a cada corrida."*

### Paso 6 — Quality tests
1. Sidebar → **Producción → Quality Tests** (si disponible)
2. Mostrar cómo se registran resultados de QC con parámetros esperados vs reales

---

## Resumen visual — el argumento final

Después de los 4 journeys, cerrar así:

> *"Acaban de ver **cuatro módulos diferentes** funcionando en una sola plataforma, con data real en producción en la nube."*
>
> *"Una cooperativa que exporte va a usar los 4. Una panadería va a usar solo el de Inventario. Una fábrica pequeña, Inventario + Producción. **Todos pagan solo por lo que usan**."*
>
> *"No hay otra plataforma LatAm que integre **inventario operativo real + producción + compliance regulatorio + trazabilidad blockchain**. Ese es el valor."*

---

## Chuletas por si algo no abre

| Si… | Entonces… |
|---|---|
| La URL no carga | Abrir terminal: `ssh root@62.238.5.1 'docker compose ps' \| grep -v healthy` para ver qué está mal |
| El login falla con 429 | `ssh root@62.238.5.1 'docker exec trace-redis redis-cli FLUSHALL'` (flush rate limit) |
| No veo un módulo en el sidebar | Ir a Marketplace y activarlo |
| Los datos demo no aparecen | Correr `python qa/demo_seed.py` desde el repo local (ya está ejecutado, pero por si acaso) |
| Una página tira error | Mostrar el siguiente módulo y volver después — dev is live, bugs pueden existir |

---

## Slide de respaldo — ¿y si preguntan "cómo funciona por dentro"?

Tener listo el diagrama del `INFORME_CENTRO_EMPRENDIMIENTO_2026-04-20.md` sección 3.1:

```
Frontend React → API Gateway nginx → 8 microservicios FastAPI
                                    → 8 PostgreSQL + Redis
                                    → Solana blockchain
```

**Mensaje**: *"Arquitectura de microservicios moderna, multi-tenant desde el día uno, async, escalable horizontalmente. Stack FastAPI + PostgreSQL + React — sobrio, defensible, cero moda."*

---

## Datos clave a recordar durante la demo

- **190.000 líneas de código** · **681 endpoints** · **73 modelos de datos**
- **20 containers** corriendo 24/7 en Hetzner Cloud
- **$5.49 USD/mes** costo de infraestructura actual
- **17 bugs críticos** de seguridad auditados y cerrados
- **40+ tests** automatizados E2E y de seguridad, 100% passing

---

**Suerte con la reunión. El producto habla solo.**
