# Arquitectura Completa — Trace Platform

---

## Vista General

```
                                    ┌──────────────┐
                                    │   Frontend    │
                                    │  React + TS   │
                                    │  Port: 3000   │
                                    └──────┬───────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
              ┌─────▼─────┐        ┌──────▼──────┐       ┌──────▼──────┐
              │ trace-api  │        │  user-api   │       │ media-api   │
              │   :8000    │        │   :9001     │       │   :9007     │
              └─────┬──────┘        └──────┬──────┘       └──────┬──────┘
                    │                      │                      │
        ┌───────────┼───────────┐          │                      │
        │           │           │          │                      │
  ┌─────▼────┐ ┌────▼─────┐ ┌──▼────────┐ │               ┌──────▼──────┐
  │inventory │ │compliance│ │subscription│ │               │   Local /   │
  │  :9003   │ │  :9005   │ │   :9002   │ │               │  S3 Storage │
  └──────────┘ └──────────┘ └───────────┘ │               └─────────────┘
        │           │                      │
  ┌─────▼────┐ ┌────▼─────┐        ┌──────▼──────┐
  │integration│ │  ai-api  │        │   Mailhog   │
  │  :9004   │ │  :9006   │        │   (SMTP)    │
  └──────────┘ └──────────┘        └─────────────┘
```

---

## Microservicios

| # | Servicio | Puerto Int. | Puerto Ext. | Base de Datos | Redis DB | Responsabilidad |
|---|----------|-------------|-------------|---------------|----------|-----------------|
| 1 | **trace-api** | 8000 | 8000 | trace-postgres (tracedb) | /0 | Assets, custodia, blockchain, workflow, envios |
| 2 | **trace-worker** | — | — | trace-postgres (tracedb) | /1 (ARQ) | Jobs asincrono: anclaje Solana, reintentos |
| 3 | **user-api** | 8001 | 9001 | user-postgres (userdb) | /2 | Auth, JWT, RBAC, perfiles, email, auditoria |
| 4 | **subscription-api** | 8002 | 9002 | subscription-postgres (subdb) | /3 | Planes, suscripciones, modulos, pagos |
| 5 | **inventory-api** | 8003 | 9003 | inventory-postgres (inventorydb) | /4 | Productos, stock, OC, OV, produccion, lotes |
| 6 | **integration-api** | 8004 | 9004 | integration-postgres (integrationdb) | /5 | Webhooks, conectores externos |
| 7 | **compliance-api** | 8005 | 9005 | compliance-postgres (compliancedb) | /6 | EUDR, parcelas, GFW, TRACES NT, certificados |
| 8 | **ai-api** | 8006 | 9006 | ai-postgres (aidb) | /7 | Analisis con Claude AI |
| 9 | **media-api** | 8007 | 9007 | media-postgres (mediadb) | /8 | Archivos centralizados, storage local/S3 |

---

## Bases de Datos (PostgreSQL 16)

| Container | Puerto Host | Usuario | Base | Servicio |
|-----------|-------------|---------|------|----------|
| trace-postgres | 5471 | trace | tracedb | trace-api + worker |
| user-postgres | 5472 | user_svc | userdb | user-api |
| subscription-postgres | 5473 | sub_svc | subdb | subscription-api |
| inventory-postgres | 5474 | inv_svc | inventorydb | inventory-api |
| integration-postgres | 5475 | int_svc | integrationdb | integration-api |
| compliance-postgres | 5476 | cmp_svc | compliancedb | compliance-api |
| ai-postgres | 5477 | ai_svc | aidb | ai-api |
| media-postgres | 5478 | media_svc | mediadb | media-api |

**Total: 8 bases de datos independientes (una por servicio)**

---

## Redis (Compartido)

| DB # | Servicio | Uso |
|------|----------|-----|
| /0 | trace-api | Idempotency keys, cache |
| /1 | trace-worker | ARQ job queue |
| /2 | user-api | JWT blacklist, session cache |
| /3 | subscription-api | Module cache, plan cache |
| /4 | inventory-api | Stock cache, module gating |
| /5 | integration-api | Webhook state |
| /6 | compliance-api | Compliance cache |
| /7 | ai-api | AI response cache |
| /8 | media-api | File metadata cache |

---

## Comunicacion Service-to-Service (S2S)

Autenticacion: Header `X-Service-Token` (shared secret)

