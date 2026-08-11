"""add independent web discovery tables

Revision ID: a8d9e0f1a2b3
Revises: d2b3c4d5e6f7
Create Date: 2026-08-10 11:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a8d9e0f1a2b3"
down_revision = "d2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bd_web_seeds",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("connector_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("seed_url", sa.String(), nullable=False),
        sa.Column("seed_type", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("crawl_scope", sa.String(), nullable=False, server_default="same_domain"),
        sa.Column("max_depth", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("max_pages", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("crawl_frequency", sa.String(), nullable=False, server_default="weekly"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("industry", sa.String(), nullable=True),
        sa.Column("organization_name", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_crawl_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["bd_connectors.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "connector_id", "seed_url", name="uq_bd_web_seed_tenant_connector_url"),
    )
    op.create_index("ix_bd_web_seeds_tenant_id", "bd_web_seeds", ["tenant_id"])
    op.create_index("ix_bd_web_seeds_connector_id", "bd_web_seeds", ["connector_id"])
    op.create_index("ix_bd_web_seeds_seed_type", "bd_web_seeds", ["seed_type"])
    op.create_index("ix_bd_web_seeds_enabled", "bd_web_seeds", ["enabled"])
    op.create_index("ix_bd_web_seeds_priority", "bd_web_seeds", ["priority"])
    op.create_index("ix_bd_web_seeds_country", "bd_web_seeds", ["country"])
    op.create_index("ix_bd_web_seeds_industry", "bd_web_seeds", ["industry"])
    op.create_index("ix_bd_web_seeds_organization_name", "bd_web_seeds", ["organization_name"])
    op.create_index("ix_bd_web_seeds_last_crawled_at", "bd_web_seeds", ["last_crawled_at"])
    op.create_index("ix_bd_web_seeds_next_crawl_at", "bd_web_seeds", ["next_crawl_at"])
    op.create_index("ix_bd_web_seeds_tenant_connector_priority", "bd_web_seeds", ["tenant_id", "connector_id", "priority"])

    op.create_table(
        "bd_web_domains",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("connector_id", sa.String(), nullable=False),
        sa.Column("seed_id", sa.String(), nullable=True),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("proposed_type", sa.String(), nullable=True),
        sa.Column("trust_source_type", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("approval_status", sa.String(), nullable=False, server_default="approved"),
        sa.Column("robots_status", sa.String(), nullable=False, server_default="unknown"),
        sa.Column("robots_crawl_delay_seconds", sa.Integer(), nullable=True),
        sa.Column("robots_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("robots_url", sa.String(), nullable=True),
        sa.Column("found_from_url", sa.String(), nullable=True),
        sa.Column("found_context", sa.Text(), nullable=True),
        sa.Column("pages_indexed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opportunities_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_crawl_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_crawl_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="ready"),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["bd_connectors.id"]),
        sa.ForeignKeyConstraint(["seed_id"], ["bd_web_seeds.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "connector_id", "domain", name="uq_bd_web_domain_tenant_connector_domain"),
    )
    for index_name, columns in (
        ("ix_bd_web_domains_tenant_id", ["tenant_id"]),
        ("ix_bd_web_domains_connector_id", ["connector_id"]),
        ("ix_bd_web_domains_seed_id", ["seed_id"]),
        ("ix_bd_web_domains_domain", ["domain"]),
        ("ix_bd_web_domains_proposed_type", ["proposed_type"]),
        ("ix_bd_web_domains_trust_source_type", ["trust_source_type"]),
        ("ix_bd_web_domains_enabled", ["enabled"]),
        ("ix_bd_web_domains_approval_status", ["approval_status"]),
        ("ix_bd_web_domains_robots_status", ["robots_status"]),
        ("ix_bd_web_domains_last_crawl_at", ["last_crawl_at"]),
        ("ix_bd_web_domains_next_crawl_at", ["next_crawl_at"]),
        ("ix_bd_web_domains_status", ["status"]),
        ("ix_bd_web_domains_tenant_connector_status", ["tenant_id", "connector_id", "status"]),
    ):
        op.create_index(index_name, "bd_web_domains", columns)

    op.create_table(
        "bd_web_frontier",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("connector_id", sa.String(), nullable=False),
        sa.Column("seed_id", sa.String(), nullable=True),
        sa.Column("domain_id", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("canonical_url", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("parent_url", sa.String(), nullable=True),
        sa.Column("anchor_text", sa.String(), nullable=True),
        sa.Column("link_context", sa.Text(), nullable=True),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("priority", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_fetch_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["bd_connectors.id"]),
        sa.ForeignKeyConstraint(["domain_id"], ["bd_web_domains.id"]),
        sa.ForeignKeyConstraint(["seed_id"], ["bd_web_seeds.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "connector_id", "canonical_url", name="uq_bd_web_frontier_tenant_connector_canonical"),
    )
    for index_name, columns in (
        ("ix_bd_web_frontier_tenant_id", ["tenant_id"]),
        ("ix_bd_web_frontier_connector_id", ["connector_id"]),
        ("ix_bd_web_frontier_seed_id", ["seed_id"]),
        ("ix_bd_web_frontier_domain_id", ["domain_id"]),
        ("ix_bd_web_frontier_domain", ["domain"]),
        ("ix_bd_web_frontier_depth", ["depth"]),
        ("ix_bd_web_frontier_priority", ["priority"]),
        ("ix_bd_web_frontier_status", ["status"]),
        ("ix_bd_web_frontier_discovered_at", ["discovered_at"]),
        ("ix_bd_web_frontier_next_fetch_at", ["next_fetch_at"]),
        ("ix_bd_web_frontier_content_hash", ["content_hash"]),
        ("ix_bd_web_frontier_error_code", ["error_code"]),
        ("ix_bd_web_frontier_tenant_connector_status_priority", ["tenant_id", "connector_id", "status", "priority"]),
    ):
        op.create_index(index_name, "bd_web_frontier", columns)

    op.create_table(
        "bd_web_pages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("connector_id", sa.String(), nullable=False),
        sa.Column("seed_id", sa.String(), nullable=True),
        sa.Column("domain_id", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("canonical_url", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("plain_text", sa.Text(), nullable=True),
        sa.Column("safe_html", sa.Text(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("page_type", sa.String(), nullable=False, server_default="unknown"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("source_metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("contact_routes_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("opportunity_candidate_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["bd_connectors.id"]),
        sa.ForeignKeyConstraint(["domain_id"], ["bd_web_domains.id"]),
        sa.ForeignKeyConstraint(["seed_id"], ["bd_web_seeds.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "connector_id", "canonical_url", name="uq_bd_web_page_tenant_connector_canonical"),
    )
    for index_name, columns in (
        ("ix_bd_web_pages_tenant_id", ["tenant_id"]),
        ("ix_bd_web_pages_connector_id", ["connector_id"]),
        ("ix_bd_web_pages_seed_id", ["seed_id"]),
        ("ix_bd_web_pages_domain_id", ["domain_id"]),
        ("ix_bd_web_pages_domain", ["domain"]),
        ("ix_bd_web_pages_language", ["language"]),
        ("ix_bd_web_pages_page_type", ["page_type"]),
        ("ix_bd_web_pages_published_at", ["published_at"]),
        ("ix_bd_web_pages_content_hash", ["content_hash"]),
        ("ix_bd_web_pages_last_seen_at", ["last_seen_at"]),
        ("ix_bd_web_pages_last_changed_at", ["last_changed_at"]),
        ("ix_bd_web_pages_tenant_connector_type", ["tenant_id", "connector_id", "page_type"]),
        ("ix_bd_web_pages_tenant_domain_changed", ["tenant_id", "domain", "last_changed_at"]),
    ):
        op.create_index(index_name, "bd_web_pages", columns)

    op.execute("UPDATE bd_web_pages SET source_metadata_json='{}'::json, contact_routes_json='[]'::json, opportunity_candidate_json='{}'::json")
    op.alter_column("bd_web_pages", "source_metadata_json", server_default=None)
    op.alter_column("bd_web_pages", "contact_routes_json", server_default=None)
    op.alter_column("bd_web_pages", "opportunity_candidate_json", server_default=None)


def downgrade() -> None:
    op.drop_table("bd_web_pages")
    op.drop_table("bd_web_frontier")
    op.drop_table("bd_web_domains")
    op.drop_table("bd_web_seeds")
