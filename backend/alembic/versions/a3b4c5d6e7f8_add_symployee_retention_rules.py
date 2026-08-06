"""Add Symployee retention rules table.

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-07-14 22:17:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_retention_rules",
        sa.Column("retention_rule_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("rule_code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("record_category", sa.String(), nullable=False),
        sa.Column("trigger_event", sa.String(), nullable=False),
        sa.Column("retention_period_value", sa.Integer(), nullable=False),
        sa.Column("retention_period_unit", sa.String(), nullable=False, server_default="YEARS"),
        sa.Column("disposition_action", sa.String(), nullable=False),
        sa.Column("approver_role_code", sa.String(), nullable=True),
        sa.Column("legal_authority", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("scope_type", sa.String(), nullable=False, server_default="tenant"),
        sa.Column("scope_ref", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("retention_rule_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "rule_code",
            "scope_type",
            "scope_ref",
            name="uq_symployee_retention_rule_scope",
        ),
    )

    for index_name, columns in [
        ("ix_symployee_retention_rules_tenant_id", ["tenant_id"]),
        ("ix_symployee_retention_rules_rule_code", ["rule_code"]),
        ("ix_symployee_retention_rules_record_category", ["record_category"]),
        ("ix_symployee_retention_rules_trigger_event", ["trigger_event"]),
        ("ix_symployee_retention_rules_disposition_action", ["disposition_action"]),
        ("ix_symployee_retention_rules_status", ["status"]),
        ("ix_symployee_retention_rules_scope_type", ["scope_type"]),
        ("ix_symployee_retention_rules_scope_ref", ["scope_ref"]),
    ]:
        op.create_index(index_name, "symployee_retention_rules", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_retention_rules_scope_ref",
        "ix_symployee_retention_rules_scope_type",
        "ix_symployee_retention_rules_status",
        "ix_symployee_retention_rules_disposition_action",
        "ix_symployee_retention_rules_trigger_event",
        "ix_symployee_retention_rules_record_category",
        "ix_symployee_retention_rules_rule_code",
        "ix_symployee_retention_rules_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_retention_rules")

    op.drop_table("symployee_retention_rules")
