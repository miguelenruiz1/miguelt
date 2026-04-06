# ai-service

> Análisis de rentabilidad e inteligencia de inventario con Claude Haiku 4.5.

**Puerto:** 8006 (interno) · 9006 (externo)
**DB:** `ai-postgres:5442` · **Redis:** `db=6`

## Responsabilidades

- Análisis de rentabilidad por producto con contexto enriquecido (alertas de inventario, variaciones de costo, márgenes negativos)
- Memoria conversacional per tenant
- Rate limit diario per tenant (default 50 análisis/día)
- Settings tenant-scoped (provider, modelo, temperatura)

## Endpoints clave

```
POST   /api/v1/analyze
GET    /api/v1/settings
PATCH  /api/v1/settings
GET    /api/v1/memory
DELETE /api/v1/memory
GET    /api/v1/metrics                    # Usage metrics per tenant
```

## Variables de entorno

```bash
DATABASE_URL=postgresql+asyncpg://ai_svc:aipass@ai-postgres:5442/aidb
REDIS_URL=redis://redis:6379/6
USER_SERVICE_URL=http://user-api:8001
INVENTORY_SERVICE_URL=http://inventory-api:8003
JWT_SECRET=<32+ char>
S2S_SERVICE_TOKEN=<32+ char>
ANTHROPIC_API_KEY=sk-ant-...
AI_ANALYSIS_DAILY_LIMIT=50
ENV=production
```
