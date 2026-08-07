"""add excluded domains to bd search profiles

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-07 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bd_search_profiles",
        sa.Column("excluded_domains_json", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.alter_column("bd_search_profiles", "excluded_domains_json", server_default=None)


def downgrade() -> None:
    op.drop_column("bd_search_profiles", "excluded_domains_json")
