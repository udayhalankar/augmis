"""add bd connector secrets

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-07 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bd_connector_secrets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("connector_id", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("credential_type", sa.String(), nullable=False, server_default="api_key"),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("key_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("last_four", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_status", sa.String(), nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["connector_id"], ["bd_connectors.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "provider",
            "credential_type",
            name="uq_bd_connector_secret_tenant_provider_type",
        ),
    )
    op.create_index(
        "ix_bd_connector_secrets_tenant_provider",
        "bd_connector_secrets",
        ["tenant_id", "provider"],
        unique=False,
    )
    op.create_index(op.f("ix_bd_connector_secrets_tenant_id"), "bd_connector_secrets", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_bd_connector_secrets_connector_id"), "bd_connector_secrets", ["connector_id"], unique=False)
    op.create_index(op.f("ix_bd_connector_secrets_provider"), "bd_connector_secrets", ["provider"], unique=False)
    op.create_index(op.f("ix_bd_connector_secrets_credential_type"), "bd_connector_secrets", ["credential_type"], unique=False)
    op.create_index(op.f("ix_bd_connector_secrets_status"), "bd_connector_secrets", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bd_connector_secrets_status"), table_name="bd_connector_secrets")
    op.drop_index(op.f("ix_bd_connector_secrets_credential_type"), table_name="bd_connector_secrets")
    op.drop_index(op.f("ix_bd_connector_secrets_provider"), table_name="bd_connector_secrets")
    op.drop_index(op.f("ix_bd_connector_secrets_connector_id"), table_name="bd_connector_secrets")
    op.drop_index(op.f("ix_bd_connector_secrets_tenant_id"), table_name="bd_connector_secrets")
    op.drop_index("ix_bd_connector_secrets_tenant_provider", table_name="bd_connector_secrets")
    op.drop_table("bd_connector_secrets")
