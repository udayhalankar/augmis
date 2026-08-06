"""Add lifecycle context fields to Symployee AI recommendations.

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-17 10:38:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "symployee_ai_recommendations",
        sa.Column("lifecycle_action_type", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_ai_recommendations",
        sa.Column("lifecycle_state_dimension", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_ai_recommendations",
        sa.Column("lifecycle_target_state", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_ai_recommendations",
        sa.Column("lifecycle_context_json", sa.JSON(), nullable=True),
    )

    op.create_index(
        "ix_symployee_ai_recommendations_lifecycle_action_type",
        "symployee_ai_recommendations",
        ["lifecycle_action_type"],
        unique=False,
    )
    op.create_index(
        "ix_symployee_ai_recommendations_lifecycle_state_dimension",
        "symployee_ai_recommendations",
        ["lifecycle_state_dimension"],
        unique=False,
    )
    op.create_index(
        "ix_symployee_ai_recommendations_lifecycle_target_state",
        "symployee_ai_recommendations",
        ["lifecycle_target_state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_symployee_ai_recommendations_lifecycle_target_state",
        table_name="symployee_ai_recommendations",
    )
    op.drop_index(
        "ix_symployee_ai_recommendations_lifecycle_state_dimension",
        table_name="symployee_ai_recommendations",
    )
    op.drop_index(
        "ix_symployee_ai_recommendations_lifecycle_action_type",
        table_name="symployee_ai_recommendations",
    )
    op.drop_column("symployee_ai_recommendations", "lifecycle_context_json")
    op.drop_column("symployee_ai_recommendations", "lifecycle_target_state")
    op.drop_column("symployee_ai_recommendations", "lifecycle_state_dimension")
    op.drop_column("symployee_ai_recommendations", "lifecycle_action_type")
