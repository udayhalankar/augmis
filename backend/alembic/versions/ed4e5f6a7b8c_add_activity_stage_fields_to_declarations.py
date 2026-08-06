"""add activity stage fields to record declarations

Revision ID: ed4e5f6a7b8c
Revises: ec3d4e5f6a7b
Create Date: 2026-07-20 00:40:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ed4e5f6a7b8c"
down_revision = "ec3d4e5f6a7b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "symployee_record_declarations",
        sa.Column("record_stage", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_record_declarations",
        sa.Column("active_from", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "symployee_record_declarations",
        sa.Column("inactive_from", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "symployee_record_declarations",
        sa.Column("inactive_reason_code", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_symployee_record_declarations_record_stage",
        "symployee_record_declarations",
        ["record_stage"],
    )
    op.create_index(
        "ix_symployee_record_declarations_active_from",
        "symployee_record_declarations",
        ["active_from"],
    )
    op.create_index(
        "ix_symployee_record_declarations_inactive_from",
        "symployee_record_declarations",
        ["inactive_from"],
    )
    op.create_index(
        "ix_symployee_record_declarations_inactive_reason_code",
        "symployee_record_declarations",
        ["inactive_reason_code"],
    )
    op.create_check_constraint(
        "ck_symployee_record_declarations_record_stage",
        "symployee_record_declarations",
        "record_stage is null or record_stage in ('ACTIVE', 'INACTIVE', 'ARCHIVED')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_symployee_record_declarations_record_stage",
        "symployee_record_declarations",
        type_="check",
    )
    op.drop_index(
        "ix_symployee_record_declarations_inactive_reason_code",
        table_name="symployee_record_declarations",
    )
    op.drop_index(
        "ix_symployee_record_declarations_inactive_from",
        table_name="symployee_record_declarations",
    )
    op.drop_index(
        "ix_symployee_record_declarations_active_from",
        table_name="symployee_record_declarations",
    )
    op.drop_index(
        "ix_symployee_record_declarations_record_stage",
        table_name="symployee_record_declarations",
    )
    op.drop_column("symployee_record_declarations", "inactive_reason_code")
    op.drop_column("symployee_record_declarations", "inactive_from")
    op.drop_column("symployee_record_declarations", "active_from")
    op.drop_column("symployee_record_declarations", "record_stage")
