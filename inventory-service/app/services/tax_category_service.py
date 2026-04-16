"""Tax categories CRUD service.

Tax categories are tenant-managed catalogs of tax kinds (IVA, IRPF, ICMS, ...).
Each category has a behavior (addition or withholding) that determines how the
calculation engine applies it to a sales order line.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.models.tax import TaxCategory, TaxRate

# Colombia MVP — catálogo bloqueado. Espejo de tax_service.CO_ALLOWED_TAX_SLUGS.
CO_ALLOWED_TAX_SLUGS = frozenset({"iva", "retefuente"})


class TaxCategoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_categories(self, tenant_id: str, *, include_inactive: bool = False) -> list[tuple[TaxCategory, int]]:
        """Return list of (category, rate_count) sorted by sort_order then name."""
        stmt = select(TaxCategory).where(TaxCategory.tenant_id == tenant_id)
        if not include_inactive:
            stmt = stmt.where(TaxCategory.is_active == True)
        stmt = stmt.order_by(TaxCategory.sort_order, TaxCategory.name)
        cats = list((await self.db.execute(stmt)).scalars().all())

        # Count rates per category in one query
        if not cats:
            return []
        ids = [c.id for c in cats]
        counts_rows = (await self.db.execute(
            select(TaxRate.category_id, func.count(TaxRate.id))
            .where(TaxRate.tenant_id == tenant_id, TaxRate.is_active == True, TaxRate.category_id.in_(ids))
            .group_by(TaxRate.category_id)
        )).all()
        counts = {row[0]: row[1] for row in counts_rows}
        return [(c, counts.get(c.id, 0)) for c in cats]

    async def get_category(self, tenant_id: str, category_id: str) -> TaxCategory:
        cat = (await self.db.execute(
            select(TaxCategory).where(
                TaxCategory.tenant_id == tenant_id,
                TaxCategory.id == category_id,
            )
        )).scalar_one_or_none()
        if not cat:
            raise NotFoundError("Categoría de impuesto no encontrada")
        return cat

    async def get_by_slug(self, tenant_id: str, slug: str) -> TaxCategory | None:
        return (await self.db.execute(
            select(TaxCategory).where(
                TaxCategory.tenant_id == tenant_id,
                TaxCategory.slug == slug,
                TaxCategory.is_active == True,
            )
        )).scalar_one_or_none()

    async def create_category(self, tenant_id: str, data: dict) -> TaxCategory:
        slug = data.get("slug", "").strip().lower()
        if not slug:
            raise ValidationError("El slug es obligatorio")
        # Colombia MVP: solo IVA y Retefuente
        if slug not in CO_ALLOWED_TAX_SLUGS:
            raise ValidationError(
                "Solo se permiten categorías IVA y Retefuente en Colombia"
            )
        existing = (await self.db.execute(
            select(TaxCategory).where(
                TaxCategory.tenant_id == tenant_id,
                TaxCategory.slug == slug,
            )
        )).scalar_one_or_none()
        if existing is not None:
            if existing.is_active:
                raise ConflictError(f"Ya existe una categoría con el slug '{slug}'")
            # Reactivate soft-deleted
            existing.is_active = True
            for k in ("name", "behavior", "base_kind", "description", "color", "sort_order"):
                if k in data and data[k] is not None:
                    setattr(existing, k, data[k])
            existing.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(existing)
            return existing

        cat = TaxCategory(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            slug=slug,
            name=data["name"].strip(),
            behavior=data["behavior"],
            base_kind=data.get("base_kind", "subtotal"),
            description=(data.get("description") or "").strip() or None,
            color=data.get("color"),
            sort_order=data.get("sort_order", 0),
            is_system=False,
            is_active=True,
        )
        self.db.add(cat)
        await self.db.flush()
        await self.db.refresh(cat)
        return cat

    async def update_category(self, tenant_id: str, category_id: str, data: dict) -> TaxCategory:
        cat = await self.get_category(tenant_id, category_id)
        if cat.is_system:
            # System categories: only name/description/color/sort_order are editable
            allowed = {"name", "description", "color", "sort_order", "is_active"}
            unsafe = set(data.keys()) - allowed
            if unsafe:
                raise ValidationError(
                    f"No se pueden modificar campos críticos en categoría del sistema: {', '.join(sorted(unsafe))}"
                )
        for k, v in data.items():
            if v is not None:
                setattr(cat, k, v)
        cat.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(cat)
        return cat

    async def delete_category(self, tenant_id: str, category_id: str) -> tuple[bool, int]:
        """Soft-delete. Returns (True, 0) on success or (False, rate_count) if blocked."""
        cat = await self.get_category(tenant_id, category_id)
        if cat.is_system:
            raise ValidationError("Las categorías del sistema no se pueden eliminar")
        # Block if any active tax_rate references it
        rate_count = ((await self.db.execute(
            select(func.count()).select_from(TaxRate).where(
                TaxRate.tenant_id == tenant_id,
                TaxRate.category_id == cat.id,
                TaxRate.is_active == True,
            )
        )).scalar() or 0)
        if rate_count > 0:
            return False, int(rate_count)
        cat.is_active = False
        cat.updated_at = datetime.utcnow()
        await self.db.flush()
        return True, 0
