# CLAUDE.md — Reglas de trabajo para Claude en este repo

Estas reglas existen porque ya cometí errores concretos en este proyecto y el
usuario perdió tiempo. Son obligatorias, no sugerencias. Si alguna no aplica a
una tarea puntual, lo digo explícitamente antes de saltármela.

## 0. Regla #0 — NUNCA tocar GCP. Producción vive en Hetzner.

**Prohibido** ejecutar cualquier comando `gcloud ...`, `gsutil ...`,
`gke ...`, abrir `console.cloud.google.com`, o inspeccionar recursos en el
proyecto `trace-log`. La migración GCP → Hetzner terminó en abril 2026 y GCP
quedó apagado. Si veo código, scripts o docs que todavía apunten a GCP, los
señalo al usuario pero no los resucito.

**Toda referencia a deploy apunta a Hetzner Cloud:**

- **Consola**: https://console.hetzner.com/
- **Host de producción**: `root@62.238.5.1` (Hetzner CAX11 ARM64, Helsinki)
- **URL pública actual**: http://62.238.5.1 (gateway en puerto 80 → 9000)
- **Compose de producción**: `deploy/docker-compose.production.yml`

**Flujo de deploy (reemplaza todo lo que decía "gcloud" en reglas viejas):**

```bash
# 1. Push local → origin/main (tras seguir el flow #11 de branches)
git push origin main

# 2. SSH al VM y actualizar código
ssh root@62.238.5.1 'cd /opt/trace && git pull'

# 3. Rebuild solo los servicios afectados (deducir de archivos modificados)
ssh root@62.238.5.1 \
  'cd /opt/trace && docker compose -f deploy/docker-compose.production.yml build <service> && \
   docker compose -f deploy/docker-compose.production.yml up -d <service>'

# 4. Si cambió cualquier backend detrás del gateway nginx, reiniciar el gateway
ssh root@62.238.5.1 \
  'cd /opt/trace && docker compose -f deploy/docker-compose.production.yml restart gateway'

# 5. Smoke test (regla #14, adaptada): curl + logs
ssh root@62.238.5.1 'docker compose -f /opt/trace/deploy/docker-compose.production.yml \
  logs --since=5m <service> | grep -iE "error|exception|traceback"'
curl -sI http://62.238.5.1/
```

**Deploys de solo-docs o solo-scripts-de-QA** (ej: `*.md`, `qa/*.py`) **NO
requieren rebuild**. Basta con `git pull` en el VM — no afecta runtime.

Si una regla más abajo (ej. #13 sobre `gcloud builds submit`, #16 sobre APIs
GCP) contradice esta, **gana la #0**. Esas reglas quedaron obsoletas con la
migración pero las dejo como historial de errores pasados.


## 0.bis. Blockchain SIEMPRE real. Simulación eliminada del código.

La plataforma **no puede** correr con provider simulado en ningún ambiente
que el usuario vea — local, staging, producción. Todo wallet, todo mint,
todo evento de custodia se firma contra **Solana real (devnet via Helius
por defecto)**.

Motivo histórico: una wallet simulada producía pubkeys tipo `sim1c632e09...`
que no existen en Solana, no son verificables en Solscan, y rompen la
narrativa fundamental de Trace ("trazabilidad anclada en blockchain"). **Un
demo con datos simulados es un demo que miente** — incompatible con lo que
se le vende al BID, a clientes o a cualquier evaluador técnico.

**Estado actual del código (lo que ya está hecho):**

- `trace-service/app/clients/simulation_provider.py` — **eliminado**.
- `SOLANA_SIMULATION` — removido de `settings.py`, `.env.example`,
  `deploy/env.production.template`, `deploy/docker-compose.production.yml`.
- `SolanaClient.generate_wallet()`, `try_airdrop()`, `send_memo()`,
  `get_account_info()`, `get_signature_status()` — sin ramas `if _simulation`.
- `SolanaClient.mint_logistics_asset()` — borrado (era sólo stub simulado).
- `provider_factory.get_blockchain_provider()` — retorna **siempre**
  `HeliusProvider`. Si falta `HELIUS_API_KEY` o `SOLANA_KEYPAIR`,
  **`BlockchainConfigError` al arrancar** (no hay fallback).

**Reglas firmes (lo que debo respetar a futuro):**

- Nunca reintroducir una env var tipo `SOLANA_SIMULATION` o un
  `SimulationProvider`, aunque sea para "dev rápido". Si hace falta un
  mock para tests, va como fixture pytest que monkeypatch-ea el provider,
  no como flag global de la app.
