# TRACE — Informe Tecnico Completo

## Arquitectura

Plataforma SaaS multi-tenant con 8 microservicios independientes comunicandose via REST API.

```
FRONTEND (React/Vite) → GATEWAY (nginx) → 8 MICROSERVICIOS → 8 PostgreSQL + Redis
```

### Servicios

| Servicio | Puerto | Base de Datos | Funcion |
|----------|--------|---------------|---------|
| trace-service | 8000 | trace-postgres | Cadena de custodia, wallets, Solana |
| user-service | 8001 | user-postgres | Auth, RBAC, audit, email |
| subscription-service | 8002 | subscription-postgres | SaaS billing, planes, modulos, pagos |
| inventory-service | 8003 | inventory-postgres | Productos, stock, ordenes, produccion, IA |
| integration-service | 8004 | integration-postgres | Facturacion electronica, DIAN, Matias API |
| compliance-service | 8005 | compliance-postgres | EUDR, USDA, FSSAI frameworks |
| ai-service | 8006 | ai-postgres | Analisis con Claude Haiku 4.5 |
| media-service | 8007 | media-postgres | Imagenes, archivos, S3 |
| gateway | 9000 | — | nginx routing y CORS |
| frontend | 5173 | — | React/TypeScript UI |

## Stack Tecnologico

### Backend
- Python 3.12+ / FastAPI
- SQLAlchemy 2.0 async + asyncpg
- Redis 7 (cache + colas ARQ)
- JWT (access 15min + refresh 7d)

### Frontend
- TypeScript 5.7 / React 19 / Vite
- Tailwind CSS 3
- Zustand + React Query
- React Router v6

### Cloud & DevOps
- GCP Cloud Run (serverless)
- Cloud SQL (PostgreSQL 16)
- Memorystore (Redis 7)
- GitHub Actions CI/CD
- Docker + docker-compose

### Integraciones Externas
- **Solana** — Blockchain anchoring (Helius DAS API)
- **Anthropic Claude Haiku 4.5** — Analisis IA de rentabilidad
- **Matias API** — Facturacion electronica DIAN Colombia (UBL 2.1)
- **Wompi** — Pasarela de pagos Colombia
- **AWS S3** — Almacenamiento de archivos
- **Resend** — Email transaccional

## Numeros Clave

| Metrica | Cantidad |
|---------|----------|
| Microservicios | 8 |
| Endpoints API | 425+ |
| Paginas frontend | 80+ |
| Tablas en base de datos | 94+ |
| Permisos RBAC | 26 |
| Modulos activables | 7 |

## Modulos

| Modulo | Descripcion |
|--------|-------------|
| Logistica | Cadena de custodia, wallets, tracking, blockchain |
| Inventario | Productos, stock, bodegas, movimientos, kardex |
| Compras | Ordenes de compra, recepcion, proveedores |
| Ventas | Ordenes de venta, picking, despacho, facturacion |
| Produccion | Recetas (BOM), corridas, MRP, costeo |
| Facturacion Electronica | DIAN Colombia via Matias API, 6 tipos documento |
| Cumplimiento | EUDR, USDA, FSSAI, parcelas, certificados PDF |
| Inteligencia Artificial | Analisis P&L con Claude, alertas, anomalias |
| Administracion | Usuarios, roles, permisos, audit trail |
| Plataforma (superuser) | Tenants, planes, suscripciones, metricas, CMS |

## Funcionalidades Principales

### Inventario
- Productos con SKU, UoM, categorias, variantes, lotes, seriales
- Multi-bodega con ubicaciones jerarquicas
- Costeo: FIFO, LIFO, FEFO, promedio ponderado
- Kardex valorizado por producto
- Alertas de stock bajo y reorden automatico
- Conteos ciclicos con reconciliacion
- Precios especiales por cliente

### Ordenes de Compra
- Flujo: borrador → confirmada → recibida
- Recepcion parcial con tracking por linea
- Actualizacion automatica de costo promedio
- Sugerencia de precio de venta post-recepcion

### Ordenes de Venta
- Flujo: borrador → confirmada → picking → enviada → entregada
- Reserva de stock al confirmar
- Backorders automaticos si stock insuficiente
- Facturacion electronica automatica al confirmar
- Medio de pago (contado/credito) + metodo (efectivo/transferencia/tarjeta)
- Retencion en la fuente

### Facturacion Electronica
- 6 tipos documento DIAN: FEV, NC, ND, DS, POS, ER
- Integracion Matias API v2 (UBL 2.1)
- Resolucion DIAN con numeracion automatica
- Datos fiscales por cliente (CC/NIT/CE con DV, regimen, responsabilidad)
- Municipio auto-mapping (50+ ciudades colombianas)
- Retencion en la fuente en factura
- Modo simulacion para pruebas

### Produccion
- Recetas (BOM) con componentes y cantidades
- Corridas de produccion (consumo → producto terminado)
- MRP (planificacion de requerimientos)
- Costeo por transformacion
- Recursos y centros de trabajo

### Inteligencia Artificial
- Analisis de rentabilidad con Claude Haiku ($0.006/analisis)
- Deteccion de anomalias en costos de compra
- Alertas de margen negativo
- Productos estrella y oportunidades
- Memoria por tenant (90 dias)
- Metricas de uso y costo por tenant

### Cadena de Custodia
- Eventos inmutables con hash criptografico
- Timeline visual de custodia
- Wallets (allowlist) con estados
- Anchoring en Solana blockchain
- Verificacion publica via QR/link
- Flujos de trabajo personalizables

### Cumplimiento Normativo
- Frameworks: EUDR, USDA Organic, FSSAI, RSPO
- Gestion de parcelas con GPS
- Registros de auditoria por parcela
- Certificados PDF con QR
- Verificacion publica de certificados

### SaaS / Monetizacion
- 4 planes: Free, Starter ($49), Professional ($149), Enterprise
- Modulos activables por tenant
- Pasarela de pagos Wompi
- Licencias con validacion
- Enforcement automatico de limites
- Metricas de ventas (MRR, ARR, churn)

## Seguridad
- JWT con refresh tokens y blacklist
- RBAC con 26 permisos granulares
- Aislamiento multi-tenant a nivel de fila
- Encriptacion de credenciales (Fernet)
- Audit trail inmutable
- CORS configurado en gateway
- Service-to-service tokens (S2S)

## Despliegue
- **Desarrollo**: docker-compose up (todo local)
- **Produccion**: GCP Cloud Run (auto-scaling, serverless)
- **CI/CD**: GitHub Actions → build → push → deploy
- **Migraciones**: Alembic (ejecuta al iniciar cada servicio)

## URLs de Produccion
- Frontend: https://front-trace-421343664920.southamerica-east1.run.app
- Gateway: https://gateway-421343664920.southamerica-east1.run.app
- Region: southamerica-east1 (Sao Paulo)
