"""Add Symployee record legal holds table.

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-07-14 22:21:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_record_legal_holds",
        sa.Column("legal_hold_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("identity_id", sa.String(), nullable=False),
        sa.Column("record_declaration_id", sa.String(), nullable=True),
        sa.Column("hold_code", sa.String(), nullable=False),
        sa.Column("hold_status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("authority", sa.String(), nullable=False),
        sa.Column("matter_reference", sa.String(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("placed_by", sa.String(), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by", sa.String(), nullable=True),
        sa.Column("release_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["identity_id"], ["symployee_document_identities.identity_id"]),
        sa.ForeignKeyConstraint(["placed_by"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["record_declaration_id"], ["symployee_record_declarations.record_declaration_id"]),
        sa.ForeignKeyConstraint(["released_by"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("legal_hold_id"),
    )

    for index_name, columns in [
        ("ix_symployee_record_legal_holds_tenant_id", ["tenant_id"]),
        ("ix_symployee_record_legal_holds_identity_id", ["identity_id"]),
        ("ix_symployee_record_legal_holds_record_declaration_id", ["record_declaration_id"]),
        ("ix_symployee_record_legal_holds_hold_code", ["hold_code"]),
        ("ix_symployee_record_legal_holds_hold_status", ["hold_status"]),
        ("ix_symployee_record_legal_holds_authority", ["authority"]),
        ("ix_symployee_record_legal_holds_placed_by", ["placed_by"]),
        ("ix_symployee_record_legal_holds_released_by", ["released_by"]),
        ("ix_symployee_record_legal_holds_placed_at", ["placed_at"]),
    ]:
        op.create_index(index_name, "symployee_record_legal_holds", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_record_legal_holds_placed_at",
        "ix_symployee_record_legal_holds_released_by",
        "ix_symployee_record_legal_holds_placed_by",
        "ix_symployee_record_legal_holds_authority",
        "ix_symployee_record_legal_holds_hold_status",
        "ix_symployee_record_legal_holds_hold_code",
        "ix_symployee_record_legal_holds_record_declaration_id",
        "ix_symployee_record_legal_holds_identity_id",
        "ix_symployee_record_legal_holds_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_record_legal_holds")

    op.drop_table("symployee_record_legal_holds")
