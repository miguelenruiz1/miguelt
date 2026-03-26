"""Serial and batch tracking models."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.entity import Product
    from app.db.models.warehouse import Warehouse, WarehouseLocation


class SerialStatus(Base):
    __tablename__ = "serial_statuses"

    id:          Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:   Mapped[str]        = mapped_column(String(255), nullable=False)
    name:        Mapped[str]        = mapped_column(String(150), nullable=False)
    slug:        Mapped[str]        = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color:       Mapped[str | None] = mapped_column(String(20), nullable=True, server_default="#3b82f6")
    is_active:   Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    created_at:  Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:  Mapped[DateTime]   = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    serials: Mapped[list[EntitySerial]] = relationship("EntitySerial", back_populates="status")

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_serial_status_tenant_slug"),
        Index("ix_serial_statuses_tenant_id", "tenant_id"),
    )


class EntitySerial(Base):
    __tablename__ = "entity_serials"

    id:            Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:     Mapped[str]        = mapped_column(String(255), nullable=False)
    entity_id:     Mapped[str]        = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    serial_number: Mapped[str]        = mapped_column(String(255), nullable=False)
    status_id:     Mapped[str]        = mapped_column(
        String(36), ForeignKey("serial_statuses.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id:  Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True
    )
    location_id:   Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True
    )
    batch_id:      Mapped[str | None] = mapped_column(
        String(36), ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True
    )
    notes:         Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_:     Mapped[dict]       = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    created_by:    Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by:    Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:    Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[DateTime]   = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    entity:    Mapped[Product]                    = relationship("Product")
    status:    Mapped[SerialStatus]               = relationship("SerialStatus", back_populates="serials")
    warehouse: Mapped[Warehouse | None]           = relationship("Warehouse")
    location:  Mapped[WarehouseLocation | None]   = relationship("WarehouseLocation")
    batch:     Mapped[EntityBatch | None]         = relationship("EntityBatch", back_populates="serials")

    __table_args__ = (
        UniqueConstraint("tenant_id", "entity_id", "serial_number", name="uq_serial_tenant_entity"),
        Index("ix_entity_serials_tenant_id", "tenant_id"),
        Index("ix_entity_serials_entity_id", "entity_id"),
    )


class EntityBatch(Base):
    __tablename__ = "entity_batches"

    id:               Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:        Mapped[str]            = mapped_column(String(255), nullable=False)
    entity_id:        Mapped[str]            = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    batch_number:     Mapped[str]            = mapped_column(String(100), nullable=False)
    manufacture_date: Mapped[Date | None]    = mapped_column(Date, nullable=True)
    expiration_date:  Mapped[Date | None]    = mapped_column(Date, nullable=True)
    cost:             Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    quantity:         Mapped[Decimal]        = mapped_column(Numeric(12, 4), nullable=False, server_default="0")
    notes:            Mapped[str | None]     = mapped_column(Text, nullable=True)
    metadata_:        Mapped[dict]           = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    is_active:        Mapped[bool]           = mapped_column(Boolean, nullable=False, server_default="true")

    # Blockchain anchoring
    anchor_hash:      Mapped[str | None]     = mapped_column(String(64), nullable=True)
    anchor_status:    Mapped[str]            = mapped_column(String(20), nullable=False, server_default="none")
    anchor_tx_sig:    Mapped[str | None]     = mapped_column(String(128), nullable=True)
    anchored_at:      Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Blockchain cNFT (minted via trace-service)
    blockchain_asset_id: Mapped[str | None]  = mapped_column(String(128), nullable=True)
    blockchain_tx_sig:   Mapped[str | None]  = mapped_column(String(128), nullable=True)
    blockchain_status:   Mapped[str]         = mapped_column(String(20), nullable=False, server_default="none")

    created_by:       Mapped[str | None]     = mapped_column(String(255), nullable=True)
    updated_by:       Mapped[str | None]     = mapped_column(String(255), nullable=True)
    created_at:       Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:       Mapped[DateTime]       = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    entity:  Mapped[Product] = relationship("Product")
    serials: Mapped[list[EntitySerial]] = relationship("EntitySerial", back_populates="batch")

    __table_args__ = (
        UniqueConstraint("tenant_id", "entity_id", "batch_number", name="uq_batch_tenant_entity"),
        Index("ix_entity_batches_tenant_id", "tenant_id"),
        Index("ix_entity_batches_entity_id", "entity_id"),
        Index("ix_entity_batches_expiration", "expiration_date"),
        Index("ix_entity_batches_tenant_entity_active", "tenant_id", "entity_id", "is_active"),
    )
