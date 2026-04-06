# media-service

> Gestión de archivos (uploads, validación MIME, storage S3/GCS) para todos los microservicios.

**Puerto:** 8007 (interno) · 9007 (externo)
**DB:** `media-postgres:5443` · **Redis:** `db=8`

## Responsabilidades

- Upload de archivos con MIME validation y allowlist por categoría
- Storage backend pluggable (LocalStorage / S3 / GCS)
- Path traversal hardening (sanitización de filename y category)
- Per-tenant isolation
- File metadata (hash SHA256, content-type, tamaño)

## Seguridad

- ✅ JWT auth obligatorio (era el bug crítico — antes aceptaba cualquier `X-Tenant-Id`)
- ✅ `tenant_id` derivado del JWT validado, NO del header
- ✅ Path traversal cerrado: `_sanitize_segment()` + `_sanitize_filename()` + path resolve check
- ✅ MIME allowlist (`ALLOWED_MIME_TYPES` config)
- ✅ Category enum (`ALLOWED_CATEGORIES`)
- ✅ Max upload size 50MB

## Endpoints clave

```
POST   /api/v1/media/files                # Upload (multipart)
GET    /api/v1/media/files                # List per tenant
GET    /api/v1/media/files/{id}
DELETE /api/v1/media/files/{id}
GET    /api/v1/internal/media/files/{id}  # S2S, requires X-Service-Token
```

## Variables de entorno

```bash
DATABASE_URL=postgresql+asyncpg://media_svc:mediapass@media-postgres:5443/mediadb
REDIS_URL=redis://redis:6379/8
JWT_SECRET=<32+ char>
S2S_SERVICE_TOKEN=<32+ char>
USER_SERVICE_URL=http://user-api:8001

# Storage
STORAGE_BACKEND=s3                          # local | s3
DOCUMENT_MAX_SIZE_MB=50
AWS_S3_BUCKET=trace-media-prod
AWS_S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>

ENV=production
```
