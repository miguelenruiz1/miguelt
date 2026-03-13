"""Add profile fields to users: phone, job_title, company, bio, timezone, language

Revision ID: 006
Revises: 005
Create Date: 2026-03-03
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(30), nullable=True))
    op.add_column("users", sa.Column("job_title", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("company", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("bio", sa.Text, nullable=True))
    op.add_column("users", sa.Column("timezone", sa.String(100), nullable=True, server_default=sa.text("'America/Bogota'")))
    op.add_column("users", sa.Column("language", sa.String(10), nullable=True, server_default=sa.text("'es'")))


def downgrade() -> None:
    op.drop_column("users", "language")
    op.drop_column("users", "timezone")
    op.drop_column("users", "bio")
    op.drop_column("users", "company")
    op.drop_column("users", "job_title")
    op.drop_column("users", "phone")
