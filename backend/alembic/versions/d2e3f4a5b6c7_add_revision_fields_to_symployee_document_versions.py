"""Add revision fields to Symployee document versions.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-07-17 10:24:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "symployee_document_versions",
        sa.Column("revision_status", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_document_versions",
        sa.Column("issue_status", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_document_versions",
        sa.Column("is_current_revision", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "symployee_document_versions",
        sa.Column("revision_sequence_no", sa.Integer(), nullable=True),
    )
    op.add_column(
        "symployee_document_versions",
        sa.Column("revision_purpose_code", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_document_versions",
        sa.Column("revision_description", sa.Text(), nullable=True),
    )

    op.create_index(
        "ix_symployee_document_versions_revision_status",
        "symployee_document_versions",
        ["revision_status"],
        unique=False,
    )
    op.create_index(
        "ix_symployee_document_versions_issue_status",
        "symployee_document_versions",
        ["issue_status"],
        unique=False,
    )
    op.create_index(
        "ix_symployee_document_versions_is_current_revision",
        "symployee_document_versions",
        ["is_current_revision"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_symployee_document_versions_is_current_revision",
        table_name="symployee_document_versions",
    )
    op.drop_index(
        "ix_symployee_document_versions_issue_status",
        table_name="symployee_document_versions",
    )
    op.drop_index(
        "ix_symployee_document_versions_revision_status",
        table_name="symployee_document_versions",
    )
    op.drop_column("symployee_document_versions", "revision_description")
    op.drop_column("symployee_document_versions", "revision_purpose_code")
    op.drop_column("symployee_document_versions", "revision_sequence_no")
    op.drop_column("symployee_document_versions", "is_current_revision")
    op.drop_column("symployee_document_versions", "issue_status")
    op.drop_column("symployee_document_versions", "revision_status")
