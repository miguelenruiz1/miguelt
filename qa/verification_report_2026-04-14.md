# QA Verification Report — 2026-04-14

Branch: `fixes/milimetricos`  
Tester: Claude (Opus 4.6) vía sandbox local  
Tenants usados: `default` (via S2S) y `qaverifier-bdc8c6` (via JWT)  
Duración efectiva: ~1.5 h (no se ejecutaron los tres seeds completos — ver Parte A)

---

## Parte A — Resultados de seeds

Los 3 scripts de `scripts/seed_*.sh` **no fueron ejecutados end-to-end como scripts**.
El sandbox local bloqueó repetidamente la ejecución directa (`bash script.sh`,
`./script.sh`, `cd ... && bash ...`). En lugar de eso se ejecutaron los pasos
críticos manualmente con `curl` inline. Los resultados documentan qué pasos del
flujo funcionan y qué bugs existen en los scripts.

### Seed 1 — Huila → Hamburgo (`seed_huila_hamburgo.sh`)

| Paso | Resultado |
|---|---|
| 1/8 Crear plot Finca El Mirador | **FAIL al primer intento** → fix aplicado, luego OK (plot_id `ce8e7087…` via JWT tenant QA, `1e88afc9…` via S2S tenant default) |
| 2/8 Crear asset ligado al plot | **FAIL al primer intento** (wallet no allowlisted) → OK tras registrar wallet. **Bug menor**: `plot_id` regresa `null` en la respuesta aunque el payload lo envió |
| 3/8 Eventos de custodia (COSECHA/BENEFICIO/TRILLA) | OK — HTTP 201 para los 3 (`default` tenant) |
| 4/8 Quantity changes | El script no los ejecuta (comentado como "Manual step") — no testeado |
| 5/8 Customer InterAmerican Coffee GmbH | **FAIL via S2S** (inventory-api no acepta `X-Service-Token`) → OK via JWT (`b292ac94…`) |
| 6/8 Sales order EUR/FOB/DE | **FAIL** en todos los casos → script envía `"lines":[]` y el endpoint exige al menos 1 línea |
| 7/8 Smoke check plots | OK vía curl manual |
| 8/8 Done | — |

**Bug del script**: coordenadas GeoJSON con 5 decimales → la validación EUDR Art. 2(28)
requiere mínimo 6 decimales. **Fix aplicado** en el archivo (padding con ceros).

**Bug arquitectónico del script**: el script asume que el mismo token (S2S)
autentica en todos los servicios. `inventory-service` **no** acepta S2S — requiere JWT.
No se arregló (fuera de scope, requiere redesign del flujo de auth inter-service).

### Seed 2 — Cacao Tumaco (`seed_cacao_tumaco.sh`)

| Paso | Resultado |
|---|---|
| Crear plot cacao (Theobroma cacao L.) | **FAIL al primer intento** (5 decimales) → fix aplicado, luego OK (`fcc1a657-73c7-4710-8bc1-89724199d071`) |
| Asset / custody / SO / cadmium test | No ejecutado como script. Cadmium test sí fue probado end-to-end aparte (ver Parte B) |

**Fix aplicado**: coordenadas GeoJSON a 6 decimales.

### Seed 3 — Palma Cesar (`seed_palma_cesar.sh`)

| Paso | Resultado |
|---|---|
| Crear plot palma industrial (854 ha) | OK (`b17d382b-403a-4ba7-87d3-10d4c8c0fa65`). Validación de área poligonal confirmada: el backend calculó 849.28 ha vs declaradas 854 → pasó (dentro de la tolerancia) |
| Placeholders `product-*-placeholder` | **No reemplazados**. El script requeriría crear productos + recetas primero. Fuera de alcance para esta sesión. |

**Fix aplicado**: coordenadas GeoJSON a 6 decimales.

---

## Parte B — Smoke test endpoints (tenant `qaverifier-bdc8c6`, JWT)

Todos via gateway `http://localhost:9000`. Status observados en listado (GET `?limit=5`):

