# Trace Platform — Informe de Infraestructura Cloud

**Fecha:** 31 de marzo de 2026
**Proveedor:** Google Cloud Platform (GCP)
**Proyecto:** trace-log
**Region:** southamerica-east1 (Sao Paulo, Brasil)

---

## 1. Arquitectura Desplegada

```
                    Internet
                       │
                       ▼
              ┌─────────────────┐
              │    Frontend     │  Cloud Run (Nginx + React build)
              │  128Mi, 0-5    │  https://frontend-e7ujx6tiba-rj.a.run.app
              └───────┬─────────┘
                      │
                      ▼
              ┌─────────────────┐
              │    Gateway      │  Cloud Run (Nginx reverse proxy)
              │  256Mi, 1-10   │  https://gateway-e7ujx6tiba-rj.a.run.app
              └───────┬─────────┘
                      │ Rutea por path /api/v1/*
          ┌───────────┼───────────────────────────────┐
          ▼           ▼           ▼           ▼       ▼
    ┌──────────┐┌──────────┐┌──────────┐┌──────────┐┌──────────┐
    │ user-api ││ sub-api  ││ inv-api  ││trace-api ││ comply   │ ...
    │ 512Mi    ││ 256Mi    ││ 512Mi    ││ 512Mi    ││ 512Mi    │
    │ min:1    ││ min:1    ││ min:0    ││ min:0    ││ min:0    │
    └────┬─────┘└────┬─────┘└────┬─────┘└────┬─────┘└────┬─────┘
         │           │           │           │           │
         └─────────┬─┴───────────┴───────────┴───────────┘
                   │              │
          ┌────────▼──────┐  ┌───▼───────────┐
          │  Cloud SQL    │  │   Redis       │
          │  PostgreSQL 16│  │  Memorystore  │
          │  db-g1-small  │  │  7.0, 1GB     │
          │  8 databases  │  │  10.139.47.27 │
          │ 35.247.234.143│  └───────────────┘
          └───────────────┘
```

---

## 2. Servicios Cloud Run (10 containers)

| Servicio | URL | RAM | Min | Max | Estado |
|---|---|---|---|---|---|
| **frontend** | frontend-e7ujx6tiba-rj.a.run.app | 128Mi | 1 | 5 | Siempre activo |
| **gateway** | gateway-e7ujx6tiba-rj.a.run.app | 256Mi | 1 | 10 | Siempre activo |
| **user-api** | user-api-e7ujx6tiba-rj.a.run.app | 512Mi | 1 | 5 | Siempre activo |
| **subscription-api** | subscription-api-e7ujx6tiba-rj.a.run.app | 256Mi | 1 | 5 | Siempre activo |
| **trace-api** | trace-api-e7ujx6tiba-rj.a.run.app | 512Mi | 0 | 5 | Scale to zero |
| **inventory-api** | inventory-api-e7ujx6tiba-rj.a.run.app | 512Mi | 0 | 5 | Scale to zero |
| **compliance-api** | compliance-api-e7ujx6tiba-rj.a.run.app | 512Mi | 0 | 5 | Scale to zero |
| **integration-api** | integration-api-e7ujx6tiba-rj.a.run.app | 256Mi | 0 | 5 | Scale to zero |
| **ai-api** | ai-api-e7ujx6tiba-rj.a.run.app | 256Mi | 0 | 5 | Scale to zero |
| **media-api** | media-api-e7ujx6tiba-rj.a.run.app | 256Mi | 0 | 5 | Scale to zero |

**Servicios siempre activos (4):** frontend, gateway, user-api, subscription-api — son los que se usan en cada request.

**Servicios bajo demanda (6):** se despiertan cuando se necesitan (~2-3s cold start), luego quedan activos 15 min.

---

## 3. Base de Datos

### Cloud SQL PostgreSQL 16
- **Instancia:** trace-db
- **Tier:** db-g1-small (1 vCPU, 1.7GB RAM)
- **Storage:** 10GB SSD (auto-increase)
- **IP Publica:** 35.247.234.143
- **Backup:** Automatico diario (retencion 7 dias, incluido en Cloud SQL)
- **8 databases en 1 instancia:**

