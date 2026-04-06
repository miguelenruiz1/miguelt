# user-service

> Auth, RBAC con 26 permisos granulares, y audit log inmutable para la plataforma Trace.

**Puerto:** 8001 (interno) · 9001 (externo)
**DB:** `user-postgres:5438` · **Redis:** `db=2`

## Responsabilidades

- Autenticación JWT (access 15min + refresh 7d con jti)
- Refresh token rotation con blacklist en Redis
- 26 permisos sembrados en 7 módulos (admin, inventory, subscription, compliance, etc.)
- Roles tenant-scoped + role templates
- Audit log append-only via PG trigger (Hábeas Data / GDPR ready)
- Email templates (invitación, password reset, etc.)
- Onboarding flow

## Endpoints clave

```
POST   /api/v1/auth/register           # Rate limited 10/h/IP
POST   /api/v1/auth/login              # Rate limited 5/15min/IP
POST   /api/v1/auth/refresh            # Rotates jti
POST   /api/v1/auth/logout             # Blacklists current jti
GET    /api/v1/auth/me
POST   /api/v1/auth/forgot-password    # Rate limited 3/h/IP, timing-padded
POST   /api/v1/auth/reset-password

GET    /api/v1/users                   # Tenant-scoped list
GET    /api/v1/users/{id}              # IDOR-safe
PATCH  /api/v1/users/{id}              # Tenant-scoped
POST   /api/v1/users/{id}/roles/{rid}  # Cross-tenant assignment blocked

GET    /api/v1/roles                   # Tenant-scoped
PUT    /api/v1/roles/{id}/permissions  # Tenant-scoped

GET    /api/v1/audit                   # Append-only log
```

## Seguridad

- ✅ JWT validators fail-closed en boot (`ENV=production`)
- ✅ `secrets.compare_digest` para token comparisons
- ✅ Rate limiting via Redis-backed sliding window
- ✅ Forgot password timing-padded a 300ms (anti email enumeration)
- ✅ `_enforce_user_limit` fail-CLOSED en prod (no DoS bypass de billing)
- ✅ Audit logs append-only via `BEFORE UPDATE/DELETE` trigger
- ✅ PII scrubbing helpers (`audit_retention_service.anonymize_user_audit_logs`)

## Multi-tenancy

`User.email` y `User.username` son **unique per tenant** (no global), permitiendo que `admin@empresa.com` exista en múltiples tenants. Migración 016.

## Variables de entorno

```bash
DATABASE_URL=postgresql+asyncpg://user_svc:userpass@user-postgres:5438/userdb
REDIS_URL=redis://redis:6379/2
JWT_SECRET=<32+ char>           # Validator fail-closed en prod
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
S2S_SERVICE_TOKEN=<32+ char>
SUBSCRIPTION_SERVICE_URL=http://subscription-api:8002
ENV=production                  # Activa validators
```

## Migraciones

17 migraciones aplicadas. Las más recientes:
- `015` — permisos compliance
- `016` — users unique per tenant
- `017` — audit logs append-only trigger

## Tests

```bash
pytest tests/
```
