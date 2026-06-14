# Trace — Journeys de usuario avanzados (2026-06-13)

> Recorridos end-to-end **multi-módulo** que muestran el valor real de la
> plataforma. Estado post-eliminación de EUDR: la trazabilidad ya no depende de
> un módulo de cumplimiento — es trazabilidad blockchain genérica, útil para
> cualquier mercado.
>
> Cada journey indica: **actor**, **objetivo**, **pasos** (con pantalla / módulo /
> endpoint), **datos** y **resultado verificable**.

---

## Journey 1 — Trazabilidad de exportación finca → puerto con anclaje blockchain

**Actor:** Operador logístico de una exportadora de café.
**Objetivo:** Que un comprador internacional verifique, sin login, toda la cadena
de custodia de un lote anclada en Solana.

1. **Alta de custodios** (`/wallets`, módulo Logística): el operador registra o
   genera wallets para cada actor de la cadena — finca, transportadora, bodega,
   agente de aduana. Cada wallet entra al allowlist (`POST /api/v1/registry/wallets`).
2. **Alta de organizaciones** (`/organizations`): crea la finca de origen y la
   vincula a su wallet.
3. **Crear la carga** (`/assets` → "Nueva carga"): registra el lote (producto,
   cantidad/peso, grado, origen, custodio inicial). El asset nace en
   `IN_CUSTODY`; el anclaje blockchain es fire-and-forget (`POST /api/v1/assets/mint`).
4. **Registrar la cadena de eventos** (`/assets/:id` → "Agregar evento"): a medida
   que el lote se mueve, se registran eventos respetando la state machine:
   `HANDOFF` (finca→transportadora) → `LOADED` → `DEPARTED`/`IN_TRANSIT` →
   `ARRIVED` (bodega) → `QC` (calidad) → `GATE_IN`/`GATE_OUT` (puerto) →
   `CUSTOMS_HOLD`/`CUSTOMS_CLEARED` → `RELEASED`. Cada evento puede pedir
   documentos según su tipo (QC pide fotos, etc.).
5. **Anclaje on-chain:** el worker ARQ ancla los hashes de eventos en Solana
   (Memo + cNFT comprimido vía Helius). El estado pasa a `anchored`/`minted`.
6. **PDF + QR** (`/assets/:id` → "Descargar PDF de trazabilidad"):
   `generateTraceabilityPDF` produce el reporte con narrativa, tabla técnica
   (hashes + anclaje), datos de blockchain y un **QR** al verificador público.
7. **Verificación del comprador** (`/verificar/:batch`, **sin login**): escanea el
   QR, ve la proof-chain con links a Solscan y los hashes; puede recalcular SHA-256
   para detectar manipulación.

**Resultado:** trazabilidad finca→puerto inmutable y verificable por un tercero
sin cuenta, anclada en Solana real.

---

## Journey 2 — De materia prima a producto terminado (compra → producción → venta)

**Actor:** Jefe de planta de una empresa de alimentos (módulos Inventario +
Producción activos).
**Objetivo:** Convertir insumos en producto terminado con costeo correcto y stock
consistente.

1. **Comprar insumos** (`/inventario/compras`): crea una OC al proveedor, la envía
   y la **recibe** por líneas → genera `StockMovement` tipo `purchase`, sube
   `qty_on_hand` y actualiza el costo (promedio ponderado / FIFO según el producto).
2. **Definir la receta (BOM)** (`/produccion/recetas`): producto de salida +
   componentes de entrada con cantidades. Soporta multi-salida (ej. RFF → CPO + PKO)
   con costo compartido.
3. **Crear orden de producción** (`/produccion/ordenes`): vincula la receta y una
   bodega, define cantidad objetivo.
4. **Emisiones** (`/produccion/emisiones`): consume el stock de insumos
   (`production_out`) según la BOM.
5. **Recibos** (`/produccion/recibos`): ingresa el producto terminado
   (`production_in`) con el costo layered de los insumos consumidos.
6. **Lotes y vencimiento** (`/inventario/lotes`, feature `lotes`): el producto
   terminado se registra con `batch_number` y `expiry_date`; un scan diario crea
   **alertas** de vencimiento (`/inventario/alertas`).
7. **Vender** (`/inventario/ventas`): SO al cliente → picking → ship → descuenta
   stock por FIFO de lote (fecha de cosecha/vencimiento).

**Resultado:** trazabilidad insumo→producto con costo real y stock por lote,
listo para vender y (opcionalmente) anclar la carga en Logística.

---

## Journey 3 — Consolidación de órdenes de compra

**Actor:** Comprador que maneja muchas OC chicas al mismo proveedor.
**Objetivo:** Reducir fletes/costos juntando varias OC en un solo envío.

1. **Detectar candidatas** (`/inventario/compras`): el sistema busca OC del mismo
   proveedor en estado consolidable.
2. **Consolidar** (acción "Consolidar"): fusiona N OC en una sola orden al
   proveedor (`is_consolidated`, `consolidated_from_ids` guardan el origen).
3. **Aprobación** (`/inventario/aprobaciones`, feature `aprobaciones`): si la OC
   consolidada supera el umbral, requiere aprobación (`approved_by`/`rejected_by`).
4. **Recepción única:** se recibe la OC consolidada en una sola entrada; el stock
   se reparte a los productos originales.

**Resultado:** menos envíos, trazabilidad de qué OC originales componen la
consolidada, y control por aprobación.

---

## Journey 4 — Onboarding de un nuevo tenant SaaS

**Actor:** Admin de una empresa que se suscribe a Trace.
**Objetivo:** Dejar el tenant operativo con los módulos correctos y el equipo.

1. **Registro** (`/register`): el primer usuario del tenant se crea y obtiene
   automáticamente el rol `administrador` (user-service).
