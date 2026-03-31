# Journey: Envio Nacional de Materiales de Construccion

Flujo completo para configurar y operar el modulo de logistica con materiales de construccion a nivel nacional.

**Prerequisitos:**
- Frontend corriendo en `http://localhost:3000`
- trace-service corriendo en `http://localhost:8000`
- Base de datos limpia con tenant `default`
- Blockchain configurado (Helius API key + SOL en fee payer)

---

## Paso 1 — Configurar Workflow

**Ruta:** `/configuracion/flujo-de-trabajo`

1. Ir a tab **Plantillas de industria**
2. Click **"Aplicar plantilla"** en la tarjeta construction
3. Ir a tab **Estados** y verificar 6 estados:

| # | Color | Estado | Badges |
|---|---|---|---|
| 1 | Amarillo | Solicitado | `Inicial` |
| 2 | Morado | En fabricacion | |
| 3 | Azul | En obra | |
| 4 | Cyan | Instalado | |
| 5 | Verde | Cerrado | |
| 6 | Naranja | Devuelto | |

4. Ir a tab **Transiciones** y verificar 6 transiciones
5. Ir a tab **Tipos de evento** y verificar 7 eventos incluyendo DEVOLUCION

---

## Paso 2 — Crear Tipos de Custodio

**Ruta:** `/organizations` → seccion colapsable **"Gestionar tipos de custodio"**

Crear 4 tipos:

| Nombre | Slug | Color | Icono |
|---|---|---|---|
| Fabrica | fabrica | morado | factory |
| Transportista | transportista | amarillo | truck |
| Bodega | bodega | azul | warehouse |
| Obra | obra | naranja | hard-hat |

---

## Paso 3 — Crear Organizaciones

**Ruta:** `/organizations` → boton **"Nueva Organizacion"**

Crear 4 organizaciones:

| Nombre | Tipo | Descripcion |
|---|---|---|
| Cementos del Norte | Fabrica | Planta de produccion de cemento y bloques |
| TransCarga Express | Transportista | Servicio de transporte terrestre nacional |
| Bodega Central Bogota | Bodega | Centro de distribucion principal |
| Obra Torres del Parque | Obra | Proyecto residencial Fase 2 - Medellin |

**Verificar:** cada org aparece como tarjeta con badge de tipo y color.

---

## Paso 4 — Crear Wallets

**Ruta:** `/wallets` → boton **"Crear Wallet"**

Crear 4 wallets (una por organizacion):

| Nombre de Wallet | Organizacion | Etiquetas | Estado |
|---|---|---|---|
| Planta Cementos | Cementos del Norte | produccion | Activa |
| Camion TC-01 | TransCarga Express | transporte, ruta-bog-med | Activa |
| Bodega BOG | Bodega Central Bogota | bodega | Activa |
| Recepcion Obra | Obra Torres del Parque | obra, destino | Activa |

**Verificar en tabla:**
- 4 filas con icono, nombre, pubkey real (no `sim...`), organizacion, estado Activa
- Click en cualquier wallet abre su detalle con balance Solana

---

## Paso 5 — Registrar Carga

**Ruta:** `/assets` → boton **"Registrar Carga"**

Llenar el formulario:

| Campo | Valor |
|---|---|
| Tipo de producto | Click **otro** (icono caja) → escribir `cemento_portland` |
| Nombre de la carga | 500 sacos Cemento Tipo I - Lote 0342 |
| Organizacion / Finca | Cementos del Norte |
| Wallet custodio inicial | Planta Cementos (aparece al elegir la org) |
| Peso / Cantidad | 25000 |
| Unidad | kg |
| Calidad / Grado | Tipo I - Resistencia 28 dias |
| Origen | Planta Sogamoso, Boyaca |
| Descripcion | Cemento para fundicion columnas nivel 3 |

Click **"Registrar Carga"**

**Verificar en tabla de cargas:**
- Columna "Carga": nombre + pubkey corta
- Columna "Producto": cemento_portland
- Columna "Cantidad": 25,000 kg
- Columna "Custodio": Planta Cementos
- Columna "Blockchain": cambia de "Certificando..." a "Certificado" (refrescar)

---

## Paso 6 — Verificar Detalle del Asset

**Ruta:** Click en la carga en la tabla → `/assets/{id}`

**Verificar columna izquierda:**
- Estado: badge con color del workflow (estado inicial)
- Blockchain: "Certificado" o "Certificando..."
- Custodio: pubkey de Planta Cementos
- Ultimo hash: hash del evento CREATED
- Eventos: 1

**Verificar columna derecha (Cadena de Custodia):**
- 1 evento CREATED con hash y timestamp
- Evento marcado como anclado (check verde)

---

## Paso 7 — Transferir al Transportista

