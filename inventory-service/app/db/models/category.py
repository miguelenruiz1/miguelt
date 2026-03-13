"""Product categories — hierarchical classification."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    pass


class Category(Base):
    __tablename__ = "categories"

    id:          Mapped[str]           = mapped_column(String(36), primary_key=True)
    tenant_id:   Mapped[str]           = mapped_column(String(255), nullable=False)
    name:        Mapped[str]           = mapped_column(String(150), nullable=False)
    slug:        Mapped[str]           = mapped_column(String(150), nullable=False)
    description: Mapped[str | None]    = mapped_column(Text, nullable=True)
    parent_id:   Mapped[str | None]    = mapped_column(
        String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    is_active:   Mapped[bool]          = mapped_column(Boolean, nullable=False, server_default="true")
    sort_order:  Mapped[int]           = mapped_column(Integer, nullable=False, server_default="0")
    created_by:  Mapped[str | None]    = mapped_column(String(255), nullable=True)
    updated_by:  Mapped[str | None]    = mapped_column(String(255), nullable=True)
    created_at:  Mapped[DateTime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:  Mapped[DateTime]      = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    parent:   Mapped[Category | None]    = relationship(
        "Category", remote_side="Category.id", foreign_keys=[parent_id], back_populates="children",
    )
    children: Mapped[list[Category]]     = relationship(
        "Category", back_populates="parent", foreign_keys="Category.parent_id",
    )

    __table_args__ = (
        Index("ix_categories_tenant_id", "tenant_id"),
        Index("ix_categories_parent_id", "parent_id"),
    )
