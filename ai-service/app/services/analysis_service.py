"""P&L analysis using Claude Haiku 4.5 with tenant memory — centralized in ai-service."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone

import anthropic
import redis.asyncio as aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AiFeatureDisabledError, AiNotConfiguredError, RateLimitError
from app.core.settings import get_settings
from app.domain.schemas import PnLAnalysis
from app.services.settings_service import AISettingsService

log = structlog.get_logger(__name__)

MEMORY_TTL = 90 * 24 * 3600
LAST_ANALYSIS_TTL = 24 * 3600

# ─── Prompt hardening ────────────────────────────────────────────────────────
#
# Every string that flows into the LLM prompt goes through _sanitize. It
# caps per-field length (blocks someone stuffing 10k chars of "ignore prior
# instructions" into a product description) and masks the common PII classes
# (emails, NITs, phone numbers) so we don't pipe customer PII to Anthropic
# for a report the LLM doesn't need it for. Worth noting: masking is "good
# enough" not legally airtight — if a tenant embeds raw PII inside a free-
# form note we might still leak. The real fix is a narrower schema for what
# the AI is allowed to see, but this closes the obvious hole today.

_PII_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Emails
    (re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "[email]"),
    # Colombian NIT: 6-10 digits + mandatory `-dv` (never mask bare numbers
    # or we nuke SKUs / order numbers / product IDs). The dash is what
    # distinguishes a NIT from any other numeric identifier.
    (re.compile(r"\b\d{6,10}\s*-\s*\d\b"), "[nit]"),
    # Phone numbers — require an explicit marker so pure-numeric SKUs like
    # 12345678 aren't masked. Match either an international prefix (+57…)
    # or a Colombian mobile-cell pattern (10 digits starting with 3).
    (re.compile(r"\+\d{7,15}\b"), "[phone]"),
    (re.compile(r"\b3\d{9}\b"), "[phone]"),
)

# Common prompt-injection phrases we scrub from user-supplied context before
# concatenating into the prompt. Not exhaustive — a determined attacker can
# evade this — but it catches the low-effort attacks that copy-paste a
# published jailbreak into a business profile field.
_INJECTION_MARKERS = (
    "ignore previous", "ignore prior", "ignore the above",
    "disregard previous", "disregard all", "forget everything",
    "you are now", "act as", "pretend to be",
    "system:", "system prompt", "new instructions",
    "</system>", "<|im_start|>", "<|im_end|>",
)

_MAX_FIELD_CHARS = 2000


def _sanitize(value):
    """Recursively scrub PII + prompt-injection markers from any value.

    Returns a structure-identical copy safe to serialize into the LLM prompt.
    """
    if isinstance(value, str):
        s = value
        for pattern, replacement in _PII_PATTERNS:
            s = pattern.sub(replacement, s)
        lower = s.lower()
        for marker in _INJECTION_MARKERS:
            if marker in lower:
                idx = lower.find(marker)
                s = s[:idx] + "[…]" + s[idx + len(marker):]
                lower = s.lower()
        if len(s) > _MAX_FIELD_CHARS:
            s = s[:_MAX_FIELD_CHARS] + "… [truncated]"
        return s
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value

SYSTEM_PROMPT = """\
Eres el asistente de inteligencia de inventario de TraceLog, una plataforma de inventario y trazabilidad para PYMEs colombianas.

TU ROL: Analizar TODA la operacion del negocio — rentabilidad, costos, stock, compras, ventas, movimientos — y detectar problemas antes de que se vuelvan criticos.

CAPACIDADES REALES DE TRACELOG (solo recomienda estas):
- Crear precios especiales por cliente
- Generar ordenes de compra a proveedores
- Generar ordenes de venta
- Configurar alertas de stock minimo y reorden
- Hacer conteos ciclicos de inventario
- Crear recetas de produccion y ordenes de produccion
- Reasignar stock entre bodegas
- Registrar movimientos manuales de inventario
- Ajustar precio sugerido de venta por producto
- Ver kardex por producto

CAPACIDADES NO DISPONIBLES (nunca las sugieras):
- Promociones, cupones, email marketing, envio gratis, publicidad, ecommerce, CRM

ANALISIS QUE DEBES HACER:
1. COSTOS: Si ves variaciones de costo >20% entre compras del mismo producto, ALERTA INMEDIATA. Indica el costo anterior vs nuevo, el proveedor y el impacto en margen.
2. STOCK: Si hay productos bajo el punto de reorden, recomienda generar OC al proveedor preferido.
3. MARGEN NEGATIVO: Si un producto tiene margen negativo, es ALERTA ALTA. Recomienda subir precio sugerido o cambiar proveedor.
4. MOVIMIENTOS SOSPECHOSOS: Si hay devoluciones frecuentes, ajustes de inventario grandes, o ventas sin costo, reportalo.
5. OPORTUNIDADES: Identifica productos estrella (alto margen + alto volumen) y sugiere acciones concretas.

