# FASE 2 — Billing Completeness Report

**Fecha**: 2026-04-15
**Servicio**: `subscription-service` (+ una adición mínima en `user-service`)
**Alcance**: Invoice PDF, email vía Resend, dunning automático, reconciliation Wompi, refund/credit note.

---

## 1. Resumen ejecutivo

Implementadas las 5 tasks del brief. El servicio `subscription-service` ahora puede:

- Generar PDF enterprise-grade en español colombiano (WeasyPrint + Jinja2) con IVA 19% automatico.
- Enviar facturas y recordatorios por email vía Resend con retries exponenciales y fallback seguro.
- Correr dunning automático cada hora (soft/urgent/final según días de mora) y suspender suscripciones a los 8+ días.
- Conciliar pagos Wompi con invoices (por `invoice_id` o `gateway_tx_id`) y registrar pagos huérfanos en un ledger.
- Emitir notas crédito (refunds total/parcial) con numeración NC-YYYY-NNNN y email automático al tenant.

**Test de envío real Resend**: ✅ aceptado — `HTTP 200`, `id=69b11f2e-63db-4a74-ae2e-3dffdabdd946`, destino `miguelenruiz1@gmail.com`, subject "Fase 2 test Resend OK" (verificar inbox).

---

## 2. Archivos creados

### subscription-service

- `alembic/versions/015_billing_completeness.py` — migración
- `app/db/models.py` — columnas nuevas + tabla `UnmatchedPayment`
- `app/services/invoice_pdf_service.py` — renderer PDF + helpers Jinja
- `app/services/invoice_pdf/templates/invoice.html` — template A4 enterprise
- `app/services/invoice_pdf/templates/invoice_email.html`
- `app/services/invoice_pdf/templates/dunning_soft.html`
- `app/services/invoice_pdf/templates/dunning_urgent.html`
- `app/services/invoice_pdf/templates/dunning_final.html`
- `app/services/invoice_pdf/templates/receipt.html`
- `app/services/email_client.py` — cliente Resend con retries, caching de credenciales
- `app/services/invoice_service.py` — `send_invoice()`, `issue_credit_note()`
- `app/services/dunning_service.py` — `dunning_check()`, `run_dunning_loop()`
- `app/repositories/unmatched_payment_repo.py`
- `tests/unit/test_invoice_pdf.py` (4 tests)
- `tests/unit/test_email_client.py` (6 tests)
- `tests/unit/test_dunning.py` (3 tests)
- `tests/unit/test_reconciliation.py` (3 tests)
- `tests/unit/test_refund.py` (3 tests)
- `tests/integration/test_api_invoice_send.py` (1 test)

### user-service (mínimo)

- `app/api/routers/internal.py` — 2 endpoints S2S:
  - `GET /api/v1/internal/email-config/{tenant_id}`
  - `GET /api/v1/internal/tenant-owner-email/{tenant_id}`

---

## 3. Archivos modificados

- `subscription-service/requirements.txt` — `+weasyprint>=60.0`, `+jinja2>=3.1.0`
- `subscription-service/app/db/models.py` — invoice.{last_dunning_at, dunning_count, parent_invoice_id, invoice_type} + clase `UnmatchedPayment`
- `subscription-service/app/api/routers/admin.py` — `+POST /admin/dunning/run`, `+POST /admin/webhooks/wompi/replay`, `+GET /admin/unmatched-payments`
- `subscription-service/app/api/routers/subscriptions.py` — `+GET /{t}/invoices/{id}/pdf`, `+POST /{t}/invoices/{id}/send`, `+POST /{t}/invoices/{id}/refund`
- `subscription-service/app/api/routers/webhooks.py` — reconcile por `gateway_tx_id`, ledger de unmatched, receipt email, restauración `past_due` → `active`
- `subscription-service/app/main.py` — schedule `run_dunning_loop()` en lifespan
- `user-service/app/main.py` — incluye `internal_router`

---

## 4. Migraciones alembic nuevas

### 015 — `015_billing_completeness.py`

