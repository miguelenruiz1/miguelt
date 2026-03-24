"""AI-powered P&L analysis using Claude Haiku 4.5 with tenant memory."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import anthropic
import httpx
import redis.asyncio as aioredis
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import RateLimitError
from app.core.settings import get_settings
from app.domain.schemas.pnl_analysis import PnLAnalysis

log = structlog.get_logger(__name__)

MEMORY_TTL = 90 * 24 * 3600  # 90 days in seconds

SYSTEM_PROMPT = """\
Eres el asistente de rentabilidad de TraceLog, una plataforma de inventario y trazabilidad para PYMEs colombianas.

CAPACIDADES REALES DE TRACELOG (solo recomienda estas):
- Crear precios especiales por cliente (modulo inventario)
- Generar ordenes de compra a proveedores
- Generar ordenes de venta
- Configurar alertas de stock minimo y reorden
- Hacer conteos ciclicos de inventario
- Crear recetas de produccion y ordenes de produccion
- Reasignar stock entre bodegas
- Registrar movimientos manuales de inventario
- Ajustar precio sugerido de venta por producto

CAPACIDADES NO DISPONIBLES EN TRACELOG (nunca las sugieras):
- Promociones con descuento automatico
- Cupones o codigos de descuento
- Email marketing o campanas
- Envio gratis
- Publicidad o pauta digital
- Integraciones con ecommerce o marketplaces
- CRM o gestion de clientes avanzada

