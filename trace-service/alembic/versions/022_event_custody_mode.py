"""Add custody_mode column to custody_events.

MITECO webinar 3 (Fredy, EFI): la "trazabilidad" en EUDR no es monolitica —
depende del modo de custodia. Tres modos reconocidos:

  - identity_preserved: el lote del productor se mantiene fisicamente
    separado hasta el destino. Maxima credibilidad.
  - segregated: lotes certificados/no certificados separados pero mezclas
    entre lotes certificados son permitidas.
  - mass_balance: se permite mezcla fisica siempre que el volumen certificado
    vendido no exceda el volumen certificado comprado. Menor credibilidad,
    requiere evidencia de libro mayor de compensacion.

Nuevos eventos usan el modo explicitamente; eventos existentes se marcan
como 'segregated' (asuncion conservadora por defecto).

Revision ID: 022_event_custody_mode
Revises: 021_event_parent
"""
from alembic import op
import sqlalchemy as sa


revision = "022_event_custody_mode"
down_revision = "021_event_parent"
branch_labels = None
depends_on = None


VALID_MODES = ("identity_preserved", "segregated", "mass_balance")


def upgrade() -> None:
    op.add_column(
        "custody_events",
        sa.Column(
            "custody_mode",
            sa.Text(),
            nullable=False,
            server_default="segregated",
        ),
    )
    op.create_check_constraint(
        "ck_custody_events_custody_mode",
        "custody_events",
        "custody_mode IN (" + ",".join(f"'{m}'" for m in VALID_MODES) + ")",
    )
    # Drop the server_default so future inserts must be explicit from the app
    # layer; legacy rows keep the seeded value.
    op.alter_column("custody_events", "custody_mode", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_custody_events_custody_mode", "custody_events", type_="check"
    )
    op.drop_column("custody_events", "custody_mode")
