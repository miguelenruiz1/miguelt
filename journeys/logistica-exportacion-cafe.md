# Journey: Exportacion de Cafe Colombiano a Europa con Compliance EUDR

Flujo completo de exportacion internacional con documentos de comercio exterior, cadena de frio, trazabilidad blockchain y cumplimiento de la norma EUDR (European Union Deforestation Regulation).

**Contexto del negocio:**
- Cooperativa cafetera en Huila, Colombia
- Exporta cafe especial a Hamburgo, Alemania
- El cliente europeo exige cumplimiento EUDR (trazabilidad desde la finca hasta el puerto destino)
- Transporte multimodal: terrestre (finca→puerto) + maritimo (Buenaventura→Hamburgo)

**Prerequisitos:**
- Frontend corriendo en `http://localhost:3000`
- trace-service corriendo en `http://localhost:8000`
- Base de datos limpia con tenant `default`
- Blockchain configurado (Helius + SOL en fee payer)

---

## Paso 1 — Configurar Workflow

**Ruta:** `/configuracion/flujo-de-trabajo`

1. Tab **Plantillas de industria** → click **"Aplicar plantilla"** en **logistics**
2. Verificar en tab **Estados** — 6 estados:

| # | Color | Estado | Tipo |
|---|---|---|---|
| 1 | Cyan | Recibido | Inicial |
| 2 | Morado | En bodega | |
| 3 | Amarillo | En transito | |
| 4 | Azul | En reparto | |
| 5 | Verde | Entregado | |
| 6 | Naranja | Devuelto | |

3. Verificar tab **Transiciones** — 7 transiciones incluyendo devoluciones
4. Verificar tab **Tipos de evento** — 7 tipos incluyendo DEVOLUCION

---

## Paso 2 — Crear Tipos de Custodio

**Ruta:** `/organizations` → **"Gestionar tipos de custodio"**

| Nombre | Slug | Color | Icono |
|---|---|---|---|
| Finca | finca | verde | sprout |
| Cooperativa | cooperativa | morado | building-2 |
| Transportista | transportista | amarillo | truck |
| Puerto | puerto | azul | ship |
| Agente Aduanero | agente_aduanero | naranja | shield |
| Importador | importador | cyan | globe |

---

## Paso 3 — Crear Organizaciones

**Ruta:** `/organizations` → **"Nueva Organizacion"**

| Nombre | Tipo | Descripcion |
|---|---|---|
| Finca La Esperanza | Finca | Finca cafetera en Pitalito, Huila. 12 hectareas, cafe arablca lavado |
| Cooperativa CafeHuila | Cooperativa | Centro de acopio y beneficio. Certif. Rainforest Alliance |
| TransAndina Cargo | Transportista | Transporte refrigerado Huila-Buenaventura |
| Puerto de Buenaventura | Puerto | Terminal maritima del Pacifico colombiano |
| Agencia Aduanera GlobalTrade | Agente Aduanero | Agente de aduanas para exportacion |
| Hamburg Coffee Imports GmbH | Importador | Importador y tostador aleman |

---

## Paso 4 — Crear Wallets

**Ruta:** `/wallets` → **"Crear Wallet"**

Crear 6 wallets:

| Nombre | Organizacion | Etiquetas |
|---|---|---|
| Finca La Esperanza | Finca La Esperanza | finca, huila, origen |
| Bodega CafeHuila | Cooperativa CafeHuila | cooperativa, acopio, beneficio |
| Camion Refrigerado TA-01 | TransAndina Cargo | transporte, refrigerado, ruta-huila-bv |
| Terminal Buenaventura | Puerto de Buenaventura | puerto, maritimo, exportacion |
| Agente GlobalTrade | Agencia Aduanera GlobalTrade | aduana, exportacion, comex |
| Hamburg Coffee Imports | Hamburg Coffee Imports GmbH | importador, destino, europa |

---

## Paso 5 — Registrar la Carga de Cafe

**Ruta:** `/assets` → **"Registrar Carga"**

| Campo | Valor |
|---|---|
| Tipo de producto | Click **cafe** (icono taza) |
| Nombre de la carga | Lote HLA-2026-0089 — Cafe Especial Huila 84pts |
| Organizacion | Finca La Esperanza |
| Wallet custodio | Finca La Esperanza |
| Peso | 18000 |
| Unidad | kg |
| Calidad | SHG EP — Sccore 84, Taza limpia, notas citricos y caramelo |
| Origen | Pitalito, Huila, Colombia |
| Descripcion | 300 sacos de 60kg. Cafe arabica lavado, secado en camas elevadas. Cosecha marzo 2026. Parcela El Mirador, altitud 1750 msnm |