- `HELIUS_API_KEY` y `SOLANA_KEYPAIR` son **requeridos** en cualquier
  ambiente (incluido local de dev). Valores de ejemplo en
  `.env.example` apuntan al flujo real.
- `SOLANA_NETWORK=devnet` por default (cambiar a `mainnet-beta` solo con
  decisión explícita del usuario en la misma sesión).
- Si en la DB veo `registry_wallets.wallet_pubkey LIKE 'sim%'`, son
  residuos de un bug anterior. Borrarlos con
  `DELETE FROM registry_wallets WHERE wallet_pubkey LIKE 'sim%';` antes
  de demoear.

**Cómo verificar rápido en cualquier ambiente:**

```bash
# 1. Env del trace-api debe tener keys seteadas (la var SOLANA_SIMULATION ya
#    no existe — si aparece en algún lado, es un remanente a limpiar).
docker exec trace-api bash -c \
  'echo HELIUS=${#HELIUS_API_KEY} KP=${#SOLANA_KEYPAIR}'
# Esperado: HELIUS=36 KP=88 (aproximado, según el keypair/key usados).

# 2. Provider activo tiene que ser HeliusProvider (única opción posible
#    tras el refactor).
docker exec trace-api python -c \
  'from app.clients.provider_factory import get_blockchain_provider;
   p = get_blockchain_provider(); assert type(p).__name__ == "HeliusProvider",
   f"P0: provider activo es {type(p).__name__}"'

# 3. Sanity: wallets en DB no deben empezar con "sim".
docker exec trace-postgres psql -U trace -d tracedb -At -c \
  "SELECT COUNT(*) FROM registry_wallets WHERE wallet_pubkey LIKE 'sim%'"
# Esperado: 0.
```

Si cualquiera de los tres falla, es bug P0 y se arregla antes de continuar
con otra cosa.


## 1. Antes de escribir SQL crudo: leer el esquema

Si voy a usar `text("SELECT ...")`, `db.execute(text(...))` o cualquier SQL
literal en strings, **primero** verifico los nombres reales de tablas y
columnas con uno de estos:

- Leer el modelo SQLAlchemy correspondiente en `*/app/db/models/*.py`.
- `docker exec <postgres-container> psql -U <user> -d <db> -c "\d <tabla>"`.

Nunca asumo nombres por analogía con otra tabla (ej: si `purchase_order_lines`
tiene `po_id`, **no** asumo que `sales_order_lines` tiene `so_id` — la columna
real es `order_id`). Este error específico ya pasó.

**Regla más fuerte aún**: si existe un modelo ORM para la tabla, prefiero
`select(Model).where(...)` antes que `text(...)`. El ORM atrapa nombres mal
escritos en tiempo de import; el SQL crudo solo falla en runtime y puede
envenenar la transacción.

## 2. Manejo defensivo en transacciones Postgres

Un `try/except` alrededor de una query Postgres **no protege** las queries
siguientes: cuando una query falla dentro de una transacción, asyncpg marca la
transacción como abortada y todas las queries posteriores lanzan
`InFailedSQLTransactionError` hasta que se haga `ROLLBACK`.

Si tengo varias queries "tentativas" (chequeos de uso, validaciones opcionales,
features experimentales), cada una va dentro de un SAVEPOINT:

```python
try:
    async with db.begin_nested():
        result = await db.execute(text(sql), params)
except Exception:
    result = None  # o el fallback que aplique
```

## 3. Probar endpoints nuevos con curl antes de decir "listo"

Cuando agrego o modifico un endpoint backend, antes de avisarle al usuario que
ya está, hago al menos **una** llamada real con curl al gateway o al servicio.
Aceptable que sea sin auth (espero 401/403) — lo importante es confirmar que
la ruta resuelve, el método existe y no devuelve 500.

Ejemplo mínimo:
```bash
curl -s -o /tmp/out.txt -w "HTTP %{http_code}\n" \
  -X DELETE "http://localhost:9003/api/v1/uom/test-id" \
  -H "X-Tenant-Id: default"
cat /tmp/out.txt
```

Si el endpoint requiere lógica que ya tiene datos en la DB, lo digo y le pido
al usuario que lo pruebe él, pero **nunca** asumo que funcionó solo porque
compiló.

## 4. Después de rebuildear una imagen de un servicio detrás del gateway

