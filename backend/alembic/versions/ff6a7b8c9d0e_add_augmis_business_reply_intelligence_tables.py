"""add augmis business reply intelligence tables

Revision ID: ff6a7b8c9d0e
Revises: fe5f6a7b8c9d
Create Date: 2026-08-07 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "ff6a7b8c9d0e"
down_revision = "fe5f6a7b8c9d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bd_replies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("opportunity_id", sa.String(), nullable=True),
        sa.Column("lead_id", sa.String(), nullable=False),
        sa.Column("prospect_id", sa.String(), nullable=True),
        sa.Column("contact_id", sa.String(), nullable=True),
        sa.Column("outreach_id", sa.String(), nullable=True),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=True),
        sa.Column("raw_message", sa.Text(), nullable=False),
        sa.Column("sender_display", sa.String(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reply_status", sa.String(), nullable=False, server_default="received"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["contact_id"], ["bd_contacts.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["bd_leads.id"]),
        sa.ForeignKeyConstraint(["opportunity_id"], ["bd_opportunities.id"]),
        sa.ForeignKeyConstraint(["outreach_id"], ["bd_outreach_drafts.id"]),
        sa.ForeignKeyConstraint(["prospect_id"], ["bd_prospects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bd_replies_tenant_received", "bd_replies", ["tenant_id", "received_at"])
    op.create_index("ix_bd_replies_tenant_status", "bd_replies", ["tenant_id", "reply_status"])
    op.create_index("ix_bd_replies_tenant_lead", "bd_replies", ["tenant_id", "lead_id"])
    op.create_index(op.f("ix_bd_replies_contact_id"), "bd_replies", ["contact_id"])
    op.create_index(op.f("ix_bd_replies_lead_id"), "bd_replies", ["lead_id"])
    op.create_index(op.f("ix_bd_replies_opportunity_id"), "bd_replies", ["opportunity_id"])
    op.create_index(op.f("ix_bd_replies_outreach_id"), "bd_replies", ["outreach_id"])
    op.create_index(op.f("ix_bd_replies_prospect_id"), "bd_replies", ["prospect_id"])
    op.create_index(op.f("ix_bd_replies_tenant_id"), "bd_replies", ["tenant_id"])
    op.create_index(op.f("ix_bd_replies_channel"), "bd_replies", ["channel"])
    op.create_index(op.f("ix_bd_replies_received_at"), "bd_replies", ["received_at"])
    op.create_index(op.f("ix_bd_replies_reply_status"), "bd_replies", ["reply_status"])

    op.create_table(
        "bd_reply_ai_analyses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("reply_id", sa.String(), nullable=False),
        sa.Column("analysis_version", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_bundle_version", sa.String(), nullable=False, server_default="phase4c_v1"),
        sa.Column("intent", sa.String(), nullable=False),
        sa.Column("sentiment", sa.String(), nullable=False),
        sa.Column("engagement_level", sa.String(), nullable=False),
        sa.Column("urgency", sa.String(), nullable=False),
        sa.Column("objection_category", sa.String(), nullable=True),
        sa.Column("recommended_pipeline_stage", sa.String(), nullable=True),
        sa.Column("recommended_next_action", sa.Text(), nullable=False),
        sa.Column("analysis_json", sa.JSON(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["reply_id"], ["bd_replies.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "reply_id", "analysis_version", name="uq_bd_reply_ai_analysis_version"),
    )
    op.create_index(
        "ix_bd_reply_ai_analyses_tenant_reply_created",
        "bd_reply_ai_analyses",
        ["tenant_id", "reply_id", "created_at"],
    )
    op.create_index(op.f("ix_bd_reply_ai_analyses_tenant_id"), "bd_reply_ai_analyses", ["tenant_id"])
    op.create_index(op.f("ix_bd_reply_ai_analyses_reply_id"), "bd_reply_ai_analyses", ["reply_id"])
    op.create_index(op.f("ix_bd_reply_ai_analyses_intent"), "bd_reply_ai_analyses", ["intent"])
    op.create_index(op.f("ix_bd_reply_ai_analyses_sentiment"), "bd_reply_ai_analyses", ["sentiment"])
    op.create_index(op.f("ix_bd_reply_ai_analyses_engagement_level"), "bd_reply_ai_analyses", ["engagement_level"])
    op.create_index(op.f("ix_bd_reply_ai_analyses_urgency"), "bd_reply_ai_analyses", ["urgency"])
    op.create_index(op.f("ix_bd_reply_ai_analyses_objection_category"), "bd_reply_ai_analyses", ["objection_category"])
    op.create_index(op.f("ix_bd_reply_ai_analyses_recommended_pipeline_stage"), "bd_reply_ai_analyses", ["recommended_pipeline_stage"])

    op.create_table(
        "bd_reply_response_drafts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("reply_id", sa.String(), nullable=False),
        sa.Column("opportunity_id", sa.String(), nullable=True),
        sa.Column("lead_id", sa.String(), nullable=False),
        sa.Column("prospect_id", sa.String(), nullable=True),
        sa.Column("contact_id", sa.String(), nullable=True),
        sa.Column("analysis_id", sa.String(), nullable=True),
        sa.Column("tone", sa.String(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("structured_content_json", sa.JSON(), nullable=False),
        sa.Column("generation_version", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_bundle_version", sa.String(), nullable=False, server_default="phase4c_v1"),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["analysis_id"], ["bd_reply_ai_analyses.id"]),
        sa.ForeignKeyConstraint(["contact_id"], ["bd_contacts.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["bd_leads.id"]),
        sa.ForeignKeyConstraint(["opportunity_id"], ["bd_opportunities.id"]),
        sa.ForeignKeyConstraint(["prospect_id"], ["bd_prospects.id"]),
        sa.ForeignKeyConstraint(["reply_id"], ["bd_replies.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "reply_id", "generation_version", name="uq_bd_reply_response_generation_version"),
    )
    op.create_index(
        "ix_bd_reply_response_drafts_tenant_reply_created",
        "bd_reply_response_drafts",
        ["tenant_id", "reply_id", "created_at"],
    )
    op.create_index(op.f("ix_bd_reply_response_drafts_analysis_id"), "bd_reply_response_drafts", ["analysis_id"])
    op.create_index(op.f("ix_bd_reply_response_drafts_contact_id"), "bd_reply_response_drafts", ["contact_id"])
    op.create_index(op.f("ix_bd_reply_response_drafts_lead_id"), "bd_reply_response_drafts", ["lead_id"])
    op.create_index(op.f("ix_bd_reply_response_drafts_opportunity_id"), "bd_reply_response_drafts", ["opportunity_id"])
    op.create_index(op.f("ix_bd_reply_response_drafts_prospect_id"), "bd_reply_response_drafts", ["prospect_id"])
    op.create_index(op.f("ix_bd_reply_response_drafts_reply_id"), "bd_reply_response_drafts", ["reply_id"])
    op.create_index(op.f("ix_bd_reply_response_drafts_status"), "bd_reply_response_drafts", ["status"])
    op.create_index(op.f("ix_bd_reply_response_drafts_tenant_id"), "bd_reply_response_drafts", ["tenant_id"])
    op.create_index(op.f("ix_bd_reply_response_drafts_tone"), "bd_reply_response_drafts", ["tone"])


def downgrade() -> None:
    op.drop_index(op.f("ix_bd_reply_response_drafts_tone"), table_name="bd_reply_response_drafts")
    op.drop_index(op.f("ix_bd_reply_response_drafts_tenant_id"), table_name="bd_reply_response_drafts")
    op.drop_index(op.f("ix_bd_reply_response_drafts_status"), table_name="bd_reply_response_drafts")
    op.drop_index(op.f("ix_bd_reply_response_drafts_reply_id"), table_name="bd_reply_response_drafts")
    op.drop_index(op.f("ix_bd_reply_response_drafts_prospect_id"), table_name="bd_reply_response_drafts")
    op.drop_index(op.f("ix_bd_reply_response_drafts_opportunity_id"), table_name="bd_reply_response_drafts")
    op.drop_index(op.f("ix_bd_reply_response_drafts_lead_id"), table_name="bd_reply_response_drafts")
    op.drop_index(op.f("ix_bd_reply_response_drafts_contact_id"), table_name="bd_reply_response_drafts")
    op.drop_index(op.f("ix_bd_reply_response_drafts_analysis_id"), table_name="bd_reply_response_drafts")
    op.drop_index("ix_bd_reply_response_drafts_tenant_reply_created", table_name="bd_reply_response_drafts")
    op.drop_table("bd_reply_response_drafts")

    op.drop_index(op.f("ix_bd_reply_ai_analyses_recommended_pipeline_stage"), table_name="bd_reply_ai_analyses")
    op.drop_index(op.f("ix_bd_reply_ai_analyses_objection_category"), table_name="bd_reply_ai_analyses")
    op.drop_index(op.f("ix_bd_reply_ai_analyses_urgency"), table_name="bd_reply_ai_analyses")
    op.drop_index(op.f("ix_bd_reply_ai_analyses_engagement_level"), table_name="bd_reply_ai_analyses")
    op.drop_index(op.f("ix_bd_reply_ai_analyses_sentiment"), table_name="bd_reply_ai_analyses")
    op.drop_index(op.f("ix_bd_reply_ai_analyses_intent"), table_name="bd_reply_ai_analyses")
    op.drop_index(op.f("ix_bd_reply_ai_analyses_reply_id"), table_name="bd_reply_ai_analyses")
    op.drop_index(op.f("ix_bd_reply_ai_analyses_tenant_id"), table_name="bd_reply_ai_analyses")
    op.drop_index("ix_bd_reply_ai_analyses_tenant_reply_created", table_name="bd_reply_ai_analyses")
    op.drop_table("bd_reply_ai_analyses")

    op.drop_index(op.f("ix_bd_replies_reply_status"), table_name="bd_replies")
    op.drop_index(op.f("ix_bd_replies_received_at"), table_name="bd_replies")
    op.drop_index(op.f("ix_bd_replies_channel"), table_name="bd_replies")
    op.drop_index(op.f("ix_bd_replies_tenant_id"), table_name="bd_replies")
    op.drop_index(op.f("ix_bd_replies_prospect_id"), table_name="bd_replies")
    op.drop_index(op.f("ix_bd_replies_outreach_id"), table_name="bd_replies")
    op.drop_index(op.f("ix_bd_replies_opportunity_id"), table_name="bd_replies")
    op.drop_index(op.f("ix_bd_replies_lead_id"), table_name="bd_replies")
    op.drop_index(op.f("ix_bd_replies_contact_id"), table_name="bd_replies")
    op.drop_index("ix_bd_replies_tenant_lead", table_name="bd_replies")
    op.drop_index("ix_bd_replies_tenant_status", table_name="bd_replies")
    op.drop_index("ix_bd_replies_tenant_received", table_name="bd_replies")
    op.drop_table("bd_replies")
