# Trace — Manual de Usuario

> Sistema de Cadena de Custodia para Activos Digitales y Físicos

---

## ¿Qué es Trace?

**Trace** es un sistema que registra de forma permanente e inalterable el historial completo de un activo: quién lo tuvo, cuándo, dónde y en qué condición. Cada movimiento queda grabado en una cadena de eventos encadenados criptográficamente, y cada evento se ancla en la blockchain de **Solana** como prueba externa e independiente.

Imagínalo como un **libro de actas notariales digital**: una vez que algo se escribe, no se puede borrar ni modificar. Solo se pueden añadir nuevas páginas.

---

## ¿Para qué sirve?

Trace resuelve una pregunta crítica en logística, comercio y transferencia de activos:

> **"¿Cómo sé que este activo estuvo en manos de X persona, en Y lugar, en el momento Z, y que nadie alteró ese registro?"**

Casos de uso típicos:

- **Logística y supply chain**: rastrear un producto desde el fabricante hasta el comprador final.
- **Arte y coleccionables**: probar la cadena de propietarios de una obra.
- **Industria farmacéutica**: trazabilidad de medicamentos con temperatura y condiciones.
- **Activos digitales (NFTs)**: registrar transferencias de custodia con prueba blockchain.
- **Equipos de alto valor**: laptops, maquinaria, equipos médicos que pasan entre departamentos.

---

## Conceptos clave (sin tecnicismos)

### Wallet (Cartera)
Una **wallet** es la identidad de quién puede tener un activo. Piénsala como el nombre de una persona o empresa registrada en el sistema. Antes de que alguien pueda recibir o entregar un activo, su wallet debe estar en la **lista blanca (allowlist)**.

```
Ejemplo de wallet:  "Almacén-Norte-CDMX"  o  "Carrier-DHL-001"
```

### Allowlist (Lista blanca)
Es el **directorio de participantes autorizados**. Solo quienes estén en esta lista pueden recibir activos. Si intentas mover un activo a alguien no registrado, el sistema lo rechaza automáticamente.

Una wallet puede tener tres estados:

| Estado | Significado |
|--------|-------------|
| `active` | Puede recibir y entregar activos |
| `suspended` | Temporalmente sin acceso (puede reactivarse) |
| `revoked` | Permanentemente excluida |

### Asset (Activo)
Es el **objeto que se rastrea**. Puede ser físico (una caja, un equipo) o digital (un NFT). Cada activo tiene:
- Un identificador único de mint (como una matrícula)
- Un tipo de producto
- Un custodio actual (quién lo tiene en este momento)
- Un estado actual
- Todo su historial de eventos

### Evento de custodia
Cada cosa que le pasa al activo se registra como un **evento inmutable**. Los eventos están encadenados: cada uno apunta al anterior, formando una cadena que no se puede romper ni alterar sin que se note.

---

## Estados de un activo

Un activo avanza por estos estados durante su vida:

```
                    ┌─────────────────────────────────────────────┐
                    │                                             │
   [Creación]       │         Ciclo de vida del activo           │
       │            │                                             │
       ▼            └─────────────────────────────────────────────┘
  ┌──────────┐
  │ IN_CUSTODY│  ← El activo está en manos de su custodio actual
  └──────────┘
       │
       │  HANDOFF (entrega a otro)
       ▼
  ┌──────────┐
  │IN_TRANSIT│  ← El activo está en tránsito hacia otro custodio
  └──────────┘
       │
       │  ARRIVED (llegó)
       ▼
  ┌──────────┐
  │ IN_CUSTODY│  ← Nuevo custodio recibe el activo
  └──────────┘
       │
       │  LOADED (se carga en transporte/lote)
       ▼
  ┌──────────┐
  │  LOADED  │
  └──────────┘
       │
       │  QC (control de calidad)
       ▼
  ┌──────────────────────┐
  │ QC_PASSED / QC_FAILED│
  └──────────────────────┘
       │
       │  RELEASE (liberación — solo admins)
       ▼
  ┌──────────┐
  │ RELEASED │  ← Fin de la cadena. El activo sale del sistema.
  └──────────┘
```

