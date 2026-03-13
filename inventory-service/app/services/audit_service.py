"""Service layer for inventory audit logging."""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_repo import InventoryAuditRepository


def _json_safe(obj: Any) -> Any:
    """Recursively convert non-JSON-serializable values (Decimal, UUID, etc.)."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (UUID, datetime.date, datetime.datetime)):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return str(obj)

# ── Human-readable descriptions ──────────────────────────────────────────────
# Maps action code → (base_text, field_to_extract_from_data)
# If field_to_extract_from_data is set, the value is appended: "Creó el producto «Leche»"

_ACTION_LABELS: dict[str, tuple[str, str | None]] = {
    # Products
    "inventory.product.create": ("Creó el producto", "name"),
    "inventory.product.update": ("Actualizó el producto", "name"),
    "inventory.product.delete": ("Eliminó un producto", None),
    # Warehouses
    "inventory.warehouse.create": ("Creó la bodega", "name"),
    "inventory.warehouse.update": ("Actualizó la bodega", "name"),
    "inventory.warehouse.delete": ("Eliminó una bodega", None),
    # Suppliers
    "inventory.supplier.create": ("Creó el proveedor", "name"),
    "inventory.supplier.update": ("Actualizó el proveedor", "name"),
    "inventory.supplier.delete": ("Eliminó un proveedor", None),
    # Stock movements
    "inventory.stock.receive": ("Registró entrada de stock", None),
    "inventory.stock.issue": ("Registró salida de stock", None),
    "inventory.stock.transfer": ("Transfirió stock entre bodegas", None),
    "inventory.stock.adjust": ("Ajustó inventario", None),
    "inventory.stock.adjust_in": ("Registró ajuste de entrada", None),
    "inventory.stock.adjust_out": ("Registró ajuste de salida", None),
    "inventory.stock.return": ("Registró devolución de stock", None),
    "inventory.stock.waste": ("Registró merma de stock", None),
    "inventory.stock.qc_approve": ("Aprobó QC de stock", None),
    "inventory.stock.qc_reject": ("Rechazó QC de stock", None),
    # Purchase orders
    "inventory.po.create": ("Creó orden de compra", "order_number"),
    "inventory.po.update": ("Actualizó orden de compra", "order_number"),
    "inventory.po.delete": ("Eliminó orden de compra", "order_number"),
    "inventory.po.send": ("Envió orden de compra al proveedor", "order_number"),
    "inventory.po.confirm": ("Confirmó orden de compra", "order_number"),
    "inventory.po.cancel": ("Canceló orden de compra", "order_number"),
    "inventory.po.receive": ("Recibió mercancía de orden de compra", "order_number"),
    # Production
    "inventory.production.create": ("Creó corrida de producción", None),
    "inventory.production.execute": ("Ejecutó corrida de producción", None),
    "inventory.production.finish": ("Finalizó corrida de producción", None),
    "inventory.production.approve": ("Aprobó corrida de producción", None),
    "inventory.production.reject": ("Rechazó corrida de producción", None),
    "inventory.production.delete": ("Eliminó corrida de producción", None),
    # Cycle counts
    "inventory.cycle_count.create": ("Creó conteo cíclico", None),
    "inventory.cycle_count.start": ("Inició conteo cíclico", None),
    "inventory.cycle_count.count": ("Registró conteo de artículo", None),
    "inventory.cycle_count.recount": ("Registró reconteo de artículo", None),
    "inventory.cycle_count.complete": ("Completó conteo cíclico", None),
    "inventory.cycle_count.approve": ("Aprobó conteo cíclico", None),
    "inventory.cycle_count.cancel": ("Canceló conteo cíclico", None),
    # Recipes
    "inventory.recipe.create": ("Creó la receta", "name"),
    "inventory.recipe.update": ("Actualizó la receta", "name"),
    "inventory.recipe.delete": ("Eliminó una receta", None),
    # Batches
    "inventory.batch.create": ("Creó el lote", "batch_number"),
    "inventory.batch.update": ("Actualizó el lote", "batch_number"),
    "inventory.batch.delete": ("Eliminó un lote", None),
    # Serials
    "inventory.serial.create": ("Creó el serial", "serial_number"),
    "inventory.serial.update": ("Actualizó el serial", "serial_number"),
    "inventory.serial.delete": ("Eliminó un serial", None),
    # Events
    "inventory.event.create": ("Creó evento de inventario", "title"),
    "inventory.event.update_status": ("Cambió estado de evento", None),
    "inventory.event.add_impact": ("Agregó impacto a evento", None),
    # Config — product types
    "inventory.config.product_type.create": ("Creó tipo de producto", "name"),
    "inventory.config.product_type.update": ("Actualizó tipo de producto", "name"),
    "inventory.config.product_type.delete": ("Eliminó tipo de producto", None),
    # Config — order types
    "inventory.config.order_type.create": ("Creó tipo de orden", "name"),
    "inventory.config.order_type.update": ("Actualizó tipo de orden", "name"),
    "inventory.config.order_type.delete": ("Eliminó tipo de orden", None),
    # Config — custom fields
    "inventory.config.custom_field.create": ("Creó campo personalizado", "name"),
    "inventory.config.custom_field.update": ("Actualizó campo personalizado", "name"),
    "inventory.config.custom_field.delete": ("Eliminó campo personalizado", None),
    # Config — supplier types
    "inventory.config.supplier_type.create": ("Creó tipo de proveedor", "name"),
    "inventory.config.supplier_type.update": ("Actualizó tipo de proveedor", "name"),
    "inventory.config.supplier_type.delete": ("Eliminó tipo de proveedor", None),
    # Config — supplier fields
    "inventory.config.supplier_field.create": ("Creó campo de proveedor", "name"),
    "inventory.config.supplier_field.update": ("Actualizó campo de proveedor", "name"),
    "inventory.config.supplier_field.delete": ("Eliminó campo de proveedor", None),
    # Config — movement types
    "inventory.config.movement_type.create": ("Creó tipo de movimiento", "name"),
    "inventory.config.movement_type.update": ("Actualizó tipo de movimiento", "name"),
    "inventory.config.movement_type.delete": ("Eliminó tipo de movimiento", None),
    # Config — warehouse types
    "inventory.config.warehouse_type.create": ("Creó tipo de bodega", "name"),
    "inventory.config.warehouse_type.update": ("Actualizó tipo de bodega", "name"),
    "inventory.config.warehouse_type.delete": ("Eliminó tipo de bodega", None),
    # Config — locations
    "inventory.config.location.create": ("Creó ubicación", "name"),
    "inventory.config.location.update": ("Actualizó ubicación", "name"),
    "inventory.config.location.delete": ("Eliminó ubicación", None),
    # Config — event types
    "inventory.config.event_type.create": ("Creó tipo de evento", "name"),
    "inventory.config.event_type.update": ("Actualizó tipo de evento", "name"),
    "inventory.config.event_type.delete": ("Eliminó tipo de evento", None),
    # Config — event severities
    "inventory.config.event_severity.create": ("Creó severidad de evento", "name"),
    "inventory.config.event_severity.update": ("Actualizó severidad de evento", "name"),
    "inventory.config.event_severity.delete": ("Eliminó severidad de evento", None),
    # Config — event statuses
    "inventory.config.event_status.create": ("Creó estado de evento", "name"),
    "inventory.config.event_status.update": ("Actualizó estado de evento", "name"),
    "inventory.config.event_status.delete": ("Eliminó estado de evento", None),
    # Config — serial statuses
    "inventory.config.serial_status.create": ("Creó estado de serial", "name"),
    "inventory.config.serial_status.update": ("Actualizó estado de serial", "name"),
    "inventory.config.serial_status.delete": ("Eliminó estado de serial", None),
    # Config — warehouse fields
    "inventory.config.warehouse_field.create": ("Creó campo de bodega", "name"),
    "inventory.config.warehouse_field.update": ("Actualizó campo de bodega", "name"),
    "inventory.config.warehouse_field.delete": ("Eliminó campo de bodega", None),
    # Config — movement fields
    "inventory.config.movement_field.create": ("Creó campo de movimiento", "name"),
    "inventory.config.movement_field.update": ("Actualizó campo de movimiento", "name"),
    "inventory.config.movement_field.delete": ("Eliminó campo de movimiento", None),
    # Sales orders
    "inventory.so.create": ("Creó orden de venta", "order_number"),
    "inventory.so.update": ("Actualizó orden de venta", "order_number"),
    "inventory.so.delete": ("Eliminó orden de venta", "order_number"),
    "inventory.so.confirm": ("Confirmó orden de venta", "order_number"),
    "inventory.so.pick": ("Inició picking de orden", "order_number"),
    "inventory.so.ship": ("Despachó orden de venta", "order_number"),
    "inventory.so.deliver": ("Entregó orden de venta", "order_number"),
    "inventory.so.return": ("Registró devolución de orden", "order_number"),
    "inventory.so.cancel": ("Canceló orden de venta", "order_number"),
    # Customers
    "inventory.customer.create": ("Creó el cliente", "name"),
    "inventory.customer.update": ("Actualizó el cliente", "name"),
    "inventory.customer.delete": ("Eliminó un cliente", None),
    "inventory.customer_type.create": ("Creó tipo de cliente", "name"),
    "inventory.customer_type.update": ("Actualizó tipo de cliente", "name"),
    "inventory.customer_type.delete": ("Eliminó tipo de cliente", None),
}


def _build_description(
    action: str,
    new_data: dict | None,
    old_data: dict | None,
) -> str:
    """Auto-generate a human-readable description from action code + data."""
    label_info = _ACTION_LABELS.get(action)
    if not label_info:
        return action

    base_text, name_field = label_info
    data = new_data or old_data or {}

    # Extract entity name
    entity_name: str | None = data.get(name_field) if name_field else None
    parts: list[str] = [f"{base_text} «{entity_name}»" if entity_name else base_text]

    # Enrich with contextual details
    extras: list[str] = []
    qty = data.get("quantity") or data.get("qty_ordered") or data.get("new_qty")
    if qty is not None:
        extras.append(f"{qty} uds")

    product_name = data.get("product_name")
    if product_name and name_field != "name":
        extras.append(f"de «{product_name}»")

    customer_name = data.get("customer_name")
    if customer_name:
        extras.append(f"para «{customer_name}»")

    warehouse_name = data.get("warehouse_name")
    from_wh = data.get("from_warehouse_name")
    to_wh = data.get("to_warehouse_name")
    if from_wh and to_wh:
        extras.append(f"de «{from_wh}» a «{to_wh}»")
    elif warehouse_name:
        extras.append(f"en «{warehouse_name}»")

    if extras:
        parts.append(" — " + ", ".join(extras))

    return "".join(parts)


class InventoryAuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = InventoryAuditRepository(db)

    async def log(
        self,
        *,
        tenant_id: str,
        user: dict,
        action: str,
        resource_type: str,
        resource_id: str,
        old_data: dict | None = None,
        new_data: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        user_id = str(user.get("id", user.get("sub", "")))
        user_email = user.get("email")
        user_name = user.get("full_name") or user.get("username") or user_email
        safe_old = _json_safe(old_data)
        safe_new = _json_safe(new_data)
        description = _build_description(action, safe_new, safe_old)

        await self.repo.create(
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            action=action,
            description=description,
            resource_type=resource_type,
            resource_id=str(resource_id),
            old_data=safe_old,
            new_data=safe_new,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def list(
        self,
        tenant_id: str,
        **filters,
    ):
        return await self.repo.list(tenant_id, **filters)

    async def entity_timeline(
        self,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        **kwargs,
    ):
        return await self.repo.entity_timeline(
            tenant_id, resource_type, resource_id, **kwargs
        )