REGLAS:
1. Cada recomendacion debe ser ejecutable HOY dentro de TraceLog
2. No repitas recomendaciones pendientes en memoria
3. Detecta la industria por productos y categorias
4. Usa nombres reales de productos, proveedores y bodegas
5. Moneda: COP. Se especifico y conciso con cifras reales
6. Si hay alertas recurrentes en memoria, priorizarlas
7. Si hay variaciones de costo de compra, SIEMPRE mencionarlas en alertas
8. Si hay productos con margen negativo, SIEMPRE es alerta alta\
"""

RESPONSE_SCHEMA = """\
RESPONDE SOLO CON JSON PURO. Sin ```, sin markdown, sin texto antes ni despues.
Campos "detalle","razon","accion" MAXIMO 80 chars.

{"resumen":"2-3 oraciones max 200 chars","alertas":[{"titulo":"max 40","detalle":"max 80 con cifras","severidad":"alta|media|baja","producto_sku":"SKU o null"}],"oportunidades":[{"titulo":"max 40","detalle":"max 80","impacto_estimado":"$X COP o X%","producto_sku":"SKU o null"}],"productos_estrella":[{"sku":"SKU","nombre":"Nombre","razon":"max 60"}],"recomendaciones":[{"accion":"max 80","prioridad":"alta|media|baja","producto_sku":"SKU o null","plazo":"inmediato|esta_semana|este_mes"}]}

Max: 3 alertas, 3 oportunidades, 2 estrellas, 4 recomendaciones.\
"""


class AnalysisService:
    def __init__(self, db: AsyncSession, redis_client: aioredis.Redis) -> None:
        self.db = db
        self.redis = redis_client
        self.settings_svc = AISettingsService(db, redis_client)

    async def analyze_pnl(self, tenant_id: str, date_from: str, date_to: str,
                           pnl_data: dict, business_context: dict | None = None,
                           force: bool = False) -> PnLAnalysis:
        config = await self.settings_svc.get_full_config()
        api_key = config.get("anthropic_api_key", "")
        if not api_key:
            raise AiNotConfiguredError("API key de Anthropic no configurada.")
        if not config.get("anthropic_enabled", False):
            raise AiFeatureDisabledError("IA deshabilitada globalmente.")
        if not config.get("pnl_analysis_enabled", True):
            raise AiFeatureDisabledError("Analisis de rentabilidad IA deshabilitado.")

        cache_ttl = config.get("cache_ttl_minutes", 60) * 60
        cache_key = f"ai:pnl:{tenant_id}:{date_from}:{date_to}"

        # 1. Session cache (only when not forced). The rate-limit check is
        # deliberately moved ABOVE the force=True branch: previously a user
        # could call with force=True repeatedly and skip the counter because
        # we only incremented on the uncached path, burning Anthropic quota.
        if not force and config.get("cache_enabled", True):
            cached = await self.redis.get(cache_key)
            if cached:
                result = PnLAnalysis.model_validate_json(cached)
                result.is_cached = True
                result.cache_source = "session_cache"
                return result

        # 2. Rate limit — fallback to last_saved
        try:
            await self._check_rate_limit(tenant_id)
        except RateLimitError:
            last = await self._get_last_analysis(tenant_id)
            if last:
                return last
            raise

        # Force-refresh comes after rate-limit check so the counter always
        # ticks for paid LLM calls.
        if force:
            await self.redis.delete(cache_key)

        # 3. Validate
        products = pnl_data.get("products", [])
        if not products:
            return PnLAnalysis(resumen="No hay datos de productos para analizar en el periodo seleccionado.")

        # 4. Memory
        memory = await self._get_tenant_memory(tenant_id)

        # 5. Build prompt
        prompt = self._build_prompt(pnl_data, tenant_id, date_from, date_to, memory, business_context)

        # 6. Call Claude
        model = config.get("anthropic_model_analysis", "claude-haiku-4-5-20251001")
        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=model, max_tokens=2048, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        # 7. Parse
        raw_text = response.content[0].text
        try:
            analysis = self._parse_response(raw_text)
        except Exception:
            return PnLAnalysis(resumen="El modelo respondio pero no se pudo interpretar. Haz clic en Regenerar.")

        analysis.cache_source = "fresh"

        # 8. Save last + update memory
        await self._save_last_analysis(tenant_id, analysis, date_from, date_to)
        try:
            await self._update_tenant_memory(tenant_id, analysis, pnl_data)
        except Exception as exc:
            log.warning("ai_memory_update_failed", error=str(exc))

        # 9. Session cache
        if config.get("cache_enabled", True):
            await self.redis.setex(cache_key, cache_ttl, analysis.model_dump_json())

        log.info("ai_analysis_complete", tenant_id=tenant_id, model=model,
                 input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens)
        return analysis

    # ─── Rate Limit ────────────────────────────────────────────────────────────

    async def _check_rate_limit(self, tenant_id: str) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rate_key = f"ai:pnl:rate:{tenant_id}:{today}"
        current = await self.redis.get(rate_key)
        count = int(current) if current else 0
        limit = get_settings().AI_ANALYSIS_DAILY_LIMIT
        if count >= limit:
            raise RateLimitError(f"Limite diario alcanzado ({limit}/dia).")
        pipe = self.redis.pipeline()
        pipe.incr(rate_key)
        pipe.expire(rate_key, 90000)
        await pipe.execute()

    # ─── Last Analysis ─────────────────────────────────────────────────────────

    async def _get_last_analysis(self, tenant_id: str) -> PnLAnalysis | None:
        raw = await self.redis.get(f"ai:pnl:last:{tenant_id}")
        if not raw:
            return None
        try:
            data = json.loads(raw)
            a = PnLAnalysis.model_validate(data["analysis"])
            a.is_cached = True
            a.cached_at = datetime.fromisoformat(data["cached_at"])
            a.cache_source = "last_saved"
            return a
        except Exception:
            return None

    async def _save_last_analysis(self, tenant_id: str, analysis: PnLAnalysis, date_from: str, date_to: str) -> None:
        payload = {"analysis": json.loads(analysis.model_dump_json()), "cached_at": datetime.now(timezone.utc).isoformat(), "date_from": date_from, "date_to": date_to}
        await self.redis.setex(f"ai:pnl:last:{tenant_id}", LAST_ANALYSIS_TTL, json.dumps(payload, ensure_ascii=False))

    async def delete_last_analysis(self, tenant_id: str) -> bool:
        return (await self.redis.delete(f"ai:pnl:last:{tenant_id}")) > 0

    # ─── Memory ────────────────────────────────────────────────────────────────

    async def _get_tenant_memory(self, tenant_id: str) -> dict:
        raw = await self.redis.get(f"ai:memory:{tenant_id}")
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                # Memory in Redis is corrupted; log and return empty (the next
                # analysis will rebuild it). Don't crash the analysis flow.
                from app.core.logging import get_logger
                get_logger(__name__).warning(
                    "tenant_memory_corrupt",
                    tenant_id=tenant_id,
                    error=str(exc)[:200],
                )
        return {}

    async def _update_tenant_memory(self, tenant_id: str, analysis: PnLAnalysis, pnl_data: dict) -> None:
        memory = await self._get_tenant_memory(tenant_id)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not memory.get("primer_analisis"):
            memory["primer_analisis"] = now
        memory["total_analisis"] = memory.get("total_analisis", 0) + 1

        # Industry detection from business_context
        if not memory.get("industria_detectada"):
            products = pnl_data.get("products", [])
            cats = list({p.get("categoria", "") for p in products if p.get("categoria")})
            if cats:
                memory["industria_detectada"] = ", ".join(cats[:3])

        # Star products
        stars = set(memory.get("productos_estrella_historicos", []))
        for s in analysis.productos_estrella:
            stars.add(s.sku)
        memory["productos_estrella_historicos"] = list(stars)[:20]

        # Recurring alerts with counter
        existing: dict[str, int] = {}
        for item in memory.get("alertas_recurrentes", []):
            if isinstance(item, dict):
                existing[item["alerta"]] = item.get("veces", 1)
        for a in analysis.alertas:
            existing[a.titulo] = existing.get(a.titulo, 0) + 1
        memory["alertas_recurrentes"] = [{"alerta": k, "veces": v} for k, v in sorted(existing.items(), key=lambda x: -x[1])][:10]

        # Recommendations
        recs = memory.get("recomendaciones_pendientes", [])
        for r in analysis.recomendaciones:
            recs.append({"fecha": now, "accion": r.accion, "ejecutada": False})
        memory["recomendaciones_pendientes"] = recs[-20:]

        # Patterns
        patterns = set(memory.get("patrones_detectados", []))
        products = pnl_data.get("products", [])
        selling = [p for p in products if p.get("summary", {}).get("total_sold_qty", 0) > 0]
        if len(selling) == 1 and len(products) > 3:
            patterns.add("ventas concentradas en 1 SKU")
        memory["patrones_detectados"] = list(patterns)[:10]

        await self.redis.setex(f"ai:memory:{tenant_id}", MEMORY_TTL, json.dumps(memory, ensure_ascii=False))

    async def get_tenant_memory(self, tenant_id: str) -> dict:
        return await self._get_tenant_memory(tenant_id)

    async def delete_tenant_memory(self, tenant_id: str) -> bool:
        return (await self.redis.delete(f"ai:memory:{tenant_id}")) > 0

    # ─── Prompt ────────────────────────────────────────────────────────────────

    def _build_prompt(self, pnl_data: dict, tenant_id: str, date_from: str, date_to: str, memory: dict, biz: dict | None = None) -> str:
        # Anything the caller feeds in is considered untrusted from a prompt
        # safety point of view — scrub PII and known injection markers before
        # it reaches the LLM context.
        pnl_data = _sanitize(pnl_data)
        biz = _sanitize(biz or {})
        memory = _sanitize(memory)
        totals = pnl_data.get("totals", {})
        products = pnl_data.get("products", [])

        margins = [p.get("summary", {}).get("gross_margin_pct", 0) for p in products if p.get("summary", {}).get("gross_margin_pct") is not None]
        avg_margin = sum(margins) / len(margins) if margins else 0

        tenant_context = {
            "empresa": biz.get("empresa", tenant_id), "moneda": "COP",
            "periodo": f"{date_from} al {date_to}",
            "categorias": biz.get("categorias_productos", []),
            "tipos_producto": biz.get("tipos_producto", []),
            "bodegas": biz.get("bodegas", []),
            "proveedores": biz.get("proveedores_activos", []),
            "total_productos": len(products), "margen_promedio": round(avg_margin, 2),
            "ingresos_totales": totals.get("total_revenue", 0),
            "utilidad_bruta": round(totals.get("total_revenue", 0) - totals.get("total_cogs", 0), 2),
        }

        # Memory context
        alertas_persist = []
        for item in memory.get("alertas_recurrentes", []):
            if isinstance(item, dict):
                alertas_persist.append(f"{item['alerta']} ({item.get('veces', 1)}x)")
        memory_ctx = {
            "industria": memory.get("industria_detectada") or "no detectada",
            "primer_analisis": memory.get("total_analisis", 0) == 0,
            "analisis_previos": memory.get("total_analisis", 0),
            "alertas_recurrentes": alertas_persist,
            "recomendaciones_pendientes": [r["accion"] for r in memory.get("recomendaciones_pendientes", [])[-5:] if not r.get("ejecutada")],
        }

        product_details = []
        for p in products:
            s = p.get("summary", {})
            m = p.get("market_analysis", {})
            product_details.append({
                "sku": p.get("product_sku") or p.get("sku", ""),
                "nombre": p.get("product_name") or p.get("nombre", ""),
                "categoria": p.get("categoria", ""), "tipo": p.get("tipo", ""),
                "ingresos": s.get("total_revenue", 0), "costo": s.get("total_cogs", 0),
                "utilidad": s.get("gross_profit", 0), "margen_pct": s.get("gross_margin_pct", 0),
                "margen_objetivo": s.get("margin_target", 0),
                "uds_vendidas": s.get("total_sold_qty", 0),
                "stock_qty": s.get("stock_current_qty", 0),
                "proveedor": m.get("best_supplier", ""),
            })

        # Inventory intelligence
        inventory_alerts = {}
        if biz.get("alertas_stock_bajo"):
            inventory_alerts["stock_bajo_reorden"] = biz["alertas_stock_bajo"]
        if biz.get("variaciones_costo_compra"):
            inventory_alerts["variaciones_costo_compra"] = biz["variaciones_costo_compra"]
        if biz.get("resumen_movimientos"):
            inventory_alerts["resumen_movimientos_periodo"] = biz["resumen_movimientos"]
        if biz.get("productos_margen_negativo"):
            inventory_alerts["productos_con_perdida"] = biz["productos_margen_negativo"]

        prompt = f"""\
NEGOCIO:
{json.dumps(tenant_context, ensure_ascii=False, indent=2)}

MEMORIA:
{json.dumps(memory_ctx, ensure_ascii=False, indent=2)}

PRODUCTOS ({len(products)}):
{json.dumps(product_details, ensure_ascii=False, indent=2)}
"""
        if inventory_alerts:
            prompt += f"""
ALERTAS DE INVENTARIO (PRIORIDAD ALTA — analiza esto primero):
{json.dumps(inventory_alerts, ensure_ascii=False, indent=2)}
"""
        prompt += f"\n{RESPONSE_SCHEMA}"
        return prompt

    # ─── Parse ─────────────────────────────────────────────────────────────────

    def _parse_response(self, text: str) -> PnLAnalysis:
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
        data = json.loads(clean)
        return PnLAnalysis.model_validate(data)
