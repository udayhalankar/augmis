"""Extend AUGMIS Business prospect and contact contract.

Revision ID: fc2d3e4f5a6b
Revises: fb1c2d3e4f5a
Create Date: 2026-08-07 14:15:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fc2d3e4f5a6b"
down_revision: Union[str, Sequence[str], None] = "fb1c2d3e4f5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bd_prospects", sa.Column("city", sa.String(), nullable=True))
    op.add_column("bd_prospects", sa.Column("organization_type", sa.String(), nullable=True))
    op.add_column("bd_prospects", sa.Column("employee_range", sa.String(), nullable=True))
    op.add_column("bd_prospects", sa.Column("general_email", sa.String(), nullable=True))
    op.add_column("bd_prospects", sa.Column("general_phone", sa.String(), nullable=True))
    op.add_column("bd_prospects", sa.Column("estimated_account_potential_min", sa.Float(), nullable=True))
    op.add_column("bd_prospects", sa.Column("estimated_account_potential_max", sa.Float(), nullable=True))
    op.add_column("bd_prospects", sa.Column("estimated_currency", sa.String(), nullable=True))
    op.create_index("ix_bd_prospects_city", "bd_prospects", ["city"], unique=False)
    op.create_index("ix_bd_prospects_organization_type", "bd_prospects", ["organization_type"], unique=False)
    op.create_index("ix_bd_prospects_general_email", "bd_prospects", ["general_email"], unique=False)

    op.alter_column("bd_contacts", "full_name", existing_type=sa.String(), nullable=True)
    op.add_column("bd_contacts", sa.Column("department", sa.String(), nullable=True))
    op.add_column("bd_contacts", sa.Column("buyer_role", sa.String(), nullable=True))
    op.add_column("bd_contacts", sa.Column("company_profile_url", sa.String(), nullable=True))
    op.add_column("bd_contacts", sa.Column("contact_source", sa.String(), nullable=True))
    op.add_column("bd_contacts", sa.Column("source_url", sa.String(), nullable=True))
    op.add_column("bd_contacts", sa.Column("evidence_text", sa.Text(), nullable=True))
    op.add_column(
        "bd_contacts",
        sa.Column("verification_status", sa.String(), nullable=False, server_default="unverified"),
    )
    op.add_column("bd_contacts", sa.Column("confidence_score", sa.Float(), nullable=True))
    op.create_index("ix_bd_contacts_buyer_role", "bd_contacts", ["buyer_role"], unique=False)
    op.create_index("ix_bd_contacts_verification_status", "bd_contacts", ["verification_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bd_contacts_verification_status", table_name="bd_contacts")
    op.drop_index("ix_bd_contacts_buyer_role", table_name="bd_contacts")
    op.drop_column("bd_contacts", "confidence_score")
    op.drop_column("bd_contacts", "verification_status")
    op.drop_column("bd_contacts", "evidence_text")
    op.drop_column("bd_contacts", "source_url")
    op.drop_column("bd_contacts", "contact_source")
    op.drop_column("bd_contacts", "company_profile_url")
    op.drop_column("bd_contacts", "buyer_role")
    op.drop_column("bd_contacts", "department")
    op.alter_column("bd_contacts", "full_name", existing_type=sa.String(), nullable=False)

    op.drop_index("ix_bd_prospects_general_email", table_name="bd_prospects")
    op.drop_index("ix_bd_prospects_organization_type", table_name="bd_prospects")
    op.drop_index("ix_bd_prospects_city", table_name="bd_prospects")
    op.drop_column("bd_prospects", "estimated_currency")
    op.drop_column("bd_prospects", "estimated_account_potential_max")
    op.drop_column("bd_prospects", "estimated_account_potential_min")
    op.drop_column("bd_prospects", "general_phone")
    op.drop_column("bd_prospects", "general_email")
    op.drop_column("bd_prospects", "employee_range")
    op.drop_column("bd_prospects", "organization_type")
    op.drop_column("bd_prospects", "city")
