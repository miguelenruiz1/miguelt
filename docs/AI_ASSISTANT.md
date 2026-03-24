# Asistente IA de Rentabilidad — Documentación Técnica y Lógica

## Qué es

Un asistente de inteligencia artificial integrado en el módulo de **Rentabilidad (P&L)** del inventario. Analiza los datos financieros reales del tenant (ventas, costos, márgenes, stock, proveedores) y genera insights accionables específicos para su tipo de negocio.

**Modelo**: Claude Haiku 4.5 (Anthropic)
**Costo promedio**: ~$0.01 USD por análisis
**Latencia**: 3-8 segundos

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                              │
│                                                                  │
│  PnLPage.tsx                                                    │
│  ├── KPI Cards (ingresos, costos, utilidad, margen)             │
│  ├── AiInsightsPanel ← usePnLAnalysis() hook                   │
│  │   ├── Resumen ejecutivo                                      │
│  │   ├── Alertas (severidad: alta/media/baja)                   │
│  │   ├── Oportunidades (con impacto estimado)                   │
│  │   ├── Productos estrella                                     │
│  │   └── Recomendaciones (prioridad + plazo)                    │
│  └── Tabla de productos expandible                              │
│                                                                  │
│  GET /api/v1/reports/pnl/analysis?date_from=X&date_to=Y        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 INVENTORY-SERVICE (Python/FastAPI)               │
│                                                                  │
│  reports.py → GET /pnl/analysis                                 │
│       │                                                          │
│       ▼                                                          │
│  AiAnalysisService.analyze_pnl()                                │
│       │                                                          │
│       ├─ 1. _get_ai_config()                                    │
│       │     └─ subscription-service/api/v1/platform/ai/config   │
│       │        (Redis cache 60s → fallback env var)              │
│       │                                                          │
│       ├─ 2. Redis cache check                                    │
│       │     key: ai:pnl:{tenant_id}:{date_from}:{date_to}      │
│       │     TTL: 60 min (configurable)                           │
│       │                                                          │
│       ├─ 3. _check_rate_limit()                                  │
│       │     key: ai:pnl:rate:{tenant_id}:{YYYY-MM-DD}           │
│       │     limit: 10/día (configurable por plan)                │
│       │                                                          │
│       ├─ 4. _build_prompt()                                      │
│       │     ├─ _get_business_context() ← DB queries              │
│       │     │   ├─ Categorías de productos                       │
│       │     │   ├─ Tipos de producto                             │
│       │     │   ├─ Bodegas                                       │
│       │     │   └─ Proveedores activos                           │
│       │     ├─ _get_product_category_map() ← JOIN product→cat    │
│       │     ├─ _get_product_type_map() ← JOIN product→type       │
│       │     ├─ _get_tenant_info() ← HTTP user-service            │
│       │     └─ Arma JSON con contexto + datos P&L                │
│       │                                                          │
│       ├─ 5. anthropic.messages.create()                          │
│       │     model: claude-haiku-4-5-20251001                     │
│       │     max_tokens: 2048                                     │
│       │     system: SYSTEM_PROMPT                                │
│       │     user: prompt construido                              │
│       │                                                          │
│       ├─ 6. _parse_response()                                    │
│       │     ├─ Strip markdown fences                              │
│       │     ├─ Extraer JSON puro                                 │
│       │     └─ Validar con Pydantic (PnLAnalysis)                │
│       │                                                          │
│       └─ 7. Cache resultado en Redis (si parse exitoso)          │
│                                                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              SUBSCRIPTION-SERVICE (Config & Métricas)            │
│                                                                  │
│  Tabla: platform_ai_settings (singleton)                        │
│  ├── anthropic_api_key_encrypted (base64)                       │
│  ├── anthropic_model_analysis                                    │
│  ├── anthropic_enabled (bool)                                    │
│  ├── global_daily_limit_{free|starter|professional|enterprise}   │
│  ├── cache_ttl_minutes, cache_enabled                            │
│  ├── pnl_analysis_enabled                                        │
│  ├── estimated_cost_per_analysis_usd                             │
│  └── alert_monthly_cost_usd                                      │
│                                                                  │
│  Endpoints (superuser only):                                     │
│  ├── GET    /platform/ai/settings      → config enmascarada     │
│  ├── POST   /platform/ai/settings      → update config          │
│  ├── PATCH  /platform/ai/settings/api-key → guardar key         │
│  ├── POST   /platform/ai/settings/test → probar conexión        │
│  ├── GET    /platform/ai/metrics       → uso del mes            │
│  ├── DELETE /platform/ai/cache         → limpiar caches         │
│  └── GET    /platform/ai/config        → interno (sin auth)     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flujo Completo (paso a paso)