**Verificar:**
- Blockchain Status: **CONFIRMED** (cNFT real en Solana devnet)
- Estado: recibido (estado inicial del preset logistics)
- 1 evento CREATED en la cadena de custodia

---

## Paso 6 — Transferir a la Cooperativa (Centro de Acopio)

**En detalle del asset** → **"Transferir Custodia"**

| Campo | Valor |
|---|---|
| Custodio destino | Bodega CafeHuila |
| Ubicacion | Centro de Acopio CafeHuila, Pitalito |
| Notas | Recepcion de 300 sacos. Muestra retenida para cupping. Humedad: 11.2% |

**Verificar:** custodio cambio a Bodega CafeHuila, 2 eventos en cadena.

---

## Paso 7 — Control de Calidad (Cupping)

**En detalle del asset** → **"Control de Calidad"**

| Campo | Valor |
|---|---|
| Resultado | Aprobado (pass) |
| Notas | Cupping score: 84 pts. Fragancia 8/10, Acidez 8.5/10, Cuerpo 7.5/10. Aprobado por Q-Grader Juan Mendez. Sin defectos. Apto para exportacion especialidad |

**Verificar:** estado cambia a qc_passed, 3 eventos.

---

## Paso 8 — Crear Documentos de Comercio Exterior

**Ruta:** `/logistica/documentos-comex` → **"Nuevo Documento"**

### Documento 1: Certificado de Origen

| Campo | Valor |
|---|---|
| Tipo | Certificado de Origen |
| Numero | CO-2026-HLA-0089 |
| Titulo | Certificado de Origen — Cafe Arabica Lavado Colombia |
| Autoridad Emisora | Camara de Comercio del Huila |
| Pais Emisor | COL |
| Codigo Arancelario | 0901.11.90 |
| Valor FOB | 86400.00 |
| Valor CIF | 94200.00 |
| Moneda | USD |
| Descripcion | 300 sacos x 60kg de cafe verde arabica lavado. Origen: Pitalito, Huila. Partida arancelaria 0901.11.90. Acogido al TLC Colombia-Union Europea |

Click **"Crear"** → Luego click **"Aprobar"** en la tabla

### Documento 2: Certificado Fitosanitario

| Campo | Valor |
|---|---|
| Tipo | Fitosanitario |
| Numero | ICA-FIT-2026-034521 |
| Titulo | Certificado Fitosanitario de Exportacion |
| Autoridad Emisora | ICA - Instituto Colombiano Agropecuario |
| Pais Emisor | COL |
| Codigo Arancelario | 0901.11.90 |
| Descripcion | Inspeccion fitosanitaria aprobada. Lote libre de broca (Hypothenemus hampei), roya (Hemileia vastatrix) y CBD. Cumple requisitos fitosanitarios de la Union Europea (Directiva 2000/29/CE) |

Click **"Crear"** → **"Aprobar"**

### Documento 3: DEX (Declaracion de Exportacion)

| Campo | Valor |
|---|---|
| Tipo | DEX |
| Numero | DEX-2026-BUN-001247 |
| Titulo | Declaracion de Exportacion — Cafe Verde |
| Autoridad Emisora | DIAN Colombia |
| Pais Emisor | COL |
| Codigo Arancelario | 0901.11.90 |
| Valor FOB | 86400.00 |
| Moneda | USD |
| Descripcion | Exportacion definitiva. Regimen: 10. Aduana: Buenaventura. Destino: Hamburgo, Alemania. Incoterm: FOB Buenaventura. 300 bultos, 18000 kg neto |

Click **"Crear"** → **"Aprobar"**

**Verificar:** 3 documentos en tabla, todos con estado "Aprobado" (verde).

---

## Paso 9 — Despacho Terrestre (Huila → Buenaventura)

### 9a. Crear Documento de Transporte Terrestre

**Ruta:** `/logistica/envios` → **"Nuevo Documento"**