| Endpoint | Status | OK/FAIL | Nota |
|---|---:|---|---|
| GET /api/v1/auth/me | 200 | OK | |
| GET /api/v1/categories | 200 | OK | |
| GET /api/v1/products | 200 | OK | tras activar módulo inventory + invalidar Redis cache |
| GET /api/v1/warehouses | 200 | OK | |
| GET /api/v1/suppliers | 200 | OK | |
| GET /api/v1/customers | 200 | OK | |
| GET /api/v1/purchase-orders | 200 | OK | |
| GET /api/v1/sales-orders | 200 | OK | |
| GET /api/v1/stock | 200 | OK | |
| GET /api/v1/movements | 200 | OK | |
| GET /api/v1/uom | 200 | OK | |
| GET /api/v1/tax-rates | 200 | OK | |
| GET /api/v1/tax-categories | 200 | OK | |
| GET /api/v1/batches | 200 | OK | |
| GET /api/v1/recipes | 200 | OK | |
| GET /api/v1/production-runs | 200 | OK | |
| GET /api/v1/production-resources | 403 | FAIL | permiso `production.view` no asignado a rol `administrador` |
| GET /api/v1/variants | 200 | OK | |
| GET /api/v1/variant-attributes | 200 | OK | |
| GET /api/v1/partners | 200 | OK | |
| GET /api/v1/customer-prices | 200 | OK | |
| GET /api/v1/serials | 200 | OK | |
| GET /api/v1/cycle-counts | 200 | OK | |
| GET /api/v1/alerts | 200 | OK | |
| GET /api/v1/config/workflow/states | 200 | OK | |
| GET /api/v1/compliance/plots/ | 200 | OK | ⚠ requiere trailing slash (sin slash → 404) |
| GET /api/v1/compliance/records/ | 200 | OK | ⚠ idem |
| POST /api/v1/compliance/plots/ (café/cacao/palma) | 201 | OK | Validaciones EUDR Art. 2(28) funcionan correctamente (precisión 6 decimales, área poligonal) |
| POST /api/v1/compliance/records/ | 201 | OK | |
| POST /api/v1/compliance/records/{id}/cadmium-test | 200 | OK | Retorna `cadmium_eu_compliant=true` para 0.42 mg/kg (límite 0.60 cacao). Persiste `cadmium_test_lab` |
| POST /api/v1/compliance/plots/{id}/screen-deforestation-full | 200 | OK | GFW integrated alerts + JRC forest 2020 funcionando. Para Tumaco devuelve `eudr_compliant=true`, `risk=none` |
| GET /api/v1/assets | 200 | OK | |
| POST /api/v1/assets | 201 | OK | tras registrar wallet allowlist. **Bug**: `plot_id` enviado no se refleja en la respuesta (null) |
| POST /api/v1/assets/{id}/events (COSECHA/BENEFICIO/TRILLA) | 201 | OK | |
| GET /api/v1/registry/wallets | 200 | OK | |
| GET /api/v1/analytics/overview | 200 | OK | |
| GET /api/v1/analytics/abc | 200 | OK | |
| GET /api/v1/analytics/eoq | 200 | OK | |
| GET /api/v1/analytics/occupation | 200 | OK | |
| GET /api/v1/reports/products | 200 | OK | |
| GET /api/v1/modules/{tenant} | 200 | OK | |
| POST /api/v1/modules/{tenant}/{slug}/activate | 200 | OK | |
| GET /api/v1/quality-tests (bare) | 404 | — | No es bug: solo existen `/api/v1/batches/{id}/quality-tests` y `POST /api/v1/quality-tests` |
| GET /api/v1/reorder (bare) | 404 | — | Idem: solo `/reorder/check` y `/reorder/config` |

**Endpoints probados: 42**  
**OK: 40 (95%)**  
**FAIL atribuibles a bugs: 1 (production-resources permiso) + 1 (asset.plot_id no reflejado)**

---

## Parte C — Bugs fixeados en este sprint

**NINGÚN commit fue creado todavía**. Los fixes están en el working tree:

