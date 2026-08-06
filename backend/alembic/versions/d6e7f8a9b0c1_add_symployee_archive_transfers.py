"""Add Symployee archive transfers table.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-07-14 22:29:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_archive_transfers",
        sa.Column("archive_transfer_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("identity_id", sa.String(), nullable=False),
        sa.Column("record_declaration_id", sa.String(), nullable=True),
        sa.Column("disposition_case_id", sa.String(), nullable=True),
        sa.Column("transfer_status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("archive_destination", sa.String(), nullable=True),
        sa.Column("preservation_format", sa.String(), nullable=True),
        sa.Column("checksum_value", sa.Text(), nullable=True),
        sa.Column("checksum_algorithm", sa.String(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("requested_by", sa.String(), nullable=True),
        sa.Column("transferred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("transferred_by", sa.String(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["disposition_case_id"], ["symployee_disposition_cases.disposition_case_id"]),
        sa.ForeignKeyConstraint(["identity_id"], ["symployee_document_identities.identity_id"]),
        sa.ForeignKeyConstraint(["record_declaration_id"], ["symployee_record_declarations.record_declaration_id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["transferred_by"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["verified_by"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("archive_transfer_id"),
    )

    for index_name, columns in [
        ("ix_symployee_archive_transfers_tenant_id", ["tenant_id"]),
        ("ix_symployee_archive_transfers_identity_id", ["identity_id"]),
        ("ix_symployee_archive_transfers_record_declaration_id", ["record_declaration_id"]),
        ("ix_symployee_archive_transfers_disposition_case_id", ["disposition_case_id"]),
        ("ix_symployee_archive_transfers_transfer_status", ["transfer_status"]),
        ("ix_symployee_archive_transfers_archive_destination", ["archive_destination"]),
        ("ix_symployee_archive_transfers_requested_by", ["requested_by"]),
        ("ix_symployee_archive_transfers_transferred_by", ["transferred_by"]),
        ("ix_symployee_archive_transfers_verified_by", ["verified_by"]),
        ("ix_symployee_archive_transfers_requested_at", ["requested_at"]),
    ]:
        op.create_index(index_name, "symployee_archive_transfers", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_archive_transfers_requested_at",
        "ix_symployee_archive_transfers_verified_by",
        "ix_symployee_archive_transfers_transferred_by",
        "ix_symployee_archive_transfers_requested_by",
        "ix_symployee_archive_transfers_archive_destination",
        "ix_symployee_archive_transfers_transfer_status",
        "ix_symployee_archive_transfers_disposition_case_id",
        "ix_symployee_archive_transfers_record_declaration_id",
        "ix_symployee_archive_transfers_identity_id",
        "ix_symployee_archive_transfers_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_archive_transfers")

    op.drop_table("symployee_archive_transfers")
