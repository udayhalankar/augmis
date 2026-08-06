"""Add Symployee record archive policies configuration table.

Revision ID: d4e5f6a7b8c
Revises: d3d4e5f6a7b
Create Date: 2026-07-18 17:34:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c"
down_revision: Union[str, Sequence[str], None] = "d3d4e5f6a7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_record_archive_policies",
        sa.Column("archive_policy_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("repository_id", sa.String(), nullable=True),
        sa.Column("business_area", sa.String(), nullable=True),
        sa.Column("document_type", sa.String(), nullable=True),
        sa.Column("policy_code", sa.String(), nullable=False),
        sa.Column("policy_name", sa.String(), nullable=False),
        sa.Column("policy_description", sa.Text(), nullable=True),
        sa.Column("record_category_code", sa.String(), nullable=True),
        sa.Column("transfer_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("destination_code", sa.String(), nullable=False),
        sa.Column("package_format_code", sa.String(), nullable=False),
        sa.Column("checksum_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_profile_code", sa.String(), nullable=False),
        sa.Column("preservation_review_interval_days", sa.Integer(), nullable=True),
        sa.Column("receipt_confirmation_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("criteria_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="DRAFT"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_current_version", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("rule_priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("config_payload_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status in ('DRAFT', 'ACTIVE', 'INACTIVE', 'RETIRED')",
            name="ck_symployee_record_archive_policies_status",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.repository_id"]),
        sa.PrimaryKeyConstraint("archive_policy_id"),
    )

    for index_name, columns in [
        ("ix_symployee_record_archive_policies_tenant_id", ["tenant_id"]),
        ("ix_symployee_record_archive_policies_repository_id", ["repository_id"]),
        ("ix_symployee_record_archive_policies_business_area", ["business_area"]),
        ("ix_symployee_record_archive_policies_document_type", ["document_type"]),
        ("ix_symployee_record_archive_policies_policy_code", ["policy_code"]),
        ("ix_symployee_record_archive_policies_record_category_code", ["record_category_code"]),
        ("ix_symployee_record_archive_policies_transfer_required", ["transfer_required"]),
        ("ix_symployee_record_archive_policies_destination_code", ["destination_code"]),
        ("ix_symployee_record_archive_policies_package_format_code", ["package_format_code"]),
        ("ix_symployee_record_archive_policies_checksum_required", ["checksum_required"]),
        ("ix_symployee_record_archive_policies_metadata_profile_code", ["metadata_profile_code"]),
        ("ix_symployee_archive_policies_pres_review_days", ["preservation_review_interval_days"]),
        ("ix_symployee_archive_policies_receipt_confirm", ["receipt_confirmation_required"]),
        ("ix_symployee_record_archive_policies_status", ["status"]),
        ("ix_symployee_record_archive_policies_effective_from", ["effective_from"]),
        ("ix_symployee_record_archive_policies_effective_to", ["effective_to"]),
        ("ix_symployee_record_archive_policies_is_current_version", ["is_current_version"]),
        ("ix_symployee_record_archive_policies_rule_priority", ["rule_priority"]),
    ]:
        op.create_index(index_name, "symployee_record_archive_policies", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_record_archive_policies_rule_priority",
        "ix_symployee_record_archive_policies_is_current_version",
        "ix_symployee_record_archive_policies_effective_to",
        "ix_symployee_record_archive_policies_effective_from",
        "ix_symployee_record_archive_policies_status",
        "ix_symployee_archive_policies_receipt_confirm",
        "ix_symployee_archive_policies_pres_review_days",
        "ix_symployee_record_archive_policies_metadata_profile_code",
        "ix_symployee_record_archive_policies_checksum_required",
        "ix_symployee_record_archive_policies_package_format_code",
        "ix_symployee_record_archive_policies_destination_code",
        "ix_symployee_record_archive_policies_transfer_required",
        "ix_symployee_record_archive_policies_record_category_code",
        "ix_symployee_record_archive_policies_policy_code",
        "ix_symployee_record_archive_policies_document_type",
        "ix_symployee_record_archive_policies_business_area",
        "ix_symployee_record_archive_policies_repository_id",
        "ix_symployee_record_archive_policies_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_record_archive_policies")

    op.drop_table("symployee_record_archive_policies")
