# compliance-service

> Cumplimiento normativo internacional: EUDR (UE 2023/1115), Global Forest Watch screening, sumisión DDS a TRACES NT, generación de certificados PDF verificables.

**Puerto:** 8005 (interno) · 9005 (externo)
**DB:** `compliance-postgres:5441` · **Redis:** `db=5`

## Responsabilidades

- Frameworks regulatorios (EUDR, USDA Organic, FSSAI, JFS-2200, etc.)
- Tenant framework activations
- Plots (parcelas de producción) con polígonos GeoJSON
- Compliance records linkando assets a frameworks
- Screening satelital de deforestación via Global Forest Watch API
- Sumisión DDS a TRACES NT (UE) via SOAP/WS-Security
- Generación de certificados PDF con QR público y blockchain anchor
- Risk assessments (EUDR Art. 10-11)
- Supply chain nodes (EUDR Art. 9.1.e-f)
- Document evidence linking
- Per-tenant encrypted credentials para GFW y TRACES NT (Fernet)

## Endpoints clave

```
GET    /api/v1/compliance/frameworks
POST   /api/v1/compliance/activations
GET    /api/v1/compliance/plots
POST   /api/v1/compliance/plots
POST   /api/v1/compliance/plots/{id}/screen-deforestation   # GFW real query
GET    /api/v1/compliance/records
POST   /api/v1/compliance/records                            # asset_id optional (standalone)
POST   /api/v1/compliance/records/{id}/plots                 # Cross-tenant link blocked
POST   /api/v1/compliance/records/{id}/export-dds            # JSON DDS payload
POST   /api/v1/compliance/records/{id}/submit-traces         # SOAP submission, idempotent
POST   /api/v1/compliance/records/{id}/certificate           # Generates PDF + uploads
GET    /api/v1/compliance/certificates/{id}/download         # Redirects to S3/GCS

GET    /api/v1/compliance/verify/{certificate_number}        # PUBLIC, no auth
PATCH  /api/v1/compliance/integrations/{provider}            # Per-tenant credentials
```

## Seguridad

- ✅ Per-tenant encrypted credentials (Fernet, `(tenant_id, provider)` UNIQUE)
- ✅ `FERNET_KEY` settings dedicado (no derivado de JWT_SECRET en prod)
- ✅ SOAP envelope con `xml.sax.saxutils.escape()` (anti-injection)
- ✅ WS-Security UsernameToken con `<wsu:Expires>` (TRACES NT requirement)
- ✅ Polygons reales en DDS (no Point cuando hay polígono real)
- ✅ Plot link cross-tenant validation (no certificate forgery)
- ✅ `LocalStorage` rechazado en Cloud Run (`K_SERVICE` env detection)
- ✅ Certificate download path validation (defense in depth)
- ✅ `/verify` excluido del TenantMiddleware (público)

## Data integrity

- `compliance_plots` CHECK constraints: lat ∈ [-90,90], lng ∈ [-180,180], area>0, risk_level enum, geolocation_type enum
- `compliance_records` CHECK constraints: compliance_status enum, declaration_status enum
- `compliance_records.asset_id` nullable (standalone records permitidos)
- Partial unique indexes: linked vs standalone records
- Sequence counter atómico para certificate numbering (`TL-{year}-{seq:06d}`)

## Variables de entorno

```bash
DATABASE_URL=postgresql+asyncpg://cmp_svc:cmppass@compliance-postgres:5441/compliancedb
REDIS_URL=redis://redis:6379/5
USER_SERVICE_URL=http://user-api:8001
TRACE_SERVICE_URL=http://trace-api:8000
MEDIA_SERVICE_URL=http://media-api:8007
JWT_SECRET=<32+ char>
S2S_SERVICE_TOKEN=<32+ char>
FERNET_KEY=<base64 fernet key>            # Validator fail-closed en prod

# Storage
CERTIFICATE_STORAGE=gcs                    # local | s3 | gcs
AWS_BUCKET_NAME=trace-certificates-prod

# Optional defaults (per-tenant credentials override these)
GFW_API_KEY=<gfw key>
TRACES_NT_USERNAME=<eu username>
TRACES_NT_AUTH_KEY=<eu auth key>
TRACES_NT_ENV=acceptance                   # acceptance | production
TRACES_NT_CLIENT_ID=eudr-test
TRACES_NT_TIMEOUT=180.0
GFW_TIMEOUT=120.0
ENV=production
```

## Migraciones

19 migraciones. Las más recientes:
- `015` — sequence counters (cert numbering)
- `016` — plot CHECK constraints (lat/lng/area)
- `017` — records partial unique
- `018` — record status CHECK
- `019` — plot risk_level + geolocation_type CHECK
