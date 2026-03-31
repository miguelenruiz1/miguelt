# Journey: Carga Internacional Completa con Cumplimiento EUDR

Flujo paso a paso para exportar cafe colombiano a Europa cumpliendo con la norma EUDR (Regulation EU 2023/1115). Cubre los 3 modulos: Inventario, Logistica y Cumplimiento.

**Contexto:**
- Cooperativa cafetera en Huila, Colombia
- Exporta 18,000 kg de cafe verde arabica a Hamburg, Alemania
- El importador europeo exige certificado EUDR con trazabilidad completa
- Transporte multimodal: terrestre (finca -> puerto) + maritimo (Buenaventura -> Hamburg)

**Prerequisitos:**
- Frontend corriendo en `http://localhost:5173`
- Todos los servicios corriendo via `docker compose up`
- Tenant `default` creado
- Usuario autenticado con rol `administrador`

---

## FASE 0 — Configuracion Inicial (una sola vez)

### Paso 0.1 — Activar Modulos

**Ruta:** `/marketplace`

1. Encontrar tarjeta **Inventario** → click toggle **"Activar"**
2. Encontrar tarjeta **Logistica** → click toggle **"Activar"**
3. Encontrar tarjeta **Cumplimiento** → click toggle **"Activar"**

**Verificar:** en el sidebar aparecen las 3 secciones: Inventario, Logistica, Cumplimiento.

---

### Paso 0.2 — Seedear Workflow de Logistica

**Ruta:** `/configuracion/flujo-de-trabajo`

1. Click tab **"Plantillas de industria"**
2. Hay 6 plantillas disponibles. Seleccionar **supply_chain** (icono de caja) → click **"Aplicar"**

> **Por que supply_chain y no logistics?** El preset `logistics` solo tiene 6 estados y 7 eventos (recibido/bodega/transito/reparto/entregado) — es para entregas domesticas simples. El preset `supply_chain` tiene 12 estados, 39 transiciones y 17 tipos de evento, incluyendo CUSTOMS_HOLD, CUSTOMS_CLEARED, SEALED, UNSEALED, DEPARTED, DAMAGED, RETURN y eventos informativos (TEMPERATURE_CHECK, INSPECTION, NOTE) — todo lo necesario para logistica internacional con aduanas.

3. Verificar tab **"Estados"** — deben aparecer **12 estados**:

| # | Slug | Label | Color | Icono | Tipo |
|---|------|-------|-------|-------|------|
| 1 | in_custody | En custodia | Morado #8b5cf6 | package | **Inicial** |
| 2 | in_transit | En transito | Amarillo #f59e0b | truck | |
| 3 | loaded | Cargado | Azul #3b82f6 | container | |
| 4 | qc_passed | QC aprobado | Verde #22c55e | check-circle | |
| 5 | qc_failed | QC fallido | Rojo #ef4444 | x-circle | |
| 6 | customs_hold | Retencion aduana | Naranja #f97316 | shield-alert | |
| 7 | damaged | Danado | Rojo oscuro #dc2626 | alert-triangle | |
| 8 | sealed | Sellado | Cyan #06b6d4 | lock | |
| 9 | delivered | Entregado | Verde #059669 | check-circle-2 | |
| 10 | released | Liberado | Verde #10b981 | unlock | **Terminal** |
| 11 | burned | Entrega finalizada | Gris #6b7280 | flame | **Terminal** |
| 12 | returned | Devuelto | Naranja #ea580c | undo-2 | |

4. Verificar tab **"Transiciones"** — deben aparecer **39 transiciones**, incluyendo:

| Desde | Hacia | Evento | Descripcion |
|-------|-------|--------|-------------|
| in_custody | in_transit | HANDOFF | Transferir custodia |
| in_transit | in_transit | HANDOFF | Re-transferir |
| loaded | in_transit | HANDOFF | Despachar |
| in_transit | in_custody | ARRIVED | Registrar llegada |
| in_custody | loaded | LOADED | Cargar en transporte |
| in_custody | qc_passed | QC | QC aprobado |
| in_custody | qc_failed | QC | QC fallido |
| qc_failed | qc_passed | QC | Re-inspeccion OK |
| in_custody | customs_hold | CUSTOMS_HOLD | Retener en aduana |
| in_transit | customs_hold | CUSTOMS_HOLD | Retener en aduana |
| customs_hold | in_custody | CUSTOMS_CLEARED | Liberar de aduana |
| loaded | sealed | SEALED | Sellar |
| sealed | loaded | UNSEALED | Remover sello |
| in_custody | delivered | DELIVERED | Entregar |
| in_transit | delivered | DELIVERED | Entregar |
| delivered | returned | RETURN | Devolver |
| delivered | burned | BURN | Cerrar cadena |
| *(+ 22 transiciones mas para cubrir todos los caminos)* | | | |

5. Verificar tab **"Tipos de evento"** — deben aparecer **17 tipos**:

| # | Slug | Nombre | Icono | Color | Requiere |
|---|------|--------|-------|-------|----------|
| 1 | CREATED | Carga registrada | plus-circle | Verde | Docs: foto (opcional), titulo parcela (compliance) |
| 2 | HANDOFF | Transferir custodia | arrow-right | Azul | **Wallet destino**, Docs: remision, foto, guia terrestre (compliance) |
| 3 | ARRIVED | Registrar llegada | map-pin | Morado | Docs: foto recepcion (opcional) |
| 4 | LOADED | Cargar en transporte | container | Cyan | Docs: foto (opcional) |
| 5 | QC | Control de calidad | clipboard-check | Amarillo | **Notas obligatorias**, Docs: reporte QC, analisis lab (compliance) |
| 6 | DELIVERED | Entregar | check-circle | Verde | **Wallet destino**, Docs: prueba de entrega, firma (compliance: bloquea sin POD) |
| 7 | BURN | Finalizar entrega | flame | Rojo | **Razon obligatoria** |
| 8 | RELEASED | Liberar (admin) | unlock | Verde | **Razon + Admin obligatorio** |
| 9 | CUSTOMS_HOLD | Retencion aduana | shield-alert | Naranja | **Razon obligatoria**, Docs: notificacion retencion |
| 10 | CUSTOMS_CLEARED | Liberado de aduana | shield-check | Verde | Docs: acta liberacion, compliance: cert origen + fitosanitario + DEX (**bloquea sin ellos**) |
| 11 | DAMAGED | Reportar dano | alert-triangle | Rojo | **Razon obligatoria**, Docs: foto del dano |
| 12 | SEALED | Sellar carga | lock | Cyan | Docs: foto sello, compliance: BL + seguro (**bloquea sin ellos**) |
| 13 | UNSEALED | Remover sello | unlock | Amarillo | |
| 14 | RETURN | Devolucion | undo-2 | Naranja | **Razon obligatoria** |
| 15 | TEMPERATURE_CHECK | Lectura de temperatura | thermometer | Rojo | *Informativo* (no cambia estado) |
| 16 | INSPECTION | Inspeccion | search | Morado | *Informativo*, Docs: reporte inspeccion |
| 17 | NOTE | Nota | message-square | Gris | *Informativo* |

