"""Add Symployee record assignment rules configuration table.

Revision ID: d5f6a7b8c9d
Revises: d4e5f6a7b8c
Create Date: 2026-07-18 17:42:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5f6a7b8c9d"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_record_assignment_rules",
        sa.Column("assignment_rule_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("repository_id", sa.String(), nullable=True),
        sa.Column("business_area", sa.String(), nullable=True),
        sa.Column("document_type", sa.String(), nullable=True),
        sa.Column("rule_code", sa.String(), nullable=False),
        sa.Column("rule_name", sa.String(), nullable=False),
        sa.Column("rule_description", sa.Text(), nullable=True),
        sa.Column("record_category_code", sa.String(), nullable=True),
        sa.Column("assignment_context", sa.String(), nullable=False),
        sa.Column("owner_role_code", sa.String(), nullable=True),
        sa.Column("performer_role_code", sa.String(), nullable=True),
        sa.Column("approver_role_code", sa.String(), nullable=True),
        sa.Column("escalation_role_code", sa.String(), nullable=True),
        sa.Column("fallback_role_code", sa.String(), nullable=True),
        sa.Column("assignment_logic_json", sa.JSON(), nullable=True),
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
            "assignment_context in ('DECLARATION', 'VITAL_REVIEW', 'HOLD_PLACEMENT', 'RETENTION_REVIEW', 'DISPOSITION_APPROVAL', 'ARCHIVE_TRANSFER')",
            name="ck_symployee_record_assignment_rules_context",
        ),
        sa.CheckConstraint(
            "status in ('DRAFT', 'ACTIVE', 'INACTIVE', 'RETIRED')",
            name="ck_symployee_record_assignment_rules_status",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.repository_id"]),
        sa.PrimaryKeyConstraint("assignment_rule_id"),
    )

    for index_name, columns in [
        ("ix_symployee_record_assignment_rules_tenant_id", ["tenant_id"]),
        ("ix_symployee_record_assignment_rules_repository_id", ["repository_id"]),
        ("ix_symployee_record_assignment_rules_business_area", ["business_area"]),
        ("ix_symployee_record_assignment_rules_document_type", ["document_type"]),
        ("ix_symployee_record_assignment_rules_rule_code", ["rule_code"]),
        ("ix_symployee_record_assignment_rules_record_category_code", ["record_category_code"]),
        ("ix_symployee_record_assignment_rules_assignment_context", ["assignment_context"]),
        ("ix_symployee_record_assignment_rules_owner_role_code", ["owner_role_code"]),
        ("ix_symployee_record_assignment_rules_perf_role_code", ["performer_role_code"]),
        ("ix_symployee_record_assignment_rules_appr_role_code", ["approver_role_code"]),
        ("ix_symployee_record_assignment_rules_esc_role_code", ["escalation_role_code"]),
        ("ix_symployee_record_assignment_rules_fallback_role", ["fallback_role_code"]),
        ("ix_symployee_record_assignment_rules_status", ["status"]),
        ("ix_symployee_record_assignment_rules_effective_from", ["effective_from"]),
        ("ix_symployee_record_assignment_rules_effective_to", ["effective_to"]),
        ("ix_symployee_record_assignment_rules_is_current_version", ["is_current_version"]),
        ("ix_symployee_record_assignment_rules_rule_priority", ["rule_priority"]),
    ]:
        op.create_index(index_name, "symployee_record_assignment_rules", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_record_assignment_rules_rule_priority",
        "ix_symployee_record_assignment_rules_is_current_version",
        "ix_symployee_record_assignment_rules_effective_to",
        "ix_symployee_record_assignment_rules_effective_from",
        "ix_symployee_record_assignment_rules_status",
        "ix_symployee_record_assignment_rules_fallback_role",
        "ix_symployee_record_assignment_rules_esc_role_code",
        "ix_symployee_record_assignment_rules_appr_role_code",
        "ix_symployee_record_assignment_rules_perf_role_code",
        "ix_symployee_record_assignment_rules_owner_role_code",
        "ix_symployee_record_assignment_rules_assignment_context",
        "ix_symployee_record_assignment_rules_record_category_code",
        "ix_symployee_record_assignment_rules_rule_code",
        "ix_symployee_record_assignment_rules_document_type",
        "ix_symployee_record_assignment_rules_business_area",
        "ix_symployee_record_assignment_rules_repository_id",
        "ix_symployee_record_assignment_rules_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_record_assignment_rules")

    op.drop_table("symployee_record_assignment_rules")
