"""add config linkage to symployee record declarations

Revision ID: e8f9a0b1c2d3
Revises: d5f6a7b8c9d
Create Date: 2026-07-18 18:55:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e8f9a0b1c2d3"
down_revision = "d5f6a7b8c9d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "symployee_record_declarations",
        sa.Column("declaration_rule_id", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_record_declarations",
        sa.Column("lifecycle_rule_id", sa.String(), nullable=True),
    )
    op.add_column(
        "symployee_record_declarations",
        sa.Column("retention_schedule_id", sa.String(), nullable=True),
    )

    op.create_foreign_key(
        "fk_srd_declaration_rule_id",
        "symployee_record_declarations",
        "symployee_record_declaration_rules",
        ["declaration_rule_id"],
        ["declaration_rule_id"],
    )
    op.create_foreign_key(
        "fk_srd_lifecycle_rule_id",
        "symployee_record_declarations",
        "symployee_record_lifecycle_rules",
        ["lifecycle_rule_id"],
        ["lifecycle_rule_id"],
    )
    op.create_foreign_key(
        "fk_srd_retention_schedule_id",
        "symployee_record_declarations",
        "symployee_retention_schedules",
        ["retention_schedule_id"],
        ["retention_schedule_id"],
    )

    op.create_index(
        "ix_symployee_record_declarations_declaration_rule_id",
        "symployee_record_declarations",
        ["declaration_rule_id"],
        unique=False,
    )
    op.create_index(
        "ix_symployee_record_declarations_lifecycle_rule_id",
        "symployee_record_declarations",
        ["lifecycle_rule_id"],
        unique=False,
    )
    op.create_index(
        "ix_symployee_record_declarations_retention_schedule_id",
        "symployee_record_declarations",
        ["retention_schedule_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_symployee_record_declarations_retention_schedule_id",
        table_name="symployee_record_declarations",
    )
    op.drop_index(
        "ix_symployee_record_declarations_lifecycle_rule_id",
        table_name="symployee_record_declarations",
    )
    op.drop_index(
        "ix_symployee_record_declarations_declaration_rule_id",
        table_name="symployee_record_declarations",
    )

    op.drop_constraint(
        "fk_srd_retention_schedule_id",
        "symployee_record_declarations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_srd_lifecycle_rule_id",
        "symployee_record_declarations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_srd_declaration_rule_id",
        "symployee_record_declarations",
        type_="foreignkey",
    )

    op.drop_column("symployee_record_declarations", "retention_schedule_id")
    op.drop_column("symployee_record_declarations", "lifecycle_rule_id")
    op.drop_column("symployee_record_declarations", "declaration_rule_id")
