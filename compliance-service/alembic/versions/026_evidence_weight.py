"""Add evidence_weight to plot_legal_compliance.

MITECO webinar 3 (Alice / Fredy, EFI): una declaracion jurada no tiene el
mismo peso que evidencia documental independiente. Este campo permite al
decision-tree levantar advertencia cuando la unica evidencia es una
declaracion jurada, y obliga al operador a buscar corroboracion cruzada.

Weights:
  - primary: documento oficial (titulo, licencia, auditoria externa)
  - secondary: documento de respaldo (factura, registro contable)
  - affidavit: declaracion jurada del productor — peso reducido,
    requiere corroboracion cruzada

Revision ID: 026_evidence_weight
Revises: 025_cert_country_risk
"""
from alembic import op
import sqlalchemy as sa


revision = "026_evidence_weight"
down_revision = "025_cert_country_risk"
branch_labels = None
depends_on = None


WEIGHTS = ("primary", "secondary", "affidavit")


def upgrade() -> None:
    op.add_column(
        "plot_legal_compliance",
        sa.Column(
            "evidence_weight",
            sa.Text(),
            nullable=False,
            server_default="primary",
        ),
    )
    op.create_check_constraint(
        "ck_plot_legal_evidence_weight",
        "plot_legal_compliance",
        "evidence_weight IN (" + ",".join(f"'{w}'" for w in WEIGHTS) + ")",
    )
    op.alter_column("plot_legal_compliance", "evidence_weight", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_plot_legal_evidence_weight", "plot_legal_compliance", type_="check"
    )
    op.drop_column("plot_legal_compliance", "evidence_weight")
