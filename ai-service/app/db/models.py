"""AI service database models."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlatformAISettings(Base):
    """Singleton table for global AI configuration."""
    __tablename__ = "platform_ai_settings"

    id:                              Mapped[str]     = mapped_column(String(36), primary_key=True)
    created_at:                      Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:                      Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # Anthropic
    anthropic_api_key_encrypted:     Mapped[str | None] = mapped_column(Text, nullable=True)
    anthropic_model_analysis:        Mapped[str]     = mapped_column(String(100), nullable=False, server_default="claude-haiku-4-5-20251001")
    anthropic_model_premium:         Mapped[str]     = mapped_column(String(100), nullable=False, server_default="claude-sonnet-4-6")
    anthropic_max_tokens:            Mapped[int]     = mapped_column(Integer, nullable=False, server_default="2048")
    anthropic_enabled:               Mapped[bool]    = mapped_column(Boolean, nullable=False, server_default="false")
    # Limits per plan
    global_daily_limit_free:         Mapped[int]     = mapped_column(Integer, nullable=False, server_default="0")
    global_daily_limit_starter:      Mapped[int]     = mapped_column(Integer, nullable=False, server_default="3")
    global_daily_limit_professional: Mapped[int]     = mapped_column(Integer, nullable=False, server_default="10")
    global_daily_limit_enterprise:   Mapped[int]     = mapped_column(Integer, nullable=False, server_default="30")
    # Cache
    cache_ttl_minutes:               Mapped[int]     = mapped_column(Integer, nullable=False, server_default="60")
    cache_enabled:                   Mapped[bool]    = mapped_column(Boolean, nullable=False, server_default="true")
    # Cost monitoring
    estimated_cost_per_analysis_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, server_default="0.006")
    alert_monthly_cost_usd:          Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, server_default="50.0")
    current_month_calls:             Mapped[int]     = mapped_column(Integer, nullable=False, server_default="0")
    current_month_cost_usd:          Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, server_default="0.0")
    # Features
    pnl_analysis_enabled:            Mapped[bool]    = mapped_column(Boolean, nullable=False, server_default="true")
