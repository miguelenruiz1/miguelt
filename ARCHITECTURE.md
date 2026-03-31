# Trace — Fronteras Canónicas entre Microservicios

Este archivo es la **fuente de verdad** para decidir qué vive en cada servicio.
Cualquier duda futura se resuelve leyendo aquí primero.

---

## Regla fundamental

**inventory-service** responde a la pregunta: **¿QUE tengo, CUANTO vale y CON QUIEN comercio?**
**trace-service** responde a la pregunta: **¿DONDE esta, QUIEN lo tiene y QUE le paso?**

Cuando tengas duda sobre donde va algo, aplica esta regla antes de decidir.

---

## Propiedad de inventory-service

### 1. Maestro de productos
- Toda la entidad Product (SKU, nombre, descripcion, UoM, categorias, imagenes, variantes)
- Atributos comerciales: precio, costo, margenes, impuestos (IVA, retencion)
- Configuracion de reorden: min_stock_level, reorder_point, reorder_quantity, auto_reorder
- Metodos de valorizacion: FIFO, FEFO, LIFO, promedio ponderado
- Recetas / BOM (EntityRecipe, RecipeComponent)
- Tipos de producto configurables por tenant

### 2. Stock y movimientos fisicos
- StockLevel por producto + bodega + ubicacion
- StockMovement: entradas, salidas, ajustes, mermas, traslados internos
- StockReservation: reservas generadas por ordenes de venta confirmadas
- StockLayer: capas de costo para valorizacion
- Kardex (historial valorizado de movimientos)
- Clasificacion ABC de productos por valor/rotacion
- Alertas de stock bajo, sin stock, punto de reorden

### 3. Bodegas y ubicaciones
- Warehouse con tipo, area, costo/m2, capacidad maxima
- WarehouseLocation (ubicaciones internas jerarquicas: pasillo, estante, posicion)
- Conteo ciclico (CycleCount, CycleCountItem, IRASnapshot)
- Scanner de codigos de barras para movimientos rapidos
- Picking fisico de ordenes de venta

### 4. Proveedores y clientes — registro maestro
- BusinessPartner es el registro canonico de toda contraparte comercial
- Supplier (proveedor): lead_time_days, supplier_type, risk_level, payment_terms
- Customer (cliente): credit_limit, default_discount_pct, customer_type
- Historial de precios de compra por proveedor
- Precios especiales por cliente (CustomerPrice)
- Evaluacion y scoring de proveedores

### 5. Ordenes comerciales
- PurchaseOrder (OC): flujo draft->received, aprobaciones, recepcion parcial, consolidacion
- SalesOrder (OV): flujo draft->delivered, aprobaciones por monto, backorders, devoluciones
- Documentos fiscales y comerciales generados DESDE ordenes:
  - Remision (generada al despachar una OV)
  - Nota credito / nota debito (generadas desde una OV)
  - Factura comercial de compra (adjunta a una OC)
  - Packing list (generado desde una OV)
- Portal de autogestion del cliente (/portal/:customerId)

### 6. Produccion
- ProductionRun: ejecucion de recetas, consumo de componentes, generacion de producto terminado
- Aprobacion de corridas de produccion

### 7. Lotes y seriales — registro operativo de inventario
- EntityBatch: numero de lote, cantidad, fechas de fabricacion y vencimiento, costo
- EntitySerial: numero de serie, estado operativo (disponible, vendido, danado, etc.)
- NOTA: inventory-service es dueno del DATO del lote/serial
  trace-service puede REFERENCIAR un batch_id/serial_id para trazabilidad, pero no lo crea

### 8. Configuracion de inventario
- Tipos de producto, proveedor, bodega, movimiento (configurables por tenant)
- Campos personalizados por tipo (CustomProductField, etc.)
- Tasas de impuesto (TaxRate: IVA, retencion, ICA) — seed Colombia
- Unidades de medida y conversiones (UoM) — seed Colombia
- TenantInventoryConfig (umbrales de aprobacion, fulfillment type)

### 9. Analytics de negocio
- Rentabilidad / P&L por producto
- Rotacion por tipo, top 10 por valor, costo de almacenamiento
- Ocupacion de bodegas