2. **Onboarding FSM** (`/onboarding`): welcome → profile → modules → done.
3. **Suscripción** (`/empresa/suscripcion`): elige plan; el plan define límites
   (usuarios/assets) y módulos permitidos.
4. **Activar módulos** (`/marketplace`): togglea `logistics`, `inventory`,
   `production`, `electronic-invoicing`, `ai-analysis` (con dependencias: e-invoice
   y production requieren inventory). Esto invalida el cache de módulos en cada
   servicio consumidor.
5. **Crear roles y permisos** (`/equipo/roles`): matriz estilo Drupal; asigna
   permisos por módulo (`inventory.manage`, `admin.users`, etc.).
6. **Invitar al equipo** (`/equipo/usuarios`): crea usuarios con rol; reciben
   invitación por correo (provider configurado en `/empresa/correo`).

**Resultado:** tenant aislado, con módulos pagos activos, roles definidos y equipo
invitado; el sidebar de cada usuario muestra solo lo que su rol + módulos permiten.

---

## Journey 5 — Portal de clientes + verificación pública de lote (B2B self-service)

**Actor:** Cliente B2B de un tenant; y un consumidor final.
**Objetivo:** Que el cliente gestione sus pedidos solo, y que cualquiera verifique
el origen de un lote.

1. **Crear portal** (`/inventario/portal`): el tenant habilita un portal por
   cliente (acceso protegido).
2. **Self-service del cliente** (`/inventario/portal/:customerId`): ve sus órdenes
   abiertas, hace tracking de envíos y descarga facturas — sin tocar el back-office.
3. **Precios por cliente** (`/inventario/precios-clientes`, feature `precios`):
   overrides de precio por volumen/tier aplicados a ese cliente.
4. **Verificación pública del lote** (`/verificar/:batch`, **sin login**): el
   consumidor final escanea el QR del empaque → ve producto, SKU, lote, estado de
   vencimiento (Vigente/Pronto/Vencido), origen y la **proof-chain** anclada
   on-chain con links a Solscan (`/api/v1/public-verify`).

**Resultado:** menos carga operativa (el cliente se autogestiona) y confianza al
consumidor con verificación blockchain pública.

---

## Journey 6 — Facturación electrónica DIAN (venta → factura legal)

**Actor:** Facturador (módulos Inventario + Facturación Electrónica activos).
**Objetivo:** Emitir una factura electrónica válida ante la DIAN desde una venta.

1. **Configurar resolución** (`/facturacion-electronica/resolucion`, permiso
   `integrations.manage`): registra la resolución DIAN (prefijo, rango, vigencia)
   en integration-service (`InvoiceResolution`, numeración auto-incremental).
2. **Venta** (`/inventario/ventas`): confirma una SO.
3. **Emitir e-factura** (`/facturacion-electronica`): genera la factura vía
   proveedor **MATIAS/DIAN** (integration-service). subscription-service guarda
   `cufe`, `einvoice_number`, `einvoice_pdf_url`, `einvoice_status`.
4. **Descargar/enviar:** PDF legal con CUFE; el cliente lo ve en su portal.

**Resultado:** factura electrónica legal con CUFE, numerada según resolución DIAN,
trazada a la venta original.

---

## Journey 7 — Análisis de rentabilidad con IA

**Actor:** Gerente con plan que incluye `ai-analysis`.
**Objetivo:** Entender márgenes y recibir recomendaciones accionables.

1. **Datos de P&L** (`/inventario/rentabilidad`): inventory-service arma el P&L por
   SKU/categoría/proveedor (costeo + ventas).
2. **Análisis IA** (`POST /api/v1/analyze/pnl`): ai-service llama a Claude (Haiku
   para rutina, Sonnet para premium) con el P&L + contexto de negocio.
3. **Límites y cache:** el servicio respeta el límite diario por plan y cachea el
   resultado (Redis, TTL configurable); `force=true` lo recalcula.
4. **Insights:** alertas de margen, productos de baja rotación, oportunidades.

**Resultado:** lectura ejecutiva del negocio con recomendaciones, con costo de IA
controlado por plan y tracking de gasto mensual.

---

## Journey 8 — Conteo cíclico, ajuste y auditoría

**Actor:** Responsable de bodega + auditor.
**Objetivo:** Mantener el stock exacto y dejar rastro de cada ajuste.

1. **Crear conteo** (`/inventario/conteos`, feature `conteo`): elige metodología
   (ABC, grupo de control, ubicación, aleatorio…).
2. **Contar:** registra cantidades reales; el sistema calcula varianzas vs.
   `qty_on_hand`.
3. **Aprobar varianza:** al aprobar, genera `StockMovement` de ajuste
   (`adjustment_in`/`adjustment_out`).
4. **Kardex** (`/inventario/kardex`, feature `kardex`): el libro mayor perpetuo
   refleja el ajuste con saldo corriente.
5. **Auditoría** (`/inventario/auditoria` o `/equipo/auditoria`): cada movimiento
   queda logueado con usuario, IP, timestamp y old/new data.

**Resultado:** inventario reconciliado con trazabilidad completa de quién ajustó
qué, cuándo y por qué.

---

## Combinando módulos — el "journey maestro"

El mayor valor aparece al encadenar: **comprar** insumos → **producir** producto
terminado (con costo y lote) → **registrar la carga** en Logística y anclar su
cadena de custodia en Solana → **vender** y emitir **e-factura** DIAN → el cliente
hace **tracking** desde su portal y el consumidor final **verifica** el origen por
QR sin login → el gerente cierra el ciclo con **análisis de rentabilidad IA**.
Todo dentro de un mismo tenant, con permisos por rol y módulos activados a demanda.
