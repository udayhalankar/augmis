"""add augmis business listener foundation

Revision ID: a1b2c3d4e5f6
Revises: ff6a7b8c9d0e
Create Date: 2026-08-07 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "ff6a7b8c9d0e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bd_search_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("target_regions_json", sa.JSON(), nullable=False),
        sa.Column("target_countries_json", sa.JSON(), nullable=False),
        sa.Column("target_industries_json", sa.JSON(), nullable=False),
        sa.Column("include_keywords_json", sa.JSON(), nullable=False),
        sa.Column("include_technologies_json", sa.JSON(), nullable=False),
        sa.Column("include_capabilities_json", sa.JSON(), nullable=False),
        sa.Column("exclude_keywords_json", sa.JSON(), nullable=False),
        sa.Column("excluded_categories_json", sa.JSON(), nullable=False),
        sa.Column("minimum_budget", sa.Float(), nullable=True),
        sa.Column("currencies_json", sa.JSON(), nullable=False),
        sa.Column("allow_budget_unknown", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("solo_feasibility_preference", sa.String(), nullable=True),
        sa.Column("small_team_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("max_delivery_months", sa.Integer(), nullable=True),
        sa.Column("max_age_days", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_bd_search_profile_tenant_name"),
    )
    op.create_index("ix_bd_search_profiles_tenant_enabled", "bd_search_profiles", ["tenant_id", "enabled"])

    op.create_table(
        "bd_connectors",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("search_profile_id", sa.String(), nullable=True),
        sa.Column("connector_type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source_category", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="configured"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("schedule_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("schedule_expression", sa.String(), nullable=True),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("search_criteria_json", sa.JSON(), nullable=False),
        sa.Column("capability_flags_json", sa.JSON(), nullable=False),
        sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["search_profile_id"], ["bd_search_profiles.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_bd_connector_tenant_name"),
    )
    op.create_index("ix_bd_connectors_tenant_type", "bd_connectors", ["tenant_id", "connector_type"])
    op.create_index("ix_bd_connectors_tenant_status", "bd_connectors", ["tenant_id", "status"])

    op.create_table(
        "bd_connector_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("connector_id", sa.String(), nullable=False),
        sa.Column("run_type", sa.String(), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_new", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_duplicate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_filtered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("run_metadata_json", sa.JSON(), nullable=False),
        sa.Column("initiated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["connector_id"], ["bd_connectors.id"]),
        sa.ForeignKeyConstraint(["initiated_by"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bd_connector_runs_tenant_connector_started",
        "bd_connector_runs",
        ["tenant_id", "connector_id", "started_at"],
    )
    op.create_index(
        "ix_bd_connector_runs_tenant_status_started",
        "bd_connector_runs",
        ["tenant_id", "status", "started_at"],
    )

    op.create_table(
        "bd_discovered_opportunities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("connector_id", sa.String(), nullable=False),
        sa.Column("connector_run_id", sa.String(), nullable=True),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("canonical_source_url", sa.String(), nullable=True),
        sa.Column("source_domain", sa.String(), nullable=True),
        sa.Column("source_country", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("normalized_title", sa.String(), nullable=False),
        sa.Column("organization_name", sa.String(), nullable=True),
        sa.Column("normalized_organization_name", sa.String(), nullable=True),
        sa.Column("published_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closing_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_summary", sa.Text(), nullable=True),
        sa.Column("requirement_summary", sa.Text(), nullable=True),
        sa.Column("raw_content_json", sa.JSON(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("industry", sa.String(), nullable=True),
        sa.Column("budget_min", sa.Float(), nullable=True),
        sa.Column("budget_max", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("retrieval_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovery_status", sa.String(), nullable=False, server_default="new"),
        sa.Column("duplicate_of_discovery_id", sa.String(), nullable=True),
        sa.Column("possible_duplicate_of_discovery_id", sa.String(), nullable=True),
        sa.Column("imported_opportunity_id", sa.String(), nullable=True),
        sa.Column("preliminary_relevance_score", sa.Float(), nullable=True),
        sa.Column("relevance_reasons_json", sa.JSON(), nullable=False),
        sa.Column("matched_keywords_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("normalized_search_text", sa.Text(), nullable=True),
        sa.Column("url_fingerprint", sa.String(), nullable=True),
        sa.Column("composite_fingerprint", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["connector_id"], ["bd_connectors.id"]),
        sa.ForeignKeyConstraint(["connector_run_id"], ["bd_connector_runs.id"]),
        sa.ForeignKeyConstraint(["duplicate_of_discovery_id"], ["bd_discovered_opportunities.id"]),
        sa.ForeignKeyConstraint(["imported_opportunity_id"], ["bd_opportunities.id"]),
        sa.ForeignKeyConstraint(["possible_duplicate_of_discovery_id"], ["bd_discovered_opportunities.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "connector_id",
            "external_id",
            name="uq_bd_discovery_tenant_connector_external",
        ),
    )
    op.create_index("ix_bd_discoveries_tenant_status", "bd_discovered_opportunities", ["tenant_id", "discovery_status"])
    op.create_index("ix_bd_discoveries_tenant_connector", "bd_discovered_opportunities", ["tenant_id", "connector_id"])
    op.create_index("ix_bd_discoveries_tenant_discovered", "bd_discovered_opportunities", ["tenant_id", "discovered_at"])
    op.create_index("ix_bd_discoveries_tenant_closing", "bd_discovered_opportunities", ["tenant_id", "closing_date"])
    op.create_index("ix_bd_discoveries_tenant_imported", "bd_discovered_opportunities", ["tenant_id", "imported_opportunity_id"])


def downgrade() -> None:
    op.drop_index("ix_bd_discoveries_tenant_imported", table_name="bd_discovered_opportunities")
    op.drop_index("ix_bd_discoveries_tenant_closing", table_name="bd_discovered_opportunities")
    op.drop_index("ix_bd_discoveries_tenant_discovered", table_name="bd_discovered_opportunities")
    op.drop_index("ix_bd_discoveries_tenant_connector", table_name="bd_discovered_opportunities")
    op.drop_index("ix_bd_discoveries_tenant_status", table_name="bd_discovered_opportunities")
    op.drop_table("bd_discovered_opportunities")
    op.drop_index("ix_bd_connector_runs_tenant_status_started", table_name="bd_connector_runs")
    op.drop_index("ix_bd_connector_runs_tenant_connector_started", table_name="bd_connector_runs")
    op.drop_table("bd_connector_runs")
    op.drop_index("ix_bd_connectors_tenant_status", table_name="bd_connectors")
    op.drop_index("ix_bd_connectors_tenant_type", table_name="bd_connectors")
    op.drop_table("bd_connectors")
    op.drop_index("ix_bd_search_profiles_tenant_enabled", table_name="bd_search_profiles")
    op.drop_table("bd_search_profiles")
