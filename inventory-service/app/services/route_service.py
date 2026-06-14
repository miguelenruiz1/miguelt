"""WM route service: generate multi-step routes from the warehouse step config
and produce the chained movement orders for a flow (pick → pack → out)."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models import Route, RouteRule, WMWarehouseConfig
from app.domain.schemas.wm_route import GenerateChainIn
from app.domain.schemas.wm_transfer import MovementOrderCreate, MovementOrderLineCreate
from app.services.movement_order_service import MovementOrderService

# Fixed presets per (flow, steps) — each tuple is (step_name, source_zone, dest_zone, operation_code).
# "STOCK" is the general warehouse stock (no interim bin); the rest are interim zones.
ROUTE_PRESETS: dict[tuple[str, int], list[tuple[str, str, str, str]]] = {
    ("inbound", 1): [("recepción", "GR-ZONE", "STOCK", "101")],
    ("inbound", 2): [("recepción", "GR-ZONE", "QA-ZONE", "101"),
                     ("almacenaje", "QA-ZONE", "STOCK", "101")],
    ("inbound", 3): [("recepción", "GR-ZONE", "QA-ZONE", "101"),
                     ("calidad", "QA-ZONE", "PACK-ZONE", "101"),
                     ("almacenaje", "PACK-ZONE", "STOCK", "101")],
    ("outbound", 1): [("salida", "STOCK", "GI-ZONE", "201")],
    ("outbound", 2): [("pick", "STOCK", "PACK-ZONE", "201"),
                      ("salida", "PACK-ZONE", "GI-ZONE", "201")],
    ("outbound", 3): [("pick", "STOCK", "PACK-ZONE", "201"),
                      ("pack", "PACK-ZONE", "QA-ZONE", "201"),
                      ("salida", "QA-ZONE", "GI-ZONE", "201")],
    ("manufacture", 1): [("ingreso", "PROD-ZONE", "STOCK", "501")],
    ("manufacture", 2): [("ingreso", "PROD-ZONE", "QA-ZONE", "501"),
                         ("almacenaje", "QA-ZONE", "STOCK", "501")],
    ("manufacture", 3): [("ingreso", "PROD-ZONE", "QA-ZONE", "501"),
                         ("calidad", "QA-ZONE", "PACK-ZONE", "501"),
                         ("almacenaje", "PACK-ZONE", "STOCK", "501")],
}

FLOW_LABEL = {"inbound": "Recepción", "outbound": "Entrega", "manufacture": "Fabricación"}


class RouteService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create_config(self, tenant_id: str, warehouse_id: str) -> WMWarehouseConfig:
        cfg = (await self.db.execute(
            select(WMWarehouseConfig).where(
                WMWarehouseConfig.tenant_id == tenant_id,
                WMWarehouseConfig.warehouse_id == warehouse_id,
            )
        )).scalar_one_or_none()
        if cfg is None:
            cfg = WMWarehouseConfig(
                id=str(uuid.uuid4()), tenant_id=tenant_id, warehouse_id=warehouse_id,
            )
            self.db.add(cfg)
            await self.db.flush()
            await self.db.refresh(cfg)
        return cfg

    async def apply_config(
        self, tenant_id: str, warehouse_id: str, receive: int, deliver: int, manufacture: int,
    ) -> WMWarehouseConfig:
        cfg = await self.get_or_create_config(tenant_id, warehouse_id)
        cfg.receive_steps = receive
        cfg.deliver_steps = deliver
        cfg.manufacture_steps = manufacture
        await self.db.flush()
        # Make sure operation types + interim zones exist, then regenerate routes.
        mo = MovementOrderService(self.db)
        await mo.seed_operation_types(tenant_id)
        await mo.ensure_interim_locations(tenant_id, warehouse_id)
        await self.regenerate_routes(tenant_id, cfg)
        await self.db.refresh(cfg)
        return cfg

    async def regenerate_routes(self, tenant_id: str, cfg: WMWarehouseConfig) -> list[Route]:
        # Drop existing routes (rules cascade) for this warehouse.
        existing = list((await self.db.execute(
            select(Route).where(
                Route.tenant_id == tenant_id, Route.warehouse_id == cfg.warehouse_id,
            )
        )).scalars().all())
        for r in existing:
            await self.db.delete(r)
        await self.db.flush()

        flows = {
            "inbound": cfg.receive_steps,
            "outbound": cfg.deliver_steps,
            "manufacture": cfg.manufacture_steps,
        }
        routes: list[Route] = []
        for flow, steps in flows.items():
            preset = ROUTE_PRESETS[(flow, steps)]
            route = Route(
                id=str(uuid.uuid4()), tenant_id=tenant_id, warehouse_id=cfg.warehouse_id,
                code=f"{flow}_{steps}step", name=f"{FLOW_LABEL[flow]} {steps} paso(s)",
                flow=flow, steps=steps,
            )
            self.db.add(route)
            for i, (name, src, dst, op) in enumerate(preset, start=1):
                self.db.add(RouteRule(
                    id=str(uuid.uuid4()), tenant_id=tenant_id, route_id=route.id,
                    sequence=i, name=name, source_zone=src, dest_zone=dst, operation_code=op,
                ))
            routes.append(route)
        await self.db.flush()
        return routes

    async def list_routes(self, tenant_id: str, warehouse_id: str) -> list[tuple[Route, list[RouteRule]]]:
        routes = list((await self.db.execute(
            select(Route).where(
                Route.tenant_id == tenant_id, Route.warehouse_id == warehouse_id,
            ).order_by(Route.flow)
        )).scalars().all())
        out = []
        for r in routes:
            rules = list((await self.db.execute(
                select(RouteRule).where(RouteRule.route_id == r.id).order_by(RouteRule.sequence)
            )).scalars().all())
            out.append((r, rules))
        return out

    async def generate_chain(self, tenant_id: str, body: GenerateChainIn, user_id: str | None) -> tuple[Route, list]:
        route = (await self.db.execute(
            select(Route).where(
                Route.tenant_id == tenant_id,
                Route.warehouse_id == body.warehouse_id,
                Route.flow == body.flow,
            )
        )).scalar_one_or_none()
        if not route:
            raise ValidationError(
                f"No hay ruta para el flujo {body.flow!r} en este almacén. "
                f"Configurá los pasos primero (PUT /wm/warehouses/{{id}}/config)."
            )
        rules = list((await self.db.execute(
            select(RouteRule).where(RouteRule.route_id == route.id).order_by(RouteRule.sequence)
        )).scalars().all())

        mo = MovementOrderService(self.db)
        zones = await mo.ensure_interim_locations(tenant_id, body.warehouse_id)

        def resolve(zone: str) -> str | None:
            if zone == "STOCK":
                return None
            loc = zones.get(zone)
            return loc.id if loc else None

        created = []
        for rule in rules:
            op_type_id = None  # could map operation_code → OperationType.id; kept simple
            order = await mo.create_order(
                tenant_id,
                MovementOrderCreate(
                    warehouse_id=body.warehouse_id,
                    operation_type_id=op_type_id,
                    source_doc_type=body.source_doc_type,
                    source_doc_id=body.source_doc_id,
                    notes=f"{route.name} · {rule.name} ({rule.source_zone}→{rule.dest_zone})",
                    lines=[
                        MovementOrderLineCreate(
                            product_id=ln.product_id, batch_id=ln.batch_id, variant_id=ln.variant_id,
                            quantity=ln.quantity, uom=ln.uom,
                            source_location_id=resolve(rule.source_zone),
                            dest_location_id=resolve(rule.dest_zone),
                        )
                        for ln in body.lines
                    ],
                ),
                user_id,
            )
            created.append((rule, order))
        return route, created
