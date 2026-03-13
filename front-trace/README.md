# Trace — Manual de Usuario del Frontend

> Panel de control web para el sistema de cadena de custodia Trace.
> Consume el microservicio FastAPI y permite gestionar wallets, assets y eventos de custodia desde el navegador.

---

## Índice

1. [Requisitos y arranque rápido](#1-requisitos-y-arranque-rápido)
2. [Estructura del proyecto](#2-estructura-del-proyecto)
3. [Arquitectura y flujo de datos](#3-arquitectura-y-flujo-de-datos)
4. [Navegación — las 5 pantallas](#4-navegación--las-5-pantallas)
   - [Dashboard `/`](#41-dashboard-)
   - [Wallets `/wallets`](#42-wallets-wallets)
   - [Assets `/assets`](#43-assets-assets)
   - [Detalle de Asset `/assets/:id`](#44-detalle-de-asset-assetsid)
   - [Sistema `/system`](#45-sistema-system)
5. [Flujo completo de custodia](#5-flujo-completo-de-custodia)
6. [Admin Key — acciones restringidas](#6-admin-key--acciones-restringidas)
7. [Idempotencia en el frontend](#7-idempotencia-en-el-frontend)
8. [Estados de un asset](#8-estados-de-un-asset)
9. [Anchoring en Solana — qué significa cada badge](#9-anchoring-en-solana--qué-significa-cada-badge)
10. [Preguntas frecuentes](#10-preguntas-frecuentes)

---

## 1. Requisitos y arranque rápido

### Lo que necesitas

| Requisito | Versión mínima |
|-----------|---------------|
| Node.js   | 18+           |
| npm       | 9+            |
| Backend Trace corriendo | Puerto 8000 |

### Pasos

```bash
# 1. Entra a la carpeta del frontend
cd Trace/front-trace

# 2. Copia el archivo de entorno
cp .env.example .env

# 3. Instala dependencias
npm install

# 4. Inicia el servidor de desarrollo
npm run dev
```

Abre el navegador en **http://localhost:3000**

El frontend hace proxy automático: todo lo que llega a `/api/*` se redirige a `http://localhost:8000`.
No necesitas configurar CORS ni cambiar ninguna URL mientras el backend esté en el puerto 8000.

### Variables de entorno (`.env`)

```env
VITE_API_BASE_URL=http://localhost:8000
```

> En producción, configura esta variable con la URL real del backend.

---

## 2. Estructura del proyecto

```
front-trace/
├── src/
│   ├── main.tsx              ← Punto de entrada React
│   ├── App.tsx               ← Definición de rutas
│   ├── index.css             ← Estilos base + Tailwind
│   │
│   ├── types/
│   │   └── api.ts            ← Tipos TypeScript de todas las entidades
│   │
│   ├── lib/
│   │   ├── api.ts            ← Cliente HTTP tipado (wrapper sobre fetch)
│   │   ├── query-client.ts   ← Configuración de TanStack Query
│   │   └── utils.ts          ← Helpers: fechas, hashes, clases CSS
│   │
│   ├── store/
│   │   ├── admin.ts          ← Almacena Admin Key en localStorage
│   │   └── toast.ts          ← Sistema de notificaciones toast
│   │
│   ├── hooks/
│   │   ├── useWallets.ts     ← Queries y mutaciones de wallets
│   │   ├── useAssets.ts      ← Queries y mutaciones de assets
│   │   └── useHealth.ts      ← Health checks y Solana debug
│   │
│   ├── components/
│   │   ├── ui/               ← Librería de componentes base
│   │   │   ├── Button.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Dialog.tsx
│   │   │   ├── Misc.tsx      ← Card, Spinner, HashChip, EmptyState...
│   │   │   └── Toast.tsx
│   │   ├── layout/           ← Estructura principal
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Topbar.tsx
│   │   │   └── Layout.tsx
│   │   ├── wallets/
│   │   │   ├── WalletTable.tsx
│   │   │   └── RegisterWalletModal.tsx
│   │   ├── assets/
│   │   │   ├── AssetCard.tsx
│   │   │   └── CreateAssetModal.tsx
│   │   └── events/
│   │       ├── EventTimeline.tsx
│   │       └── EventModals.tsx
│   │
│   └── pages/
│       ├── DashboardPage.tsx
│       ├── WalletsPage.tsx
│       ├── AssetsPage.tsx
│       ├── AssetDetailPage.tsx
│       └── SystemPage.tsx
│
├── vite.config.ts            ← Proxy al backend + alias de imports
├── tailwind.config.ts        ← Tema oscuro personalizado
├── package.json
└── .env.example
```

---

## 3. Arquitectura y flujo de datos

```
┌─────────────────────────────────────────────────┐
│                  Navegador                       │
│                                                  │
│  ┌──────────┐    ┌──────────────────────────┐   │
│  │ Sidebar  │    │        Página activa       │   │
│  │          │    │                           │   │
│  │ /        │    │  ┌─────────────────────┐  │   │
│  │ /wallets │    │  │   React Hook Form   │  │   │
│  │ /assets  │    │  │   TanStack Query    │  │   │
│  │ /system  │    │  │   Zustand Store     │  │   │
│  └──────────┘    │  └────────┬────────────┘  │   │
│                  └──────────┼────────────────┘   │
│                             │                    │
└─────────────────────────────┼────────────────────┘
                              │ fetch /api/...
                              ▼
                   ┌──────────────────┐
                   │  Vite Dev Proxy  │
                   │  localhost:3000  │
                   └────────┬─────────┘
                            │ HTTP
                            ▼
                   ┌──────────────────┐
                   │  FastAPI Backend  │
                   │  localhost:8000  │
                   └──────────────────┘
```

### ¿Cómo fluye la información?

1. El usuario navega a una página (ej. `/assets`)
2. El **hook** correspondiente (`useAssetList`) hace una query a TanStack Query
3. TanStack Query revisa su **caché** (válido por 30 segundos)
4. Si no está en caché o está expirado, llama a `api.assets.list()` en `lib/api.ts`
5. `api.ts` hace un `fetch` a `/api/v1/assets` (proxy → backend :8000)
6. La respuesta llega, se guarda en caché, y React re-renderiza
7. Si hay un **error**, el hook lo expone y se muestra un `EmptyState` o un toast

### Mutaciones (acciones del usuario)

Cuando el usuario ejecuta una acción (ej. Handoff):
1. Se abre el modal correspondiente
2. El formulario valida con **Zod** antes de enviar
3. El hook de mutación (ej. `useHandoff`) llama a `api.assets.handoff()`
4. El cliente HTTP agrega automáticamente un `Idempotency-Key` único
5. Si la respuesta es exitosa:
   - Se invalida el caché del asset y sus eventos
   - Se muestra un toast de éxito
   - Se cierra el modal
6. Si hay error, se muestra el mensaje del backend en el formulario

---

## 4. Navegación — las 5 pantallas

### 4.1 Dashboard `/`

**Propósito:** Vista rápida del estado del sistema.

**Qué muestra:**

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ Total Assets│Active Wallets│  API Status │   Version   │
│     42      │     18      │   Online    │    1.0.0    │
└─────────────┴─────────────┴─────────────┴─────────────┘

┌────────────────────────────────────────────┐
│ System Health                              │
│ ✅ API (liveness)                    ok   │
│ ✅ database                          ok   │
│ ✅ redis                             ok   │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Recent Assets                  View all → │
│                                            │
│ 📦 AbC...XYZ    ABCD...WXYZ  In Custody  │
│ 📦 DeF...UVW    EFGH...STUV  In Transit  │
└────────────────────────────────────────────┘
```

**Tarjetas de stats:**
| Tarjeta | Fuente | Qué indica |
|---------|--------|------------|
| Total Assets | `GET /api/v1/assets` | Todos los assets registrados |
| Active Wallets | `GET /api/v1/wallets?status=active` | Wallets habilitadas para recibir custodia |
| API Status | `GET /health` | Si el backend responde |
| Version | `GET /health` | Versión del microservicio |

**Health checks:**
- Verde (✅) = componente respondiendo `"ok"`
- Rojo (❌) = componente caído o con error

**Assets recientes:** Muestra los últimos 6 assets modificados. Click en cualquiera lleva a `/assets/:id`.

---

### 4.2 Wallets `/wallets`

**Propósito:** Gestionar las wallets de Solana autorizadas para custodiar assets.

**Concepto clave:** Solo wallets **registradas y activas** pueden ser custodios de un asset. Si intentas hacer un handoff a una wallet no registrada, el backend lo rechazará.

#### Filtros disponibles

| Filtro | Descripción |
|--------|-------------|
| Buscar | Filtra por public key o por tags (búsqueda local, no va al servidor) |
| Estado | All / Active / Suspended / Revoked |
| Refresh (↺) | Recarga desde el backend |

#### Tabla de wallets

Cada fila muestra:
- **Public key** — copia al portapapeles al hacer hover
- **Tags** — chips de categorías asignadas (ej. `almacen`, `distribuidor`)
- **Estado** — badge de color: Active (verde), Suspended (amarillo), Revoked (rojo)
- **Creada** — fecha de registro
- **Menú (⋮)** — acciones: Activate / Suspend / Revoke

#### Registrar wallet nueva

Botón **Register Wallet** (esquina superior derecha).

```
┌─────────────────────────────────────────┐
│         Register Wallet                 │
│                                         │
│ Wallet Public Key *                     │
│ ┌─────────────────────────────────────┐ │
│ │ 7xKXtg2CW... (Solana pubkey)        │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Tags (optional)                         │
│ ┌─────────────────────────────────────┐ │
│ │ almacen, distribuidor, zona-norte   │ │
│ └─────────────────────────────────────┘ │
│ Comma-separated tags                    │
│                                         │
│ Status                                  │
│ ┌─────────────────────────────────────┐ │
│ │ active              ▼               │ │
│ └─────────────────────────────────────┘ │
│                                         │
│              [Cancel] [Register Wallet] │
└─────────────────────────────────────────┘
```

**Validaciones:**
- Public key es obligatoria
- Si el backend responde 409, significa que la wallet ya está registrada

---

### 4.3 Assets `/assets`

**Propósito:** Ver y buscar todos los assets en el sistema.

#### Filtros disponibles

| Filtro | Comportamiento |
|--------|---------------|
| Buscar (🔍) | Filtra localmente por mint address o wallet del custodio |
| Product type | Filtra en el servidor por tipo de producto |
| Estado | Filtra en el servidor (in_custody, in_transit, loaded, qc_passed, qc_failed, released) |
| Refresh (↺) | Recarga desde el backend |

#### Grid de asset cards

Cada tarjeta muestra:
```
┌──────────────────────────────┐
│ 📦  AbC...XYZ   [In Transit] │
│     Tipo: Electronics        │
│                              │
│ Custodio                     │
│ ABCD...WXYZ                  │
│                              │
│ Último hash                  │
│ [a1b2c3...] 📋               │
│                              │
│ hace 5 minutos               │
└──────────────────────────────┘
```

Click en la tarjeta → va a `/assets/:id`

#### Crear asset nuevo

Botón **Create Asset** (esquina superior derecha).

```
┌─────────────────────────────────────────┐
│           Create New Asset              │
│                                         │
│ Asset Mint Address *                    │
│ ┌─────────────────────────────────────┐ │
│ │ TokenMintAddress...                 │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Product Type *                          │
│ ┌─────────────────────────────────────┐ │
│ │ Electronics                         │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Initial Custodian Wallet *              │
│ ┌─────────────────────────────────────┐ │
│ │ WalletPubKey...                     │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Metadata (JSON, optional)               │
│ ┌─────────────────────────────────────┐ │
│ │ {"serial": "ABC123", "weight": 5}   │ │
│ └─────────────────────────────────────┘ │
│                                         │
│              [Cancel] [Create Asset]    │
└─────────────────────────────────────────┘
```

**Al crear exitosamente**, navega automáticamente a la página de detalle del nuevo asset.

**Validaciones:**
- Mint address y product type son obligatorios
- La wallet inicial debe estar registrada en el sistema
- Metadata debe ser JSON válido si se especifica

---

### 4.4 Detalle de Asset `/assets/:id`

**Propósito:** Pantalla central de operación. Aquí se ejecutan todas las acciones de custodia y se ve el historial completo.

**Layout:**
```
←  Back to Assets

┌─────────────────┐  ┌──────────────────────────────────────┐
│   Asset Info    │  │         Custody Chain (N events)     │
│                 │  │                                      │
│ 📦              │  │  ● [Handoff]  ABCD→EFGH  📍 Miami   │
│ Mint: AbC...    │  │    Hash: [a1b2...] 📋               │
│ Tipo: Electr.   │  │    Solana: [sig...] 🔗              │
│                 │  │    ▼ Show data                       │
│ State: In Trans │  │                                      │
│ Custodian: ABCD │  │  ● [QC Passed]  EFGH→EFGH  📍 Miami │
│ Last hash: a1b2 │  │    Hash: [b2c3...] 📋               │
│ Events: 5       │  │    ⚡ Simulated                      │
│ Created: Jan 1  │  │                                      │
│ Updated: Jan 5  │  │  ● [Created]   —→ABCD               │
│                 │  │    Hash: [c3d4...] 📋               │
│ ▶ Show metadata │  │    🔗 Anchored                       │
│                 │  │                                      │
├─────────────────┤  └──────────────────────────────────────┘
│    Actions      │
│                 │
│ [🚚 Handoff]    │
│ [📍 Arrived]    │
│ [📦 Loaded]     │
│ [📊 QC Check]   │
│ ─────────────── │
│ [🛡 Release]    │
└─────────────────┘
```

#### Panel izquierdo — Información del asset

| Campo | Descripción |
|-------|-------------|
| Mint | Dirección del token NFT en Solana |
| Product type | Categoría del producto |
| State | Estado actual en la cadena de custodia |
| Custodian | Wallet que tiene la custodia ahora mismo |
| Last hash | Hash SHA-256 del evento más reciente |
| Events | Número total de eventos registrados |
| Created / Updated | Timestamps |
| Metadata | JSON con datos adicionales del asset (expandible) |

#### Panel derecho — Cadena de custodia

Timeline vertical con todos los eventos, del más reciente al más antiguo.

Cada evento muestra:
- **Tipo de evento** — badge de color (ver sección 8)
- **Badge de Solana** — estado del anchoring (ver sección 9)
- **From → To** — wallets de origen y destino
- **Ubicación** — si fue especificada
- **Hash del evento** — copiable al click
- **Firma Solana** — si ya fue anclada, link/chip copiable
- **Datos JSON** — expandible con "Show data"
- **Error de anchor** — si falló el anchoring, muestra el motivo y botón Retry

> El timeline se refresca automáticamente cada 15 segundos para mostrar actualizaciones de anchoring.

#### Acciones disponibles

Cada acción abre un modal con formulario. Las acciones disponibles dependen del estado actual del asset:

| Acción | Cuándo usarla | Campos |
|--------|--------------|--------|
| **Handoff** | Transferir custodia a otra wallet | Nueva wallet custodio, ubicación (opcional), notas (opcional) |
| **Mark Arrived** | El asset llegó a su destino | Ubicación de llegada, notas |
| **Mark Loaded** | El asset fue cargado a un vehículo/contenedor | Ubicación, notas |
| **QC Check** | Resultado de inspección de calidad | Resultado (passed/failed), notas, datos adicionales JSON |
| **Release** | Sacar el asset de la cadena de custodia (irreversible) | Requiere Admin Key |

> Cuando el asset está en estado `released`, las acciones desaparecen y se muestra un aviso informativo.

---

### Modales de acción en detalle

#### Handoff — Transferir custodia

```
┌─────────────────────────────────────────┐
│          Handoff Asset                  │
│                                         │
│ New Custodian Wallet *                  │
│ ┌─────────────────────────────────────┐ │
│ │ 9xABCDEFGH... (debe estar activa)   │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Location                                │
│ ┌─────────────────────────────────────┐ │
│ │ Bogotá, Colombia                    │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Notes                                   │
│ ┌─────────────────────────────────────┐ │
│ │ Entregado al transportista #342     │ │
│ └─────────────────────────────────────┘ │
│                                         │
│              [Cancel] [Confirm Handoff] │
└─────────────────────────────────────────┘
```

**Regla de negocio:** La wallet destino debe estar registrada y en estado `active`.

#### QC Check — Inspección de calidad

```
┌─────────────────────────────────────────┐
│           QC Check                      │
│                                         │
│ Result *                                │
│ ○ Passed    ● Failed                    │
│                                         │
│ Notes                                   │
│ ┌─────────────────────────────────────┐ │
│ │ Grieta visible en el embalaje       │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Additional Data (JSON)                  │
│ ┌─────────────────────────────────────┐ │
│ │ {"inspector": "Juan", "temp": 22}   │ │
│ └─────────────────────────────────────┘ │
│                                         │
│              [Cancel]  [Submit QC]      │
└─────────────────────────────────────────┘
```

#### Release — Liberar asset (admin)

```
┌─────────────────────────────────────────┐
│           Release Asset                 │
│                                         │
│ ⚠️  Esta acción es IRREVERSIBLE.        │
│    El asset saldrá de la cadena de      │
│    custodia permanentemente.            │
│                                         │
│ [No Admin Key configured — set it in   │
│  the toolbar before proceeding]         │  ← si no hay admin key
│                                         │
│ Reason *                                │
│ ┌─────────────────────────────────────┐ │
│ │ Entregado al cliente final          │ │
│ └─────────────────────────────────────┘ │
│                                         │
│              [Cancel]  [Release Asset]  │
└─────────────────────────────────────────┘
```

---

### 4.5 Sistema `/system`

**Propósito:** Diagnóstico técnico del sistema y herramientas de debug para Solana.

#### Health Checks

Muestra el estado de todos los componentes del backend:

```
┌──────────────────────────────────────────────────┐
│ Health Checks                        [↺ Refresh] │
│                                                  │
│ ✅ API liveness                             ok   │
│ ✅ database                                 ok   │
│ ✅ redis                                    ok   │
│ ❌ solana_rpc                           error    │
└──────────────────────────────────────────────────┘
```

#### Solana Account Lookup

Consulta el estado de cualquier cuenta de Solana en la blockchain:

```
┌──────────────────────────────────────────────────┐
│ 🔗 Solana Account Lookup                         │
│                                                  │
│ ┌──────────────────────────────────────┐ [Lookup]│
│ │ Enter Solana public key...           │         │
│ └──────────────────────────────────────┘         │
│                                                  │
│ ⚡ Simulated  (o)  🔗 Live                       │
│ {                                                │
│   "lamports": 1000000,                           │
│   "owner": "TokenkegQfe...",                     │
│   ...                                            │
│ }                                                │
└──────────────────────────────────────────────────┘
```

#### Transaction Status

Consulta el estado de una transacción Solana por su firma:

```
┌──────────────────────────────────────────────────┐
│ 🔗 Transaction Status                            │
│                                                  │
│ ┌──────────────────────────────────────┐ [Lookup]│
│ │ Enter transaction signature...       │         │
│ └──────────────────────────────────────┘         │
│                                                  │
│ ✅ 32 confirmations                              │
│ {                                                │
│   "slot": 284920,                                │
│   "confirmations": 32,                           │
│   "err": null,                                   │
│   ...                                            │
│ }                                                │
└──────────────────────────────────────────────────┘
```

**Badges posibles en TX:**
- `✅ N confirmations` — transacción confirmada
- `❌ Error` — transacción fallida en la blockchain
- `⚡ Simulated` — el backend está en modo simulación (sin RPC real)

---

## 5. Flujo completo de custodia

Este es el recorrido típico de un asset a través del sistema:

```
                      SISTEMA TRACE — FLUJO DE VIDA DE UN ASSET
                      ==========================================

1. REGISTRAR WALLETS
   ├─ Ir a /wallets → Register Wallet
   ├─ Wallet A: "Almacén Central"  (activa)
   ├─ Wallet B: "Transportista"    (activa)
   └─ Wallet C: "Distribuidor"     (activa)

2. CREAR ASSET
   ├─ Ir a /assets → Create Asset
   ├─ Mint: TokenMintABC...
   ├─ Product type: "Electronics"
   ├─ Custodio inicial: Wallet A
   └─ Estado resultante: IN_CUSTODY

3. HANDOFF → WALLET B (salida del almacén)
   ├─ /assets/:id → Handoff
   ├─ Nueva wallet: Wallet B
   ├─ Ubicación: "Almacén Central, Bogotá"
   └─ Estado resultante: IN_TRANSIT

4. MARK ARRIVED (llegó al distribuidor)
   ├─ /assets/:id → Mark Arrived
   ├─ Ubicación: "Centro Distribución, Medellín"
   └─ Estado resultante: IN_CUSTODY

5. MARK LOADED (cargado a vehículo final)
   ├─ /assets/:id → Mark Loaded
   └─ Estado resultante: LOADED

6. QC CHECK (inspección)
   ├─ /assets/:id → QC Check
   ├─ Result: passed
   └─ Estado resultante: QC_PASSED  (o QC_FAILED si falló)

7. RELEASE (entrega final — irreversible)
   ├─ /assets/:id → Release (admin)
   ├─ Requiere Admin Key
   └─ Estado resultante: RELEASED (fin de cadena)
```

### Diagrama de estados

```
                  create
   ───────────────────────────► IN_CUSTODY
                                    │
                    handoff         │  arrived
                  ◄─────────────────┘────────────────►  IN_CUSTODY
                  │                                          │
             IN_TRANSIT                                      │
                  │                                      loaded
              arrived│                                       │
                  │                                          ▼
                  └─────────────────────────────────►   LOADED
                                                           │
                                                        qc_check
                                                           │
                                           ┌──────────────┴──────────────┐
                                           ▼                             ▼
                                       QC_PASSED                    QC_FAILED
                                           │                             │
                                           └──────────┬──────────────────┘
                                                      │ release (admin)
                                                      ▼
                                                   RELEASED
                                               (fin, inmutable)
```

> **Nota:** El backend impone estas transiciones. Si intentas una acción inválida para el estado actual, recibirás un error 422 y el frontend mostrará el mensaje correspondiente.

---

## 6. Admin Key — acciones restringidas

Algunas operaciones requieren una clave de administrador para preveniraccesos no autorizados.

### Configurar la Admin Key

1. Haz click en el ícono de llave (🔑) en la **Topbar** (barra superior derecha)
2. Escribe o pega tu `TRACE_ADMIN_KEY` (la misma configurada en el backend)
3. Click en **Save** — se guarda en `localStorage` del navegador
4. El ícono cambia a verde cuando hay una clave activa

```
                              ┌────────────────────────────┐
Topbar:  Assets ──────────── │ 🔑 Admin Key               │
                              │                            │
                              │ ┌──────────────────────┐   │
                              │ │ my-secret-key    👁  │   │
                              │ └──────────────────────┘   │
                              │      [Clear]  [Save]       │
                              └────────────────────────────┘
```

### Acciones que requieren Admin Key

| Acción | Endpoint |
|--------|----------|
| **Release** de un asset | `POST /api/v1/assets/:id/release` |

### ¿Qué pasa si no hay Admin Key?

El modal de Release mostrará una advertencia y enviará la petición sin header `X-Admin-Key`. El backend responderá `403 Forbidden` y el frontend mostrará el error en el modal.

### Seguridad

La Admin Key se guarda en `localStorage`. Para sesiones compartidas o en producción, se recomienda limpiarla al terminar (`Clear` en el diálogo).

---

## 7. Idempotencia en el frontend

**¿Qué es?** Si por algún motivo envías la misma operación dos veces (por ejemplo, doble click o reintento), el sistema no creará el evento dos veces.

**¿Cómo funciona en el frontend?**

Cada vez que se abre un modal de acción (Handoff, Arrived, Loaded, QC), se genera un `UUID v4` único como `Idempotency-Key`. Este UUID se envía en el header de la petición HTTP.

```
POST /api/v1/assets/:id/handoff
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
```

Si la petición se envía de nuevo con el mismo UUID (dentro de las 24 horas), el backend devuelve el mismo resultado sin crear un evento duplicado.

> Si el modal se cierra y se vuelve a abrir, se genera un nuevo UUID, lo que permite reintentos legítimos.

---

## 8. Estados de un asset

| Estado | Badge | Descripción |
|--------|-------|-------------|
| `in_custody` | 🔵 In Custody | Asset bajo custodia, sin movimiento activo |
| `in_transit` | 🟡 In Transit | En tránsito entre custodios |
| `loaded` | 🟣 Loaded | Cargado en vehículo/contenedor |
| `qc_passed` | 🟢 QC Passed | Pasó la inspección de calidad |
| `qc_failed` | 🔴 QC Failed | Falló la inspección de calidad |
| `released` | ⚫ Released | Liberado del sistema (fin de cadena) |

---

## 9. Anchoring en Solana — qué significa cada badge

Cada evento de custodia se intenta registrar en la blockchain de Solana de forma asíncrona.

| Badge | Color | Significado |
|-------|-------|------------|
| **Anchored** | 🟢 Verde | Evento registrado en Solana. La firma es verificable on-chain. |
| **Pending** | 🟡 Amarillo | En cola, esperando ser procesado por el worker. |
| **Queued** | 🔵 Azul | Encolado en Redis, el worker lo tomará pronto. |
| **Failed** | 🔴 Rojo | El intento falló. Se muestra el error y un botón **Retry**. |
| **Simulated** | ⚡ Naranja | El backend está en modo simulación. La firma empieza con `SIM_`. |

### ¿Por qué puede fallar el anchoring?

- El RPC de Solana no está disponible
- No hay saldo (SOL) en la wallet firmante
- Timeout de red

### Retry de anchoring

En el timeline, los eventos con anchoring fallido muestran el error y un botón **Retry**. Al hacer click se llama a `POST /api/v1/assets/:id/events/:eventId/anchor` y el worker intenta nuevamente.

---

## 10. Preguntas frecuentes

**¿Por qué el handoff me da error?**
La wallet destino debe estar registrada (`/wallets`) y en estado **active**. Verifica que existe y no está suspendida o revocada.

**¿Por qué no veo el evento recién creado?**
El timeline se refresca automáticamente cada 15 segundos. Puedes forzar la recarga con el botón ↺ en la Topbar.

**¿Por qué el badge de Solana sigue en "Pending"?**
El anchoring es asíncrono — el worker de ARQ lo procesa en segundo plano. En producción suele tardar unos segundos. Si lleva mucho tiempo, revisa el estado del sistema en `/system`.

**¿Cómo sé si el sistema está en modo simulación?**
Los eventos anclados mostrarán el badge `⚡ Simulated` en lugar de una firma real. También puedes verificar en `/system → Transaction Status` — las firmas `SIM_*` son simuladas.

**¿Puedo deshacer un release?**
No. El estado `released` es final e irreversible. El evento queda registrado en la cadena de custodia con la razón del release.

**¿Los datos del frontend están en tiempo real?**
Casi. TanStack Query mantiene un caché con 30 segundos de validez. El timeline de eventos se refresca cada 15 segundos automáticamente para capturar actualizaciones de anchoring.

**¿Qué pasa si cierro el navegador a mitad de una operación?**
- Si ya se envió la petición HTTP, el evento fue creado en el backend (con su idempotency key). Al volver, verás el nuevo estado.
- Si no se había enviado, no pasa nada — el formulario se limpió.

**¿Dónde se guarda la Admin Key?**
En `localStorage` del navegador, bajo la clave `trace-admin-store`. No se envía al servidor hasta que ejecutas una acción que la requiere.

---

## Stack tecnológico

| Tecnología | Versión | Uso |
|------------|---------|-----|
| React | 19 | Framework UI |
| Vite | 6 | Build tool y dev server |
| TypeScript | 5 (strict) | Tipado estático |
| TanStack Query | 5 | Caché y sincronización de datos |
| Zustand | 5 | Estado global (Admin Key, toasts) |
| React Router | 7 | Navegación SPA |
| React Hook Form | 7 | Formularios |
| Zod | 3 | Validación de schemas |
| Tailwind CSS | 3 | Estilos |
| lucide-react | — | Iconos |
| date-fns | 4 | Formateo de fechas |

---

*Frontend de Trace — Manual de Usuario v1.0*