### 1. Usuario abre /inventario/rentabilidad

El componente `PnLPage` hace dos queries independientes:
- `usePnL(dateFrom, dateTo)` → datos del P&L (siempre funciona)
- `usePnLAnalysis(dateFrom, dateTo)` → análisis IA (opcional, nunca bloquea el P&L)

### 2. Frontend llama al endpoint

```
GET /api/v1/reports/pnl/analysis?date_from=2026-01-01&date_to=2026-03-24
Authorization: Bearer {jwt}
X-Tenant-Id: {tenant_slug}
```

### 3. Backend obtiene configuración de IA

```
inventory-service → GET subscription-service/api/v1/platform/ai/config
```

Respuesta (ejemplo):
```json
{
  "anthropic_api_key": "sk-ant-api03-...",
  "anthropic_model_analysis": "claude-haiku-4-5-20251001",
  "anthropic_enabled": true,
  "cache_ttl_minutes": 60,
  "cache_enabled": true,
  "pnl_analysis_enabled": true,
  "global_daily_limit_starter": 10
}
```

Se cachea en Redis 60 segundos. Si el subscription-service está caído, usa `ANTHROPIC_API_KEY` de las variables de entorno como fallback.

### 4. Verifica cache

Clave: `ai:pnl:{tenant_id}:{date_from}:{date_to}`

Si existe → devuelve sin llamar a Anthropic (no consume rate limit).
Si `force=true` → borra el cache y continúa.

### 5. Verifica rate limit

Clave: `ai:pnl:rate:{tenant_id}:{YYYY-MM-DD}`

Si el contador >= límite del plan → HTTP 429 con mensaje "Límite diario alcanzado".
Solo se incrementa cuando se va a hacer una llamada real a Anthropic.

### 6. Consulta contexto del negocio

Hace 5 queries a la BD del inventario:

| Query | Tabla | Dato |
|-------|-------|------|
| Categorías | `categories` | "Limpieza", "Cuidado personal" |
| Tipos de producto | `product_types` | "Producto terminado", "Materia prima" |
| Bodegas | `warehouses` | "Planta producción", "Bodega principal" |
| Proveedores | `partners` (is_supplier=true) | "Químicos del Valle", "Empaques SAS" |
| Nombre empresa | user-service HTTP | "Jabones del Pacífico SAS" |

### 7. Construye el prompt

El prompt tiene 3 bloques:

**System prompt** (fijo):
```
Eres un asesor financiero experto en rentabilidad para PYMEs.
Analizas P&L y generas insights ESPECIFICOS para el sector del negocio.
NO sugieras estrategias genéricas de ecommerce.
Basa TODAS tus recomendaciones en los productos, proveedores y operación REALES.
```

**Contexto del negocio** (dinámico):
```json
{
  "empresa": "Jabones del Pacífico SAS",
  "categorias_productos": ["Limpieza hogar", "Cuidado personal"],
  "tipos_producto": ["Producto terminado"],
  "bodegas": ["Planta producción", "Centro distribución"],
  "proveedores_activos": ["Químicos del Valle", "Empaques SAS"],
  "total_productos": 14,
  "margen_promedio": 4.07,
  "ingresos_totales": 795.51,
  "utilidad_bruta": 453.51,
  "productos_margen_negativo": 0,
  "top_3_utilidad": [...],
  "bottom_3_margen": [...]
}
```

