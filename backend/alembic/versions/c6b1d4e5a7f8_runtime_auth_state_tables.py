"""runtime auth state tables

Revision ID: c6b1d4e5a7f8
Revises: 9af781b967f6
Create Date: 2026-06-26 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c6b1d4e5a7f8"
down_revision: Union[str, Sequence[str], None] = "9af781b967f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS runtime_auth_state (
                state_name VARCHAR PRIMARY KEY,
                state_json JSONB NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS runtime_auth_challenges (
                store_name VARCHAR PRIMARY KEY,
                store_json JSONB NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS runtime_auth_challenges"))
    op.execute(sa.text("DROP TABLE IF EXISTS runtime_auth_state"))
