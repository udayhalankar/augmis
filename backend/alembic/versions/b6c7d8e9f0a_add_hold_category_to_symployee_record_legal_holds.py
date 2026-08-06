"""Add hold category to Symployee record legal holds.

Revision ID: b6c7d8e9f0a
Revises: a5b6c7d8e9f0
Create Date: 2026-07-18 00:40:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6c7d8e9f0a"
down_revision: Union[str, Sequence[str], None] = "a5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "symployee_record_legal_holds",
        sa.Column("hold_category", sa.String(), nullable=True),
    )
    op.create_check_constraint(
        "ck_symployee_record_legal_holds_hold_category",
        "symployee_record_legal_holds",
        "hold_category is null or hold_category in ('LEGAL', 'VALIDATION', 'RECORDS', 'OPERATIONAL', 'OTHER')",
    )
    op.create_index(
        "ix_symployee_record_legal_holds_hold_category",
        "symployee_record_legal_holds",
        ["hold_category"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_symployee_record_legal_holds_hold_category",
        table_name="symployee_record_legal_holds",
    )
    op.drop_constraint(
        "ck_symployee_record_legal_holds_hold_category",
        "symployee_record_legal_holds",
        type_="check",
    )
    op.drop_column("symployee_record_legal_holds", "hold_category")
