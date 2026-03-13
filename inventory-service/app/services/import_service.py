"""CSV import and demo seeding service."""

from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.batch_repo import BatchRepository
from app.repositories.config_repo import OrderTypeRepository, ProductTypeRepository, SupplierTypeRepository
from app.repositories.event_repo import (
    EventSeverityRepository, EventStatusRepository, EventTypeRepository, InventoryEventRepository,
)
from app.repositories.po_repo import PORepository
from app.repositories.product_repo import ProductRepository
from app.repositories.production_repo import ProductionRunRepository
from app.repositories.recipe_repo import RecipeRepository
from app.repositories.serial_repo import SerialRepository
from app.repositories.stock_repo import StockRepository
from app.repositories.supplier_repo import SupplierRepository
from app.repositories.warehouse_repo import WarehouseRepository
from app.services.demo_data import DEMO_DATA, SHARED_EVENT_CONFIG


class ImportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_repo = ProductRepository(db)
        self.warehouse_repo = WarehouseRepository(db)
        self.stock_repo = StockRepository(db)
        self.supplier_repo = SupplierRepository(db)
        self.product_type_repo = ProductTypeRepository(db)
        self.supplier_type_repo = SupplierTypeRepository(db)
        self.order_type_repo = OrderTypeRepository(db)
        self.batch_repo = BatchRepository(db)
        self.serial_repo = SerialRepository(db)
        self.recipe_repo = RecipeRepository(db)
        self.po_repo = PORepository(db)
        self.production_repo = ProductionRunRepository(db)
        self.event_type_repo = EventTypeRepository(db)
        self.event_sev_repo = EventSeverityRepository(db)
        self.event_status_repo = EventStatusRepository(db)
        self.event_repo = InventoryEventRepository(db)

    # ─── CSV Import ────────────────────────────────────────────────────────────

    async def import_products_csv(
        self,
        tenant_id: str,
        csv_content: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Parse CSV, create products and optionally set initial stock."""
        delimiter = self._detect_delimiter(csv_content)
        reader = csv.DictReader(io.StringIO(csv_content), delimiter=delimiter)

        if not reader.fieldnames:
            return {"created": 0, "skipped": 0, "errors": [{"row": 0, "field": "", "message": "CSV vacío o sin encabezados"}]}

        # Normalize headers
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]

        if "sku" not in reader.fieldnames or "name" not in reader.fieldnames:
            return {
                "created": 0,
                "skipped": 0,
                "errors": [{"row": 0, "field": "sku/name", "message": "Columnas requeridas: sku, name"}],
            }

        created = 0
        skipped = 0
        errors: list[dict[str, Any]] = []
        seen_skus: set[str] = set()

        for row_num, row in enumerate(reader, start=2):  # row 1 = header
            sku = (row.get("sku") or "").strip()
            name = (row.get("name") or "").strip()

            if not sku:
                errors.append({"row": row_num, "field": "sku", "message": "SKU vacío"})
                skipped += 1
                continue
            if not name:
                errors.append({"row": row_num, "field": "name", "message": "Nombre vacío"})
                skipped += 1
                continue

            # Duplicate in CSV
            if sku in seen_skus:
                errors.append({"row": row_num, "field": "sku", "message": f"SKU duplicado en CSV: {sku}"})
                skipped += 1
                continue
            seen_skus.add(sku)

            # Duplicate in DB
            existing = await self.product_repo.get_by_sku(sku, tenant_id)
            if existing:
                errors.append({"row": row_num, "field": "sku", "message": f"SKU ya existe en BD: {sku}"})
                skipped += 1
                continue

            # Parse optional fields
            cost_price = self._parse_decimal(row.get("cost_price"), Decimal("0"))
            sale_price = self._parse_decimal(row.get("sale_price"), Decimal("0"))
            min_stock = self._parse_int(row.get("min_stock_level"), 0)
            reorder_point = self._parse_int(row.get("reorder_point"), 0)

            product_data: dict[str, Any] = {
                "tenant_id": tenant_id,
                "sku": sku,
                "name": name,
                "barcode": (row.get("barcode") or "").strip() or None,
                "description": (row.get("description") or "").strip() or None,
                "unit_of_measure": (row.get("unit_of_measure") or "").strip() or "un",
                "cost_price": cost_price,
                "sale_price": sale_price,
                "currency": (row.get("currency") or "").strip() or "USD",
                "product_type_id": (row.get("product_type_id") or "").strip() or None,
                "min_stock_level": min_stock,
                "reorder_point": reorder_point,
                "created_by": user_id,
            }

            try:
                product = await self.product_repo.create(product_data)
            except Exception as exc:
                errors.append({"row": row_num, "field": "", "message": f"Error al crear producto: {exc}"})
                skipped += 1
                continue

            # Set initial stock if warehouse_id and initial_stock provided
            warehouse_id = (row.get("warehouse_id") or "").strip()
            initial_stock_str = (row.get("initial_stock") or "").strip()

            if warehouse_id and initial_stock_str:
                qty = self._parse_decimal(initial_stock_str, None)
                if qty is not None and qty > 0:
                    try:
                        await self.stock_repo.upsert_level(
                            tenant_id=tenant_id,
                            product_id=product.id,
                            warehouse_id=warehouse_id,
                            delta=qty,
                        )
                    except Exception as exc:
                        errors.append({
                            "row": row_num,
                            "field": "warehouse_id/initial_stock",
                            "message": f"Producto creado pero error al fijar stock: {exc}",
                        })

            created += 1

        return {"created": created, "skipped": skipped, "errors": errors}

    # ─── Templates ─────────────────────────────────────────────────────────────

    def generate_template(self, name: str) -> str:
        """Return a CSV template string with example rows."""
        headers = [
            "sku", "name", "barcode", "description", "unit_of_measure",
            "cost_price", "sale_price", "currency", "product_type_id",
            "warehouse_id", "initial_stock", "min_stock_level", "reorder_point",
        ]

        rows: list[list[str]] = []

        if name == "pet_food":
            rows = [
                ["MP-HPOLLO-001", "Harina de pollo", "", "Harina de subproducto avícola", "kg", "3.50", "0", "USD", "", "", "500", "100", "200"],
                ["PT-CROQC1K", "Croquetas Cachorro 1kg", "7701234567890", "Alimento premium cachorro", "un", "5.20", "8.90", "USD", "", "", "300", "50", "100"],
                ["EM-BOLSA1K", "Bolsas 1kg", "", "Empaque metalizado", "un", "0.15", "0", "USD", "", "", "2000", "500", "1000"],
            ]
        elif name == "technology":
            rows = [
                ["COMP-I513400", "Procesador Intel i5-13400", "0735858531238", "13th Gen 10 cores", "un", "189.00", "249.00", "USD", "", "", "25", "5", "10"],
                ["PERI-MON24", "Monitor 24\" FHD 75Hz", "0123456789012", "Panel IPS", "un", "120.00", "179.00", "USD", "", "", "10", "3", "5"],
                ["ACC-HDMI2M", "Cable HDMI 2m", "", "HDMI 2.1 alta velocidad", "un", "3.50", "8.00", "USD", "", "", "100", "20", "50"],
            ]
        elif name == "cleaning":
            rows = [
                ["LH-DETLIQ1L", "Detergente líquido 1L", "7709876543210", "Multiusos concentrado", "un", "1.80", "3.50", "USD", "", "", "200", "50", "100"],
                ["CP-GELANTI250", "Gel antibacterial 250ml", "", "70% alcohol", "un", "1.80", "4.20", "USD", "", "", "80", "20", "40"],
                ["IND-DESENG5L", "Desengrasante industrial 5L", "", "Para cocinas industriales", "un", "8.00", "15.00", "USD", "", "", "40", "10", "20"],
            ]
        else:
            # basic template — empty example rows
            rows = [
                ["SKU-001", "Producto ejemplo", "7700000000000", "Descripción", "un", "10.00", "25.00", "USD", "", "", "100", "10", "20"],
            ]

        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(headers)
        for r in rows:
            writer.writerow(r)
        return out.getvalue()

    # ─── Demo Seeding ──────────────────────────────────────────────────────────

    async def seed_demo(
        self,
        tenant_id: str,
        industry: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Seed/restore demo data for one industry.

        Idempotent: re-running restores soft-deleted entities and creates
        any missing ones without duplicating existing active data.
        """
        now = datetime.now(timezone.utc)

        data = DEMO_DATA.get(industry)
        if not data:
            return {"industry": industry, "error": f"Industria desconocida: {industry}"}

        counts: dict[str, int] = {
            "types_created": 0, "types_restored": 0,
            "warehouses_created": 0, "warehouses_restored": 0,
            "suppliers_created": 0, "suppliers_restored": 0,
            "products_created": 0, "products_restored": 0,
            "supplier_types_created": 0, "supplier_types_restored": 0,
            "order_types_created": 0, "order_types_restored": 0,
            "batches_created": 0,
            "serials_created": 0,
            "recipes_created": 0, "recipes_restored": 0,
            "pos_created": 0,
            "production_runs_created": 0,
            "event_config_created": 0,
            "events_created": 0,
        }

        # 1. Product types
        type_map: dict[str, str] = {}
        for pt in data["product_types"]:
            existing = await self._find_product_type_by_name(tenant_id, pt["name"])
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    await self.db.flush()
                    counts["types_restored"] += 1
                type_map[pt["name"]] = existing.id
            else:
                try:
                    obj = await self.product_type_repo.create(tenant_id, {
                        "name": pt["name"],
                        "slug": self._slugify(pt["name"]),
                        "color": pt.get("color"),
                        "created_by": user_id,
                    })
                    type_map[pt["name"]] = obj.id
                    counts["types_created"] += 1
                except Exception:
                    await self.db.rollback()
                    existing = await self._find_product_type_by_name(tenant_id, pt["name"])
                    if existing:
                        type_map[pt["name"]] = existing.id

        # 2. Supplier types
        sup_type_map: dict[str, str] = {}
        for st in data.get("supplier_types", []):
            existing = await self._find_by_name(tenant_id, "SupplierType", st["name"])
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    await self.db.flush()
                    counts["supplier_types_restored"] += 1
                sup_type_map[st["name"]] = existing.id
            else:
                try:
                    obj = await self.supplier_type_repo.create(tenant_id, {
                        "name": st["name"],
                        "slug": self._slugify(st["name"]),
                        "color": st.get("color"),
                        "created_by": user_id,
                    })
                    sup_type_map[st["name"]] = obj.id
                    counts["supplier_types_created"] += 1
                except Exception:
                    await self.db.rollback()
                    existing = await self._find_by_name(tenant_id, "SupplierType", st["name"])
                    if existing:
                        sup_type_map[st["name"]] = existing.id

        # 3. Order types
        order_type_map: dict[str, str] = {}
        for ot in data.get("order_types", []):
            existing = await self._find_by_name(tenant_id, "OrderType", ot["name"])
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    await self.db.flush()
                    counts["order_types_restored"] += 1
                order_type_map[ot["name"]] = existing.id
            else:
                try:
                    obj = await self.order_type_repo.create(tenant_id, {
                        "name": ot["name"],
                        "slug": self._slugify(ot["name"]),
                        "color": ot.get("color"),
                        "created_by": user_id,
                    })
                    order_type_map[ot["name"]] = obj.id
                    counts["order_types_created"] += 1
                except Exception:
                    await self.db.rollback()
                    existing = await self._find_by_name(tenant_id, "OrderType", ot["name"])
                    if existing:
                        order_type_map[ot["name"]] = existing.id

        # 4. Warehouses
        wh_map: dict[str, str] = {}
        for wh in data["warehouses"]:
            existing = await self.warehouse_repo.get_by_code(wh["code"], tenant_id)
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    await self.db.flush()
                    counts["warehouses_restored"] += 1
                wh_map[wh["code"]] = existing.id
            else:
                try:
                    obj = await self.warehouse_repo.create({
                        "tenant_id": tenant_id,
                        "name": wh["name"],
                        "code": wh["code"],
                        "type": wh.get("type", "main"),
                        "created_by": user_id,
                    })
                    wh_map[wh["code"]] = obj.id
                    counts["warehouses_created"] += 1
                except Exception:
                    await self.db.rollback()
                    existing = await self.warehouse_repo.get_by_code(wh["code"], tenant_id)
                    if existing:
                        wh_map[wh["code"]] = existing.id

        # 5. Suppliers (with supplier_type_id + extra fields)
        supplier_map: dict[str, str] = {}
        for sup in data["suppliers"]:
            existing = await self.supplier_repo.get_by_code(sup["code"], tenant_id)
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    await self.db.flush()
                    counts["suppliers_restored"] += 1
                supplier_map[sup["code"]] = existing.id
            else:
                sup_data: dict[str, Any] = {
                    "tenant_id": tenant_id,
                    "name": sup["name"],
                    "code": sup["code"],
                    "created_by": user_id,
                }
                # Optional fields from demo data
                if sup.get("type"):
                    sup_data["supplier_type_id"] = sup_type_map.get(sup["type"])
                if sup.get("contact"):
                    sup_data["contact_name"] = sup["contact"]
                if sup.get("email"):
                    sup_data["email"] = sup["email"]
                if sup.get("phone"):
                    sup_data["phone"] = sup["phone"]
                if sup.get("lead_time"):
                    sup_data["lead_time_days"] = sup["lead_time"]
                try:
                    obj = await self.supplier_repo.create(sup_data)
                    supplier_map[sup["code"]] = obj.id
                    counts["suppliers_created"] += 1
                except Exception:
                    await self.db.rollback()
                    existing = await self.supplier_repo.get_by_code(sup["code"], tenant_id)
                    if existing:
                        supplier_map[sup["code"]] = existing.id

        # 6. Products — build product_map (sku → id) for later use
        product_map: dict[str, str] = {}
        for p in data["products"]:
            sku = p["sku"]
            wh_code = p.get("wh", "")
            wh_id = wh_map.get(wh_code)
            stock_qty = p.get("stock", 0)

            existing = await self.product_repo.get_by_sku(sku, tenant_id)

            if existing and existing.is_active:
                product_map[sku] = existing.id
                continue

            if existing and not existing.is_active:
                existing.is_active = True
                await self.db.flush()
                counts["products_restored"] += 1
                product_map[sku] = existing.id
                if wh_id and stock_qty > 0:
                    await self._set_stock_absolute(tenant_id, existing.id, wh_id, stock_qty, now)
                continue

            # Create fresh
            product_type_id = type_map.get(p.get("type", ""))
            product_data: dict[str, Any] = {
                "tenant_id": tenant_id,
                "sku": sku,
                "name": p["name"],
                "unit_of_measure": p.get("unit", "un"),
                "cost_price": Decimal(str(p.get("cost", 0))),
                "sale_price": Decimal(str(p.get("sale", 0))),
                "product_type_id": product_type_id,
                "reorder_point": int(stock_qty * 0.2),
                "created_by": user_id,
            }
            try:
                product = await self.product_repo.create(product_data)
                counts["products_created"] += 1
                product_map[sku] = product.id
            except Exception:
                await self.db.rollback()
                continue

            if wh_id and stock_qty > 0:
                try:
                    await self.stock_repo.upsert_level(
                        tenant_id=tenant_id,
                        product_id=product.id,
                        warehouse_id=wh_id,
                        delta=Decimal(str(stock_qty)),
                    )
                except Exception:
                    pass

        # 7. Batches — idempotent by (entity_id, batch_number)
        for b in data.get("batches", []):
            entity_id = product_map.get(b["sku"])
            if not entity_id:
                continue
            existing = await self._find_batch(tenant_id, entity_id, b["batch"])
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    await self.db.flush()
                continue
            try:
                await self.batch_repo.create(tenant_id, {
                    "entity_id": entity_id,
                    "batch_number": b["batch"],
                    "manufacture_date": self._parse_date(b.get("mfg")),
                    "expiration_date": self._parse_date(b.get("exp")),
                    "quantity": Decimal(str(b.get("qty", 0))),
                    "created_by": user_id,
                })
                counts["batches_created"] += 1
            except Exception:
                await self.db.rollback()

        # 8. Serials — need a "Disponible" serial status
        serial_status_id: str | None = None
        if data.get("serials"):
            serial_status_id = await self._ensure_serial_status(tenant_id)

        for s in data.get("serials", []):
            entity_id = product_map.get(s["sku"])
            if not entity_id or not serial_status_id:
                continue
            # Resolve warehouse from product's warehouse
            prod_def = next((p for p in data["products"] if p["sku"] == s["sku"]), None)
            serial_wh_id = wh_map.get(prod_def["wh"]) if prod_def and prod_def.get("wh") else None
            for sn in s.get("numbers", []):
                existing = await self._find_serial(tenant_id, entity_id, sn)
                if existing:
                    continue
                try:
                    await self.serial_repo.create(tenant_id, {
                        "entity_id": entity_id,
                        "serial_number": sn,
                        "status_id": serial_status_id,
                        "warehouse_id": serial_wh_id,
                        "created_by": user_id,
                    })
                    counts["serials_created"] += 1
                except Exception:
                    await self.db.rollback()

        # 9. Recipes — idempotent by name
        for r in data.get("recipes", []):
            output_id = product_map.get(r["output_sku"])
            if not output_id:
                continue
            existing = await self._find_recipe_by_name(tenant_id, r["name"])
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    await self.db.flush()
                    counts["recipes_restored"] += 1
                continue
            components: list[dict[str, Any]] = []
            skip_recipe = False
            for comp in r.get("components", []):
                comp_id = product_map.get(comp["sku"])
                if not comp_id:
                    skip_recipe = True
                    break
                components.append({
                    "component_entity_id": comp_id,
                    "quantity_required": Decimal(str(comp["qty"])),
                })
            if skip_recipe:
                continue
            try:
                await self.recipe_repo.create(tenant_id, {
                    "name": r["name"],
                    "output_entity_id": output_id,
                    "output_quantity": Decimal(str(r.get("output_qty", 1))),
                    "created_by": user_id,
                }, components)
                counts["recipes_created"] += 1
            except Exception:
                await self.db.rollback()

        # 10. Purchase Orders — idempotent by notes (unique demo fingerprint)
        for po in data.get("purchase_orders", []):
            supplier_id = supplier_map.get(po["supplier_code"])
            wh_id = wh_map.get(po.get("wh_code", ""))
            if not supplier_id:
                continue
            # Check if PO with same notes already exists
            po_notes = po.get("notes", "")
            if po_notes:
                existing_po = await self._find_po_by_notes(tenant_id, po_notes)
                if existing_po:
                    continue
            # Build lines
            lines: list[dict[str, Any]] = []
            skip_po = False
            for line in po.get("lines", []):
                prod_id = product_map.get(line["sku"])
                if not prod_id:
                    skip_po = True
                    break
                qty = Decimal(str(line["qty"]))
                cost = Decimal(str(line["cost"]))
                qty_received = qty if po.get("status") == "received" else Decimal("0")
                lines.append({
                    "product_id": prod_id,
                    "qty_ordered": qty,
                    "qty_received": qty_received,
                    "unit_cost": cost,
                    "line_total": qty * cost,
                })
            if skip_po:
                continue
            try:
                po_number = await self.po_repo.next_po_number(tenant_id)
                # Pick the first order type if available
                ot_id = next(iter(order_type_map.values()), None) if order_type_map else None
                await self.po_repo.create({
                    "tenant_id": tenant_id,
                    "po_number": po_number,
                    "supplier_id": supplier_id,
                    "status": po.get("status", "draft"),
                    "warehouse_id": wh_id,
                    "order_type_id": ot_id,
                    "notes": po_notes,
                    "created_by": user_id,
                    "lines": lines,
                })
                counts["pos_created"] += 1
            except Exception:
                await self.db.rollback()

        # 11. Production runs — idempotent by notes fingerprint
        recipe_name_map: dict[str, str] = {}
        # Build recipe name→id map from what was just created or already exists
        for r in data.get("recipes", []):
            existing = await self._find_recipe_by_name(tenant_id, r["name"])
            if existing:
                recipe_name_map[r["name"]] = existing.id
        for pr in data.get("production_runs", []):
            recipe_id = recipe_name_map.get(pr["recipe_name"])
            wh_id = wh_map.get(pr.get("wh_code", ""))
            if not recipe_id or not wh_id:
                continue
            run_notes = f"Demo: {pr['recipe_name']}"
            existing_run = await self._find_production_run_by_notes(tenant_id, run_notes)
            if existing_run:
                continue
            try:
                run_number = await self.production_repo.next_run_number(tenant_id)
                await self.production_repo.create({
                    "tenant_id": tenant_id,
                    "recipe_id": recipe_id,
                    "warehouse_id": wh_id,
                    "run_number": run_number,
                    "multiplier": Decimal(str(pr.get("multiplier", 1))),
                    "notes": run_notes,
                })
                counts["production_runs_created"] += 1
            except Exception:
                await self.db.rollback()

        # 12. Event config (shared across industries, idempotent by slug)
        evt_type_map, evt_sev_map, evt_status_map = await self._ensure_event_config(
            tenant_id, user_id, counts,
        )

        # 13. Events with impacts
        for ev in data.get("events", []):
            et_id = evt_type_map.get(ev["event_type_slug"])
            sev_id = evt_sev_map.get(ev["severity_slug"])
            st_id = evt_status_map.get(ev["status_slug"])
            ev_wh_id = wh_map.get(ev.get("wh_code", ""))
            if not et_id or not sev_id or not st_id:
                continue
            # Check if event with same title already exists to avoid duplicates
            existing = await self._find_event_by_title(tenant_id, ev["title"])
            if existing:
                continue
            try:
                event_obj = await self.event_repo.create({
                    "tenant_id": tenant_id,
                    "event_type_id": et_id,
                    "severity_id": sev_id,
                    "status_id": st_id,
                    "warehouse_id": ev_wh_id,
                    "title": ev["title"],
                    "description": ev.get("description"),
                    "occurred_at": now,
                    "reported_by": user_id,
                })
                for imp in ev.get("impacts", []):
                    entity_id = product_map.get(imp["sku"])
                    if entity_id:
                        await self.event_repo.create_impact({
                            "event_id": event_obj.id,
                            "entity_id": entity_id,
                            "quantity_impact": Decimal(str(imp.get("qty", 0))),
                        })
                counts["events_created"] += 1
            except Exception:
                await self.db.rollback()

        return {
            "industry": industry,
            "label": data.get("label", industry),
            **counts,
        }

    async def delete_demo(
        self,
        tenant_id: str,
        industry: str,
    ) -> dict[str, Any]:
        """Delete demo data for one industry using SKUs/codes/names from DEMO_DATA.

        Uses raw SQL DELETE to bypass ORM relationship handling and let
        PostgreSQL ON DELETE CASCADE work directly.

        Order respects FK constraints:
        1. Production runs (RESTRICT on warehouse)
        2. Events by title (CASCADE deletes impacts)
        3. Purchase orders by notes (CASCADE deletes lines → unblocks product RESTRICT)
        4. Recipes by name (CASCADE deletes components → unblocks product RESTRICT)
        5. Products by SKU (DB CASCADE: stock_levels, stock_movements, batches,
           serials, stock_layers, event_impacts)
        6. Suppliers by code
        7. Warehouses by code (DB CASCADE: locations)
        8. Config types by name (supplier, order, product)

        Event config (types, severities, statuses) is shared → NOT deleted.
        """
        from app.db.models import (
            EntityRecipe, InventoryEvent,
            Product, ProductionRun, PurchaseOrder,
            Supplier, Warehouse,
        )
        from app.db.models.config import OrderType, ProductType, SupplierType

        data = DEMO_DATA.get(industry)
        if not data:
            return {"industry": industry, "error": f"Industria desconocida: {industry}"}

        counts: dict[str, int] = {
            "products_deleted": 0,
            "warehouses_deleted": 0,
            "suppliers_deleted": 0,
            "types_deleted": 0,
            "supplier_types_deleted": 0,
            "order_types_deleted": 0,
            "recipes_deleted": 0,
            "pos_deleted": 0,
            "production_runs_deleted": 0,
            "events_deleted": 0,
            "batches_deleted": 0,
            "serials_deleted": 0,
        }

        # Collect identifiers from demo data
        product_skus = [p["sku"] for p in data.get("products", [])]
        warehouse_codes = [w["code"] for w in data.get("warehouses", [])]
        supplier_codes = [s["code"] for s in data.get("suppliers", [])]
        recipe_names = [r["name"] for r in data.get("recipes", [])]
        production_run_notes = [f"Demo: {pr['recipe_name']}" for pr in data.get("production_runs", [])]
        event_titles = [e["title"] for e in data.get("events", [])]
        po_notes_list = [po.get("notes", "") for po in data.get("purchase_orders", []) if po.get("notes")]
        product_type_names = [pt["name"] for pt in data.get("product_types", [])]
        supplier_type_names = [st["name"] for st in data.get("supplier_types", [])]
        order_type_names = [ot["name"] for ot in data.get("order_types", [])]

        # Resolve product IDs (needed for counting cascaded children)
        product_ids: list[str] = []
        if product_skus:
            for sku in product_skus:
                result = await self.db.execute(
                    select(Product.id).where(
                        Product.tenant_id == tenant_id,
                        Product.sku == sku,
                    )
                )
                pid = result.scalar_one_or_none()
                if pid:
                    product_ids.append(pid)

        # Helper: resolve IDs by column match, then bulk SQL DELETE
        async def _bulk_delete(model, filters, count_key: str) -> None:
            result = await self.db.execute(delete(model).where(*filters))
            counts[count_key] += result.rowcount

        # 1. Production runs by notes
        if production_run_notes:
            await _bulk_delete(
                ProductionRun,
                [ProductionRun.tenant_id == tenant_id, ProductionRun.notes.in_(production_run_notes)],
                "production_runs_deleted",
            )

        # 2. Events by title (DB CASCADE deletes impacts)
        if event_titles:
            await _bulk_delete(
                InventoryEvent,
                [InventoryEvent.tenant_id == tenant_id, InventoryEvent.title.in_(event_titles)],
                "events_deleted",
            )

        # 3. Purchase orders by notes (DB CASCADE deletes lines)
        if po_notes_list:
            await _bulk_delete(
                PurchaseOrder,
                [PurchaseOrder.tenant_id == tenant_id, PurchaseOrder.notes.in_(po_notes_list)],
                "pos_deleted",
            )

        # 4. Recipes by name (DB CASCADE deletes components)
        if recipe_names:
            await _bulk_delete(
                EntityRecipe,
                [EntityRecipe.tenant_id == tenant_id, EntityRecipe.name.in_(recipe_names)],
                "recipes_deleted",
            )

        # 5. Products by SKU (DB CASCADE: stock_levels, stock_movements, batches,
        #    serials, stock_layers, event_impacts)
        if product_skus:
            # Count cascaded children before deleting
            from app.db.models import EntityBatch, EntitySerial
            if product_ids:
                for count_model, count_key in [
                    (EntitySerial, "serials_deleted"),
                    (EntityBatch, "batches_deleted"),
                ]:
                    result = await self.db.execute(
                        select(func.count()).where(
                            count_model.tenant_id == tenant_id,
                            count_model.entity_id.in_(product_ids),
                        )
                    )
                    counts[count_key] = result.scalar_one()

            await _bulk_delete(
                Product,
                [Product.tenant_id == tenant_id, Product.sku.in_(product_skus)],
                "products_deleted",
            )

        # 6. Suppliers by code
        if supplier_codes:
            await _bulk_delete(
                Supplier,
                [Supplier.tenant_id == tenant_id, Supplier.code.in_(supplier_codes)],
                "suppliers_deleted",
            )

        # 7. Warehouses by code (DB CASCADE: locations, remaining stock_levels)
        if warehouse_codes:
            await _bulk_delete(
                Warehouse,
                [Warehouse.tenant_id == tenant_id, Warehouse.code.in_(warehouse_codes)],
                "warehouses_deleted",
            )

        # 8. Config types by name
        if supplier_type_names:
            await _bulk_delete(
                SupplierType,
                [SupplierType.tenant_id == tenant_id, SupplierType.name.in_(supplier_type_names)],
                "supplier_types_deleted",
            )
        if order_type_names:
            await _bulk_delete(
                OrderType,
                [OrderType.tenant_id == tenant_id, OrderType.name.in_(order_type_names)],
                "order_types_deleted",
            )
        if product_type_names:
            await _bulk_delete(
                ProductType,
                [ProductType.tenant_id == tenant_id, ProductType.name.in_(product_type_names)],
                "types_deleted",
            )

        return {
            "industry": industry,
            "label": data.get("label", industry),
            **counts,
        }

    async def seed_all_demos(
        self,
        tenant_id: str,
        user_id: str,
    ) -> list[dict[str, Any]]:
        """Seed all 3 industries."""
        results = []
        for industry in ["pet_food", "technology", "cleaning"]:
            result = await self.seed_demo(tenant_id, industry, user_id)
            results.append(result)
        return results

    # ─── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _slugify(name: str) -> str:
        """Generate a URL-safe slug from a name."""
        slug = name.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_-]+", "-", slug)
        return slug[:150]

    @staticmethod
    def _detect_delimiter(text: str) -> str:
        """Auto-detect CSV delimiter."""
        first_line = text.split("\n", 1)[0]
        for delim in [",", ";", "\t"]:
            if delim in first_line:
                return delim
        return ","

    @staticmethod
    def _parse_decimal(value: str | None, default: Decimal | None) -> Decimal | None:
        if not value or not value.strip():
            return default
        try:
            return Decimal(value.strip())
        except (InvalidOperation, ValueError):
            return default

    @staticmethod
    def _parse_int(value: str | None, default: int) -> int:
        if not value or not value.strip():
            return default
        try:
            return int(float(value.strip()))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        """Parse YYYY-MM-DD string to date."""
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except (ValueError, TypeError):
            return None

    async def _set_stock_absolute(
        self, tenant_id: str, product_id: str, warehouse_id: str, qty: int, now: datetime,
    ) -> None:
        """Set stock to an absolute target value (for demo restore)."""
        target = Decimal(str(qty))
        level = await self.stock_repo.get_level(product_id, warehouse_id)
        if level:
            level.qty_on_hand = target
            level.updated_at = now
            await self.db.flush()
        else:
            await self.stock_repo.upsert_level(
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                delta=target,
            )

    async def _find_product_type_by_name(self, tenant_id: str, name: str):
        """Find a product type by name."""
        from app.db.models.config import ProductType
        stmt = select(ProductType).where(
            ProductType.tenant_id == tenant_id,
            ProductType.name == name,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_by_name(self, tenant_id: str, model_name: str, name: str):
        """Find a config entity (SupplierType, OrderType) by name."""
        from app.db.models.config import OrderType, SupplierType
        model_cls = {"SupplierType": SupplierType, "OrderType": OrderType}[model_name]
        stmt = select(model_cls).where(
            model_cls.tenant_id == tenant_id,
            model_cls.name == name,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_batch(self, tenant_id: str, entity_id: str, batch_number: str):
        """Find a batch by (entity_id, batch_number)."""
        from app.db.models import EntityBatch
        stmt = select(EntityBatch).where(
            EntityBatch.tenant_id == tenant_id,
            EntityBatch.entity_id == entity_id,
            EntityBatch.batch_number == batch_number,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_serial(self, tenant_id: str, entity_id: str, serial_number: str):
        """Find a serial by (entity_id, serial_number)."""
        from app.db.models import EntitySerial
        stmt = select(EntitySerial).where(
            EntitySerial.tenant_id == tenant_id,
            EntitySerial.entity_id == entity_id,
            EntitySerial.serial_number == serial_number,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_recipe_by_name(self, tenant_id: str, name: str):
        """Find a recipe by name."""
        from app.db.models import EntityRecipe
        stmt = select(EntityRecipe).where(
            EntityRecipe.tenant_id == tenant_id,
            EntityRecipe.name == name,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _ensure_serial_status(self, tenant_id: str) -> str:
        """Ensure a 'Disponible' serial status exists, return its ID."""
        from app.db.models import SerialStatus
        slug = "disponible"
        stmt = select(SerialStatus).where(
            SerialStatus.tenant_id == tenant_id,
            SerialStatus.slug == slug,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing.id
        status_id = str(uuid.uuid4())
        obj = SerialStatus(
            id=status_id,
            tenant_id=tenant_id,
            name="Disponible",
            slug=slug,
            description="Serial disponible en inventario",
            color="#10b981",
        )
        self.db.add(obj)
        await self.db.flush()
        return status_id

    async def _ensure_event_config(
        self, tenant_id: str, user_id: str, counts: dict[str, int],
    ) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
        """Ensure shared event types, severities, statuses exist. Returns slug→id maps."""
        from app.db.models import EventSeverity, EventStatus, EventType

        evt_type_map: dict[str, str] = {}
        for et in SHARED_EVENT_CONFIG["event_types"]:
            existing = await self._find_by_slug(tenant_id, EventType, et["slug"])
            if existing:
                evt_type_map[et["slug"]] = existing.id
            else:
                try:
                    obj = await self.event_type_repo.create(tenant_id, {
                        "name": et["name"], "slug": et["slug"],
                        "color": et.get("color"), "icon": et.get("icon"),
                    })
                    evt_type_map[et["slug"]] = obj.id
                    counts["event_config_created"] += 1
                except Exception:
                    await self.db.rollback()
                    existing = await self._find_by_slug(tenant_id, EventType, et["slug"])
                    if existing:
                        evt_type_map[et["slug"]] = existing.id

        evt_sev_map: dict[str, str] = {}
        for sv in SHARED_EVENT_CONFIG["event_severities"]:
            existing = await self._find_by_slug(tenant_id, EventSeverity, sv["slug"])
            if existing:
                evt_sev_map[sv["slug"]] = existing.id
            else:
                try:
                    obj = await self.event_sev_repo.create(tenant_id, {
                        "name": sv["name"], "slug": sv["slug"],
                        "weight": sv.get("weight", 1), "color": sv.get("color"),
                    })
                    evt_sev_map[sv["slug"]] = obj.id
                    counts["event_config_created"] += 1
                except Exception:
                    await self.db.rollback()
                    existing = await self._find_by_slug(tenant_id, EventSeverity, sv["slug"])
                    if existing:
                        evt_sev_map[sv["slug"]] = existing.id

        evt_status_map: dict[str, str] = {}
        for st in SHARED_EVENT_CONFIG["event_statuses"]:
            existing = await self._find_by_slug(tenant_id, EventStatus, st["slug"])
            if existing:
                evt_status_map[st["slug"]] = existing.id
            else:
                try:
                    obj = await self.event_status_repo.create(tenant_id, {
                        "name": st["name"], "slug": st["slug"],
                        "is_final": st.get("is_final", False),
                        "color": st.get("color"), "sort_order": st.get("sort_order", 0),
                    })
                    evt_status_map[st["slug"]] = obj.id
                    counts["event_config_created"] += 1
                except Exception:
                    await self.db.rollback()
                    existing = await self._find_by_slug(tenant_id, EventStatus, st["slug"])
                    if existing:
                        evt_status_map[st["slug"]] = existing.id

        return evt_type_map, evt_sev_map, evt_status_map

    async def _find_by_slug(self, tenant_id: str, model_cls: type, slug: str):
        """Generic find-by-slug for any model with tenant_id + slug."""
        stmt = select(model_cls).where(
            model_cls.tenant_id == tenant_id,
            model_cls.slug == slug,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_po_by_notes(self, tenant_id: str, notes: str):
        """Find a purchase order by notes (demo fingerprint)."""
        from app.db.models import PurchaseOrder
        stmt = select(PurchaseOrder).where(
            PurchaseOrder.tenant_id == tenant_id,
            PurchaseOrder.notes == notes,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def _find_production_run_by_notes(self, tenant_id: str, notes: str):
        """Find a production run by notes (demo fingerprint)."""
        from app.db.models import ProductionRun
        stmt = select(ProductionRun).where(
            ProductionRun.tenant_id == tenant_id,
            ProductionRun.notes == notes,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def _find_event_by_title(self, tenant_id: str, title: str):
        """Find an event by title to avoid duplicates."""
        from app.db.models import InventoryEvent
        stmt = select(InventoryEvent).where(
            InventoryEvent.tenant_id == tenant_id,
            InventoryEvent.title == title,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

