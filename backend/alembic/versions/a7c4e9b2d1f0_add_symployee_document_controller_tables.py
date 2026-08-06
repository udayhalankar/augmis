"""Add Symployee document controller tables.

Revision ID: a7c4e9b2d1f0
Revises: f1a2b3c4d5e6
Create Date: 2026-07-06 17:15:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c4e9b2d1f0"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symployee_definitions",
        sa.Column("symployee_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("employee_type", sa.String(), nullable=False, server_default="document_controller"),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("instruction_profile_code", sa.String(), nullable=True),
        sa.Column("permission_profile_json", sa.JSON(), nullable=True),
        sa.Column("default_policy_set_code", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("symployee_id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_symployee_definitions_tenant_code"),
    )
    op.create_index("ix_symployee_definitions_tenant_id", "symployee_definitions", ["tenant_id"], unique=False)
    op.create_index("ix_symployee_definitions_status", "symployee_definitions", ["status"], unique=False)

    op.create_table(
        "symployee_policy_configs",
        sa.Column("policy_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("symployee_code", sa.String(), nullable=False),
        sa.Column("policy_domain", sa.String(), nullable=False),
        sa.Column("policy_code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(), nullable=False, server_default="DRAFT"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("policy_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "symployee_code",
            "policy_domain",
            "policy_code",
            "version_no",
            name="uq_symployee_policy_version",
        ),
    )
    op.create_index("ix_symployee_policy_configs_tenant_id", "symployee_policy_configs", ["tenant_id"], unique=False)
    op.create_index("ix_symployee_policy_configs_symployee_code", "symployee_policy_configs", ["symployee_code"], unique=False)
    op.create_index("ix_symployee_policy_configs_policy_domain", "symployee_policy_configs", ["policy_domain"], unique=False)
    op.create_index("ix_symployee_policy_configs_status", "symployee_policy_configs", ["status"], unique=False)

    op.create_table(
        "symployee_document_identities",
        sa.Column("identity_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("repository_id", sa.String(), nullable=False),
        sa.Column("canonical_document_number", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("document_type_code", sa.String(), nullable=True),
        sa.Column("discipline_code", sa.String(), nullable=True),
        sa.Column("project_code", sa.String(), nullable=True),
        sa.Column("originator_code", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="REGISTERED"),
        sa.Column("current_version_id", sa.String(), nullable=True),
        sa.Column("current_document_id", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["current_document_id"], ["documents.document_id"]),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.repository_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("identity_id"),
    )
    for index_name, columns in [
        ("ix_symployee_document_identities_tenant_id", ["tenant_id"]),
        ("ix_symployee_document_identities_repository_id", ["repository_id"]),
        ("ix_symployee_document_identities_canonical_document_number", ["canonical_document_number"]),
        ("ix_symployee_document_identities_title", ["title"]),
        ("ix_symployee_document_identities_document_type_code", ["document_type_code"]),
        ("ix_symployee_document_identities_discipline_code", ["discipline_code"]),
        ("ix_symployee_document_identities_project_code", ["project_code"]),
        ("ix_symployee_document_identities_originator_code", ["originator_code"]),
        ("ix_symployee_document_identities_status", ["status"]),
        ("ix_symployee_document_identities_current_version_id", ["current_version_id"]),
        ("ix_symployee_document_identities_current_document_id", ["current_document_id"]),
    ]:
        op.create_index(index_name, "symployee_document_identities", columns, unique=False)

    op.create_table(
        "symployee_document_source_objects",
        sa.Column("source_object_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("identity_id", sa.String(), nullable=False),
        sa.Column("repository_id", sa.String(), nullable=False),
        sa.Column("source_system_type", sa.String(), nullable=False),
        sa.Column("external_object_id", sa.Text(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("source_version_ref", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["identity_id"], ["symployee_document_identities.identity_id"]),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.repository_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("source_object_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "repository_id",
            "source_system_type",
            "external_object_id",
            name="uq_symployee_source_object_external",
        ),
    )
    for index_name, columns in [
        ("ix_symployee_document_source_objects_tenant_id", ["tenant_id"]),
        ("ix_symployee_document_source_objects_identity_id", ["identity_id"]),
        ("ix_symployee_document_source_objects_repository_id", ["repository_id"]),
        ("ix_symployee_document_source_objects_source_system_type", ["source_system_type"]),
    ]:
        op.create_index(index_name, "symployee_document_source_objects", columns, unique=False)

    op.create_table(
        "symployee_connector_events",
        sa.Column("connector_event_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=True),
        sa.Column("repository_id", sa.String(), nullable=False),
        sa.Column("event_key", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("external_object_id", sa.Text(), nullable=True),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("file_hash", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("processing_status", sa.String(), nullable=False, server_default="accepted"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("identity_id", sa.String(), nullable=True),
        sa.Column("version_id", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["identity_id"], ["symployee_document_identities.identity_id"]),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.repository_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("connector_event_id"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_symployee_connector_events_idempotency"),
    )
    for index_name, columns in [
        ("ix_symployee_connector_events_tenant_id", ["tenant_id"]),
        ("ix_symployee_connector_events_agent_id", ["agent_id"]),
        ("ix_symployee_connector_events_repository_id", ["repository_id"]),
        ("ix_symployee_connector_events_idempotency_key", ["idempotency_key"]),
        ("ix_symployee_connector_events_event_type", ["event_type"]),
        ("ix_symployee_connector_events_file_hash", ["file_hash"]),
        ("ix_symployee_connector_events_processing_status", ["processing_status"]),
        ("ix_symployee_connector_events_identity_id", ["identity_id"]),
        ("ix_symployee_connector_events_version_id", ["version_id"]),
    ]:
        op.create_index(index_name, "symployee_connector_events", columns, unique=False)

    op.create_table(
        "symployee_document_versions",
        sa.Column("version_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("identity_id", sa.String(), nullable=False),
        sa.Column("connector_file_id", sa.String(), nullable=True),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("revision_code", sa.String(), nullable=True),
        sa.Column("version_label", sa.String(), nullable=True),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("file_extension", sa.String(), nullable=True),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("file_hash", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("supersedes_version_id", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["connector_file_id"], ["connector_files.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"]),
        sa.ForeignKeyConstraint(["identity_id"], ["symployee_document_identities.identity_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("version_id"),
        sa.UniqueConstraint("tenant_id", "document_id", name="uq_symployee_document_versions_document"),
    )
    for index_name, columns in [
        ("ix_symployee_document_versions_tenant_id", ["tenant_id"]),
        ("ix_symployee_document_versions_identity_id", ["identity_id"]),
        ("ix_symployee_document_versions_connector_file_id", ["connector_file_id"]),
        ("ix_symployee_document_versions_document_id", ["document_id"]),
        ("ix_symployee_document_versions_file_hash", ["file_hash"]),
        ("ix_symployee_document_versions_status", ["status"]),
        ("ix_symployee_document_versions_supersedes_version_id", ["supersedes_version_id"]),
    ]:
        op.create_index(index_name, "symployee_document_versions", columns, unique=False)

    op.create_table(
        "symployee_ai_recommendations",
        sa.Column("recommendation_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("symployee_id", sa.String(), nullable=False),
        sa.Column("identity_id", sa.String(), nullable=False),
        sa.Column("version_id", sa.String(), nullable=True),
        sa.Column("recommendation_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="NEEDS_REVIEW"),
        sa.Column("recommendation_json", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("model_provider", sa.String(), nullable=True),
        sa.Column("prompt_profile_code", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column("policy_code", sa.String(), nullable=True),
        sa.Column("policy_version_no", sa.Integer(), nullable=True),
        sa.Column("source_evidence_json", sa.JSON(), nullable=True),
        sa.Column("approval_outcome", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["identity_id"], ["symployee_document_identities.identity_id"]),
        sa.ForeignKeyConstraint(["symployee_id"], ["symployee_definitions.symployee_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["version_id"], ["symployee_document_versions.version_id"]),
        sa.PrimaryKeyConstraint("recommendation_id"),
    )
    for index_name, columns in [
        ("ix_symployee_ai_recommendations_tenant_id", ["tenant_id"]),
        ("ix_symployee_ai_recommendations_symployee_id", ["symployee_id"]),
        ("ix_symployee_ai_recommendations_identity_id", ["identity_id"]),
        ("ix_symployee_ai_recommendations_version_id", ["version_id"]),
        ("ix_symployee_ai_recommendations_recommendation_type", ["recommendation_type"]),
        ("ix_symployee_ai_recommendations_status", ["status"]),
    ]:
        op.create_index(index_name, "symployee_ai_recommendations", columns, unique=False)

    op.create_table(
        "symployee_approval_records",
        sa.Column("approval_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("approval_subject_type", sa.String(), nullable=False),
        sa.Column("approval_subject_id", sa.String(), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("approver_user_id", sa.String(), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("policy_code", sa.String(), nullable=True),
        sa.Column("policy_version_no", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["approver_user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("approval_id"),
    )
    for index_name, columns in [
        ("ix_symployee_approval_records_tenant_id", ["tenant_id"]),
        ("ix_symployee_approval_records_approval_subject_type", ["approval_subject_type"]),
        ("ix_symployee_approval_records_approval_subject_id", ["approval_subject_id"]),
        ("ix_symployee_approval_records_decision", ["decision"]),
        ("ix_symployee_approval_records_approver_user_id", ["approver_user_id"]),
    ]:
        op.create_index(index_name, "symployee_approval_records", columns, unique=False)

    op.create_table(
        "symployee_override_records",
        sa.Column("override_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("override_subject_type", sa.String(), nullable=False),
        sa.Column("override_subject_id", sa.String(), nullable=False),
        sa.Column("related_recommendation_id", sa.String(), nullable=True),
        sa.Column("overridden_by_user_id", sa.String(), nullable=False),
        sa.Column("reason_code", sa.String(), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("before_state_json", sa.JSON(), nullable=True),
        sa.Column("after_state_json", sa.JSON(), nullable=True),
        sa.Column("requires_second_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="EFFECTIVE"),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["overridden_by_user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["related_recommendation_id"], ["symployee_ai_recommendations.recommendation_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("override_id"),
    )
    for index_name, columns in [
        ("ix_symployee_override_records_tenant_id", ["tenant_id"]),
        ("ix_symployee_override_records_override_subject_type", ["override_subject_type"]),
        ("ix_symployee_override_records_override_subject_id", ["override_subject_id"]),
        ("ix_symployee_override_records_related_recommendation_id", ["related_recommendation_id"]),
        ("ix_symployee_override_records_overridden_by_user_id", ["overridden_by_user_id"]),
        ("ix_symployee_override_records_status", ["status"]),
    ]:
        op.create_index(index_name, "symployee_override_records", columns, unique=False)

    op.create_table(
        "symployee_connector_commands",
        sa.Column("command_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=True),
        sa.Column("repository_id", sa.String(), nullable=False),
        sa.Column("identity_id", sa.String(), nullable=False),
        sa.Column("version_id", sa.String(), nullable=True),
        sa.Column("command_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING_APPROVAL"),
        sa.Column("approval_status", sa.String(), nullable=False, server_default="PENDING_APPROVAL"),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("policy_code", sa.String(), nullable=True),
        sa.Column("policy_version_no", sa.Integer(), nullable=True),
        sa.Column("source_recommendation_id", sa.String(), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["identity_id"], ["symployee_document_identities.identity_id"]),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.repository_id"]),
        sa.ForeignKeyConstraint(["source_recommendation_id"], ["symployee_ai_recommendations.recommendation_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["version_id"], ["symployee_document_versions.version_id"]),
        sa.PrimaryKeyConstraint("command_id"),
    )
    for index_name, columns in [
        ("ix_symployee_connector_commands_tenant_id", ["tenant_id"]),
        ("ix_symployee_connector_commands_agent_id", ["agent_id"]),
        ("ix_symployee_connector_commands_repository_id", ["repository_id"]),
        ("ix_symployee_connector_commands_identity_id", ["identity_id"]),
        ("ix_symployee_connector_commands_version_id", ["version_id"]),
        ("ix_symployee_connector_commands_command_type", ["command_type"]),
        ("ix_symployee_connector_commands_status", ["status"]),
        ("ix_symployee_connector_commands_approval_status", ["approval_status"]),
        ("ix_symployee_connector_commands_source_recommendation_id", ["source_recommendation_id"]),
        ("ix_symployee_connector_commands_idempotency_key", ["idempotency_key"]),
    ]:
        op.create_index(index_name, "symployee_connector_commands", columns, unique=False)

    op.create_table(
        "symployee_idempotency_records",
        sa.Column("idempotency_record_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("scope_type", sa.String(), nullable=False),
        sa.Column("scope_key", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_status", sa.String(), nullable=False, server_default="accepted"),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_by", sa.String(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("idempotency_record_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "scope_type",
            "idempotency_key",
            name="uq_symployee_idempotency_scope_key",
        ),
    )
    for index_name, columns in [
        ("ix_symployee_idempotency_records_tenant_id", ["tenant_id"]),
        ("ix_symployee_idempotency_records_scope_type", ["scope_type"]),
        ("ix_symployee_idempotency_records_idempotency_key", ["idempotency_key"]),
        ("ix_symployee_idempotency_records_resolution_status", ["resolution_status"]),
    ]:
        op.create_index(index_name, "symployee_idempotency_records", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_symployee_idempotency_records_resolution_status",
        "ix_symployee_idempotency_records_idempotency_key",
        "ix_symployee_idempotency_records_scope_type",
        "ix_symployee_idempotency_records_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_idempotency_records")
    op.drop_table("symployee_idempotency_records")

    for index_name in [
        "ix_symployee_connector_commands_idempotency_key",
        "ix_symployee_connector_commands_source_recommendation_id",
        "ix_symployee_connector_commands_approval_status",
        "ix_symployee_connector_commands_status",
        "ix_symployee_connector_commands_command_type",
        "ix_symployee_connector_commands_version_id",
        "ix_symployee_connector_commands_identity_id",
        "ix_symployee_connector_commands_repository_id",
        "ix_symployee_connector_commands_agent_id",
        "ix_symployee_connector_commands_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_connector_commands")
    op.drop_table("symployee_connector_commands")

    for index_name in [
        "ix_symployee_override_records_status",
        "ix_symployee_override_records_overridden_by_user_id",
        "ix_symployee_override_records_related_recommendation_id",
        "ix_symployee_override_records_override_subject_id",
        "ix_symployee_override_records_override_subject_type",
        "ix_symployee_override_records_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_override_records")
    op.drop_table("symployee_override_records")

    for index_name in [
        "ix_symployee_approval_records_approver_user_id",
        "ix_symployee_approval_records_decision",
        "ix_symployee_approval_records_approval_subject_id",
        "ix_symployee_approval_records_approval_subject_type",
        "ix_symployee_approval_records_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_approval_records")
    op.drop_table("symployee_approval_records")

    for index_name in [
        "ix_symployee_ai_recommendations_status",
        "ix_symployee_ai_recommendations_recommendation_type",
        "ix_symployee_ai_recommendations_version_id",
        "ix_symployee_ai_recommendations_identity_id",
        "ix_symployee_ai_recommendations_symployee_id",
        "ix_symployee_ai_recommendations_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_ai_recommendations")
    op.drop_table("symployee_ai_recommendations")

    for index_name in [
        "ix_symployee_document_versions_supersedes_version_id",
        "ix_symployee_document_versions_status",
        "ix_symployee_document_versions_file_hash",
        "ix_symployee_document_versions_document_id",
        "ix_symployee_document_versions_connector_file_id",
        "ix_symployee_document_versions_identity_id",
        "ix_symployee_document_versions_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_document_versions")
    op.drop_table("symployee_document_versions")

    for index_name in [
        "ix_symployee_connector_events_version_id",
        "ix_symployee_connector_events_identity_id",
        "ix_symployee_connector_events_processing_status",
        "ix_symployee_connector_events_file_hash",
        "ix_symployee_connector_events_event_type",
        "ix_symployee_connector_events_idempotency_key",
        "ix_symployee_connector_events_repository_id",
        "ix_symployee_connector_events_agent_id",
        "ix_symployee_connector_events_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_connector_events")
    op.drop_table("symployee_connector_events")

    for index_name in [
        "ix_symployee_document_source_objects_source_system_type",
        "ix_symployee_document_source_objects_repository_id",
        "ix_symployee_document_source_objects_identity_id",
        "ix_symployee_document_source_objects_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_document_source_objects")
    op.drop_table("symployee_document_source_objects")

    for index_name in [
        "ix_symployee_document_identities_current_document_id",
        "ix_symployee_document_identities_current_version_id",
        "ix_symployee_document_identities_status",
        "ix_symployee_document_identities_originator_code",
        "ix_symployee_document_identities_project_code",
        "ix_symployee_document_identities_discipline_code",
        "ix_symployee_document_identities_document_type_code",
        "ix_symployee_document_identities_title",
        "ix_symployee_document_identities_canonical_document_number",
        "ix_symployee_document_identities_repository_id",
        "ix_symployee_document_identities_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_document_identities")
    op.drop_table("symployee_document_identities")

    for index_name in [
        "ix_symployee_policy_configs_status",
        "ix_symployee_policy_configs_policy_domain",
        "ix_symployee_policy_configs_symployee_code",
        "ix_symployee_policy_configs_tenant_id",
    ]:
        op.drop_index(index_name, table_name="symployee_policy_configs")
    op.drop_table("symployee_policy_configs")

    op.drop_index("ix_symployee_definitions_status", table_name="symployee_definitions")
    op.drop_index("ix_symployee_definitions_tenant_id", table_name="symployee_definitions")
    op.drop_table("symployee_definitions")

