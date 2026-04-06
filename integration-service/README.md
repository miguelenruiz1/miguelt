# integration-service

> Integraciones con APIs externas: facturación electrónica DIAN (vía Matias API), webhooks salientes y configuración de resoluciones de facturación.

**Puerto:** 8004 (interno) · 9004 (externo)
**DB:** `integration-postgres:5440` · **Redis:** `db=4`

## Responsabilidades

- Adaptador Matias API v2 (UBL 2.1) para DIAN Colombia
- Soporte para los 6 tipos de documento DIAN: FEV, NC, ND, DS, POS, ER
- Gestión de resoluciones de facturación
- Webhooks salientes (eventos de billing, ventas, etc.)
- Encrypted credentials per tenant (Fernet)
- CUFE generation y validación

## Endpoints clave

```
POST   /api/v1/integrations/{provider}        # Configure credentials
GET    /api/v1/integrations
PATCH  /api/v1/integrations/{provider}

POST   /api/v1/resolutions
GET    /api/v1/resolutions
PATCH  /api/v1/resolutions/{id}

POST   /api/v1/internal/einvoicing/issue      # S2S from inventory-service
POST   /api/v1/webhooks/{event}
```

## Variables de entorno

```bash
DATABASE_URL=postgresql+asyncpg://int_svc:intpass@integration-postgres:5440/integrationdb
REDIS_URL=redis://redis:6379/4
USER_SERVICE_URL=http://user-api:8001
SUBSCRIPTION_SERVICE_URL=http://subscription-api:8002
INVENTORY_SERVICE_URL=http://inventory-api:8003
JWT_SECRET=<32+ char>
ENCRYPTION_KEY=<32+ char strong random>      # Validator fail-closed en prod
ENV=production
```