---

## Propiedad de trace-service

### 1. Asset trazable
- Asset es una INSTANCIA FISICA de un producto en movimiento o custodia
  (no es el producto en si — el producto vive en inventory-service)
- Asset referencia opcionalmente un entity_id de inventory-service (FK logica, no FK de BD)
- Cada asset tiene: product_type, custodian (wallet), state, historial de eventos
- Minting de cNFT en Solana para activos que requieren trazabilidad blockchain

### 2. Cadena de custodia
- Wallet (Custodian): representa a cualquier actor que puede tener custodia de un asset
  (bodega, transportista, distribuidor, punto de venta, cliente final)
- NOTA: un Wallet puede corresponder a un BusinessPartner de inventory-service
  (FK logica: wallet.partner_id -> inventory.business_partners.id)
  pero Wallet NO duplica los datos comerciales del partner (precio, credito, etc.)
- Custody events: handoff, arrived, loaded, qc, release, burn, y eventos custom
- Timeline de custodia: quien tuvo el asset, cuando y donde

### 3. Workflow de estados configurable por tenant
- WorkflowState: estados personalizados por tenant (no hardcodeados)
- WorkflowTransition: que estado puede ir a que otro
- WorkflowEventType: tipos de evento renombrables por tenant
- Industry presets: logistics, pharma, coldchain, retail, construction
- El kanban/tracking board usa los estados del tenant, no los del sistema

### 4. Organizaciones y taxonomia logistica
- Organization: entidad en la cadena logistica (fabricante, distribuidor, transportista)
  NOTA: Organization NO duplica datos comerciales de BusinessPartner
  Organization modela el ROL logistico; BusinessPartner modela la relacion comercial
  Pueden coexistir con un vinculo opcional (org.partner_id -> inventory.business_partners.id)
- CustodianType: tipos de custodian configurables por tenant

### 5. Documentos de transporte (en transito)
- Shipment: documento que acompana el movimiento fisico de mercancia
  Tipos: remision_transporte, BL, AWB, carta_porte, guia_terrestre
  NOTA: estos son documentos de TRANSITO, no documentos fiscales
  La remision FISCAL vive en inventory-service (generada desde SO)
  El BL/AWB/carta_porte de trace-service son los documentos del transportista/aduana
- Trade documents de comercio exterior:
  cert_origen, fitosanitario, invima, DEX, DIM, insurance_cert
  NOTA: la factura_comercial y el packing_list viven en inventory-service
  trace-service solo tiene los documentos aduaneros y de certificacion

### 6. Compliance y certificacion
- Framework de compliance (EUDR, RSPO, organico, etc.) — completamente en trace-service
- Activaciones por tenant, parcelas, registros, declaraciones
- Certificados de compliance generados y verificables publicamente
- AssetCompliance: vincula un asset con su estado de cumplimiento

### 7. Blockchain y anclaje
- trace-service es el UNICO servicio con worker de anclaje Solana
- inventory-service llama a trace-service via S2S para anclar sus recursos
- El anclaje siempre pasa por trace-service — inventory NO tiene worker blockchain propio
- Endpoint de verificacion publica: /api/v1/public/verify/{hash}
- useSolanaAccount(), useSolanaTx() solo en trace-service

---

## Tabla de documentos

| Documento              | Dueno               | Razon                                              |
|------------------------|---------------------|----------------------------------------------------|
| Remision fiscal        | inventory-service   | Generada desde SO, tiene impuestos, DIAN           |
| Nota credito/debito    | inventory-service   | Derivada de SO, afecta cartera                     |
| Factura comercial      | inventory-service   | Documento de compraventa, vinculada a OC/OV        |
| Packing list           | inventory-service   | Detalle de bultos de una OV                        |
| BL / AWB / carta_porte | trace-service       | Documento del transportista, sigue al asset        |
| Guia terrestre         | trace-service       | Documento de transito fisico                       |
| Cert. de origen        | trace-service       | Documento aduanero, sigue al asset                 |
| Fitosanitario / INVIMA | trace-service       | Certificacion del producto en transito             |
| DEX / DIM              | trace-service       | Declaracion de exportacion/importacion             |
| Insurance cert         | trace-service       | Seguro de carga, sigue al asset en transito        |

