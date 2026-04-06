"""CHECK constraints for compliance_records.compliance_status and declaration_status.

Locks the column to canonical values so a SQL bug or buggy client can't
insert garbage that would silently break validators.

Revision ID: 018_record_checks
Revises: 017_records_partial
"""
from alembic import op

revision = "018_record_checks"
down_revision = "017_records_partial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_records_compliance_status",
        "compliance_records",
        "compliance_status IN ('compliant','partial','incomplete','declared','ready','non_compliant')",
    )
    op.create_check_constraint(
        "ck_records_declaration_status",
        "compliance_records",
        "declaration_status IN ('not_required','pending','submitted','accepted','rejected')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_records_compliance_status", "compliance_records", type_="check")
    op.drop_constraint("ck_records_declaration_status", "compliance_records", type_="check")
