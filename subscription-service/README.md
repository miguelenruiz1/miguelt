# subscription-service

> Billing SaaS, planes, módulos activables, licencias y CMS de páginas públicas.

**Puerto:** 8002 (interno) · 9002 (externo)
**DB:** `subscription-postgres:5439` · **Redis:** `db=3`

## Responsabilidades

- Plans (Free / Starter / Professional / Enterprise)
- Subscriptions tenant-scoped (UNIQUE per tenant)
- Invoices con numeración fiscal atómica (`INV-YYYY-NNNN`)
- License keys con max_activations
- Module activation (logistics, inventory, compliance)
- Payment gateway (Wompi)
- CMS para landing pages públicas

## Endpoints clave

```
GET    /api/v1/plans                                # Public catalog
POST   /api/v1/subscriptions                         # Auto on register
GET    /api/v1/subscriptions/{tenant_id}            # Tenant-guarded
PATCH  /api/v1/subscriptions/{tenant_id}            # Plan upgrade (tenant-guarded)
POST   /api/v1/subscriptions/{tenant_id}/cancel     # Tenant-guarded

GET    /api/v1/modules/                             # Public catalog
GET    /api/v1/modules/{tenant_id}                  # Per-tenant status
POST   /api/v1/modules/{tenant_id}/{slug}/activate  # Tenant-guarded

GET    /api/v1/licenses
POST   /api/v1/licenses
GET    /api/v1/licenses/validate/{key}              # Public

GET    /api/v1/payments/catalog                     # Public
GET    /api/v1/payments/{tenant_id}/active          # Public (active gateway)

POST   /api/v1/cms/pages                            # CMS pages
GET    /p/{slug}                                    # Public page render
```

## Concurrency-safe numbering

`InvoiceRepository.next_invoice_number()` usa la tabla `sequence_counters` con UPSERT atómico:

```sql
INSERT INTO sequence_counters (scope, value, updated_at)
VALUES ('invoice-2026', 1, NOW())
ON CONFLICT (scope) DO UPDATE
    SET value = sequence_counters.value + 1
RETURNING value
```

Migración 011. Reemplaza el legacy `MAX(invoice_number)+1` que tenía race conditions fiscales.

## Multi-tenancy

- Endpoints `{tenant_id}` en path con `_enforce_tenant_match` guard (no IDOR)
- License repo defense in depth con `tenant_id` filter

## Data integrity

- `Subscription.plan_id` ondelete **RESTRICT** (no CASCADE — protege historia de billing)
- `Invoice.amount` Numeric(18,2) — soporta facturas COP grandes

## Variables de entorno

```bash
DATABASE_URL=postgresql+asyncpg://sub_svc:subpass@subscription-postgres:5439/subscriptiondb
REDIS_URL=redis://redis:6379/3
USER_SERVICE_URL=http://user-api:8001
INTEGRATION_SERVICE_URL=http://integration-api:8004
JWT_SECRET=<32+ char>
ENV=production
```

## Migraciones

12 migraciones. Las más recientes:
- `011` — sequence counters
- `012` — plan_id RESTRICT
