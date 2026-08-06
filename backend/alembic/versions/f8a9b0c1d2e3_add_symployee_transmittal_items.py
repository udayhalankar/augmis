"""Add Symployee transmittal items table.

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-07-14 22:37:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_transmittal_items",
        sa.Column("transmittal_item_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("transmittal_id", sa.String(), nullable=False),
        sa.Column("identity_id", sa.String(), nullable=False),
        sa.Column("version_id", sa.String(), nullable=True),
        sa.Column("item_status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("issue_status", sa.String(), nullable=True),
        sa.Column("sequence_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("document_number", sa.String(), nullable=True),
        sa.Column("revision_code", sa.String(), nullable=True),
        sa.Column("purpose_code", sa.String(), nullable=True),
        sa.Column("response_code", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["identity_id"], ["symployee_document_identities.identity_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["transmittal_id"], ["symployee_transmittals.transmittal_id"]),
        sa.ForeignKeyConstraint(["version_id"], ["symployee_document_versions.version_id"]),
        sa.PrimaryKeyConstraint("transmittal_item_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "transmittal_id",
            "identity_id",
            "version_id",
            name="uq_symployee_transmittal_item_version",
        ),
    )

    for index_name, columns in [
        ("ix_symployee_transmittal_items_tenant_id", ["tenant_id"]),
        ("ix_symployee_transmittal_items_transmittal_id", ["transmittal_id"]),
        ("ix_symployee_transmittal_items_identity_id", ["identity_id"]),
        ("ix_symployee_transmittal_items_version_id", ["version_id"]),
        ("ix_symployee_transmittal_items_item_status", ["item_status"]),
        ("ix_symployee_transmittal_items_issue_status", ["issue_status"]),
        ("ix_symployee_transmittal_items_document_number", ["document_number"]),
        ("ix_symployee_transmittal_items_revision_code", ["revision_code"]),
    ]:
        op.create_index(index_name, "symployee_transmittal_items", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_transmittal_items_revision_code",
        "ix_symployee_transmittal_items_document_number",
        "ix_symployee_transmittal_items_issue_status",
        "ix_symployee_transmittal_items_item_status",
        "ix_symployee_transmittal_items_version_id",
        "ix_symployee_transmittal_items_identity_id",
        "ix_symployee_transmittal_items_transmittal_id",
        "ix_symployee_transmittal_items_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_transmittal_items")

    op.drop_table("symployee_transmittal_items")
