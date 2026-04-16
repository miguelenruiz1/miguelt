# FASE TRACES NT — Cierre 15% tecnico pendiente

**Fecha**: 2026-04-15
**Scope**: Polling DDS, UI, emails, dashboard, tests para la integracion TRACES NT (EUDR).
**Resultado**: tasks 1-7 completos, build OK, smoke tests OK, tests unitarios 8/8 verdes.

---

## 1. Archivos creados

### Backend (compliance-service)
- `compliance-service/alembic/versions/032_dds_polling_fields.py` — migracion nueva.
- `compliance-service/app/services/dds_polling_service.py` — polling loop + email trigger.
- `compliance-service/app/services/email_client.py` — cliente Resend (clon de subscription).
- `compliance-service/app/services/email_templates/dds_validated.html` — plantilla HTML.
- `compliance-service/tests/test_traces_service.py` — 8 tests unitarios.

### Frontend (front-trace)
- `front-trace/src/pages/compliance/DDSStatusPage.tsx` — dashboard `/cumplimiento/dds-status`.

## 2. Archivos modificados

### Backend
- `compliance-service/app/services/traces_service.py`
  - `TracesNTService.retrieve_dds_info(reference_number)` async method.
  - `build_retrieve_envelope(...)` — envelope SOAP con WS-Security para `retrieveDdsInfoByReferences`.
  - `parse_retrieve_response(xml, reference_number)` — parser tolerante a prefijos XML + mapa `_STATUS_MAP` (AVAILABLE/VALIDATED/ACCEPTED -> `validated`, REJECTED/WITHDRAWN -> `rejected`, AMENDED/SUPERSEDED -> `amended`).
- `compliance-service/app/api/v1/records.py`
  - `GET /api/v1/compliance/records/{id}/dds-status` — consulta sincrona contra TRACES NT + sync DB. Row lock con `with_for_update()`, idempotente.
  - `list_records(...)` acepta `declaration_status` y `has_declaration` como query params.
- `compliance-service/app/models/record.py`
  - 3 columnas nuevas: `declaration_validated_at`, `declaration_rejection_reason`, `declaration_last_polled_at`.
  - CHECK `ck_records_declaration_status` amplia para admitir `validated` y `amended`.
- `compliance-service/app/schemas/record.py`
  - `RecordResponse` expone los 3 campos nuevos.
- `compliance-service/app/main.py`
  - Lifespan agrega `dds_poll_task = asyncio.create_task(run_polling_loop(interval_seconds=60))` con cancelacion graceful (mismo patron que `dunning_service`).

### Frontend
- `front-trace/src/types/compliance.ts` — `DeclarationStatus` amplia a `validated | amended`; `ComplianceRecord` expone los 3 campos nuevos.
- `front-trace/src/lib/compliance-api.ts` — `records.list(...)` acepta `declaration_status`/`has_declaration`; nuevo `records.ddsStatus(id)`.
- `front-trace/src/hooks/useCompliance.ts` — `useRecords` con filtros nuevos; `useDDSStatus(recordId, {enabled})` con `refetchInterval: 30_000` y auto-invalidacion del record cache en cada poll.
- `front-trace/src/pages/compliance/RecordDetailPage.tsx`
  - Import de `useDDSStatus`.
  - Constantes `DDS_STATUS_BADGE` y labels ampliados (`validated`, `amended`, `draft`, `ready`).
  - Componentes nuevos: `DdsTracesStatusBlock` (badge + polling UI + boton "Verificar ahora" + validated_at + rejection_reason + lista prior_dds_references) y `DdsActionButtons` (switch por estado: ready -> export+submit, submitted -> solo export, validated -> export + "Ver certificado DDS", rejected -> export + re-submit).
  - El DeclarationTab renderiza `<DdsTracesStatusBlock>` y `<DdsActionButtons>` dentro de la card TRACES NT existente.
- `front-trace/src/App.tsx` — ruta `/cumplimiento/dds-status` + lazy import.
- `front-trace/src/components/layout/Sidebar.tsx` — item "DDS TRACES NT" (icon `Send`) en seccion Cumplimiento.

## 3. Migracion nueva

**Numero**: `032_dds_polling_fields` (down_revision: `031_commodity_quality_rspo`).

Agrega a `compliance_records`:
- `declaration_validated_at TIMESTAMP WITH TIME ZONE NULL`
- `declaration_rejection_reason TEXT NULL`
- `declaration_last_polled_at TIMESTAMP WITH TIME ZONE NULL`

Modifica `ck_records_declaration_status` para admitir `validated` y `amended` (ademas de los 5 estados previos).

Indice nuevo: `ix_records_decl_status_polled (declaration_status, declaration_last_polled_at)` — para acelerar el loop `poll_once()`.