```
inventory-api ──→ trace-api
  POST /api/v1/internal/assets/from-po-receipt    (OC recibida → crea Asset)
  POST /api/v1/internal/assets/handoff-from-so    (OV despachada → handoff)
  POST /api/v1/anchoring/hash                     (anclar hash en Solana)

trace-api ──→ inventory-api
  GET /api/v1/internal/batches/{batch_id}          (consultar datos de lote)

compliance-api ──→ trace-api
  GET /api/v1/assets/{asset_id}                    (validar asset, datos blockchain)

compliance-api ──→ media-api
  GET /api/v1/internal/media/files/{file_id}       (resolver URL de documento)

inventory-api ──→ media-api
  POST /api/v1/internal/media/files                (subir imagen producto, adjunto OC)
  GET  /api/v1/internal/media/files/{file_id}      (obtener metadata)
  DELETE /api/v1/internal/media/files/{file_id}     (eliminar archivo)

user-api ──→ media-api
  POST /api/v1/internal/media/files                (subir avatar)

trace-api ──→ media-api
  POST /api/v1/internal/media/files                (subir evidencia de evento)

ALL services ──→ user-api
  GET /api/v1/auth/me                              (validar JWT, obtener usuario)

ALL services ──→ subscription-api
  GET /api/v1/modules/{tenant_id}/{slug}           (verificar modulo activo)
```

---

## Frontend (React)

| Aspecto | Detalle |
|---------|---------|
| Framework | React 19 + TypeScript + Vite |
| Routing | React Router 7 |
| State | Zustand (auth, settings, toast) + React Query (server state) |
| UI | Tailwind CSS + lucide-react icons |
| Puerto dev | 3000 |

### APIs que consume el frontend:

| Variable | URL | Servicio |
|----------|-----|----------|
| VITE_API_URL | http://localhost:8000 | trace-api (via Vite proxy) |
| VITE_USER_API_URL | http://localhost:9001 | user-api |
| VITE_SUBSCRIPTION_API_URL | http://localhost:9002 | subscription-api |
| VITE_INVENTORY_API_URL | http://localhost:9003 | inventory-api |
| VITE_COMPLIANCE_API_URL | http://localhost:9005 | compliance-api |
| VITE_AI_API_URL | http://localhost:9006 | ai-api |
| VITE_MEDIA_API_URL | http://localhost:9007 | media-api |

---

## Modulos del Sistema (activables por suscripcion)

| Modulo | Servicio Backend | Seccion Frontend | Activacion |
|--------|-----------------|------------------|------------|
| **Logistica** | trace-api | Seguimiento, Cargas, Custodios, Organizaciones, Analiticas, Workflow | `logistics` |
| **Inventario** | inventory-api | Productos, Bodegas, Movimientos, Compras, Ventas, Lotes, Config | `inventory` |
| **Produccion** | inventory-api | Dashboard, Ordenes, Recetas, Emisiones, Recibos, Reportes | `production` |
| **Cumplimiento** | compliance-api | Frameworks, Activaciones, Parcelas, Registros, Certificados | `compliance` |
| **Facturacion Electronica** | inventory-api | Facturacion DIAN | `electronic-invoicing` |
| **AI** | ai-api | Analisis inteligente | `ai-analysis` |

---

## Integraciones Externas

| Integracion | Servicio | Protocolo | Proposito |
|-------------|----------|-----------|-----------|
| **Solana Blockchain** | trace-api, worker | JSON-RPC | Anclaje de hashes (Memo Program), mint cNFTs |
| **Helius** | trace-api, worker | JSON-RPC (DAS) | Mint cNFTs, verificacion on-chain, tree management |
| **Global Forest Watch** | compliance-api | REST API | Alertas de deforestacion post dic-2020 |
| **TRACES NT** | compliance-api | SOAP/XML | Envio DDS a sistema EU (Regulation 2023/1115) |
| **Anthropic Claude** | ai-api | REST API | Analisis de contenido, generacion de texto |
| **AWS S3** | media-api, trace-api | AWS SDK | Storage de archivos en produccion |
| **SMTP (Mailhog)** | user-api | SMTP | Emails transaccionales (dev: Mailhog, prod: real SMTP) |
| **Wompi** | subscription-api | REST API | Pasarela de pagos Colombia/LatAm |

---

## Tablas por Servicio

### trace-service (17 tablas)
```
tenants, tenant_merkle_trees
assets, custody_events, event_document_links
registry_wallets, organizations, custodian_types
shipment_documents, trade_documents
media_files, anchor_requests, anchor_rules
workflow_states, workflow_transitions, workflow_event_types
event_type_configs
```