**En pagina de detalle** → click **"Transferir Custodia"** (icono camion)

| Campo | Valor |
|---|---|
| Custodio destino | Camion TC-01 |
| Ubicacion | Planta Sogamoso, Muelle de carga 2 |
| Notas | Despacho ruta Sogamoso-Bogota |

Click **"Confirmar Transferencia"**

**Verificar:**
- Estado cambia
- Custodio actual: Camion TC-01
- Cadena de Custodia: 2 eventos (CREATED → HANDOFF)
- HANDOFF muestra wallets from/to y ubicacion

---

## Paso 8 — Registrar Llegada a Bodega

Click **"Registrar Llegada"** (icono pin de mapa, cyan)

| Campo | Valor |
|---|---|
| Ubicacion | Bodega Central Bogota, Bahia 3 |
| Notas | Recibido completo sin novedades |

Click **"Confirmar Llegada"**

**Verificar:** 3 eventos en la cadena.

---

## Paso 9 — Transferir a la Obra Destino

Click **"Transferir Custodia"**

| Campo | Valor |
|---|---|
| Custodio destino | Recepcion Obra |
| Ubicacion | Bodega Central, Muelle de salida |
| Notas | Despacho final Bogota-Medellin |

Click **"Confirmar Transferencia"**

**Verificar:**
- Custodio actual: Recepcion Obra
- 4 eventos en la cadena

---

## Paso 10 — Completar Entrega

Click **"Completar Entrega"** (icono check, cyan)

| Campo | Valor |
|---|---|
| Observaciones de entrega | Entregado en Obra Torres del Parque. 500 sacos recibidos por Ing. Rodriguez. Sin novedades. |

Click **"Completar Entrega"**

**Verificar:**
- Cuadro cyan: "Entrega completada — La cadena de custodia ha sido finalizada y certificada en blockchain."
- Ya no hay botones de accion
- Cadena de Custodia completa: 5 eventos

```
BURN (Completar Entrega)     ← Recepcion Obra
HANDOFF                      ← Bodega BOG → Recepcion Obra
ARRIVED                      ← Camion TC-01 (Bodega Central)
HANDOFF                      ← Planta Cementos → Camion TC-01
CREATED                      ← Planta Cementos
```

- Cada evento tiene hash encadenado al anterior (verificar que `prev_hash` de cada uno = `hash` del anterior)

---

## Paso 11 — Verificar en Solana Explorer

En detalle del asset → click **"Ver en Solana Explorer"**

**Verificar:** pagina de Solana Explorer muestra transaccion real en devnet con los datos del memo (hash del evento).

---

## Paso 12 — Tablero Kanban

**Ruta:** `/tracking`

**Verificar:**
- La carga aparece en la columna correspondiente al estado final
- Muestra: producto, cantidad, custodio actual, estado blockchain, tiempo desde ultimo evento
- Filtrar por organizacion funciona
- Click en fila lleva al detalle

---

## Paso 13 — Documento de Transporte

**Ruta:** `/logistica/envios` → boton **"Nuevo Documento"**

| Campo | Valor |
|---|---|
| Tipo | Guia Terrestre |
| Numero | GT-2026-00891 |
| Transportista | TransCarga Express |
| Placa | ABC-123 |
| Ciudad Origen | Sogamoso |
| Ciudad Destino | Medellin |
| Paquetes | 500 |
| Peso (kg) | 25000 |
| Tracking # | TC-2026-00891 |

Click **"Crear"**

**Verificar en tabla:**
- Documento aparece con estado "Borrador"
- Click **"Emitir"** → estado: Emitido
- Click **"En Transito"** → estado: En Transito
- Click **"Entregado"** → estado: Entregado

---

## Paso 14 — Descargar Certificado PDF

**Ruta:** detalle del asset → boton **"Certificado PDF"** (arriba a la derecha)

**Verificar:** se descarga PDF con:
- Datos del asset (producto, peso, origen)
- Cadena de custodia completa con hashes
- Link de verificacion blockchain

---

## Checklist Final

- [ ] Workflow construction aplicado (6 estados, 6 transiciones, 7 eventos)
- [ ] 4 tipos de custodio creados
- [ ] 4 organizaciones creadas
- [ ] 4 wallets creadas con pubkey real (no simulada)
- [ ] Carga registrada con metadata completa
- [ ] Blockchain status: Certificado (no Simulado)
- [ ] Handoff exitoso (custodia transferida)
- [ ] Llegada registrada
- [ ] Segundo handoff exitoso
- [ ] Entrega completada (estado terminal)
- [ ] Cadena de custodia: 5 eventos con hash chain valido
- [ ] Solana Explorer muestra transaccion real
- [ ] Tablero kanban muestra la carga
- [ ] Documento de transporte creado y con flujo de estados
- [ ] Certificado PDF descargado
