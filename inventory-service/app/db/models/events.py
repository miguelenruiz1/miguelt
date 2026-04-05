"""Event engine models: types, severities, statuses, events, impacts."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.config import DynamicMovementType
    from app.db.models.entity import Product
    from app.db.models.stock import StockMovement
    from app.db.models.warehouse import Warehouse


class EventType(Base):
    __tablename__ = "event_types"

    id:                              Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:                       Mapped[str]        = mapped_column(String(255), nullable=False)
    name:                            Mapped[str]        = mapped_column(String(150), nullable=False)
    slug:                            Mapped[str]        = mapped_column(String(150), nullable=False)
    description:                     Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_generate_movement_type_id:  Mapped[str | None] = mapped_column(
        String(36), ForeignKey("movement_types.id", ondelete="SET NULL"), nullable=True
    )
    color:                           Mapped[str | None] = mapped_column(String(20), nullable=True, server_default="#ef4444")
    icon:                            Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active:                       Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")

    auto_movement_type: Mapped[DynamicMovementType | None] = relationship("DynamicMovementType")
    events:             Mapped[list[InventoryEvent]] = relationship("InventoryEvent", back_populates="event_type")

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_event_type_tenant_slug"),
        Index("ix_event_types_tenant_id", "tenant_id"),
    )


class EventSeverity(Base):
    __tablename__ = "event_severities"

    id:        Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str]        = mapped_column(String(255), nullable=False)
    name:      Mapped[str]        = mapped_column(String(150), nullable=False)
    slug:      Mapped[str]        = mapped_column(String(150), nullable=False)
    weight:    Mapped[int]        = mapped_column(Integer, nullable=False, server_default="1")
    color:     Mapped[str | None] = mapped_column(String(20), nullable=True, server_default="#f59e0b")
    is_active: Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")

    events: Mapped[list[InventoryEvent]] = relationship("InventoryEvent", back_populates="severity")

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_event_severity_tenant_slug"),
        Index("ix_event_severities_tenant_id", "tenant_id"),
    )


class EventStatus(Base):
    __tablename__ = "event_statuses"

    id:         Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:  Mapped[str]        = mapped_column(String(255), nullable=False)
    name:       Mapped[str]        = mapped_column(String(150), nullable=False)
    slug:       Mapped[str]        = mapped_column(String(150), nullable=False)
    is_final:   Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    color:      Mapped[str | None] = mapped_column(String(20), nullable=True, server_default="#6b7280")
    sort_order: Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    is_active:  Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")

    events: Mapped[list[InventoryEvent]] = relationship("InventoryEvent", back_populates="status")

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_event_status_tenant_slug"),
        Index("ix_event_statuses_tenant_id", "tenant_id"),
    )


class InventoryEvent(Base):
    __tablename__ = "inventory_events"

    id:            Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:     Mapped[str]            = mapped_column(String(255), nullable=False)
    event_type_id: Mapped[str]            = mapped_column(
        String(36), ForeignKey("event_types.id", ondelete="RESTRICT"), nullable=False
    )
    severity_id:   Mapped[str]            = mapped_column(
        String(36), ForeignKey("event_severities.id", ondelete="RESTRICT"), nullable=False
    )
    status_id:     Mapped[str]            = mapped_column(
        String(36), ForeignKey("event_statuses.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id:  Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True
    )
    title:         Mapped[str]            = mapped_column(String(255), nullable=False)
    description:   Mapped[str | None]     = mapped_column(Text, nullable=True)
    occurred_at:   Mapped[DateTime]       = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at:   Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reported_by:   Mapped[str | None]     = mapped_column(String(255), nullable=True)
    updated_by:    Mapped[str | None]     = mapped_column(String(255), nullable=True)
    metadata_:     Mapped[dict]           = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    created_at:    Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[DateTime]       = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    event_type: Mapped[EventType]     = relationship("EventType", back_populates="events")
    severity:   Mapped[EventSeverity] = relationship("EventSeverity", back_populates="events")
    status:     Mapped[EventStatus]   = relationship("EventStatus", back_populates="events")
    warehouse:  Mapped[Warehouse | None] = relationship("Warehouse")
    impacts:    Mapped[list[EventImpact]] = relationship(
        "EventImpact", back_populates="event", cascade="all, delete-orphan"
    )
    status_logs: Mapped[list[EventStatusLog]] = relationship(
        "EventStatusLog", back_populates="event", cascade="all, delete-orphan",
        order_by="EventStatusLog.created_at",
    )

    __table_args__ = (
        Index("ix_inventory_events_tenant_id", "tenant_id"),
        Index("ix_inventory_events_type", "event_type_id"),
        Index("ix_inventory_events_occurred", "occurred_at"),
    )


class EventStatusLog(Base):
    """Records every status transition for an event."""
    __tablename__ = "event_status_logs"

    id:             Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:      Mapped[str]            = mapped_column(String(255), nullable=False, index=True)
    event_id:       Mapped[str]            = mapped_column(
        String(36), ForeignKey("inventory_events.id", ondelete="CASCADE"), nullable=False
    )
    from_status_id: Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("event_statuses.id", ondelete="SET NULL"), nullable=True
    )
    to_status_id:   Mapped[str]            = mapped_column(
        String(36), ForeignKey("event_statuses.id", ondelete="RESTRICT"), nullable=False
    )
    changed_by:     Mapped[str | None]     = mapped_column(String(255), nullable=True)
    notes:          Mapped[str | None]     = mapped_column(Text, nullable=True)
    created_at:     Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    event:       Mapped[InventoryEvent]      = relationship("InventoryEvent", back_populates="status_logs")
    from_status: Mapped[EventStatus | None]  = relationship("EventStatus", foreign_keys=[from_status_id])
    to_status:   Mapped[EventStatus]         = relationship("EventStatus", foreign_keys=[to_status_id])

    __table_args__ = (
        Index("ix_event_status_logs_event_id", "event_id"),
    )


class EventImpact(Base):
    __tablename__ = "event_impacts"

    id:              Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:       Mapped[str]            = mapped_column(String(255), nullable=False, index=True)
    event_id:        Mapped[str]            = mapped_column(
        String(36), ForeignKey("inventory_events.id", ondelete="CASCADE"), nullable=False
    )
    entity_id:       Mapped[str]            = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    quantity_impact: Mapped[Decimal]        = mapped_column(Numeric(18, 4), nullable=False, server_default="0")
    batch_id:        Mapped[str | None]     = mapped_column(String(36), nullable=True)
    serial_id:       Mapped[str | None]     = mapped_column(String(36), nullable=True)
    movement_id:     Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("stock_movements.id", ondelete="SET NULL"), nullable=True
    )
    notes:           Mapped[str | None]     = mapped_column(Text, nullable=True)

    event:    Mapped[InventoryEvent] = relationship("InventoryEvent", back_populates="impacts")
    entity:   Mapped[Product]        = relationship("Product")
    movement: Mapped[StockMovement | None] = relationship("StockMovement")
