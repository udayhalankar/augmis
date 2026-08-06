"""Add Symployee workflow tables.

Revision ID: b3f1c2d4e5f6
Revises: a7c4e9b2d1f0
Create Date: 2026-07-08 19:35:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3f1c2d4e5f6"
down_revision: Union[str, Sequence[str], None] = "a7c4e9b2d1f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_workflow_instances",
        sa.Column("workflow_instance_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("symployee_id", sa.String(), nullable=False),
        sa.Column("identity_id", sa.String(), nullable=False),
        sa.Column("version_id", sa.String(), nullable=True),
        sa.Column("workflow_code", sa.String(), nullable=False),
        sa.Column("workflow_status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("routing_status", sa.String(), nullable=False, server_default="PLANNED"),
        sa.Column("current_step_code", sa.String(), nullable=True),
        sa.Column("policy_code", sa.String(), nullable=True),
        sa.Column("policy_version_no", sa.Integer(), nullable=True),
        sa.Column("workflow_payload_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["identity_id"], ["symployee_document_identities.identity_id"]),
        sa.ForeignKeyConstraint(["symployee_id"], ["symployee_definitions.symployee_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["version_id"], ["symployee_document_versions.version_id"]),
        sa.PrimaryKeyConstraint("workflow_instance_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "identity_id",
            "version_id",
            "workflow_code",
            name="uq_symployee_workflow_instance_version",
        ),
    )
    for index_name, columns in [
        ("ix_symployee_workflow_instances_tenant_id", ["tenant_id"]),
        ("ix_symployee_workflow_instances_symployee_id", ["symployee_id"]),
        ("ix_symployee_workflow_instances_identity_id", ["identity_id"]),
        ("ix_symployee_workflow_instances_version_id", ["version_id"]),
        ("ix_symployee_workflow_instances_workflow_code", ["workflow_code"]),
        ("ix_symployee_workflow_instances_workflow_status", ["workflow_status"]),
        ("ix_symployee_workflow_instances_routing_status", ["routing_status"]),
    ]:
        op.create_index(index_name, "symployee_workflow_instances", columns, unique=False)

    op.create_table(
        "symployee_workflow_tasks",
        sa.Column("workflow_task_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("workflow_instance_id", sa.String(), nullable=False),
        sa.Column("identity_id", sa.String(), nullable=False),
        sa.Column("version_id", sa.String(), nullable=True),
        sa.Column("task_code", sa.String(), nullable=False),
        sa.Column("task_name", sa.String(), nullable=False),
        sa.Column("task_type", sa.String(), nullable=False, server_default="recommendation_review"),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("sequence_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("assigned_role_code", sa.String(), nullable=True),
        sa.Column("assigned_user_id", sa.String(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sla_status", sa.String(), nullable=False, server_default="ON_TRACK"),
        sa.Column("escalation_status", sa.String(), nullable=False, server_default="NONE"),
        sa.Column("task_payload_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["identity_id"], ["symployee_document_identities.identity_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["version_id"], ["symployee_document_versions.version_id"]),
        sa.ForeignKeyConstraint(["workflow_instance_id"], ["symployee_workflow_instances.workflow_instance_id"]),
        sa.PrimaryKeyConstraint("workflow_task_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "workflow_instance_id",
            "task_code",
            name="uq_symployee_workflow_task_code",
        ),
    )
    for index_name, columns in [
        ("ix_symployee_workflow_tasks_tenant_id", ["tenant_id"]),
        ("ix_symployee_workflow_tasks_workflow_instance_id", ["workflow_instance_id"]),
        ("ix_symployee_workflow_tasks_identity_id", ["identity_id"]),
        ("ix_symployee_workflow_tasks_version_id", ["version_id"]),
        ("ix_symployee_workflow_tasks_task_code", ["task_code"]),
        ("ix_symployee_workflow_tasks_task_type", ["task_type"]),
        ("ix_symployee_workflow_tasks_status", ["status"]),
        ("ix_symployee_workflow_tasks_assigned_role_code", ["assigned_role_code"]),
        ("ix_symployee_workflow_tasks_assigned_user_id", ["assigned_user_id"]),
        ("ix_symployee_workflow_tasks_sla_status", ["sla_status"]),
        ("ix_symployee_workflow_tasks_escalation_status", ["escalation_status"]),
    ]:
        op.create_index(index_name, "symployee_workflow_tasks", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_workflow_tasks_escalation_status",
        "ix_symployee_workflow_tasks_sla_status",
        "ix_symployee_workflow_tasks_assigned_user_id",
        "ix_symployee_workflow_tasks_assigned_role_code",
        "ix_symployee_workflow_tasks_status",
        "ix_symployee_workflow_tasks_task_type",
        "ix_symployee_workflow_tasks_task_code",
        "ix_symployee_workflow_tasks_version_id",
        "ix_symployee_workflow_tasks_identity_id",
        "ix_symployee_workflow_tasks_workflow_instance_id",
        "ix_symployee_workflow_tasks_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_workflow_tasks")
    op.drop_table("symployee_workflow_tasks")

    for index_name in [
        "ix_symployee_workflow_instances_routing_status",
        "ix_symployee_workflow_instances_workflow_status",
        "ix_symployee_workflow_instances_workflow_code",
        "ix_symployee_workflow_instances_version_id",
        "ix_symployee_workflow_instances_identity_id",
        "ix_symployee_workflow_instances_symployee_id",
        "ix_symployee_workflow_instances_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_workflow_instances")
    op.drop_table("symployee_workflow_instances")
