"""Add Symployee record hold policies configuration table.

Revision ID: d2c3d4e5f6a
Revises: d1b2c3d4e5f
Create Date: 2026-07-18 17:14:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2c3d4e5f6a"
down_revision: Union[str, Sequence[str], None] = "d1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_record_hold_policies",
        sa.Column("hold_policy_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("repository_id", sa.String(), nullable=True),
        sa.Column("business_area", sa.String(), nullable=True),
        sa.Column("document_type", sa.String(), nullable=True),
        sa.Column("policy_code", sa.String(), nullable=False),
        sa.Column("policy_name", sa.String(), nullable=False),
        sa.Column("policy_description", sa.Text(), nullable=True),
        sa.Column("record_category_code", sa.String(), nullable=True),
        sa.Column("hold_category", sa.String(), nullable=False),
        sa.Column("placement_role_code", sa.String(), nullable=False),
        sa.Column("release_role_code", sa.String(), nullable=True),
        sa.Column("matter_reference_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reason_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("blocks_disposition", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("blocks_archive_transfer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("default_expiry_mode", sa.String(), nullable=True),
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
            "hold_category in ('LEGAL', 'VALIDATION', 'RECORDS', 'OPERATIONAL', 'OTHER')",
            name="ck_symployee_record_hold_policies_hold_category",
        ),
        sa.CheckConstraint(
            "default_expiry_mode is null or default_expiry_mode in ('NONE', 'FIXED_DATE', 'REVIEW_DATE')",
            name="ck_symployee_record_hold_policies_expiry_mode",
        ),
        sa.CheckConstraint(
            "status in ('DRAFT', 'ACTIVE', 'INACTIVE', 'RETIRED')",
            name="ck_symployee_record_hold_policies_status",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.repository_id"]),
        sa.PrimaryKeyConstraint("hold_policy_id"),
    )

    for index_name, columns in [
        ("ix_symployee_record_hold_policies_tenant_id", ["tenant_id"]),
        ("ix_symployee_record_hold_policies_repository_id", ["repository_id"]),
        ("ix_symployee_record_hold_policies_business_area", ["business_area"]),
        ("ix_symployee_record_hold_policies_document_type", ["document_type"]),
        ("ix_symployee_record_hold_policies_policy_code", ["policy_code"]),
        ("ix_symployee_record_hold_policies_record_category_code", ["record_category_code"]),
        ("ix_symployee_record_hold_policies_hold_category", ["hold_category"]),
        ("ix_symployee_record_hold_policies_placement_role_code", ["placement_role_code"]),
        ("ix_symployee_record_hold_policies_release_role_code", ["release_role_code"]),
        ("ix_symployee_record_hold_policies_matter_reference_required", ["matter_reference_required"]),
        ("ix_symployee_record_hold_policies_reason_required", ["reason_required"]),
        ("ix_symployee_record_hold_policies_blocks_disposition", ["blocks_disposition"]),
        ("ix_symployee_record_hold_policies_blocks_archive_transfer", ["blocks_archive_transfer"]),
        ("ix_symployee_record_hold_policies_default_expiry_mode", ["default_expiry_mode"]),
        ("ix_symployee_record_hold_policies_status", ["status"]),
        ("ix_symployee_record_hold_policies_effective_from", ["effective_from"]),
        ("ix_symployee_record_hold_policies_effective_to", ["effective_to"]),
        ("ix_symployee_record_hold_policies_is_current_version", ["is_current_version"]),
        ("ix_symployee_record_hold_policies_rule_priority", ["rule_priority"]),
    ]:
        op.create_index(index_name, "symployee_record_hold_policies", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_record_hold_policies_rule_priority",
        "ix_symployee_record_hold_policies_is_current_version",
        "ix_symployee_record_hold_policies_effective_to",
        "ix_symployee_record_hold_policies_effective_from",
        "ix_symployee_record_hold_policies_status",
        "ix_symployee_record_hold_policies_default_expiry_mode",
        "ix_symployee_record_hold_policies_blocks_archive_transfer",
        "ix_symployee_record_hold_policies_blocks_disposition",
        "ix_symployee_record_hold_policies_reason_required",
        "ix_symployee_record_hold_policies_matter_reference_required",
        "ix_symployee_record_hold_policies_release_role_code",
        "ix_symployee_record_hold_policies_placement_role_code",
        "ix_symployee_record_hold_policies_hold_category",
        "ix_symployee_record_hold_policies_record_category_code",
        "ix_symployee_record_hold_policies_policy_code",
        "ix_symployee_record_hold_policies_document_type",
        "ix_symployee_record_hold_policies_business_area",
        "ix_symployee_record_hold_policies_repository_id",
        "ix_symployee_record_hold_policies_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_record_hold_policies")

    op.drop_table("symployee_record_hold_policies")