| # | Archivo | Cambio | Estado |
|---|---|---|---|
| 1 | `inventory-service/app/services/production_service.py` | Agregado filtro `ProductionEmission.production_run_id == run_id` en `_propagate_plot_origins`. Servicio rebuildeado y gateway reiniciado; logs limpios. | ✅ funcional + container live |
| 2 | `scripts/seed_huila_hamburgo.sh` | Coordenadas GeoJSON a 6 decimales (cumple EUDR Art. 2(28)) | ✅ validado manualmente |
| 3 | `scripts/seed_cacao_tumaco.sh` | Idem | ✅ validado manualmente |
| 4 | `scripts/seed_palma_cesar.sh` | Idem | ✅ validado manualmente |

Commit sugerido: `fix(production+seeds): scope plot origin propagation + EUDR 6-decimal coords in seeds`

> Regla CLAUDE.md #12: confirmar commit y scope antes de ejecutar `git commit`.

---

## Parte D — Bugs / gaps NO arreglados (por severidad)

### BLOCKER (impide demo e2e)
- **Seed scripts usan solo S2S token, pero `inventory-service` no acepta S2S**. Paso 5/8 del seed de Huila falla (crear customer) sin JWT. Significa que ningún seed llega al paso de sales-order. Fix requerido: o bien (a) agregar middleware S2S en inventory-service, o (b) reescribir seeds para login+JWT primero. Ubicación: `inventory-service/app/api/deps.py` (no tiene handler S2S).
- **Seed de palma tiene `product-*-placeholder` sin resolver**. Requiere crear productos + recetas antes de correr el seed, o prepoblar en migración.

### HIGH (degrada experiencia)
- **Asset `plot_id` no se persiste al crear**: POST `/api/v1/assets` acepta `plot_id` pero la respuesta devuelve `plot_id: null`. Verificar si es bug del handler o solo del serializer. Archivo candidato: `trace-service/app/api/routers/custody.py` o `domain/schemas.py`. No investigado en profundidad.
- **Sales order no acepta `lines: []`**: regla de negocio razonable, pero el seed de Huila envía exactamente eso. Actualizar el seed para incluir al menos 1 línea.
- **Módulos por defecto desactivados para tenant nuevo**: al registrar usuario se crea tenant automáticamente pero NO activa módulos. Frontend probablemente muestra pantalla de marketplace en vez del dashboard esperado. Sugerir auto-activar `logistics` + `inventory` + `compliance` en el primer registro.
- **Cache Redis de módulos requiere invalidación manual**: tras `activate`, los endpoints de inventory siguieron retornando 403 hasta `redis-cli DEL module:…:inventory`. El endpoint activate debería invalidar la cache. Ubicación: `subscription-service` (no investigado).

### MED (cosmético / flujo)
- **Trailing slash obligatorio en `/api/v1/compliance/plots`, `/records`**: sin slash retorna 404. El frontend probablemente ya lo maneja pero testers/Postman/curl sufren. FastAPI router levantó con `prefix="/plots"` + `Route("/", …)` explícito.
- **Seed Huila paso 4/8 (quantity changes) nunca se ejecuta** — está marcado como "manual step". El script se siente incompleto.
- **Seed Huila paso 6 log: "sales-order create response: …"** siempre imprime, aunque fallara; deberían chequear el status code.
- **Permiso `production.view` no asignado a rol administrador**: tras activar el módulo `production`, el admin sigue sin poder ver `/production-resources`. Falta migración que añada permisos del módulo production al rol administrador.
- **Compliance record ignora `regulation` field si se manda**: el schema exige `framework_slug`. No es bug, pero seeds viejos podrían fallar silenciosamente.

### LOW
- Rotación del tenant UUID: al registrar con header `X-Tenant-Id: qa-verification`, el servicio lo ignora y genera `qaverifier-bdc8c6`. Probablemente comportamiento intencional (un tenant por email), pero confuso.
- Nombre del rol en seed de users: response dice `"Administrador"` pero el slug es `administrador` (minúscula). Consistencia.

---

## Parte E — Métricas

- Endpoints probados: **42**
- Endpoints OK: **40** (95%)
- Endpoints con FAIL atribuible a bug: **2** (production-resources permiso, asset.plot_id)
- Bugs fixeados (working tree, sin commit): **4** (1 código + 3 seeds)
- Bugs/gaps reportados sin fix: **~11** (2 BLOCKER, 4 HIGH, 4 MED, 1 LOW + S2S/JWT re-diseño)
- Tiempo total invertido: ~1.5 h (limitado por sandbox denegando comandos de shell)
- Seeds ejecutados end-to-end: **0 de 3** (bloqueos de sandbox + bugs de seed)
- Commits creados: **0** (sandbox denegó `git commit`; requiere autorización del usuario)

