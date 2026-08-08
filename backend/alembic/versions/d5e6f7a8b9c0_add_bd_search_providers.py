"""add bd search providers

Revision ID: d5e6f7a8b9c0
Revises: c3d4e5f6a7b8
Create Date: 2026-08-08 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d5e6f7a8b9c0"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bd_search_providers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("provider_code", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("provider_type", sa.String(), nullable=False),
        sa.Column("adapter_code", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("credential_type", sa.String(), nullable=False, server_default="api_key"),
        sa.Column("configuration_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bd_search_providers_scope_code", "bd_search_providers", ["tenant_id", "provider_code"], unique=False)
    op.create_index("ix_bd_search_providers_scope_enabled", "bd_search_providers", ["tenant_id", "enabled"], unique=False)
    op.create_index(op.f("ix_bd_search_providers_tenant_id"), "bd_search_providers", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_bd_search_providers_provider_code"), "bd_search_providers", ["provider_code"], unique=False)
    op.create_index(op.f("ix_bd_search_providers_provider_type"), "bd_search_providers", ["provider_type"], unique=False)
    op.create_index(op.f("ix_bd_search_providers_adapter_code"), "bd_search_providers", ["adapter_code"], unique=False)
    op.create_index(op.f("ix_bd_search_providers_enabled"), "bd_search_providers", ["enabled"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bd_search_providers_enabled"), table_name="bd_search_providers")
    op.drop_index(op.f("ix_bd_search_providers_adapter_code"), table_name="bd_search_providers")
    op.drop_index(op.f("ix_bd_search_providers_provider_type"), table_name="bd_search_providers")
    op.drop_index(op.f("ix_bd_search_providers_provider_code"), table_name="bd_search_providers")
    op.drop_index(op.f("ix_bd_search_providers_tenant_id"), table_name="bd_search_providers")
    op.drop_index("ix_bd_search_providers_scope_enabled", table_name="bd_search_providers")
    op.drop_index("ix_bd_search_providers_scope_code", table_name="bd_search_providers")
    op.drop_table("bd_search_providers")
