"""Add linkage fields to Symployee connector commands.

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-07-17 10:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "symployee_connector_commands",
        sa.Column("lifecycle_event_id", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_connector_commands",
        sa.Column("transmittal_id", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_connector_commands",
        sa.Column("disposition_case_id", sa.String(), nullable=True),
    )

    op.create_foreign_key(
        "fk_symployee_connector_commands_lifecycle_event_id",
        "symployee_connector_commands",
        "symployee_document_lifecycle_events",
        ["lifecycle_event_id"],
        ["event_id"],
    )
    op.create_foreign_key(
        "fk_symployee_connector_commands_transmittal_id",
        "symployee_connector_commands",
        "symployee_transmittals",
        ["transmittal_id"],
        ["transmittal_id"],
    )
    op.create_foreign_key(
        "fk_symployee_connector_commands_disposition_case_id",
        "symployee_connector_commands",
        "symployee_disposition_cases",
        ["disposition_case_id"],
        ["disposition_case_id"],
    )

    op.create_index(
        "ix_symployee_connector_commands_lifecycle_event_id",
        "symployee_connector_commands",
        ["lifecycle_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_symployee_connector_commands_transmittal_id",
        "symployee_connector_commands",
        ["transmittal_id"],
        unique=False,
    )
    op.create_index(
        "ix_symployee_connector_commands_disposition_case_id",
        "symployee_connector_commands",
        ["disposition_case_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_symployee_connector_commands_disposition_case_id",
        table_name="symployee_connector_commands",
    )
    op.drop_index(
        "ix_symployee_connector_commands_transmittal_id",
        table_name="symployee_connector_commands",
    )
    op.drop_index(
        "ix_symployee_connector_commands_lifecycle_event_id",
        table_name="symployee_connector_commands",
    )

    op.drop_constraint(
        "fk_symployee_connector_commands_disposition_case_id",
        "symployee_connector_commands",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_symployee_connector_commands_transmittal_id",
        "symployee_connector_commands",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_symployee_connector_commands_lifecycle_event_id",
        "symployee_connector_commands",
        type_="foreignkey",
    )

    op.drop_column("symployee_connector_commands", "disposition_case_id")
    op.drop_column("symployee_connector_commands", "transmittal_id")
    op.drop_column("symployee_connector_commands", "lifecycle_event_id")