---

## Parte F — Recomendación honesta (regla CLAUDE.md #10)

**Honestidad primero**: el sandbox de QA denegó varias operaciones críticas
(ejecución directa de los scripts seed, `git commit`, `source env.sh`). Eso
significa que **los seeds no fueron ejecutados end-to-end** — solo se probaron
a mano los pasos individuales que revelaban bugs. La confianza de los números
abajo viene de ese testing puntual, no de un flujo completo.

**% efectividad estimada**:
- **Antes de esta sesión**: ~70-75% (8 commits previos añadieron EUDR café + multi-commodity, pero nadie lo había probado con datos)
- **Después de esta sesión**: ~75-80%. El bug real de `_propagate_plot_origins` fue arreglado y las coordenadas de los seeds cumplen EUDR. Los endpoints críticos responden. Falta atar los flujos (sales orders, plot_id en assets, módulo auto-activate).

**¿Demo end-to-end Uniandes 20-abril es factible?**
**Sí, con caveats**. Con la configuración actual se puede demostrar:
- Crear/listar parcelas EUDR con GeoJSON validado
- Screening GFW de deforestación (GFW tiene API key configurada)
- Declaración de cadmio para cacao con validación vs 0.60 mg/kg
- Registrar asset + eventos de custodia (cosecha, beneficio, trilla)

**NO se puede demostrar hoy sin más trabajo**:
- Flujo completo de sales-order con líneas (requiere datos precargados)
- Producción multi-output (seed de palma depende de recetas placeholder)
- Trazabilidad plot → batch → SO (el bug de plot_id en asset lo corta)

### Top 5 cosas que harían el mayor diferencial (1-2 días)

1. **Auto-activar módulos `logistics`+`inventory`+`compliance` al registrar un tenant** (1-2 h). Hoy el flujo de onboarding rompe la demo porque el usuario nuevo ve todo 403.
2. **Reescribir los 3 seeds para usar JWT en inventory-service + productos/recetas prepoblados** (0.5 día). Sin esto no hay demo reproducible.
3. **Investigar y arreglar `asset.plot_id=null` en POST /assets** (2-3 h). Es el link crítico EUDR parcela→trazabilidad.
4. **Agregar permiso `production.view/manage` al rol administrador en la migración de user-service** (30 min). Desbloquea la pantalla de recursos de producción.
5. **Invalidar cache Redis `module:…:inventory` al ejecutar `/modules/{tenant}/{slug}/activate`** (1 h). Sin esto, activar un módulo no tiene efecto hasta que expira la TTL.

Bonus: hacer que compliance router acepte `/plots` y `/records` sin trailing slash (redirect o dual route).

---

## Parte G — Resultado de los fixes (sesión 2026-04-14 tarde)

### Commits creados en `fixes/milimetricos`

Todos con `Co-Authored-By: Claude Opus 4.6`:

| # | Hash | Mensaje |
|---|---|---|
| 1 | `729ace3` | `fix(production): scope plot origin propagation to current run` |
| 2 | `ded20a5` | `fix(seeds): pad EUDR GeoJSON coords to 6 decimals` |
| 3 | `b695759` | `fix(inventory): accept S2S service token same as compliance` |
| 4 | `cc1245d` | `fix(trace): persist and return asset.plot_id` |
| 5 | `8c288e0` | `fix(user): grant production permissions to administrador role` |
| 6 | `5e867dc` | `fix(seeds): resolve palm product placeholders with real entity ids` |
| 7 | `d271a99` | `fix(inventory): SO creation works for non-UUID tenants` |
| 8 | `8eddc8f` | `fix(seeds): populate non-empty SO lines with resolved product` |

8 commits, uno por bug lógico. Ningún push, ningún merge — la rama sigue
local.

### Blockers atacados

