"""Add Symployee policy scope fields.

Revision ID: d4e5f6a7b8c9
Revises: b3f1c2d4e5f6
Create Date: 2026-07-10 22:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "b3f1c2d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "symployee_policy_configs",
        sa.Column("scope_type", sa.String(), nullable=False, server_default="tenant"),
    )
    op.add_column(
        "symployee_policy_configs",
        sa.Column("scope_ref", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_symployee_policy_configs_scope_type",
        "symployee_policy_configs",
        ["scope_type"],
        unique=False,
    )
    op.create_index(
        "ix_symployee_policy_configs_scope_ref",
        "symployee_policy_configs",
        ["scope_ref"],
        unique=False,
    )
    op.drop_constraint(
        "uq_symployee_policy_version",
        "symployee_policy_configs",
        type_="unique",
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_symployee_policy_version
            ON symployee_policy_configs (
                tenant_id,
                symployee_code,
                policy_domain,
                policy_code,
                scope_type,
                COALESCE(scope_ref, ''),
                version_no
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_index("uq_symployee_policy_version", table_name="symployee_policy_configs")
    op.create_unique_constraint(
        "uq_symployee_policy_version",
        "symployee_policy_configs",
        [
            "tenant_id",
            "symployee_code",
            "policy_domain",
            "policy_code",
            "version_no",
        ],
    )
    op.drop_index("ix_symployee_policy_configs_scope_ref", table_name="symployee_policy_configs")
    op.drop_index("ix_symployee_policy_configs_scope_type", table_name="symployee_policy_configs")
    op.drop_column("symployee_policy_configs", "scope_ref")
    op.drop_column("symployee_policy_configs", "scope_type")
