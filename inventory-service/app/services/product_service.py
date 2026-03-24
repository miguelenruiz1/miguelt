"""Business logic for Product management."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func, select

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.models import Product, PurchaseOrder, PurchaseOrderLine, POStatus, RecipeComponent, StockLevel, StockMovement
from app.repositories.product_repo import ProductRepository

# Fields that become immutable once the product has stock movements.
# Changing these would break traceability / historical accuracy.
LOCKED_FIELDS_WITH_MOVEMENTS = {"sku", "unit_of_measure", "track_batches", "valuation_method"}


class ProductService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ProductRepository(db)

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
        return await self.repo.list(
            tenant_id=tenant_id,
            product_type_id=product_type_id,
            is_active=is_active,
            search=search,
            stock_status=stock_status,
            offset=offset,
            limit=limit,
        )

    async def get(self, product_id: str, tenant_id: str) -> Product:
        product = await self.repo.get_by_id(product_id, tenant_id)
        if not product:
            raise NotFoundError(f"Product {product_id!r} not found")
        return product

    async def has_movements(self, product_id: str, tenant_id: str) -> bool:
        """Check if a product has any stock movements (makes certain fields immutable)."""
        count = (await self.db.execute(
            select(func.count())
            .select_from(StockMovement)
            .where(StockMovement.product_id == product_id, StockMovement.tenant_id == tenant_id)
        )).scalar_one()
        return count > 0

    async def create(self, tenant_id: str, data: dict) -> Product:
        # Apply ProductType defaults if a type is set
        product_type_id = data.get("product_type_id")
        if product_type_id:
            from app.db.models.config import ProductType
            pt = (await self.db.execute(
                select(ProductType).where(ProductType.id == product_type_id, ProductType.tenant_id == tenant_id)
            )).scalar_one_or_none()
            if pt:
                # Default category from type if not explicitly set
                if not data.get("category_id") and pt.default_category_id:
                    data["category_id"] = pt.default_category_id
                # Default track_batches from type
                if "track_batches" not in data or not data["track_batches"]:
                    data["track_batches"] = pt.tracks_batches
                # Auto-generate SKU with prefix if SKU not provided or is empty
                if pt.sku_prefix and (not data.get("sku") or data["sku"].strip() == ""):
                    data["sku"] = await self._next_sku(tenant_id, pt.sku_prefix)

        if await self.repo.get_by_sku(data["sku"], tenant_id):
            raise ConflictError(f"SKU {data['sku']!r} already exists for this tenant")
        product = await self.repo.create({"tenant_id": tenant_id, **data})
        return product

    async def _next_sku(self, tenant_id: str, prefix: str) -> str:
        """Generate next sequential SKU: PREFIX-0001, PREFIX-0002, etc."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Product)
            .where(Product.tenant_id == tenant_id, Product.sku.like(f"{prefix}-%"))
        )
        count = result.scalar_one()
        return f"{prefix}-{count + 1:04d}"

    async def update(self, product_id: str, tenant_id: str, data: dict) -> Product:
        product = await self.get(product_id, tenant_id)
        # Enforce immutable fields once the product has movements
        attempted_locked = {
            k for k in LOCKED_FIELDS_WITH_MOVEMENTS
            if k in data and data[k] != getattr(product, k)
        }
        if attempted_locked and await self.has_movements(product_id, tenant_id):
            labels = {"sku": "SKU", "unit_of_measure": "Unidad de medida", "track_batches": "Rastreo por lotes", "valuation_method": "Método de valorización"}
            names = ", ".join(labels.get(f, f) for f in attempted_locked)
            raise ValidationError(
                f"No se puede modificar {names} porque el producto ya tiene movimientos de inventario"
            )
        if "sku" in data and data["sku"] != product.sku:
            existing = await self.repo.get_by_sku(data["sku"], tenant_id)
            if existing:
                raise ConflictError(f"SKU {data['sku']!r} already exists for this tenant")
        product = await self.repo.update(product, data)

        # Auto-recalculate prices when margins change
        if any(k in data for k in ("margin_target", "margin_minimum", "margin_cost_method")):
            from app.services.pricing_engine import PricingEngine
            engine = PricingEngine(self.db)
            await engine.recalculate_product_prices(product, tenant_id)

        # Propagate reorder_point / min_stock_level changes to StockLevels
        # that still use the product-level default (i.e. have no warehouse override)
        if "reorder_point" in data or "min_stock_level" in data:
            new_rp = max(product.reorder_point or 0, product.min_stock_level or 0)
            await self.db.execute(
                StockLevel.__table__.update()
                .where(
                    StockLevel.product_id == product_id,
                    StockLevel.tenant_id == tenant_id,
                )
                .values(reorder_point=new_rp)
            )

        return product

    async def delete(self, product_id: str, tenant_id: str) -> None:
        product = await self.get(product_id, tenant_id)
        # Check no active PO lines reference this product
        terminal = {POStatus.canceled, POStatus.received}
        active_po_count = (await self.db.execute(
            select(func.count())
            .select_from(PurchaseOrderLine)
            .join(PurchaseOrder, PurchaseOrderLine.po_id == PurchaseOrder.id)
            .where(
                PurchaseOrder.tenant_id == tenant_id,
                PurchaseOrderLine.product_id == product_id,
                PurchaseOrder.status.notin_(terminal),
            )
        )).scalar_one()
        if active_po_count:
            raise ValidationError(
                f"No se puede eliminar: el producto tiene {active_po_count} línea(s) en órdenes de compra activas"
            )
        # Check no active recipe components reference this product
        recipe_count = (await self.db.execute(
            select(func.count())
            .select_from(RecipeComponent)
            .where(RecipeComponent.component_entity_id == product_id)
        )).scalar_one()
        if recipe_count:
            raise ValidationError(
                f"No se puede eliminar: el producto es componente en {recipe_count} receta(s)"
            )
        await self.repo.soft_delete(product)