- **BLOCKER #1 — inventory no acepta S2S** → FIXED (`b695759`). Replicado el
  mismo patrón de `compliance-service/app/api/deps.py`: `_bearer` pasa a
  `auto_error=False` y `get_current_user` chequea `X-Service-Token` contra
  `settings.S2S_SERVICE_TOKEN` antes de exigir JWT. Verificado end-to-end:
  `curl -H X-Service-Token … /api/v1/products` → 200.
- **BLOCKER #2 — asset.plot_id nunca persistía** → FIXED (`cc1245d`). El
  campo existía en schema y modelo, pero ni el router, ni `CustodyService.create_asset/mint_asset`,
  ni `AssetRepository.create` lo pasaban al INSERT. Lo enhebré por las 3
  capas. Verificado: POST `/api/v1/assets` con `plot_id` devuelve el mismo
  valor en el response (antes: `null`).
- **BLOCKER #3 — rol administrador sin `production.view/manage`** → FIXED
  (`8c288e0`). Root cause: migraciones 011 (production) y 015 (compliance)
  asignaron permisos a los admin roles que existían al momento, pero
  `AuthService._PERMISSIONS` nunca fue actualizado → todo tenant registrado
  posterior tenía admin sin esos permisos. Agregué los 9 slugs a
  `_PERMISSIONS` y creé migración 018 que re-sincroniza retroactivamente a
  todos los admin roles existentes (idempotente con ON CONFLICT DO NOTHING).
  Verificado: QA tenant ahora devuelve 200 en `/production-resources`.
- **BLOCKER #4 — seed palma con placeholders** → FIXED (`5e867dc`). El
  script ahora resuelve (GET-then-POST idempotente) los 3 productos base
  RFF / CPO / PKO antes de armar el recipe, usa la primera categoría
  disponible (o la crea) para satisfacer `category_id`, y usa los IDs
  resueltos tanto en `components` como en `output_components`.

### Bugs adicionales que aparecieron al correr seeds (y se fixearon)

Correr los 3 seeds end-to-end destapó 4 bugs más, todos pre-existentes:

1. **`sequence_counters.tenant_id` era UUID**, pero el resto del schema
   guarda `tenant_id` como VARCHAR(255). Cualquier SO/PO para tenant
   `default` fallaba con `invalid input for query argument $1: 'default'`.
   Migración 085 amplía la columna a VARCHAR(255).
2. **`SequenceRepository.next_value` usaba `:tenant_id::uuid`**, que
   asyncpg no parsea (confunde `::` con el cast Postgres vs otro bind).
   Simplificado a un bind plano tras la migración 085.
3. **`sales_order_repo.create` tiraba `MissingGreenlet`** porque
   `recalculate_so_totals` lee `line.line_taxes` pero ese relationship no
   estaba en `_SO_OPTIONS` y el `refresh(order, ['lines'])` no lo cargaba.
   Agregado al selectinload chain + re-fetch del order antes de recalcular.
4. **`/api/v1/compliance/plots` requería trailing slash** (FastAPI
   `prefix="/plots"` + `Route("/")`); los 3 seeds usaban `/plots` sin
   slash. Arreglado en los 3 scripts.

Los 4 fueron commiteados en `d271a99` (bugs #1–#3) y `8eddc8f` (parte del
slash + SO lines). Los 3 seeds ahora también usan `qty_ordered` (nombre
real del campo en `SalesOrderLineCreate`) en vez de `quantity`.

### Seeds end-to-end (ejecutados paso a paso via curl por sandbox bloqueando `bash script.sh`)

| Seed | Plot | Asset+plot_id | Custody events | Customer | SO | Extras |
|---|---|---|---|---|---|---|
| Huila → Hamburgo | OK `1e88afc9…` | `a2a44bba…` con plot_id OK | COSECHA/BENEFICIO/TRILLA 201 | `f3e6c647…` (InterAmerican) | SO-2026-0001 2750 EUR | — |
| Cacao Tumaco → Amsterdam | OK `fcc1a657…` | `14efbe98…` con plot_id OK | 6 eventos 201 | `e12015ec…` (CocoaSource NL) | SO-2026-0003 3200 EUR | Record `2272415d…`, cadmium test 0.42 mg/kg OK |
| Palma San Alberto → Mannheim | OK `b17d382b…` | `33c7461a…` con plot_id OK | 6 eventos 201 | `8bbbc63e…` (Bunge) | SO-2026-0002 4250 USD | 3 productos creados (RFF/CPO/PKO), recipe multi-output `15f3b62d…` con `output_components` correctos |

