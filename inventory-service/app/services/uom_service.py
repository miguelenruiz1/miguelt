"""Unit of Measure service — conversions, initialization, caching."""
from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models.uom import UnitOfMeasure, UoMConversion


_STANDARD_UOMS: list[tuple[str, str, str, bool, Decimal | None]] = [
    ("Gramo", "g", "weight", True, None),
    ("Kilogramo", "kg", "weight", False, Decimal("1000")),
    ("Tonelada", "ton", "weight", False, Decimal("1000000")),
    ("Libra", "lb", "weight", False, Decimal("500")),
    ("Arroba", "arroba", "weight", False, Decimal("12500")),
    ("Mililitro", "ml", "volume", True, None),
    ("Litro", "L", "volume", False, Decimal("1000")),
    ("Galón", "gal", "volume", False, Decimal("3785")),
    ("Centímetro", "cm", "length", True, None),
    ("Metro", "m", "length", False, Decimal("100")),
    ("Vara", "vara", "length", False, Decimal("80")),
    ("Unidad", "un", "unit", True, None),
    ("Docena", "docena", "unit", False, Decimal("12")),
]


class UoMService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def initialize_tenant_uoms(self, tenant_id: str) -> list[UnitOfMeasure]:
        created: list[UnitOfMeasure] = []
        base_map: dict[str, str] = {}
        for name, symbol, category, is_base, factor in _STANDARD_UOMS:
            existing = (await self.db.execute(
                select(UnitOfMeasure).where(UnitOfMeasure.tenant_id == tenant_id, UnitOfMeasure.symbol == symbol)
            )).scalar_one_or_none()
            if existing:
                if is_base:
                    base_map[category] = existing.id
                continue
            uom = UnitOfMeasure(id=str(uuid.uuid4()), tenant_id=tenant_id, name=name, symbol=symbol, category=category, is_base=is_base)
            self.db.add(uom)
            await self.db.flush()
            created.append(uom)
            if is_base:
                base_map[category] = uom.id

        for name, symbol, category, is_base, factor in _STANDARD_UOMS:
            if is_base or factor is None:
                continue
            base_id = base_map.get(category)
            if not base_id:
                continue
            uom_result = (await self.db.execute(
                select(UnitOfMeasure).where(UnitOfMeasure.tenant_id == tenant_id, UnitOfMeasure.symbol == symbol)
            )).scalar_one_or_none()
            if not uom_result:
                continue
            existing_conv = (await self.db.execute(
                select(UoMConversion).where(UoMConversion.tenant_id == tenant_id, UoMConversion.from_uom_id == uom_result.id, UoMConversion.to_uom_id == base_id)
            )).scalar_one_or_none()
            if existing_conv:
                continue
            conv = UoMConversion(id=str(uuid.uuid4()), tenant_id=tenant_id, from_uom_id=uom_result.id, to_uom_id=base_id, factor=factor)
            self.db.add(conv)
        await self.db.flush()
        return created

    async def list_uoms(self, tenant_id: str) -> list[UnitOfMeasure]:
        result = await self.db.execute(
            select(UnitOfMeasure).where(UnitOfMeasure.tenant_id == tenant_id, UnitOfMeasure.is_active == True).order_by(UnitOfMeasure.category, UnitOfMeasure.name)
        )
        return list(result.scalars().all())

    async def create_uom(self, tenant_id: str, data: dict) -> UnitOfMeasure:
        uom = UnitOfMeasure(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(uom)
        await self.db.flush()
        await self.db.refresh(uom)
        return uom

    async def list_conversions(self, tenant_id: str) -> list[UoMConversion]:
        result = await self.db.execute(select(UoMConversion).where(UoMConversion.tenant_id == tenant_id, UoMConversion.is_active == True))
        return list(result.scalars().all())

    async def create_conversion(self, tenant_id: str, data: dict) -> UoMConversion:
        conv = UoMConversion(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(conv)
        await self.db.flush()
        await self.db.refresh(conv)
        return conv

    async def get_conversion_factor(self, from_uom_symbol: str, to_uom_symbol: str, tenant_id: str) -> Decimal:
        if from_uom_symbol == to_uom_symbol:
            return Decimal("1")
        from_uom = (await self.db.execute(select(UnitOfMeasure).where(UnitOfMeasure.tenant_id == tenant_id, UnitOfMeasure.symbol == from_uom_symbol))).scalar_one_or_none()
        to_uom = (await self.db.execute(select(UnitOfMeasure).where(UnitOfMeasure.tenant_id == tenant_id, UnitOfMeasure.symbol == to_uom_symbol))).scalar_one_or_none()
        if not from_uom or not to_uom:
            raise NotFoundError(f"UoM not found: {from_uom_symbol} or {to_uom_symbol}")
        if from_uom.category != to_uom.category:
            raise ValidationError(f"Cannot convert between different categories: {from_uom.category} → {to_uom.category}")

        direct = (await self.db.execute(select(UoMConversion).where(UoMConversion.tenant_id == tenant_id, UoMConversion.from_uom_id == from_uom.id, UoMConversion.to_uom_id == to_uom.id, UoMConversion.is_active == True))).scalar_one_or_none()
        if direct:
            return direct.factor
        reverse = (await self.db.execute(select(UoMConversion).where(UoMConversion.tenant_id == tenant_id, UoMConversion.from_uom_id == to_uom.id, UoMConversion.to_uom_id == from_uom.id, UoMConversion.is_active == True))).scalar_one_or_none()
        if reverse:
            return (Decimal("1") / reverse.factor).quantize(Decimal("0.0000000001"))

        from_to_base = (await self.db.execute(select(UoMConversion).where(UoMConversion.tenant_id == tenant_id, UoMConversion.from_uom_id == from_uom.id, UoMConversion.is_active == True))).scalar_one_or_none()
        to_to_base = (await self.db.execute(select(UoMConversion).where(UoMConversion.tenant_id == tenant_id, UoMConversion.from_uom_id == to_uom.id, UoMConversion.is_active == True))).scalar_one_or_none()
        if from_to_base and to_to_base:
            return (from_to_base.factor / to_to_base.factor).quantize(Decimal("0.0000000001"))
        if from_to_base and to_uom.is_base:
            return from_to_base.factor
        if to_to_base and from_uom.is_base:
            return (Decimal("1") / to_to_base.factor).quantize(Decimal("0.0000000001"))
        raise ValidationError(f"No conversion path found: {from_uom_symbol} → {to_uom_symbol}")

    async def convert(self, quantity: Decimal, from_uom_symbol: str, to_uom_symbol: str, tenant_id: str) -> Decimal:
        if from_uom_symbol == to_uom_symbol:
            return quantity
        factor = await self.get_conversion_factor(from_uom_symbol, to_uom_symbol, tenant_id)
        return (quantity * factor).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    async def convert_to_base(self, quantity: Decimal, from_uom_symbol: str, tenant_id: str) -> Decimal:
        uom = (await self.db.execute(select(UnitOfMeasure).where(UnitOfMeasure.tenant_id == tenant_id, UnitOfMeasure.symbol == from_uom_symbol))).scalar_one_or_none()
        if not uom:
            raise NotFoundError(f"UoM {from_uom_symbol!r} not found")
        if uom.is_base:
            return quantity
        base = (await self.db.execute(select(UnitOfMeasure).where(UnitOfMeasure.tenant_id == tenant_id, UnitOfMeasure.category == uom.category, UnitOfMeasure.is_base == True))).scalar_one_or_none()
        if not base:
            raise ValidationError(f"No base UoM found for category {uom.category!r}")
        return await self.convert(quantity, from_uom_symbol, base.symbol, tenant_id)
