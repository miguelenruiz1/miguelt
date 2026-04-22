# trace-service — Documentación Técnica

Microservicio FastAPI de cadena de custodia con anclaje Solana.

---

## Índice

1. [Stack tecnológico](#stack-tecnológico)
2. [Arquitectura interna](#arquitectura-interna)
3. [Estructura de carpetas](#estructura-de-carpetas)
4. [Modelo de datos](#modelo-de-datos)
5. [Encadenamiento hash](#encadenamiento-hash)
6. [Idempotencia](#idempotencia)
7. [Worker ARQ](#worker-arq)
8. [Cliente Solana](#cliente-solana)
9. [Circuit breaker](#circuit-breaker)
10. [Configuración](#configuración)
11. [Correr en desarrollo](#correr-en-desarrollo)
12. [Tests](#tests)
13. [Migraciones](#migraciones)
14. [Endpoints completos](#endpoints-completos)
15. [Decisiones de diseño](#decisiones-de-diseño)

---

## Stack tecnológico

| Componente | Tecnología | Motivo |
|---|---|---|
| Framework | FastAPI 0.111 + Uvicorn + uvloop | Async nativo, mayor throughput que Starlette solo |
| Validación | Pydantic v2 | 5-10x más rápido que v1 por core Rust |
| ORM | SQLAlchemy 2.0 async + asyncpg | Pool async real, sin bloquear el event loop |
| Base de datos | PostgreSQL 16 | JSONB, arrays, `SELECT FOR UPDATE`, ACID |
| Cache / Colas | Redis 7 + hiredis | hiredis = parser C, ~3x más rápido que parser Python |
| Worker | **ARQ** (no Celery) | Nativo asyncio, cero eventlet/gevent, API limpia |
| HTTP client | httpx (HTTP/2 ready) | Pool de conexiones reutilizable, async |
| Blockchain | solders + solana-py | solders = bindings Rust (Keypair, Tx building) |
| Logging | structlog + JSON | Structured logging con correlation-id |
| Resiliencia | tenacity + circuit breaker propio | Reintentos con jitter, no bloquea el loop |
| Métricas | prometheus-fastapi-instrumentator | `/metrics` estándar Prometheus |
| Migraciones | Alembic (async-compatible) | `run_sync` para compatibilidad asyncio |

---

## Arquitectura interna

### Capas de la aplicación

```
HTTP Request
     │
     ▼
┌─────────────────────────────────────┐
│            Middlewares              │
│  CorrelationIdMiddleware            │  → inyecta X-Correlation-Id
│  IdempotencyKeyMiddleware           │  → expone Idempotency-Key en request.state
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│            API Routers              │
│  /health  /registry  /assets        │
│  /solana                            │
│                                     │
│  • Lee idempotency_key del state    │
│  • Llama a Services                 │
│  • Llama a enqueue_anchor() DESPUÉS │
│    del commit                       │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│            Services                 │
│  RegistryService                    │
│  CustodyService                     │  ← lógica de negocio, validaciones
│  AnchorService                      │  ← solo encola, no ancla directamente
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│          Repositories               │
│  RegistryRepository                 │
│  AssetRepository                    │  ← SELECT FOR UPDATE aquí
│  CustodyEventRepository             │
└─────────────────────────────────────┘
     │
     ▼
┌──────────────────┐  ┌──────────────┐
│   PostgreSQL     │  │    Redis     │
│  (asyncpg pool)  │  │  (idempotency│
│                  │  │   + ARQ)     │
└──────────────────┘  └──────────────┘
```

### Flujo de creación de evento (ruta crítica)

```
POST /assets/{id}/events/handoff
           │
           ▼
1. Middleware: bind correlation_id al contexto structlog
2. Middleware: exponer Idempotency-Key en request.state
           │
           ▼
3. Router: check idempotency (Redis SET NX)
   → si cacheado: return 200 con respuesta anterior
           │
           ▼
4. CustodyService.handoff():
   a. SELECT FOR UPDATE en assets → bloquea fila
   b. assert to_wallet en allowlist activa
   c. assert asset no está RELEASED
   d. compute_event_hash(prev_hash=asset.last_event_hash, ...)
   e. INSERT custody_events (anchored=false)
   f. UPDATE assets (state, custodian, last_event_hash)
   g. flush() — no commit aún
           │
           ▼
5. Router: await db.commit()  ← transacción completa
           │
           ▼
6. Router: enqueue_anchor(event.id) → Redis ARQ
           │
           ▼
7. Router: guarda respuesta en Redis (idempotency)
           │
           ▼
8. Return 201 {asset, event{anchored:false, event_hash:...}}


                 En paralelo, el Worker:
                 ┌──────────────────────┐
                 │ anchor_event(event_id)│
                 │  → send_memo(hash)   │
                 │  → UPDATE anchored=T │
                 └──────────────────────┘
```

---

## Estructura de carpetas

```
trace-service/
│
├── Dockerfile                   # multi-stage: builder (poetry) + runtime (slim)
├── pyproject.toml               # dependencias con Poetry
├── alembic.ini                  # configuración Alembic
│
├── alembic/
│   ├── env.py                   # entorno async-compatible
│   ├── script.py.mako           # template de migraciones
│   └── versions/
│       └── 001_initial_schema.py
│
├── app/
│   ├── main.py                  # factory, lifespan, middlewares, routers
│   │
│   ├── core/
│   │   ├── settings.py          # pydantic-settings, todas las env vars
│   │   ├── logging.py           # structlog JSON con correlation-id
│   │   ├── errors.py            # excepciones de dominio + handlers FastAPI
│   │   └── middleware.py        # CorrelationId + IdempotencyKey middlewares
│   │
│   ├── api/
│   │   └── routers/
│   │       ├── health.py        # GET /health, GET /ready
│   │       ├── registry.py      # CRUD wallets allowlist
│   │       ├── custody.py       # assets + todos los eventos de custodia
│   │       └── solana.py        # debug: account info, tx status
│   │
│   ├── domain/
│   │   ├── types.py             # enums: WalletStatus, AssetState, EventType
│   │   └── schemas.py           # Pydantic v2: request/response models
│   │
│   ├── services/
│   │   ├── registry_service.py  # lógica wallets: register, update, assert_active
│   │   ├── custody_service.py   # lógica activos y eventos: create, handoff, qc...
│   │   └── anchor_service.py    # enqueue_anchor() → ARQ pool
│   │
│   ├── repositories/
│   │   ├── registry_repo.py     # queries SQL wallets
│   │   └── custody_repo.py      # queries SQL assets y events (incl. FOR UPDATE)
│   │
│   ├── clients/
│   │   └── solana_client.py     # RPC client + circuit breaker + sim mode
│   │
│   ├── db/
│   │   ├── base.py              # DeclarativeBase
│   │   ├── models.py            # ORM: RegistryWallet, Asset, CustodyEvent
│   │   ├── session.py           # engine async, session factory, dependency
│   │   └── migrations_helpers.py
│   │
│   └── utils/
│       ├── json_canonical.py    # serialización JSON determinista
│       ├── hashing.py           # SHA-256 del evento
│       └── idempotency.py       # IdempotencyStore (Redis)
│
├── worker/
│   └── worker_main.py           # ARQ WorkerSettings, anchor_event job, cron sweep
│
└── tests/
    ├── conftest.py              # fixtures: engine, db_session, client, helpers
    ├── test_allowlist.py        # 6 tests allowlist enforcement
    ├── test_custody_flow.py     # 5 tests flujo completo + hash chain
    ├── test_concurrency.py      # 2 tests SELECT FOR UPDATE
    └── test_idempotency.py      # 4 tests Idempotency-Key deduplication
```

---

## Modelo de datos

### `registry_wallets`

```sql
CREATE TABLE registry_wallets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_pubkey   TEXT NOT NULL,
    tags            TEXT[] NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'active',  -- active|suspended|revoked
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_registry_wallets_pubkey UNIQUE (wallet_pubkey)
);

CREATE INDEX ix_registry_wallets_status ON registry_wallets(status);
```

### `assets`

```sql
CREATE TABLE assets (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_mint               TEXT NOT NULL,          -- identificador NFT/activo
    product_type             TEXT NOT NULL,
    metadata                 JSONB NOT NULL DEFAULT '{}',
    current_custodian_wallet TEXT NOT NULL,          -- quién lo tiene ahora
    state                    TEXT NOT NULL,          -- ver AssetState enum
    last_event_hash          TEXT,                   -- hash del último evento

    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_assets_mint UNIQUE (asset_mint)
);

CREATE INDEX ix_assets_product_type ON assets(product_type);
CREATE INDEX ix_assets_custodian    ON assets(current_custodian_wallet);
CREATE INDEX ix_assets_state        ON assets(state);
```

### `custody_events` (append-only)

```sql
CREATE TABLE custody_events (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id         UUID NOT NULL REFERENCES assets(id) ON DELETE RESTRICT,
    event_type       TEXT NOT NULL,     -- CREATED|HANDOFF|ARRIVED|LOADED|QC|RELEASED
    from_wallet      TEXT,
    to_wallet        TEXT,
    timestamp        TIMESTAMPTZ NOT NULL,
    location         JSONB,
    data             JSONB NOT NULL DEFAULT '{}',
    prev_event_hash  TEXT,             -- null solo en CREATED
    event_hash       TEXT NOT NULL,    -- SHA-256 del evento

    -- Anclaje Solana
    solana_tx_sig    TEXT,
    anchored         BOOLEAN NOT NULL DEFAULT false,
    anchor_attempts  INTEGER NOT NULL DEFAULT 0,
    anchor_last_error TEXT,

    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_custody_events_hash UNIQUE (event_hash)
);

-- Consultas frecuentes
CREATE INDEX ix_custody_events_asset_timestamp
    ON custody_events(asset_id, timestamp DESC);
CREATE INDEX ix_custody_events_anchored
    ON custody_events(anchored);
```

**Nota de diseño**: `custody_events` es append-only por contrato. No existen rutas PUT/DELETE sobre eventos. Las actualizaciones de `anchored`/`solana_tx_sig` son excepciones controladas desde el worker.

---

## Encadenamiento hash

### Algoritmo

```python
def compute_event_hash(asset_id, event_type, from_wallet, to_wallet,
                       timestamp, location, data, prev_event_hash) -> str:
    payload = {
        "asset_id":        str(asset_id),
        "event_type":      event_type,
        "from_wallet":     from_wallet,       # None → JSON null
        "to_wallet":       to_wallet,
        "timestamp":       timestamp.isoformat(),
        "location":        location,
        "data":            data,
        "prev_event_hash": prev_event_hash,
    }
    canonical = json.dumps(payload, sort_keys=True,
                           separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
```

### Propiedades del canonical JSON

- Claves ordenadas lexicográficamente (recursivo en dicts anidados)
- Sin espacios (`separators=(',', ':')`)
- `ensure_ascii=True` para reproducibilidad byte-a-byte entre plataformas
- `None` → `null` (no omitido), garantiza determinismo

### Verificación de la cadena

Para verificar que el evento `E` es auténtico:

1. Obtener todos los eventos del activo ordenados por `created_at`.
2. Para cada evento, recalcular `compute_event_hash(...)` con los datos del evento y el `prev_event_hash` del registro anterior.
3. Si el hash calculado == `event_hash` almacenado, el evento no fue alterado.
4. Si algún hash no coincide, la cadena está corrompida.

---

## Idempotencia

### Implementación

Usa Redis con el patrón **SET NX** (Set if Not eXists):

```
1. GET idem:{sha256(namespace:key)}
   ├─ HIT  → return cached_response (200)
   └─ MISS →

2. SET idem:{key} "__PROCESSING__" EX 60 NX
   ├─ OK    → proceso adquirido, ejecutar handler
   └─ FAIL  → otro worker está procesando → 409

3. Ejecutar lógica de negocio
   ├─ OK  → SET idem:{key} {json_response} EX TTL
   └─ ERR → DEL idem:{key}, propagar excepción

TTL por defecto: 86400s (24h), configurable con IDEMPOTENCY_TTL
```

### Namespaces

Cada endpoint usa su propio namespace para evitar colisiones de keys:

| Endpoint | Namespace |
|---|---|
| POST /registry/wallets | `register_wallet` |
| POST /assets | `create_asset` |
| POST /assets/{id}/events/handoff | `handoff:{asset_id}` |
| POST /assets/{id}/events/release | `release:{asset_id}` |

### Clave Redis

```python
key = f"idem:{sha256(f'{namespace}:{idempotency_key}')}"
```

El SHA-256 normaliza claves de longitud variable y permite cualquier carácter.

---

## Worker ARQ

### ¿Por qué ARQ y no Celery?

| Criterio | ARQ | Celery |
|---|---|---|
| Runtime | asyncio nativo | eventlet/gevent (monkey-patch) |
| Compatibilidad Python 3.11+ | Total | Problemas con gevent |
| Overhead | Mínimo (Redis directo) | Brokers complejos |
| API async | Primera clase | Workaround |
| Dependencias | ~0 | Kombu, billiard, vine, ... |

### Ciclo de vida de un job

```
anchor_event(ctx, event_id: str):
    1. SELECT custody_events WHERE id = event_id
    2. Si anchored = true → return (ya hecho)
    3. solana_client.send_memo(event.event_hash)
       ├─ OK  → UPDATE SET anchored=true, solana_tx_sig=...
       └─ ERR → UPDATE SET anchor_attempts+=1, anchor_last_error=...
                raise → ARQ reintenta con backoff exponencial
```

### Backoff exponencial con jitter

```python
delay = min(2 ** attempt, 300)  # max 5 minutos
jitter = random.uniform(0, delay * 0.2)
total_delay = delay + jitter
```

| Intento | Delay base | Con jitter (aprox) |
|---------|------------|---------------------|
| 1 | 2s | 2.0 – 2.4s |
| 2 | 4s | 4.0 – 4.8s |
| 3 | 8s | 8.0 – 9.6s |
| 4 | 16s | 16.0 – 19.2s |
| 5 | 32s | 32.0 – 38.4s |

### Cron de barrido (sweep)

Cada 5 minutos, el worker barre `custody_events WHERE anchored = false` y re-encola eventos que no llegaron a la cola (reinicio del worker, caída de Redis, etc.). Respeta `anchor_attempts < ANCHOR_MAX_RETRIES`.

### WorkerSettings relevantes

```python
class WorkerSettings:
    functions    = [anchor_event]
    cron_jobs    = [cron(sweep_pending_anchors, minute={0,5,10,...})]
    queue_name   = "anchor"
    max_jobs     = 20        # concurrencia del worker
    job_timeout  = 300       # 5 min por job
    max_tries    = 5         # configurable por ANCHOR_MAX_RETRIES
    keep_result  = 3600      # mantiene resultado 1h en Redis
```

---

## Cliente Solana

### Config blockchain (CLAUDE.md #0.bis)

La simulación fue eliminada — todo va contra Solana real (devnet por defecto)
vía Helius. Config mínima en `.env`:

```bash
SOLANA_NETWORK=devnet
SOLANA_KEYPAIR=<base58 64 bytes>  # o path a archivo JSON
HELIUS_API_KEY=<key de https://dev.helius.xyz>
```

Si falta `SOLANA_KEYPAIR` o `HELIUS_API_KEY`, `trace-api` **falla al
arrancar** con `BlockchainConfigError` — no hay fallback silencioso.

### Envío de memo

```python
# Programa de Memo en Solana
MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"

# Instrucción:
Instruction(
    program_id = MEMO_PROGRAM_ID,
    data       = event_hash.encode('utf-8'),  # el hash SHA-256 como texto
    accounts   = [AccountMeta(keypair.pubkey(), is_signer=True, is_writable=False)]
)
```

El contenido del memo es el `event_hash` del evento (64 bytes hex). Cualquiera puede leerlo en Solana Explorer buscando el `solana_tx_sig`.

### Sin fallback

Si falta `SOLANA_KEYPAIR` o `HELIUS_API_KEY`, el servicio lanza
`BlockchainConfigError` al construir el provider — no se degrada a
simulación (CLAUDE.md #0.bis).

---

## Circuit Breaker

Implementación propia con tres estados y asyncio.Lock para thread-safety en el event loop:

```
Estado CLOSED (normal)
  → Cada falla incrementa failure_count
  → Si failure_count >= threshold (default: 5) → pasa a OPEN

Estado OPEN (rechaza rápido)
  → Levanta CircuitOpenError inmediatamente sin llamar al RPC
  → Si elapsed >= recovery_timeout (default: 60s) → pasa a HALF_OPEN

Estado HALF_OPEN (probando recuperación)
  → Deja pasar UNA llamada
  → Si OK  → vuelve a CLOSED y resetea contador
  → Si ERR → vuelve a OPEN
```

Cuando el circuito está OPEN, el worker captura `CircuitOpenError`, incrementa `anchor_attempts` y ARQ reintenta más tarde. El API puede seguir respondiendo a peticiones normalmente (el anclaje es asíncrono).

---

## Configuración

Todas las variables se leen de `.env` o del entorno. Definidas en `app/core/settings.py` con validación Pydantic.

```bash
# ─── Base de datos ───────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://trace:tracepass@postgres:5432/tracedb
DB_POOL_SIZE=20          # conexiones en pool
DB_MAX_OVERFLOW=40       # conexiones extra bajo carga pico
DB_POOL_TIMEOUT=30       # segundos esperando conexión libre
DB_POOL_RECYCLE=1800     # reciclar conexiones cada 30min
DB_ECHO=false            # true = loguear todas las queries SQL

# ─── Redis ───────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0      # DB 0: idempotency
ARQ_REDIS_URL=redis://redis:6379/1  # DB 1: ARQ queue
IDEMPOTENCY_TTL=86400               # TTL en segundos (24h)

# ─── Solana ──────────────────────────────────────────────────
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_KEYPAIR=                     # base58 o path a JSON
SOLANA_COMMITMENT=confirmed         # processed|confirmed|finalized
SOLANA_TIMEOUT=30.0
SOLANA_CIRCUIT_BREAKER_THRESHOLD=5
SOLANA_CIRCUIT_BREAKER_RECOVERY=60

# ─── Seguridad ───────────────────────────────────────────────
TRACE_ADMIN_KEY=change-me-in-production

# ─── Aplicación ──────────────────────────────────────────────
LOG_LEVEL=INFO         # DEBUG|INFO|WARNING|ERROR
DEBUG=false

# ─── Worker ──────────────────────────────────────────────────
ANCHOR_MAX_RETRIES=5
ANCHOR_RETRY_DELAY=2.0
ANCHOR_QUEUE_NAME=anchor
```

---

## Correr en desarrollo

### Con Docker Compose (recomendado)

```bash
# 1. Configurar
cp .env.example ../.env

# 2. Levantar todo
cd ..
docker compose up --build

# 3. Probar
curl http://localhost:8000/health
open http://localhost:8000/docs    # Swagger UI interactivo
```

### Sin Docker (para iterar rápido)

```bash
# Prereqs: Python 3.11+, Poetry, Postgres y Redis locales

# Instalar dependencias
poetry install

# Variables de entorno para desarrollo local
export DATABASE_URL="postgresql+asyncpg://trace:tracepass@localhost:5432/tracedb"
export REDIS_URL="redis://localhost:6379/0"
export ARQ_REDIS_URL="redis://localhost:6379/1"
export TRACE_ADMIN_KEY=dev-admin-key

# Correr migraciones
alembic upgrade head

# Iniciar API (reload automático)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# En otra terminal: iniciar worker
python -m worker.worker_main
```

---

## Tests

### Prerrequisitos

- Postgres corriendo en `localhost:5432` con DB `tracedb_test`
- Redis corriendo en `localhost:6379`

```bash
# Levantar solo infraestructura
docker compose up postgres redis -d

# Crear DB de test
docker exec trace-postgres psql -U trace -c "CREATE DATABASE tracedb_test;"

# Correr todos los tests
TEST_DATABASE_URL="postgresql+asyncpg://trace:tracepass@localhost:5432/tracedb_test" \
  poetry run pytest tests/ -v

# Con cobertura
poetry run pytest tests/ -v --cov=app --cov-report=term-missing
```

### Tests incluidos

| Archivo | Qué prueba |
|---|---|
| `test_allowlist.py` | Wallets no allowlisted, suspendidas, revocadas, reactivadas |
| `test_custody_flow.py` | Flujo completo, hash chain, doble mint, release sin key |
| `test_concurrency.py` | SELECT FOR UPDATE, handoffs simultáneos |
| `test_idempotency.py` | Deduplication por Idempotency-Key en wallets, assets, handoffs |

### Patrón de fixtures

```python
# Cada test obtiene su propia transacción que se rollback al finalizar
# → tests independientes, sin limpiar datos manualmente

@pytest_asyncio.fixture
async def db_session(engine):
    async with factory() as session:
        yield session
        await session.rollback()  # ← limpieza automática

# El cliente HTTP apunta al mismo session → todo en memoria, sin commit global
app.dependency_overrides[get_db_session] = lambda: db_session

# enqueue_anchor está mockeado → no necesita Redis real
with patch("app.services.anchor_service.enqueue_anchor", AsyncMock()):
    yield client
```

---

## Migraciones

```bash
# Crear nueva migración (auto-detect desde modelos)
alembic revision --autogenerate -m "descripcion del cambio"

# Aplicar migraciones pendientes
alembic upgrade head

# Ver estado actual
alembic current

# Revertir último step
alembic downgrade -1

# Ver historial
alembic history --verbose
```

**El API aplica migraciones automáticamente al arrancar** (`alembic upgrade head` en el CMD del Dockerfile).

---

## Endpoints completos

### Registry

| Método | Path | Idempotente | Descripción |
|--------|------|-------------|-------------|
| `POST` | `/api/v1/registry/wallets` | ✅ | Registrar wallet en allowlist |
| `GET` | `/api/v1/registry/wallets` | — | Listar wallets (filtros: tag, status) |
| `GET` | `/api/v1/registry/wallets/{id}` | — | Obtener wallet por ID |
| `PATCH` | `/api/v1/registry/wallets/{id}` | — | Actualizar tags o status |

### Assets y Eventos

| Método | Path | Idempotente | Admin | Descripción |
|--------|------|-------------|-------|-------------|
| `POST` | `/api/v1/assets` | ✅ | — | Crear activo + evento CREATED |
| `GET` | `/api/v1/assets` | — | — | Listar activos (filtros) |
| `GET` | `/api/v1/assets/{id}` | — | — | Obtener activo |
| `GET` | `/api/v1/assets/{id}/events` | — | — | Historial de eventos |
| `POST` | `/api/v1/assets/{id}/events/handoff` | ✅ | — | Transferir custodia |
| `POST` | `/api/v1/assets/{id}/events/arrived` | — | — | Confirmar llegada |
| `POST` | `/api/v1/assets/{id}/events/loaded` | — | — | Marcar como cargado |
| `POST` | `/api/v1/assets/{id}/events/qc` | — | — | Registrar control de calidad |
| `POST` | `/api/v1/assets/{id}/events/release` | ✅ | ✅ | Liberar a wallet externa |
| `POST` | `/api/v1/assets/{id}/events/{eid}/anchor` | — | — | Reintentar anclaje Solana |

### Debug Solana

| Método | Path | Descripción |
|--------|------|-------------|
| `GET` | `/api/v1/solana/account/{pubkey}` | Info de cuenta Solana |
| `GET` | `/api/v1/solana/tx/{sig}` | Estado de transacción |

### Sistema

| Método | Path | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/ready` | Readiness probe (DB + Redis) |
| `GET` | `/metrics` | Métricas Prometheus |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc UI |

---

## Decisiones de diseño

### ¿Por qué commit explícito en el router y no auto-commit?

El router hace `await db.commit()` **antes** de llamar a `enqueue_anchor()`. Esto garantiza que cuando el worker procese el job, el evento ya esté visible en la DB. Si el orden fuera inverso (primero encolar, luego commit), el worker podría intentar leer un evento que aún no existe.

### ¿Por qué `metadata_` en el modelo y no `metadata`?

`DeclarativeBase` expone `metadata` como atributo de clase (instancia de `MetaData` de SQLAlchemy). Usar el mismo nombre en una columna genera conflicto en tiempo de definición. Se usa `metadata_` como atributo Python con alias de columna `"metadata"` a nivel de SQL. Pydantic v2 resuelve esto con `AliasChoices("metadata_", "metadata")`.

### ¿Por qué no validar `from_wallet` en HANDOFF?

En HANDOFF, `from_wallet` siempre es `asset.current_custodian_wallet` — se toma del estado de la DB, no del cliente. Esto elimina un vector de ataque donde un cliente podría falsificar el remitente.

### ¿Por qué Redis DB separadas para idempotencia (0) y ARQ (1)?

Para poder hacer `FLUSHDB` en la DB de ARQ en tests/staging sin afectar las claves de idempotencia, y viceversa. Separación de concerns a nivel de datos.

### ¿Por qué uvloop?

uvloop reemplaza el event loop estándar de Python con una implementación en C/Cython basada en libuv (la misma que usa Node.js). En benchmarks, reduce la latencia del event loop un 2-4x en operaciones I/O intensivas. Se activa con `--loop uvloop` en el comando uvicorn.

### ¿Por qué `expire_on_commit=False` en la session factory?

Después de un `commit()`, SQLAlchemy por defecto expira todos los atributos de los objetos cargados (los marca como "stale") para forzar una recarga en el próximo acceso. En contextos async con múltiples `await` después del commit, esto puede causar accesos fuera del contexto de la sesión. `expire_on_commit=False` evita esto, dejando los objetos en su último estado leído.
