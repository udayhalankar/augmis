"""Add migration agent monitoring tables.

Revision ID: f1a2b3c4d5e6
Revises: 6d3c9dbd4b2e, c6b1d4e5a7f8
Create Date: 2026-07-04 17:58:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = ("6d3c9dbd4b2e", "c6b1d4e5a7f8")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "migration_agents",
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("machine_name", sa.String(), nullable=True),
        sa.Column("hostname", sa.String(), nullable=True),
        sa.Column("platform", sa.String(), nullable=True),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("root_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="UNKNOWN"),
        sa.Column("pending_change_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column(
            "modified_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("agent_id"),
    )
    op.create_index("ix_migration_agents_tenant_id", "migration_agents", ["tenant_id"], unique=False)
    op.create_index("ix_migration_agents_hostname", "migration_agents", ["hostname"], unique=False)
    op.create_index("ix_migration_agents_status", "migration_agents", ["status"], unique=False)
    op.create_index("ix_migration_agents_last_seen_at", "migration_agents", ["last_seen_at"], unique=False)
    op.create_index("ix_migration_agents_last_sync_at", "migration_agents", ["last_sync_at"], unique=False)

    op.create_table(
        "migration_agent_activities",
        sa.Column("activity_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("root_path", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(), nullable=True),
        sa.Column("kind", sa.String(), nullable=True),
        sa.Column("change_type", sa.String(), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column(
            "modified_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["migration_agents.agent_id"]),
        sa.PrimaryKeyConstraint("activity_id"),
    )
    op.create_index("ix_migration_agent_activities_agent_id", "migration_agent_activities", ["agent_id"], unique=False)
    op.create_index("ix_migration_agent_activities_tenant_id", "migration_agent_activities", ["tenant_id"], unique=False)
    op.create_index("ix_migration_agent_activities_occurred_at", "migration_agent_activities", ["occurred_at"], unique=False)
    op.create_index("ix_migration_agent_activities_event_type", "migration_agent_activities", ["event_type"], unique=False)
    op.create_index("ix_migration_agent_activities_change_type", "migration_agent_activities", ["change_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_migration_agent_activities_change_type", table_name="migration_agent_activities")
    op.drop_index("ix_migration_agent_activities_event_type", table_name="migration_agent_activities")
    op.drop_index("ix_migration_agent_activities_occurred_at", table_name="migration_agent_activities")
    op.drop_index("ix_migration_agent_activities_tenant_id", table_name="migration_agent_activities")
    op.drop_index("ix_migration_agent_activities_agent_id", table_name="migration_agent_activities")
    op.drop_table("migration_agent_activities")

    op.drop_index("ix_migration_agents_last_sync_at", table_name="migration_agents")
    op.drop_index("ix_migration_agents_last_seen_at", table_name="migration_agents")
    op.drop_index("ix_migration_agents_status", table_name="migration_agents")
    op.drop_index("ix_migration_agents_hostname", table_name="migration_agents")
    op.drop_index("ix_migration_agents_tenant_id", table_name="migration_agents")
    op.drop_table("migration_agents")
