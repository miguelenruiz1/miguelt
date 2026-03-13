"""Repository for Product CRUD."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Product, StockLevel


class ProductRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: str,
        product_type_id: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        stock_status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Product], int]:
        q = (
            select(Product)
            .where(Product.tenant_id == tenant_id)
        )
        if product_type_id is not None:
            q = q.where(Product.product_type_id == product_type_id)
        if is_active is not None:
            q = q.where(Product.is_active == is_active)
        if search:
            pattern = f"%{search}%"
            q = q.where(Product.name.ilike(pattern) | Product.sku.ilike(pattern))

        # Stock status filter
        if stock_status == "low":
            # Products that have stock but qty <= effective threshold
            from sqlalchemy import case
            effective = case(
                (StockLevel.reorder_point > 0, StockLevel.reorder_point),
                else_=case(
                    (Product.reorder_point > Product.min_stock_level, Product.reorder_point),
                    else_=Product.min_stock_level,
                ),
            )
            q = q.join(StockLevel, StockLevel.product_id == Product.id).where(
                StockLevel.qty_on_hand <= effective,
                StockLevel.qty_on_hand > 0,
                (StockLevel.reorder_point > 0) | (Product.reorder_point > 0) | (Product.min_stock_level > 0),
            )
        elif stock_status == "out":
            # Products with threshold configured but no stock records at all
            products_with_stock = (
                select(StockLevel.product_id)
                .where(StockLevel.tenant_id == tenant_id)
                .distinct()
                .correlate(None)
            )
            q = q.where(
                (Product.min_stock_level > 0) | (Product.reorder_point > 0),
                ~Product.id.in_(products_with_stock),
            )

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(Product.name).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().unique().all()), total

    async def get_by_id(self, product_id: str, tenant_id: str) -> Product | None:
        result = await self.db.execute(
            select(Product)
            .where(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_sku(self, sku: str, tenant_id: str) -> Product | None:
        result = await self.db.execute(
            select(Product).where(
                Product.sku == sku,
                Product.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Product:
        product = Product(id=str(uuid.uuid4()), **data)
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def update(self, product: Product, data: dict) -> Product:
        for k, v in data.items():
            setattr(product, k, v)
        product.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def soft_delete(self, product: Product) -> None:
        product.is_active = False
        product.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
