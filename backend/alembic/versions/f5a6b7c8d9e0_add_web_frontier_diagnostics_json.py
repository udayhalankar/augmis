"""add web frontier diagnostics json

Revision ID: f5a6b7c8d9e0
Revises: a8d9e0f1a2b3
Create Date: 2026-08-11 19:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f5a6b7c8d9e0"
down_revision = "a8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bd_web_frontier",
        sa.Column("diagnostic_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.alter_column("bd_web_frontier", "diagnostic_json", server_default=None)


def downgrade() -> None:
    op.drop_column("bd_web_frontier", "diagnostic_json")
