"""Business logic for inventory events."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models import MovementType
from app.repositories.event_repo import InventoryEventRepository, EventTypeRepository
from app.repositories.movement_repo import MovementRepository
from app.repositories.stock_repo import StockRepository


class EventService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = InventoryEventRepository(db)
        self.et_repo = EventTypeRepository(db)
        self.movement_repo = MovementRepository(db)
        self.stock_repo = StockRepository(db)

    async def list(
        self,
        tenant_id: str,
        event_type_id: str | None = None,
        severity_id: str | None = None,
        status_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ):
        return await self.repo.list(tenant_id, event_type_id, severity_id, status_id, offset, limit)

    async def get(self, tenant_id: str, event_id: str):
        event = await self.repo.get(tenant_id, event_id)
        if not event:
            raise NotFoundError("Evento no encontrado")
        return event

    async def create(self, tenant_id: str, data: dict, impacts: list[dict] | None = None):
        # Validate event type exists
        et = await self.et_repo.get(tenant_id, data["event_type_id"])
        if not et:
            raise ValidationError("Tipo de evento no encontrado")

        event = await self.repo.create({
            "tenant_id": tenant_id,
            "event_type_id": data["event_type_id"],
            "severity_id": data["severity_id"],
            "status_id": data["status_id"],
            "warehouse_id": data.get("warehouse_id"),
            "title": data["title"],
            "description": data.get("description"),
            "occurred_at": data["occurred_at"],
            "reported_by": data.get("reported_by"),
            "metadata_": data.get("metadata", {}),
        })

        # Log initial status
        await self.repo.create_status_log({
            "event_id": event.id,
            "from_status_id": None,
            "to_status_id": data["status_id"],
            "changed_by": data.get("reported_by"),
            "notes": "Evento creado",
        })

        if impacts:
            for imp in impacts:
                movement_id = None
                # Auto-generate movement if event type has auto_generate_movement_type_id
                if et.auto_generate_movement_type_id and imp.get("quantity_impact"):
                    raw_impact = imp["quantity_impact"]
                    qty = abs(raw_impact)
                    if qty > 0:
                        wh_id = data.get("warehouse_id")
                        if wh_id:
                            # Preserve the sign: negative impact = deduct, positive = add
                            delta = -qty if raw_impact < 0 else qty
                            await self.stock_repo.upsert_level(
                                tenant_id, imp["entity_id"], wh_id, delta
                            )
                            movement_type = MovementType.adjustment_out if raw_impact < 0 else MovementType.adjustment_in
                            mov = await self.movement_repo.create({
                                "tenant_id": tenant_id,
                                "movement_type": movement_type,
                                "movement_type_id": et.auto_generate_movement_type_id,
                                "product_id": imp["entity_id"],
                                "from_warehouse_id": wh_id if raw_impact < 0 else None,
                                "to_warehouse_id": wh_id if raw_impact >= 0 else None,
                                "quantity": qty,
                                "notes": f"Auto-generado por evento: {data['title']}",
                                "performed_by": data.get("reported_by"),
                            })
                            movement_id = mov.id

                await self.repo.create_impact({
                    "event_id": event.id,
                    "entity_id": imp["entity_id"],
                    "quantity_impact": imp.get("quantity_impact", 0),
                    "batch_id": imp.get("batch_id"),
                    "serial_id": imp.get("serial_id"),
                    "movement_id": movement_id,
                    "notes": imp.get("notes"),
                })

        # Reload with impacts
        return await self.repo.get(tenant_id, event.id)

    async def change_status(
        self, tenant_id: str, event_id: str, status_id: str,
        notes: str | None = None, changed_by: str | None = None,
        resolved_at=None,
    ):
        event = await self.repo.get(tenant_id, event_id)
        if not event:
            raise NotFoundError("Evento no encontrado")

        from_status_id = event.status_id

        # Create status log entry
        await self.repo.create_status_log({
            "event_id": event_id,
            "from_status_id": from_status_id,
            "to_status_id": status_id,
            "changed_by": changed_by,
            "notes": notes,
        })

        update_data: dict = {"status_id": status_id, "updated_by": changed_by}
        if resolved_at:
            update_data["resolved_at"] = resolved_at
        return await self.repo.update(event, update_data)

    async def add_impact(self, tenant_id: str, event_id: str, impact_data: dict):
        event = await self.repo.get(tenant_id, event_id)
        if not event:
            raise NotFoundError("Evento no encontrado")
        return await self.repo.create_impact({
            "event_id": event_id,
            **impact_data,
        })
