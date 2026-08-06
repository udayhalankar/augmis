"""Add Symployee transmittals table.

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-07-14 22:33:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_transmittals",
        sa.Column("transmittal_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("transmittal_number", sa.String(), nullable=False),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("purpose_code", sa.String(), nullable=False),
        sa.Column("transmittal_status", sa.String(), nullable=False, server_default="DRAFT"),
        sa.Column("sender_org", sa.String(), nullable=True),
        sa.Column("recipient_org", sa.String(), nullable=True),
        sa.Column("response_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("response_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("prepared_by", sa.String(), nullable=True),
        sa.Column("issued_by", sa.String(), nullable=True),
        sa.Column("workflow_instance_id", sa.String(), nullable=True),
        sa.Column("subject", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["issued_by"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["prepared_by"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["workflow_instance_id"], ["symployee_workflow_instances.workflow_instance_id"]),
        sa.PrimaryKeyConstraint("transmittal_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "transmittal_number",
            name="uq_symployee_transmittal_number",
        ),
    )

    for index_name, columns in [
        ("ix_symployee_transmittals_tenant_id", ["tenant_id"]),
        ("ix_symployee_transmittals_transmittal_number", ["transmittal_number"]),
        ("ix_symployee_transmittals_direction", ["direction"]),
        ("ix_symployee_transmittals_purpose_code", ["purpose_code"]),
        ("ix_symployee_transmittals_transmittal_status", ["transmittal_status"]),
        ("ix_symployee_transmittals_response_due_at", ["response_due_at"]),
        ("ix_symployee_transmittals_prepared_by", ["prepared_by"]),
        ("ix_symployee_transmittals_issued_by", ["issued_by"]),
        ("ix_symployee_transmittals_workflow_instance_id", ["workflow_instance_id"]),
    ]:
        op.create_index(index_name, "symployee_transmittals", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_transmittals_workflow_instance_id",
        "ix_symployee_transmittals_issued_by",
        "ix_symployee_transmittals_prepared_by",
        "ix_symployee_transmittals_response_due_at",
        "ix_symployee_transmittals_transmittal_status",
        "ix_symployee_transmittals_purpose_code",
        "ix_symployee_transmittals_direction",
        "ix_symployee_transmittals_transmittal_number",
        "ix_symployee_transmittals_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_transmittals")

    op.drop_table("symployee_transmittals")
