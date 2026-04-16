"""Reserve revision 002 to keep the migration chain linear.

Revision 002 was originally skipped when 003_module_activations.py landed
with down_revision='001'. Leaving the gap made it easy for two devs on
parallel branches to both create a real '002', producing alembic merge
conflicts that are painful to untangle.

This is an intentional no-op: it exists purely to own the '002' slot so
the chain is 001 → 002 → 003 → ... → N. Running it against a prod DB
that already holds head '015' (or any later revision) is a no-op because
alembic only walks history when upgrading/downgrading through this point.

Revision ID: 002
Revises: 001
Create Date: 2026-04-16
"""
from __future__ import annotations

from typing import Sequence, Union

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
