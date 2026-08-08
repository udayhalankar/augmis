"""add augmis business discovery translation tables

Revision ID: a6b7c8d9e0f1
Revises: d5e6f7a8b9c0
Create Date: 2026-08-08 15:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a6b7c8d9e0f1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bd_discovery_translations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("discovery_id", sa.String(), nullable=False),
        sa.Column("translation_version", sa.Integer(), nullable=False),
        sa.Column("source_language", sa.String(), nullable=False),
        sa.Column("target_language", sa.String(), nullable=False, server_default="en"),
        sa.Column("source_content_hash", sa.String(), nullable=False),
        sa.Column("translated_title", sa.Text(), nullable=True),
        sa.Column("translated_summary", sa.Text(), nullable=True),
        sa.Column("translated_description", sa.Text(), nullable=True),
        sa.Column("translated_detail_json", sa.JSON(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False, server_default="openai"),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_bundle_version", sa.String(), nullable=False, server_default="phase5c4_v1"),
        sa.Column("prompt_version", sa.String(), nullable=False, server_default="discovery_translation_v1"),
        sa.Column("usage_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["discovery_id"], ["bd_discovered_opportunities.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "discovery_id",
            "translation_version",
            name="uq_bd_discovery_translation_version",
        ),
    )
    op.create_index(
        "ix_bd_discovery_translations_tenant_discovery_created",
        "bd_discovery_translations",
        ["tenant_id", "discovery_id", "created_at"],
    )
    op.create_index(
        "ix_bd_discovery_translations_tenant_discovery_target_hash",
        "bd_discovery_translations",
        ["tenant_id", "discovery_id", "target_language", "source_content_hash"],
    )
    op.create_index(op.f("ix_bd_discovery_translations_tenant_id"), "bd_discovery_translations", ["tenant_id"])
    op.create_index(op.f("ix_bd_discovery_translations_discovery_id"), "bd_discovery_translations", ["discovery_id"])
    op.create_index(op.f("ix_bd_discovery_translations_source_language"), "bd_discovery_translations", ["source_language"])
    op.create_index(op.f("ix_bd_discovery_translations_target_language"), "bd_discovery_translations", ["target_language"])
    op.create_index(op.f("ix_bd_discovery_translations_source_content_hash"), "bd_discovery_translations", ["source_content_hash"])


def downgrade() -> None:
    op.drop_index(op.f("ix_bd_discovery_translations_source_content_hash"), table_name="bd_discovery_translations")
    op.drop_index(op.f("ix_bd_discovery_translations_target_language"), table_name="bd_discovery_translations")
    op.drop_index(op.f("ix_bd_discovery_translations_source_language"), table_name="bd_discovery_translations")
    op.drop_index(op.f("ix_bd_discovery_translations_discovery_id"), table_name="bd_discovery_translations")
    op.drop_index(op.f("ix_bd_discovery_translations_tenant_id"), table_name="bd_discovery_translations")
    op.drop_index("ix_bd_discovery_translations_tenant_discovery_target_hash", table_name="bd_discovery_translations")
    op.drop_index("ix_bd_discovery_translations_tenant_discovery_created", table_name="bd_discovery_translations")
    op.drop_table("bd_discovery_translations")
