"""Add Symployee retention schedules configuration table.

Revision ID: d0a1b2c3d4e
Revises: c9f0a1b2c3d
Create Date: 2026-07-18 16:56:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d0a1b2c3d4e"
down_revision: Union[str, Sequence[str], None] = "c9f0a1b2c3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_retention_schedules",
        sa.Column("retention_schedule_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("repository_id", sa.String(), nullable=True),
        sa.Column("business_area", sa.String(), nullable=True),
        sa.Column("document_type", sa.String(), nullable=True),
        sa.Column("schedule_code", sa.String(), nullable=False),
        sa.Column("schedule_name", sa.String(), nullable=False),
        sa.Column("schedule_description", sa.Text(), nullable=True),
        sa.Column("record_category_code", sa.String(), nullable=True),
        sa.Column("retention_start_event", sa.String(), nullable=False),
        sa.Column("retention_period_value", sa.Integer(), nullable=False),
        sa.Column("retention_period_unit", sa.String(), nullable=False),
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("review_offset_value", sa.Integer(), nullable=True),
        sa.Column("review_offset_unit", sa.String(), nullable=True),
        sa.Column("suspend_on_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("final_disposition_policy_code", sa.String(), nullable=False),
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
            "retention_period_unit in ('DAYS', 'MONTHS', 'YEARS')",
            name="ck_symployee_retention_schedules_period_unit",
        ),
        sa.CheckConstraint(
            "review_offset_unit is null or review_offset_unit in ('DAYS', 'MONTHS', 'YEARS')",
            name="ck_symployee_retention_schedules_review_offset_unit",
        ),
        sa.CheckConstraint(
            "status in ('DRAFT', 'ACTIVE', 'INACTIVE', 'RETIRED')",
            name="ck_symployee_retention_schedules_status",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.repository_id"]),
        sa.PrimaryKeyConstraint("retention_schedule_id"),
    )

    for index_name, columns in [
        ("ix_symployee_retention_schedules_tenant_id", ["tenant_id"]),
        ("ix_symployee_retention_schedules_repository_id", ["repository_id"]),
        ("ix_symployee_retention_schedules_business_area", ["business_area"]),
        ("ix_symployee_retention_schedules_document_type", ["document_type"]),
        ("ix_symployee_retention_schedules_schedule_code", ["schedule_code"]),
        ("ix_symployee_retention_schedules_record_category_code", ["record_category_code"]),
        ("ix_symployee_retention_schedules_retention_start_event", ["retention_start_event"]),
        ("ix_symployee_retention_schedules_retention_period_value", ["retention_period_value"]),
        ("ix_symployee_retention_schedules_retention_period_unit", ["retention_period_unit"]),
        ("ix_symployee_retention_schedules_review_required", ["review_required"]),
        ("ix_symployee_retention_schedules_review_offset_value", ["review_offset_value"]),
        ("ix_symployee_retention_schedules_review_offset_unit", ["review_offset_unit"]),
        ("ix_symployee_retention_schedules_suspend_on_hold", ["suspend_on_hold"]),
        ("ix_symployee_retention_schedules_final_disposition_policy_code", ["final_disposition_policy_code"]),
        ("ix_symployee_retention_schedules_status", ["status"]),
        ("ix_symployee_retention_schedules_effective_from", ["effective_from"]),
        ("ix_symployee_retention_schedules_effective_to", ["effective_to"]),
        ("ix_symployee_retention_schedules_is_current_version", ["is_current_version"]),
        ("ix_symployee_retention_schedules_rule_priority", ["rule_priority"]),
    ]:
        op.create_index(index_name, "symployee_retention_schedules", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_retention_schedules_rule_priority",
        "ix_symployee_retention_schedules_is_current_version",
        "ix_symployee_retention_schedules_effective_to",
        "ix_symployee_retention_schedules_effective_from",
        "ix_symployee_retention_schedules_status",
        "ix_symployee_retention_schedules_final_disposition_policy_code",
        "ix_symployee_retention_schedules_suspend_on_hold",
        "ix_symployee_retention_schedules_review_offset_unit",
        "ix_symployee_retention_schedules_review_offset_value",
        "ix_symployee_retention_schedules_review_required",
        "ix_symployee_retention_schedules_retention_period_unit",
        "ix_symployee_retention_schedules_retention_period_value",
        "ix_symployee_retention_schedules_retention_start_event",
        "ix_symployee_retention_schedules_record_category_code",
        "ix_symployee_retention_schedules_schedule_code",
        "ix_symployee_retention_schedules_document_type",
        "ix_symployee_retention_schedules_business_area",
        "ix_symployee_retention_schedules_repository_id",
        "ix_symployee_retention_schedules_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_retention_schedules")

    op.drop_table("symployee_retention_schedules")