| Base de datos | Servicio | Contenido |
|---|---|---|
| tracedb | trace-api | Assets, custody, wallets, workflows, blockchain |
| userdb | user-api | Users, roles, permissions, audit, email |
| subdb | subscription-api | Plans, subscriptions, invoices, modules, payments |
| inventorydb | inventory-api | Products, stock, warehouses, orders, production |
| integrationdb | integration-api | E-invoicing configs, webhooks, resolutions |
| compliancedb | compliance-api | Frameworks, plots, records, certificates |
| aidb | ai-api | AI analysis history, settings, memory |
| mediadb | media-api | File metadata, references |

### Redis Memorystore 7.0
- **Instancia:** trace-redis
- **Memoria:** 1GB
- **IP Privada:** 10.139.47.27:6379
- **8 databases logicas:** DB 0-1 (trace), DB 2 (user), DB 3 (sub), DB 4 (inv), DB 5 (integ), DB 6 (comply), DB 7 (ai), DB 8 (media)

---

## 4. Networking

### VPC Connector
- **Nombre:** trace-connector
- **Rango IP:** 10.8.0.0/28
- **Proposito:** Permite que Cloud Run (serverless) acceda a Redis Memorystore (que solo tiene IP privada)
- **Usado por:** Todos los servicios backend que necesitan Redis

### Conectividad
- Cloud Run → Cloud SQL: via IP publica (35.247.234.143)
- Cloud Run → Redis: via VPC connector → IP privada (10.139.47.27)
- Frontend → Gateway: via HTTPS publico
- Gateway → Servicios: via HTTPS publico (Cloud Run URLs)
- Servicios entre si: via HTTPS publico (Cloud Run URLs)

---

## 5. Artifact Registry (Docker Images)

**Repositorio:** southamerica-east1-docker.pkg.dev/trace-log/trace

| Imagen | Tipo |
|---|---|
| frontend | Nginx + React build estatico |
| gateway | Nginx reverse proxy |
| user-api | Python 3.11 FastAPI |
| subscription-api | Python 3.11 FastAPI |
| trace-api | Python 3.11 FastAPI |
| inventory-api | Python 3.11 FastAPI |
| integration-api | Python 3.11 FastAPI |
| compliance-api | Python 3.11 FastAPI |
| ai-api | Python 3.11 FastAPI |
| media-api | Python 3.11 FastAPI |

Todas las imagenes usan multi-stage builds optimizados (~150-200MB cada una).

---

## 6. Seguridad

| Capa | Mecanismo |
|---|---|
| HTTPS | Automatico en Cloud Run (certificados gestionados por Google) |
| Autenticacion | JWT (HS256), tokens de acceso 8h, refresh 7d |
| Secrets | JWT_SECRET, S2S_TOKEN, ENCRYPTION_KEY generados con openssl rand |
| DB Access | IP publica con password, usuario unico "trace" |
| Redis | Solo accesible via VPC privada (no expuesto a internet) |
| Service Account | github-deploy con roles minimos (run.admin, artifactregistry.writer) |
| CORS | Centralizado en el gateway Nginx |

### Secrets Configurados
- `JWT_SECRET` — Compartido entre todos los servicios para validar tokens
- `S2S_SERVICE_TOKEN` — Para comunicacion entre servicios (trace, user, inventory, compliance, media)
- `ENCRYPTION_KEY` — Para cifrar credenciales de integraciones (integration-service)
- `TRACE_ADMIN_KEY` — Para operaciones de release/blockchain
- `DB_PASSWORD` — Password de Cloud SQL

---

## 7. Despliegue Continuo (CI/CD)

### Pipeline (GitHub Actions)
**Archivo:** `.github/workflows/deploy.yml`
**Trigger:** Push a branch `main`

```
git push origin main
       │
       ▼
┌─────────────────────────────┐
│  build-images (paralelo)    │  ~5 min
│  9 Docker builds + push     │
│  al Artifact Registry       │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│  deploy-services (3 a la vez)│  ~3 min
│  8 servicios → Cloud Run    │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│  deploy-gateway             │  ~1 min
│  Lee URLs de los servicios  │
│  Configura upstreams        │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│  deploy-frontend            │  ~2 min
│  npm build con VITE_API_URL │
│  del gateway                │
│  Deploy a Cloud Run         │
└─────────────────────────────┘
```

**Tiempo total de deploy:** ~12 minutos de push a produccion

