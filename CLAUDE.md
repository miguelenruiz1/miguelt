# CLAUDE.md — Reglas de trabajo para Claude en este repo

Estas reglas existen porque ya cometí errores concretos en este proyecto y el
usuario perdió tiempo. Son obligatorias, no sugerencias. Si alguna no aplica a
una tarea puntual, lo digo explícitamente antes de saltármela.

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
