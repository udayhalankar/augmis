"""Add reporting domain to repositories

Revision ID: 6d3c9dbd4b2e
Revises: 9af781b967f6
Create Date: 2026-06-10 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6d3c9dbd4b2e"
down_revision: Union[str, Sequence[str], None] = "9af781b967f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "repositories",
        sa.Column("reporting_domain", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("repositories", "reporting_domain")
