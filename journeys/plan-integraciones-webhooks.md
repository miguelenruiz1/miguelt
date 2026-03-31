# Plan: Sistema de Integraciones y Webhooks

## Objetivo

Permitir que sistemas externos (contabilidad, ERP, e-commerce, etc.) se conecten con Trace de forma bidireccional:
- **Outbound**: Trace emite eventos cuando algo pasa (OV despachada, OC recibida, produccion completada)
- **Inbound**: Sistemas externos envian datos a Trace (pago confirmado, factura creada)
- **Conectores**: Adaptadores pre-construidos para sistemas populares

---

## Lo que ya existe en integration-service

- Tabla `integration_configs` — configuraciones por tenant con credenciales encriptadas
- Tabla `sync_jobs` + `sync_logs` — historial de sincronizaciones
- Tabla `webhook_logs` — auditoria de webhooks recibidos
- Adaptadores: MATIAS (facturacion DIAN) + Sandbox (simulacion)
- Endpoint `POST /api/v1/webhooks/{provider_slug}` — recibe webhooks externos
- Base adapter pattern con interfaz estandar

---

## Lo que falta implementar

### 1. Webhook Subscriptions (outbound)

Nueva tabla `webhook_subscriptions`:
```
id, tenant_id, name, target_url, secret (para firmar),
events[] (array de eventos a escuchar),
is_active, retry_count, last_triggered_at,
created_by, created_at, updated_at
```

**Eventos que Trace puede emitir:**

| Evento | Servicio origen | Cuando se dispara |
|--------|----------------|-------------------|
| `inventory.po.received` | inventory-api | OC recibida |
| `inventory.so.shipped` | inventory-api | OV despachada |
| `inventory.so.delivered` | inventory-api | OV entregada |
| `inventory.stock.alert` | inventory-api | Alerta de stock bajo |
| `inventory.movement.created` | inventory-api | Movimiento de inventario |
| `production.run.completed` | inventory-api | Produccion completada |
| `production.run.closed` | inventory-api | Produccion cerrada con variaciones |
| `trace.asset.created` | trace-api | Asset/carga creada |
| `trace.event.recorded` | trace-api | Evento de custodia registrado |
| `trace.asset.delivered` | trace-api | Carga entregada (terminal) |
| `compliance.record.validated` | compliance-api | Registro EUDR validado |
| `compliance.certificate.generated` | compliance-api | Certificado PDF generado |
| `compliance.dds.submitted` | compliance-api | DDS enviada a TRACES NT |
| `media.file.uploaded` | media-api | Archivo subido |

**Flujo:**
1. Servicio origen (ej: inventory-api) llama a integration-api via S2S:
   `POST /api/v1/internal/events` con `{ event_type, tenant_id, payload }`
2. Integration-service busca subscriptions activas para ese tenant + evento
3. Para cada subscription: envia POST al target_url con payload firmado (HMAC SHA-256)
4. Registra resultado en `webhook_delivery_logs`
5. Si falla: reintenta con backoff exponencial (1min, 5min, 30min)

### 2. Webhook Delivery Log

Nueva tabla `webhook_delivery_logs`:
```
id, subscription_id, event_type, payload,
status (pending/delivered/failed),
http_status, response_body,
attempts, next_retry_at,
created_at, delivered_at
```

### 3. API para gestionar subscriptions

```
GET    /api/v1/webhooks/subscriptions          — listar mis subscriptions
POST   /api/v1/webhooks/subscriptions          — crear subscription
GET    /api/v1/webhooks/subscriptions/{id}     — detalle
PATCH  /api/v1/webhooks/subscriptions/{id}     — editar (url, eventos, activo)
DELETE /api/v1/webhooks/subscriptions/{id}     — eliminar
POST   /api/v1/webhooks/subscriptions/{id}/test — enviar evento de prueba
GET    /api/v1/webhooks/deliveries             — historial de entregas
```

### 4. Internal Event Receiver (S2S)

```
POST /api/v1/internal/events
Headers: X-Service-Token
Body: { event_type, tenant_id, payload, source_service }
```

Cada microservicio llama este endpoint cuando algo relevante pasa. Integration-service distribuye a los subscribers.

### 5. Conectores Pre-construidos (adaptadores nuevos)

| Conector | Tipo | Que hace |
|----------|------|----------|
| **Generic Webhook** | Outbound | Envia JSON a cualquier URL (el mas usado) |
| **Siigo** | Bidireccional | Sync facturas, pagos, clientes (Colombia) |
| **Alegra** | Bidireccional | Sync facturas, productos (Latam) |
| **QuickBooks** | Bidireccional | Sync invoices, payments (Internacional) |
| **Zapier/Make** | Outbound | Webhook generico compatible con Zapier/Make |
| **Slack** | Outbound | Notificaciones a canal de Slack |
| **Email** | Outbound | Enviar email cuando ocurre un evento |

Para la primera version implementamos: **Generic Webhook** + **Slack** + **Email**.
Los contables (Siigo, Alegra, QuickBooks) se agregan despues como modulos premium.

### 6. Frontend — Pagina de Integraciones

