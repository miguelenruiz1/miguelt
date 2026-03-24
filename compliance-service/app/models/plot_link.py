"""CompliancePlotLink — N:N between plots and compliance records."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CompliancePlotLink(Base):
    __tablename__ = "compliance_plot_links"
    __table_args__ = (
        UniqueConstraint("record_id", "plot_id", name="uq_plot_link_record_plot"),
        Index("ix_plot_links_record", "record_id"),
        Index("ix_plot_links_plot", "plot_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_records.id", ondelete="CASCADE"), nullable=False
    )
    plot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_plots.id", ondelete="RESTRICT"), nullable=False
    )
    quantity_from_plot_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    percentage_from_plot: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