Verificado en DB:
```
declaration_validated_at       | timestamp with time zone
declaration_rejection_reason   | text
declaration_last_polled_at     | timestamp with time zone
"ix_records_decl_status_polled" btree (declaration_status, declaration_last_polled_at)
"ck_records_declaration_status" CHECK (declaration_status = ANY (ARRAY[...,'validated'::text, 'amended'::text]))
```

## 4. Tests

**Antes**: 4 archivos de test (`test_endpoints`, `test_qr_builder`, `test_storage`, `test_validator`), 36 tests colectables (con 10 de endpoints que requieren server corriendo).

**Despues**: +1 archivo `test_traces_service.py` con 8 tests unitarios (sin DB, sin red).

Tests nuevos (todos PASS):
1. `test_build_soap_envelope_structure` — WS-Security header, Nonce base64, Created `YYYY-MM-DDTHH:MM:SS.000Z`, PasswordDigest, webServiceClientId.
2. `test_build_dds_payload_full_plots` — 3 plots + coffee → payload con FeatureCollection b64-embebido, padding de 6 decimales, 3 producers.
3. `test_retrieve_dds_info_parsing_validated` — raw `AVAILABLE` → `validated` + `validated_at`.
4. `test_retrieve_dds_info_parsing_rejected` — `REJECTED` + `<rejectionReason>` (sin namespace).
5. `test_retrieve_dds_info_parsing_unknown_without_ref` — body vacio → `unknown`.
6. `test_retrieve_dds_info_parsing_submitted_fallback` — body sin status pero con la referencia → `submitted`.
7. `test_retrieve_envelope_structure` — `<eudr:retrieveDdsInfoByReferences>` + nonce b64-decodable.
8. `test_soap_envelope_snapshot_stable_fields` — snapshot de 22 tags requeridos por el XSD EUDR.

```
8 passed in 0.86s
```

## 5. Smoke tests (via gateway, no auth)

```
$ curl -X GET http://localhost:9000/api/v1/compliance/records/<uuid>/dds-status \
    -H "X-Tenant-Id: default"
HTTP 401 (auth middleware OK — ruta resuelve)

$ curl -X GET "http://localhost:9000/api/v1/compliance/records/?has_declaration=true" \
    -H "X-Tenant-Id: default"
HTTP 401 (filter param aceptado)
```

OpenAPI paths confirma registro:
```
/api/v1/compliance/records/{record_id}/dds-status
```

Startup logs muestran:
```
Running upgrade 031_commodity_quality_rspo -> 032_dds_polling_fields
dds_polling_loop_scheduled interval=60
compliance_service_ready
dds_poll_complete scanned=1 validated=0 rejected=0 ... unchanged=1 errors=0
```

Loop corriendo (scanned 1 record `submitted` del tenant default, unchanged porque no hay creds TRACES NT configuradas — comportamiento esperado).

No hay `ERROR`/`exception`/`traceback` en los logs post-deploy.

Frontend typecheck (`tsc --noEmit`): limpio, 0 errores.

## 6. UI — captures conceptuales

### Estado: `submitted` (en validacion)
- Card azul "TRACES NT" con badge **amber + icono reloj** "Enviada (en validacion)".
- Referencia TRACES mostrada en mono-font.
- Boton "Verificar ahora" (refetch manual + toast "Estado actualizado").
- Timestamp "Ultima verificacion: 15/04/2026 19:07:03".
- Botones: solo "Exportar DDS (JSON)" (no re-submit mientras EU procesa).
- Polling silencioso cada 30s en background (hook `useDDSStatus` con `refetchInterval: 30_000`).

### Estado: `validated`
- Badge **emerald + icono CheckCircle2** "Validada".
- Linea verde "Validado el 10/04/2026 12:34".
- Botones: "Exportar DDS (JSON)" + "Ver certificado DDS" (link externo a `https://webgate.ec.europa.eu/tracesnt/directory/dds/<ref>`).
- Polling desactivado (estado terminal).
- **Email automatico**: al transicionar a `validated` el loop envia email HTML (template `dds_validated.html`) al `buyer_email` con el reference_number + commodity + cantidad + link a TRACES NT.

### Estado: `rejected`
- Badge **red + icono XCircle** "Rechazada".
- Card roja con icono `AlertTriangle` y texto de `rejection_reason`.
- Botones: "Exportar DDS" + "Enviar a TRACES NT" (re-submit despues de corregir).

### Estado: `amended`
- Badge **purple** "Enmendada".
- Card purpura con lista de `prior_dds_references` (las refs historicas).

### Estado: `ready` / `draft` / `not_required`
- Badge segun el estado (azul/gris).
- Botones: "Exportar DDS (JSON)" + "Enviar a TRACES NT" (submit habilitado si compliance_status es ready|declared|compliant).