---

### Paso 0.3 — Crear Tipos de Custodio

**Ruta:** `/organizations` → section **"Gestionar tipos de custodio"**

Crear los siguientes tipos (si no existen):

| Nombre | Slug | Icono |
|--------|------|-------|
| Finca | finca | sprout |
| Cooperativa | cooperativa | building-2 |
| Transportista | transportista | truck |
| Puerto | puerto | ship |
| Agente Aduanero | agente_aduanero | shield |
| Naviera | naviera | ship |
| Importador | importador | globe |

---

### Paso 0.4 — Crear Organizaciones

**Ruta:** `/organizations` → **"Nueva Organizacion"**

| # | Nombre | Tipo | Descripcion |
|---|--------|------|-------------|
| 1 | Finca La Esperanza | Finca | Finca cafetera en Pitalito, Huila. 12 ha, arabica lavado, 1750 msnm |
| 2 | Cooperativa CafeHuila | Cooperativa | Centro de acopio y beneficio. Certif. Rainforest Alliance |
| 3 | TransAndina Cargo | Transportista | Transporte refrigerado Huila-Buenaventura |
| 4 | Puerto de Buenaventura | Puerto | Terminal maritima del Pacifico colombiano |
| 5 | Agencia GlobalTrade | Agente Aduanero | Agente de aduanas para exportacion |
| 6 | Maersk Line | Naviera | Naviera - ruta Buenaventura-Hamburg |
| 7 | Hamburg Coffee Imports GmbH | Importador | Importador y tostador aleman, Speicherstadt |

---

### Paso 0.5 — Crear Wallets (Custodios)

**Ruta:** `/wallets` → **"Crear Wallet"** (boton verde)

Para cada organizacion, crear un wallet:

| # | Nombre | Organizacion | Etiquetas |
|---|--------|-------------|-----------|
| 1 | Finca La Esperanza | Finca La Esperanza | finca, huila, origen |
| 2 | Bodega CafeHuila | Cooperativa CafeHuila | cooperativa, acopio |
| 3 | Camion Refrigerado TA-01 | TransAndina Cargo | transporte, refrigerado |
| 4 | Terminal Buenaventura | Puerto de Buenaventura | puerto, maritimo |
| 5 | Agente GlobalTrade | Agencia GlobalTrade | aduana, exportacion |
| 6 | M/V Maersk Seletar | Maersk Line | naviera, buque |
| 7 | Hamburg Coffee Imports | Hamburg Coffee Imports GmbH | importador, destino |

**Verificar:** cada wallet tiene un pubkey de Solana asignado y status **Activo**.

---

### Paso 0.6 — Registrar Socios Comerciales

**Ruta:** `/inventario/socios` → **"Nuevo Socio"**

**Socio 1 — Proveedor (Finca):**

| Campo | Valor |
|-------|-------|
| Nombre | Finca La Esperanza S.A.S. |
| Codigo | FINCA-HLA-001 |
| Es proveedor | Si |
| Es cliente | No |
| NIT | 900.123.456-7 |
| Contacto | Maria Gonzalez |
| Email | maria@fincalaesperanza.co |
| Telefono | +57 320 555 1234 |
| Direccion | Vereda El Mirador, Pitalito, Huila |
| Dias de entrega | 3 |
| Terminos de pago | 30 dias |

**Socio 2 — Cliente EU (Importador):**

| Campo | Valor |
|-------|-------|
| Nombre | Hamburg Coffee Imports GmbH |
| Codigo | HCI-HAM-001 |
| Es proveedor | No |
| Es cliente | Si |
| NIT / VAT | DE-123456789 |
| Contacto | Klaus Mueller |
| Email | klaus@hamburgcoffee.de |
| Telefono | +49 40 555 6789 |
| Direccion | Speicherstadt 12, 20457 Hamburg, Germany |
| Limite de credito | 200000 |
| Descuento | 0 |
| Terminos de pago | 60 dias |

---

### Paso 0.7 — Crear Producto

**Ruta:** `/inventario/productos` → **"Nuevo Producto"**

| Campo | Valor |
|-------|-------|
| Nombre | Cafe Verde Arabica Lavado — Huila Especial 84pts |
| SKU | CAFE-HLA-ESP-84 |
| Categoria | Cafe Verde |
| Descripcion | Cafe arabica lavado, secado en camas elevadas. Score 84. Notas citricos y caramelo |
| Unidad de medida | kg |
| Precio sugerido venta | 4.80 USD/kg |
| Costo estimado | 3.20 USD/kg |

---

## FASE 1 — Registrar Parcelas de Produccion

### Paso 1.1 — Activar Framework EUDR

**Ruta:** `/cumplimiento/activaciones` → **"Activar Framework"**

| Campo | Valor |
|-------|-------|
| Framework | EUDR (EU Deforestation Regulation) |
| Destino de exportacion | EU |

Click **"Activar"**

**Verificar:** en la lista aparece EUDR con status **Activo**.

---

### Paso 1.2 — Crear Parcela El Mirador

**Ruta:** `/cumplimiento/parcelas` → **"Nueva Parcela"**

| Campo | Valor |
|-------|-------|
| Codigo | PARC-HLA-MIRADOR-01 |
| Organizacion | Finca La Esperanza |
| Area (ha) | 6.5 |
| Tipo de geolocalizacion | Poligono (OBLIGATORIO: parcela >= 4 ha) |
| Latitud | 1.8547 |
| Longitud | -76.0492 |
| Pais | CO |
| Region | Huila |
| Municipio | Pitalito |
| Numero titulo de tierra | MAT-PITALITO-2019-00567 |
| Tipo de cultivo | cafe_arabica |
| Fecha de establecimiento | 2015-03-15 |
| Fecha de renovacion | 2022-08-10 |
| Tipo de renovacion | Renovacion por zoca |

Click **"Crear"**

---

### Paso 1.3 — Subir Poligono GeoJSON

**En detalle de la parcela** `/cumplimiento/parcelas/{id}`

1. Seccion **"Poligono GeoJSON"** → click **"Subir GeoJSON"**
2. Seleccionar archivo `.geojson` con los limites exactos de la parcela
3. El sistema calcula el hash SHA-256 del archivo y lo almacena

**Verificar:** aparece la URL del GeoJSON y el hash.

---

### Paso 1.4 — Verificar Deforestacion con GFW

**En detalle de la parcela** → click boton **"Verificar Deforestacion (GFW)"**

El sistema:
1. Envia las coordenadas a Global Forest Watch
2. Busca alertas de deforestacion posteriores al 31-dic-2020 (fecha de corte EUDR)
3. Actualiza automaticamente el campo `deforestation_free`

