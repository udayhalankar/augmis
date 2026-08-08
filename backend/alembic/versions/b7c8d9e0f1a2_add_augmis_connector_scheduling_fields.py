"""add augmis connector scheduling fields

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-08-08 22:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b7c8d9e0f1a2"
down_revision = "a6b7c8d9e0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bd_connectors", sa.Column("schedule_type", sa.String(), nullable=False, server_default="manual"))
    op.add_column("bd_connectors", sa.Column("schedule_interval_minutes", sa.Integer(), nullable=True))
    op.add_column("bd_connectors", sa.Column("schedule_day_of_week", sa.Integer(), nullable=True))
    op.add_column("bd_connectors", sa.Column("schedule_time_local", sa.String(), nullable=True))
    op.add_column("bd_connectors", sa.Column("schedule_timezone", sa.String(), nullable=True))
    op.add_column("bd_connectors", sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bd_connectors", sa.Column("last_scheduled_run_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bd_connectors", sa.Column("schedule_retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("bd_connectors", sa.Column("schedule_retry_run_id", sa.String(), nullable=True))
    op.add_column("bd_connectors", sa.Column("active_run_id", sa.String(), nullable=True))
    op.add_column("bd_connectors", sa.Column("schedule_updated_by", sa.String(), nullable=True))
    op.add_column("bd_connectors", sa.Column("schedule_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_bd_connectors_schedule_type", "bd_connectors", ["schedule_type"], unique=False)
    op.create_index("ix_bd_connectors_next_run_at", "bd_connectors", ["next_run_at"], unique=False)
    op.create_index("ix_bd_connectors_active_run_id", "bd_connectors", ["active_run_id"], unique=False)

    op.add_column("bd_connector_runs", sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("bd_connector_runs", sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("bd_connector_runs", sa.Column("retry_of_run_id", sa.String(), nullable=True))
    op.add_column("bd_connector_runs", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_bd_connector_runs_retry_of_run_id",
        "bd_connector_runs",
        "bd_connector_runs",
        ["retry_of_run_id"],
        ["id"],
    )
    op.create_index("ix_bd_connector_runs_retry_of_run_id", "bd_connector_runs", ["retry_of_run_id"], unique=False)
    op.create_index("ix_bd_connector_runs_next_retry_at", "bd_connector_runs", ["next_retry_at"], unique=False)

    op.execute("UPDATE bd_connectors SET schedule_type = 'manual' WHERE schedule_type IS NULL")
    op.execute(
        """
        UPDATE bd_connectors
        SET schedule_timezone = COALESCE(NULLIF(schedule_timezone, ''), 'UTC'),
            schedule_expression = CASE
                WHEN COALESCE(schedule_enabled, FALSE) = FALSE THEN 'Manual'
                ELSE COALESCE(schedule_expression, 'Manual')
            END
        """
    )

    op.alter_column("bd_connectors", "schedule_type", server_default=None)
    op.alter_column("bd_connectors", "schedule_retry_count", server_default=None)
    op.alter_column("bd_connector_runs", "attempt_number", server_default=None)
    op.alter_column("bd_connector_runs", "max_attempts", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_bd_connector_runs_next_retry_at", table_name="bd_connector_runs")
    op.drop_index("ix_bd_connector_runs_retry_of_run_id", table_name="bd_connector_runs")
    op.drop_constraint("fk_bd_connector_runs_retry_of_run_id", "bd_connector_runs", type_="foreignkey")
    op.drop_column("bd_connector_runs", "next_retry_at")
    op.drop_column("bd_connector_runs", "retry_of_run_id")
    op.drop_column("bd_connector_runs", "max_attempts")
    op.drop_column("bd_connector_runs", "attempt_number")

    op.drop_index("ix_bd_connectors_active_run_id", table_name="bd_connectors")
    op.drop_index("ix_bd_connectors_next_run_at", table_name="bd_connectors")
    op.drop_index("ix_bd_connectors_schedule_type", table_name="bd_connectors")
    op.drop_column("bd_connectors", "schedule_updated_at")
    op.drop_column("bd_connectors", "schedule_updated_by")
    op.drop_column("bd_connectors", "active_run_id")
    op.drop_column("bd_connectors", "schedule_retry_run_id")
    op.drop_column("bd_connectors", "schedule_retry_count")
    op.drop_column("bd_connectors", "last_scheduled_run_at")
    op.drop_column("bd_connectors", "next_run_at")
    op.drop_column("bd_connectors", "schedule_timezone")
    op.drop_column("bd_connectors", "schedule_time_local")
    op.drop_column("bd_connectors", "schedule_day_of_week")
    op.drop_column("bd_connectors", "schedule_interval_minutes")
    op.drop_column("bd_connectors", "schedule_type")