`trace-gateway` (nginx) **cachea la IP del upstream**. Cuando recreo cualquier
servicio (`docker compose up -d --build inventory-api`, `user-api`,
`subscription-api`, `trace-service`), el contenedor cambia de IP en la red de
docker y nginx sigue apuntando a la vieja → 502 Bad Gateway.

Después de cualquier rebuild o recreación de un servicio backend, **siempre**:

```bash
docker compose restart gateway
```

Esto se hace incluso si no me lo piden — es parte del flujo de "deployar" el
cambio.

## 5. Migraciones y datos: cuidado con los volúmenes

- Nunca borro volúmenes (`docker volume rm`, `down -v`) sin que el usuario lo
  haya pedido explícitamente en ese mensaje. "Reiniciar el servicio" **no**
  significa "borrar la base".
- Cuando borro un volumen porque me lo pidieron, lo hago apuntando al servicio
  específico (ej: `trace_inventory-postgres-data`), nunca con `down -v` global
  que también arrastra `user-postgres`, `subscription-postgres`, `redis`, etc.
- Después de borrar, levanto el servicio y verifico que las migraciones de
  alembic corrieron OK antes de decir "listo".

## 6. Soft delete y auto-seed: no asumir lo conveniente

- Si una tabla usa soft delete (`is_active=False`), las funciones de
  inicialización/seed deben **reactivar** los registros existentes antes de
  intentar insertar duplicados — o van a chocar contra los UNIQUE constraints.
