"""Add Symployee distribution acknowledgements table.

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-07-14 22:41:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9b0c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_distribution_acknowledgements",
        sa.Column("acknowledgement_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("transmittal_id", sa.String(), nullable=False),
        sa.Column("transmittal_item_id", sa.String(), nullable=True),
        sa.Column("recipient_ref", sa.String(), nullable=False),
        sa.Column("recipient_name", sa.String(), nullable=True),
        sa.Column("acknowledgement_status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("response_status", sa.String(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["transmittal_id"], ["symployee_transmittals.transmittal_id"]),
        sa.ForeignKeyConstraint(["transmittal_item_id"], ["symployee_transmittal_items.transmittal_item_id"]),
        sa.PrimaryKeyConstraint("acknowledgement_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "transmittal_id",
            "transmittal_item_id",
            "recipient_ref",
            name="uq_symployee_distribution_ack",
        ),
    )

    for index_name, columns in [
        ("ix_symployee_distribution_acknowledgements_tenant_id", ["tenant_id"]),
        ("ix_symployee_distribution_acknowledgements_transmittal_id", ["transmittal_id"]),
        ("ix_symployee_distribution_acknowledgements_transmittal_item_id", ["transmittal_item_id"]),
        ("ix_symployee_distribution_acknowledgements_recipient_ref", ["recipient_ref"]),
        ("ix_symployee_distribution_acknowledgements_ack_status", ["acknowledgement_status"]),
        ("ix_symployee_distribution_acknowledgements_response_status", ["response_status"]),
        ("ix_symployee_distribution_acknowledgements_due_at", ["due_at"]),
        ("ix_symployee_distribution_acknowledgements_acknowledged_at", ["acknowledged_at"]),
    ]:
        op.create_index(index_name, "symployee_distribution_acknowledgements", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_distribution_acknowledgements_acknowledged_at",
        "ix_symployee_distribution_acknowledgements_due_at",
        "ix_symployee_distribution_acknowledgements_response_status",
        "ix_symployee_distribution_acknowledgements_ack_status",
        "ix_symployee_distribution_acknowledgements_recipient_ref",
        "ix_symployee_distribution_acknowledgements_transmittal_item_id",
        "ix_symployee_distribution_acknowledgements_transmittal_id",
        "ix_symployee_distribution_acknowledgements_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_distribution_acknowledgements")

    op.drop_table("symployee_distribution_acknowledgements")