REGLAS:
1. Cada recomendacion debe ser ejecutable HOY dentro de TraceLog
2. Si el negocio tiene historial, NO repitas recomendaciones ya dadas
3. Detecta la industria del negocio por sus productos y categorias
4. Usa los nombres reales de productos, proveedores y bodegas del tenant
5. Los valores monetarios estan en COP (pesos colombianos)
6. Se especifico: "Crear OC a Quimicos del Valle por 500 uds de LH-DETLIQ1L" no "considerar reabastecer"
7. Si hay alertas recurrentes en la memoria, priorizalas como criticas\
"""

RESPONSE_SCHEMA = """\
RESPONDE SOLO CON JSON PURO. Sin ```, sin markdown, sin texto antes ni despues.
Cada campo "detalle", "razon" y "accion" debe tener MAXIMO 80 caracteres. Se conciso.

{"resumen":"2-3 oraciones max 200 chars","alertas":[{"titulo":"max 40 chars","detalle":"max 80 chars con cifras","severidad":"alta|media|baja","producto_sku":"SKU o null"}],"oportunidades":[{"titulo":"max 40 chars","detalle":"max 80 chars","impacto_estimado":"$X COP o X%","producto_sku":"SKU o null"}],"productos_estrella":[{"sku":"SKU","nombre":"Nombre","razon":"max 60 chars"}],"recomendaciones":[{"accion":"max 80 chars","prioridad":"alta|media|baja","producto_sku":"SKU o null","plazo":"inmediato|esta_semana|este_mes"}]}

Maximo: 3 alertas, 3 oportunidades, 2 estrellas, 4 recomendaciones.\
"""


class AiNotConfiguredError(Exception):
    pass


class AiFeatureDisabledError(Exception):
    pass


class AiAnalysisService:
    def __init__(self, db: AsyncSession, redis_client: aioredis.Redis) -> None:
        self.db = db
        self.redis = redis_client
        self.settings = get_settings()

    # ─── Config ────────────────────────────────────────────────────────────────

    async def _get_ai_config(self) -> dict:
        cache_key = "ai:platform:config"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.settings.SUBSCRIPTION_SERVICE_URL}/api/v1/platform/ai/config")
            if resp.status_code == 200:
                config = resp.json()
                await self.redis.setex(cache_key, 60, json.dumps(config))
                return config
        except httpx.RequestError as exc:
            log.warning("ai_config_fetch_failed", error=str(exc))
        if self.settings.ANTHROPIC_API_KEY:
            return {
                "anthropic_api_key": self.settings.ANTHROPIC_API_KEY,
                "anthropic_model_analysis": "claude-haiku-4-5-20251001",
                "anthropic_enabled": True, "cache_ttl_minutes": 60,
                "cache_enabled": True, "pnl_analysis_enabled": True,
            }
        return {}

    # ─── Main Analysis ─────────────────────────────────────────────────────────

    async def analyze_pnl(
        self, pnl_data: dict, tenant_id: str,
        date_from: str, date_to: str, force: bool = False,
    ) -> PnLAnalysis:
        config = await self._get_ai_config()
        api_key = config.get("anthropic_api_key", "")
        if not api_key:
            raise AiNotConfiguredError("API key de Anthropic no configurada.")
        if not config.get("anthropic_enabled", False):
            raise AiFeatureDisabledError("IA deshabilitada globalmente.")
        if not config.get("pnl_analysis_enabled", True):
            raise AiFeatureDisabledError("Analisis de rentabilidad IA deshabilitado.")

        cache_ttl = config.get("cache_ttl_minutes", 60) * 60
        cache_key = f"ai:pnl:{tenant_id}:{date_from}:{date_to}"

        # 1. Cache check
        if force:
            await self.redis.delete(cache_key)
        elif config.get("cache_enabled", True):
            cached = await self.redis.get(cache_key)
            if cached:
                return PnLAnalysis.model_validate_json(cached)

        # 2. Rate limit
        await self._check_rate_limit(tenant_id)

        # 3. Validate data
        products = pnl_data.get("products", [])
        if not products:
            return PnLAnalysis(resumen="No hay datos de productos para analizar en el periodo seleccionado.")

        # 4. Get tenant memory
        memory = await self._get_tenant_memory(tenant_id)

        # 5. Build prompt (with memory)
        prompt = await self._build_prompt(pnl_data, tenant_id, date_from, date_to, memory)

        # 6. Call Claude
        model = config.get("anthropic_model_analysis", "claude-haiku-4-5-20251001")
        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=model, max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        # 7. Parse response
        raw_text = response.content[0].text
        try:
            analysis = self._parse_response(raw_text)
        except Exception:
            return PnLAnalysis(resumen="El modelo respondio pero no se pudo interpretar. Haz clic en Regenerar.")

        # 8. Update tenant memory (only on success)
        await self._update_tenant_memory(tenant_id, analysis, pnl_data)

        # 9. Cache result
        if config.get("cache_enabled", True):
            await self.redis.setex(cache_key, cache_ttl, analysis.model_dump_json())

        log.info("ai_analysis_complete", tenant_id=tenant_id, model=model,
                 input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens)
        return analysis

    # ─── Rate Limiting ─────────────────────────────────────────────────────────

    async def _check_rate_limit(self, tenant_id: str) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rate_key = f"ai:pnl:rate:{tenant_id}:{today}"
        current = await self.redis.get(rate_key)
        count = int(current) if current else 0
        limit = self.settings.AI_ANALYSIS_DAILY_LIMIT
        if count >= limit:
            raise RateLimitError(f"Limite diario de analisis IA alcanzado ({limit}/dia).")
        pipe = self.redis.pipeline()
        pipe.incr(rate_key)
        pipe.expire(rate_key, 90000)
        await pipe.execute()

    # ─── Tenant Memory ─────────────────────────────────────────────────────────

    async def _get_tenant_memory(self, tenant_id: str) -> dict:
        """Read persistent tenant memory from Redis."""
        key = f"ai:memory:{tenant_id}"
        raw = await self.redis.get(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        return {
            "industria_detectada": None,
            "productos_estrella_historicos": [],
            "alertas_recurrentes": [],
            "recomendaciones_dadas": [],
            "patrones_detectados": [],
            "primer_analisis": None,
            "total_analisis": 0,
        }

    async def _update_tenant_memory(self, tenant_id: str, analysis: PnLAnalysis, pnl_data: dict) -> None:
        """Update persistent memory after a successful analysis."""
        memory = await self._get_tenant_memory(tenant_id)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        month = datetime.now(timezone.utc).strftime("%Y-%m")

        # First analysis date
        if not memory.get("primer_analisis"):
            memory["primer_analisis"] = now

        # Increment counter
        memory["total_analisis"] = memory.get("total_analisis", 0) + 1

        # Detect industry from categories if not set
        if not memory.get("industria_detectada"):
            biz = await self._get_business_context(tenant_id)
            cats = biz.get("categorias_productos", [])
            types = biz.get("tipos_producto", [])
            if cats or types:
                memory["industria_detectada"] = ", ".join(cats[:3]) if cats else ", ".join(types[:3])

        # Accumulate star products (deduplicated)
        existing_stars = set(memory.get("productos_estrella_historicos", []))
        for star in analysis.productos_estrella:
            existing_stars.add(star.sku)
        memory["productos_estrella_historicos"] = list(existing_stars)[:20]

        # Track recurring alerts (if same title appears 2+ times, mark as recurrent)
        alert_titles = [a.titulo for a in analysis.alertas]
        prev_alerts = memory.get("alertas_recurrentes", [])
        all_alert_history = memory.get("_alert_history", [])
        all_alert_history.extend(alert_titles)
        # Keep last 30 alert titles
        all_alert_history = all_alert_history[-30:]
        memory["_alert_history"] = all_alert_history
        # Find titles that appear 2+ times
        from collections import Counter
        counts = Counter(all_alert_history)
        recurrent = [t for t, c in counts.items() if c >= 2]
        memory["alertas_recurrentes"] = recurrent[:10]

        # Track recommendations given (keep last 20)
        prev_recs = memory.get("recomendaciones_dadas", [])
        for rec in analysis.recomendaciones:
            prev_recs.append({
                "fecha": month,
                "accion": rec.accion,
                "ejecutada": False,
            })
        memory["recomendaciones_dadas"] = prev_recs[-20:]

        # Save
        key = f"ai:memory:{tenant_id}"
        await self.redis.setex(key, MEMORY_TTL, json.dumps(memory, ensure_ascii=False))
        log.info("ai_memory_updated", tenant_id=tenant_id, total_analisis=memory["total_analisis"],
                 recurrent_alerts=len(memory["alertas_recurrentes"]))

    async def get_tenant_memory(self, tenant_id: str) -> dict:
        """Public accessor for the memory endpoint."""
        return await self._get_tenant_memory(tenant_id)

    async def delete_tenant_memory(self, tenant_id: str) -> bool:
        """Delete tenant memory (reset)."""
        key = f"ai:memory:{tenant_id}"
        deleted = await self.redis.delete(key)
        log.info("ai_memory_deleted", tenant_id=tenant_id)
        return deleted > 0

    # ─── Business Context Queries ──────────────────────────────────────────────

    async def _get_business_context(self, tenant_id: str) -> dict:
        from app.db.models.category import Category
        from app.db.models.config import ProductType
        from app.db.models.warehouse import Warehouse
        from app.db.models.partner import Partner

        result = await self.db.execute(select(Category.name).where(Category.tenant_id == tenant_id).limit(20))
        categories = [r[0] for r in result.all()]

        result = await self.db.execute(select(ProductType.name).where(ProductType.tenant_id == tenant_id).limit(10))
        product_types = [r[0] for r in result.all()]

        result = await self.db.execute(select(Warehouse.name).where(Warehouse.tenant_id == tenant_id).limit(10))
        warehouses = [r[0] for r in result.all()]

        try:
            result = await self.db.execute(
                select(Partner.name).where(Partner.tenant_id == tenant_id, Partner.is_supplier == True, Partner.is_active == True).limit(15)  # noqa: E712
            )
            suppliers = [r[0] for r in result.all()]
        except Exception:
            suppliers = []

        return {"categorias_productos": categories, "tipos_producto": product_types,
                "bodegas": warehouses, "proveedores_activos": suppliers}

    async def _get_product_category_map(self, tenant_id: str) -> dict[str, str]:
        from app.db.models import Product
        from app.db.models.category import Category
        result = await self.db.execute(
            select(Product.id, Category.name).outerjoin(Category, Product.category_id == Category.id).where(Product.tenant_id == tenant_id)
        )
        return {r[0]: (r[1] or "") for r in result.all()}

    async def _get_product_type_map(self, tenant_id: str) -> dict[str, str]:
        from app.db.models import Product
        from app.db.models.config import ProductType
        result = await self.db.execute(
            select(Product.id, ProductType.name).outerjoin(ProductType, Product.product_type_id == ProductType.id).where(Product.tenant_id == tenant_id)
        )
        return {r[0]: (r[1] or "") for r in result.all()}

    # ─── Prompt Building ───────────────────────────────────────────────────────

    async def _build_prompt(self, pnl_data: dict, tenant_id: str, date_from: str, date_to: str, memory: dict) -> str:
        totals = pnl_data.get("totals", {})
        products = pnl_data.get("products", [])

        biz = await self._get_business_context(tenant_id)
        cat_map = await self._get_product_category_map(tenant_id)
        type_map = await self._get_product_type_map(tenant_id)
        tenant_info = await self._get_tenant_info(tenant_id)

        margins = [p["summary"]["gross_margin_pct"] for p in products if p.get("summary", {}).get("gross_margin_pct") is not None]
        avg_margin = sum(margins) / len(margins) if margins else 0
        total_revenue = totals.get("total_revenue", 0)
        total_cogs = totals.get("total_cogs", 0)
        negative_count = sum(1 for p in products if (p.get("summary", {}).get("gross_margin_pct") or 0) < 0)

        sorted_by_profit = sorted(products, key=lambda x: x.get("summary", {}).get("gross_profit", 0), reverse=True)
        sorted_by_margin = sorted(products, key=lambda x: x.get("summary", {}).get("gross_margin_pct", 0) if x.get("summary", {}).get("gross_margin_pct") is not None else float("inf"))

        tenant_context = {
            "empresa": tenant_info.get("empresa", tenant_id),
            "moneda": "COP",
            "periodo": f"{date_from} al {date_to}",
            "categorias_productos": biz["categorias_productos"],
            "tipos_producto": biz["tipos_producto"],
            "bodegas": biz["bodegas"],
            "proveedores_activos": biz["proveedores_activos"],
            "total_productos": len(products),
            "margen_promedio": round(avg_margin, 2),
            "ingresos_totales": total_revenue,
            "costo_total": total_cogs,
            "utilidad_bruta": round(total_revenue - total_cogs, 2),
            "productos_margen_negativo": negative_count,
            "top_3_utilidad": [
                {"nombre": p.get("product_name"), "sku": p.get("product_sku"), "utilidad": p.get("summary", {}).get("gross_profit", 0)}
                for p in sorted_by_profit[:3]
            ],
            "bottom_3_margen": [
                {"nombre": p.get("product_name"), "sku": p.get("product_sku"), "margen": p.get("summary", {}).get("gross_margin_pct", 0)}
                for p in sorted_by_margin[:3]
            ],
        }

        # Build memory context for the prompt
        memory_context = {
            "industria_detectada": memory.get("industria_detectada") or "no detectada aun",
            "es_primer_analisis": memory.get("total_analisis", 0) == 0,
            "total_analisis_previos": memory.get("total_analisis", 0),
            "alertas_que_persisten": memory.get("alertas_recurrentes", []),
            "recomendaciones_pendientes": [
                r["accion"] for r in memory.get("recomendaciones_dadas", [])[-5:]
                if not r.get("ejecutada", False)
            ],
        }

        log.info("ai_prompt_context", tenant_id=tenant_id, empresa=tenant_context["empresa"],
                 industria=memory_context["industria_detectada"],
                 analisis_previos=memory_context["total_analisis_previos"],
                 alertas_recurrentes=len(memory_context["alertas_que_persisten"]))

        # Product details
        product_details = []
        for p in products:
            s = p.get("summary", {})
            m = p.get("market_analysis", {})
            pid = p.get("product_id", "")
            product_details.append({
                "sku": p.get("product_sku"), "nombre": p.get("product_name"),
                "categoria": cat_map.get(pid, ""), "tipo": type_map.get(pid, ""),
                "ingresos": s.get("total_revenue", 0), "costo": s.get("total_cogs", 0),
                "utilidad": s.get("gross_profit", 0), "margen_pct": s.get("gross_margin_pct", 0),
                "margen_objetivo": s.get("margin_target", 0), "uds_vendidas": s.get("total_sold_qty", 0),
                "stock_qty": s.get("stock_current_qty", 0), "stock_valor": s.get("stock_current_value", 0),
                "proveedor": m.get("best_supplier", ""), "precio_sugerido": m.get("suggested_price_today", 0),
            })

        return f"""\
CONTEXTO DEL NEGOCIO:
{json.dumps(tenant_context, ensure_ascii=False, indent=2)}

MEMORIA DEL NEGOCIO (historial de analisis previos):
{json.dumps(memory_context, ensure_ascii=False, indent=2)}

PRODUCTOS ({len(products)}):
{json.dumps(product_details, ensure_ascii=False, indent=2)}

{RESPONSE_SCHEMA}"""

    # ─── Tenant Info ───────────────────────────────────────────────────────────

    async def _get_tenant_info(self, tenant_id: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(
                    f"{self.settings.USER_SERVICE_URL}/api/v1/users",
                    headers={"X-Tenant-Id": tenant_id},
                    params={"limit": 1, "offset": 0},
                )
            if resp.status_code == 200:
                users = resp.json().get("items", [])
                if users:
                    return {"empresa": users[0].get("company") or tenant_id}
        except httpx.RequestError:
            pass
        return {"empresa": tenant_id}

    # ─── Response Parsing ──────────────────────────────────────────────────────

    def _parse_response(self, text: str) -> PnLAnalysis:
        log.info("ai_raw_response", length=len(text), preview=text[:200])
        clean = text.strip()
        if clean.startswith("```"):
            nl = clean.find("\n")
            clean = clean[nl + 1:] if nl > 0 else clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()
        if not clean.startswith("{"):
            start = clean.find("{")
            if start >= 0:
                clean = clean[start:]
        if not clean.endswith("}"):
            end = clean.rfind("}")
            if end >= 0:
                clean = clean[:end + 1]
        try:
            data = json.loads(clean)
            result = PnLAnalysis.model_validate(data)
            log.info("ai_parse_success", alertas=len(result.alertas), recomendaciones=len(result.recomendaciones))
            return result
        except json.JSONDecodeError as exc:
            log.error("ai_json_parse_error", error=str(exc), raw=clean[:500])
            raise
        except Exception as exc:
            log.error("ai_validation_error", error=str(exc), raw=clean[:500])
            raise
