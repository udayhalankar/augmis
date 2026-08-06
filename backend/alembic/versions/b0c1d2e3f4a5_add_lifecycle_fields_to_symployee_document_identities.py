"""Add lifecycle fields to Symployee document identities.

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-07-17 10:09:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b0c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "a9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "symployee_document_identities",
        sa.Column("document_lifecycle_stage", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_document_identities",
        sa.Column("review_status", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_document_identities",
        sa.Column("issue_status", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_document_identities",
        sa.Column("record_status", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_document_identities",
        sa.Column("retention_status", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_document_identities",
        sa.Column("disposition_status", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_document_identities",
        sa.Column("security_status", sa.String(), nullable=True),
    )

    for index_name, column_name in [
        ("ix_symployee_document_identities_document_lifecycle_stage", "document_lifecycle_stage"),
        ("ix_symployee_document_identities_review_status", "review_status"),
        ("ix_symployee_document_identities_issue_status", "issue_status"),
        ("ix_symployee_document_identities_record_status", "record_status"),
        ("ix_symployee_document_identities_retention_status", "retention_status"),
        ("ix_symployee_document_identities_disposition_status", "disposition_status"),
        ("ix_symployee_document_identities_security_status", "security_status"),
    ]:
        op.create_index(index_name, "symployee_document_identities", [column_name], unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_document_identities_security_status",
        "ix_symployee_document_identities_disposition_status",
        "ix_symployee_document_identities_retention_status",
        "ix_symployee_document_identities_record_status",
        "ix_symployee_document_identities_issue_status",
        "ix_symployee_document_identities_review_status",
        "ix_symployee_document_identities_document_lifecycle_stage",
    ]:
        op.drop_index(index_name, table_name="symployee_document_identities")

    op.drop_column("symployee_document_identities", "security_status")
    op.drop_column("symployee_document_identities", "disposition_status")
    op.drop_column("symployee_document_identities", "retention_status")
    op.drop_column("symployee_document_identities", "record_status")
    op.drop_column("symployee_document_identities", "issue_status")
    op.drop_column("symployee_document_identities", "review_status")
    op.drop_column("symployee_document_identities", "document_lifecycle_stage")