---

## Socios comerciales — resolucion definitiva

### inventory-service es dueno de:
- BusinessPartner: el registro maestro comercial (NIT, contacto, terminos de pago, credito)
- SupplierType, CustomerType: clasificacion comercial
- Toda la data financiera: precios, descuentos, limites de credito, historial de compras

### trace-service usa:
- Wallet: representa el rol LOGISTICO de un actor (custodian de assets)
- Organization: representa el rol LOGISTICO en la cadena de suministro
- Wallet y Organization pueden tener un campo partner_id (FK logica a inventory.business_partners)
  para vincular sin duplicar
- Wallet y Organization NUNCA duplican: precio, credito, terminos de pago, NIT fiscal

---

## Lotes y seriales — resolucion definitiva

- inventory-service CREA y ES DUENO de EntityBatch y EntitySerial
- trace-service puede REFERENCIAR batch_id o serial_id en sus eventos de custodia
- Si se necesita trazabilidad de un lote, trace-service llama a inventory-service
  via S2S para obtener los datos del lote (expiry_date, batch_number, etc.)
- trace-service NO crea su propia tabla de lotes

---

## Blockchain — resolucion definitiva

- trace-service es el UNICO servicio con worker de anclaje Solana
- inventory-service expone config de anchor_rules pero trace-service las ejecuta
- inventory-service NO tiene worker blockchain propio
- La verificacion publica es UN SOLO endpoint en trace-service
  inventory-service redirige o referencia ese endpoint

---

## Integraciones S2S requeridas

### Evento: OC recibida en inventory -> trace
```
POST trace-service/api/v1/internal/assets/from-po-receipt
Body: { po_id, entity_id, batch_id?, warehouse_id, tenant_id, quantity }
Resultado: se crea Asset en trace-service con state=in_custody, wallet=bodega_destino
```

### Evento: OV despachada en inventory -> trace
```
POST trace-service/api/v1/internal/assets/handoff-from-so
Body: { so_id, asset_ids[], to_wallet_id, tracking_number, tenant_id }
Resultado: evento handoff en trace-service, asset pasa a in_transit
```

### Evento: Asset anclar desde inventory -> trace
```
POST trace-service/api/v1/anchoring/hash
Body: { resource_type, resource_id, hash, tenant_id }
Resultado: anclaje blockchain, retorna { tx_signature, anchored_at }
```

### Lectura: trace consulta datos de lote -> inventory
```
GET inventory-service/api/v1/internal/batches/{batch_id}
Headers: X-Service-Token, X-Tenant-Id
Resultado: { batch_number, expiry_date, manufacture_date, entity_id, quantity }
```

---

## Duplicaciones a eliminar

### De inventory-service:
- Tabla `anchor_rules` -> mover configuracion a trace-service
- Endpoint `/api/v1/blockchain/anchor` -> reemplazar por call S2S a trace
- TradeDocument tipos: cert_origen, fitosanitario, insurance_cert -> mover a trace-service

### De trace-service:
- factura_comercial y packing_list de trade_documents -> estos viven en inventory
- Datos financieros en Organizations (precio, credito, NIT) -> solo en inventory BusinessPartner
- Logica de reorden y alertas de stock -> solo en inventory

---

## Criterio para nuevas features

Antes de agregar cualquier feature nueva, responde:

1. Afecta QUE tengo o CUANTO vale? -> inventory-service
2. Afecta DONDE esta o QUIEN lo tiene? -> trace-service
3. Genera un documento FISCAL (con impuestos, DIAN)? -> inventory-service
4. Genera un documento de TRANSITO (sigue al asset fisico)? -> trace-service
5. Es data COMERCIAL (precio, credito, NIT)? -> inventory-service
6. Es data LOGISTICA (estado, ubicacion, evento de custodia)? -> trace-service
7. Necesita blockchain? -> la logica va en trace-service, inventory solo llama S2S
