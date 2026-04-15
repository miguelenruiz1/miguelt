"""Add NUTS code, coordinate datum and screening evidence hash to compliance_plots.

EUDR / TRACES NT need:
- nuts_code: NUTS code for EU plots (Art. 9(1)(d) — admin code).
- coordinate_system_datum: explicit datum so that GeoJSON consumers know the
  reference frame (TRACES expects WGS84; some CO cadastral exports come in
  MAGNA-SIRGAS).
- screening_evidence_hash / anchored_at: SHA256 of canonical evidence bundle
  (GFW + Hansen + JRC + WDPA snapshots) anchored on Solana for tamper-proof
  audit (regulator can re-verify the screening).
"""

revision = "030_plot_nuts_datum"
down_revision = "029_plot_colombia_fields"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "compliance_plots",
        sa.Column("nuts_code", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "compliance_plots",
        sa.Column(
            "coordinate_system_datum",
            sa.String(length=20),
            nullable=False,
            server_default="WGS84",
        ),
    )
    op.add_column(
        "compliance_plots",
        sa.Column("screening_evidence_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "compliance_plots",
        sa.Column(
            "screening_evidence_anchored_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("compliance_plots", "screening_evidence_anchored_at")
    op.drop_column("compliance_plots", "screening_evidence_hash")
    op.drop_column("compliance_plots", "coordinate_system_datum")
    op.drop_column("compliance_plots", "nuts_code")
