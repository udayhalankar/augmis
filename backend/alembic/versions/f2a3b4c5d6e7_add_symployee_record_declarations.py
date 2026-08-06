"""Add Symployee record declarations table.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-14 22:13:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_record_declarations",
        sa.Column("record_declaration_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("identity_id", sa.String(), nullable=False),
        sa.Column("version_id", sa.String(), nullable=True),
        sa.Column("record_category", sa.String(), nullable=False),
        sa.Column("record_status", sa.String(), nullable=False, server_default="DECLARED_RECORD"),
        sa.Column("owner_user_id", sa.String(), nullable=True),
        sa.Column("declared_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("declared_by", sa.String(), nullable=True),
        sa.Column("declaration_reason", sa.Text(), nullable=True),
        sa.Column("source_event_id", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["declared_by"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["identity_id"], ["symployee_document_identities.identity_id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["source_event_id"], ["symployee_document_lifecycle_events.event_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["version_id"], ["symployee_document_versions.version_id"]),
        sa.PrimaryKeyConstraint("record_declaration_id"),
    )

    for index_name, columns in [
        ("ix_symployee_record_declarations_tenant_id", ["tenant_id"]),
        ("ix_symployee_record_declarations_identity_id", ["identity_id"]),
        ("ix_symployee_record_declarations_version_id", ["version_id"]),
        ("ix_symployee_record_declarations_record_category", ["record_category"]),
        ("ix_symployee_record_declarations_record_status", ["record_status"]),
        ("ix_symployee_record_declarations_owner_user_id", ["owner_user_id"]),
        ("ix_symployee_record_declarations_declared_by", ["declared_by"]),
        ("ix_symployee_record_declarations_declared_at", ["declared_at"]),
        ("ix_symployee_record_declarations_source_event_id", ["source_event_id"]),
    ]:
        op.create_index(index_name, "symployee_record_declarations", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_record_declarations_source_event_id",
        "ix_symployee_record_declarations_declared_at",
        "ix_symployee_record_declarations_declared_by",
        "ix_symployee_record_declarations_owner_user_id",
        "ix_symployee_record_declarations_record_status",
        "ix_symployee_record_declarations_record_category",
        "ix_symployee_record_declarations_version_id",
        "ix_symployee_record_declarations_identity_id",
        "ix_symployee_record_declarations_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_record_declarations")

    op.drop_table("symployee_record_declarations")
