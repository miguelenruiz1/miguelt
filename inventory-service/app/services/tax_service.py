"""Tax calculation service — Colombian tax system (IVA, retention)."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tax import TaxRate


class TaxService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Queries ────────────────────────────────────────────────────────────────

    async def list_rates(
        self, tenant_id: str, *, tax_type: str | None = None, is_active: bool | None = True,
    ) -> list[TaxRate]:
        stmt = select(TaxRate).where(TaxRate.tenant_id == tenant_id)
        if tax_type:
            stmt = stmt.where(TaxRate.tax_type == tax_type)
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
        if data.get("is_default"):
            await self._unset_default(tenant_id, data["tax_type"])
        tax = TaxRate(id=str(uuid4()), tenant_id=tenant_id, **data)
        self.db.add(tax)
        await self.db.flush()
        return tax

    async def update_rate(self, rate_id: str, tenant_id: str, data: dict) -> TaxRate:
        tax = await self.get_rate(rate_id, tenant_id)
        if not tax:
            from app.core.errors import NotFoundError
            raise NotFoundError("Tarifa no encontrada")
        if data.get("is_default"):
            await self._unset_default(tenant_id, tax.tax_type)
        for k, v in data.items():
            setattr(tax, k, v)
        await self.db.flush()
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

        Persists *post-discount* values on each line so per-line aggregates
        always agree with SO totals — previously the lines stored pre-discount
        values while the SO totals were post-discount, causing DIAN reject and
        confusing customer-facing PDFs. Also fixes the tax_rate_pct double
        division by 100 (the column is Numeric(5,4) stored as a fraction).
        """
        total_tax = Decimal("0")
        total_retention = Decimal("0")
        subtotal_before_tax = Decimal("0")

        so_disc_pct = Decimal(str(so.discount_pct or 0))
        so_disc_factor = (Decimal("1") - so_disc_pct / Decimal("100")) if so_disc_pct > 0 else Decimal("1")

        for line in so.lines:
            line_subtotal = Decimal(str(line.unit_price)) * Decimal(str(line.qty_ordered))
            if line.discount_pct:
                line_subtotal *= (Decimal("1") - Decimal(str(line.discount_pct)) / Decimal("100"))
            # Apply global SO discount on every line so persisted line totals
            # match the SO totals.
            line_subtotal = (line_subtotal * so_disc_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # tax_rate_pct is Numeric(5,4) and stored as a *fraction* (0.19);
            # the legacy `tax_rate` column was a percent (19). Distinguish so
            # we don't divide by 100 twice.
            if getattr(line, "tax_rate_pct", None) is not None:
                tax_rate_frac = Decimal(str(line.tax_rate_pct))
            else:
                tax_rate_frac = Decimal(str(line.tax_rate or 0)) / Decimal("100")
            retention_pct = Decimal(str(line.retention_pct or 0)) if getattr(line, "retention_pct", None) else None

            taxes = self.calculate_line_taxes(line_subtotal, tax_rate_frac, retention_pct)

            line.tax_amount = taxes["tax_amount"]
            line.retention_amount = taxes["retention_amount"]
            line.line_total_with_tax = taxes["line_total_with_tax"]

            total_tax += taxes["tax_amount"]
            total_retention += taxes["retention_amount"]
            subtotal_before_tax += line_subtotal

        so.tax_amount = total_tax.quantize(Decimal("0.01"))
        so.total_retention = total_retention.quantize(Decimal("0.01"))
        so.total_with_tax = (subtotal_before_tax + total_tax).quantize(Decimal("0.01"))
        so.total_payable = (so.total_with_tax - total_retention).quantize(Decimal("0.01"))

    # ── Tenant initialization ──────────────────────────────────────────────────

    async def initialize_tenant_rates(self, tenant_id: str) -> list[TaxRate]:
        """Create default Colombian tax rates for a tenant. Idempotent."""
        defaults = [
            {"name": "IVA 19%", "tax_type": "iva", "rate": Decimal("0.1900"),
             "is_default": True, "dian_code": "01", "description": "Tarifa general IVA Colombia"},
            {"name": "IVA 5%", "tax_type": "iva", "rate": Decimal("0.0500"),
             "is_default": False, "dian_code": "02", "description": "Tarifa diferencial IVA Colombia"},
            {"name": "IVA 0% Exento", "tax_type": "iva", "rate": Decimal("0.0000"),
             "is_default": False, "dian_code": "ZA", "description": "Bienes exentos de IVA"},
            {"name": "Retención 2.5%", "tax_type": "retention", "rate": Decimal("0.0250"),
             "is_default": False, "dian_code": None, "description": "Retención en la fuente general"},
            {"name": "Retención 3.5%", "tax_type": "retention", "rate": Decimal("0.0350"),
             "is_default": False, "dian_code": None, "description": "Retención en la fuente servicios"},
        ]
        created = []
        for d in defaults:
            existing = await self.db.execute(
                select(TaxRate).where(TaxRate.tenant_id == tenant_id, TaxRate.name == d["name"]).limit(1)
            )
            if not existing.scalar_one_or_none():
                tax = TaxRate(id=str(uuid4()), tenant_id=tenant_id, **d)
                self.db.add(tax)
                created.append(tax)
        if created:
            await self.db.flush()
        return created