### GitHub Secrets Requeridos
| Secret | Descripcion |
|---|---|
| `GCP_PROJECT_ID` | trace-log |
| `GCP_SA_KEY` | JSON de service account github-deploy |

### Estado Actual
El workflow esta creado localmente en `.github/workflows/deploy.yml` pero **pendiente de subir a GitHub** (requiere token con scope `workflow`).

---

## 8. URLs de Acceso

### Produccion
| Recurso | URL |
|---|---|
| **Frontend (App)** | https://frontend-e7ujx6tiba-rj.a.run.app |
| **API Gateway** | https://gateway-e7ujx6tiba-rj.a.run.app |
| **Health Check** | https://gateway-e7ujx6tiba-rj.a.run.app/health |

### Superusuario
| Campo | Valor |
|---|---|
| Email | miguelenruiz1@gmail.com |
| Tenant | platform |
| Rol | Superuser + Administrador |

---

## 9. Costos Estimados (mensual)

| Recurso | Costo |
|---|---|
| Cloud SQL (db-g1-small) | ~$25 |
| Redis Memorystore (1GB basic) | ~$35 |
| Cloud Run - 4 instancias activas (gateway, frontend, user, sub) | ~$15 |
| Cloud Run - 6 instancias bajo demanda | ~$5 |
| Artifact Registry (storage) | ~$1 |
| VPC Connector | ~$7 |
| Networking (egress) | ~$2 |
| **Total estimado** | **~$90/mes** |

### Optimizaciones Futuras para Reducir Costos
- Migrar Cloud SQL a db-f1-micro cuando tenga bajo trafico ($10/mes vs $25)
- Reducir Redis a 0.5GB si no se necesita mas cache
- Mover servicios poco usados (ai-api, integration-api) a instancias mas pequenas (128Mi)

---

## 10. Monitoreo

### Incluido en GCP (sin costo extra)
- **Cloud Run Metrics:** Requests/seg, latencia, errores, instancias activas
- **Cloud SQL Metrics:** CPU, memoria, conexiones, storage
- **Logs:** Todos los servicios escriben a Cloud Logging automaticamente (stdout/stderr capturado)

### Acceso
- **Console:** console.cloud.google.com → Cloud Run → Seleccionar servicio → Metrics/Logs
- **Logs en vivo:** `gcloud run services logs read SERVICE_NAME --region=southamerica-east1`
- **Alertas:** Configurables en Cloud Monitoring (email/SMS cuando un servicio falle)

---

## 11. Comparacion Dev vs Prod

| Aspecto | Desarrollo (local) | Produccion (GCP) |
|---|---|---|
| PostgreSQL | 8 instancias Docker | 1 Cloud SQL, 8 databases |
| Redis | 1 Docker, 8 DBs logicas | 1 Memorystore, 8 DBs logicas |
| Frontend | Vite dev server (:3000) | Nginx Cloud Run (static build) |
| Gateway | Nginx Docker (:9000) | Nginx Cloud Run (HTTPS auto) |
| SSL | No | Si (automatico, gestionado por Google) |
| Puertos expuestos | 7+ servicios | 2 (frontend + gateway) |
| Auto-scaling | No | Si (0-10 instancias) |
| Backups | Manual | Automatico (Cloud SQL) |
| Logs | Docker stdout | Cloud Logging centralizado |
| Costo | $0 (tu PC) | ~$90/mes |

---

## 12. Archivos de Configuracion

| Archivo | Ubicacion | Proposito |
|---|---|---|
| docker-compose.yml | raiz | Desarrollo local (8 postgres) |
| deploy/docker-compose.production.yml | deploy/ | Produccion con Docker Compose (1 postgres) |
| deploy/env.production.template | deploy/ | Template de variables de entorno |
| deploy/init-databases.sql | deploy/ | Script para crear 8 BDs |
| deploy/setup-gcp.sh | deploy/ | Script de setup inicial GCP |
| gateway/nginx.conf | gateway/ | Routing local (Docker DNS) |
| gateway/nginx.conf.template | gateway/ | Routing cloud (env vars dinamicas) |
| .github/workflows/deploy.yml | .github/ | Pipeline CI/CD (pendiente subir) |
| front-trace/Dockerfile | front-trace/ | Build estatico + Nginx |