**Verificar resultado:**
- Alertas encontradas: 0
- Alertas alta confianza: 0
- **Libre de deforestacion: Si** (check verde)

---

### Paso 1.5 — Subir Documentos de la Parcela

**En detalle de la parcela** → tab **"Documentos"** → **"Adjuntar Documento"**

| # | Tipo de documento | Archivo | Descripcion |
|---|------------------|---------|-------------|
| 1 | Titulo de tierra (land_title) | titulo-propiedad-mirador.pdf | Matricula inmobiliaria MAT-PITALITO-2019-00567 |
| 2 | Imagen satelital (satellite_image) | sentinel-mirador-2026-01.tif | Imagen Sentinel-2 enero 2026, confirma cobertura de cafe |
| 3 | Reporte de deforestacion (deforestation_report) | gfw-report-mirador.pdf | Reporte GFW descargado, 0 alertas post-2020 |

Para cada uno: seleccionar tipo → click **"Subir"** → verificar que aparece en la lista con hash SHA-256.

---

### Paso 1.6 — Crear Segunda Parcela (si aplica)

Repetir pasos 1.2-1.5 para la parcela **La Cima**:

| Campo | Valor |
|-------|-------|
| Codigo | PARC-HLA-CIMA-02 |
| Area (ha) | 5.5 |
| Latitud | 1.8612 |
| Longitud | -76.0538 |
| Tipo de cultivo | cafe_arabica |
| Fecha de establecimiento | 2017-06-20 |

---

## FASE 2 — Comprar al Productor (Inventario)

### Paso 2.1 — Crear Orden de Compra

**Ruta:** `/inventario/compras` → **"Nueva Orden de Compra"**

| Campo | Valor |
|-------|-------|
| Proveedor | Finca La Esperanza S.A.S. |
| Bodega destino | Bodega Principal |
| Notas | Compra cosecha marzo 2026, lote HLA-2026-0089 |

**Agregar linea:**

| Producto | Cantidad | Costo unitario |
|----------|----------|---------------|
| Cafe Verde Arabica Lavado — Huila Especial 84pts | 18000 | 3.20 |

Click **"Crear"**

---

### Paso 2.2 — Aprobar y Enviar la OC

1. En la tabla de compras, encontrar la OC recien creada
2. Click **"Enviar"** → status cambia a **Enviado**
3. Click **"Confirmar"** → status cambia a **Confirmado**

---

### Paso 2.3 — Recibir la Mercancia

**En detalle de la OC** → click **"Recibir"**

| Campo | Valor |
|-------|-------|
| Cantidad recibida | 18000 |
| Numero de lote | HLA-2026-0089 |
| Numero factura proveedor | FE-FINCA-2026-0342 |
| Fecha factura | 2026-03-25 |
| Total factura | 57600.00 |
| Terminos de pago | 30 dias |
| Fecha vencimiento pago | 2026-04-25 |

Click **"Confirmar Recepcion"**

**Verificar:**
- OC status: **Recibido**
- Stock del producto aumento en 18,000 kg
- En `/assets`: aparece un nuevo **Asset** con estado **IN_CUSTODY**, wallet = Bodega

> El sistema automaticamente llamo al trace-service via S2S y creo el asset.

---

## FASE 3 — Crear Registro de Cumplimiento EUDR

### Paso 3.1 — Nuevo Registro

**Ruta:** `/cumplimiento/registros` → **"Nuevo Registro"**

| Campo | Valor |
|-------|-------|
| Asset | (seleccionar el asset creado en paso 2.3) |
| Framework | EUDR |

Click **"Crear"**

---

### Paso 3.2 — Completar Datos del Producto

**Ruta:** `/cumplimiento/registros/{id}` → tab **"Producto"**

| Campo | Valor |
|-------|-------|
| Codigo HS | 0901.11.90 |
| Tipo de commodity | coffee |
| Descripcion del producto | Cafe verde arabica lavado, grano entero, sin tostar. Score cupping SCA 84 puntos. Notas: citricos, caramelo, cuerpo medio |
| Nombre cientifico | Coffea arabica |
| Cantidad (kg) | 18000 |
| Unidad | kg |
| Pais de produccion | CO |
| Inicio periodo produccion | 2026-03-01 |
| Fin periodo produccion | 2026-03-20 |
| Tipo de actividad | export |

Click **"Guardar"**

---

### Paso 3.3 — Datos del Proveedor

En la misma tab **"Producto"**, seccion Proveedor:

| Campo | Valor |
|-------|-------|
| Nombre proveedor | Finca La Esperanza S.A.S. |
| Direccion proveedor | Vereda El Mirador, Pitalito, Huila, Colombia |
| Email proveedor | maria@fincalaesperanza.co |

Click **"Guardar"**

---

### Paso 3.4 — Datos del Comprador / Operador EU

Seccion Comprador:

| Campo | Valor |
|-------|-------|
| Nombre comprador | Hamburg Coffee Imports GmbH |
| Direccion comprador | Speicherstadt 12, 20457 Hamburg, Germany |
| Email comprador | klaus@hamburgcoffee.de |
| EORI del operador | DE123456789000 |

Click **"Guardar"**

---

### Paso 3.5 — Vincular Parcelas

Tab **"Parcelas"** → click **"Vincular Parcela"**

**Parcela 1:**

| Campo | Valor |
|-------|-------|
| Parcela | PARC-HLA-MIRADOR-01 (Finca La Esperanza, 6.5 ha) |
| Cantidad de esta parcela (kg) | 10800 |
| Porcentaje del total | 60 |

**Parcela 2:**

| Campo | Valor |
|-------|-------|
| Parcela | PARC-HLA-CIMA-02 (5.5 ha) |
| Cantidad de esta parcela (kg) | 7200 |
| Porcentaje del total | 40 |

**Verificar:** cada parcela muestra badges:
- Libre de deforestacion: Si
- Conforme fecha de corte: Si
- Uso legal de tierra: Si

---

### Paso 3.6 — Cadena de Suministro

Tab **"Cadena"** → agregar nodos en orden secuencial:

**Nodo 1:**

| Campo | Valor |
|-------|-------|
| Orden | 1 |
| Rol | Productor |
| Nombre | Finca La Esperanza S.A.S. |
| Pais | CO |
| NIT | 900.123.456-7 |
| Fecha de transferencia | 2026-03-22 |
| Cantidad (kg) | 18000 |

**Nodo 2:**

| Campo | Valor |
|-------|-------|
| Orden | 2 |
| Rol | Acopiador (collector) |
| Nombre | Cooperativa CafeHuila |
| Pais | CO |
| NIT | 800.456.789-1 |
| Fecha de transferencia | 2026-03-23 |
| Cantidad (kg) | 18000 |

**Nodo 3:**

| Campo | Valor |
|-------|-------|
| Orden | 3 |
| Rol | Exportador |
| Nombre | Cooperativa CafeHuila (tambien exporta) |
| Pais | CO |
| NIT | 800.456.789-1 |
| EORI | (vacio — no aplica para exportador CO) |
| Fecha de transferencia | 2026-04-02 |
| Cantidad (kg) | 18000 |