| Campo | Valor |
|---|---|
| Tipo | Guia Terrestre |
| Numero | GT-TA-2026-00234 |
| Transportista | TransAndina Cargo |
| Placa | XYZ-789 |
| Ciudad Origen | Pitalito, Huila |
| Ciudad Destino | Buenaventura, Valle del Cauca |
| Paquetes | 300 |
| Peso (kg) | 18000 |
| Tracking # | TA-TRACK-00234 |

Click **"Crear"** → **"Emitir"** → **"En Transito"**

### 9b. Transferir Custodia al Transportista

**Ruta:** Detalle del asset → **"Transferir Custodia"**

| Campo | Valor |
|---|---|
| Custodio destino | Camion Refrigerado TA-01 |
| Ubicacion | Bodega CafeHuila, Muelle de carga |
| Notas | Despacho terrestre refrigerado a 18C. Tiempo estimado: 14 horas. Guia GT-TA-2026-00234 |

---

## Paso 10 — Llegada al Puerto

### 10a. Registrar Llegada

**En detalle del asset** → **"Registrar Llegada"**

| Campo | Valor |
|---|---|
| Ubicacion | Puerto de Buenaventura, Terminal de Contenedores, Bodega 7 |
| Notas | Llegada sin novedad. Temperatura mantenida a 18C durante transito. 300 sacos verificados |

### 10b. Transferir al Agente Aduanero

**"Transferir Custodia"**

| Campo | Valor |
|---|---|
| Custodio destino | Agente GlobalTrade |
| Ubicacion | Puerto de Buenaventura, Zona Primaria |
| Notas | Entrega a agente aduanero para tramite de exportacion. DEX-2026-BUN-001247 |

---

## Paso 11 — Crear Documento de Transporte Maritimo

**Ruta:** `/logistica/envios` → **"Nuevo Documento"**

| Campo | Valor |
|---|---|
| Tipo | Bill of Lading |
| Numero | MAEU-BUN-HAM-2026-00891 |
| Transportista | Maersk Line |
| Ciudad Origen | Buenaventura |
| Ciudad Destino | Hamburg |
| Buque | Maersk Seletar |
| Contenedor | MSKU-7234561 |
| Paquetes | 300 |
| Peso (kg) | 18000 |
| Tracking # | MAEU-2026-00891 |

Click **"Crear"** → **"Emitir"** → **"En Transito"**

---

## Paso 12 — Despacho Maritimo (Embarque)

**Detalle del asset** → **"Transferir Custodia"**

| Campo | Valor |
|---|---|
| Custodio destino | Terminal Buenaventura |
| Ubicacion | Puerto Buenaventura, Muelle 5, Contenedor MSKU-7234561 |
| Notas | Carga embarcada en M/V Maersk Seletar. BL: MAEU-BUN-HAM-2026-00891. ETD: 2026-04-05. ETA Hamburg: 2026-05-02 |

**Verificar:** cadena de custodia muestra todo el recorrido hasta ahora.

---

## Paso 13 — Llegada a Destino (Hamburg)

Cuando la carga llega a Hamburgo (28 dias despues):

### 13a. Registrar Llegada

**"Registrar Llegada"**

| Campo | Valor |
|---|---|
| Ubicacion | Port of Hamburg, Container Terminal Altenwerder |
| Notas | Arribo M/V Maersk Seletar. Contenedor MSKU-7234561 descargado sin novedad. Sellos intactos |

### 13b. Transferir al Importador

**"Transferir Custodia"**

| Campo | Valor |
|---|---|
| Custodio destino | Hamburg Coffee Imports |
| Ubicacion | Hamburg Coffee Imports Warehouse, Speicherstadt |
| Notas | Entrega al importador final. 300 sacos verificados, peso conforme. BL entregado |

---

## Paso 14 — Completar Entrega

**"Completar Entrega"**

| Campo | Valor |
|---|---|
| Observaciones | Exportacion completada exitosamente. 300 sacos (18,000 kg) de cafe arabica lavado entregados a Hamburg Coffee Imports GmbH en Speicherstadt, Hamburgo. Todos los documentos de comercio exterior aprobados. Cadena de custodia certificada en blockchain Solana. Cumplimiento EUDR verificable. |

**Verificar:**
- Cuadro cyan: "Entrega completada"
- Cadena de custodia completa con ~10 eventos
- Cada evento anclado en Solana

---

## Paso 15 — Verificar Cadena Completa

**En detalle del asset**, la cadena de custodia debe mostrar:

