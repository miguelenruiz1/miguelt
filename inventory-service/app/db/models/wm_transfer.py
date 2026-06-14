"""WM transfer documents: operation types, transfer requirements, transfer orders.

SAP-WM core: **no physical movement without a document**. Every receipt, issue
or internal move is (or generates) a Transfer Order (orden de transporte) with a
source bin + destination bin and up to two confirmations (pick / putaway).

- ``OperationType`` ≈ SAP clase de movimiento (101 receipt, 201 issue, 311
  internal transfer, 601 delivery) — drives direction + interim zones.
- ``TransferRequirement`` ≈ necesidad de transporte — a planned/provisional need
  (from a PO, SO, production order, or manual), processed into a Transfer Order.
- ``TransferOrder`` / ``TransferOrderLine`` ≈ orden de transporte — the executed
  document; on full confirmation it posts a kardex StockMovement.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OperationType(Base):
    """WM movement class (SAP clase de movimiento)."""
    __tablename__ = "wm_operation_types"

    id:           Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:    Mapped[str]        = mapped_column(String(255), nullable=False)
    warehouse_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=True
    )
    code:         Mapped[str]        = mapped_column(String(10), nullable=False)   # "101", "201", "311", "601"
    name:         Mapped[str]        = mapped_column(String(150), nullable=False)
    direction:    Mapped[str]        = mapped_column(String(12), nullable=False)   # inbound|outbound|internal
    movement_type: Mapped[str | None] = mapped_column(String(20), nullable=True)   # maps to MovementType value
    # Interim zone codes this operation pulls from / drops into (logical bins).
    source_zone:  Mapped[str | None] = mapped_column(String(20), nullable=True)    # e.g. "GR-ZONE"
    dest_zone:    Mapped[str | None] = mapped_column(String(20), nullable=True)    # e.g. "STOCK"
    requires_qa:  Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    is_active:    Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    created_at:   Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_wm_operation_type_tenant_code"),
        Index("ix_wm_operation_types_tenant_id", "tenant_id"),
    )


class TransferRequirement(Base):
    """Planned/provisional need (SAP necesidad de transporte)."""
    __tablename__ = "wm_transfer_requirements"

    id:               Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:        Mapped[str]        = mapped_column(String(255), nullable=False)
    warehouse_id:     Mapped[str]        = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    operation_type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("wm_operation_types.id", ondelete="SET NULL"), nullable=True
    )
    ref_type:         Mapped[str | None] = mapped_column(String(20), nullable=True)   # po|so|production|manual
    ref_id:           Mapped[str | None] = mapped_column(String(36), nullable=True)
    product_id:       Mapped[str]        = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    batch_id:         Mapped[str | None] = mapped_column(
        String(36), ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True
    )
    variant_id:       Mapped[str | None] = mapped_column(
        String(36), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    quantity:         Mapped[Decimal]    = mapped_column(Numeric(18, 4), nullable=False)
    uom:              Mapped[str]        = mapped_column(String(20), nullable=False, server_default="primary")
    status:           Mapped[str]        = mapped_column(String(15), nullable=False, server_default="open")  # open|processed|canceled
    requested_date:   Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:       Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_wm_transfer_requirements_tenant_id", "tenant_id"),
        Index("ix_wm_transfer_req_status", "tenant_id", "status"),
        Index("ix_wm_transfer_req_ref", "ref_type", "ref_id"),
    )


class TransferOrder(Base):
    """Executed transfer order (SAP orden de transporte) — header."""
    __tablename__ = "wm_transfer_orders"

    id:               Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:        Mapped[str]        = mapped_column(String(255), nullable=False)
    warehouse_id:     Mapped[str]        = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    to_number:        Mapped[str]        = mapped_column(String(40), nullable=False)
    operation_type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("wm_operation_types.id", ondelete="SET NULL"), nullable=True
    )
    requirement_id:   Mapped[str | None] = mapped_column(
        String(36), ForeignKey("wm_transfer_requirements.id", ondelete="SET NULL"), nullable=True
    )
    status:           Mapped[str]        = mapped_column(String(15), nullable=False, server_default="open")  # open|in_progress|confirmed|canceled
    source_doc_type:  Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_doc_id:    Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes:            Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:       Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at:     Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by:     Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "to_number", name="uq_wm_transfer_order_tenant_number"),
        Index("ix_wm_transfer_orders_tenant_id", "tenant_id"),
        Index("ix_wm_transfer_orders_status", "tenant_id", "status"),
        Index("ix_wm_transfer_orders_warehouse", "warehouse_id"),
    )


class TransferOrderLine(Base):
    """Transfer order line — bin→bin move of one product/batch with 2 confirmations."""
    __tablename__ = "wm_transfer_order_lines"

    id:                 Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:          Mapped[str]        = mapped_column(String(255), nullable=False)
    transfer_order_id:  Mapped[str]        = mapped_column(
        String(36), ForeignKey("wm_transfer_orders.id", ondelete="CASCADE"), nullable=False
    )
    line_no:            Mapped[int]        = mapped_column(Integer, nullable=False, server_default="1")
    product_id:         Mapped[str]        = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False
    )
    batch_id:           Mapped[str | None] = mapped_column(
        String(36), ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True
    )
    variant_id:         Mapped[str | None] = mapped_column(
        String(36), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    quantity:           Mapped[Decimal]    = mapped_column(Numeric(18, 4), nullable=False)
    uom:                Mapped[str]        = mapped_column(String(20), nullable=False, server_default="primary")
    source_location_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True
    )
    dest_location_id:   Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True
    )
    source_confirmed:   Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    dest_confirmed:     Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    confirmed_qty:      Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    status:             Mapped[str]        = mapped_column(String(12), nullable=False, server_default="open")  # open|picked|done

    __table_args__ = (
        Index("ix_wm_to_lines_tenant_id", "tenant_id"),
        Index("ix_wm_to_lines_order", "transfer_order_id"),
    )
