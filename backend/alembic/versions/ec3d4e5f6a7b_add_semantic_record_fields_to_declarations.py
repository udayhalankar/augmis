"""add semantic record fields to declarations

Revision ID: ec3d4e5f6a7b
Revises: eb2c3d4e5f6a
Create Date: 2026-07-18 19:42:00
"""

from alembic import op
import sqlalchemy as sa


revision = "ec3d4e5f6a7b"
down_revision = "eb2c3d4e5f6a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "symployee_record_declarations",
        sa.Column("vital_status", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_record_declarations",
        sa.Column("inactive_reason", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_symployee_record_declarations_vital_status",
        "symployee_record_declarations",
        ["vital_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_symployee_record_declarations_vital_status",
        table_name="symployee_record_declarations",
    )
    op.drop_column("symployee_record_declarations", "inactive_reason")
    op.drop_column("symployee_record_declarations", "vital_status")
