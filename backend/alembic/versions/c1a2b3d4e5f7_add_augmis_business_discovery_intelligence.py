"""add augmis business discovery intelligence

Revision ID: c1a2b3d4e5f7
Revises: b7c8d9e0f1a2
Create Date: 2026-08-09 11:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c1a2b3d4e5f7"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bd_discovered_opportunities", sa.Column("commercial_priority_score", sa.Float(), nullable=True))
    op.add_column("bd_discovered_opportunities", sa.Column("commercial_priority_band", sa.String(), nullable=True))
    op.add_column("bd_discovered_opportunities", sa.Column("commercial_recommendation", sa.String(), nullable=True))
    op.add_column(
        "bd_discovered_opportunities",
        sa.Column("commercial_component_scores_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.add_column(
        "bd_discovered_opportunities",
        sa.Column("commercial_recommendation_reasons_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column(
        "bd_discovered_opportunities",
        sa.Column("commercial_risks_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column("bd_discovered_opportunities", sa.Column("experience_match_score", sa.Float(), nullable=True))
    op.add_column(
        "bd_discovered_opportunities",
        sa.Column("matched_experience_ids_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column(
        "bd_discovered_opportunities",
        sa.Column("matched_experience_reasons_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column(
        "bd_discovered_opportunities",
        sa.Column("matched_experience_summary_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column("bd_discovered_opportunities", sa.Column("delivery_feasibility_score", sa.Float(), nullable=True))
    op.add_column("bd_discovered_opportunities", sa.Column("delivery_complexity", sa.String(), nullable=True))
    op.add_column("bd_discovered_opportunities", sa.Column("delivery_model", sa.String(), nullable=True))
    op.add_column("bd_discovered_opportunities", sa.Column("urgency_status", sa.String(), nullable=True))
    op.add_column("bd_discovered_opportunities", sa.Column("data_quality_status", sa.String(), nullable=True))
    op.add_column("bd_discovered_opportunities", sa.Column("intelligence_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_bd_discoveries_tenant_priority",
        "bd_discovered_opportunities",
        ["tenant_id", "commercial_priority_score", "commercial_recommendation"],
        unique=False,
    )
    op.create_index(op.f("ix_bd_discovered_opportunities_commercial_priority_band"), "bd_discovered_opportunities", ["commercial_priority_band"], unique=False)
    op.create_index(op.f("ix_bd_discovered_opportunities_commercial_priority_score"), "bd_discovered_opportunities", ["commercial_priority_score"], unique=False)
    op.create_index(op.f("ix_bd_discovered_opportunities_commercial_recommendation"), "bd_discovered_opportunities", ["commercial_recommendation"], unique=False)
    op.create_index(op.f("ix_bd_discovered_opportunities_delivery_complexity"), "bd_discovered_opportunities", ["delivery_complexity"], unique=False)
    op.create_index(op.f("ix_bd_discovered_opportunities_urgency_status"), "bd_discovered_opportunities", ["urgency_status"], unique=False)

    op.create_table(
        "bd_discovery_ai_assessments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("discovery_id", sa.String(), nullable=False),
        sa.Column("analysis_version", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_bundle_version", sa.String(), nullable=False, server_default="phase5f_v1"),
        sa.Column("prompt_version", sa.String(), nullable=False, server_default="discovery_deep_assess_v1"),
        sa.Column("recommendation", sa.String(), nullable=True),
        sa.Column("recommendation_confidence", sa.Float(), nullable=True),
        sa.Column("commercial_score", sa.Float(), nullable=True),
        sa.Column("delivery_feasibility_score", sa.Float(), nullable=True),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("analysis_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("usage_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["discovery_id"], ["bd_discovered_opportunities.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "discovery_id", "analysis_version", name="uq_bd_discovery_ai_assessment_version"),
    )
    op.create_index(op.f("ix_bd_discovery_ai_assessments_tenant_id"), "bd_discovery_ai_assessments", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_bd_discovery_ai_assessments_discovery_id"), "bd_discovery_ai_assessments", ["discovery_id"], unique=False)
    op.create_index(op.f("ix_bd_discovery_ai_assessments_recommendation"), "bd_discovery_ai_assessments", ["recommendation"], unique=False)
    op.create_index(
        "ix_bd_discovery_ai_assessments_tenant_discovery_created",
        "bd_discovery_ai_assessments",
        ["tenant_id", "discovery_id", "created_at"],
        unique=False,
    )

    op.alter_column("bd_discovered_opportunities", "commercial_component_scores_json", server_default=None)
    op.alter_column("bd_discovered_opportunities", "commercial_recommendation_reasons_json", server_default=None)
    op.alter_column("bd_discovered_opportunities", "commercial_risks_json", server_default=None)
    op.alter_column("bd_discovered_opportunities", "matched_experience_ids_json", server_default=None)
    op.alter_column("bd_discovered_opportunities", "matched_experience_reasons_json", server_default=None)
    op.alter_column("bd_discovered_opportunities", "matched_experience_summary_json", server_default=None)
    op.alter_column("bd_discovery_ai_assessments", "analysis_json", server_default=None)
    op.alter_column("bd_discovery_ai_assessments", "usage_json", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_bd_discovery_ai_assessments_tenant_discovery_created", table_name="bd_discovery_ai_assessments")
    op.drop_index(op.f("ix_bd_discovery_ai_assessments_recommendation"), table_name="bd_discovery_ai_assessments")
    op.drop_index(op.f("ix_bd_discovery_ai_assessments_discovery_id"), table_name="bd_discovery_ai_assessments")
    op.drop_index(op.f("ix_bd_discovery_ai_assessments_tenant_id"), table_name="bd_discovery_ai_assessments")
    op.drop_table("bd_discovery_ai_assessments")

    op.drop_index(op.f("ix_bd_discovered_opportunities_urgency_status"), table_name="bd_discovered_opportunities")
    op.drop_index(op.f("ix_bd_discovered_opportunities_delivery_complexity"), table_name="bd_discovered_opportunities")
    op.drop_index(op.f("ix_bd_discovered_opportunities_commercial_recommendation"), table_name="bd_discovered_opportunities")
    op.drop_index(op.f("ix_bd_discovered_opportunities_commercial_priority_score"), table_name="bd_discovered_opportunities")
    op.drop_index(op.f("ix_bd_discovered_opportunities_commercial_priority_band"), table_name="bd_discovered_opportunities")
    op.drop_index("ix_bd_discoveries_tenant_priority", table_name="bd_discovered_opportunities")
    op.drop_column("bd_discovered_opportunities", "intelligence_updated_at")
    op.drop_column("bd_discovered_opportunities", "data_quality_status")
    op.drop_column("bd_discovered_opportunities", "urgency_status")
    op.drop_column("bd_discovered_opportunities", "delivery_model")
    op.drop_column("bd_discovered_opportunities", "delivery_complexity")
    op.drop_column("bd_discovered_opportunities", "delivery_feasibility_score")
    op.drop_column("bd_discovered_opportunities", "matched_experience_summary_json")
    op.drop_column("bd_discovered_opportunities", "matched_experience_reasons_json")
    op.drop_column("bd_discovered_opportunities", "matched_experience_ids_json")
    op.drop_column("bd_discovered_opportunities", "experience_match_score")
    op.drop_column("bd_discovered_opportunities", "commercial_risks_json")
    op.drop_column("bd_discovered_opportunities", "commercial_recommendation_reasons_json")
    op.drop_column("bd_discovered_opportunities", "commercial_component_scores_json")
    op.drop_column("bd_discovered_opportunities", "commercial_recommendation")
    op.drop_column("bd_discovered_opportunities", "commercial_priority_band")
    op.drop_column("bd_discovered_opportunities", "commercial_priority_score")
