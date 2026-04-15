"""Business logic for module activation management."""
from __future__ import annotations

import logging

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.settings import get_settings
from app.db.models import TenantModuleActivation
from app.repositories.module_repo import ModuleRepository

log = logging.getLogger(__name__)

# Consumer Redis DBs that cache `module:{tenant_id}:{slug}` status.
# Matches REDIS_URL assignments in docker-compose.yml so a module
# toggle invalidates the cache in every service that reads it.
# Order: trace(0), user(2), inventory(4), integration(5), compliance(6),
# ai(7), media(8). Missing DBs are safely ignored (connection errors logged).
_CONSUMER_REDIS_DBS: tuple[int, ...] = (0, 2, 4, 5, 6, 7, 8)


async def _invalidate_module_cache(tenant_id: str, slug: str) -> None:
    """Best-effort: DEL `module:{tenant_id}:{slug}` in every consumer Redis DB.
    Failures are logged but never raised — the DB row is the source of truth."""
    settings = get_settings()
    base = settings.REDIS_URL.rsplit("/", 1)[0]
    key = f"module:{tenant_id}:{slug}"
    for db in _CONSUMER_REDIS_DBS:
        url = f"{base}/{db}"
        try:
            client = aioredis.from_url(url, decode_responses=True)
            await client.delete(key)
            await client.aclose()
        except Exception as exc:  # pragma: no cover — best-effort
            log.warning("module_cache_invalidate_failed db=%s key=%s err=%s", db, key, exc)

# ─── Module catalogue ─────────────────────────────────────────────────────────
# Only real modules that are fully implemented and can be toggled.

MODULE_CATALOG: list[dict] = [
    {
        "slug": "logistics",
        "name": "Logística",
        "description": "Gestión de cadena de custodia, cargas y custodios. Tracking en tiempo real.",
    },
    {
        "slug": "inventory",
        "name": "Inventario",
        "description": "Control de stock, productos, bodegas, movimientos y órdenes de compra.",
    },
    {
        "slug": "electronic-invoicing",
        "name": "Facturación Electrónica",
        "description": "Emite facturas, notas credito y notas debito ante la DIAN. Soporta modo produccion y modo sandbox (pruebas).",
        "category": "compliance",
        "requires": "inventory",
    },
    {
        "slug": "production",
        "name": "Produccion",
        "description": "Gestion de recetas (BOM), corridas de produccion y costeo por transformacion",
        "icon": "factory",
        "category": "operations",
        "dependencies": ["inventory"],
    },
    {
        "slug": "compliance",
        "name": "Cumplimiento Normativo",
        "description": "Gestión de normas regulatorias internacionales (EUDR, USDA, FSSAI). Parcelas, records, validación automática y certificados PDF.",
        "category": "compliance",
        "dependencies": ["logistics"],
        "icon": "ShieldCheck",
    },
    {
        "slug": "ai-analysis",
        "name": "Inteligencia Artificial",
        "description": "Análisis de rentabilidad con IA. Insights automáticos, alertas de margen, oportunidades y recomendaciones accionables.",
        "category": "analytics",
        "dependencies": ["inventory"],
        "icon": "Sparkles",
    },
]

_CATALOG_BY_SLUG = {m["slug"]: m for m in MODULE_CATALOG}


class ModuleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ModuleRepository(db)

    def get_catalog(self) -> list[dict]:
        return MODULE_CATALOG

    async def is_active(self, tenant_id: str, slug: str) -> bool:
        record = await self.repo.get(tenant_id, slug)
        return record is not None and record.is_active

    async def activate(
        self,
        tenant_id: str,
        slug: str,
        performed_by: str | None = None,
    ) -> TenantModuleActivation:
        record = await self.repo.activate(tenant_id, slug, performed_by=performed_by)
        # Flush the cache in every consumer service so the change takes effect
        # immediately instead of waiting for the TTL to expire.
        await _invalidate_module_cache(tenant_id, slug)
        return record

    async def deactivate(
        self,
        tenant_id: str,
        slug: str,
        performed_by: str | None = None,
    ) -> TenantModuleActivation:
        record = await self.repo.deactivate(tenant_id, slug, performed_by=performed_by)
        if not record:
            raise NotFoundError(f"Module '{slug}' has no activation record for tenant '{tenant_id}'")
        await _invalidate_module_cache(tenant_id, slug)
        return record

    async def list_tenant_modules(self, tenant_id: str) -> list[dict]:
        """Return catalog enriched with is_active status for this tenant."""
        activations = {
            r.module_slug: r.is_active
            for r in await self.repo.list_for_tenant(tenant_id)
        }

        return [
            {**mod, "is_active": activations.get(mod["slug"], False)}
            for mod in MODULE_CATALOG
        ]
