"""Business logic for module activation management."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models import TenantModuleActivation
from app.repositories.module_repo import ModuleRepository

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
        return await self.repo.activate(tenant_id, slug, performed_by=performed_by)

    async def deactivate(
        self,
        tenant_id: str,
        slug: str,
        performed_by: str | None = None,
    ) -> TenantModuleActivation:
        record = await self.repo.deactivate(tenant_id, slug, performed_by=performed_by)
        if not record:
            raise NotFoundError(f"Module '{slug}' has no activation record for tenant '{tenant_id}'")
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
