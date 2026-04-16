"""Tax calculation service — administrable, multi-country.

Each tax_rate belongs to a tax_category. The category's `behavior` determines
whether the rate ADDS to the line total ("addition" — IVA, VAT, GST, ICA, ICMS)
or SUBTRACTS from the payable amount ("withholding" — Retención, IRPF, PIS).

The legacy `tax_type` string column is kept for backwards compatibility but
new rates should always have `category_id` set.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.tax import TaxRate, TaxCategory


# Colombia MVP — catálogo bloqueado. Agregar slugs acá cuando se expanda soporte.
CO_ALLOWED_TAX_SLUGS = frozenset({"iva", "retefuente"})


class TaxService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Queries ────────────────────────────────────────────────────────────────

    async def list_rates(
        self,
        tenant_id: str,
        *,
        tax_type: str | None = None,
        category_id: str | None = None,
        is_active: bool | None = True,
    ) -> list[TaxRate]:
        stmt = (
            select(TaxRate)
            .where(TaxRate.tenant_id == tenant_id)
            .options(selectinload(TaxRate.category))
        )
        if tax_type:
            stmt = stmt.where(TaxRate.tax_type == tax_type)
        if category_id:
            stmt = stmt.where(TaxRate.category_id == category_id)
        if is_active is not None:
            stmt = stmt.where(TaxRate.is_active == is_active)
        stmt = stmt.order_by(TaxRate.tax_type, TaxRate.rate.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_rate(self, rate_id: str, tenant_id: str) -> TaxRate | None:
        stmt = select(TaxRate).where(TaxRate.id == rate_id, TaxRate.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_iva_rate(self, tenant_id: str) -> TaxRate | None:
        stmt = select(TaxRate).where(
            TaxRate.tenant_id == tenant_id,
            TaxRate.tax_type == "iva",
            TaxRate.is_default == True,  # noqa: E712
            TaxRate.is_active == True,  # noqa: E712
        ).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_summary(self, tenant_id: str) -> dict:
        rates = await self.list_rates(tenant_id, is_active=True)
        default_iva = None
        iva_rates = []
        retention_rates = []
        for r in rates:
            if r.tax_type == "iva":
                iva_rates.append(r)
                if r.is_default:
                    default_iva = r
            elif r.tax_type == "retention":
                retention_rates.append(r)
        return {
            "default_iva": default_iva,
            "available_iva": iva_rates,
            "available_retention": retention_rates,
        }

    # ── Mutations ──────────────────────────────────────────────────────────────

    async def create_rate(self, tenant_id: str, data: dict) -> TaxRate:
        from app.core.errors import ValidationError, NotFoundError

        # Resolve category: prefer explicit category_id, fall back to slug, then legacy tax_type
        category_id = data.pop("category_id", None)
        category_slug = data.pop("category_slug", None)
        legacy_type = data.get("tax_type")

        category: TaxCategory | None = None
        if category_id:
            category = (await self.db.execute(
                select(TaxCategory).where(
                    TaxCategory.tenant_id == tenant_id,
                    TaxCategory.id == category_id,
                    TaxCategory.is_active == True,
                )
            )).scalar_one_or_none()
            if not category:
                raise NotFoundError("Categoría de impuesto no encontrada")
        elif category_slug:
            category = (await self.db.execute(
                select(TaxCategory).where(
                    TaxCategory.tenant_id == tenant_id,
                    TaxCategory.slug == category_slug,
                    TaxCategory.is_active == True,
                )
            )).scalar_one_or_none()
            if not category:
                raise NotFoundError(f"Categoría '{category_slug}' no encontrada")
        elif legacy_type:
            # Legacy fallback: try to find a category whose slug matches tax_type
            category = (await self.db.execute(
                select(TaxCategory).where(
                    TaxCategory.tenant_id == tenant_id,
                    TaxCategory.slug == legacy_type.lower(),
                    TaxCategory.is_active == True,
                )
            )).scalar_one_or_none()

        if not category:
            raise ValidationError(
                "Debes especificar una categoría de impuesto (category_id o category_slug)."
            )

        # Colombia MVP: bloquear cualquier categoría fuera de IVA/Retefuente
        from app.core.errors import ConflictError as _ConflictError
        if category.slug not in CO_ALLOWED_TAX_SLUGS:
            raise _ConflictError(
                "Impuesto no soportado en Colombia MVP: use IVA o Retefuente"
            )

        # Sync the legacy tax_type column to the category slug (kept for compat)
        data["tax_type"] = category.slug

        if data.get("is_default"):
            await self._unset_default(tenant_id, category.slug)

        from sqlalchemy.exc import IntegrityError
        from app.core.errors import ConflictError
        try:
            async with self.db.begin_nested():
                tax = TaxRate(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    category_id=category.id,
                    **data,
                )
                self.db.add(tax)
                await self.db.flush()
        except IntegrityError:
            raise ConflictError(
                f"Ya existe una tasa con ese nombre o valor para la categoría '{category.slug}'"
            )
        # Re-fetch with category eager-loaded for the response
        await self.db.refresh(tax, attribute_names=["category"])
        return tax

    async def update_rate(self, rate_id: str, tenant_id: str, data: dict) -> TaxRate:
        from app.core.errors import NotFoundError

        tax = await self.get_rate(rate_id, tenant_id)
        if not tax:
            raise NotFoundError("Tarifa no encontrada")

        # If category_id is being changed, validate it exists for this tenant
        new_category_id = data.get("category_id")
        if new_category_id and new_category_id != tax.category_id:
            new_cat = (await self.db.execute(
                select(TaxCategory).where(
                    TaxCategory.tenant_id == tenant_id,
                    TaxCategory.id == new_category_id,
                    TaxCategory.is_active == True,
                )
            )).scalar_one_or_none()
            if not new_cat:
                raise NotFoundError("Categoría de impuesto no encontrada")
            # Keep the legacy column in sync
            tax.tax_type = new_cat.slug

        if data.get("is_default"):
            slug_for_default = (
                tax.tax_type if not new_category_id else
                (await self.db.execute(
                    select(TaxCategory.slug).where(TaxCategory.id == new_category_id)
                )).scalar_one()
            )
            await self._unset_default(tenant_id, slug_for_default)

        for k, v in data.items():
            setattr(tax, k, v)
        await self.db.flush()
        await self.db.refresh(tax, attribute_names=["category"])
        return tax

    async def deactivate_rate(self, rate_id: str, tenant_id: str) -> TaxRate:
        tax = await self.get_rate(rate_id, tenant_id)
        if not tax:
            from app.core.errors import NotFoundError
            raise NotFoundError("Tarifa no encontrada")
        if tax.is_default:
            from app.core.errors import ValidationError
            raise ValidationError("No puedes desactivar la tarifa por defecto")
        tax.is_active = False
        await self.db.flush()
        return tax

    async def _unset_default(self, tenant_id: str, tax_type: str) -> None:
        stmt = (
            update(TaxRate)
            .where(
                TaxRate.tenant_id == tenant_id,
                TaxRate.tax_type == tax_type,
                TaxRate.is_default == True,  # noqa: E712
            )
            .values(is_default=False)
        )
        await self.db.execute(stmt)

    # ── Tax calculation ────────────────────────────────────────────────────────

    async def get_product_tax_rate(
        self, product, tenant_id: str
    ) -> tuple[Decimal, str | None]:
        """Return (rate, tax_rate_id) for a product following the hierarchy:
        1. product.is_tax_exempt → 0.00
        2. product.tax_rate_id → specific rate
        3. tenant default IVA → typically 19%
        4. hardcoded fallback → 0.19
        """
        if getattr(product, "is_tax_exempt", False):
            return Decimal("0.0000"), None

        tax_rate_id = getattr(product, "tax_rate_id", None)
        if tax_rate_id:
            tax = await self.get_rate(tax_rate_id, tenant_id)
            if tax and tax.is_active:
                return tax.rate, tax.id

        default_tax = await self.get_default_iva_rate(tenant_id)
        if default_tax:
            return default_tax.rate, default_tax.id

        return Decimal("0.1900"), None

    @staticmethod
    def calculate_line_taxes(
        subtotal: Decimal,
        tax_rate: Decimal,
        retention_rate: Decimal | None = None,
    ) -> dict:
        """Calculate taxes for a single SO line.

        Args:
            subtotal: price × qty − line discount
            tax_rate: e.g. Decimal("0.19")
            retention_rate: e.g. Decimal("0.025") or None
        """
        tax_amount = (subtotal * tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        retention_amount = Decimal("0")
        if retention_rate:
            retention_amount = (subtotal * retention_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        return {
            "tax_amount": tax_amount,
            "retention_amount": retention_amount,
            "line_total_with_tax": subtotal + tax_amount,
        }

    async def recalculate_so_taxes(self, so) -> None:
        """Recalculate all line taxes and update SO totals.

        New model: each line has a `line_taxes` collection (multi-stack). Each
        row links to a tax_rate whose category determines:
          - behavior: 'addition' (sums into tax_amount) or 'withholding' (sums
            into retention_amount).
          - base_kind: 'subtotal' (base = line subtotal) or
            'subtotal_with_other_additions' (base = subtotal + sum of other
            non-cumulative additions). The latter is needed for Brazil's IPI
            which is cumulative on top of ICMS.

        Legacy compatibility: lines without any line_taxes fall back to the
        single tax_rate_id + retention_pct columns (the old code path).
        """
        from app.db.models.tax import SalesOrderLineTax, TaxCategory, TaxRate

        total_tax = Decimal("0")
        total_retention = Decimal("0")
        subtotal_before_tax = Decimal("0")

        so_disc_pct = Decimal(str(so.discount_pct or 0))
        so_disc_factor = (Decimal("1") - so_disc_pct / Decimal("100")) if so_disc_pct > 0 else Decimal("1")

        for line in so.lines:
            line_subtotal = Decimal(str(line.unit_price)) * Decimal(str(line.qty_ordered))
            if line.discount_pct:
                line_subtotal *= (Decimal("1") - Decimal(str(line.discount_pct)) / Decimal("100"))
            line_subtotal = (line_subtotal * so_disc_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            line_addition = Decimal("0")
            line_withholding = Decimal("0")

            line_taxes = list(getattr(line, "line_taxes", None) or [])

            if line_taxes:
                # ── New path: multi-stack from line_taxes ──
                # Load rate + category for each line tax (cached eager-load)
                rate_ids = [lt.tax_rate_id for lt in line_taxes]
                rates_rows = (await self.db.execute(
                    select(TaxRate).where(TaxRate.id.in_(rate_ids))
                    .options(selectinload(TaxRate.category))
                )).scalars().all()
                rate_map = {r.id: r for r in rates_rows}

                # First pass: compute non-cumulative additions on the subtotal.
                # Cumulative additions and all withholdings are computed in pass two.
                non_cumulative_total = Decimal("0")
                for lt in line_taxes:
                    rate = rate_map.get(lt.tax_rate_id)
                    if not rate:
                        continue
                    cat = rate.category
                    if cat is None or cat.behavior != "addition":
                        continue
                    if cat.base_kind == "subtotal_with_other_additions":
                        continue
                    rate_frac = Decimal(str(rate.rate))
                    base = line_subtotal
                    amount = (base * rate_frac).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    lt.rate_pct = rate_frac
                    lt.base_amount = base
                    lt.tax_amount = amount
                    lt.behavior = "addition"
                    line_addition += amount
                    non_cumulative_total += amount

                # Second pass: cumulative additions (Brazil IPI on top of ICMS)
                for lt in line_taxes:
                    rate = rate_map.get(lt.tax_rate_id)
                    if not rate:
                        continue
                    cat = rate.category
                    if cat is None or cat.behavior != "addition":
                        continue
                    if cat.base_kind != "subtotal_with_other_additions":
                        continue
                    rate_frac = Decimal(str(rate.rate))
                    base = line_subtotal + non_cumulative_total
                    amount = (base * rate_frac).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    lt.rate_pct = rate_frac
                    lt.base_amount = base
                    lt.tax_amount = amount
                    lt.behavior = "addition"
                    line_addition += amount

                # Third pass: withholdings (always on subtotal)
                for lt in line_taxes:
                    rate = rate_map.get(lt.tax_rate_id)
                    if not rate:
                        continue
                    cat = rate.category
                    if cat is None or cat.behavior != "withholding":
                        continue
                    rate_frac = Decimal(str(rate.rate))
                    base = line_subtotal
                    amount = (base * rate_frac).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    lt.rate_pct = rate_frac
                    lt.base_amount = base
                    lt.tax_amount = amount
                    lt.behavior = "withholding"
                    line_withholding += amount

            else:
                # ── Legacy path: single tax_rate_id + retention_pct ──
                if getattr(line, "tax_rate_pct", None) is not None:
                    tax_rate_frac = Decimal(str(line.tax_rate_pct))
                else:
                    tax_rate_frac = Decimal(str(line.tax_rate or 0)) / Decimal("100")
                retention_pct = (
                    Decimal(str(line.retention_pct or 0))
                    if getattr(line, "retention_pct", None) else None
                )
                taxes = self.calculate_line_taxes(line_subtotal, tax_rate_frac, retention_pct)
                line_addition = taxes["tax_amount"]
                line_withholding = taxes["retention_amount"]

            # Persist the per-line summary so old reports keep working
            line.tax_amount = line_addition
            line.retention_amount = line_withholding
            line.line_total_with_tax = line_subtotal + line_addition

            total_tax += line_addition
            total_retention += line_withholding
            subtotal_before_tax += line_subtotal

        so.tax_amount = total_tax.quantize(Decimal("0.01"))
        so.total_retention = total_retention.quantize(Decimal("0.01"))
        so.total_with_tax = (subtotal_before_tax + total_tax).quantize(Decimal("0.01"))
        so.total_payable = (so.total_with_tax - total_retention).quantize(Decimal("0.01"))

    # ── Tenant initialization ──────────────────────────────────────────────────

    async def initialize_tenant_rates(self, tenant_id: str) -> list[TaxRate]:
        """Deprecated. The tax system is now fully administrable per tenant.

        Country-specific seed presets should be applied via the frontend wizard
        (or a future /tax-categories/seed-preset endpoint), not hardcoded here.
        Returning an empty list keeps callers from breaking.
        """
        return []