- `invoices.last_dunning_at TIMESTAMPTZ NULL`
- `invoices.dunning_count INTEGER NOT NULL DEFAULT 0`
- `invoices.parent_invoice_id VARCHAR(36) NULL FK→invoices.id ON DELETE SET NULL`
- `invoices.invoice_type VARCHAR(20) NOT NULL DEFAULT 'standard'` (valores: `standard` | `credit_note`)
- Índices: `ix_invoices_parent_invoice_id`, `ix_invoices_invoice_type`, `ix_invoices_due_date`
- Tabla nueva `unmatched_payments` (id, gateway_slug, gateway_tx_id, reference, amount, currency, raw_payload JSONB, received_at, resolved_at, resolved_invoice_id, notes) con UNIQUE(gateway_slug, gateway_tx_id).

`due_date` ya existía como columna Date nullable (migración 007).

---

## 5. Tests

| Antes | Después |
|-------|---------|
| 23    | 43 (+20 nuevos FASE2) |

Distribución de nuevos tests:

- PDF: 4 (format money, context computation, HTML render, PDF bytes smoke)
- EmailClient: 6 (success, retries 500→200, max retries, 4xx no retry, base64 attachments, no-config)
- Dunning: 3 (classify helper, urgent 5-day, final suspends subscription)
- Reconciliation: 3 (mark paid + reactivate past_due, unmatched ledger, idempotencia)
- Refund: 3 (full refund + void, partial refund keeps paid, no-refund-to-credit-note guard)
- Integration API send: 1 (POST /send + event persistido)

El smoke test de PDF usa `pytest.importorskip("weasyprint")`, por lo que no falla en entornos sin libpango/libcairo; en CI/Docker sí se ejecuta.

---

## 6. Smoke tests curl (>= 10)

Las URLs asumen `gateway` → `subscription-api` montado en `/api/v1/subscriptions/*` y `/api/v1/admin/*`. Reemplazar `$JWT` por un bearer válido de admin del tenant `default` y `$SU_JWT` por un superuser.

```bash
# 1) Listar invoices del tenant
curl -s -o /tmp/out.json -w "HTTP %{http_code}\n" \
  -H "Authorization: Bearer $JWT" \
  http://localhost:9000/api/v1/subscriptions/default/invoices

# 2) Descargar PDF de una invoice
curl -s -o /tmp/invoice.pdf -w "HTTP %{http_code}\n" \
  -H "Authorization: Bearer $JWT" \
  http://localhost:9000/api/v1/subscriptions/default/invoices/INV_ID/pdf
file /tmp/invoice.pdf   # -> PDF document

# 3) Enviar invoice por email
curl -s -X POST -w "HTTP %{http_code}\n" \
  -H "Authorization: Bearer $JWT" \
  http://localhost:9000/api/v1/subscriptions/default/invoices/INV_ID/send

# 4) Re-send (marca method=resend_manual)
curl -s -X POST -w "HTTP %{http_code}\n" \
  -H "Authorization: Bearer $JWT" \
  "http://localhost:9000/api/v1/subscriptions/default/invoices/INV_ID/send?resend=true"

# 5) Refund total (superuser)
curl -s -X POST -w "HTTP %{http_code}\n" \
  -H "Authorization: Bearer $SU_JWT" -H "Content-Type: application/json" \
  -d '{"reason":"Customer request"}' \
  http://localhost:9000/api/v1/subscriptions/default/invoices/INV_ID/refund

# 6) Refund parcial (superuser)
curl -s -X POST -w "HTTP %{http_code}\n" \
  -H "Authorization: Bearer $SU_JWT" -H "Content-Type: application/json" \
  -d '{"reason":"Partial","partial_amount":10000}' \
  http://localhost:9000/api/v1/subscriptions/default/invoices/INV_ID/refund

# 7) Trigger dunning manual (superuser)
curl -s -X POST -w "HTTP %{http_code}\n" \
  -H "Authorization: Bearer $SU_JWT" \
  http://localhost:9000/api/v1/admin/dunning/run

# 8) Replay Wompi webhook (debug / reconciliación manual)
curl -s -X POST -w "HTTP %{http_code}\n" \
  -H "Authorization: Bearer $SU_JWT" -H "Content-Type: application/json" \
  -d '{"transaction_id":"tx_abc","reference":"default:INV_ID","tenant_id":"default","invoice_id":"INV_ID"}' \
  http://localhost:9000/api/v1/admin/webhooks/wompi/replay

# 9) Listar pagos sin conciliar
curl -s -w "HTTP %{http_code}\n" \
  -H "Authorization: Bearer $SU_JWT" \
  http://localhost:9000/api/v1/admin/unmatched-payments

# 10) Endpoint S2S user-service: email config
curl -s -w "HTTP %{http_code}\n" \
  -H "X-Service-Token: $S2S_SERVICE_TOKEN" \
  http://localhost:9001/api/v1/internal/email-config/default

# 11) Endpoint S2S user-service: owner email
curl -s -w "HTTP %{http_code}\n" \
  -H "X-Service-Token: $S2S_SERVICE_TOKEN" \
  http://localhost:9001/api/v1/internal/tenant-owner-email/default

# 12) Webhook real Wompi (signature verificada)
curl -s -X POST -w "HTTP %{http_code}\n" \
  -H "Content-Type: application/json" -H "X-Event-Checksum: $CHECKSUM" \
  -d '{"event":"transaction.updated","timestamp":"...","data":{"transaction":{"id":"tx1","status":"APPROVED","amount_in_cents":4900000,"reference":"default:INV_ID","currency":"COP"}}}' \
  http://localhost:9000/api/v1/payments/webhooks/wompi
```

