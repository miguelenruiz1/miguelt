"""ComplianceSupplyChainNode — EUDR Art. 9.1.e-f supply chain actors."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class ComplianceSupplyChainNode(Base):
    __tablename__ = "compliance_supply_chain_nodes"
    __table_args__ = (
        UniqueConstraint("record_id", "sequence_order", name="uq_sc_record_sequence"),
        Index("ix_sc_tenant", "tenant_id"),
        Index("ix_sc_record", "record_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_records.id", ondelete="CASCADE"), nullable=False
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    actor_name: Mapped[str] = mapped_column(Text, nullable=False)
    actor_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_country: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_tax_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_eori: Mapped[str | None] = mapped_column(Text, nullable=True)
    handoff_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    verification_status: Mapped[str] = mapped_column(Text, nullable=False, default="unverified")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
