"""Add lifecycle linkage fields to Symployee workflow instances.

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-07-17 10:18:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b0c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "symployee_workflow_instances",
        sa.Column("lifecycle_state_dimension", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_workflow_instances",
        sa.Column("lifecycle_target_state", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_workflow_instances",
        sa.Column("lifecycle_context_json", sa.JSON(), nullable=True),
    )

    op.create_index(
        "ix_symployee_workflow_instances_lifecycle_state_dimension",
        "symployee_workflow_instances",
        ["lifecycle_state_dimension"],
        unique=False,
    )
    op.create_index(
        "ix_symployee_workflow_instances_lifecycle_target_state",
        "symployee_workflow_instances",
        ["lifecycle_target_state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_symployee_workflow_instances_lifecycle_target_state",
        table_name="symployee_workflow_instances",
    )
    op.drop_index(
        "ix_symployee_workflow_instances_lifecycle_state_dimension",
        table_name="symployee_workflow_instances",
    )
    op.drop_column("symployee_workflow_instances", "lifecycle_context_json")
    op.drop_column("symployee_workflow_instances", "lifecycle_target_state")
    op.drop_column("symployee_workflow_instances", "lifecycle_state_dimension")