**Nodo 4:**

| Campo | Valor |
|-------|-------|
| Orden | 4 |
| Rol | Importador |
| Nombre | Hamburg Coffee Imports GmbH |
| Pais | DE |
| NIT / VAT | DE-123456789 |
| EORI | DE123456789000 |
| Fecha de transferencia | 2026-05-05 |
| Cantidad (kg) | 18000 |

**Verificar:** la timeline muestra 4 nodos conectados con flechas, todos con estado "No verificado" (se verifican despues).

---

### Paso 3.7 — Evaluacion de Riesgo

Tab **"Riesgo"** → click **"Crear Evaluacion"**

**Paso 1 — Riesgo Pais:**

| Campo | Valor |
|-------|-------|
| Nivel de riesgo pais | Estandar |
| Fuente de datos | EU Country Benchmarking — Regulation (EU) 2023/1115, Art. 29 |
| Notas | Colombia clasificada como riesgo estandar por la Comision Europea. No hay clasificacion de bajo riesgo para paises productores de cafe en la lista inicial |

Click **"Guardar"**

**Paso 2 — Riesgo Cadena de Suministro:**

| Campo | Valor |
|-------|-------|
| Nivel de riesgo | Bajo |
| Notas cadena | Relacion directa con productor desde 2019. Cooperativa con certificacion Rainforest Alliance vigente. Trazabilidad de lote completa desde parcela hasta puerto |
| Estado verificacion proveedor | Verificado |
| Confianza en trazabilidad | Alta |

Click **"Guardar"**

**Paso 3 — Riesgo Regional:**

| Campo | Valor |
|-------|-------|
| Nivel de riesgo regional | Bajo |
| Prevalencia de deforestacion | Baja — Huila es zona cafetera consolidada, no frontera agricola |
| Riesgo derechos indigenas | No |
| Nota indice de corrupcion | CPI Colombia 2025: 39/100. Mitigado por relacion directa y auditorias periodicas |

Click **"Guardar"**

**Medidas de Mitigacion:**

Click **"Agregar Medida"** para cada una:

| # | Medida |
|---|--------|
| 1 | Visita presencial anual a la finca con verificacion GPS de linderos |
| 2 | Certificacion Rainforest Alliance vigente (auditorias anuales independientes) |
| 3 | Monitoreo satelital trimestral de las parcelas via Global Forest Watch |
| 4 | Documentacion fotografica de cada cosecha con geoetiqueta |

**Conclusion:**

| Campo | Valor |
|-------|-------|
| Nivel de riesgo general | Bajo |
| Conclusion | Aprobado |
| Notas de conclusion | Riesgo bajo confirmado. Trazabilidad completa desde parcela hasta destino. Proveedor verificado con certificacion de terceros. Monitoreo satelital confirma ausencia de deforestacion. Se recomienda mantener monitoreo trimestral |

Click **"Completar Evaluacion"**

**Verificar:** el status de la evaluacion cambia a **Completado** y el badge de riesgo muestra "Bajo" en verde.

---

### Paso 3.8 — Adjuntar Documentos de Evidencia

Tab **"Documentos"** → **"Adjuntar Documento"**

| # | Tipo | Archivo | Descripcion |
|---|------|---------|-------------|
| 1 | Declaracion del proveedor (supplier_declaration) | declaracion-finca-2026.pdf | Declaracion jurada de la finca sobre origen de la produccion y ausencia de deforestacion |
| 2 | Certificado legal (legal_cert) | cert-rainforest-2026.pdf | Certificado Rainforest Alliance vigente hasta dic 2027 |
| 3 | Reporte de deforestacion (deforestation_report) | gfw-consolidated-report.pdf | Reporte consolidado GFW para ambas parcelas, 0 alertas |
| 4 | Imagen satelital (satellite_image) | sentinel-huila-mar2026.tif | Compuesto Sentinel-2 marzo 2026 mostrando parcelas con cobertura de cafe |
| 5 | Documento de transporte (transport_doc) | guia-terrestre-preview.pdf | Pre-visualizacion guia terrestre Huila-Buenaventura |

Para cada uno: seleccionar tipo en dropdown → click **"Subir"** → verificar que aparece con hash SHA-256.

---

### Paso 3.9 — Firmar Declaraciones

Tab **"Producto"** → seccion inferior **"Declaraciones"**:

| Campo | Valor |
|-------|-------|
| Declaracion libre de deforestacion | Marcar checkbox |
| Declaracion de cumplimiento legal | Marcar checkbox |
| Nombre del firmante | Maria Gonzalez Ruiz |
| Cargo del firmante | Gerente de Exportaciones |
| Fecha de firma | 2026-04-01 |

Click **"Guardar"**

---

### Paso 3.10 — Validar el Registro

Tab **"Validacion"** → click **"Validar ahora"**

**Resultado esperado:**
- Valido: Si (check verde)
- Compliance status: **Ready**
- Campos faltantes: 0
- Advertencias: 0 (o advertencias informativas no bloqueantes)

**Verificar:** el tracker de progreso en la parte superior muestra **6 de 7 pasos** completos (falta solo el certificado).

---

## FASE 4 — Declaracion DDS y Certificado EUDR

### Paso 4.1 — Exportar DDS para Revision

**Ruta:** `/cumplimiento/registros/{id}` → tab **"Declaracion"**

1. Click boton **"Exportar DDS"**
2. Se descarga un archivo `DDS-{recordId}.json`
3. Abrir el JSON y verificar que contiene:
   - Datos del operador (EORI, nombre, email)
   - Commodities (HS code, cantidad, nombre cientifico)
   - Geolocalizacion (coordenadas de las parcelas)
   - Periodo de produccion
   - Datos del proveedor
   - Declaraciones (deforestacion libre, cumplimiento legal)
   - Firmante

---

### Paso 4.2 — Enviar a TRACES NT

1. En la misma tab **"Declaracion"** → click boton **"Enviar a TRACES NT"**
2. El sistema envia la declaracion al sistema TRACES NT de la Comision Europea
3. Si TRACES NT no esta configurado, el sistema descarga el payload para envio manual

**Resultado esperado:**
- Numero de referencia: `DDS-2026-XXXX` (asignado por TRACES NT)
- Estado de declaracion: **Submitted**
- Fecha de envio: (automatica)

---

### Paso 4.3 — Generar Certificado EUDR

Tab **"Certificado"** → click **"Generar Certificado"**

El sistema:
1. Valida que todos los campos requeridos estan completos
2. Valida que las parcelas >= 4 ha tienen poligono (no solo punto)
3. Genera un PDF profesional con:
   - Numero de certificado (EUDR-2026-XXXX)
   - Codigo QR para verificacion publica
   - Datos del producto y commodity
   - Tabla de parcelas con coordenadas y status de deforestacion
   - Cadena de suministro
   - Resultado de evaluacion de riesgo
   - Documentos de evidencia
   - Datos blockchain (si hay cNFT)
   - Periodo de validez