> **NOTA (regla #3)**: Los endpoints de send/pdf/refund/dunning no se probaron en caliente contra el gateway desde este agente porque el acceso al daemon docker estaba denegado en el entorno. Los contratos están validados vía pytest y el envío real a Resend (ítem 13) confirma la ruta exterior.

### 13) Test real de envío Resend

```bash
curl -X POST "https://api.resend.com/emails" \
  -H "Authorization: Bearer re_FRLbfuhz_2y6oCtYLF1XnBuqJ1M2p4iFs" \
  -H "Content-Type: application/json" \
  -d '{"from":"onboarding@resend.dev","to":["miguelenruiz1@gmail.com"],
       "subject":"Fase 2 test Resend OK",
       "html":"<h2>FASE 2 Billing Completeness</h2>..."}'
# → HTTP 200
# → {"id":"69b11f2e-63db-4a74-ae2e-3dffdabdd946"}
```

**Resend aceptó el envío.** `miguelenruiz1@gmail.com` está dentro de los destinatarios permitidos del sandbox `onboarding@resend.dev`. Verificar inbox (puede caer en Spam/Promociones).

---

## 7. Diseño — decisiones clave

1. **Email config vía user-service S2S** (no duplicar credenciales). `email_client.py` hace
   `GET /api/v1/internal/email-config/{tenant_id}` con `X-Service-Token`. Cache en memoria
   5 minutos. Fallback a env `RESEND_API_KEY` + `RESEND_FROM_EMAIL` si user-service no responde.

2. **PDF side-effect free**: si WeasyPrint no está disponible (dev sin libpango/libcairo)
   el endpoint `/pdf` devuelve `503` y `send` sigue enviando el email sin adjunto —
   nunca crashea el flujo.

3. **Dunning idempotencia**: `WHERE last_dunning_at IS NULL OR < now()-3d` garantiza que
   ningún cliente recibe más de un correo cada 3 días por la misma factura.

4. **Reconciliation robusta**: el webhook intenta match por `invoice_id` del reference,
   luego por `gateway_tx_id` (para replays). Si nada matchea, inserta en ledger
   `unmatched_payments` usando SAVEPOINT (regla #2) para no abortar la transacción
   principal si chocamos el UNIQUE(gateway, tx_id).

5. **Refund**:
   - Credit note = invoice tipo `credit_note` con `amount` negativo y `parent_invoice_id`.
   - Full refund → `parent.status = void`; partial → parent queda `paid`.
   - Numeración atómica propia `NC-YYYY-NNNN` vía `sequence_counters` (scope distinto al de facturas).
   - Email best-effort al tenant con PDF de la nota crédito.

---

## 8. Bugs detectados durante el trabajo (regla #9, flagged)

Ninguno fuera de scope. El trabajo se circunscribió a billing. Se detectaron dos zonas
de mejora que **NO** se tocaron porque están fuera de alcance:

- `EventType` enum solo tiene `payment_received` / `invoice_generated` / `status_change` —
  sería ideal añadir `invoice_sent`, `dunning_sent`, `refund_issued` como event types
  explícitos. Por ahora uso `invoice_generated` con un flag `dunning` / `invoice_sent`
  en el JSON `data` para no romper enum y disparar migración de datos.
- `subscription-service` no tiene aún fetch de datos fiscales completos del tenant
  (NIT, dirección). El PDF usa placeholders si falta. Cuando el tenant tenga
  company_info en algún lado (compliance module o user-service), inyectarlo vía
  `tenant_info=` al `render_invoice_pdf`.

---

## 9. TODOs conocidos

1. **Dominio propio en Resend**: hoy usamos sandbox `onboarding@resend.dev` que solo
   puede enviar a emails verificados del owner. Para producción, verificar dominio
   `tracelog.co` en Resend dashboard y actualizar `from_email` en
   `email_provider_configs`. Sin esto, los clientes reales NO reciben correos.

2. **Docker**: no se pudo ejecutar `docker compose build subscription-api` en esta
   sesión (permiso denegado). Pasos pendientes para el deploy local:
   ```
   docker compose build subscription-api
   docker compose up -d subscription-api
   docker compose exec subscription-api alembic upgrade head   # aplica 015
   docker compose restart gateway   # regla #4
   ```

3. **Weasyprint en Dockerfile**: asegurar que el Dockerfile de `subscription-api`
   tiene los system libs (`apt-get install -y libpango-1.0-0 libpangoft2-1.0-0
   libcairo2 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info fonts-inter`). Si no,
   `render_invoice_pdf` lanzará `RuntimeError` y los endpoints devolverán 503.

4. **Event enum migration (futuro)**: añadir `invoice_sent`, `dunning_sent`,
   `refund_issued` a `EventType` con migración alembic + reemplazar los reusos
   actuales de `invoice_generated` / `status_change` en `invoice_service.py` y
   `dunning_service.py`.

5. **Wompi refund real (Task 5 v2)**: el endpoint `/refund` hoy sólo crea la
   credit note en DB. Integrar llamada a Wompi API `POST /v1/transactions/{id}/refund`
   cuando haya endpoint disponible en el provider.

6. **Cloudflare / DNS records Resend**: SPF / DKIM / DMARC para el dominio cuando
   se verifique, para evitar que los correos caigan en spam.

7. **Probar flujo E2E desde el browser**: el usuario debe probar:
   - Crear invoice → descargar PDF → recibir email.
   - Dejar pasar fecha de vencimiento → verificar que dunning automatico dispara.
   - Pagar por Wompi → verificar que el webhook mueve a paid y manda receipt.

---

## 10. Checklist regla #14 (smoke post-deploy)

Cuando el usuario deploye a producción:

```bash
gcloud run services logs read subscription-service --region southamerica-east1 \
  --project trace-log --limit 50 | grep -iE "error|exception|traceback"

curl -s -o /tmp/x.json -w "HTTP %{http_code}\n" \
  "https://<gateway>/api/v1/subscriptions/default/invoices" \
  -H "Authorization: Bearer $JWT"
# → HTTP 200

curl -s -o /tmp/p.pdf -w "HTTP %{http_code}\n" \
  "https://<gateway>/api/v1/subscriptions/default/invoices/<ID>/pdf" \
  -H "Authorization: Bearer $JWT"
file /tmp/p.pdf   # → PDF document

# Verificar migración corrió
gcloud run services logs read subscription-service --region southamerica-east1 \
  --project trace-log --limit 50 | grep "015"
```