```
BURN (Entrega completada)         ← Hamburg Coffee Imports
HANDOFF                           ← Terminal Buenaventura → Hamburg Coffee Imports
ARRIVED                           ← Port of Hamburg
HANDOFF                           ← Agente GlobalTrade → Terminal Buenaventura
HANDOFF                           ← Camion Refrigerado TA-01 → Agente GlobalTrade
ARRIVED                           ← Puerto de Buenaventura
HANDOFF                           ← Bodega CafeHuila → Camion Refrigerado TA-01
QC (Aprobado)                     ← Bodega CafeHuila
HANDOFF                           ← Finca La Esperanza → Bodega CafeHuila
CREATED                           ← Finca La Esperanza
```

Cada evento tiene:
- Hash SHA-256 encadenado al anterior
- Timestamp inmutable
- Wallets from/to
- Anclado en Solana (check verde)

---

## Paso 16 — Verificar en Solana Explorer

Click **"Ver en Solana Explorer"** → debe abrir la transaccion real en devnet.

Click **"Certificado PDF"** → descarga el certificado de trazabilidad completo.

---

## Paso 17 — Documentos de Transporte Completados

**Ruta:** `/logistica/envios`

Cambiar estados finales:
- Guia Terrestre GT-TA-2026-00234 → **"Entregado"**
- Bill of Lading MAEU-BUN-HAM-2026-00891 → **"Entregado"**

---

## Como cumple esto con la norma EUDR

La **EUDR** (Reglamento UE 2023/1115) exige que los importadores europeos demuestren que los productos no provienen de tierras deforestadas despues de diciembre 2020. Para cumplir, necesitan:

| Requisito EUDR | Como lo cumple Trace |
|---|---|
| **Geolocalizacion de la parcela** | Metadata del asset: origen = "Pitalito, Huila" + coordenadas en location de eventos |
| **Fecha de produccion** | Evento CREATED con timestamp inmutable, anclado en blockchain |
| **Cadena de custodia completa** | 10 eventos desde finca hasta importador, cada uno con hash encadenado |
| **Verificacion independiente** | Endpoint publico POST /anchoring/verify — cualquiera puede verificar sin login |
| **Inmutabilidad de registros** | Hash chain + anclaje en Solana — imposible modificar retroactivamente |
| **Certificado de origen** | TradeDocument tipo cert_origen con autoridad emisora y HS code |
| **Certificado fitosanitario** | TradeDocument tipo fitosanitario aprobado por ICA |
| **Declaracion de exportacion** | TradeDocument tipo DEX con numero DIAN |
| **Trazabilidad del lote** | Metadata incluye lote, parcela, altitud, metodo de procesamiento |
| **Due diligence del importador** | PDF descargable con toda la cadena para archivo del importador |

El importador aleman (Hamburg Coffee Imports) puede:
1. Descargar el **Certificado PDF** con toda la trazabilidad
2. Verificar cada hash en **Solana Explorer** (prueba publica)
3. Usar el endpoint **POST /anchoring/verify** para validacion automatizada
4. Presentar estos documentos ante la autoridad competente de la UE

---

## Checklist Final

- [ ] Workflow logistics aplicado (6 estados, 7 transiciones, 7 eventos)
- [ ] 6 tipos de custodio creados (finca→importador)
- [ ] 6 organizaciones creadas
- [ ] 6 wallets con pubkey real en Solana devnet
- [ ] Carga de cafe registrada con metadata completa (lote, score, altitud, parcela)
- [ ] cNFT minteado y CONFIRMED en blockchain
- [ ] Certificado de Origen creado y aprobado
- [ ] Certificado Fitosanitario creado y aprobado
- [ ] DEX creado y aprobado
- [ ] Guia terrestre creada con flujo de estados completo
- [ ] Bill of Lading creado con datos de buque y contenedor
- [ ] Handoffs exitosos en toda la cadena (finca→cooperativa→transporte→puerto→agente→puerto→importador)
- [ ] QC registrado con score de cupping
- [ ] Entrega completada (estado terminal)
- [ ] ~10 eventos en cadena de custodia con hash chain valido
- [ ] Solana Explorer muestra transacciones reales
- [ ] Certificado PDF descargado
- [ ] 3 documentos de comercio exterior aprobados
- [ ] 2 documentos de transporte con flujo de estados
- [ ] Cumplimiento EUDR demostrable con evidencia blockchain
