"""Invoice resolution management — DIAN numbering ranges per tenant."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models.integration import InvoiceResolution


class ResolutionExpiredError(ValidationError):
    def __init__(self):
        super().__init__("La resolución de facturación está vencida. Configure una nueva resolución.")


class ResolutionExhaustedError(ValidationError):
    def __init__(self):
        super().__init__("El rango de numeración está agotado. Configure una nueva resolución.")


class ResolutionNotConfiguredError(ValidationError):
    def __init__(self, provider: str):
        super().__init__(f"No hay resolución configurada para el proveedor '{provider}'. Configure la resolución DIAN antes de emitir facturas.")


class ResolutionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active_resolution(self, tenant_id: str, provider: str) -> InvoiceResolution | None:
        result = await self.db.execute(
            select(InvoiceResolution).where(
                InvoiceResolution.tenant_id == tenant_id,
                InvoiceResolution.provider == provider,
                InvoiceResolution.is_active == True,  # noqa: E712
            )
        )
        return result.scalars().first()

    async def get_next_number(self, tenant_id: str, provider: str) -> tuple[str, int]:
        """Atomically increment and return the next invoice number.

        Returns (formatted_number, raw_number) e.g. ("SANDBOX990000001", 990000001).
        """
        resolution = await self.get_active_resolution(tenant_id, provider)
        if not resolution:
            raise ResolutionNotConfiguredError(provider)

        if resolution.valid_to < date.today():
            raise ResolutionExpiredError()

        if resolution.current_number >= resolution.range_to:
            raise ResolutionExhaustedError()

        # Atomic increment with range guard
        stmt = (
            update(InvoiceResolution)
            .where(
                InvoiceResolution.id == resolution.id,
                InvoiceResolution.current_number < InvoiceResolution.range_to,
            )
            .values(current_number=InvoiceResolution.current_number + 1)
            .returning(InvoiceResolution.current_number)
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if not row:
            raise ResolutionExhaustedError()

        new_number = row[0]
        formatted = f"{resolution.prefix}{new_number}"
        return formatted, new_number

    async def create_resolution(self, tenant_id: str, data: dict) -> InvoiceResolution:
        provider = data["provider"]

        # Deactivate previous active resolution for same tenant+provider
        await self.db.execute(
            update(InvoiceResolution)
            .where(
                InvoiceResolution.tenant_id == tenant_id,
                InvoiceResolution.provider == provider,
                InvoiceResolution.is_active == True,  # noqa: E712
            )
            .values(is_active=False)
        )

        resolution = InvoiceResolution(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            provider=provider,
            is_active=True,
            resolution_number=data["resolution_number"],
            prefix=data["prefix"],
            range_from=data["range_from"],
            range_to=data["range_to"],
            current_number=data.get("current_number", 0),
            valid_from=data["valid_from"],
            valid_to=data["valid_to"],
        )
        self.db.add(resolution)
        await self.db.flush()
        await self.db.refresh(resolution)
        return resolution

    async def deactivate_resolution(self, tenant_id: str, provider: str) -> None:
        result = await self.db.execute(
            update(InvoiceResolution)
            .where(
                InvoiceResolution.tenant_id == tenant_id,
                InvoiceResolution.provider == provider,
                InvoiceResolution.is_active == True,  # noqa: E712
            )
            .values(is_active=False)
        )
        if result.rowcount == 0:
            raise NotFoundError("No hay resolución activa para desactivar")

    async def ensure_sandbox_resolution(self, tenant_id: str) -> InvoiceResolution:
        """Create default sandbox resolution if none exists for this tenant."""
        existing = await self.get_active_resolution(tenant_id, "sandbox")
        if existing:
            return existing

        return await self.create_resolution(tenant_id, {
            "provider": "sandbox",
            "resolution_number": "18760000001",
            "prefix": "SANDBOX",
            "range_from": 990000000,
            "range_to": 995000000,
            "current_number": 0,
            "valid_from": date(2019, 1, 19),
            "valid_to": date(2030, 1, 19),
        })
