"""Add Symployee record disposition policies configuration table.

Revision ID: d3d4e5f6a7b
Revises: d2c3d4e5f6a
Create Date: 2026-07-18 17:23:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3d4e5f6a7b"
down_revision: Union[str, Sequence[str], None] = "d2c3d4e5f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_record_disposition_policies",
        sa.Column("disposition_policy_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("repository_id", sa.String(), nullable=True),
        sa.Column("business_area", sa.String(), nullable=True),
        sa.Column("document_type", sa.String(), nullable=True),
        sa.Column("policy_code", sa.String(), nullable=False),
        sa.Column("policy_name", sa.String(), nullable=False),
        sa.Column("policy_description", sa.Text(), nullable=True),
        sa.Column("record_category_code", sa.String(), nullable=True),
        sa.Column("allowed_outcome", sa.String(), nullable=False, server_default="MIXED"),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("records_approval_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("legal_approval_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("business_owner_approval_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("evidence_requirements_json", sa.JSON(), nullable=True),
        sa.Column("blocked_by_active_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("disposition_execution_role_code", sa.String(), nullable=False),
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
            "allowed_outcome in ('ARCHIVE', 'DESTROY', 'REVIEW_EXTEND', 'MIXED')",
            name="ck_symployee_record_disposition_policies_allowed_outcome",
        ),
        sa.CheckConstraint(
            "status in ('DRAFT', 'ACTIVE', 'INACTIVE', 'RETIRED')",
            name="ck_symployee_record_disposition_policies_status",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.repository_id"]),
        sa.PrimaryKeyConstraint("disposition_policy_id"),
    )

    for index_name, columns in [
        ("ix_symployee_record_disposition_policies_tenant_id", ["tenant_id"]),
        ("ix_symployee_record_disposition_policies_repository_id", ["repository_id"]),
        ("ix_symployee_record_disposition_policies_business_area", ["business_area"]),
        ("ix_symployee_record_disposition_policies_document_type", ["document_type"]),
        ("ix_symployee_record_disposition_policies_policy_code", ["policy_code"]),
        ("ix_symployee_record_disposition_policies_record_category_code", ["record_category_code"]),
        ("ix_symployee_record_disposition_policies_allowed_outcome", ["allowed_outcome"]),
        ("ix_symployee_disp_policies_approval_required", ["approval_required"]),
        ("ix_symployee_disp_policies_records_approval_req", ["records_approval_required"]),
        ("ix_symployee_disp_policies_legal_approval_req", ["legal_approval_required"]),
        ("ix_symployee_disp_policies_business_owner_req", ["business_owner_approval_required"]),
        ("ix_symployee_disp_policies_blocked_by_hold", ["blocked_by_active_hold"]),
        ("ix_symployee_disp_policies_execution_role", ["disposition_execution_role_code"]),
        ("ix_symployee_record_disposition_policies_status", ["status"]),
        ("ix_symployee_record_disposition_policies_effective_from", ["effective_from"]),
        ("ix_symployee_record_disposition_policies_effective_to", ["effective_to"]),
        ("ix_symployee_record_disposition_policies_is_current_version", ["is_current_version"]),
        ("ix_symployee_record_disposition_policies_rule_priority", ["rule_priority"]),
    ]:
        op.create_index(index_name, "symployee_record_disposition_policies", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_record_disposition_policies_rule_priority",
        "ix_symployee_record_disposition_policies_is_current_version",
        "ix_symployee_record_disposition_policies_effective_to",
        "ix_symployee_record_disposition_policies_effective_from",
        "ix_symployee_record_disposition_policies_status",
        "ix_symployee_disp_policies_execution_role",
        "ix_symployee_disp_policies_blocked_by_hold",
        "ix_symployee_disp_policies_business_owner_req",
        "ix_symployee_disp_policies_legal_approval_req",
        "ix_symployee_disp_policies_records_approval_req",
        "ix_symployee_disp_policies_approval_required",
        "ix_symployee_record_disposition_policies_allowed_outcome",
        "ix_symployee_record_disposition_policies_record_category_code",
        "ix_symployee_record_disposition_policies_policy_code",
        "ix_symployee_record_disposition_policies_document_type",
        "ix_symployee_record_disposition_policies_business_area",
        "ix_symployee_record_disposition_policies_repository_id",
        "ix_symployee_record_disposition_policies_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_record_disposition_policies")

    op.drop_table("symployee_record_disposition_policies")