---

## Tipos de eventos

### CREATED — Creación del activo
Marca el nacimiento del activo en el sistema. El primer custodio queda registrado. Este evento no tiene "evento anterior", es el origen de la cadena.

**Regla**: El custodio inicial debe estar en la allowlist activa.

### HANDOFF — Entrega a otro custodio
Registra la transferencia de responsabilidad de un custodio a otro. Es el evento más importante de la cadena de custodia.

**Reglas estrictas**:
- El custodio destino (`to_wallet`) debe estar en la allowlist y estar activo.
- Si dos personas intentan hacer un handoff al mismo tiempo, solo uno pasa. El otro es rechazado.

```
Ejemplo:
  Almacén-Norte entrega a Carrier-DHL
  → El activo pasa a estado IN_TRANSIT
  → Carrier-DHL es el nuevo custodio
```

### ARRIVED — Llegada al destino
Confirma que el activo llegó físicamente al lugar de destino. El custodio actual registra la llegada.

```
Ejemplo:
  Carrier-DHL confirma entrega en Almacén-Sur
  → El activo vuelve a estado IN_CUSTODY
```

### LOADED — Cargado en transporte o lote
Registra que el activo fue embarcado, cargado en un contenedor o incluido en un lote.

```
Ejemplo:
  Almacén-Sur carga el activo en el contenedor CONT-001
  → Estado: LOADED
```

### QC — Control de calidad
Registra el resultado de una inspección de calidad.

```
Ejemplo:
  Inspector registra: resultado = "pass", notas = "Todo en orden"
  → Estado: QC_PASSED

  Si falla:
  → Estado: QC_FAILED
```

### RELEASED — Liberación (solo administradores)
Saca el activo del sistema hacia una entidad externa (comprador, destinatario final) que **no necesita estar en la allowlist**. Este evento requiere una clave de administrador y queda completamente auditado.

**Esta operación es irreversible.** Una vez liberado, el activo no puede recibir más eventos.

```
Ejemplo:
  Admin autoriza entrega final al comprador "CompraFinal-SA"
  → Estado: RELEASED
  → Queda registrado: quién lo autorizó, motivo, wallet destino
```

---

## El encadenamiento criptográfico

Cada evento genera una **huella digital única (hash)** calculada a partir de:
- El ID del activo
- El tipo de evento
- Quién lo entregó y quién lo recibió
- La fecha y hora exacta
- La ubicación (si se proporcionó)
- Datos adicionales
- **La huella del evento anterior**

Este último punto es lo que crea la **cadena**: si alguien intentara modificar un evento del pasado, la huella del siguiente evento ya no coincidiría, y se detectaría la manipulación inmediatamente.

```
Evento 1 (CREATED)
  hash: "a3f9..."
      │
      ▼
Evento 2 (HANDOFF)     prev_hash = "a3f9..."
  hash: "7bc2..."
      │
      ▼
Evento 3 (ARRIVED)     prev_hash = "7bc2..."
  hash: "e41d..."
      │
      ▼
  ... y así sucesivamente
```

---

## Anclaje en Solana (blockchain)

Cada evento, además de guardarse en la base de datos interna, se **ancla en la blockchain de Solana** usando el programa Memo. Esto significa que la huella de cada evento queda registrada de forma pública e independiente en una blockchain descentralizada.

**¿Para qué sirve esto?**
- Prueba externa e independiente de que el evento ocurrió.
- No depende de confiar en Trace ni en quien lo opera.
- Cualquiera puede verificar la cadena en Solana.

**¿El anclaje es instantáneo?**

No. El API responde inmediatamente (no bloquea esperando a Solana). El anclaje ocurre en segundo plano: un proceso separado (worker) toma los eventos pendientes y los ancla con reintentos automáticos si la red Solana falla temporalmente.