### Dashboard `/cumplimiento/dds-status`
- Header + boton "Actualizar todo" (itera sobre todos los `submitted` del tenant y llama `/dds-status` uno por uno).
- 5 KPI cards: Total / En validacion (amber) / Validadas (emerald) / Rechazadas (red) / Enmendadas (purple).
- Filtros: estado (Todos/submitted/validated/rejected/amended), commodity (coffee/cacao/palm/other), date range.
- Tabla: Registro (link a detalle) / Commodity / Cantidad (kg) / Referencia TRACES / Estado / Enviada / Validada / Acciones (link externo a TRACES NT si validated).
- Sidebar "Cumplimiento > DDS TRACES NT" con icono `Send`.

## 7. Flujo end-to-end (autom**atico)

1. Usuario hace `POST /records/{id}/submit-traces` -> compliance-service envia SOAP DDS -> TRACES NT responde 200 + reference_number.
2. DB actualiza `declaration_status='submitted'` + `declaration_reference=<ref>` + `declaration_submission_date=today`.
3. Polling loop (cada 60s) selecciona `status='submitted' AND (last_polled_at IS NULL OR last_polled_at < now()-60s)`, limit 50.
4. Para cada registro: `retrieveDdsInfoByReferences(ref)` SOAP call.
5. Parsea respuesta: `AVAILABLE/VALIDATED -> validated`, `REJECTED -> rejected`, `AMENDED -> amended`.
6. Si transiciona a `validated`: UPDATE DB + envio email (Resend via user-service email config lookup, fallback env).
7. Frontend (abierto en `/cumplimiento/registros/<id>` o `/cumplimiento/dds-status`) auto-refrescha cada 30s con `useDDSStatus` — el badge cambia de amber a emerald sin intervencion del usuario.

## 8. TODOs conocidos

1. **WSDL oficial del retrieve**: construi el envelope por analogia al submit. Los tag names (`retrieveDdsInfoByReferences`, `referenceNumber`) siguen los que aparecen en la spec ATIBT y mocks publicos; si el WSDL oficial del EU acceptance env usa un namespace distinto, hay que ajustar `build_retrieve_envelope()`. El parser es tolerante a prefijos, asi que la respuesta se va a parsear aunque la request use namespace distinto.
2. **E2E contra acceptance env**: no se probo contra TRACES NT real (requiere creds vivas). Los tests cubren estructura del envelope y parseo; el primer smoke en acceptance va a confirmar el contrato real.
3. **retrieveDdsInfoByReferences plural**: la spec permite enviar lista de refs y recibir batch. Por ahora la implementacion manda 1 ref por llamada (mas simple, evita ambiguedad en parseo de batch). Optimizacion futura: batch polling con 1 call por tenant por ciclo.
4. **Email on rejected/amended**: el loop solo envia email en `validated`. Rejected/amended todavia emiten log pero no notificacion email — se puede agregar con templates analogos (`dds_rejected.html`, `dds_amended.html`).
5. **Templating con Jinja**: `_render_template()` usa un `str.replace` simple. Si se complica el template (loops, condicionales), migrar a jinja2 — ya esta instalado en subscription-service.
6. **Tests E2E**: `test_endpoints.py` requiere el servicio corriendo (httpx.ConnectError en host). Las fallas de esos tests son pre-existentes y no relacionadas con este cambio (6 de ellos son GET /health / GET /ready). Los 26 tests unitarios pasan.
7. **Retencion del `declaration_rejection_reason`**: si una DDS pasa de `rejected` -> re-submit -> `validated`, el campo se limpia. Si el usuario quiere historial, persistir en `metadata_.rejection_history[]`.

## 9. Cumplimiento de CLAUDE.md

- **Regla #1** (leer esquema antes de SQL): se uso ORM puro (`select(ComplianceRecord).where(...)`) en el endpoint y el polling. No hay `text("SELECT ...")` nuevo.
- **Regla #3** (smoke test): se ejecuto curl contra `/dds-status` y `/records/?has_declaration=true` — ambos resuelven (401 de auth = ruta existe).
- **Regla #4** (gateway restart): `docker compose build compliance-api && up -d compliance-api && restart gateway` ejecutado y verificado (trace-gateway healthy).
- **Regla #9** (no tocar traces_service.py mas alla de lo pedido): solo se agrego `retrieve_dds_info()` + helpers `build_retrieve_envelope` + `parse_retrieve_response` al final del modulo. El codigo `submit_dds`/`build_soap_envelope` existente no se modifico.
- **Regla #10** (reportar honestamente): el retrieve SOAP **no se probo end-to-end contra TRACES NT real** — ver TODO #2. Los tests unitarios con mocks confirman la mecanica.