**Detalle por producto** (compacto, sin arrays de compras/ventas):
```json
[
  {
    "sku": "LH-DETLIQ1L",
    "nombre": "Detergente líquido 1L",
    "categoria": "Limpieza hogar",
    "tipo": "Producto terminado",
    "ingresos": 795.51,
    "costo": 342.0,
    "utilidad": 453.51,
    "margen_pct": 57.01,
    "margen_objetivo": 35,
    "uds_vendidas": 191,
    "stock_qty": 9,
    "stock_valor": 16.11,
    "proveedor": "Químicos del Valle",
    "precio_sugerido": 5.9
  }
]
```

**Instrucciones de formato** (JSON schema estricto con límites de caracteres).

### 8. Llama a Claude Haiku 4.5

```python
response = await client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=2048,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": prompt}],
)
```

### 9. Parsea la respuesta

1. Strip markdown fences (```json ... ```)
2. Busca el primer `{` y el último `}`
3. `json.loads()` → dict
4. `PnLAnalysis.model_validate(data)` → schema Pydantic

Si falla el parse → devuelve mensaje de error pero **no lo cachea** (el siguiente intento es una llamada nueva).

### 10. Cachea y devuelve

Solo respuestas exitosas se guardan en Redis con el TTL configurado.

---

## Schema de Respuesta

```json
{
  "resumen": "La empresa tiene 100% de dependencia en Detergente 1L con margen 57%. 13 productos sin ventas acumulan $2.249 en stock muerto.",

  "alertas": [
    {
      "titulo": "Stock muerto en 13 productos",
      "detalle": "$2.249 COP inmovilizados sin rotación en el periodo",
      "severidad": "alta",
      "producto_sku": null
    }
  ],

  "oportunidades": [
    {
      "titulo": "Liquidar stock inactivo",
      "detalle": "Vender 13 SKUs a precio sugerido libera $2.249 COP",
      "impacto_estimado": "+$2.249 COP",
      "producto_sku": null
    }
  ],

  "productos_estrella": [
    {
      "sku": "LH-DETLIQ1L",
      "nombre": "Detergente líquido 1L",
      "razon": "57% margen, 191 uds vendidas. Supera objetivo 22pp"
    }
  ],

  "recomendaciones": [
    {
      "accion": "Negociar volumen con Químicos del Valle para bajar costo",
      "prioridad": "alta",
      "producto_sku": "LH-DETLIQ1L",
      "plazo": "esta_semana"
    }
  ]
}
```

### Tipos Pydantic

| Modelo | Campos | Validación |
|--------|--------|------------|
| `PnLAnalysis` | resumen, alertas[], oportunidades[], productos_estrella[], recomendaciones[] | Todos opcionales excepto resumen |
| `PnLAlert` | titulo, detalle, severidad (alta\|media\|baja), producto_sku? | severidad es Literal |
| `PnLOportunidad` | titulo, detalle, impacto_estimado, producto_sku? | — |
| `PnLProductoEstrella` | sku, nombre, razon | — |
| `PnLRecomendacion` | accion, prioridad (alta\|media\|baja), producto_sku?, plazo? (inmediato\|esta_semana\|este_mes) | prioridad y plazo son Literal |

---

## Estados del Módulo

| Estado | HTTP | Frontend | Causa |
|--------|------|----------|-------|
| Sin API key | 501 | Panel oculto | Superadmin no ha configurado la key |
| IA deshabilitada globalmente | 503 | "Temporalmente no disponible" | Toggle apagado en /platform/ai |
| Feature P&L deshabilitado | 503 | "Temporalmente no disponible" | Toggle "Análisis de Rentabilidad" apagado |
| Rate limit alcanzado | 429 | "Límite diario alcanzado" | Más de N análisis hoy |
| Anthropic caído | 503 | "No disponible, intenta más tarde" | Error de red con API |
| Sin datos en período | 200 | "No hay datos suficientes" | PnL vacío |
| Parse fallido | 200 | "No se pudo interpretar. Regenerar" | JSON truncado/inválido (no se cachea) |
| Funcionando | 200 | Análisis completo | Todo OK |

En **todos los estados** el P&L sigue cargando normalmente. La IA nunca bloquea la página.

---

## Caching (Redis)

| Clave | TTL | Propósito |
|-------|-----|-----------|
| `ai:platform:config` | 60s | Config de IA del subscription-service |
| `ai:pnl:{tenant}:{from}:{to}` | 60min (configurable) | Resultado del análisis |
| `ai:pnl:rate:{tenant}:{date}` | 25h | Contador de rate limit diario |

