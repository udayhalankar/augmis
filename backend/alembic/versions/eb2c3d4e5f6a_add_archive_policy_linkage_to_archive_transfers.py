"""add archive policy linkage to archive transfers

Revision ID: eb2c3d4e5f6a
Revises: ea1b2c3d4e5f
Create Date: 2026-07-18 19:09:00
"""

from alembic import op
import sqlalchemy as sa


revision = "eb2c3d4e5f6a"
down_revision = "ea1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "symployee_archive_transfers",
        sa.Column("archive_policy_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sat_archive_policy_id",
        "symployee_archive_transfers",
        "symployee_record_archive_policies",
        ["archive_policy_id"],
        ["archive_policy_id"],
    )
    op.create_index(
        "ix_symployee_archive_transfers_archive_policy_id",
        "symployee_archive_transfers",
        ["archive_policy_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_symployee_archive_transfers_archive_policy_id",
        table_name="symployee_archive_transfers",
    )
    op.drop_constraint(
        "fk_sat_archive_policy_id",
        "symployee_archive_transfers",
        type_="foreignkey",
    )
    op.drop_column("symployee_archive_transfers", "archive_policy_id")