- Si un endpoint `GET` hace auto-seed cuando ve la tabla vacía, eso es un
  comportamiento "mágico" que confunde al usuario cuando vacía la DB. Por
  defecto, evitarlo. La inicialización debe ser explícita (botón "Inicializar
  X" u endpoint POST `/initialize`).

## 7. Acciones destructivas: confirmar antes

Acciones que requieren confirmación explícita en el mismo mensaje (no vale una
autorización previa para "cosas parecidas"):

- `docker volume rm`, `docker compose down -v`
- `git reset --hard`, `git push --force`, `git branch -D`
- `DROP TABLE`, `TRUNCATE`, `DELETE FROM ... WHERE` sin filtros estrictos
- Modificar/borrar archivos fuera del directorio de trabajo del cambio

Si el usuario dice "vaciá X" puedo asumir que aplica solo a X — no a Y y Z
relacionados.

## 8. Cuando aparece un bug, primero investigar la causa raíz

No hacer "fixes" cosméticos sin entender el porqué. Concretamente:

- Si una query falla, leer el error real (no solo el wrapper de SQLAlchemy).
- Si un container está unhealthy, ver `docker compose logs` antes de
  reiniciarlo.
- Si un endpoint devuelve 502, verificar **upstream y downstream**: ¿el
  servicio está corriendo?, ¿el gateway tiene la IP correcta?, ¿la ruta nginx
  apunta donde corresponde?

## 9. No introducir cambios fuera del alcance pedido

Si me piden arreglar un bug en `UoMPage.tsx`, **no** aprovecho para
"limpiar" otros archivos, renombrar variables, o agregar features que
"quedarían bien". Cada cambio extra es superficie nueva de bugs y dificulta
revisar el diff.

## 10. Reportar honestamente cuando algo no se probó

Si no pude probar end-to-end algo (porque requiere datos, auth, o estado
específico), lo digo explícitamente: *"hice el cambio pero no lo probé contra
la DB con datos reales — confirmá vos antes de cerrar"*. No vendo como
verificado lo que no verifiqué.

## 11. Git flow: feature → develop → staging → main

Este repo sigue un flujo de ramas estricto:

- **`feature/*` o `fix/*`**: ramas de trabajo. Se crean desde `develop`.
- **`develop`**: integración. Los PR de features se mergean aquí.
- **`staging`**: pre-producción. Se mergea `develop` → `staging` para QA.
- **`main`**: producción. Solo se mergea desde `staging` después de validar.

Reglas:
- **Nunca** hacer push directo a `main`, `staging` o `develop`.
- Siempre crear PR para mergear entre ramas.
- Antes de hacer `git push` o crear un commit, **siempre preguntar al
  usuario**: mostrar qué archivos cambiaron, qué queda pendiente, y a
  qué rama se va a subir. No asumir que el usuario quiere pushear.
- Antes de desplegar a GCP, confirmar con el usuario qué servicios se
  van a actualizar y en qué rama está el código.

### 11.bis. Flujo "comitea y despliega": no preguntar lo obvio

Cuando el usuario dice **"comitea y despliega"** (o equivalente directo como
"sube esto a prod", "deploy", "mergea y despliega"), asumir lo siguiente sin
preguntar:

1. **Commit**: incluir TODOS los archivos modificados/untracked salvo:
   - Scripts locales con secretos hardcodeados (JWTs, API keys, passwords).
     Esos quedan fuera y se avisa al usuario en una línea.
   - Archivos en `.gitignore` o claramente temporales.
2. **Branch flow** (regla #11): commitear en la rama actual → push → merge
   `current → develop → staging → main` → push de cada una. Usar las ramas
   que **ya existen** (`git branch -a`); NUNCA crear `master`/`main` si una
   ya existe. Si no existe alguna rama intermedia, saltarla y avisar.
3. **Servicios a desplegar**: deducirlos de los archivos modificados en el
   commit:
   - Cambios en `<service>/app/**` o `<service>/alembic/**` → deployar ese
     servicio.
   - Cambios en `front-trace/**` → deployar `front-trace` (con
     `--config front-trace/cloudbuild.yaml --substitutions=_TAG=<sha>`).
   - Cambios en `gateway/**` → deployar `gateway` Y reiniciar nginx.
   - `docker-compose.yml` solo afecta dev local, NO se deploya solo.
4. **Tag de imagen**: usar el SHA corto del commit en `main`
   (`git rev-parse --short=7 HEAD`).
5. **Solo preguntar si**:
   - Hay archivos pre-existentes que NO testée en esta sesión (regla #15):
     avisar y preguntar si van.
   - El deploy implica romper algo conocido (downtime, migración no
     reversible, cambio de schema breaking).
   - No queda claro qué servicio backend cambió (cambio puramente cross-cut).
6. **Smoke test post-deploy** (regla #14): es obligatorio, no se pregunta;
   se hace y se reporta el resultado.

Lo que NO se pregunta nunca en este flujo: "¿push primero?", "¿qué flow de
ramas?", "¿confirmás los servicios?". Todo eso ya está decidido por estas
reglas.

## 12. Antes de git commit/push: listar cambios pendientes

Antes de cualquier operación git (commit, push, merge), **siempre**:
1. Mostrar `git status` resumido al usuario.
2. Listar los archivos modificados que NO son parte del fix/feature actual.
3. Preguntar explícitamente: "¿Hago commit de [archivos]? ¿Push a [rama]?"
4. No mezclar cambios de distintas features en un solo commit.

## 13. Leer el Dockerfile antes de buildear cualquier imagen

Antes de correr `gcloud builds submit`, `docker build` o equivalente para
**re-buildear una imagen ya existente** (no la primera vez), **siempre**:

1. Leer el Dockerfile completo del servicio.
2. Listar todos los `ARG` declarados.
3. Para cada ARG sin default, verificar cómo se está pasando al build.

**Específicamente para front-trace** (y cualquier frontend Vite):
- El Dockerfile tiene `ARG VITE_API_URL` sin default. Si no lo paso al builder,
  el bundle JS queda con `VITE_API_URL=""` y el browser intenta llamar a
  `localhost:9000` en producción → toda la app se cae silenciosamente.
- `gcloud builds submit --tag IMAGE` **NO acepta `--build-arg`** y los ignora
  silenciosamente. Para frontends con build args, **siempre** usar
  `gcloud builds submit --config front-trace/cloudbuild.yaml` (ya existe en
  el repo).
- Verificación post-build: descargar la imagen y `docker run --rm IMAGE cat
  /usr/share/nginx/html/assets/index-*.js | grep -o 'gateway-[a-z0-9-]*\.run\.app'`
  debe devolver la URL del gateway de producción, NO `localhost`.

**Este error específico ya pasó (10/4/2026)**: front-trace desplegado con
VITE_API_URL vacío rompió la app entera para todos los usuarios hasta el
rollback.

## 14. Smoke test post-deploy (Cloud Run o local)

Después de **cualquier** deploy de un backend, **antes** de avisarle al usuario
que ya está, hacer al menos:

1. `gcloud run services logs read SERVICE --region southamerica-east1
   --project trace-log --limit 50 | grep -iE "error|exception|traceback"`
   — debe estar **vacío** o solo contener errores de pre-arranque ya
   resueltos.
2. `curl` a un endpoint **listado** del servicio vía el gateway (no directo).
   Endpoints listados ejecutan la serialización Pydantic completa, que es
   donde aparecen los `ResponseValidationError` causados por columnas NULL
   en DB que el schema no acepta.
3. Si el deploy tocó migraciones alembic, verificar en logs:
   `grep "Running upgrade" en los logs del primer arranque del servicio.

**Este error específico ya pasó (10/4/2026)**: trace-api con
`ResponseValidationError` en `/api/v1/config/workflow/states/*/actions` por
`event_type.icon = NULL` en DB que el schema declaraba como `str` no nullable.
El frontend recibía 500, ocultaba el card de "Siguiente paso" y los
operadores no podían mover cargas.

## 15. Cambios pre-existentes WIP: separar y testear

Cuando el working tree tiene cambios pre-existentes (modificados antes de
empezar la sesión actual) que **yo no escribí ni testée**:

1. Identificarlos vía `git status` al inicio de la sesión y separarlos
   mentalmente del scope actual.
2. Si el usuario dice "commitea todo" o equivalente, **no** los meto en el
   mismo commit que mi feature. Hago **un commit aparte** con prefijo
   `wip:` y un mensaje que advierta explícitamente: "código pre-existente
   no probado en esta sesión".
3. Si el deploy va a incluir esos cambios pre-existentes, **smoke-testear
   los endpoints/pantallas afectados** según la regla #14 antes de declarar
   el deploy completo.
4. Si no puedo testearlos (porque requieren auth, datos específicos, etc.),
   le aviso al usuario: "incluí estos archivos pre-existentes pero no los
   probé — confirma vos antes de cerrar".

**Este error específico ya pasó (10/4/2026)**: incluí cambios de trace-service
en el commit "todo" sin testear el endpoint de workflow actions, que era el
único afectado por el bug del schema. El usuario detectó el bug en producción.

## 16. Pre-deploy GCP: checklist obligatorio

Antes de lanzar `gcloud builds submit` para un deploy a producción:

1. **Verificar que las APIs necesarias están habilitadas**:
   ```bash
   gcloud services list --enabled --filter="cloudbuild OR run OR artifactregistry" \
     --project trace-log
   ```
   Si alguna falta, habilitarla con `gcloud services enable ... --project trace-log`
   y **esperar 30 segundos** para propagación antes de lanzar builds.

2. **Conocer la imagen anterior** (para rollback rápido si algo falla):
   ```bash
   gcloud run services list --region southamerica-east1 --project trace-log \
     --format="table(metadata.name,spec.template.spec.containers[0].image)"
   ```
   Anotar el tag de la imagen actual de cada servicio que voy a actualizar.
   Si el deploy nuevo falla, rollback es:
   `gcloud run deploy SERVICE --image OLD_TAG --region southamerica-east1`

3. **Builds en paralelo solo si son independientes**: si los servicios
   comparten infraestructura (ej: un cambio de schema afecta a varios
   servicios al mismo tiempo), deployarlos en orden controlado, no en
   paralelo, para que un fallo de uno no contamine al otro.

4. **Cloud Build con `--tag` vs `--config`**:
   - `--tag IMAGE` solo sirve para servicios sin build args (compliance,
     trace, gateway). NO usar para frontends con `VITE_*`.
   - `--config path/to/cloudbuild.yaml` para servicios que necesitan
     build args (front-trace).

5. **Después del deploy**: aplicar la regla #14 (smoke test). No declarar
   el deploy "completo" sin curl OK + logs limpios.

---

## Comandos útiles del proyecto

```bash
# Rebuild + restart de un servicio (incluyendo refresh del gateway)
docker compose build inventory-api && \
  docker compose up -d inventory-api && \
  sleep 5 && \
  docker compose restart gateway

# Inspeccionar esquema de una tabla
docker exec inventory-postgres psql -U inv_svc -d inventorydb -c "\d <tabla>"

# Logs recientes filtrados de un servicio
docker compose logs --since=5m inventory-api 2>&1 | grep -iE "error|exception|traceback"

# Estado de containers
docker compose ps
```

## Nombres de servicios y bases (referencia rápida)

| Servicio        | Container            | DB container          | DB user / db          | Puerto ext |
|-----------------|----------------------|-----------------------|-----------------------|------------|
| trace-service   | trace-api            | trace-postgres        | trace_svc / tracedb   | 8000       |
| user-service    | user-api             | user-postgres         | user_svc / userdb     | 9001       |
| subscription    | subscription-api     | subscription-postgres | sub_svc / subdb       | 9002       |
| inventory       | inventory-api        | inventory-postgres    | inv_svc / inventorydb | 9003       |
| gateway (nginx) | trace-gateway        | —                     | —                     | 9000       |
| frontend        | (vite dev en host)   | —                     | —                     | 3000       |
