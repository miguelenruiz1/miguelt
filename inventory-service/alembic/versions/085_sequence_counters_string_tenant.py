"""sequence_counters.tenant_id: UUID -> VARCHAR(255)

Revision ID: 085
Revises: 084
Create Date: 2026-04-14

Every other inventory-service table stores tenant_id as VARCHAR(255)
(slugs like 'default', 'qaverifier-bdc8c6', or UUID strings). Only
sequence_counters declared the column as UUID, which meant creating
a PO / SO / Remission / Invoice for any tenant whose id isn't a valid
UUID raised::

    invalid input for query argument $1: 'default' (invalid UUID)

Widening the column to VARCHAR(255) aligns it with the rest of the
schema.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "085"
down_revision: Union[str, None] = "084"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres: cast existing UUID values to text automatically.
    op.execute(
        "ALTER TABLE sequence_counters "
        "ALTER COLUMN tenant_id TYPE VARCHAR(255) USING tenant_id::text"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE sequence_counters "
        "ALTER COLUMN tenant_id TYPE uuid USING tenant_id::uuid"
    )
