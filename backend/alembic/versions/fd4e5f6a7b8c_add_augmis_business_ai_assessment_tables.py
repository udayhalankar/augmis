"""Add AUGMIS Business AI assessment tables.

Revision ID: fd4e5f6a7b8c
Revises: fc2d3e4f5a6b
Create Date: 2026-08-07 18:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fd4e5f6a7b8c"
down_revision: Union[str, Sequence[str], None] = "fc2d3e4f5a6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bd_opportunity_ai_assessments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("opportunity_id", sa.String(), nullable=False),
        sa.Column("assessment_version", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_bundle_version", sa.String(), nullable=False),
        sa.Column("requirement_extraction_json", sa.JSON(), nullable=False),
        sa.Column("qualification_json", sa.JSON(), nullable=False),
        sa.Column("buyer_roles_json", sa.JSON(), nullable=False),
        sa.Column("final_fit_score", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("recommendation", sa.String(), nullable=True),
        sa.Column("risks_json", sa.JSON(), nullable=False),
        sa.Column("missing_information_json", sa.JSON(), nullable=False),
        sa.Column("ai_run_summary_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["bd_opportunities.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "opportunity_id",
            "assessment_version",
            name="uq_bd_opportunity_ai_assessment_version",
        ),
    )
    op.create_index(
        "ix_bd_opportunity_ai_assessments_tenant_id",
        "bd_opportunity_ai_assessments",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_bd_opportunity_ai_assessments_opportunity_id",
        "bd_opportunity_ai_assessments",
        ["opportunity_id"],
        unique=False,
    )
    op.create_index(
        "ix_bd_opportunity_ai_assessments_final_fit_score",
        "bd_opportunity_ai_assessments",
        ["final_fit_score"],
        unique=False,
    )
    op.create_index(
        "ix_bd_opportunity_ai_assessments_recommendation",
        "bd_opportunity_ai_assessments",
        ["recommendation"],
        unique=False,
    )
    op.create_index(
        "ix_bd_opportunity_ai_assessments_tenant_opportunity_created",
        "bd_opportunity_ai_assessments",
        ["tenant_id", "opportunity_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "bd_opportunity_experience_matches",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("opportunity_id", sa.String(), nullable=False),
        sa.Column("assessment_id", sa.String(), nullable=False),
        sa.Column("experience_item_id", sa.String(), nullable=False),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("matching_capabilities_json", sa.JSON(), nullable=False),
        sa.Column("matching_technologies_json", sa.JSON(), nullable=False),
        sa.Column("business_problem_similarity", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["bd_opportunity_ai_assessments.id"]),
        sa.ForeignKeyConstraint(["experience_item_id"], ["bd_experience_items.id"]),
        sa.ForeignKeyConstraint(["opportunity_id"], ["bd_opportunities.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "assessment_id",
            "experience_item_id",
            name="uq_bd_opportunity_assessment_experience_match",
        ),
    )
    op.create_index(
        "ix_bd_opportunity_experience_matches_tenant_id",
        "bd_opportunity_experience_matches",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_bd_opportunity_experience_matches_opportunity_id",
        "bd_opportunity_experience_matches",
        ["opportunity_id"],
        unique=False,
    )
    op.create_index(
        "ix_bd_opportunity_experience_matches_assessment_id",
        "bd_opportunity_experience_matches",
        ["assessment_id"],
        unique=False,
    )
    op.create_index(
        "ix_bd_opportunity_experience_matches_experience_item_id",
        "bd_opportunity_experience_matches",
        ["experience_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_bd_opportunity_experience_matches_tenant_opportunity_score",
        "bd_opportunity_experience_matches",
        ["tenant_id", "opportunity_id", "match_score"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_bd_opportunity_experience_matches_tenant_opportunity_score",
        table_name="bd_opportunity_experience_matches",
    )
    op.drop_index(
        "ix_bd_opportunity_experience_matches_experience_item_id",
        table_name="bd_opportunity_experience_matches",
    )
    op.drop_index(
        "ix_bd_opportunity_experience_matches_assessment_id",
        table_name="bd_opportunity_experience_matches",
    )
    op.drop_index(
        "ix_bd_opportunity_experience_matches_opportunity_id",
        table_name="bd_opportunity_experience_matches",
    )
    op.drop_index(
        "ix_bd_opportunity_experience_matches_tenant_id",
        table_name="bd_opportunity_experience_matches",
    )
    op.drop_table("bd_opportunity_experience_matches")

    op.drop_index(
        "ix_bd_opportunity_ai_assessments_tenant_opportunity_created",
        table_name="bd_opportunity_ai_assessments",
    )
    op.drop_index(
        "ix_bd_opportunity_ai_assessments_recommendation",
        table_name="bd_opportunity_ai_assessments",
    )
    op.drop_index(
        "ix_bd_opportunity_ai_assessments_final_fit_score",
        table_name="bd_opportunity_ai_assessments",
    )
    op.drop_index(
        "ix_bd_opportunity_ai_assessments_opportunity_id",
        table_name="bd_opportunity_ai_assessments",
    )
    op.drop_index(
        "ix_bd_opportunity_ai_assessments_tenant_id",
        table_name="bd_opportunity_ai_assessments",
    )
    op.drop_table("bd_opportunity_ai_assessments")