4. Sube el PDF al storage
5. Calcula hash SHA-256 del PDF

**Verificar:**
- Status del certificado: **Activo** (badge verde)
- Numero: EUDR-2026-XXXX
- Boton **"Descargar PDF"** disponible
- URL de verificacion publica mostrada
- Codigo QR visible

---

### Paso 4.4 — Descargar y Verificar el Certificado

1. Click **"Descargar PDF"** → se descarga `EUDR-2026-XXXX.pdf`
2. Abrir el PDF y verificar:
   - Logo y datos de la empresa
   - Numero de certificado con QR
   - Datos del producto (HS 0901.11.90, 18000 kg, Coffea arabica)
   - Tabla de parcelas con geolocalizacion
   - Evaluacion de riesgo: Bajo
   - Cadena de suministro: 4 actores
   - Declaraciones firmadas
   - Periodo de validez (5 anos desde emision)
3. Click **"Copiar URL de verificacion"** → guardar URL para compartir con el importador

---

### Paso 4.5 — Verificar Certificado Publicamente

**Ruta:** `/cumplimiento/certificados` → buscar el certificado en la lista

1. El certificado aparece con status **Activo**
2. Click en el certificado → ver todos los detalles
3. La URL publica `/api/v1/compliance/verify/{EUDR-2026-XXXX}` es accesible sin autenticacion

**Verificar en la lista de certificados:**
- Framework: EUDR
- Status: Activo (verde)
- Valido desde / hasta

---

## FASE 5 — Documentos de Comercio Exterior

### Paso 5.1 — Certificado de Origen

**Ruta:** `/logistica/documentos-comex` → **"Nuevo Documento"**

| Campo | Valor |
|-------|-------|
| Tipo | Certificado de Origen |
| Numero | CO-2026-HLA-0089 |
| Titulo | Certificado de Origen — Cafe Arabica Lavado Colombia |
| Autoridad emisora | Camara de Comercio del Huila |
| Pais emisor | CO |
| Fecha emision | 2026-03-28 |
| Codigo HS | 0901.11.90 |
| Valor FOB (USD) | 86400.00 |
| Valor CIF (USD) | 94200.00 |
| Moneda | USD |
| Descripcion | 300 sacos x 60kg cafe verde arabica lavado. Origen: Pitalito, Huila. Acogido al TLC Colombia-UE |

Click **"Crear"** → en la tabla, click **"Aprobar"**

**Verificar:** status = Aprobado (verde), anchor_status = pending (se anclara automaticamente).

---

### Paso 5.2 — Certificado Fitosanitario

**"Nuevo Documento"**

| Campo | Valor |
|-------|-------|
| Tipo | Fitosanitario |
| Numero | ICA-FIT-2026-034521 |
| Titulo | Certificado Fitosanitario de Exportacion |
| Autoridad emisora | ICA — Instituto Colombiano Agropecuario |
| Pais emisor | CO |
| Fecha emision | 2026-03-29 |
| Codigo HS | 0901.11.90 |
| Descripcion | Inspeccion fitosanitaria aprobada. Lote libre de broca (Hypothenemus hampei), roya (Hemileia vastatrix) y CBD. Cumple Directiva 2000/29/CE |

Click **"Crear"** → **"Aprobar"**

---

### Paso 5.3 — DEX (Declaracion de Exportacion)

**"Nuevo Documento"**

| Campo | Valor |
|-------|-------|
| Tipo | DEX |
| Numero | DEX-2026-BUN-001247 |
| Titulo | Declaracion de Exportacion — Cafe Verde |
| Autoridad emisora | DIAN Colombia |
| Pais emisor | CO |
| Fecha emision | 2026-04-01 |
| Codigo HS | 0901.11.90 |
| Valor FOB (USD) | 86400.00 |
| Moneda | USD |
| Descripcion | Exportacion definitiva. Regimen: 10. Aduana: Buenaventura. Destino: Hamburg, Alemania. FOB Buenaventura. 300 bultos, 18,000 kg neto |

Click **"Crear"** → **"Aprobar"**

---

### Paso 5.4 — Seguro de Carga

**"Nuevo Documento"**

| Campo | Valor |
|-------|-------|
| Tipo | Certificado de Seguro (insurance_cert) |
| Numero | POL-SURA-2026-EXP-00456 |
| Titulo | Poliza de Seguro de Carga — Exportacion Cafe |
| Autoridad emisora | Seguros SURA S.A. |
| Pais emisor | CO |
| Fecha emision | 2026-03-30 |
| Fecha vencimiento | 2026-06-30 |
| Valor CIF (USD) | 94200.00 |
| Moneda | USD |
| Descripcion | Poliza all-risk para transporte multimodal Pitalito-Hamburg. Cobertura: dano, perdida, contaminacion, robo. Deducible: USD 500 |

Click **"Crear"** → **"Aprobar"**

**Verificar en la tabla:** 4 documentos, todos con status **Aprobado** (verde).

---

## FASE 6 — Orden de Venta y Despacho

### Paso 6.1 — Crear Orden de Venta

**Ruta:** `/inventario/ventas` → **"Nueva Orden de Venta"**

| Campo | Valor |
|-------|-------|
| Cliente | Hamburg Coffee Imports GmbH |
| Bodega origen | Bodega Principal |
| Notas | Exportacion cafe especial Huila. INCOTERM: FOB Buenaventura |

**Agregar linea:**

| Producto | Cantidad | Precio unitario |
|----------|----------|----------------|
| Cafe Verde Arabica Lavado — Huila Especial 84pts | 18000 | 4.80 |

Click **"Crear"**

---

### Paso 6.2 — Confirmar, Picking y Despachar

1. Click **"Confirmar"** → status: **Confirmado** (stock reservado)
2. Click **"Picking"** → status: **Picking**
3. Click **"Despachar"** →

| Campo | Valor |
|-------|-------|
| Tracking number | TA-TRACK-00234 |
| Direccion | Speicherstadt 12, 20457 Hamburg, Germany |
| Ciudad | Hamburg |
| Estado/Prov | Hamburg |
| Codigo postal | 20457 |
| Pais | DE |

Click **"Confirmar Despacho"**

**Verificar:**
- OV status: **Shipped**
- Numero de remision generado automaticamente
- El sistema notifica automaticamente al trace-service → evento **HANDOFF** creado en el asset

---

## FASE 7 — Cadena de Custodia: Colombia

### Paso 7.1 — Verificar Handoff Automatico

**Ruta:** `/assets/{id}` (el asset creado en Fase 2)

**Verificar:** en la timeline aparece un evento **HANDOFF** automatico generado por el despacho de la OV. El asset esta en estado **IN_TRANSIT**.

---

