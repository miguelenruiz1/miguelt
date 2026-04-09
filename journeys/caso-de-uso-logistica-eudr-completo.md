# Caso de Uso: Logistica + EUDR — Exportacion de Cafe Verde a la Union Europea

**Objetivo:** Recorrer todas las funcionalidades de los modulos de **Logistica** (trazabilidad y cadena de custodia) y **Cumplimiento EUDR** (regulacion europea contra la deforestacion) usando un caso real: una exportadora colombiana de cafe verde que le vende a un importador en Alemania y necesita demostrar que su cafe no proviene de tierras deforestadas.

**Requisitos previos:**
- Tener la aplicacion corriendo (frontend en http://localhost:3000)
- Haber iniciado sesion con un usuario que tenga el rol **administrador**
- Tener los modulos **Logistica** y **Cumplimiento** activados desde el Marketplace (`/marketplace`)

**Tiempo estimado:** 30-45 minutos siguiendo cada paso.

---

## Como navegar

La barra lateral izquierda tiene dos secciones relevantes para este caso de uso:

**Seccion "Logistica"** (icono de caja):
- **Seguimiento** — tablero Kanban con el estado de todas las cargas
- **Cargas** — lista de activos/cargas rastreables
- **Custodios** — billeteras/responsables de custodia
- **Organizaciones** — empresas y actores de la cadena
- **Analiticas** — KPIs de transporte
- **Flujo de trabajo** — configurar los estados y transiciones de la cadena de custodia

**Seccion "Cumplimiento"** (icono de globo):
- **Marcos Normativos** — catalogo de regulaciones disponibles (EUDR, Organico, etc.)
- **Mis Normas** — cuales regulaciones tiene activadas tu empresa
- **Parcelas** — fincas/lotes de produccion con geolocalizacion
- **Registros** — declaraciones de cumplimiento (el formulario central del EUDR)
- **Certificados** — certificados PDF generados
- **Integraciones** — conexion con Global Forest Watch y TRACES NT

---

## Contexto del caso

**Empresa:** Cafe Origen S.A.S. (exportadora colombiana)
**Producto:** Cafe verde arabica, origen Huila
**Destino:** Hamburg, Alemania (Union Europea)
**Regulacion:** EUDR (EU Regulation 2023/1115) — Reglamento contra la Deforestacion
**Reto:** Desde diciembre 2025, todo cafe que entre a la UE debe demostrar con geolocalizacion y documentos que no proviene de tierras deforestadas despues del 31 de diciembre de 2020.

### Actores en la cadena:

| Actor | Rol | Tipo |
|-------|-----|------|
| Finca El Paraiso | Productor de cafe | Finca (productor) |
| Cafe Origen S.A.S. | Exportadora | Comercializador |
| Cooperativa Huila | Acopio y beneficio | Procesador |
| Naviera Maersk | Transporte maritimo | Transportista |
| Hamburg Import GmbH | Importador europeo | Importador |

---

## FASE 1 — Configurar el Flujo de Trabajo

Antes de registrar cargas, hay que definir los estados por los que pasa una carga en tu cadena.

---

### 1.1 Configurar los estados del flujo de trabajo

1. En la barra lateral, dentro de la seccion **Logistica**, haz click en **Flujo de trabajo**.
   - Esto te lleva a la pagina de configuracion del workflow (`/configuracion/flujo-de-trabajo`).
2. El sistema puede tener estados predeterminados. Verifica que existan estos estados (o crealos):
   - **En custodia** (in_custody) — la carga esta bajo la responsabilidad de alguien
   - **En transito** (in_transit) — la carga esta siendo transportada
   - **Cargado** (loaded) — la carga fue cargada en un vehiculo/contenedor
   - **QC Aprobado** (qc_passed) — la carga paso control de calidad
   - **QC Rechazado** (qc_failed) — la carga no paso control de calidad
   - **Liberado** (released) — la carga fue entregada/liberada al destino final
   - **Destruido** (burned) — la carga fue destruida (caso extremo)
3. Estos estados definen las columnas que veras en el tablero Kanban de **Seguimiento**.

---

## FASE 2 — Registrar las Organizaciones

Necesitamos dar de alta a todos los actores que participan en la cadena de suministro.

---

### 2.1 Crear tipos de custodio

1. En la barra lateral, dentro de la seccion **Logistica**, haz click en **Organizaciones**.
   - Esto te lleva a la pagina de Organizaciones (`/organizations`).
2. En la parte inferior de la pagina, busca la seccion de **Tipos de Custodio** (o accede desde el panel de configuracion).
3. Crea los siguientes tipos (si no existen ya):
   - **Finca** — icono: sprout (brote de planta)
   - **Procesador** — icono: building2 (edificio)
   - **Transportista** — icono: truck (camion)
   - **Comercializador** — icono: warehouse (bodega)
   - **Importador** — icono: building2

---

### 2.2 Crear las organizaciones

1. En la misma pagina de **Organizaciones**, haz click en el boton **"Nueva Organizacion"**.
2. Crea estas 5 organizaciones una por una:

   **Organizacion 1:**
   - Nombre: **Finca El Paraiso**
   - Tipo: Finca
   - Descripcion: "Finca cafetera en Pitalito, Huila. 12 hectareas de cafe arabica variedad Caturra."
   - Guardar.

   **Organizacion 2:**
   - Nombre: **Cooperativa Huila**
   - Tipo: Procesador
   - Descripcion: "Centro de acopio y beneficio humedo. Recibe cafe cereza y entrega cafe pergamino seco."
   - Guardar.

   **Organizacion 3:**
   - Nombre: **Cafe Origen S.A.S.**
   - Tipo: Comercializador
   - Descripcion: "Exportadora de cafe verde. Trilla, seleccion y exportacion."
   - Guardar.

   **Organizacion 4:**
   - Nombre: **Naviera Maersk**
   - Tipo: Transportista
   - Descripcion: "Transporte maritimo internacional."
   - Guardar.

   **Organizacion 5:**
   - Nombre: **Hamburg Import GmbH**
   - Tipo: Importador
   - Descripcion: "Importador y distribuidor de cafe verde en la Union Europea."
   - Guardar.

3. Verifica que las 5 organizaciones aparecen en la cuadricula. Puedes filtrar por tipo usando los chips de filtro en la parte superior.

---

## FASE 3 — Registrar Custodios (Billeteras)

Cada persona u organizacion que va a tener custodia de la carga necesita una "billetera" (wallet) que la identifica en el sistema.

---

### 3.1 Crear billeteras para cada actor

1. En la barra lateral, dentro de la seccion **Logistica**, haz click en **Custodios**.
   - Esto te lleva a la pagina de Custodios (`/wallets`).
2. Haz click en el boton **"Generar Billetera"** (o "Crear Billetera").
3. Crea una billetera para cada organizacion:

   **Billetera 1:**
   - Nombre: **Juan Perez — Finca El Paraiso**
   - Organizacion: Finca El Paraiso
   - Tipo: Finca
   - Guardar.
   - El sistema genera automaticamente una direccion publica (clave publica tipo Solana).

   **Billetera 2:**
   - Nombre: **Maria Lopez — Cooperativa Huila**
   - Organizacion: Cooperativa Huila
   - Tipo: Procesador
   - Guardar.

   **Billetera 3:**
   - Nombre: **Carlos Ruiz — Cafe Origen**
   - Organizacion: Cafe Origen S.A.S.
   - Tipo: Comercializador
   - Guardar.

   **Billetera 4:**
   - Nombre: **Operador Maersk**
   - Organizacion: Naviera Maersk
   - Tipo: Transportista
   - Guardar.

   **Billetera 5:**
   - Nombre: **Klaus Schmidt — Hamburg Import**
   - Organizacion: Hamburg Import GmbH
   - Tipo: Importador
   - Guardar.

4. Verifica que las 5 billeteras aparecen en la lista, agrupadas por organizacion.

---

## FASE 4 — Crear la Carga (Asset) y Registrar la Cadena de Custodia

Ahora vamos a crear la carga de cafe y registrar cada paso de su viaje desde la finca hasta el puerto.

---

### 4.1 Crear la carga (Asset)

1. En la barra lateral, dentro de la seccion **Logistica**, haz click en **Cargas**.
   - Esto te lleva a la pagina de Cargas (`/assets`).
2. Haz click en el boton **"Crear"** (o "Nueva Carga" / "Registrar Activo").
3. Llena los datos de la carga:
   - Nombre/Descripcion: **"Lote Cafe Verde Huila — Exportacion EU Abril 2026"**
   - Tipo de documento: (selecciona el que aplique, por ejemplo "Factura" o "AWB")
   - Custodio inicial: **Juan Perez — Finca El Paraiso** (la billetera del productor)
   - Metadatos adicionales (si el formulario lo permite):
     - Producto: Cafe verde arabica
     - Origen: Pitalito, Huila, Colombia
     - Peso: 18,000 kg (300 sacos de 60 kg)
     - Variedad: Caturra
4. Guardar. La carga queda en estado **"En custodia"** asignada a Juan Perez.

---

### 4.2 Evento 1: Traspaso de Finca a Cooperativa (Handoff)

Simula que el caficultor entrega el cafe cereza a la cooperativa para beneficio.

1. Entra al detalle de la carga que acabas de crear.
   - Haz click en la carga en la lista, o navega a `/assets/{id}`.
2. Veras la **linea de tiempo de eventos** (Event Timeline) — por ahora solo muestra la creacion.
3. Busca el boton para registrar un evento de **"Traspaso"** (Handoff).
4. Llena los datos:
   - Custodio destino: **Maria Lopez — Cooperativa Huila**
   - Ubicacion: "Centro de acopio Pitalito"
   - Notas: "Entrega de 300 sacos de cafe cereza para beneficio humedo"
5. Confirmar. La custodia ahora pasa a Maria Lopez.
6. En la linea de tiempo aparece el evento de traspaso con fecha y hora.

---

### 4.3 Evento 2: Control de Calidad en la Cooperativa (QC)

La cooperativa verifica la calidad del cafe.

1. En el detalle de la carga, registra un evento de **"QC"** (Control de Calidad).
2. Llena los datos:
   - Resultado: **Aprobado** (passed)
   - Notas: "Humedad 11.5%, taza 84 puntos, cero defectos. Apto para exportacion."
3. Confirmar. El estado de la carga cambia a **"QC Aprobado"**.

---

### 4.4 Subir evidencia al evento de QC

Para EUDR necesitas evidencia documental. Vamos a adjuntar el reporte de catacion.

1. En la linea de tiempo, busca el evento de QC que acabas de crear.
2. Haz click en el boton para **subir evidencia** o **adjuntar documento**.
3. Sube un archivo (puede ser un PDF de prueba o una imagen):
   - Tipo: "Reporte de catacion"
   - Archivo: (selecciona cualquier PDF de prueba)
4. Confirmar. El documento queda vinculado al evento de QC.

---

### 4.5 Evento 3: Traspaso de Cooperativa a Exportadora (Handoff)

La cooperativa entrega el cafe pergamino seco a la exportadora.

1. Registra otro evento de **"Traspaso"** (Handoff):
   - Custodio destino: **Carlos Ruiz — Cafe Origen**
   - Notas: "Entrega de 300 sacos de cafe pergamino seco. Peso neto: 18,000 kg."
2. Confirmar.

---

### 4.6 Evento 4: Carga en contenedor (Loaded)

La exportadora carga el cafe en un contenedor para envio maritimo.

1. Registra un evento de **"Cargado"** (Loaded):
   - Notas: "Cafe cargado en contenedor MSKU-1234567. Sello: AB12345. Puerto de Buenaventura."
2. Confirmar. El estado cambia a **"Cargado"**.

---

### 4.7 Evento 5: Traspaso a Naviera (Handoff — en transito)

El contenedor sale del puerto en el barco de Maersk.

1. Registra un evento de **"Traspaso"** (Handoff):
   - Custodio destino: **Operador Maersk**
   - Notas: "Contenedor MSKU-1234567 embarcado en MV Maersk Sealand. Zarpe: Buenaventura → Hamburg. ETA: 2026-05-05."
2. Confirmar. La custodia pasa a Maersk.

---

### 4.8 Evento 6: Llegada al puerto destino (Arrived)

El barco llega a Hamburg.

1. Registra un evento de **"Llegada"** (Arrived):
   - Notas: "Contenedor MSKU-1234567 descargado en Puerto de Hamburg. Sin novedades."
2. Confirmar. El estado cambia a **"Llegada"**.

---

### 4.9 Evento 7: Liberacion al importador (Release)

Aduana libera la carga y se entrega al importador aleman.

1. Registra un evento de **"Liberacion"** (Release):
   - Notas: "Carga liberada por aduana EU. Documentacion EUDR verificada. Entregada a Hamburg Import GmbH."
2. Confirmar. El estado cambia a **"Liberado"**. La cadena de custodia esta completa.

---

### 4.10 Revisar la cadena de custodia completa

1. En el detalle de la carga (`/assets/{id}`), revisa la **linea de tiempo completa**. Debe mostrar 7 eventos en orden cronologico:

   | # | Evento | Custodio | Estado |
   |---|--------|----------|--------|
   | 1 | Creacion | Juan Perez (Finca) | En custodia |
   | 2 | Traspaso | Maria Lopez (Cooperativa) | En custodia |
   | 3 | QC Aprobado | Maria Lopez | QC Aprobado |
   | 4 | Traspaso | Carlos Ruiz (Exportadora) | En custodia |
   | 5 | Cargado | Carlos Ruiz | Cargado |
   | 6 | Traspaso | Operador Maersk | En custodia |
   | 7 | Llegada | Operador Maersk | Llegada |
   | 8 | Liberacion | — | Liberado |

2. Cada evento tiene fecha, hora, custodio responsable, y hash de anclaje blockchain (si esta habilitado).

---

## FASE 5 — Crear Documentos de Transporte

Los documentos de embarque son fundamentales para la exportacion y para el cumplimiento EUDR.

---

### 5.1 Crear un Documento de Embarque (Shipment)

1. Los documentos de embarque se gestionan via API. Si existe interfaz en la app, buscala. Si no, puedes usar la API directamente.
2. Los datos del documento de embarque son:
   - Tipo de documento: **Bill of Lading (BL)**
   - Numero: **MSKU-BL-2026-0001**
   - Transportista: Maersk
   - Placa/Vehiculo: MV Maersk Sealand
   - Numero de contenedor: MSKU-1234567
   - Sello: AB12345
   - Origen: Buenaventura, Colombia
   - Destino: Hamburg, Alemania
   - Peso: 18,000 kg
   - Descripcion de carga: "300 sacos de cafe verde arabica, origen Huila, Colombia"
   - Fecha de zarpe: 2026-04-09
   - Fecha estimada de llegada: 2026-05-05

---

### 5.2 Crear un Documento Comercial (Trade Document)

1. Los documentos comerciales (facturas, certificados) tambien se gestionan como trade documents.
2. Crea un documento:
   - Tipo: **Factura comercial**
   - Numero: **FC-2026-0042**
   - Titulo: "Factura de exportacion — Cafe Verde Huila"
   - Autoridad emisora: Cafe Origen S.A.S.
   - Pais emisor: Colombia
   - Codigo HS: **0901.11** (cafe sin tostar, sin descafeinar)
   - Valor FOB: USD 54,000
   - Moneda: USD
   - Fecha de emision: 2026-04-08
3. Crea otro documento:
   - Tipo: **Certificado fitosanitario**
   - Numero: **ICA-2026-00789**
   - Autoridad emisora: ICA (Instituto Colombiano Agropecuario)
   - Pais emisor: Colombia
   - Fecha de emision: 2026-04-07
   - Fecha de vencimiento: 2026-07-07

---

## FASE 6 — Cumplimiento EUDR

Esta es la parte mas importante para la exportacion a la Union Europea. El Reglamento EUDR (EU 2023/1115) exige que todo cafe que entre a la UE demuestre que:
- No proviene de tierras deforestadas despues del 31 de diciembre de 2020
- Cumple con las leyes locales del pais de produccion
- Tiene geolocalizacion de las parcelas de origen

---

### 6.1 Activar el marco normativo EUDR

1. En la barra lateral, dentro de la seccion **Cumplimiento**, haz click en **Marcos Normativos**.
   - Esto te lleva a `/cumplimiento/frameworks`.
2. Veras un catalogo de marcos regulatorios disponibles. Busca **EUDR** (EU Regulation 2023/1115 — Deforestation-free products).
3. Haz click en el para ver los detalles: que campos requiere, que commodities cubre (cafe, cacao, madera, caucho, palma, soja, ganado).

4. Ahora ve a **Mis Normas** en la barra lateral.
   - Esto te lleva a `/cumplimiento/activaciones`.
5. Haz click en **"Activar"** y selecciona EUDR.
6. Configura:
   - Mercado destino: **Union Europea**
   - Commodity principal: **Cafe**
7. Guardar. EUDR queda activo para tu tenant.

---

### 6.2 Registrar las parcelas de produccion (Plots)

El EUDR Articulo 9.1.c exige geolocalizacion de TODAS las parcelas donde se produjo el cafe. Parcelas de 4 hectareas o mas requieren poligono completo (no solo un punto GPS).

1. En la barra lateral, dentro de la seccion **Cumplimiento**, haz click en **Parcelas**.
   - Esto te lleva a `/cumplimiento/parcelas`.
2. Haz click en **"Nueva Parcela"** (o "Crear Parcela").

   **Parcela 1 — Lote principal (grande, requiere poligono):**
   - Codigo de parcela: **FINCA-EP-LOTE-01**
   - Organizacion: Finca El Paraiso
   - Area: **8 hectareas** (como es >= 4 ha, el sistema exigira poligono)
   - Geolocalizacion:
     - Latitud: **1.8547** (Pitalito, Huila)
     - Longitud: **-76.0513**
     - Tipo: **Poligono**
     - GeoJSON: (pega un poligono GeoJSON de la finca, o sube un archivo con el poligono)
   - Pais: **CO** (Colombia)
   - Region: Huila
   - Municipio: Pitalito
   - Tipo de cultivo: Cafe arabica — Variedad Caturra
   - Fecha de establecimiento: 2015-03-01
   - Libre de deforestacion: **Si** ✓
   - Fecha de corte cumplida (posterior a 31 dic 2020): **Si** ✓
   - Uso legal del suelo: **Si** ✓
   - Nivel de riesgo: **Bajo**
   - Guardar.

   **Parcela 2 — Lote pequeno (solo punto GPS):**
   - Codigo de parcela: **FINCA-EP-LOTE-02**
   - Organizacion: Finca El Paraiso
   - Area: **3.5 hectareas** (menos de 4 ha, solo necesita punto GPS)
   - Geolocalizacion:
     - Latitud: **1.8560**
     - Longitud: **-76.0498**
     - Tipo: **Punto**
   - Pais: CO, Region: Huila, Municipio: Pitalito
   - Tipo de cultivo: Cafe arabica — Variedad Colombia
   - Libre de deforestacion: **Si** ✓
   - Nivel de riesgo: **Bajo**
   - Guardar.

3. Verifica que las 2 parcelas aparecen en la lista.

---

### 6.3 Adjuntar documentos a las parcelas

Para respaldar la informacion de las parcelas, necesitas documentos de soporte.

1. Haz click en la parcela **FINCA-EP-LOTE-01** para ver su detalle (`/cumplimiento/parcelas/{id}`).
2. Busca la seccion de **Documentos**.
3. Adjunta estos documentos:
   - **Titulo de propiedad** — tipo: "land_title"
     - Sube un PDF (puede ser de prueba). Descripcion: "Escritura publica Lote 01 — Finca El Paraiso"
   - **Reporte satelital** — tipo: "satellite_report"
     - Descripcion: "Analisis Global Forest Watch — sin deforestacion detectada 2020-2026"
4. Repite para la parcela FINCA-EP-LOTE-02.

---

### 6.4 Crear el Registro de Cumplimiento (Compliance Record)

El registro es el formulario central del EUDR. Agrupa toda la informacion requerida por el Articulo 9.1.

1. En la barra lateral, dentro de la seccion **Cumplimiento**, haz click en **Registros**.
   - Esto te lleva a `/cumplimiento/registros`.
2. Haz click en **"Nuevo Registro"** (o "Crear").
3. Llena el formulario completo (cada campo corresponde a un requisito del Art. 9.1):

   **Articulo 9.1.a — Identificacion del producto:**
   - Tipo de producto: **Cafe**
   - Descripcion: "Cafe verde arabica sin tostar, origen Huila, Colombia"
   - Codigo HS: **0901.11**

   **Articulo 9.1.b — Nombre cientifico:**
   - Nombre cientifico: **Coffea arabica**

   **Articulo 9.1.d — Periodo de produccion:**
   - Fecha inicio: **2025-10-01** (inicio de cosecha)
   - Fecha fin: **2026-03-15** (fin de cosecha)

   **Tipo de actividad:** Comercio (trade)

   **Articulo 9.1.g — Declaracion de debida diligencia:**
   - Marcar: **"Declaro que se ha realizado la debida diligencia"** ✓

4. Guardar el registro. Queda en estado **Borrador** (draft).

---

### 6.5 Vincular las parcelas al registro

1. Dentro del detalle del registro (`/cumplimiento/registros/{id}`), busca la seccion de **Parcelas**.
2. Haz click en **"Vincular Parcelas"**.
3. Selecciona ambas parcelas:
   - FINCA-EP-LOTE-01 (8 ha)
   - FINCA-EP-LOTE-02 (3.5 ha)
4. Confirmar. Las parcelas quedan vinculadas al registro.
5. El sistema verifica automaticamente:
   - ✓ Todas las parcelas tienen geolocalizacion
   - ✓ Las parcelas >= 4 ha tienen poligono
   - ✓ Todas marcadas como libres de deforestacion

---

### 6.6 Agregar la cadena de suministro (Supply Chain)

El EUDR Art. 9.1.e-f exige documentar todos los actores de la cadena.

1. Dentro del detalle del registro, busca la seccion de **Cadena de Suministro**.
2. Agrega los nodos en orden:

   **Nodo 1 — Productor:**
   - Orden: 1
   - Tipo de actor: **Productor**
   - Nombre de organizacion: Finca El Paraiso
   - Pais: Colombia
   - Contacto: Juan Perez, finca.paraiso@test.com

   **Nodo 2 — Procesador:**
   - Orden: 2
   - Tipo de actor: **Procesador**
   - Nombre: Cooperativa Huila
   - Pais: Colombia

   **Nodo 3 — Comercializador:**
   - Orden: 3
   - Tipo de actor: **Comercializador (Trader)**
   - Nombre: Cafe Origen S.A.S.
   - Pais: Colombia

   **Nodo 4 — Importador:**
   - Orden: 4
   - Tipo de actor: **Importador**
   - Nombre: Hamburg Import GmbH
   - Pais: Alemania

---

### 6.7 Realizar la Evaluacion de Riesgo (Risk Assessment)

El EUDR Art. 10-11 exige una evaluacion formal de riesgo de deforestacion.

1. Dentro del detalle del registro, busca la seccion de **Evaluacion de Riesgo**.
2. Crea la evaluacion:
   - Nivel de riesgo: **Bajo**
   - Factores de riesgo evaluados:
     - "Zona de produccion clasificada como bajo riesgo por la Comision Europea"
     - "Finca con certificacion Rainforest Alliance vigente"
     - "Imagenes satelitales GFW confirman cobertura forestal estable 2020-2026"
   - Medidas de mitigacion:
     - "Verificacion satelital anual via Global Forest Watch"
     - "Auditorias presenciales semestrales a fincas proveedoras"
   - Estado de debida diligencia: **Completada**
   - Estado de cumplimiento: **Conforme**
3. Guardar.

---

### 6.8 Adjuntar documentos de soporte al registro

1. Dentro del detalle del registro, busca la seccion de **Documentos**.
2. Adjunta:
   - Factura comercial (FC-2026-0042)
   - Certificado fitosanitario ICA
   - Bill of Lading
   - Reporte de catacion
   - Certificado Rainforest Alliance (si lo tienes)

---

### 6.9 Validar el registro

1. Haz click en el boton **"Validar"** dentro del registro.
2. El sistema verifica automaticamente contra las reglas del EUDR:
   - ✓ product_type presente
   - ✓ product_description presente
   - ✓ hs_code presente (0901.11)
   - ✓ scientific_name presente (Coffea arabica)
   - ✓ production_start_date y production_end_date presentes
   - ✓ activity_type presente
   - ✓ due_diligence_declaration marcada
   - ✓ risk_assessment completada
   - ✓ geolocalizacion en todas las parcelas
   - ✓ parcelas >= 4 ha tienen poligono
3. Si todo esta correcto, el registro puede avanzar a estado **Enviado** (submitted).
4. Si falta algo, el sistema te dira exactamente que campo falta.

---

### 6.10 Generar el Certificado EUDR

1. Una vez validado el registro, busca el boton **"Generar Certificado"**.
2. El sistema genera un PDF con:
   - Numero de certificado unico
   - Todos los datos del Art. 9.1
   - Geolocalizacion de las parcelas
   - Cadena de suministro completa
   - Evaluacion de riesgo
   - Firma digital (hash)
   - Fecha de emision y vencimiento
3. El certificado aparece en la seccion **Cumplimiento → Certificados** (`/cumplimiento/certificados`).

---

### 6.11 Verificacion publica del certificado

Cualquier persona (el importador, la aduana, un auditor) puede verificar el certificado sin necesidad de cuenta.

1. Abre una ventana de incognito (sin sesion iniciada).
2. Navega a: **`http://localhost:3000/verify/{numero-del-certificado}`**
3. La pagina muestra los datos publicos del certificado y confirma si es valido o fue revocado.

---

## FASE 7 — Integraciones Externas

---

### 7.1 Configurar Global Forest Watch (GFW)

Global Forest Watch es la herramienta satelital que usa la UE para verificar deforestacion.

1. En la barra lateral, dentro de **Cumplimiento**, haz click en **Integraciones**.
   - Esto te lleva a `/cumplimiento/integraciones`.
2. Busca el proveedor **GFW** (Global Forest Watch).
3. Si tienes credenciales de API de GFW, ingresalas aqui.
4. Haz click en **"Probar conexion"** para verificar que funciona.
5. Una vez conectado, el sistema puede verificar automaticamente si las coordenadas de tus parcelas muestran deforestacion.

---

### 7.2 Configurar TRACES NT (opcional)

TRACES NT es el sistema oficial de la Union Europea para notificacion de importaciones.

1. En la misma pagina de **Integraciones**, busca **TRACES NT**.
2. Si tienes credenciales, configuralo aqui.
3. Esto permite comunicar las declaraciones de cumplimiento directamente al sistema de la UE.

---

## FASE 8 — Seguimiento y Analiticas

---

### 8.1 Tablero de Seguimiento (Kanban)

1. En la barra lateral, dentro de **Logistica**, haz click en **Seguimiento**.
   - Esto te lleva al tablero Kanban (`/tracking`).
2. Veras las columnas correspondientes a cada estado del flujo de trabajo:
   - En custodia | En transito | Cargado | QC Aprobado | Liberado | etc.
3. La carga que creamos debe aparecer en la columna **"Liberado"** (porque ya la liberamos en el ultimo evento).
4. El tablero se actualiza automaticamente cada 30 segundos.
5. Puedes filtrar por organizacion para ver solo las cargas de un actor especifico.

---

### 8.2 Analiticas de Transporte

1. En la barra lateral, dentro de **Logistica**, haz click en **Analiticas**.
   - Esto te lleva a `/logistica/analiticas`.
2. Selecciona el periodo: **Abril 2026**.
3. Revisa los KPIs de transporte:
   - Numero de cargas en transito
   - Tiempo promedio de transito
   - Cargas completadas vs pendientes

---

## FASE 9 — Biblioteca de Medios

Todos los archivos subidos (evidencias, documentos, fotos) quedan centralizados.

1. Navega a `/media` (si existe en el menu, o ve directamente a la URL).
2. Veras todos los archivos que subiste durante el caso:
   - Reporte de catacion
   - Titulo de propiedad
   - Reporte satelital
   - Factura comercial
   - Certificado fitosanitario
3. Cada archivo tiene un hash SHA-256 que garantiza su integridad.

---

## Resumen de Funcionalidades Cubiertas

| # | Modulo | Funcionalidades | Donde se hace |
|---|--------|----------------|---------------|
| 1 | Flujo de trabajo | Configurar estados y transiciones | Logistica → Flujo de trabajo |
| 2 | Organizaciones | Tipos de custodio + CRUD organizaciones | Logistica → Organizaciones |
| 3 | Custodios | Generar billeteras por actor | Logistica → Custodios |
| 4 | Cargas | Crear activo rastreable | Logistica → Cargas |
| 5 | Traspaso (Handoff) | Transferir custodia entre actores | Detalle de carga → Evento |
| 6 | QC | Control de calidad con resultado | Detalle de carga → Evento QC |
| 7 | Evidencia | Subir documentos a eventos | Detalle de carga → Evento → Adjuntar |
| 8 | Cargado (Loaded) | Registrar carga en contenedor | Detalle de carga → Evento |
| 9 | Llegada (Arrived) | Registrar arribo a destino | Detalle de carga → Evento |
| 10 | Liberacion (Release) | Liberar carga al destino final | Detalle de carga → Evento |
| 11 | Documentos de embarque | Bill of Lading, datos de transporte | API de shipments |
| 12 | Documentos comerciales | Facturas, certificados, aprobacion | API de trade documents |
| 13 | EUDR Activacion | Activar marco regulatorio | Cumplimiento → Marcos Normativos |
| 14 | Parcelas | Geolocalizacion punto/poligono | Cumplimiento → Parcelas |
| 15 | Documentos de parcela | Titulos, reportes satelitales | Detalle de parcela → Documentos |
| 16 | Registro EUDR | Formulario Art. 9.1 completo | Cumplimiento → Registros |
| 17 | Cadena de suministro | Nodos productor→procesador→trader→importador | Detalle de registro → Supply Chain |
| 18 | Evaluacion de riesgo | Art. 10-11 EUDR | Detalle de registro → Risk Assessment |
| 19 | Validacion | Verificar contra reglas EUDR | Detalle de registro → Validar |
| 20 | Certificado | Generar PDF con firma digital | Detalle de registro → Generar Certificado |
| 21 | Verificacion publica | Validar certificado sin login | /verify/{numero} |
| 22 | GFW | Integracion satelital deforestacion | Cumplimiento → Integraciones |
| 23 | TRACES NT | Integracion sistema UE | Cumplimiento → Integraciones |
| 24 | Seguimiento Kanban | Tablero visual por estado | Logistica → Seguimiento |
| 25 | Analiticas transporte | KPIs de logistica | Logistica → Analiticas |
| 26 | Medios | Biblioteca centralizada de archivos | /media |
| 27 | Blockchain | Anclaje SHA-256 en Solana | Automatico por evento |
