"""add project scope to record assignment rules

Revision ID: ee5f6a7b8c9d
Revises: ed4e5f6a7b8c
Create Date: 2026-07-20 23:26:00
"""

from alembic import op
import sqlalchemy as sa


revision = "ee5f6a7b8c9d"
down_revision = "ed4e5f6a7b8c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "symployee_record_assignment_rules",
        sa.Column("project_code", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_symployee_record_assignment_rules_project_code",
        "symployee_record_assignment_rules",
        ["project_code"],
        unique=False,
    )
    op.drop_constraint(
        "ck_symployee_record_assignment_rules_context",
        "symployee_record_assignment_rules",
        type_="check",
    )
    op.create_check_constraint(
        "ck_symployee_record_assignment_rules_context",
        "symployee_record_assignment_rules",
        "assignment_context in ('DECLARATION', 'VITAL_REVIEW', 'HOLD_PLACEMENT', 'RETENTION_REVIEW', 'DISPOSITION_APPROVAL', 'DISPOSITION_EXECUTION', 'ARCHIVE_TRANSFER')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_symployee_record_assignment_rules_context",
        "symployee_record_assignment_rules",
        type_="check",
    )
    op.create_check_constraint(
        "ck_symployee_record_assignment_rules_context",
        "symployee_record_assignment_rules",
        "assignment_context in ('DECLARATION', 'VITAL_REVIEW', 'HOLD_PLACEMENT', 'RETENTION_REVIEW', 'DISPOSITION_APPROVAL', 'ARCHIVE_TRANSFER')",
    )
    op.drop_index(
        "ix_symployee_record_assignment_rules_project_code",
        table_name="symployee_record_assignment_rules",
    )
    op.drop_column("symployee_record_assignment_rules", "project_code")