### Paso 7.2 — Crear Guia de Transporte Terrestre

**Ruta:** `/logistica/envios` → **"Nuevo Documento"**

| Campo | Valor |
|-------|-------|
| Tipo | Guia Terrestre |
| Numero | GT-TA-2026-00234 |
| Transportista | TransAndina Cargo |
| Placa vehiculo | XYZ-789 |
| Nombre conductor | Carlos Ramirez |
| Documento conductor | CC 79.456.123 |
| Ciudad origen | Pitalito, Huila |
| Ciudad destino | Buenaventura, Valle del Cauca |
| Pais origen | CO |
| Pais destino | CO |
| Total paquetes | 300 |
| Peso total (kg) | 18000 |
| Descripcion carga | 300 sacos x 60kg cafe verde arabica. Temperatura controlada 18C |
| Valor declarado | 57600 |
| Moneda | USD |
| Fecha despacho | 2026-04-02 |
| Llegada estimada | 2026-04-03 |
| Tracking # | TA-TRACK-00234 |

Click **"Crear"** → en la tabla: **"Emitir"** → **"En Transito"**

---

### Paso 7.3 — Llegada al Puerto

**Ruta:** `/assets/{id}` → click **"Registrar Evento"** → seleccionar **ARRIVED**

| Campo | Valor |
|-------|-------|
| Ubicacion (label) | Puerto de Buenaventura, Terminal de Contenedores |
| Latitud | 3.8801 |
| Longitud | -77.0711 |
| Notas | Llegada sin novedad. Temperatura mantenida a 18C durante 14h de transito. 300 sacos verificados e intactos |

Click **"Registrar"**

**Verificar:** asset estado = **IN_CUSTODY**, wallet cambia al puerto.

---

### Paso 7.4 — Transferir al Agente Aduanero

Click **"Registrar Evento"** → seleccionar **HANDOFF**

| Campo | Valor |
|-------|-------|
| Custodio destino | Agente GlobalTrade |
| Ubicacion | Puerto de Buenaventura, Zona Primaria Aduanera |
| Notas | Entrega a agente aduanero para tramite DEX. Referencia: DEX-2026-BUN-001247 |

Click **"Registrar"**

---

### Paso 7.5 — Retencion Aduanera (Aduana Colombia)

Click **"Registrar Evento"** → seleccionar **CUSTOMS_HOLD**

| Campo | Valor |
|-------|-------|
| Ubicacion | Puerto de Buenaventura, Inspeccion DIAN |
| Notas | Retencion para inspeccion aduanera de exportacion. Presentado DEX-2026-BUN-001247, certificado fitosanitario ICA-FIT-2026-034521, certificado de origen CO-2026-HLA-0089 |

Click **"Registrar"**

**Adjuntar documentos al evento:**
En la timeline, en el evento CUSTOMS_HOLD recien creado, click el icono de documento → adjuntar los PDFs del DEX, fitosanitario y cert. de origen desde el media library.

---

### Paso 7.6 — Liberacion Aduanera

Click **"Registrar Evento"** → seleccionar **CUSTOMS_CLEARED**

| Campo | Valor |
|-------|-------|
| Ubicacion | Puerto de Buenaventura |
| Notas | Inspeccion DIAN aprobada. Mercancia liberada para embarque. Levante: LEV-2026-BUN-00789 |

Click **"Registrar"**

---

### Paso 7.7 — Carga en Contenedor

Click **"Registrar Evento"** → seleccionar **LOADED**

| Campo | Valor |
|-------|-------|
| Ubicacion | Puerto de Buenaventura, Muelle 5 |
| Notas | 300 sacos cargados en contenedor MSKU-7234561. Contenedor tipo 20ft dry. Temperatura ambiente adecuada |

Click **"Registrar"**

---

### Paso 7.8 — Sellado del Contenedor

Click **"Registrar Evento"** → seleccionar **SEALED**

| Campo | Valor |
|-------|-------|
| Ubicacion | Puerto de Buenaventura, Muelle 5, Contenedor MSKU-7234561 |
| Notas | Contenedor sellado. Numero de sello: SEAL-MK-2026-45678. Verificado por: Inspector Puerto Carlos Mendez. Sello intacto, fotografia tomada |

Click **"Registrar"**

---

### Paso 7.9 — Crear Bill of Lading

**Ruta:** `/logistica/envios` → **"Nuevo Documento"**

| Campo | Valor |
|-------|-------|
| Tipo | Bill of Lading |
| Numero | MAEU-BUN-HAM-2026-00891 |
| Transportista | Maersk Line |
| Buque | Maersk Seletar |
| Viaje | V.2026-WC-045 |
| Contenedor | MSKU-7234561 |
| Tipo contenedor | 20ft Dry |
| Numero de sello | SEAL-MK-2026-45678 |
| Ciudad origen | Buenaventura |
| Ciudad destino | Hamburg |
| Pais origen | CO |
| Pais destino | DE |
| Total paquetes | 300 |
| Peso total (kg) | 18000 |
| Volumen (m3) | 22.5 |
| Descripcion carga | 300 bags x 60kg green arabica coffee. HS: 0901.11.90 |
| Valor declarado | 86400 |
| Moneda | USD |
| Fecha despacho | 2026-04-05 |
| Llegada estimada | 2026-05-02 |
| Tracking # | MAEU-2026-00891 |
| Tracking URL | https://www.maersk.com/tracking/MAEU-2026-00891 |
| Costo flete | 3200.00 |
| Costo seguro | 1800.00 |
| Costo manejo | 1200.00 |
| Costo aduanas | 600.00 |
| Otros costos | 400.00 |

Click **"Crear"** → **"Emitir"** → **"En Transito"**

---

### Paso 7.10 — Transferir Custodia a la Naviera

**Ruta:** `/assets/{id}` → **"Registrar Evento"** → **HANDOFF**

| Campo | Valor |
|-------|-------|
| Custodio destino | M/V Maersk Seletar |
| Ubicacion | Puerto de Buenaventura, Muelle 5 |
| Notas | Custodia transferida a Maersk Line. BL: MAEU-BUN-HAM-2026-00891. Contenedor MSKU-7234561 sellado. ETD: 2026-04-05, ETA Hamburg: 2026-05-02 |

Click **"Registrar"**

---

### Paso 7.11 — Zarpe del Buque

Click **"Registrar Evento"** → seleccionar **DEPARTED**

| Campo | Valor |
|-------|-------|
| Ubicacion | Puerto de Buenaventura |
| Notas | M/V Maersk Seletar zarpo 2026-04-05 14:30 UTC. Ruta: Buenaventura → Panama Canal → Cartagena → Algeciras → Hamburg. ETA: 2026-05-02 |

Click **"Registrar"**

**Verificar en `/tracking`:** el asset aparece en la columna **En Transito**.

---

## FASE 8 — Transito Internacional y Llegada a Europa

### Paso 8.1 — Llegada a Puerto de Hamburg