### inventory-service (57 tablas)
```
entities (products), categories, product_types, product_variants
warehouses, warehouse_locations, warehouse_types
stock_levels, stock_movements, stock_reservations, stock_layers, stock_alerts
purchase_orders, purchase_order_lines, po_approval_logs
sales_orders, sales_order_lines, so_approval_logs
business_partners, suppliers, customers, customer_types
customer_prices, customer_price_history, product_cost_history
entity_batches, entity_serials, serial_statuses
entity_recipes, recipe_components
production_runs, production_emissions, production_emission_lines
production_receipts, production_receipt_lines
cycle_counts, cycle_count_items, ira_snapshots
inventory_events, event_types, event_severities, event_statuses
event_status_logs, event_impacts
units_of_measure, uom_conversions, tax_rates
tenant_inventory_configs, order_types, movement_types
custom_product_fields, custom_supplier_fields, custom_warehouse_fields
custom_movement_fields, supplier_types
variant_attributes, variant_attribute_options
inventory_audit_logs, shipment_documents, trade_documents
```

### compliance-service (10 tablas)
```
compliance_frameworks, tenant_framework_activations
compliance_plots, compliance_plot_links
compliance_records, compliance_certificates
compliance_record_documents, compliance_plot_documents
compliance_risk_assessments, compliance_supply_chain_nodes
```

### user-service (8+ tablas)
```
users, roles, permissions, user_roles, role_permissions
audit_logs, email_templates, email_provider_configs
role_templates
```

### subscription-service (5+ tablas)
```
plans, subscriptions, invoices, license_keys
subscription_events, tenant_module_activations
payment_gateway_configs
```

### media-service (1 tabla)
```
media_files
```

---

## Seguridad

| Mecanismo | Scope | Detalle |
|-----------|-------|---------|
| JWT (HS256) | Frontend → Backend | Access token 15min + refresh 7d, blacklist en Redis |
| S2S Token | Backend ↔ Backend | Shared secret en header `X-Service-Token` |
| RBAC | user-service | 26+ permisos en 7 modulos, roles asignables |
| Admin Key | trace-api | TRACE_ADMIN_KEY para operaciones destructivas (release, burn) |
| Tenant Isolation | Todas las tablas | `tenant_id` en cada tabla, filtrado en cada query |
| Hash Chain | custody_events | SHA-256 encadenado (cada evento referencia al anterior) |
| Blockchain Anchor | trace-service | Solana Memo Program para inmutabilidad publica |

---

## Volumenes Persistentes

| Volumen | Montaje | Servicio | Contenido |
|---------|---------|----------|-----------|
| postgres-data | /var/lib/postgresql/data | trace-postgres | DB trace |
| user-postgres-data | /var/lib/postgresql/data | user-postgres | DB users |
| subscription-postgres-data | /var/lib/postgresql/data | subscription-postgres | DB subs |
| inventory-postgres-data | /var/lib/postgresql/data | inventory-postgres | DB inventory |
| integration-postgres-data | /var/lib/postgresql/data | integration-postgres | DB integration |
| compliance-postgres-data | /var/lib/postgresql/data | compliance-postgres | DB compliance |
| ai-postgres-data | /var/lib/postgresql/data | ai-postgres | DB AI |
| media-postgres-data | /var/lib/postgresql/data | media-postgres | DB media |
| redis-data | /data | redis | Cache persistente |
| trace-uploads | /app/uploads | trace-api | Uploads de trace |
| user-uploads | /app/uploads | user-api | Avatares |
| inventory-uploads | /app/uploads | inventory-api | Imagenes productos |
| media-uploads | /app/uploads | media-api | **Biblioteca centralizada** |

---

## Red

- **Network:** `trace-net` (bridge)
- Todos los containers en la misma red
- Comunicacion interna por nombre de container (ej: `http://trace-api:8000`)
- Solo puertos externos expuestos al host

---

## Flujo de Datos Principal

```
Usuario → Frontend (React)
           │
           ├─ Auth → user-api → JWT → Redis blacklist
           │
           ├─ Modulos → subscription-api → module activations
           │
           ├─ Inventario → inventory-api → PostgreSQL
           │    ├─ OC Recibida → S2S → trace-api (crea Asset)
           │    ├─ OV Despachada → S2S → trace-api (handoff)
           │    ├─ Produccion → emission/receipt → stock movements
           │    └─ Imagenes → S2S → media-api
           │
           ├─ Logistica → trace-api → PostgreSQL
           │    ├─ Eventos de custodia → hash chain
           │    ├─ Anclaje → ARQ worker → Solana
           │    └─ Documentos → media-api
           │
           ├─ Cumplimiento → compliance-api → PostgreSQL
           │    ├─ Parcelas → GFW API (deforestacion)
           │    ├─ Registros → cadena suministro + riesgo
           │    ├─ DDS → TRACES NT (EU)
           │    ├─ Certificados → PDF + QR + Solana
           │    └─ Evidencia → media-api
           │
           ├─ Media → media-api → PostgreSQL + Storage
           │    └─ Archivos centralizados, referenciados por todos los modulos
           │
           └─ AI → ai-api → Anthropic Claude
```