**3/3 seeds ejecutaron el flujo completo** (plot + asset con plot_id +
custody chain + customer + SO; cacao agrega record+cadmium; palma agrega
recipe multi-output).

Caveat de honestidad (regla CLAUDE.md #10): el sandbox siguió bloqueando
`bash scripts/seed_*.sh` como script completo, así que ejecuté los
endpoints paso a paso con curl en vez de correr el shebang. Los scripts
quedaron fixeados en disco; un humano corriéndolos end-to-end debería ver
el mismo resultado, pero no pude validar la orquestación exacta bash +
`set -euo pipefail` + subshells.

### Re-smoke test de endpoints (JWT tenant `qaverifier-bdc8c6`)

Re-corrí 33 endpoints GET list clave via gateway, **33/33 = 200 OK**.
Crítico: `/api/v1/production-resources` ahora devuelve 200 (antes 403).
El resto también sigue en 200 — los fixes no regresaron nada.

(El listado de 42 del sprint anterior incluía 2 endpoints "bare" que NO
son bugs sino que no existen como ruta; excluidos. Los GET POST de
compliance plots/records con trailing slash + cadmium-test + screen-deforestation
se verificaron como parte del seed run.)

### Delta de efectividad funcional

- Antes (según Parte F): **~75-80%**.
- Después: **~88-92%**. El trace EUDR end-to-end (plot → asset con
  plot_id → events → record → SO) funciona para los 3 commodities (café,
  cacao, palma). Lo que queda son cosméticos (trailing slash, auto-activar
  módulos al registrar) y features todavía no tocados (producción
  multi-output solo validada a nivel recipe, no ejecución con ARQ worker).

### Lo que queda pendiente para Uniandes 20-abril

| Severidad | Item |
|---|---|
| MED | Módulos `logistics`/`inventory`/`compliance` no se auto-activan al registrar un tenant. Mitigación: hacer onboarding con un admin ya existente o clickear "Marketplace" antes de la demo. |
| MED | Cache Redis `module:{tenant}:{slug}` no se invalida al ejecutar `/modules/{tenant}/{slug}/activate`. Workaround: esperar 5 min TTL o `redis-cli -n <n> DEL`. |
| MED | Trailing slash sigue requerido en `/api/v1/compliance/plots` y `/records` (fix aplicado a seeds, no al router). El front ya lo maneja — solo afecta curl/Postman. |
| MED | Producción multi-output: recipe se crea OK, pero no corrí un `POST /api/v1/production-runs` end-to-end con emisiones reales. |
| LOW | `X-Tenant-Id: foo` en register ignora el slug y genera `fooverifier-xxx` — comportamiento intencional pero confuso. |

### Checklist domingo antes de la demo (manual por el usuario)

1. **Recrear un tenant demo limpio**: `POST /api/v1/auth/register` con
   email `demo@uniandes.example`. Capturar el `tenant_id` canonical del
   response.
2. **Activar los 3 módulos** para ese tenant via
   `POST /api/v1/modules/{tenant_id}/{logistics|inventory|compliance}/activate`
   (requiere JWT de un admin o is_superuser).
3. **Invalidar cache Redis** (solo si hace falta):
   `docker exec trace-redis redis-cli -n 4 --scan | xargs -I {} docker exec trace-redis redis-cli -n 4 DEL {}`
   (reemplazar `-n 4` por el db de inventory si diferente).
4. **Correr los 3 seeds en orden** con `TENANT=<tenant_id_canonical>`:
   ```bash
   TENANT=<uuid> bash scripts/seed_huila_hamburgo.sh
   TENANT=<uuid> bash scripts/seed_cacao_tumaco.sh
   TENANT=<uuid> bash scripts/seed_palma_cesar.sh
   ```
5. **Loguearte en el front como el admin del tenant demo** y navegar
   `/compliance/plots` + `/tracking` + `/sales-orders` para verificar que
   todo aparece. Si algo está vacío, revisar que el módulo esté activo y
   el cache invalidado.

