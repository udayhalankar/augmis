"""Add Symployee record lifecycle rules configuration table.

Revision ID: c9f0a1b2c3d
Revises: c8e9f0a1b2c
Create Date: 2026-07-18 16:48:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9f0a1b2c3d"
down_revision: Union[str, Sequence[str], None] = "c8e9f0a1b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_record_lifecycle_rules",
        sa.Column("lifecycle_rule_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("repository_id", sa.String(), nullable=True),
        sa.Column("business_area", sa.String(), nullable=True),
        sa.Column("document_type", sa.String(), nullable=True),
        sa.Column("rule_code", sa.String(), nullable=False),
        sa.Column("rule_name", sa.String(), nullable=False),
        sa.Column("rule_description", sa.Text(), nullable=True),
        sa.Column("record_category_code", sa.String(), nullable=True),
        sa.Column("active_start_event", sa.String(), nullable=False),
        sa.Column("inactive_eligibility_event", sa.String(), nullable=False),
        sa.Column("inactive_after_days", sa.Integer(), nullable=True),
        sa.Column("inactive_override_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reopen_to_active_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reopen_trigger_events_json", sa.JSON(), nullable=True),
        sa.Column("lifecycle_clock_basis", sa.String(), nullable=True),
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
            name="ck_symployee_record_lifecycle_rules_status",
        ),
        sa.CheckConstraint(
            "lifecycle_clock_basis is null or lifecycle_clock_basis in ('DECLARATION_DATE', 'WORKFLOW_COMPLETE_DATE', 'LAST_ACTIVITY_DATE')",
            name="ck_symployee_record_lifecycle_rules_clock_basis",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.repository_id"]),
        sa.PrimaryKeyConstraint("lifecycle_rule_id"),
    )

    for index_name, columns in [
        ("ix_symployee_record_lifecycle_rules_tenant_id", ["tenant_id"]),
        ("ix_symployee_record_lifecycle_rules_repository_id", ["repository_id"]),
        ("ix_symployee_record_lifecycle_rules_business_area", ["business_area"]),
        ("ix_symployee_record_lifecycle_rules_document_type", ["document_type"]),
        ("ix_symployee_record_lifecycle_rules_rule_code", ["rule_code"]),
        ("ix_symployee_record_lifecycle_rules_record_category_code", ["record_category_code"]),
        ("ix_symployee_record_lifecycle_rules_active_start_event", ["active_start_event"]),
        ("ix_symployee_record_lifecycle_rules_inactive_eligibility_event", ["inactive_eligibility_event"]),
        ("ix_symployee_record_lifecycle_rules_inactive_after_days", ["inactive_after_days"]),
        ("ix_symployee_record_lifecycle_rules_inactive_override_required", ["inactive_override_required"]),
        ("ix_symployee_record_lifecycle_rules_reopen_to_active_allowed", ["reopen_to_active_allowed"]),
        ("ix_symployee_record_lifecycle_rules_lifecycle_clock_basis", ["lifecycle_clock_basis"]),
        ("ix_symployee_record_lifecycle_rules_status", ["status"]),
        ("ix_symployee_record_lifecycle_rules_effective_from", ["effective_from"]),
        ("ix_symployee_record_lifecycle_rules_effective_to", ["effective_to"]),
        ("ix_symployee_record_lifecycle_rules_is_current_version", ["is_current_version"]),
        ("ix_symployee_record_lifecycle_rules_rule_priority", ["rule_priority"]),
    ]:
        op.create_index(index_name, "symployee_record_lifecycle_rules", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_record_lifecycle_rules_rule_priority",
        "ix_symployee_record_lifecycle_rules_is_current_version",
        "ix_symployee_record_lifecycle_rules_effective_to",
        "ix_symployee_record_lifecycle_rules_effective_from",
        "ix_symployee_record_lifecycle_rules_status",
        "ix_symployee_record_lifecycle_rules_lifecycle_clock_basis",
        "ix_symployee_record_lifecycle_rules_reopen_to_active_allowed",
        "ix_symployee_record_lifecycle_rules_inactive_override_required",
        "ix_symployee_record_lifecycle_rules_inactive_after_days",
        "ix_symployee_record_lifecycle_rules_inactive_eligibility_event",
        "ix_symployee_record_lifecycle_rules_active_start_event",
        "ix_symployee_record_lifecycle_rules_record_category_code",
        "ix_symployee_record_lifecycle_rules_rule_code",
        "ix_symployee_record_lifecycle_rules_document_type",
        "ix_symployee_record_lifecycle_rules_business_area",
        "ix_symployee_record_lifecycle_rules_repository_id",
        "ix_symployee_record_lifecycle_rules_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_record_lifecycle_rules")

    op.drop_table("symployee_record_lifecycle_rules")
