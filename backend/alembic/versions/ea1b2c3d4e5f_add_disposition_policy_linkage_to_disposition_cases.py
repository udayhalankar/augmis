"""add disposition policy linkage to disposition cases

Revision ID: ea1b2c3d4e5f
Revises: e9f0a1b2c3d4
Create Date: 2026-07-18 19:07:00
"""

from alembic import op
import sqlalchemy as sa


revision = "ea1b2c3d4e5f"
down_revision = "e9f0a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "symployee_disposition_cases",
        sa.Column("disposition_policy_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sdc_disposition_policy_id",
        "symployee_disposition_cases",
        "symployee_record_disposition_policies",
        ["disposition_policy_id"],
        ["disposition_policy_id"],
    )
    op.create_index(
        "ix_symployee_disposition_cases_disposition_policy_id",
        "symployee_disposition_cases",
        ["disposition_policy_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_symployee_disposition_cases_disposition_policy_id",
        table_name="symployee_disposition_cases",
    )
    op.drop_constraint(
        "fk_sdc_disposition_policy_id",
        "symployee_disposition_cases",
        type_="foreignkey",
    )
    op.drop_column("symployee_disposition_cases", "disposition_policy_id")
