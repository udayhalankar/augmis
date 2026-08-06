"""Add Symployee record categories configuration table.

Revision ID: c7d8e9f0a1b
Revises: b6c7d8e9f0a
Create Date: 2026-07-18 16:28:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7d8e9f0a1b"
down_revision: Union[str, Sequence[str], None] = "b6c7d8e9f0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_record_categories",
        sa.Column("record_category_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("repository_id", sa.String(), nullable=True),
        sa.Column("business_area", sa.String(), nullable=True),
        sa.Column("document_type", sa.String(), nullable=True),
        sa.Column("category_code", sa.String(), nullable=False),
        sa.Column("category_name", sa.String(), nullable=False),
        sa.Column("category_description", sa.Text(), nullable=True),
        sa.Column("parent_category_code", sa.String(), nullable=True),
        sa.Column("security_classification_default", sa.String(), nullable=True),
        sa.Column("retention_schedule_code_default", sa.String(), nullable=True),
        sa.Column("vital_policy_code_default", sa.String(), nullable=True),
        sa.Column("hold_policy_code_default", sa.String(), nullable=True),
        sa.Column("disposition_policy_code_default", sa.String(), nullable=True),
        sa.Column("archive_policy_code_default", sa.String(), nullable=True),
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
            name="ck_symployee_record_categories_status",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.repository_id"]),
        sa.PrimaryKeyConstraint("record_category_id"),
    )

    for index_name, columns in [
        ("ix_symployee_record_categories_tenant_id", ["tenant_id"]),
        ("ix_symployee_record_categories_repository_id", ["repository_id"]),
        ("ix_symployee_record_categories_business_area", ["business_area"]),
        ("ix_symployee_record_categories_document_type", ["document_type"]),
        ("ix_symployee_record_categories_category_code", ["category_code"]),
        ("ix_symployee_record_categories_parent_category_code", ["parent_category_code"]),
        ("ix_symployee_record_categories_status", ["status"]),
        ("ix_symployee_record_categories_effective_from", ["effective_from"]),
        ("ix_symployee_record_categories_effective_to", ["effective_to"]),
        ("ix_symployee_record_categories_is_current_version", ["is_current_version"]),
        ("ix_symployee_record_categories_rule_priority", ["rule_priority"]),
    ]:
        op.create_index(index_name, "symployee_record_categories", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_record_categories_rule_priority",
        "ix_symployee_record_categories_is_current_version",
        "ix_symployee_record_categories_effective_to",
        "ix_symployee_record_categories_effective_from",
        "ix_symployee_record_categories_status",
        "ix_symployee_record_categories_parent_category_code",
        "ix_symployee_record_categories_category_code",
        "ix_symployee_record_categories_document_type",
        "ix_symployee_record_categories_business_area",
        "ix_symployee_record_categories_repository_id",
        "ix_symployee_record_categories_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_record_categories")

    op.drop_table("symployee_record_categories")
