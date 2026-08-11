"""add discovery content normalization

Revision ID: d2b3c4d5e6f7
Revises: c1a2b3d4e5f7
Create Date: 2026-08-09 13:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d2b3c4d5e6f7"
down_revision = "c1a2b3d4e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bd_discovered_opportunities",
        sa.Column("normalized_content_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.alter_column("bd_discovered_opportunities", "normalized_content_json", server_default=None)


def downgrade() -> None:
    op.drop_column("bd_discovered_opportunities", "normalized_content_json")
