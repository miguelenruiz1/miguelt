"""Unit of Measure service — conversions, initialization, caching."""
from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.models.uom import UnitOfMeasure, UoMConversion


# Standard UoMs grouped by category. Tuple format:
#   (name, symbol, category, is_implicit_base, factor_to_implicit_base)
# `factor` = how many implicit-base units equal 1 of this UoM. The implicit base
# has factor None. Conversions are linear (new = old × factor) — categories
# requiring affine conversions (like temperature) should NOT be modeled here.
_STANDARD_UOMS: list[tuple[str, str, str, bool, Decimal | None]] = [
    # ── Peso (base implícita: gramo) ────────────────────────────────────────
    ("Gramo", "g", "weight", True, None),
    ("Kilogramo", "kg", "weight", False, Decimal("1000")),
    ("Tonelada", "ton", "weight", False, Decimal("1000000")),
    ("Libra", "lb", "weight", False, Decimal("500")),
    ("Arroba", "arroba", "weight", False, Decimal("12500")),
    ("Onza", "oz", "weight", False, Decimal("28.3495")),
    ("Quintal", "qq", "weight", False, Decimal("50000")),

    # ── Volumen (base implícita: mililitro) ─────────────────────────────────
    ("Mililitro", "ml", "volume", True, None),
    ("Litro", "L", "volume", False, Decimal("1000")),
    ("Centímetro cúbico", "cm3", "volume", False, Decimal("1")),
    ("Metro cúbico", "m3", "volume", False, Decimal("1000000")),
    ("Galón", "gal", "volume", False, Decimal("3785")),
    ("Barril", "bbl", "volume", False, Decimal("158987")),

    # ── Longitud (base implícita: centímetro) ───────────────────────────────
    ("Centímetro", "cm", "length", True, None),
    ("Milímetro", "mm", "length", False, Decimal("0.1")),
    ("Metro", "m", "length", False, Decimal("100")),
    ("Kilómetro", "km", "length", False, Decimal("100000")),
    ("Pulgada", "in", "length", False, Decimal("2.54")),
    ("Pie", "ft", "length", False, Decimal("30.48")),
    ("Vara", "vara", "length", False, Decimal("80")),

    # ── Área (base implícita: metro cuadrado) ───────────────────────────────
    ("Metro cuadrado", "m2", "area", True, None),
    ("Centímetro cuadrado", "cm2", "area", False, Decimal("0.0001")),
    ("Hectárea", "ha", "area", False, Decimal("10000")),
    ("Pie cuadrado", "ft2", "area", False, Decimal("0.092903")),
    ("Acre", "acre", "area", False, Decimal("4046.86")),

    # ── Cantidad / unidades (base implícita: unidad) ────────────────────────
    ("Unidad", "un", "unit", True, None),
    ("Par", "par", "unit", False, Decimal("2")),
    ("Docena", "docena", "unit", False, Decimal("12")),
    ("Centena", "centena", "unit", False, Decimal("100")),
    ("Millar", "millar", "unit", False, Decimal("1000")),

    # ── Tiempo (base implícita: segundo SI) ─────────────────────────────────
    ("Segundo", "s", "time", True, None),
    ("Minuto", "min", "time", False, Decimal("60")),
    ("Hora", "h", "time", False, Decimal("3600")),
    ("Día", "dia", "time", False, Decimal("86400")),
    ("Semana", "semana", "time", False, Decimal("604800")),

    # ── Energía (base implícita: joule SI) ──────────────────────────────────
    ("Joule", "J", "energy", True, None),
    ("Kilojoule", "kJ", "energy", False, Decimal("1000")),
    ("Kilovatio-hora", "kWh", "energy", False, Decimal("3600000")),
    ("BTU", "BTU", "energy", False, Decimal("1055.06")),
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
                # Reactivate if it was soft-deleted previously
                if not existing.is_active:
                    existing.is_active = True
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
                # Reactivate if it was soft-deleted previously
                if not existing_conv.is_active:
                    existing_conv.is_active = True
                continue
            conv = UoMConversion(id=str(uuid.uuid4()), tenant_id=tenant_id, from_uom_id=uom_result.id, to_uom_id=base_id, factor=factor)
            self.db.add(conv)
        await self.db.flush()
        return created

    async def setup_tenant_uoms(self, tenant_id: str, bases: list[dict]) -> dict:
        """Setup wizard — additive. `bases` = [{category, base_symbol}, ...].

        For each requested category, seeds the standard UoMs only if the
        category currently has NO active UoMs in this tenant. Categories that
        already have units are silently skipped (returned in `skipped`).

        This makes the endpoint idempotent and safe to re-run for adding new
        standard categories later. To change the base of an existing category
        use change_category_base instead.
        """
        # Determine which categories already have active units for this tenant
        already_present_rows = (await self.db.execute(
            select(UnitOfMeasure.category).where(
                UnitOfMeasure.tenant_id == tenant_id,
                UnitOfMeasure.is_active == True,
            ).distinct()
        )).all()
        already_present = {r[0] for r in already_present_rows}

        # Group standard UoMs by category
        by_category: dict[str, list[tuple]] = {}
        for entry in _STANDARD_UOMS:
            by_category.setdefault(entry[2], []).append(entry)

        created_count = 0
        configured_categories: list[str] = []
        skipped_categories: list[str] = []
        for choice in bases:
            category = choice.get("category")
            chosen_symbol = choice.get("base_symbol")
            if not category or not chosen_symbol:
                continue
            if category not in by_category:
                raise ValidationError(f"Categoría desconocida: '{category}'")
            if category in already_present:
                # Skip — already configured. Use change_category_base to modify.
                skipped_categories.append(category)
                continue
            category_uoms = by_category[category]

            chosen_entry = next((e for e in category_uoms if e[1] == chosen_symbol), None)
            if not chosen_entry:
                raise ValidationError(
                    f"Símbolo '{chosen_symbol}' no es estándar para la categoría '{category}'"
                )

            # Pivot: factor of chosen UoM in implicit-base units (1 if it IS the implicit base)
            pivot: Decimal = chosen_entry[4] if chosen_entry[4] is not None else Decimal("1")

            # Create or reactivate every UoM in this category
            uom_by_symbol: dict[str, UnitOfMeasure] = {}
            for name, symbol, cat, _is_implicit_base, _implicit_factor in category_uoms:
                is_base_flag = (symbol == chosen_symbol)
                existing = (await self.db.execute(
                    select(UnitOfMeasure).where(
                        UnitOfMeasure.tenant_id == tenant_id,
                        UnitOfMeasure.symbol == symbol,
                    )
                )).scalar_one_or_none()
                if existing:
                    existing.is_active = True
                    existing.is_base = is_base_flag
                    existing.name = name
                    existing.category = cat
                    uom_by_symbol[symbol] = existing
                else:
                    uom = UnitOfMeasure(
                        id=str(uuid.uuid4()), tenant_id=tenant_id,
                        name=name, symbol=symbol, category=cat, is_base=is_base_flag,
                    )
                    self.db.add(uom)
                    uom_by_symbol[symbol] = uom
                    created_count += 1
            await self.db.flush()

            # Create conversions: every non-base UoM → chosen base.
            # Reactivate any soft-deleted conversion with the same (from, to)
            # to avoid violating uq_uom_conv_tenant_from_to.
            chosen_uom = uom_by_symbol[chosen_symbol]
            for name, symbol, _cat, _is_implicit_base, implicit_factor in category_uoms:
                if symbol == chosen_symbol:
                    continue
                other_implicit = implicit_factor if implicit_factor is not None else Decimal("1")
                new_factor = (other_implicit / pivot).quantize(Decimal("0.0000000001"))
                from_uom = uom_by_symbol[symbol]
                existing_conv = (await self.db.execute(
                    select(UoMConversion).where(
                        UoMConversion.tenant_id == tenant_id,
                        UoMConversion.from_uom_id == from_uom.id,
                        UoMConversion.to_uom_id == chosen_uom.id,
                    )
                )).scalar_one_or_none()
                if existing_conv:
                    existing_conv.is_active = True
                    existing_conv.factor = new_factor
                else:
                    conv = UoMConversion(
                        id=str(uuid.uuid4()), tenant_id=tenant_id,
                        from_uom_id=from_uom.id, to_uom_id=chosen_uom.id,
                        factor=new_factor,
                    )
                    self.db.add(conv)

            configured_categories.append(category)

        await self.db.flush()
        return {
            "created": created_count,
            "categories_set_up": configured_categories,
            "skipped": skipped_categories,
        }

    async def change_category_base(self, tenant_id: str, category: str, new_base_id: str) -> dict:
        """Change the base UoM of a category and re-calculate qty_in_base_uom
        across all transactional tables. Atomic.
        """
        current_base = (await self.db.execute(
            select(UnitOfMeasure).where(
                UnitOfMeasure.tenant_id == tenant_id,
                UnitOfMeasure.category == category,
                UnitOfMeasure.is_base == True,
                UnitOfMeasure.is_active == True,
            )
        )).scalar_one_or_none()
        if not current_base:
            raise NotFoundError(f"No hay unidad base activa para la categoría '{category}'")

        new_base = (await self.db.execute(
            select(UnitOfMeasure).where(
                UnitOfMeasure.tenant_id == tenant_id,
                UnitOfMeasure.id == new_base_id,
                UnitOfMeasure.is_active == True,
            )
        )).scalar_one_or_none()
        if not new_base:
            raise NotFoundError("Unidad destino no encontrada")
        if new_base.category != category:
            raise ValidationError("La unidad destino no pertenece a esta categoría")
        if new_base.id == current_base.id:
            raise ValidationError("La unidad destino ya es la base actual")

        # Find pivot conversion: (new_base → current_base, factor)
        # 'factor' = how many current_base units equal 1 new_base unit
        pivot_conv = (await self.db.execute(
            select(UoMConversion).where(
                UoMConversion.tenant_id == tenant_id,
                UoMConversion.from_uom_id == new_base.id,
                UoMConversion.to_uom_id == current_base.id,
                UoMConversion.is_active == True,
            )
        )).scalar_one_or_none()
        if not pivot_conv:
            raise ValidationError(
                f"No existe una conversión de '{new_base.symbol}' → '{current_base.symbol}'. "
                "Crea esa conversión antes de cambiar la base."
            )
        pivot: Decimal = pivot_conv.factor
        if pivot <= 0:
            raise ValidationError("El factor de conversión es inválido (≤ 0)")

        # Symbols of every UoM in this category — used to identify affected products
        cat_symbols = [
            row[0] for row in (await self.db.execute(
                select(UnitOfMeasure.symbol).where(
                    UnitOfMeasure.tenant_id == tenant_id,
                    UnitOfMeasure.category == category,
                )
            )).all()
        ]
        if not cat_symbols:
            cat_symbols = [current_base.symbol]

        # Re-calculate qty_in_base_uom across transactional tables.
        # NOTE: This is wrapped in the outer request transaction, so any error
        # rolls back the whole change-base operation atomically.
        affected: dict[str, int] = {}
        update_specs = [
            ("purchase_order_lines", """
                UPDATE purchase_order_lines AS pol
                SET qty_in_base_uom = pol.qty_in_base_uom / :pivot
                FROM entities AS e, purchase_orders AS po
                WHERE pol.product_id = e.id
                  AND po.id = pol.po_id
                  AND po.tenant_id = :t
                  AND e.tenant_id = :t
                  AND e.unit_of_measure = ANY(:syms)
                  AND pol.qty_in_base_uom IS NOT NULL
            """),
            ("sales_order_lines", """
                UPDATE sales_order_lines AS sol
                SET qty_in_base_uom = sol.qty_in_base_uom / :pivot
                FROM entities AS e, sales_orders AS so
                WHERE sol.product_id = e.id
                  AND so.id = sol.order_id
                  AND so.tenant_id = :t
                  AND e.tenant_id = :t
                  AND e.unit_of_measure = ANY(:syms)
                  AND sol.qty_in_base_uom IS NOT NULL
            """),
            ("product_cost_history", """
                UPDATE product_cost_history AS pch
                SET qty_in_base_uom = pch.qty_in_base_uom / :pivot,
                    unit_cost_base_uom = pch.unit_cost_base_uom * :pivot
                FROM entities AS e
                WHERE pch.product_id = e.id
                  AND pch.tenant_id = :t
                  AND e.tenant_id = :t
                  AND e.unit_of_measure = ANY(:syms)
            """),
        ]
        for table, sql in update_specs:
            result = await self.db.execute(
                text(sql), {"pivot": pivot, "t": tenant_id, "syms": cat_symbols}
            )
            affected[table] = result.rowcount or 0

        # Rebase conversions:
        #   - The pivot row (new_base → current_base, pivot) flips to (current_base → new_base, 1/pivot)
        #   - Every other (X → current_base, F) becomes (X → new_base, F / pivot)
        convs = (await self.db.execute(
            select(UoMConversion).where(
                UoMConversion.tenant_id == tenant_id,
                UoMConversion.is_active == True,
                UoMConversion.to_uom_id == current_base.id,
            )
        )).scalars().all()
        for c in convs:
            if c.from_uom_id == new_base.id:
                c.from_uom_id = current_base.id
                c.to_uom_id = new_base.id
                c.factor = (Decimal("1") / pivot).quantize(Decimal("0.0000000001"))
            else:
                c.to_uom_id = new_base.id
                c.factor = (c.factor / pivot).quantize(Decimal("0.0000000001"))

        # Flip the base flags
        current_base.is_base = False
        new_base.is_base = True

        await self.db.flush()
        return {
            "old_base": current_base.symbol,
            "new_base": new_base.symbol,
            "pivot": str(pivot),
            "affected": affected,
        }

    async def list_uoms(self, tenant_id: str) -> list[UnitOfMeasure]:
        result = await self.db.execute(
            select(UnitOfMeasure).where(UnitOfMeasure.tenant_id == tenant_id, UnitOfMeasure.is_active == True).order_by(UnitOfMeasure.category, UnitOfMeasure.name)
        )
        return list(result.scalars().all())

    async def _demote_existing_base(self, tenant_id: str, category: str, exclude_id: str | None = None) -> None:
        """Ensure there is only one base UoM per category by demoting any other."""
        stmt = select(UnitOfMeasure).where(
            UnitOfMeasure.tenant_id == tenant_id,
            UnitOfMeasure.category == category,
            UnitOfMeasure.is_base == True,
            UnitOfMeasure.is_active == True,
        )
        if exclude_id is not None:
            stmt = stmt.where(UnitOfMeasure.id != exclude_id)
        for other in (await self.db.execute(stmt)).scalars().all():
            other.is_base = False

    async def _category_has_active_base(self, tenant_id: str, category: str, exclude_id: str | None = None) -> bool:
        stmt = select(func.count()).select_from(UnitOfMeasure).where(
            UnitOfMeasure.tenant_id == tenant_id,
            UnitOfMeasure.category == category,
            UnitOfMeasure.is_base == True,
            UnitOfMeasure.is_active == True,
        )
        if exclude_id is not None:
            stmt = stmt.where(UnitOfMeasure.id != exclude_id)
        return ((await self.db.execute(stmt)).scalar() or 0) > 0

    async def create_uom(self, tenant_id: str, data: dict) -> UnitOfMeasure:
        symbol = data.get("symbol")
        category = data.get("category")
        is_base = bool(data.get("is_base"))

        # Setting is_base from a normal create is only allowed when no base exists yet
        # for the category. To change an existing base, use change_category_base().
        if is_base and category and await self._category_has_active_base(tenant_id, category):
            raise ValidationError(
                f"La categoría '{category}' ya tiene una unidad base. "
                "Para cambiarla, usa la operación de cambio de base."
            )

        # If a UoM with this symbol already exists (active or soft-deleted),
        # either reactivate it or raise a friendly error.
        existing = (await self.db.execute(
            select(UnitOfMeasure).where(
                UnitOfMeasure.tenant_id == tenant_id,
                UnitOfMeasure.symbol == symbol,
            )
        )).scalar_one_or_none()
        if existing is not None:
            if existing.is_active:
                raise ValidationError(f"Ya existe una unidad con el símbolo '{symbol}'")
            # Reactivate and update with the new metadata. is_base stays as it was
            # unless the new value is explicitly true AND the category has no base.
            existing.is_active = True
            for field in ("name", "category"):
                if field in data and data[field] is not None:
                    setattr(existing, field, data[field])
            if is_base and not await self._category_has_active_base(tenant_id, existing.category, exclude_id=existing.id):
                existing.is_base = True
            else:
                existing.is_base = False
            await self.db.flush()
            await self.db.refresh(existing)
            return existing

        uom = UnitOfMeasure(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(uom)
        await self.db.flush()
        await self.db.refresh(uom)
        return uom

    async def get_uom_usage(self, tenant_id: str, uom_id: str) -> list[dict]:
        """Return list of {area, count} where this UoM symbol is referenced.

        UoM is referenced by symbol (string) across multiple tables, not by FK.
        """
        uom = (await self.db.execute(
            select(UnitOfMeasure).where(UnitOfMeasure.tenant_id == tenant_id, UnitOfMeasure.id == uom_id)
        )).scalar_one_or_none()
        if not uom:
            return []
        symbol = uom.symbol
        usage: list[dict] = []
        checks = [
            ("Productos",            "SELECT COUNT(*) FROM entities WHERE tenant_id = :t AND unit_of_measure = :s"),
            ("Niveles de stock",     "SELECT COUNT(*) FROM stock_levels WHERE tenant_id = :t AND uom = :s"),
            ("Líneas de compra",     "SELECT COUNT(*) FROM purchase_order_lines pol JOIN purchase_orders po ON po.id = pol.po_id WHERE po.tenant_id = :t AND pol.uom = :s"),
            ("Líneas de venta",      "SELECT COUNT(*) FROM sales_order_lines sol JOIN sales_orders so ON so.id = sol.order_id WHERE so.tenant_id = :t AND sol.uom = :s"),
        ]
        for area, sql in checks:
            count = 0
            # Use SAVEPOINT so a failing query (e.g., missing column) doesn't poison the outer txn
            try:
                async with self.db.begin_nested():
                    count = (await self.db.execute(text(sql), {"t": tenant_id, "s": symbol})).scalar() or 0
            except Exception:
                count = 0
            if count > 0:
                usage.append({"area": area, "count": int(count)})
        # Also count active conversions referencing this UoM
        conv_count = (await self.db.execute(
            select(func.count()).select_from(UoMConversion).where(
                UoMConversion.tenant_id == tenant_id,
                UoMConversion.is_active == True,
                ((UoMConversion.from_uom_id == uom_id) | (UoMConversion.to_uom_id == uom_id)),
            )
        )).scalar() or 0
        if conv_count > 0:
            usage.append({"area": "Conversiones", "count": int(conv_count)})
        return usage

    async def delete_uom(self, tenant_id: str, uom_id: str) -> tuple[bool, list[dict]]:
        uom = (await self.db.execute(
            select(UnitOfMeasure).where(UnitOfMeasure.tenant_id == tenant_id, UnitOfMeasure.id == uom_id)
        )).scalar_one_or_none()
        if not uom:
            return False, []
        usage = await self.get_uom_usage(tenant_id, uom_id)
        if usage:
            return False, usage
        uom.is_active = False
        await self.db.flush()
        return True, []

    async def delete_category(self, tenant_id: str, category: str) -> tuple[bool, list[dict]]:
        """Soft-delete every active UoM in a category plus its conversions.

        Returns (True, []) on success or (False, usage_breakdown) if any UoM
        in the category is currently in use. The usage breakdown lists each
        affected UoM and where it is referenced.
        """
        uoms_in_cat = (await self.db.execute(
            select(UnitOfMeasure).where(
                UnitOfMeasure.tenant_id == tenant_id,
                UnitOfMeasure.category == category,
                UnitOfMeasure.is_active == True,
            )
        )).scalars().all()
        if not uoms_in_cat:
            return False, []

        # Check usage for every UoM in the category. If any is in use,
        # collect a per-UoM breakdown and refuse to delete the category.
        blocking: list[dict] = []
        for u in uoms_in_cat:
            usage = await self.get_uom_usage(tenant_id, u.id)
            # Filter out "Conversiones" usage — those are internal to this category
            # and will be cleaned up below; they shouldn't block category deletion.
            usage = [x for x in usage if x.get("area") != "Conversiones"]
            if usage:
                blocking.append({
                    "uom": f"{u.name} ({u.symbol})",
                    "usage": usage,
                })
        if blocking:
            return False, blocking

        # Safe to soft-delete everything in the category
        uom_ids = [u.id for u in uoms_in_cat]
        for u in uoms_in_cat:
            u.is_active = False

        # Soft-delete every conversion that touches a UoM in this category
        convs = (await self.db.execute(
            select(UoMConversion).where(
                UoMConversion.tenant_id == tenant_id,
                UoMConversion.is_active == True,
                ((UoMConversion.from_uom_id.in_(uom_ids)) | (UoMConversion.to_uom_id.in_(uom_ids))),
            )
        )).scalars().all()
        for c in convs:
            c.is_active = False

        await self.db.flush()
        return True, []

    async def delete_conversion(self, tenant_id: str, conversion_id: str) -> bool:
        conv = (await self.db.execute(
            select(UoMConversion).where(
                UoMConversion.tenant_id == tenant_id, UoMConversion.id == conversion_id
            )
        )).scalar_one_or_none()
        if not conv:
            return False
        conv.is_active = False
        await self.db.flush()
        return True

    async def list_conversions(self, tenant_id: str) -> list[UoMConversion]:
        result = await self.db.execute(select(UoMConversion).where(UoMConversion.tenant_id == tenant_id, UoMConversion.is_active == True))
        return list(result.scalars().all())

    async def create_conversion(self, tenant_id: str, data: dict) -> UoMConversion:
        # SAVEPOINT so a UNIQUE violation doesn't poison the outer tx (CLAUDE.md #2).
        try:
            async with self.db.begin_nested():
                conv = UoMConversion(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
                self.db.add(conv)
                await self.db.flush()
        except IntegrityError:
            raise ConflictError("Ya existe una conversión entre estas unidades de medida")
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
