"""AI settings table for platform-level AI configuration.

Revision ID: 008
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_ai_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        # Anthropic
        sa.Column("anthropic_api_key_encrypted", sa.Text, nullable=True),
        sa.Column("anthropic_model_analysis", sa.String(100), server_default="claude-haiku-4-5-20251001", nullable=False),
        sa.Column("anthropic_model_premium", sa.String(100), server_default="claude-sonnet-4-6", nullable=False),
        sa.Column("anthropic_max_tokens", sa.Integer, server_default="2048", nullable=False),
        sa.Column("anthropic_enabled", sa.Boolean, server_default="false", nullable=False),
        # Global limits per plan
        sa.Column("global_daily_limit_free", sa.Integer, server_default="0", nullable=False),
        sa.Column("global_daily_limit_starter", sa.Integer, server_default="10", nullable=False),
        sa.Column("global_daily_limit_professional", sa.Integer, server_default="50", nullable=False),
        sa.Column("global_daily_limit_enterprise", sa.Integer, server_default="-1", nullable=False),
        # Cache
        sa.Column("cache_ttl_minutes", sa.Integer, server_default="60", nullable=False),
        sa.Column("cache_enabled", sa.Boolean, server_default="true", nullable=False),
        # Cost monitoring
        sa.Column("estimated_cost_per_analysis_usd", sa.Numeric(10, 6), server_default="0.003", nullable=False),
        sa.Column("alert_monthly_cost_usd", sa.Numeric(10, 2), server_default="50.0", nullable=False),
        sa.Column("current_month_calls", sa.Integer, server_default="0", nullable=False),
        sa.Column("current_month_cost_usd", sa.Numeric(10, 4), server_default="0.0", nullable=False),
        # Features
        sa.Column("pnl_analysis_enabled", sa.Boolean, server_default="true", nullable=False),
    )


def downgrade() -> None:
    op.drop_table("platform_ai_settings")