```
Tu llamada al API           Worker (segundo plano)
      │                            │
      │  POST /events/handoff      │
      ▼                            │
  Guarda en DB ─────────────────▶ Ancla en Solana
  anchored: false                  │
      │                            │  si OK:
  Responde 201 ◀                   │  anchored: true
  {event_hash, anchored: false}    │  solana_tx_sig: "abc..."
```

---

## Idempotencia: sin duplicados accidentales

Si tu sistema envía la misma petición dos veces (por error de red, timeout, etc.), Trace **no creará dos eventos**. Para ello, incluye un encabezado `Idempotency-Key` con un UUID único por operación:

```
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
```

La primera vez se procesa y guarda. La segunda vez (mismo key) devuelve exactamente la misma respuesta sin crear nada nuevo.

---

## Guía de uso paso a paso

### Paso 1: Registrar participantes en la allowlist

Antes de mover cualquier activo, registra las wallets de todos los que participarán:

```bash
# Registrar el almacén de origen
curl -X POST http://localhost:8000/api/v1/registry/wallets \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_pubkey": "Almacen-Origen-CDMX",
    "tags": ["almacen", "origen"],
    "status": "active"
  }'

# Registrar el transportista
curl -X POST http://localhost:8000/api/v1/registry/wallets \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_pubkey": "Carrier-DHL-001",
    "tags": ["carrier", "dhl"],
    "status": "active"
  }'

# Registrar el almacén de destino
curl -X POST http://localhost:8000/api/v1/registry/wallets \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_pubkey": "Almacen-Destino-MTY",
    "tags": ["almacen", "destino"],
    "status": "active"
  }'
```

### Paso 2: Crear el activo

```bash
curl -X POST http://localhost:8000/api/v1/assets \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "asset_mint": "LAPTOP-SN-XYZ-001",
    "product_type": "electronics",
    "metadata": {
      "modelo": "ThinkPad X1",
      "serie": "SN-XYZ-001",
      "valor": 25000
    },
    "initial_custodian_wallet": "Almacen-Origen-CDMX"
  }'
```

Respuesta:
```json
{
  "asset": {
    "id": "uuid-del-activo",
    "state": "in_custody",
    "current_custodian_wallet": "Almacen-Origen-CDMX"
  },
  "event": {
    "event_type": "CREATED",
    "event_hash": "a3f9b2c1...",
    "anchored": false
  }
}
```

### Paso 3: Entregar al transportista (HANDOFF)

```bash
curl -X POST http://localhost:8000/api/v1/assets/{asset_id}/events/handoff \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "to_wallet": "Carrier-DHL-001",
    "location": {
      "lat": 19.4326,
      "lng": -99.1332,
      "label": "Almacén CDMX - Puerta 3"
    },
    "data": {
      "guia": "DHL-1234567890",
      "bultos": 1
    }
  }'
```

### Paso 4: Confirmar llegada (ARRIVED)

```bash
curl -X POST http://localhost:8000/api/v1/assets/{asset_id}/events/arrived \
  -H "Content-Type: application/json" \
  -d '{
    "location": {"label": "Almacén Monterrey - Recepción"},
    "data": {"recibido_por": "Juan García"}
  }'
```

### Paso 5: Hacer entrega al almacén de destino (HANDOFF)

```bash
curl -X POST http://localhost:8000/api/v1/assets/{asset_id}/events/handoff \
  -H "Content-Type: application/json" \
  -d '{
    "to_wallet": "Almacen-Destino-MTY",
    "data": {"condicion": "perfectas condiciones"}
  }'
```

### Paso 6: Control de calidad (QC)

```bash
curl -X POST http://localhost:8000/api/v1/assets/{asset_id}/events/qc \
  -H "Content-Type: application/json" \
  -d '{
    "result": "pass",
    "notes": "Equipo funciona correctamente. Sin daños.",
    "data": {"inspector": "María López", "protocolo": "QC-v2"}
  }'
```

### Paso 7: Liberar al cliente final (RELEASE — solo admin)

