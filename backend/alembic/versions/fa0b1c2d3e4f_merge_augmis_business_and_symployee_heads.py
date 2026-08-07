"""Merge AUGMIS Business and symployee migration heads.

Revision ID: fa0b1c2d3e4f
Revises: ee5f6a7b8c9d, f9b0c1d2e3f4
Create Date: 2026-08-06 12:20:00
"""

from typing import Sequence, Union


revision: str = "fa0b1c2d3e4f"
down_revision: Union[str, Sequence[str], None] = ("ee5f6a7b8c9d", "f9b0c1d2e3f4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
