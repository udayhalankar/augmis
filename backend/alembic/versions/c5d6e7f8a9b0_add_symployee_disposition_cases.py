"""Add Symployee disposition cases table.

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-07-14 22:25:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_disposition_cases",
        sa.Column("disposition_case_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("identity_id", sa.String(), nullable=False),
        sa.Column("record_declaration_id", sa.String(), nullable=True),
        sa.Column("retention_rule_id", sa.String(), nullable=True),
        sa.Column("disposition_type", sa.String(), nullable=False),
        sa.Column("case_status", sa.String(), nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("eligibility_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("requested_by", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_by", sa.String(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("outcome_notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["approved_by"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["executed_by"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["identity_id"], ["symployee_document_identities.identity_id"]),
        sa.ForeignKeyConstraint(["record_declaration_id"], ["symployee_record_declarations.record_declaration_id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["retention_rule_id"], ["symployee_retention_rules.retention_rule_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("disposition_case_id"),
    )

    for index_name, columns in [
        ("ix_symployee_disposition_cases_tenant_id", ["tenant_id"]),
        ("ix_symployee_disposition_cases_identity_id", ["identity_id"]),
        ("ix_symployee_disposition_cases_record_declaration_id", ["record_declaration_id"]),
        ("ix_symployee_disposition_cases_retention_rule_id", ["retention_rule_id"]),
        ("ix_symployee_disposition_cases_disposition_type", ["disposition_type"]),
        ("ix_symployee_disposition_cases_case_status", ["case_status"]),
        ("ix_symployee_disposition_cases_eligibility_date", ["eligibility_date"]),
        ("ix_symployee_disposition_cases_requested_by", ["requested_by"]),
        ("ix_symployee_disposition_cases_approved_by", ["approved_by"]),
        ("ix_symployee_disposition_cases_executed_by", ["executed_by"]),
    ]:
        op.create_index(index_name, "symployee_disposition_cases", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_disposition_cases_executed_by",
        "ix_symployee_disposition_cases_approved_by",
        "ix_symployee_disposition_cases_requested_by",
        "ix_symployee_disposition_cases_eligibility_date",
        "ix_symployee_disposition_cases_case_status",
        "ix_symployee_disposition_cases_disposition_type",
        "ix_symployee_disposition_cases_retention_rule_id",
        "ix_symployee_disposition_cases_record_declaration_id",
        "ix_symployee_disposition_cases_identity_id",
        "ix_symployee_disposition_cases_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_disposition_cases")

    op.drop_table("symployee_disposition_cases")
