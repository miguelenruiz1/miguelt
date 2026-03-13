"""Business logic for Supplier management."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func, select

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.models import POStatus, PurchaseOrder, Supplier
from app.repositories.supplier_repo import SupplierRepository


class SupplierService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SupplierRepository(db)

    async def list(
        self,
        tenant_id: str,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Supplier], int]:
        return await self.repo.list(tenant_id=tenant_id, is_active=is_active, offset=offset, limit=limit)

    async def get(self, supplier_id: str, tenant_id: str) -> Supplier:
        supplier = await self.repo.get_by_id(supplier_id, tenant_id)
        if not supplier:
            raise NotFoundError(f"Supplier {supplier_id!r} not found")
        return supplier

    async def create(self, tenant_id: str, data: dict) -> Supplier:
        if await self.repo.get_by_code(data["code"], tenant_id):
            raise ConflictError(f"Supplier code {data['code']!r} already exists")
        return await self.repo.create({"tenant_id": tenant_id, **data})

    async def update(self, supplier_id: str, tenant_id: str, data: dict) -> Supplier:
        supplier = await self.get(supplier_id, tenant_id)
        if "code" in data and data["code"] != supplier.code:
            if await self.repo.get_by_code(data["code"], tenant_id):
                raise ConflictError(f"Supplier code {data['code']!r} already exists")
        return await self.repo.update(supplier, data)

    async def delete(self, supplier_id: str, tenant_id: str) -> None:
        supplier = await self.get(supplier_id, tenant_id)
        terminal = {POStatus.canceled, POStatus.received}
        active_po_count = (await self.db.execute(
            select(func.count())
            .select_from(PurchaseOrder)
            .where(
                PurchaseOrder.tenant_id == tenant_id,
                PurchaseOrder.supplier_id == supplier_id,
                PurchaseOrder.status.notin_(terminal),
            )
        )).scalar_one()
        if active_po_count:
            raise ValidationError(
                f"No se puede eliminar: el proveedor tiene {active_po_count} orden(es) de compra activa(s)"
            )
        await self.repo.soft_delete(supplier)
