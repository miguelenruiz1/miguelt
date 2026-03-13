"""Business logic for customer-specific negotiated prices."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.customer_price import CustomerPrice, CustomerPriceHistory
from app.db.models.entity import Product
from app.db.models.variant import ProductVariant


class CustomerPriceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Core lookup ────────────────────────────────────────────────────

    async def get_customer_price(
        self,
        tenant_id: str,
        customer_id: str,
        product_id: str,
        quantity: Decimal,
        variant_id: str | None = None,
        db: AsyncSession | None = None,
    ) -> CustomerPrice | None:
        """Find best matching active customer price considering validity, min_quantity, variant.

        Variant-specific prices take priority over product-level (variant_id IS NULL).
        Orders by: variant_id DESC NULLS LAST, min_quantity DESC, valid_from DESC.
        """
        session = db or self.db
        today = date.today()

        stmt = (
            select(CustomerPrice)
            .where(
                CustomerPrice.tenant_id == tenant_id,
                CustomerPrice.customer_id == customer_id,
                CustomerPrice.product_id == product_id,
                CustomerPrice.is_active == True,  # noqa: E712
                CustomerPrice.valid_from <= today,
                or_(CustomerPrice.valid_to == None, CustomerPrice.valid_to >= today),  # noqa: E711
                CustomerPrice.min_quantity <= quantity,
            )
        )

        # Include both variant-specific and product-level matches
        if variant_id:
            stmt = stmt.where(
                or_(CustomerPrice.variant_id == variant_id, CustomerPrice.variant_id == None)  # noqa: E711
            )
        else:
            stmt = stmt.where(CustomerPrice.variant_id == None)  # noqa: E711

        # Variant-specific first, then highest min_quantity, then most recent
        stmt = stmt.order_by(
            CustomerPrice.variant_id.desc().nulls_last(),
            CustomerPrice.min_quantity.desc(),
            CustomerPrice.valid_from.desc(),
        ).limit(1)

        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Create / Update ────────────────────────────────────────────────

    async def set_customer_price(
        self,
        tenant_id: str,
        customer_id: str,
        product_id: str,
        new_price: Decimal,
        created_by: str,
        created_by_name: str | None = None,
        valid_from: date | None = None,
        valid_to: date | None = None,
        reason: str | None = None,
        min_quantity: Decimal = Decimal("1"),
        variant_id: str | None = None,
        currency: str = "COP",
        db: AsyncSession | None = None,
    ) -> CustomerPrice:
        """Create or update a customer price. Logs history on price change."""
        session = db or self.db
        vf = valid_from or date.today()

        # Try to find existing active price for same key
        stmt = select(CustomerPrice).where(
            CustomerPrice.tenant_id == tenant_id,
            CustomerPrice.customer_id == customer_id,
            CustomerPrice.product_id == product_id,
            CustomerPrice.min_quantity == min_quantity,
            CustomerPrice.is_active == True,  # noqa: E712
        )
        if variant_id:
            stmt = stmt.where(CustomerPrice.variant_id == variant_id)
        else:
            stmt = stmt.where(CustomerPrice.variant_id == None)  # noqa: E711

        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            old_price = existing.price
            existing.price = new_price
            existing.valid_from = vf
            existing.valid_to = valid_to
            existing.reason = reason
            existing.currency = currency

            # Log history if price actually changed
            if old_price != new_price:
                history = CustomerPriceHistory(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    customer_price_id=existing.id,
                    customer_id=customer_id,
                    product_id=product_id,
                    old_price=old_price,
                    new_price=new_price,
                    changed_by=created_by,
                    changed_by_name=created_by_name,
                    reason=reason,
                )
                session.add(history)

            await session.flush()
            return existing
        else:
            cp = CustomerPrice(
                id=str(uuid4()),
                tenant_id=tenant_id,
                customer_id=customer_id,
                product_id=product_id,
                variant_id=variant_id,
                price=new_price,
                min_quantity=min_quantity,
                currency=currency,
                valid_from=vf,
                valid_to=valid_to,
                reason=reason,
                created_by=created_by,
            )
            session.add(cp)

            # Initial history entry
            history = CustomerPriceHistory(
                id=str(uuid4()),
                tenant_id=tenant_id,
                customer_price_id=cp.id,
                customer_id=customer_id,
                product_id=product_id,
                old_price=None,
                new_price=new_price,
                changed_by=created_by,
                changed_by_name=created_by_name,
                reason=reason,
            )
            session.add(history)

            await session.flush()
            return cp

    # ── Deactivate ─────────────────────────────────────────────────────

    async def deactivate(
        self, customer_price_id: str, tenant_id: str, db: AsyncSession | None = None,
    ) -> None:
        session = db or self.db
        await session.execute(
            update(CustomerPrice)
            .where(CustomerPrice.id == customer_price_id, CustomerPrice.tenant_id == tenant_id)
            .values(is_active=False)
        )
        await session.flush()

    # ── Listings ───────────────────────────────────────────────────────

    async def list_for_customer(
        self, tenant_id: str, customer_id: str, active_only: bool = True,
        db: AsyncSession | None = None,
    ) -> list[CustomerPrice]:
        session = db or self.db
        stmt = (
            select(CustomerPrice)
            .options(joinedload(CustomerPrice.product), joinedload(CustomerPrice.customer))
            .where(CustomerPrice.tenant_id == tenant_id, CustomerPrice.customer_id == customer_id)
        )
        if active_only:
            stmt = stmt.where(CustomerPrice.is_active == True)  # noqa: E712
        stmt = stmt.order_by(CustomerPrice.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().unique().all())

    async def list_for_product(
        self, tenant_id: str, product_id: str, active_only: bool = True,
        db: AsyncSession | None = None,
    ) -> list[CustomerPrice]:
        session = db or self.db
        stmt = (
            select(CustomerPrice)
            .options(joinedload(CustomerPrice.product), joinedload(CustomerPrice.customer))
            .where(CustomerPrice.tenant_id == tenant_id, CustomerPrice.product_id == product_id)
        )
        if active_only:
            stmt = stmt.where(CustomerPrice.is_active == True)  # noqa: E712
        stmt = stmt.order_by(CustomerPrice.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().unique().all())

    async def list_all(
        self,
        tenant_id: str,
        customer_id: str | None = None,
        product_id: str | None = None,
        is_active: bool | None = None,
        is_expired: bool | None = None,
        offset: int = 0,
        limit: int = 50,
        db: AsyncSession | None = None,
    ) -> list[CustomerPrice]:
        session = db or self.db
        stmt = (
            select(CustomerPrice)
            .options(joinedload(CustomerPrice.product), joinedload(CustomerPrice.customer))
            .where(CustomerPrice.tenant_id == tenant_id)
        )
        if customer_id:
            stmt = stmt.where(CustomerPrice.customer_id == customer_id)
        if product_id:
            stmt = stmt.where(CustomerPrice.product_id == product_id)
        if is_active is not None:
            stmt = stmt.where(CustomerPrice.is_active == is_active)
        if is_expired is True:
            today = date.today()
            stmt = stmt.where(CustomerPrice.valid_to != None, CustomerPrice.valid_to < today)  # noqa: E711
        elif is_expired is False:
            today = date.today()
            stmt = stmt.where(
                or_(CustomerPrice.valid_to == None, CustomerPrice.valid_to >= today)  # noqa: E711
            )
        stmt = stmt.order_by(CustomerPrice.created_at.desc()).offset(offset).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_id(
        self, id: str, tenant_id: str, db: AsyncSession | None = None,
    ) -> CustomerPrice | None:
        session = db or self.db
        stmt = (
            select(CustomerPrice)
            .options(
                joinedload(CustomerPrice.product),
                joinedload(CustomerPrice.customer),
                joinedload(CustomerPrice.variant),
            )
            .where(CustomerPrice.id == id, CustomerPrice.tenant_id == tenant_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    # ── History ────────────────────────────────────────────────────────

    async def get_history(
        self,
        tenant_id: str,
        customer_id: str | None = None,
        product_id: str | None = None,
        db: AsyncSession | None = None,
    ) -> list[CustomerPriceHistory]:
        session = db or self.db
        stmt = select(CustomerPriceHistory).where(CustomerPriceHistory.tenant_id == tenant_id)
        if customer_id:
            stmt = stmt.where(CustomerPriceHistory.customer_id == customer_id)
        if product_id:
            stmt = stmt.where(CustomerPriceHistory.product_id == product_id)
        stmt = stmt.order_by(CustomerPriceHistory.changed_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    # ── Price Lookup (with fallback) ───────────────────────────────────

    async def lookup(
        self,
        tenant_id: str,
        customer_id: str,
        product_id: str,
        quantity: Decimal = Decimal("1"),
        variant_id: str | None = None,
        db: AsyncSession | None = None,
    ) -> dict:
        """Full price lookup: customer special -> product base price.

        Returns {price, source, customer_price_id, valid_to, reason}.
        """
        session = db or self.db

        # Resolve base price first (always needed)
        base_price: Decimal = Decimal("0")
        if variant_id:
            v_result = await session.execute(
                select(ProductVariant.sale_price).where(ProductVariant.id == variant_id)
            )
            vp = v_result.scalar_one_or_none()
            if vp and Decimal(str(vp)) > 0:
                base_price = Decimal(str(vp))

        if base_price == 0:
            p_result = await session.execute(
                select(Product.sale_price).where(Product.id == product_id, Product.tenant_id == tenant_id)
            )
            pp = p_result.scalar_one_or_none()
            if pp:
                base_price = Decimal(str(pp))

        # 1. Customer special price
        cp = await self.get_customer_price(tenant_id, customer_id, product_id, quantity, variant_id, db=session)
        if cp:
            return {
                "price": float(cp.price),
                "original_price": float(base_price),
                "source": "customer_special",
                "customer_price_id": cp.id,
                "valid_to": cp.valid_to.isoformat() if cp.valid_to else None,
                "reason": cp.reason,
            }

        # 2. Product base price
        return {
            "price": float(base_price),
            "original_price": float(base_price),
            "source": "product_base",
            "customer_price_id": None,
            "valid_to": None,
            "reason": None,
        }

    # ── Metrics ────────────────────────────────────────────────────────

    async def count_active(self, tenant_id: str, db: AsyncSession | None = None) -> int:
        session = db or self.db
        result = await session.execute(
            select(func.count(CustomerPrice.id)).where(
                CustomerPrice.tenant_id == tenant_id,
                CustomerPrice.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one() or 0

    async def count_expiring_soon(self, tenant_id: str, days: int = 30, db: AsyncSession | None = None) -> int:
        session = db or self.db
        today = date.today()
        from datetime import timedelta
        cutoff = today + timedelta(days=days)
        result = await session.execute(
            select(func.count(CustomerPrice.id)).where(
                CustomerPrice.tenant_id == tenant_id,
                CustomerPrice.is_active == True,  # noqa: E712
                CustomerPrice.valid_to != None,  # noqa: E711
                CustomerPrice.valid_to >= today,
                CustomerPrice.valid_to <= cutoff,
            )
        )
        return result.scalar_one() or 0

    async def count_customers_with_prices(self, tenant_id: str, db: AsyncSession | None = None) -> int:
        session = db or self.db
        result = await session.execute(
            select(func.count(func.distinct(CustomerPrice.customer_id))).where(
                CustomerPrice.tenant_id == tenant_id,
                CustomerPrice.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one() or 0
