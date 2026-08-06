"""Add Symployee document lifecycle events table.

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-07-14 22:08:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_document_lifecycle_events",
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("identity_id", sa.String(), nullable=False),
        sa.Column("version_id", sa.String(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("state_dimension", sa.String(), nullable=False),
        sa.Column("previous_state", sa.String(), nullable=True),
        sa.Column("new_state", sa.String(), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("performed_by", sa.String(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("workflow_instance_id", sa.String(), nullable=True),
        sa.Column("transmittal_id", sa.String(), nullable=True),
        sa.Column("approval_id", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["approval_id"], ["symployee_approval_records.approval_id"]),
        sa.ForeignKeyConstraint(["identity_id"], ["symployee_document_identities.identity_id"]),
        sa.ForeignKeyConstraint(["performed_by"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["version_id"], ["symployee_document_versions.version_id"]),
        sa.ForeignKeyConstraint(["workflow_instance_id"], ["symployee_workflow_instances.workflow_instance_id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )

    for index_name, columns in [
        ("ix_symployee_document_lifecycle_events_tenant_id", ["tenant_id"]),
        ("ix_symployee_document_lifecycle_events_identity_id", ["identity_id"]),
        ("ix_symployee_document_lifecycle_events_version_id", ["version_id"]),
        ("ix_symployee_document_lifecycle_events_event_type", ["event_type"]),
        ("ix_symployee_document_lifecycle_events_state_dimension", ["state_dimension"]),
        ("ix_symployee_document_lifecycle_events_event_date", ["event_date"]),
        ("ix_symployee_document_lifecycle_events_performed_by", ["performed_by"]),
        ("ix_symployee_document_lifecycle_events_workflow_instance_id", ["workflow_instance_id"]),
        ("ix_symployee_document_lifecycle_events_approval_id", ["approval_id"]),
    ]:
        op.create_index(index_name, "symployee_document_lifecycle_events", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_document_lifecycle_events_approval_id",
        "ix_symployee_document_lifecycle_events_workflow_instance_id",
        "ix_symployee_document_lifecycle_events_performed_by",
        "ix_symployee_document_lifecycle_events_event_date",
        "ix_symployee_document_lifecycle_events_state_dimension",
        "ix_symployee_document_lifecycle_events_event_type",
        "ix_symployee_document_lifecycle_events_version_id",
        "ix_symployee_document_lifecycle_events_identity_id",
        "ix_symployee_document_lifecycle_events_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_document_lifecycle_events")

    op.drop_table("symployee_document_lifecycle_events")