Nueva seccion en el sidebar (dentro de "Empresa" o como modulo transversal):

```
Integraciones
  ├── Conectores (MATIAS, Sandbox + nuevos)
  ├── Webhooks (subscriptions + deliveries)
  └── Historial (sync jobs + logs)
```

**Pagina de Webhooks:**
- Tabla de subscriptions con toggle activo/inactivo
- Modal para crear: nombre, URL destino, secret, seleccionar eventos (checkboxes)
- Boton "Probar" que envia un evento de prueba
- Tab de entregas con status (delivered/failed), reintentos

---

## Migracion

```sql
-- 004_webhook_subscriptions.py

CREATE TABLE webhook_subscriptions (
  id VARCHAR(36) PK,
  tenant_id VARCHAR(255) NOT NULL,
  name VARCHAR(255) NOT NULL,
  target_url TEXT NOT NULL,
  secret VARCHAR(255),                    -- HMAC signing key
  events JSONB NOT NULL DEFAULT '[]',     -- ["inventory.so.shipped", "trace.asset.delivered"]
  headers JSONB DEFAULT '{}',             -- custom headers to include
  is_active BOOLEAN DEFAULT true,
  retry_policy VARCHAR(20) DEFAULT 'exponential',  -- exponential | fixed | none
  max_retries INTEGER DEFAULT 5,
  last_triggered_at TIMESTAMP WITH TIME ZONE,
  created_by VARCHAR(255),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE webhook_delivery_logs (
  id VARCHAR(36) PK,
  subscription_id VARCHAR(36) FK → webhook_subscriptions.id,
  tenant_id VARCHAR(255) NOT NULL,
  event_type VARCHAR(100) NOT NULL,
  payload JSONB NOT NULL,
  status VARCHAR(20) DEFAULT 'pending',   -- pending | delivered | failed
  http_status INTEGER,
  response_body TEXT,
  attempts INTEGER DEFAULT 0,
  next_retry_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  delivered_at TIMESTAMP WITH TIME ZONE
);
```

---

## Payload del Webhook (lo que recibe el sistema externo)

```json
{
  "event": "inventory.so.shipped",
  "timestamp": "2026-03-31T12:00:00Z",
  "tenant_id": "default",
  "source": "inventory-service",
  "data": {
    "order_id": "uuid",
    "order_number": "SO-2026-0042",
    "customer_id": "uuid",
    "customer_name": "Hamburg Coffee Imports GmbH",
    "total": 86400.00,
    "currency": "USD",
    "items": [
      { "product_id": "uuid", "sku": "CAFE-HLA-ESP-84", "quantity": 18000, "unit_price": 4.80 }
    ],
    "shipping": {
      "tracking_number": "MAEU-2026-00891",
      "carrier": "Maersk Line"
    }
  }
}
```

**Headers enviados:**
```
Content-Type: application/json
X-Trace-Event: inventory.so.shipped
X-Trace-Timestamp: 2026-03-31T12:00:00Z
X-Trace-Signature: sha256=abc123...  (HMAC del payload con el secret)
X-Trace-Delivery-Id: uuid
```

El receptor puede verificar la firma con su secret para confirmar autenticidad.

---

## Orden de Implementacion

### Fase 1 — Backend (integration-service)
1. Migracion 004: tablas webhook_subscriptions + webhook_delivery_logs
2. Modelos SQLAlchemy
3. Repository para subscriptions + deliveries
4. Service: create_subscription, dispatch_event, deliver_webhook, retry_failed
5. Router: CRUD subscriptions + delivery history + test
6. Internal endpoint: POST /internal/events (S2S)
7. Webhook dispatcher: busca subscribers, firma, envia, loguea

### Fase 2 — Emisores (otros servicios)
1. Crear un cliente HTTP ligero `webhook_client.py` para cada servicio
2. En inventory-api: emitir eventos en po_service (received), so_service (shipped, delivered), production_service (completed, closed)
3. En trace-api: emitir en custody_service (asset.created, event.recorded, delivered)
4. En compliance-api: emitir en records (validated), certificates (generated), traces (submitted)

### Fase 3 — Frontend
1. Pagina de webhooks en /integraciones/webhooks
2. CRUD de subscriptions con selector de eventos
3. Historial de entregas con status y reintentos
4. Boton de prueba

### Fase 4 — Conectores adicionales (futuro)
1. Slack adapter (envia a canal)
2. Email adapter (envia email via SMTP)
3. Siigo adapter (Colombia)
4. Alegra adapter (Latam)
5. QuickBooks adapter (internacional)

---

## Seguridad

- Webhook secret generado automaticamente al crear subscription (UUID + SHA)
- Payload firmado con HMAC-SHA256 usando el secret
- El receptor verifica la firma para confirmar que viene de Trace
- Las URLs destino deben ser HTTPS en produccion
- Rate limiting: max 100 deliveries/minuto por tenant
- Timeout de entrega: 10 segundos
- Reintentos con backoff exponencial: 1min, 5min, 30min, 2h, 24h
- Despues de max_retries fallidos: subscription se desactiva automaticamente
