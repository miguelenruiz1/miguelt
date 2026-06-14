"""WM multi-step routes (Odoo-style 1/2/3-step receive / deliver / manufacture).

A warehouse declares how many steps each flow takes; from that we generate
``Route`` + ordered ``RouteRule`` rows (stock→pack→output, etc). Generating a
delivery then produces a *chain* of movement orders, one per rule.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WMWarehouseConfig(Base):
    """Per-warehouse step configuration (Odoo: receive/deliver/manufacture 1/2/3)."""
    __tablename__ = "wm_warehouse_configs"

    id:                 Mapped[str]  = mapped_column(String(36), primary_key=True)
    tenant_id:          Mapped[str]  = mapped_column(String(255), nullable=False)
    warehouse_id:       Mapped[str]  = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    receive_steps:      Mapped[int]  = mapped_column(Integer, nullable=False, server_default="1")  # 1..3
    deliver_steps:      Mapped[int]  = mapped_column(Integer, nullable=False, server_default="1")  # 1..3
    manufacture_steps:  Mapped[int]  = mapped_column(Integer, nullable=False, server_default="1")  # 1..3
    created_at:         Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:         Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("warehouse_id", name="uq_wm_warehouse_config_wh"),
        Index("ix_wm_warehouse_configs_tenant_id", "tenant_id"),
    )


class Route(Base):
    """A named multi-step flow generated from the warehouse step config."""
    __tablename__ = "wm_routes"

    id:           Mapped[str]  = mapped_column(String(36), primary_key=True)
    tenant_id:    Mapped[str]  = mapped_column(String(255), nullable=False)
    warehouse_id: Mapped[str]  = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    code:         Mapped[str]  = mapped_column(String(40), nullable=False)   # e.g. "deliver_3step"
    name:         Mapped[str]  = mapped_column(String(150), nullable=False)
    flow:         Mapped[str]  = mapped_column(String(15), nullable=False)   # inbound|outbound|manufacture
    steps:        Mapped[int]  = mapped_column(Integer, nullable=False, server_default="1")
    is_active:    Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at:   Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("warehouse_id", "flow", name="uq_wm_route_wh_flow"),
        Index("ix_wm_routes_tenant_id", "tenant_id"),
    )


class RouteRule(Base):
    """One ordered step of a route: source_zone → dest_zone with an operation code."""
    __tablename__ = "wm_route_rules"

    id:             Mapped[str]  = mapped_column(String(36), primary_key=True)
    tenant_id:      Mapped[str]  = mapped_column(String(255), nullable=False)
    route_id:       Mapped[str]  = mapped_column(
        String(36), ForeignKey("wm_routes.id", ondelete="CASCADE"), nullable=False
    )
    sequence:       Mapped[int]  = mapped_column(Integer, nullable=False, server_default="1")
    name:           Mapped[str]  = mapped_column(String(80), nullable=False)   # "pick" / "pack" / "out"
    source_zone:    Mapped[str]  = mapped_column(String(20), nullable=False)    # STOCK / GR-ZONE / PACK-ZONE ...
    dest_zone:      Mapped[str]  = mapped_column(String(20), nullable=False)
    operation_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    __table_args__ = (
        Index("ix_wm_route_rules_route", "route_id"),
        Index("ix_wm_route_rules_tenant_id", "tenant_id"),
    )
