"""Add outcome fields to Symployee workflow tasks.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-17 10:31:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "symployee_workflow_tasks",
        sa.Column("outcome_code", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_workflow_tasks",
        sa.Column("response_code", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_workflow_tasks",
        sa.Column("outcome_notes", sa.Text(), nullable=True),
    )

    op.create_index(
        "ix_symployee_workflow_tasks_outcome_code",
        "symployee_workflow_tasks",
        ["outcome_code"],
        unique=False,
    )
    op.create_index(
        "ix_symployee_workflow_tasks_response_code",
        "symployee_workflow_tasks",
        ["response_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_symployee_workflow_tasks_response_code",
        table_name="symployee_workflow_tasks",
    )
    op.drop_index(
        "ix_symployee_workflow_tasks_outcome_code",
        table_name="symployee_workflow_tasks",
    )
    op.drop_column("symployee_workflow_tasks", "outcome_notes")
    op.drop_column("symployee_workflow_tasks", "response_code")
    op.drop_column("symployee_workflow_tasks", "outcome_code")
