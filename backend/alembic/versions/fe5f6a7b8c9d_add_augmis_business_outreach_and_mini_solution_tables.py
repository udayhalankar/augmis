"""Add AUGMIS Business outreach and mini-solution tables.

Revision ID: fe5f6a7b8c9d
Revises: fd4e5f6a7b8c
Create Date: 2026-08-07 21:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fe5f6a7b8c9d"
down_revision: Union[str, Sequence[str], None] = "fd4e5f6a7b8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bd_outreach_drafts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("opportunity_id", sa.String(), nullable=False),
        sa.Column("lead_id", sa.String(), nullable=True),
        sa.Column("prospect_id", sa.String(), nullable=True),
        sa.Column("contact_id", sa.String(), nullable=True),
        sa.Column("outreach_type", sa.String(), nullable=False),
        sa.Column("tone", sa.String(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("structured_content_json", sa.JSON(), nullable=False),
        sa.Column("generation_version", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_bundle_version", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["bd_contacts.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["bd_leads.id"]),
        sa.ForeignKeyConstraint(["opportunity_id"], ["bd_opportunities.id"]),
        sa.ForeignKeyConstraint(["prospect_id"], ["bd_prospects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "opportunity_id",
            "lead_id",
            "outreach_type",
            "generation_version",
            name="uq_bd_outreach_draft_generation_version",
        ),
    )
    op.create_index("ix_bd_outreach_drafts_tenant_id", "bd_outreach_drafts", ["tenant_id"], unique=False)
    op.create_index("ix_bd_outreach_drafts_opportunity_id", "bd_outreach_drafts", ["opportunity_id"], unique=False)
    op.create_index("ix_bd_outreach_drafts_lead_id", "bd_outreach_drafts", ["lead_id"], unique=False)
    op.create_index("ix_bd_outreach_drafts_prospect_id", "bd_outreach_drafts", ["prospect_id"], unique=False)
    op.create_index("ix_bd_outreach_drafts_contact_id", "bd_outreach_drafts", ["contact_id"], unique=False)
    op.create_index("ix_bd_outreach_drafts_outreach_type", "bd_outreach_drafts", ["outreach_type"], unique=False)
    op.create_index("ix_bd_outreach_drafts_tone", "bd_outreach_drafts", ["tone"], unique=False)
    op.create_index("ix_bd_outreach_drafts_status", "bd_outreach_drafts", ["status"], unique=False)
    op.create_index(
        "ix_bd_outreach_drafts_tenant_scope_created",
        "bd_outreach_drafts",
        ["tenant_id", "opportunity_id", "lead_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "bd_mini_solutions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("opportunity_id", sa.String(), nullable=False),
        sa.Column("lead_id", sa.String(), nullable=True),
        sa.Column("assessment_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("solution_json", sa.JSON(), nullable=False),
        sa.Column("generation_version", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_bundle_version", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["bd_opportunity_ai_assessments.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["bd_leads.id"]),
        sa.ForeignKeyConstraint(["opportunity_id"], ["bd_opportunities.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "opportunity_id",
            "lead_id",
            "generation_version",
            name="uq_bd_mini_solution_generation_version",
        ),
    )
    op.create_index("ix_bd_mini_solutions_tenant_id", "bd_mini_solutions", ["tenant_id"], unique=False)
    op.create_index("ix_bd_mini_solutions_opportunity_id", "bd_mini_solutions", ["opportunity_id"], unique=False)
    op.create_index("ix_bd_mini_solutions_lead_id", "bd_mini_solutions", ["lead_id"], unique=False)
    op.create_index("ix_bd_mini_solutions_assessment_id", "bd_mini_solutions", ["assessment_id"], unique=False)
    op.create_index("ix_bd_mini_solutions_status", "bd_mini_solutions", ["status"], unique=False)
    op.create_index(
        "ix_bd_mini_solutions_tenant_scope_created",
        "bd_mini_solutions",
        ["tenant_id", "opportunity_id", "lead_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bd_mini_solutions_tenant_scope_created", table_name="bd_mini_solutions")
    op.drop_index("ix_bd_mini_solutions_status", table_name="bd_mini_solutions")
    op.drop_index("ix_bd_mini_solutions_assessment_id", table_name="bd_mini_solutions")
    op.drop_index("ix_bd_mini_solutions_lead_id", table_name="bd_mini_solutions")
    op.drop_index("ix_bd_mini_solutions_opportunity_id", table_name="bd_mini_solutions")
    op.drop_index("ix_bd_mini_solutions_tenant_id", table_name="bd_mini_solutions")
    op.drop_table("bd_mini_solutions")

    op.drop_index("ix_bd_outreach_drafts_tenant_scope_created", table_name="bd_outreach_drafts")
    op.drop_index("ix_bd_outreach_drafts_status", table_name="bd_outreach_drafts")
    op.drop_index("ix_bd_outreach_drafts_tone", table_name="bd_outreach_drafts")
    op.drop_index("ix_bd_outreach_drafts_outreach_type", table_name="bd_outreach_drafts")
    op.drop_index("ix_bd_outreach_drafts_contact_id", table_name="bd_outreach_drafts")
    op.drop_index("ix_bd_outreach_drafts_prospect_id", table_name="bd_outreach_drafts")
    op.drop_index("ix_bd_outreach_drafts_lead_id", table_name="bd_outreach_drafts")
    op.drop_index("ix_bd_outreach_drafts_opportunity_id", table_name="bd_outreach_drafts")
    op.drop_index("ix_bd_outreach_drafts_tenant_id", table_name="bd_outreach_drafts")
    op.drop_table("bd_outreach_drafts")