**Regla clave**: Solo se cachean respuestas exitosas. Errores de parse nunca se cachean.

**Invalidación**:
- `force=true` en el query → borra el cache del análisis
- Admin cambia config en /platform/ai → borra `ai:platform:config`
- Admin usa "Limpiar cache global" → borra todos los `ai:pnl:*` (excepto rate keys)

---

## Rate Limiting

| Plan | Límite diario | Configurable en |
|------|---------------|-----------------|
| Free | 0 (deshabilitado) | /platform/ai |
| Starter | 10 | /platform/ai |
| Professional | 50 | /platform/ai |
| Enterprise | -1 (ilimitado) | /platform/ai |

- Cache hits **no consumen** rate limit
- Solo llamadas reales a Anthropic incrementan el contador
- El contador se reinicia a medianoche UTC (TTL 25h en Redis)
- Si se agotan los intentos con errores de parse, el admin puede resetear manualmente desde Redis

---

## Costos Estimados

| Concepto | Valor |
|----------|-------|
| Input tokens por análisis (14 productos) | ~3,000 tokens |
| Output tokens por análisis | ~600 tokens |
| Costo por análisis (Haiku 4.5) | ~$0.005 USD |
| 5 tenants × 5 análisis/día | ~$0.50/día |
| Costo mensual estimado (5 tenants) | ~$2-4 USD |

---

## Resiliencia

1. **ErrorBoundary** envuelve el panel IA en React — si crashea, muestra "Panel no disponible" sin afectar el P&L
2. **throwOnError: false** en el hook — errores nunca propagan al padre
3. **Optional chaining** en todos los accesos a datos (`analysis?.alertas ?? []`)
4. **AiAnalysisService solo lee datos** — nunca escribe en tablas de productos/ventas/stock
5. **Imports aislados** — solo importa `errors`, `settings`, `pnl_analysis` schemas. Sin dependencias circulares
6. **Timeout de 3s** en llamadas inter-servicio (config, tenant info)
7. **Fallback a env vars** si subscription-service está caído

---

## Archivos del Módulo

```
inventory-service/
├── app/services/ai_analysis_service.py    ← Servicio principal (363 líneas)
├── app/domain/schemas/pnl_analysis.py     ← Schemas Pydantic (42 líneas)
├── app/api/routers/reports.py             ← Endpoint GET /pnl/analysis
├── app/core/settings.py                   ← ANTHROPIC_API_KEY, AI_ANALYSIS_DAILY_LIMIT
└── app/core/errors.py                     ← RateLimitError (429)

subscription-service/
├── app/db/models.py                       ← PlatformAISettings model
├── app/services/ai_settings_service.py    ← CRUD settings + test + métricas
├── app/api/routers/ai_settings.py         ← Endpoints /platform/ai/*
└── alembic/versions/008_ai_settings.py    ← Migration

front-trace/
├── src/pages/inventory/PnLPage.tsx        ← AiInsightsPanel + ErrorBoundary
├── src/pages/platform/PlatformAiSettingsPage.tsx  ← Config + métricas admin
├── src/hooks/useInventory.ts              ← usePnLAnalysis hook
├── src/lib/inventory-api.ts               ← getAiAnalysis() + ApiError class
└── src/types/inventory.ts                 ← PnLAnalysis, PnLAlert, etc.
```

---

## Panel de Administración (/platform/ai)

Accesible solo para superusers. Dos tabs:

### Tab Configuración
- API key (enmascarada, botón probar/guardar)
- Modelo (Haiku 4.5 / Sonnet 4.6)
- Max tokens
- Toggle global habilitado/deshabilitado
- Toggle por módulo (Análisis de Rentabilidad)
- Límites por plan (Free/Starter/Pro/Enterprise)
- Cache (habilitado, TTL, botón limpiar)
- Alerta de costo mensual

### Tab Métricas
- KPIs: llamadas del mes, costo estimado, costo proyectado, tenants activos
- Tabla de uso por tenant
- Gráfica de barras por día
- Alerta si el costo proyectado supera el umbral