**Ruta:** `/assets/{id}` → **"Registrar Evento"** → **ARRIVED**

| Campo | Valor |
|-------|-------|
| Ubicacion (label) | Port of Hamburg, Container Terminal Altenwerder |
| Latitud | 53.5069 |
| Longitud | 9.9350 |
| Notas | M/V Maersk Seletar arribo 2026-05-02 08:15 UTC. Contenedor MSKU-7234561 descargado. Sellos intactos verificados |

Click **"Registrar"**

---

### Paso 8.2 — Apertura del Contenedor

Click **"Registrar Evento"** → seleccionar **UNSEALED**

| Campo | Valor |
|-------|-------|
| Ubicacion | Port of Hamburg, Container Terminal Altenwerder, Gate 7 |
| Notas | Sello SEAL-MK-2026-45678 roto por inspector portuario Hans Weber. Contenedor abierto, carga en buen estado. 300 sacos visualmente intactos |

Click **"Registrar"**

---

### Paso 8.3 — Retencion Aduanera EU

Click **"Registrar Evento"** → seleccionar **CUSTOMS_HOLD**

| Campo | Valor |
|-------|-------|
| Ubicacion | Port of Hamburg, EU Customs Office |
| Notas | Retencion para verificacion EUDR. Presentados: certificado EUDR (EUDR-2026-XXXX), BL, certificado de origen, fitosanitario, DDS reference. Inspector: Angela Schmidt, German Customs |

Click **"Registrar"**

**Adjuntar documentos al evento:** En la timeline, en el evento CUSTOMS_HOLD, adjuntar el certificado EUDR PDF y la DDS.

---

### Paso 8.4 — Crear DIM (Declaracion de Importacion)

**Ruta:** `/logistica/documentos-comex` → **"Nuevo Documento"**

| Campo | Valor |
|-------|-------|
| Tipo | DIM |
| Numero | DIM-HAM-2026-DE-004521 |
| Titulo | Declaracion de Importacion — Cafe Verde Colombia |
| Autoridad emisora | German Customs (Zoll) |
| Pais emisor | DE |
| Fecha emision | 2026-05-03 |
| Codigo HS | 0901.11.90 |
| Valor CIF (USD) | 94200.00 |
| Moneda | USD |
| Descripcion | Importacion definitiva. 300 bultos, 18,000 kg cafe verde arabica. Origen: Colombia. EUDR-compliant. DDS ref: DDS-2026-XXXX |

Click **"Crear"** → **"Aprobar"**

---

### Paso 8.5 — Liberacion Aduanera EU

**Ruta:** `/assets/{id}` → **"Registrar Evento"** → **CUSTOMS_CLEARED**

| Campo | Valor |
|-------|-------|
| Ubicacion | Port of Hamburg, EU Customs |
| Notas | Aduana EU aprueba importacion. EUDR compliance verificado. DIM: DIM-HAM-2026-DE-004521. Mercancia liberada para entrega al importador |

Click **"Registrar"**

---

### Paso 8.6 — Control de Calidad en Destino

Click **"Registrar Evento"** → seleccionar **QC**

| Campo | Valor |
|-------|-------|
| Resultado | Aprobado (pass) |
| Ubicacion | Hamburg Coffee Imports Warehouse, Speicherstadt |
| Notas | Cupping de verificacion: 83.5 pts (dentro de tolerancia). Humedad: 11.4%. Sin defectos de transporte. Ausencia de contaminacion. Aprobado por Q-Grader Stefan Holz. Apto para tostaduria |

Click **"Registrar"**

**Verificar:** estado = **QC_PASSED**.

---

### Paso 8.7 — Transferir al Importador

Click **"Registrar Evento"** → seleccionar **HANDOFF**

| Campo | Valor |
|-------|-------|
| Custodio destino | Hamburg Coffee Imports |
| Ubicacion | Hamburg Coffee Imports Warehouse, Speicherstadt 12 |
| Notas | Entrega final al importador. 300 sacos (18,000 kg) verificados y aprobados QC. BL original entregado |

Click **"Registrar"**

---

### Paso 8.8 — Entrega Final

Click **"Registrar Evento"** → seleccionar **DELIVERED**

| Campo | Valor |
|-------|-------|
| Ubicacion | Hamburg Coffee Imports GmbH, Speicherstadt 12, 20457 Hamburg |
| Notas | Exportacion completada. 300 sacos (18,000 kg) cafe arabica lavado entregados a Hamburg Coffee Imports GmbH. Cadena de custodia completa desde Finca La Esperanza, Pitalito, Huila hasta Hamburg. Todos los documentos de comercio exterior aprobados. Cumplimiento EUDR certificado y verificable. Certificado: EUDR-2026-XXXX |

Click **"Registrar"**

**Verificar:**
- Estado del asset: **DELIVERED** (terminal — no se permiten mas eventos)
- Badge: "Entrega completada"

---

## FASE 9 — Completar Entrega en Inventario

### Paso 9.1 — Marcar OV como Entregada

**Ruta:** `/inventario/ventas` → buscar la OV

Click **"Entregar"**

**Verificar:**
- OV status: **Delivered**
- Stock descontado (qty_on_hand disminuyo en 18,000)
- Costo de venta (COGS) calculado automaticamente

---

### Paso 9.2 — Completar Documentos de Transporte

**Ruta:** `/logistica/envios`

1. Guia Terrestre GT-TA-2026-00234 → click **"Entregado"**
2. Bill of Lading MAEU-BUN-HAM-2026-00891 → click **"Entregado"**

---

## FASE 10 — Verificacion y Auditoria

### Paso 10.1 — Verificar Cadena de Custodia Completa

**Ruta:** `/assets/{id}`

La timeline debe mostrar ~15 eventos en orden cronologico inverso:

```
DELIVERED         ← Hamburg Coffee Imports, Speicherstadt
HANDOFF           ← → Hamburg Coffee Imports
QC (Aprobado)     ← Hamburg Coffee Imports Warehouse
CUSTOMS_CLEARED   ← Port of Hamburg, EU Customs
CUSTOMS_HOLD      ← Port of Hamburg (con docs adjuntos)
UNSEALED          ← Port of Hamburg, Gate 7
ARRIVED           ← Port of Hamburg (53.50, 9.93)
DEPARTED          ← Puerto de Buenaventura
HANDOFF           ← → M/V Maersk Seletar
SEALED            ← Puerto de Buenaventura, Contenedor MSKU-7234561
LOADED            ← Puerto de Buenaventura, Muelle 5
CUSTOMS_CLEARED   ← Puerto de Buenaventura
CUSTOMS_HOLD      ← Puerto de Buenaventura (con docs adjuntos)
HANDOFF           ← → Agente GlobalTrade
ARRIVED           ← Puerto de Buenaventura (3.88, -77.07)
HANDOFF (auto)    ← generado por despacho OV
CREATED           ← generado por recepcion OC
```

