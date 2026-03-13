"""CSV report generation for inventory."""
from __future__ import annotations

import csv
import io
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Product, ProductType, StockLevel, StockMovement,
    Supplier, SupplierType, Warehouse,
    InventoryEvent, EventType, EventSeverity, EventStatus,
    EntitySerial, SerialStatus, EntityBatch,
    PurchaseOrder, PurchaseOrderLine,
    WarehouseLocation,
)
from app.db.models.events import EventImpact


class ReportsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── Products ────────────────────────────────────────────────────────────

    async def products_csv(self, tenant_id: str) -> str:
        result = await self.db.execute(
            select(Product)
            .where(Product.tenant_id == tenant_id)
            .options(
                selectinload(Product.product_type),
            )
            .order_by(Product.sku)
        )
        products = result.scalars().all()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "SKU", "Código de barras", "Nombre", "Descripción",
            "Tipo de producto", "Unidad",
            "Precio costo", "Precio venta", "Moneda", "Activo",
            "Rastreo por lotes",
            "Stock mínimo", "Punto de reorden", "Cant. reorden",
            "Método valorización",
            "Fecha creación", "Última actualización",
        ])
        for p in products:
            writer.writerow([
                p.sku,
                p.barcode or "",
                p.name,
                p.description or "",
                p.product_type.name if p.product_type else "",
                p.unit_of_measure,
                str(p.cost_price),
                str(p.sale_price),
                p.currency,
                "Sí" if p.is_active else "No",
                "Sí" if p.track_batches else "No",
                p.min_stock_level,
                p.reorder_point,
                p.reorder_quantity,
                p.valuation_method,
                p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "",
                p.updated_at.strftime("%Y-%m-%d %H:%M") if p.updated_at else "",
            ])
        return buf.getvalue()

    # ─── Stock ───────────────────────────────────────────────────────────────

    async def stock_csv(self, tenant_id: str) -> str:
        result = await self.db.execute(
            select(StockLevel)
            .where(StockLevel.tenant_id == tenant_id)
            .options(
                selectinload(StockLevel.product),
                selectinload(StockLevel.warehouse),
                selectinload(StockLevel.location),
                selectinload(StockLevel.batch),
            )
            .order_by(StockLevel.product_id)
        )
        levels = result.scalars().all()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "SKU", "Producto", "Bodega", "Ubicación", "Lote",
            "Qty en mano", "Qty reservada", "Qty en tránsito",
            "Punto de reorden", "Stock máximo",
            "Estado QC", "Costo promedio ponderado",
            "Último conteo", "Última actualización",
        ])
        for sl in levels:
            writer.writerow([
                sl.product.sku if sl.product else "",
                sl.product.name if sl.product else "",
                sl.warehouse.name if sl.warehouse else "",
                sl.location.name if sl.location else "",
                sl.batch.batch_number if sl.batch else "",
                str(sl.qty_on_hand),
                str(sl.qty_reserved),
                str(sl.qty_in_transit),
                sl.reorder_point,
                sl.max_stock if sl.max_stock >= 0 else "",
                sl.qc_status,
                str(sl.weighted_avg_cost) if sl.weighted_avg_cost is not None else "",
                sl.last_count_at.strftime("%Y-%m-%d %H:%M") if sl.last_count_at else "",
                sl.updated_at.strftime("%Y-%m-%d %H:%M") if sl.updated_at else "",
            ])
        return buf.getvalue()

    # ─── Suppliers ───────────────────────────────────────────────────────────

    async def suppliers_csv(self, tenant_id: str) -> str:
        result = await self.db.execute(
            select(Supplier)
            .where(Supplier.tenant_id == tenant_id)
            .options(selectinload(Supplier.supplier_type))
            .order_by(Supplier.name)
        )
        suppliers = result.scalars().all()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "Código", "Nombre", "Tipo", "Contacto", "Email", "Teléfono",
            "Dirección",
            "Términos de pago (días)", "Tiempo de entrega (días)",
            "Activo", "Notas",
            "Fecha creación", "Última actualización",
        ])
        for s in suppliers:
            addr = ""
            if s.address:
                parts = [
                    s.address.get("street", ""),
                    s.address.get("city", ""),
                    s.address.get("state", ""),
                    s.address.get("country", ""),
                    s.address.get("zip", ""),
                ]
                addr = ", ".join(p for p in parts if p)
            writer.writerow([
                s.code,
                s.name,
                s.supplier_type.name if s.supplier_type else "",
                s.contact_name or "",
                s.email or "",
                s.phone or "",
                addr,
                s.payment_terms_days,
                s.lead_time_days,
                "Sí" if s.is_active else "No",
                s.notes or "",
                s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
                s.updated_at.strftime("%Y-%m-%d %H:%M") if s.updated_at else "",
            ])
        return buf.getvalue()

    # ─── Movements ───────────────────────────────────────────────────────────

    async def movements_csv(
        self,
        tenant_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> str:
        q = (
            select(StockMovement)
            .where(StockMovement.tenant_id == tenant_id)
            .options(
                selectinload(StockMovement.product),
                selectinload(StockMovement.from_warehouse),
                selectinload(StockMovement.to_warehouse),
                selectinload(StockMovement.dynamic_movement_type),
            )
            .order_by(StockMovement.created_at.desc())
        )
        if date_from:
            q = q.where(StockMovement.created_at >= date_from)
        if date_to:
            q = q.where(StockMovement.created_at <= date_to)

        result = await self.db.execute(q)
        movements = result.scalars().all()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "Fecha", "Tipo", "Subtipo", "SKU", "Producto", "Cantidad",
            "Costo unitario", "Desde", "Hasta",
            "Referencia", "Lote", "Realizado por", "Notas",
        ])
        for m in movements:
            writer.writerow([
                m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else "",
                m.movement_type.value,
                m.dynamic_movement_type.name if m.dynamic_movement_type else "",
                m.product.sku if m.product else "",
                m.product.name if m.product else "",
                str(m.quantity),
                str(m.unit_cost) if m.unit_cost is not None else "",
                m.from_warehouse.name if m.from_warehouse else "",
                m.to_warehouse.name if m.to_warehouse else "",
                m.reference or "",
                m.batch_number or "",
                m.performed_by or "",
                m.notes or "",
            ])
        return buf.getvalue()

    # ─── Events ──────────────────────────────────────────────────────────────

    async def events_csv(
        self,
        tenant_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> str:
        q = (
            select(InventoryEvent)
            .where(InventoryEvent.tenant_id == tenant_id)
            .options(
                selectinload(InventoryEvent.event_type),
                selectinload(InventoryEvent.severity),
                selectinload(InventoryEvent.status),
                selectinload(InventoryEvent.warehouse),
                selectinload(InventoryEvent.impacts).selectinload(EventImpact.entity),
            )
            .order_by(InventoryEvent.occurred_at.desc())
        )
        if date_from:
            q = q.where(InventoryEvent.occurred_at >= date_from)
        if date_to:
            q = q.where(InventoryEvent.occurred_at <= date_to)

        result = await self.db.execute(q)
        events = result.scalars().all()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "Fecha ocurrencia", "Tipo", "Severidad", "Estado",
            "Título", "Descripción", "Bodega",
            "Productos afectados", "Impacto cantidad",
            "Reportado por", "Fecha resolución",
            "Fecha creación",
        ])
        for ev in events:
            affected = ", ".join(
                imp.entity.name for imp in (ev.impacts or []) if imp.entity
            )
            total_impact = sum(
                imp.quantity_impact for imp in (ev.impacts or [])
            )
            writer.writerow([
                ev.occurred_at.strftime("%Y-%m-%d %H:%M") if ev.occurred_at else "",
                ev.event_type.name if ev.event_type else "",
                ev.severity.name if ev.severity else "",
                ev.status.name if ev.status else "",
                ev.title,
                ev.description or "",
                ev.warehouse.name if ev.warehouse else "",
                affected,
                str(total_impact) if total_impact else "",
                ev.reported_by or "",
                ev.resolved_at.strftime("%Y-%m-%d %H:%M") if ev.resolved_at else "",
                ev.created_at.strftime("%Y-%m-%d %H:%M") if ev.created_at else "",
            ])
        return buf.getvalue()

    # ─── Serials ─────────────────────────────────────────────────────────────

    async def serials_csv(self, tenant_id: str) -> str:
        result = await self.db.execute(
            select(EntitySerial)
            .where(EntitySerial.tenant_id == tenant_id)
            .options(
                selectinload(EntitySerial.entity),
                selectinload(EntitySerial.status),
                selectinload(EntitySerial.warehouse),
                selectinload(EntitySerial.location),
                selectinload(EntitySerial.batch),
            )
            .order_by(EntitySerial.created_at.desc())
        )
        serials = result.scalars().all()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "Nro. serial", "SKU", "Producto", "Estado",
            "Bodega", "Ubicación", "Lote",
            "Notas", "Creado por",
            "Fecha creación", "Última actualización",
        ])
        for s in serials:
            writer.writerow([
                s.serial_number,
                s.entity.sku if s.entity else "",
                s.entity.name if s.entity else "",
                s.status.name if s.status else "",
                s.warehouse.name if s.warehouse else "",
                s.location.name if s.location else "",
                s.batch.batch_number if s.batch else "",
                s.notes or "",
                s.created_by or "",
                s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
                s.updated_at.strftime("%Y-%m-%d %H:%M") if s.updated_at else "",
            ])
        return buf.getvalue()

    # ─── Batches ─────────────────────────────────────────────────────────────

    async def batches_csv(self, tenant_id: str) -> str:
        result = await self.db.execute(
            select(EntityBatch)
            .where(EntityBatch.tenant_id == tenant_id)
            .options(selectinload(EntityBatch.entity))
            .order_by(EntityBatch.created_at.desc())
        )
        batches = result.scalars().all()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "Nro. lote", "SKU", "Producto", "Cantidad", "Costo",
            "Fecha fabricación", "Fecha expiración",
            "Activo", "Notas", "Creado por",
            "Fecha creación", "Última actualización",
        ])
        for b in batches:
            writer.writerow([
                b.batch_number,
                b.entity.sku if b.entity else "",
                b.entity.name if b.entity else "",
                str(b.quantity),
                str(b.cost) if b.cost is not None else "",
                b.manufacture_date.strftime("%Y-%m-%d") if b.manufacture_date else "",
                b.expiration_date.strftime("%Y-%m-%d") if b.expiration_date else "",
                "Sí" if b.is_active else "No",
                b.notes or "",
                b.created_by or "",
                b.created_at.strftime("%Y-%m-%d %H:%M") if b.created_at else "",
                b.updated_at.strftime("%Y-%m-%d %H:%M") if b.updated_at else "",
            ])
        return buf.getvalue()

    # ─── Purchase Orders ─────────────────────────────────────────────────────

    async def purchase_orders_csv(
        self,
        tenant_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> str:
        q = (
            select(PurchaseOrder)
            .where(PurchaseOrder.tenant_id == tenant_id)
            .options(
                selectinload(PurchaseOrder.supplier),
                selectinload(PurchaseOrder.order_type),
                selectinload(PurchaseOrder.lines).selectinload(PurchaseOrderLine.product),
            )
            .order_by(PurchaseOrder.created_at.desc())
        )
        if date_from:
            q = q.where(PurchaseOrder.created_at >= date_from)
        if date_to:
            q = q.where(PurchaseOrder.created_at <= date_to)

        result = await self.db.execute(q)
        orders = result.scalars().unique().all()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "Nro. orden", "Proveedor", "Estado", "Tipo de orden",
            "Fecha esperada", "Fecha recibido",
            "Líneas", "Total unidades pedidas", "Total unidades recibidas",
            "Total costo",
            "Notas", "Creado por",
            "Fecha creación", "Última actualización",
        ])
        for po in orders:
            total_ordered = sum(l.qty_ordered for l in po.lines)
            total_received = sum(l.qty_received for l in po.lines)
            total_cost = sum(l.line_total for l in po.lines)
            products = ", ".join(
                f"{l.product.name} x{l.qty_ordered}" for l in po.lines if l.product
            )
            writer.writerow([
                po.po_number,
                po.supplier.name if po.supplier else "",
                po.status.value,
                po.order_type.name if po.order_type else "",
                po.expected_date.strftime("%Y-%m-%d") if po.expected_date else "",
                po.received_date.strftime("%Y-%m-%d") if po.received_date else "",
                products,
                str(total_ordered),
                str(total_received),
                str(total_cost),
                po.notes or "",
                po.created_by or "",
                po.created_at.strftime("%Y-%m-%d %H:%M") if po.created_at else "",
                po.updated_at.strftime("%Y-%m-%d %H:%M") if po.updated_at else "",
            ])
        return buf.getvalue()
