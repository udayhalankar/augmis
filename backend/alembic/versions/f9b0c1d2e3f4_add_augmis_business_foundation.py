"""Add AUGMIS Business foundation tables.

Revision ID: f9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-08-06 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9b0c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bd_experience_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("business_problems_json", sa.JSON(), nullable=False),
        sa.Column("features_json", sa.JSON(), nullable=False),
        sa.Column("technologies_json", sa.JSON(), nullable=False),
        sa.Column("industries_json", sa.JSON(), nullable=False),
        sa.Column("keywords_json", sa.JSON(), nullable=False),
        sa.Column("reusable_capabilities_json", sa.JSON(), nullable=False),
        sa.Column("confidentiality_safe_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_bd_experience_item_tenant_name"),
    )

    op.create_index("ix_bd_experience_items_tenant_id", "bd_experience_items", ["tenant_id"], unique=False)
    op.create_index("ix_bd_experience_items_category", "bd_experience_items", ["category"], unique=False)
    op.create_index(
        "ix_bd_experience_items_tenant_category",
        "bd_experience_items",
        ["tenant_id", "category"],
        unique=False,
    )
    op.create_index("ix_bd_experience_items_status", "bd_experience_items", ["status"], unique=False)

    op.create_table(
        "bd_opportunities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("organization_name", sa.String(), nullable=False),
        sa.Column("organization_domain", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("industry", sa.String(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_summary", sa.Text(), nullable=True),
        sa.Column("requirement_summary", sa.Text(), nullable=False),
        sa.Column("business_problem", sa.Text(), nullable=True),
        sa.Column("expected_deliverables_json", sa.JSON(), nullable=False),
        sa.Column("required_technologies_json", sa.JSON(), nullable=False),
        sa.Column("published_budget", sa.Float(), nullable=True),
        sa.Column("published_currency", sa.String(), nullable=True),
        sa.Column("estimated_value_min", sa.Float(), nullable=True),
        sa.Column("estimated_value_max", sa.Float(), nullable=True),
        sa.Column("estimated_currency", sa.String(), nullable=True),
        sa.Column("fit_score", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("ai_recommendation", sa.Text(), nullable=True),
        sa.Column("opportunity_status", sa.String(), nullable=False, server_default="new"),
        sa.Column("source_evidence_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "source_type",
            "external_id",
            name="uq_bd_opportunity_tenant_source_external",
        ),
    )

    for index_name, columns in [
        ("ix_bd_opportunities_tenant_id", ["tenant_id"]),
        ("ix_bd_opportunities_source_type", ["source_type"]),
        ("ix_bd_opportunities_organization_name", ["organization_name"]),
        ("ix_bd_opportunities_organization_domain", ["organization_domain"]),
        ("ix_bd_opportunities_country", ["country"]),
        ("ix_bd_opportunities_region", ["region"]),
        ("ix_bd_opportunities_published_at", ["published_at"]),
        ("ix_bd_opportunities_closing_at", ["closing_at"]),
        ("ix_bd_opportunities_fit_score", ["fit_score"]),
        ("ix_bd_opportunities_opportunity_status", ["opportunity_status"]),
        ("ix_bd_opportunities_tenant_status", ["tenant_id", "opportunity_status"]),
        ("ix_bd_opportunities_tenant_closing", ["tenant_id", "closing_at"]),
        ("ix_bd_opportunities_tenant_fit", ["tenant_id", "fit_score"]),
        ("ix_bd_opportunities_tenant_domain", ["tenant_id", "organization_domain"]),
        ("ix_bd_opportunities_tenant_source_url", ["tenant_id", "source_url"]),
    ]:
        op.create_index(index_name, "bd_opportunities", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_bd_opportunities_tenant_source_url",
        "ix_bd_opportunities_tenant_domain",
        "ix_bd_opportunities_tenant_fit",
        "ix_bd_opportunities_tenant_closing",
        "ix_bd_opportunities_tenant_status",
        "ix_bd_opportunities_opportunity_status",
        "ix_bd_opportunities_fit_score",
        "ix_bd_opportunities_closing_at",
        "ix_bd_opportunities_published_at",
        "ix_bd_opportunities_region",
        "ix_bd_opportunities_country",
        "ix_bd_opportunities_organization_domain",
        "ix_bd_opportunities_organization_name",
        "ix_bd_opportunities_source_type",
        "ix_bd_opportunities_tenant_id",
    ]:
        op.drop_index(index_name, table_name="bd_opportunities")

    op.drop_table("bd_opportunities")

    for index_name in [
        "ix_bd_experience_items_status",
        "ix_bd_experience_items_tenant_category",
        "ix_bd_experience_items_category",
        "ix_bd_experience_items_tenant_id",
    ]:
        op.drop_index(index_name, table_name="bd_experience_items")

    op.drop_table("bd_experience_items")