```bash
curl -X POST http://localhost:8000/api/v1/assets/{asset_id}/events/release \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: tu-clave-admin-aqui" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "external_wallet": "Cliente-Final-Ramirez-SA",
    "reason": "Venta completada - Orden de compra #OC-2024-0891"
  }'
```

### Consultar el historial completo

```bash
# Ver estado actual del activo
curl http://localhost:8000/api/v1/assets/{asset_id}

# Ver toda la cadena de custodia
curl http://localhost:8000/api/v1/assets/{asset_id}/events
```

---

## Reglas de negocio — Resumen rápido

| Situación | Resultado |
|-----------|-----------|
| Registrar wallet que ya existe | ❌ Error 409 |
| Crear activo con custodio no allowlisted | ❌ Error 403 |
| HANDOFF a wallet suspendida o revocada | ❌ Error 403 |
| HANDOFF a wallet no registrada | ❌ Error 403 |
| Dos HANDOFF simultáneos al mismo activo | ✅ Uno pasa, ❌ el otro falla |
| RELEASE sin clave admin correcta | ❌ Error 403 |
| RELEASE con clave admin correcta | ✅ Activo liberado |
| Cualquier evento en activo RELEASED | ❌ Error 409 |
| Mismo request con mismo Idempotency-Key | ✅ Devuelve resultado original |

---

## Gestión de wallets

### Consultar wallets por etiqueta o estado

```bash
# Todas las wallets activas
curl "http://localhost:8000/api/v1/registry/wallets?status=active"

# Wallets con la etiqueta "carrier"
curl "http://localhost:8000/api/v1/registry/wallets?tag=carrier"
```

### Suspender temporalmente una wallet

```bash
curl -X PATCH http://localhost:8000/api/v1/registry/wallets/{wallet_id} \
  -H "Content-Type: application/json" \
  -d '{"status": "suspended"}'
```

### Reactivar una wallet suspendida

```bash
curl -X PATCH http://localhost:8000/api/v1/registry/wallets/{wallet_id} \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}'
```

---

## Verificar el estado del sistema

```bash
# ¿Está vivo el servidor?
curl http://localhost:8000/health
# → {"status": "ok", "version": "0.1.0"}

# ¿Están bien la base de datos y Redis?
curl http://localhost:8000/ready
# → {"status": "ok", "checks": {"postgres": "ok", "redis": "ok"}}
```

---

## Reintentar anclaje en Solana manualmente

Si un evento no se ancló (por caída temporal de la red Solana), puedes reintentarlo:

```bash
curl -X POST http://localhost:8000/api/v1/assets/{asset_id}/events/{event_id}/anchor
```

---

## Preguntas frecuentes

**¿Puedo modificar un evento ya registrado?**
No. Los eventos son permanentes e inmutables por diseño. Eso es precisamente lo que hace que la cadena sea confiable.

**¿Qué pasa si Solana está caída?**
El evento se guarda normalmente en la base de datos interna y queda marcado como `anchored: false`. El worker intentará anclarlo automáticamente con reintentos. Puedes también disparar un reintento manual.

**¿Puedo reutilizar el mismo Idempotency-Key para diferentes operaciones?**
No. Cada clave es única por operación. Si usas el mismo key para dos operaciones distintas, la segunda recibirá la respuesta cacheada de la primera.

**¿Cómo sé si mi evento ya está anclado en Solana?**
Consulta el evento: si `anchored: true`, ya tiene su `solana_tx_sig` que puedes verificar en cualquier explorador de Solana.

**¿Qué es el `event_hash`?**
Es la huella digital única de ese evento. Sirve para verificar que el evento no fue alterado. Si el hash coincide al recalcularlo con los mismos datos, el evento es auténtico.

**¿Qué pasa si dos sistemas mandan el mismo HANDOFF al mismo tiempo?**
El sistema usa bloqueo de base de datos (`SELECT FOR UPDATE`) para garantizar que solo uno de los dos pase. El otro recibe un error de conflicto.
