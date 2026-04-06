# Trace

> Plataforma SaaS multi-tenant para PYMEs latinoamericanas: inventario, facturación electrónica DIAN, trazabilidad blockchain y cumplimiento EUDR — todo en un solo producto.

[![License: Proprietary](https://img.shields.io/badge/license-proprietary-red)](#)
[![Stack](https://img.shields.io/badge/stack-FastAPI%20%7C%20React%2019%20%7C%20PostgreSQL%20%7C%20Redis%20%7C%20Solana-blue)](#)
[![Cloud](https://img.shields.io/badge/cloud-GCP%20Cloud%20Run-orange)](#)

---

## 🌎 Qué resuelve

Las PYMEs colombianas (cooperativas, exportadoras, distribuidoras) hoy usan **3-5 herramientas distintas** para manejar inventario, facturar a la DIAN, demostrar origen del producto y cumplir regulaciones europeas (EUDR). Trace unifica todo eso en una sola plataforma con cumplimiento legal real, no demos.

**Casos de uso reales:**
- 🌱 Cooperativa de café exporta a Alemania bajo Reglamento UE 2023/1115 (EUDR) con polígonos satelitales validados
- 📦 Distribuidor de alimentos manejando 1000 SKUs en 5 bodegas con kardex valorizado y costo promedio ponderado
- 🧾 PYMEs facturando ante DIAN con CUFE real y soporte para los 6 tipos de documento (FEV, NC, ND, DS, POS, ER)
- 🔗 Lotes con trazabilidad on-chain en Solana — cada cliente puede verificar el origen vía QR público

---

## 🏗️ Arquitectura

Microservicios FastAPI desplegados en **GCP Cloud Run** con PostgreSQL Cloud SQL, Memorystore Redis, y Artifact Registry.

```
┌─────────────────────────────────────────────────────────────────┐
│                       front-trace (React 19)                    │
│            Vite • TypeScript • TanStack Query • Tailwind        │
└─────────────────────────────────────────────────────────────────┘
                                │
                       ┌────────▼────────┐
                       │   gateway/nginx │  CORS allowlist + JWT
                       └────────┬────────┘
        ┌──────────────┬────────┼────────┬──────────────┐
        │              │        │        │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌▼──────┐ ┌▼────────────┐ ┌▼──────────┐
│ user-service │ │ inventory- │ │trace- │ │compliance-  │ │integration│
│ JWT/RBAC/    │ │ service    │ │service│ │service      │ │service    │
│ Audit        │ │ Stock/PO/  │ │Custody│ │EUDR/GFW/    │ │Matias     │
│              │ │ SO/Kardex  │ │Solana │ │TRACES NT    │ │DIAN       │
└──────────────┘ └────────────┘ └───────┘ └─────────────┘ └───────────┘
        │              │            │           │
┌───────▼──────────────▼────────────▼───────────▼────────────────┐
│         subscription-service       │     ai-service             │
│         Plans/Billing/Modules      │     Claude Haiku analysis  │
└────────────────────────────────────┴────────────────────────────┘
                            │
                  ┌─────────▼─────────┐
                  │   media-service   │  S3/GCS uploads
                  └───────────────────┘
```

### Microservicios

| Servicio | Puerto | Responsabilidad |
|---|---|---|
| `user-service` | 8001 | Auth JWT, RBAC con 26 permisos, audit log append-only |
| `subscription-service` | 8002 | Billing SaaS, planes, módulos activables por tenant |
| `inventory-service` | 8003 | Productos, bodegas, OC/OV, kardex con costo ponderado |
| `integration-service` | 8004 | Facturación electrónica DIAN vía Matias API (UBL 2.1) |
| `compliance-service` | 8005 | EUDR, GFW deforestación, TRACES NT DDS, certificados |
| `ai-service` | 8006 | Análisis de rentabilidad e inteligencia de inventario |
| `media-service` | 8007 | Gestión de archivos con S3/GCS, MIME validation |
| `trace-service` | 8000 | Cadena de custodia + anclaje en Solana (cNFT + Memo) |

---

## 🔒 Seguridad y multi-tenancy

- **JWT auth** con rate limiting (login 5/15min, register 10/h, forgot 3/h)
- **`secrets.compare_digest`** en todas las comparaciones de tokens (anti-timing)
- **Multi-tenant strict isolation**: cada query filtra por `tenant_id`, repos defense-in-depth
- **Sequence counters atómicos** para PO/SO/Invoice/Cert numbering (sin race conditions fiscales)
- **Stock layer atomic UPDATEs** para evitar overselling en concurrencia
- **Hash chain** criptográfica en custody events anclada en Solana via Memo Program
- **Audit logs append-only** via PG trigger (Hábeas Data / GDPR ready)
- **CHECK constraints** en enums de status para invariantes a nivel DB
- **Validators fail-closed** para JWT_SECRET / FERNET_KEY / S2S_TOKEN al boot en producción

---

## 📊 Observability

- **Prometheus** `/metrics` en los 8 services (`prometheus-fastapi-instrumentator`)
- **OpenTelemetry tracing** opcional via `OTEL_EXPORTER_OTLP_ENDPOINT` (Jaeger / Honeycomb / Tempo)
- **Correlation IDs** propagados end-to-end (frontend → gateway → backend)
- **Structured logging** con `structlog`
- **Healthchecks** distinguen liveness (`/health`) vs readiness (`/ready`, verifica DB + Redis)

---

## 🚀 Quick start (desarrollo local)

```bash
# 1. Levantar todos los servicios + DBs
docker-compose up -d

# 2. Aplicar migraciones a cada servicio
for svc in user-service subscription-service inventory-service trace-service compliance-service integration-service ai-service media-service; do
  docker-compose exec $svc alembic upgrade head
done

# 3. Frontend
cd front-trace
npm install
npm run dev
# → http://localhost:5173

# 4. Usuario default
# email: admin@trace.local
# password: admin (cambiar en primer login)
```

---

## ⚙️ Variables de entorno críticas

Antes de deploy a producción, configurar (NUNCA usar defaults):

```bash
# Auth
JWT_SECRET=<32+ char strong random>          # mismo en todos los services
S2S_SERVICE_TOKEN=<32+ char strong random>   # mismo en todos los services
TRACE_ADMIN_KEY=<32+ char strong random>
FERNET_KEY=<output of: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">

# Environment switch (activa validators fail-closed)
ENV=production

# DBs (Cloud SQL connection strings)
DATABASE_URL=postgresql+asyncpg://...

# Observability (opcional)
OTEL_EXPORTER_OTLP_ENDPOINT=https://...

# Storage
CERTIFICATE_STORAGE=gcs
AWS_BUCKET_NAME=trace-certificates-prod
```

Ver `.env.example` en cada microservicio para la lista completa.

---

## 🔧 Stack técnico

**Backend:** FastAPI · Python 3.12 · SQLAlchemy 2.0 async · asyncpg · Alembic · Redis · ARQ workers · PyJWT · Pydantic v2 · structlog · Prometheus

**Frontend:** React 19 · Vite 6 · TypeScript · TanStack Query · React Router · Zustand · Tailwind · shadcn/ui · Radix · React Hook Form · zod · DOMPurify · Leaflet

**Blockchain:** Solana · Helius · cNFT (compressed NFTs) · Memo Program

**IA:** Anthropic Claude Haiku 4.5

**Integraciones:** Matias API (DIAN Colombia, UBL 2.1) · Global Forest Watch · TRACES NT (EU Commission)

**Infra:** GCP Cloud Run · Cloud SQL · Memorystore · Artifact Registry · GitHub Actions · Docker multi-stage

---

## 📁 Estructura del repo

```
.
├── user-service/             # Auth, RBAC, audit
├── subscription-service/     # Plans, billing, modules
├── inventory-service/        # Stock, PO/SO, kardex
├── trace-service/            # Custody chain, Solana anchoring
├── compliance-service/       # EUDR, GFW, TRACES NT
├── integration-service/      # DIAN e-invoicing
├── ai-service/               # Claude analysis
├── media-service/            # File storage
├── gateway/                  # nginx CORS + auth proxy
├── front-trace/              # React frontend
├── docker-compose.yml        # Local development
└── .github/workflows/        # CI/CD
```

---

## 📄 Licencia

Propietario — © 2026 Trace. Todos los derechos reservados.