Cada evento tiene:
- Hash SHA-256 encadenado al anterior (click "Detalles tecnicos" para ver)
- Timestamp inmutable
- Wallets from/to
- Badge **"Verificado"** (anclado en Solana)

---

### Paso 10.2 — Verificar Blockchain

**Ruta:** `/assets/{id}` → seccion **"Blockchain"**

1. Click **"Ver NFT en XRAY"** → abre XRAY con imagen, metadata y atributos del cNFT
2. Click **"Ver transaccion en Solana Explorer"** → muestra la TX de mint

**Ruta:** `/logistica/blockchain`

1. Copiar el `event_hash` de cualquier evento (desde "Detalles tecnicos")
2. Pegarlo en el buscador → click **"Consultar"**
3. Verificar: status = **Anclado**, TX Solana visible
4. Click **"Verificar en Solana"** → confirma que el hash existe on-chain

---

### Paso 10.3 — Verificar Certificado EUDR Publicamente

**Ruta:** `/cumplimiento/certificados`

1. Encontrar certificado EUDR-2026-XXXX
2. Click **"Copiar URL de verificacion"**
3. Abrir la URL en navegador incognito (sin login) → debe mostrar los datos del certificado
4. Escanear el QR del PDF con celular → debe abrir la misma pagina de verificacion

---

### Paso 10.4 — Revisar Analiticas de Transporte

**Ruta:** `/logistica/analiticas`

Verificar:
- **Entregas a tiempo**: debe mostrar % basado en la comparacion ETA vs llegada real
- **Transito promedio**: dias entre despacho y entrega
- **Costos logisticos**: desglose de flete ($3,200), seguro ($1,800), manejo ($1,200), aduanas ($600), otros ($400) = total $7,200
- **Top transportistas**: TransAndina Cargo y Maersk Line

---

### Paso 10.5 — Compartir con el Importador

El importador europeo (Hamburg Coffee Imports) recibe:

| # | Documento | Como lo obtiene |
|---|-----------|----------------|
| 1 | Certificado EUDR PDF | Descarga directa o URL de verificacion |
| 2 | URL de verificacion publica | Para presentar ante autoridad competente EU |
| 3 | DDS reference number | Para cruzar con TRACES NT |
| 4 | Bill of Lading | Documento fisico + copia en sistema |
| 5 | Certificado de Origen | Copia certificada |
| 6 | Certificado Fitosanitario | Copia certificada |
| 7 | Poliza de Seguro | Copia digital |

---

## Checklist Final

### Configuracion
- [ ] 3 modulos activados (Inventario, Logistica, Cumplimiento)
- [ ] Workflow supply_chain aplicado
- [ ] 7 tipos de custodio creados
- [ ] 7 organizaciones creadas
- [ ] 7 wallets con pubkey Solana
- [ ] 2 socios comerciales (proveedor CO + cliente EU)
- [ ] 1 producto con HS code y nombre cientifico

### Cumplimiento EUDR
- [ ] Framework EUDR activado para el tenant
- [ ] 2 parcelas registradas con poligono GeoJSON
- [ ] GFW screening aprobado (0 alertas post-2020)
- [ ] Documentos de parcelas subidos (titulos, imagenes satelitales)
- [ ] Registro de cumplimiento creado y completo (7/7 pasos)
- [ ] Cadena de suministro registrada (4 nodos: productor → acopiador → exportador → importador)
- [ ] Evaluacion de riesgo completada (resultado: Bajo, conclusion: Aprobado)
- [ ] 5 documentos de evidencia adjuntos
- [ ] Declaraciones firmadas (deforestacion libre + cumplimiento legal)
- [ ] Validacion aprobada (0 campos faltantes)
- [ ] DDS exportada/enviada a TRACES NT
- [ ] Certificado EUDR generado con QR verificable
- [ ] Certificado PDF descargado

### Inventario
- [ ] OC creada, enviada, confirmada, recibida (stock + lote creados)
- [ ] OV creada, confirmada, picking, despachada, entregada
- [ ] Stock descontado correctamente

### Logistica
- [ ] Asset creado automaticamente por recepcion de OC
- [ ] 5 documentos de comercio exterior (cert. origen, fitosanitario, DEX, seguro, DIM)
- [ ] 2 documentos de transporte (guia terrestre, BL con costos)
- [ ] ~15 eventos de custodia en la timeline
- [ ] Documentos adjuntos a eventos criticos (CUSTOMS_HOLD)
- [ ] Hash chain valido (cada evento referencia al anterior)
- [ ] Eventos anclados en Solana (badge "Verificado")
- [ ] Estado final: DELIVERED (terminal)

### Verificacion
- [ ] NFT verificable en XRAY
- [ ] Hashes verificables en Solana Explorer
- [ ] Certificado EUDR verificable publicamente sin login
- [ ] Analiticas de transporte muestran metricas correctas
- [ ] Todos los documentos de transporte en status "Entregado"

---

## Mapeo EUDR — Articulo por Articulo

| Requisito EUDR | Articulo | Donde se cumple en Trace |
|----------------|----------|--------------------------|
| Identificacion del operador | Anexo II #1 | Registro EUDR: `operator_eori`, `buyer_name`, `buyer_address` |
| Tipo de actividad | Anexo II #2 | Registro EUDR: `activity_type: export` |
| HS code + descripcion | Anexo II #3-4 | Registro EUDR: `hs_code`, `product_description`, `scientific_name`, `quantity_kg` |
| Trazabilidad cadena suministro | Anexo II #5 | Nodos de cadena: productor → acopiador → exportador → importador |
| Geolocalizacion parcelas | Art. 9.1.c | Parcelas con coordenadas + poligono GeoJSON (>= 4 ha) |
| Periodo de produccion | Anexo II #7 | Registro: `production_period_start`, `production_period_end` |
| DDS asociadas previas | Anexo II #8 | Campo `prior_dds_references` (si aplica para derivados) |
| Declaracion libre deforestacion | Anexo II #9 | Checkbox + firma del responsable |
| Declaracion cumplimiento legal | Anexo II #9 | Checkbox + firma del responsable |
| Firmante | Anexo II #10 | `signatory_name`, `signatory_role`, `signatory_date` |
| Evaluacion de riesgo (3 pasos) | Art. 10-11 | Risk assessment: pais, cadena, regional + mitigacion |
| Benchmarking pais | Art. 29 | `country_risk_level` + fuente de datos |
| Verificacion satelital | Art. 10.2 | GFW screening automatico + imagenes Sentinel-2 |
| Retencion documental (5 anos) | Art. 12 | Certificado con `valid_until` = fecha + 5 anos |
| Envio a TRACES NT | Art. 4.2 | Envio automatico via SOAP, referencia `DDS-2026-XXXX` |
| Verificacion publica | — | Endpoint publico `/verify/{cert_number}` + QR code |
| Inmutabilidad | — | Hash chain + anclaje Solana (prueba criptografica) |
