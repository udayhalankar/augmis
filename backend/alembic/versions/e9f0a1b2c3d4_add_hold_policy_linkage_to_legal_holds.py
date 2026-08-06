"""add hold policy linkage to legal holds

Revision ID: e9f0a1b2c3d4
Revises: e8f9a0b1c2d3
Create Date: 2026-07-18 19:05:00
"""

from alembic import op
import sqlalchemy as sa


revision = "e9f0a1b2c3d4"
down_revision = "e8f9a0b1c2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "symployee_record_legal_holds",
        sa.Column("hold_policy_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_srlh_hold_policy_id",
        "symployee_record_legal_holds",
        "symployee_record_hold_policies",
        ["hold_policy_id"],
        ["hold_policy_id"],
    )
    op.create_index(
        "ix_symployee_record_legal_holds_hold_policy_id",
        "symployee_record_legal_holds",
        ["hold_policy_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_symployee_record_legal_holds_hold_policy_id",
        table_name="symployee_record_legal_holds",
    )
    op.drop_constraint(
        "fk_srlh_hold_policy_id",
        "symployee_record_legal_holds",
        type_="foreignkey",
    )
    op.drop_column("symployee_record_legal_holds", "hold_policy_id")
