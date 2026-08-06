from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class AuditColumnsMixin:
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    modified_by = Column(String, nullable=True)
    modified_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Tenant(AuditColumnsMixin, Base):
    __tablename__ = "tenants"

    tenant_id = Column(String, primary_key=True)
    tenant_name = Column(String, nullable=False)
    status = Column(String, default="ACTIVE")
    plan_id = Column(String)
    subscription_status = Column(String, default="ACTIVE")
    billing_status = Column(String, default="TRIAL")
    subscription_start = Column(String)
    subscription_end = Column(String)

class Plan(AuditColumnsMixin, Base):
    __tablename__ = "plans"

    plan_id = Column(String, primary_key=True)
    plan_name = Column(String, nullable=False)
    price_monthly = Column(Float, default=0)
    currency = Column(String, default="INR")
    max_users = Column(Integer, default=5)
    max_documents = Column(Integer, default=100)
    max_storage_mb = Column(Float, default=500)
    monthly_ai_tokens = Column(Integer, default=100000)
    allowed_modules = Column(JSON, default=list)
    features = Column(JSON, default=list)


class TenantUsage(AuditColumnsMixin, Base):
    __tablename__ = "tenant_usage"

    usage_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False)
    users_count = Column(Integer, default=0)
    documents_count = Column(Integer, default=0)
    storage_used_mb = Column(Float, default=0)
    ai_tokens_used = Column(Integer, default=0)
    period = Column(String, nullable=False)


class User(AuditColumnsMixin, Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False)
    tenant_name = Column(String)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    status = Column(String, default="ACTIVE")
    allowed_modules = Column(JSON, default=list)
    permissions = Column(JSON, default=list)


class AuthSession(AuditColumnsMixin, Base):
    __tablename__ = "auth_sessions"

    session_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    remember_me = Column(Boolean, nullable=False, default=False)
    refresh_token_hash = Column(String, nullable=False, unique=True, index=True)
    refresh_expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    absolute_expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True, index=True)

class Repository(AuditColumnsMixin, Base):
    __tablename__ = "repositories"

    repository_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False)
    repository_name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    business_area = Column(String, nullable=False)
    status = Column(String, default="ACTIVE")
    source_path = Column(Text)
    connection_config = Column(JSON, default=dict)
    sync_status = Column(String, default="NOT_SYNCED")
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_run_id = Column(String, nullable=True)
    last_sync_status = Column(String, nullable=True)
    last_sync_started_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_completed_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_error = Column(Text, nullable=True)
    sync_enabled = Column(Boolean, nullable=False, default=True)
    sync_interval_minutes = Column(Integer, nullable=True)
    sync_cursor = Column(Text, nullable=True)
    sync_metadata = Column(JSON, default=dict)


class RepositoryAccess(AuditColumnsMixin, Base):
    __tablename__ = "repository_access"

    access_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    can_read = Column(Boolean, default=True)
    can_ingest = Column(Boolean, default=False)
    can_admin = Column(Boolean, default=False)
    business_area = Column(String)


class IntelligencePattern(AuditColumnsMixin, Base):
    __tablename__ = "intelligence_patterns"

    pattern_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    dashboard_type = Column(String, default="generic")
    tags_keywords = Column(JSON, default=list)
    summary_focus = Column(JSON, default=list)
    risk_rules = Column(JSON, default=list)
    thresholds = Column(JSON, default=list)
    required_specifics = Column(JSON, default=list)
    entities_to_extract = Column(JSON, default=list)
    summary_template = Column(Text, default="")
    threshold_rules = Column(JSON, default=list)
    fact_extractors = Column(JSON, default=list)
    enabled_checks = Column(JSON, default=list)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_intelligence_patterns_tenant_name"),
    )


class BusinessArea(AuditColumnsMixin, Base):
    __tablename__ = "business_areas"

    business_area_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    intelligence_pattern = Column(String, nullable=True)
    dashboard_type = Column(String, default="generic")
    tags_keywords = Column(JSON, default=list)
    summary_focus = Column(JSON, default=list)
    risk_rules = Column(JSON, default=list)
    thresholds = Column(JSON, default=list)
    required_specifics = Column(JSON, default=list)
    entities_to_extract = Column(JSON, default=list)
    summary_template = Column(Text, default="")
    threshold_rules = Column(JSON, default=list)
    fact_extractors = Column(JSON, default=list)
    enabled_checks = Column(JSON, default=list)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_business_areas_tenant_name"),
    )


class ExtractedFact(AuditColumnsMixin, Base):
    __tablename__ = "extracted_facts"

    extracted_fact_id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    document_id = Column(String, nullable=False, index=True)
    repository_id = Column(String, nullable=False, index=True)
    business_area = Column(String, nullable=False, index=True)
    intelligence_pattern = Column(String, nullable=True, index=True)
    file_name = Column(String, nullable=False, index=True)
    record_id = Column(String, nullable=False, index=True)
    facts_json = Column(JSON, default=dict)
    extracted_entities = Column(JSON, default=list)
    required_specifics_presence = Column(JSON, default=dict)
    compiled_checks = Column(JSON, default=list)
    matched_rule_labels = Column(JSON, default=list)
    summary_payload = Column(JSON, default=dict)
    source_modified_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "document_id",
            "business_area",
            name="uq_extracted_facts_tenant_document_area",
        ),
    )


class Document(AuditColumnsMixin, Base):
    __tablename__ = "documents"

    document_id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    repository_id = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    original_file_name = Column(String)
    source_type = Column(String, index=True)
    business_area = Column(String)
    stored_path = Column(Text)
    uploaded_by = Column(String)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata_json = Column(JSON, default=dict)

    external_file_id = Column(Text, nullable=True, index=True)
    file_hash = Column(Text, nullable=True, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    is_current_version = Column(Boolean, nullable=False, default=True)
    source_created_at = Column(DateTime(timezone=True), nullable=True)
    source_modified_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    connector_file_id = Column(String, nullable=True, index=True)


class DocumentChunk(AuditColumnsMixin, Base):
    __tablename__ = "document_chunks"

    chunk_id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=False)
    tenant_id = Column(String, nullable=False)
    repository_id = Column(String, nullable=False)
    business_area = Column(String)
    file_name = Column(String)
    chunk_index = Column(Integer)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    metadata_json = Column(JSON, default=dict)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

class ChatSession(AuditColumnsMixin, Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    title = Column(String, default="New Conversation")
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(AuditColumnsMixin, Base):
    __tablename__ = "chat_messages"

    message_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"), nullable=False)
    tenant_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(JSON, default=list)

class AuditLog(AuditColumnsMixin, Base):
    __tablename__ = "audit_logs"

    audit_id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    user_id = Column(String, nullable=True)
    event_type = Column(String, nullable=False)
    event_category = Column(String, nullable=False)
    description = Column(Text)
    resource_type = Column(String)
    resource_id = Column(String)
    ip_address = Column(String)
    user_agent = Column(Text)
    request_id = Column(String, index=True)
    metadata_json = Column(JSON, default=dict)


class ServerLog(AuditColumnsMixin, Base):
    __tablename__ = "server_logs"

    log_id = Column(String, primary_key=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    source = Column(String, nullable=False, index=True)
    level = Column(String, nullable=False, index=True)
    logger = Column(String, nullable=True, index=True)
    category = Column(String, nullable=True, index=True)
    message = Column(Text, nullable=False)
    exception = Column(Text, nullable=True)
    stack = Column(Text, nullable=True)
    route = Column(Text, nullable=True, index=True)
    method = Column(String, nullable=True, index=True)
    status_code = Column(Integer, nullable=True, index=True)
    request_id = Column(String, nullable=True, index=True)
    tenant_id = Column(String, nullable=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    user_email = Column(String, nullable=True, index=True)
    repository_id = Column(String, nullable=True, index=True)
    business_area = Column(String, nullable=True, index=True)
    component = Column(String, nullable=True, index=True)
    is_critical = Column(Boolean, nullable=False, default=False, index=True)
    metadata_json = Column(JSON, default=dict)

class ConnectorSyncRun(AuditColumnsMixin, Base):
    __tablename__ = "connector_sync_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    sync_started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    sync_completed_at = Column(DateTime(timezone=True), nullable=True)
    sync_status = Column(String(50), nullable=False, default="running", index=True)
    sync_mode = Column(String(50), nullable=False, default="manual")
    files_discovered = Column(Integer, nullable=False, default=0)
    files_processed = Column(Integer, nullable=False, default=0)
    files_skipped = Column(Integer, nullable=False, default=0)
    files_failed = Column(Integer, nullable=False, default=0)
    files_deleted = Column(Integer, nullable=False, default=0)
    chunks_created = Column(Integer, nullable=False, default=0)
    embeddings_created = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    started_by = Column(String, ForeignKey("users.user_id"), nullable=True)

class ConnectorFile(AuditColumnsMixin, Base):
    __tablename__ = "connector_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    external_file_id = Column(Text, nullable=False)
    file_name = Column(Text, nullable=False)
    file_path = Column(Text, nullable=True)
    file_hash = Column(Text, nullable=True, index=True)
    file_size = Column(BigInteger, nullable=True)
    source_created_at = Column(DateTime(timezone=True), nullable=True)
    source_modified_at = Column(DateTime(timezone=True), nullable=True)
    first_synced_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_status = Column(String(50), nullable=False, default="pending", index=True)
    last_sync_run_id = Column(String, ForeignKey("connector_sync_runs.id"), nullable=True)
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=True, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    is_current_version = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    last_error_message = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "repository_id",
            "external_file_id",
            "version_number",
            name="uq_connector_file_version",
        ),
        Index(
            "idx_connector_files_incremental",
            "tenant_id",
            "repository_id",
            "external_file_id",
            "source_modified_at",
        ),
        Index(
            "idx_connector_files_hash",
            "tenant_id",
            "repository_id",
            "file_hash",
        ),
    )


class ConnectorSyncFailure(AuditColumnsMixin, Base):
    __tablename__ = "connector_sync_failures"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=False, index=True)
    sync_run_id = Column(String, ForeignKey("connector_sync_runs.id"), nullable=True, index=True)
    connector_file_id = Column(String, ForeignKey("connector_files.id"), nullable=True, index=True)
    external_file_id = Column(Text, nullable=True)
    file_name = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    failure_stage = Column(String(80), nullable=False)
    error_message = Column(Text, nullable=False)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    resolved = Column(Boolean, nullable=False, default=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class MigrationAgent(AuditColumnsMixin, Base):
    __tablename__ = "migration_agents"

    agent_id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=True, index=True)
    machine_name = Column(String, nullable=True)
    hostname = Column(String, nullable=True, index=True)
    platform = Column(String, nullable=True)
    version = Column(String, nullable=False)
    root_path = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="UNKNOWN", index=True)
    pending_change_count = Column(Integer, nullable=False, default=0)
    last_seen_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_error = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)


class MigrationAgentActivity(AuditColumnsMixin, Base):
    __tablename__ = "migration_agent_activities"

    activity_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    agent_id = Column(String, ForeignKey("migration_agents.agent_id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=True, index=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    event_type = Column(String, nullable=False, index=True)
    root_path = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    file_name = Column(String, nullable=True)
    kind = Column(String, nullable=True)
    change_type = Column(String, nullable=True, index=True)
    item_count = Column(Integer, nullable=True)
    metadata_json = Column(JSON, default=dict)


class SymployeeDefinition(AuditColumnsMixin, Base):
    __tablename__ = "symployee_definitions"

    symployee_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    employee_type = Column(String, nullable=False, default="document_controller")
    status = Column(String, nullable=False, default="ACTIVE", index=True)
    instruction_profile_code = Column(String, nullable=True)
    permission_profile_json = Column(JSON, default=dict)
    default_policy_set_code = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_symployee_definitions_tenant_code"),
    )


class SymployeePolicyConfig(AuditColumnsMixin, Base):
    __tablename__ = "symployee_policy_configs"

    policy_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    symployee_code = Column(String, nullable=False, index=True)
    policy_domain = Column(String, nullable=False, index=True)
    policy_code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    version_no = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="DRAFT", index=True)
    is_default = Column(Boolean, nullable=False, default=False)
    scope_type = Column(String, nullable=False, default="tenant", index=True)
    scope_ref = Column(String, nullable=True, index=True)
    config_json = Column(JSON, default=dict)

    __table_args__ = (
        Index(
            "uq_symployee_policy_version",
            "tenant_id",
            "symployee_code",
            "policy_domain",
            "policy_code",
            "scope_type",
            func.coalesce(scope_ref, ""),
            "version_no",
            unique=True,
        ),
    )


class SymployeeDocumentIdentity(AuditColumnsMixin, Base):
    __tablename__ = "symployee_document_identities"

    identity_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=False, index=True)
    canonical_document_number = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False, index=True)
    document_type_code = Column(String, nullable=True, index=True)
    discipline_code = Column(String, nullable=True, index=True)
    project_code = Column(String, nullable=True, index=True)
    originator_code = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="REGISTERED", index=True)
    document_lifecycle_stage = Column(String, nullable=True, index=True)
    review_status = Column(String, nullable=True, index=True)
    issue_status = Column(String, nullable=True, index=True)
    record_status = Column(String, nullable=True, index=True)
    retention_status = Column(String, nullable=True, index=True)
    disposition_status = Column(String, nullable=True, index=True)
    security_status = Column(String, nullable=True, index=True)
    current_version_id = Column(String, nullable=True, index=True)
    current_document_id = Column(String, ForeignKey("documents.document_id"), nullable=True, index=True)


class SymployeeDocumentSourceObject(AuditColumnsMixin, Base):
    __tablename__ = "symployee_document_source_objects"

    source_object_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    identity_id = Column(String, ForeignKey("symployee_document_identities.identity_id"), nullable=False, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=False, index=True)
    source_system_type = Column(String, nullable=False, index=True)
    external_object_id = Column(Text, nullable=False)
    source_path = Column(Text, nullable=True)
    source_version_ref = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "repository_id",
            "source_system_type",
            "external_object_id",
            name="uq_symployee_source_object_external",
        ),
    )


class SymployeeConnectorEvent(AuditColumnsMixin, Base):
    __tablename__ = "symployee_connector_events"

    connector_event_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    agent_id = Column(String, nullable=True, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=False, index=True)
    event_key = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    external_object_id = Column(Text, nullable=True)
    source_path = Column(Text, nullable=True)
    file_hash = Column(Text, nullable=True, index=True)
    payload_json = Column(JSON, default=dict)
    processing_status = Column(String, nullable=False, default="accepted", index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    identity_id = Column(String, ForeignKey("symployee_document_identities.identity_id"), nullable=True, index=True)
    version_id = Column(String, nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_symployee_connector_events_idempotency",
        ),
    )


class SymployeeDocumentVersion(AuditColumnsMixin, Base):
    __tablename__ = "symployee_document_versions"

    version_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    identity_id = Column(String, ForeignKey("symployee_document_identities.identity_id"), nullable=False, index=True)
    connector_file_id = Column(String, ForeignKey("connector_files.id"), nullable=True, index=True)
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=False, index=True)
    revision_code = Column(String, nullable=True)
    revision_status = Column(String, nullable=True, index=True)
    issue_status = Column(String, nullable=True, index=True)
    is_current_revision = Column(Boolean, nullable=False, default=False, index=True)
    revision_sequence_no = Column(Integer, nullable=True)
    revision_purpose_code = Column(String, nullable=True)
    revision_description = Column(Text, nullable=True)
    version_label = Column(String, nullable=True)
    file_name = Column(String, nullable=False)
    file_extension = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)
    file_hash = Column(Text, nullable=True, index=True)
    page_count = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="ACTIVE", index=True)
    supersedes_version_id = Column(String, nullable=True, index=True)
    metadata_json = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "document_id",
            name="uq_symployee_document_versions_document",
        ),
    )


class SymployeeRecordLegalHold(AuditColumnsMixin, Base):
    __tablename__ = "symployee_record_legal_holds"

    legal_hold_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    identity_id = Column(String, ForeignKey("symployee_document_identities.identity_id"), nullable=False, index=True)
    record_declaration_id = Column(String, nullable=True, index=True)
    hold_policy_id = Column(
        String,
        ForeignKey("symployee_record_hold_policies.hold_policy_id"),
        nullable=True,
        index=True,
    )
    hold_category = Column(String, nullable=True, index=True)
    hold_code = Column(String, nullable=False, index=True)
    hold_status = Column(String, nullable=False, default="ACTIVE", index=True)
    authority = Column(String, nullable=False, index=True)
    matter_reference = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    placed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    placed_by = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    released_by = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    release_reason = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)


class SymployeeRecordDeclaration(AuditColumnsMixin, Base):
    __tablename__ = "symployee_record_declarations"

    record_declaration_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    identity_id = Column(String, ForeignKey("symployee_document_identities.identity_id"), nullable=False, index=True)
    version_id = Column(String, nullable=True, index=True)
    record_category = Column(String, nullable=False, index=True)
    record_status = Column(String, nullable=False, default="DECLARED_RECORD", index=True)
    record_stage = Column(String, nullable=True, index=True)
    active_from = Column(DateTime(timezone=True), nullable=True, index=True)
    inactive_from = Column(DateTime(timezone=True), nullable=True, index=True)
    inactive_reason_code = Column(String, nullable=True, index=True)
    vital_status = Column(String, nullable=True, index=True)
    inactive_reason = Column(Text, nullable=True)
    owner_user_id = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    declared_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    declared_by = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    declaration_reason = Column(Text, nullable=True)
    source_event_id = Column(String, ForeignKey("symployee_document_lifecycle_events.event_id"), nullable=True, index=True)
    declaration_rule_id = Column(
        String,
        ForeignKey("symployee_record_declaration_rules.declaration_rule_id"),
        nullable=True,
        index=True,
    )
    lifecycle_rule_id = Column(
        String,
        ForeignKey("symployee_record_lifecycle_rules.lifecycle_rule_id"),
        nullable=True,
        index=True,
    )
    retention_schedule_id = Column(
        String,
        ForeignKey("symployee_retention_schedules.retention_schedule_id"),
        nullable=True,
        index=True,
    )
    metadata_json = Column(JSON, default=dict)


class SymployeeDispositionCase(AuditColumnsMixin, Base):
    __tablename__ = "symployee_disposition_cases"

    disposition_case_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    identity_id = Column(String, ForeignKey("symployee_document_identities.identity_id"), nullable=False, index=True)
    record_declaration_id = Column(
        String,
        ForeignKey("symployee_record_declarations.record_declaration_id"),
        nullable=True,
        index=True,
    )
    retention_rule_id = Column(
        String,
        ForeignKey("symployee_retention_rules.retention_rule_id"),
        nullable=True,
        index=True,
    )
    disposition_type = Column(String, nullable=False, index=True)
    case_status = Column(String, nullable=False, default="PENDING_REVIEW", index=True)
    eligibility_date = Column(DateTime(timezone=True), nullable=True, index=True)
    requested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    requested_by = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    executed_by = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    reason = Column(Text, nullable=True)
    outcome_notes = Column(Text, nullable=True)
    disposition_policy_id = Column(
        String,
        ForeignKey("symployee_record_disposition_policies.disposition_policy_id"),
        nullable=True,
        index=True,
    )
    metadata_json = Column(JSON, default=dict)


class SymployeeRecordCategory(AuditColumnsMixin, Base):
    __tablename__ = "symployee_record_categories"

    record_category_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=True, index=True)
    business_area = Column(String, nullable=True, index=True)
    document_type = Column(String, nullable=True, index=True)
    category_code = Column(String, nullable=False, index=True)
    category_name = Column(String, nullable=False)
    category_description = Column(Text, nullable=True)
    parent_category_code = Column(String, nullable=True, index=True)
    security_classification_default = Column(String, nullable=True)
    retention_schedule_code_default = Column(String, nullable=True)
    vital_policy_code_default = Column(String, nullable=True)
    hold_policy_code_default = Column(String, nullable=True)
    disposition_policy_code_default = Column(String, nullable=True)
    archive_policy_code_default = Column(String, nullable=True)
    status = Column(String, nullable=False, default="DRAFT", index=True)
    effective_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    effective_to = Column(DateTime(timezone=True), nullable=True, index=True)
    version_no = Column(Integer, nullable=False, default=1)
    is_current_version = Column(Boolean, nullable=False, default=True, index=True)
    rule_priority = Column(Integer, nullable=False, default=100, index=True)
    config_payload_json = Column(JSON, default=dict)


class SymployeeRecordDeclarationRule(AuditColumnsMixin, Base):
    __tablename__ = "symployee_record_declaration_rules"

    declaration_rule_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=True, index=True)
    business_area = Column(String, nullable=True, index=True)
    document_type = Column(String, nullable=True, index=True)
    rule_code = Column(String, nullable=False, index=True)
    rule_name = Column(String, nullable=False)
    rule_description = Column(Text, nullable=True)
    record_category_code = Column(String, nullable=False, index=True)
    declaration_mode = Column(String, nullable=False, default="CANDIDATE_FIRST", index=True)
    approval_required = Column(Boolean, nullable=False, default=False, index=True)
    approval_role_code = Column(String, nullable=True)
    candidate_trigger_event = Column(String, nullable=False, index=True)
    declaration_trigger_event = Column(String, nullable=False, index=True)
    metadata_requirements_json = Column(JSON, default=dict)
    matching_criteria_json = Column(JSON, default=dict)
    status = Column(String, nullable=False, default="DRAFT", index=True)
    effective_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    effective_to = Column(DateTime(timezone=True), nullable=True, index=True)
    version_no = Column(Integer, nullable=False, default=1)
    is_current_version = Column(Boolean, nullable=False, default=True, index=True)
    rule_priority = Column(Integer, nullable=False, default=100, index=True)
    config_payload_json = Column(JSON, default=dict)


class SymployeeRecordLifecycleRule(AuditColumnsMixin, Base):
    __tablename__ = "symployee_record_lifecycle_rules"

    lifecycle_rule_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=True, index=True)
    business_area = Column(String, nullable=True, index=True)
    document_type = Column(String, nullable=True, index=True)
    rule_code = Column(String, nullable=False, index=True)
    rule_name = Column(String, nullable=False)
    rule_description = Column(Text, nullable=True)
    record_category_code = Column(String, nullable=True, index=True)
    active_start_event = Column(String, nullable=False, index=True)
    inactive_eligibility_event = Column(String, nullable=False, index=True)
    inactive_after_days = Column(Integer, nullable=True, index=True)
    inactive_override_required = Column(Boolean, nullable=False, default=False, index=True)
    reopen_to_active_allowed = Column(Boolean, nullable=False, default=False, index=True)
    reopen_trigger_events_json = Column(JSON, default=list)
    lifecycle_clock_basis = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="DRAFT", index=True)
    effective_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    effective_to = Column(DateTime(timezone=True), nullable=True, index=True)
    version_no = Column(Integer, nullable=False, default=1)
    is_current_version = Column(Boolean, nullable=False, default=True, index=True)
    rule_priority = Column(Integer, nullable=False, default=100, index=True)
    config_payload_json = Column(JSON, default=dict)


class SymployeeRetentionRule(AuditColumnsMixin, Base):
    __tablename__ = "symployee_retention_rules"

    retention_rule_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    rule_code = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    record_category = Column(String, nullable=False, index=True)
    trigger_event = Column(String, nullable=False, index=True)
    retention_period_value = Column(Integer, nullable=False)
    retention_period_unit = Column(String, nullable=False, default="YEARS")
    disposition_action = Column(String, nullable=False, index=True)
    approver_role_code = Column(String, nullable=True)
    legal_authority = Column(String, nullable=True)
    status = Column(String, nullable=False, default="ACTIVE", index=True)
    is_default = Column(Boolean, nullable=False, default=False)
    scope_type = Column(String, nullable=False, default="tenant", index=True)
    scope_ref = Column(String, nullable=True, index=True)
    metadata_json = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "rule_code",
            "scope_type",
            "scope_ref",
            name="uq_symployee_retention_rule_scope",
        ),
    )


class SymployeeRetentionSchedule(AuditColumnsMixin, Base):
    __tablename__ = "symployee_retention_schedules"

    retention_schedule_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=True, index=True)
    business_area = Column(String, nullable=True, index=True)
    document_type = Column(String, nullable=True, index=True)
    schedule_code = Column(String, nullable=False, index=True)
    schedule_name = Column(String, nullable=False)
    schedule_description = Column(Text, nullable=True)
    record_category_code = Column(String, nullable=True, index=True)
    retention_start_event = Column(String, nullable=False, index=True)
    retention_period_value = Column(Integer, nullable=False, index=True)
    retention_period_unit = Column(String, nullable=False, index=True)
    review_required = Column(Boolean, nullable=False, default=False, index=True)
    review_offset_value = Column(Integer, nullable=True, index=True)
    review_offset_unit = Column(String, nullable=True, index=True)
    suspend_on_hold = Column(Boolean, nullable=False, default=False, index=True)
    final_disposition_policy_code = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="DRAFT", index=True)
    effective_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    effective_to = Column(DateTime(timezone=True), nullable=True, index=True)
    version_no = Column(Integer, nullable=False, default=1)
    is_current_version = Column(Boolean, nullable=False, default=True, index=True)
    rule_priority = Column(Integer, nullable=False, default=100, index=True)
    config_payload_json = Column(JSON, default=dict)


class SymployeeRecordVitalPolicy(AuditColumnsMixin, Base):
    __tablename__ = "symployee_record_vital_policies"

    vital_policy_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=True, index=True)
    business_area = Column(String, nullable=True, index=True)
    document_type = Column(String, nullable=True, index=True)
    policy_code = Column(String, nullable=False, index=True)
    policy_name = Column(String, nullable=False)
    policy_description = Column(Text, nullable=True)
    record_category_code = Column(String, nullable=True, index=True)
    classification_mode = Column(String, nullable=False, default="RULE_DRIVEN", index=True)
    default_vital_flag = Column(Boolean, nullable=False, default=False, index=True)
    review_required = Column(Boolean, nullable=False, default=False, index=True)
    review_role_code = Column(String, nullable=True, index=True)
    review_interval_days = Column(Integer, nullable=True, index=True)
    criteria_json = Column(JSON, default=dict)
    status = Column(String, nullable=False, default="DRAFT", index=True)
    effective_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    effective_to = Column(DateTime(timezone=True), nullable=True, index=True)
    version_no = Column(Integer, nullable=False, default=1)
    is_current_version = Column(Boolean, nullable=False, default=True, index=True)
    rule_priority = Column(Integer, nullable=False, default=100, index=True)
    config_payload_json = Column(JSON, default=dict)


class SymployeeRecordHoldPolicy(AuditColumnsMixin, Base):
    __tablename__ = "symployee_record_hold_policies"

    hold_policy_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=True, index=True)
    business_area = Column(String, nullable=True, index=True)
    document_type = Column(String, nullable=True, index=True)
    policy_code = Column(String, nullable=False, index=True)
    policy_name = Column(String, nullable=False)
    policy_description = Column(Text, nullable=True)
    record_category_code = Column(String, nullable=True, index=True)
    hold_category = Column(String, nullable=False, index=True)
    placement_role_code = Column(String, nullable=False, index=True)
    release_role_code = Column(String, nullable=True, index=True)
    matter_reference_required = Column(Boolean, nullable=False, default=False, index=True)
    reason_required = Column(Boolean, nullable=False, default=False, index=True)
    blocks_disposition = Column(Boolean, nullable=False, default=False, index=True)
    blocks_archive_transfer = Column(Boolean, nullable=False, default=False, index=True)
    default_expiry_mode = Column(String, nullable=True, index=True)
    criteria_json = Column(JSON, default=dict)
    status = Column(String, nullable=False, default="DRAFT", index=True)
    effective_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    effective_to = Column(DateTime(timezone=True), nullable=True, index=True)
    version_no = Column(Integer, nullable=False, default=1)
    is_current_version = Column(Boolean, nullable=False, default=True, index=True)
    rule_priority = Column(Integer, nullable=False, default=100, index=True)
    config_payload_json = Column(JSON, default=dict)


class SymployeeRecordDispositionPolicy(AuditColumnsMixin, Base):
    __tablename__ = "symployee_record_disposition_policies"

    disposition_policy_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=True, index=True)
    business_area = Column(String, nullable=True, index=True)
    document_type = Column(String, nullable=True, index=True)
    policy_code = Column(String, nullable=False, index=True)
    policy_name = Column(String, nullable=False)
    policy_description = Column(Text, nullable=True)
    record_category_code = Column(String, nullable=True, index=True)
    allowed_outcome = Column(String, nullable=False, default="MIXED", index=True)
    approval_required = Column(Boolean, nullable=False, default=False, index=True)
    records_approval_required = Column(Boolean, nullable=False, default=False, index=True)
    legal_approval_required = Column(Boolean, nullable=False, default=False, index=True)
    business_owner_approval_required = Column(Boolean, nullable=False, default=False, index=True)
    evidence_requirements_json = Column(JSON, default=dict)
    blocked_by_active_hold = Column(Boolean, nullable=False, default=False, index=True)
    disposition_execution_role_code = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="DRAFT", index=True)
    effective_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    effective_to = Column(DateTime(timezone=True), nullable=True, index=True)
    version_no = Column(Integer, nullable=False, default=1)
    is_current_version = Column(Boolean, nullable=False, default=True, index=True)
    rule_priority = Column(Integer, nullable=False, default=100, index=True)
    config_payload_json = Column(JSON, default=dict)


class SymployeeRecordArchivePolicy(AuditColumnsMixin, Base):
    __tablename__ = "symployee_record_archive_policies"

    archive_policy_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=True, index=True)
    business_area = Column(String, nullable=True, index=True)
    document_type = Column(String, nullable=True, index=True)
    policy_code = Column(String, nullable=False, index=True)
    policy_name = Column(String, nullable=False)
    policy_description = Column(Text, nullable=True)
    record_category_code = Column(String, nullable=True, index=True)
    transfer_required = Column(Boolean, nullable=False, default=False, index=True)
    destination_code = Column(String, nullable=False, index=True)
    package_format_code = Column(String, nullable=False, index=True)
    checksum_required = Column(Boolean, nullable=False, default=False, index=True)
    metadata_profile_code = Column(String, nullable=False, index=True)
    preservation_review_interval_days = Column(Integer, nullable=True, index=True)
    receipt_confirmation_required = Column(Boolean, nullable=False, default=False, index=True)
    criteria_json = Column(JSON, default=dict)
    status = Column(String, nullable=False, default="DRAFT", index=True)
    effective_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    effective_to = Column(DateTime(timezone=True), nullable=True, index=True)
    version_no = Column(Integer, nullable=False, default=1)
    is_current_version = Column(Boolean, nullable=False, default=True, index=True)
    rule_priority = Column(Integer, nullable=False, default=100, index=True)
    config_payload_json = Column(JSON, default=dict)


class SymployeeRecordAssignmentRule(AuditColumnsMixin, Base):
    __tablename__ = "symployee_record_assignment_rules"

    assignment_rule_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=True, index=True)
    business_area = Column(String, nullable=True, index=True)
    project_code = Column(String, nullable=True, index=True)
    document_type = Column(String, nullable=True, index=True)
    rule_code = Column(String, nullable=False, index=True)
    rule_name = Column(String, nullable=False)
    rule_description = Column(Text, nullable=True)
    record_category_code = Column(String, nullable=True, index=True)
    assignment_context = Column(String, nullable=False, index=True)
    owner_role_code = Column(String, nullable=True, index=True)
    performer_role_code = Column(String, nullable=True, index=True)
    approver_role_code = Column(String, nullable=True, index=True)
    escalation_role_code = Column(String, nullable=True, index=True)
    fallback_role_code = Column(String, nullable=True, index=True)
    assignment_logic_json = Column(JSON, default=dict)
    status = Column(String, nullable=False, default="DRAFT", index=True)
    effective_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    effective_to = Column(DateTime(timezone=True), nullable=True, index=True)
    version_no = Column(Integer, nullable=False, default=1)
    is_current_version = Column(Boolean, nullable=False, default=True, index=True)
    rule_priority = Column(Integer, nullable=False, default=100, index=True)
    config_payload_json = Column(JSON, default=dict)


class SymployeeWorkflowInstance(AuditColumnsMixin, Base):
    __tablename__ = "symployee_workflow_instances"

    workflow_instance_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    symployee_id = Column(String, ForeignKey("symployee_definitions.symployee_id"), nullable=False, index=True)
    identity_id = Column(String, ForeignKey("symployee_document_identities.identity_id"), nullable=False, index=True)
    version_id = Column(String, ForeignKey("symployee_document_versions.version_id"), nullable=True, index=True)
    workflow_code = Column(String, nullable=False, index=True)
    workflow_status = Column(String, nullable=False, default="ACTIVE", index=True)
    routing_status = Column(String, nullable=False, default="PLANNED", index=True)
    current_step_code = Column(String, nullable=True)
    policy_code = Column(String, nullable=True)
    policy_version_no = Column(Integer, nullable=True)
    lifecycle_state_dimension = Column(String, nullable=True, index=True)
    lifecycle_target_state = Column(String, nullable=True, index=True)
    lifecycle_context_json = Column(JSON, default=dict)
    workflow_payload_json = Column(JSON, default=dict)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "identity_id",
            "version_id",
            "workflow_code",
            name="uq_symployee_workflow_instance_version",
        ),
    )


class SymployeeWorkflowTask(AuditColumnsMixin, Base):
    __tablename__ = "symployee_workflow_tasks"

    workflow_task_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    workflow_instance_id = Column(
        String,
        ForeignKey("symployee_workflow_instances.workflow_instance_id"),
        nullable=False,
        index=True,
    )
    identity_id = Column(String, ForeignKey("symployee_document_identities.identity_id"), nullable=False, index=True)
    version_id = Column(String, ForeignKey("symployee_document_versions.version_id"), nullable=True, index=True)
    task_code = Column(String, nullable=False, index=True)
    task_name = Column(String, nullable=False)
    task_type = Column(String, nullable=False, default="recommendation_review", index=True)
    status = Column(String, nullable=False, default="PENDING", index=True)
    sequence_no = Column(Integer, nullable=False, default=1)
    assigned_role_code = Column(String, nullable=True, index=True)
    assigned_user_id = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    outcome_code = Column(String, nullable=True, index=True)
    response_code = Column(String, nullable=True, index=True)
    outcome_notes = Column(Text, nullable=True)
    sla_status = Column(String, nullable=False, default="ON_TRACK", index=True)
    escalation_status = Column(String, nullable=False, default="NONE", index=True)
    task_payload_json = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "workflow_instance_id",
            "task_code",
            name="uq_symployee_workflow_task_code",
        ),
    )


class SymployeeDocumentLifecycleEvent(AuditColumnsMixin, Base):
    __tablename__ = "symployee_document_lifecycle_events"

    event_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    identity_id = Column(
        String,
        ForeignKey("symployee_document_identities.identity_id"),
        nullable=False,
        index=True,
    )
    version_id = Column(
        String,
        ForeignKey("symployee_document_versions.version_id"),
        nullable=True,
        index=True,
    )
    event_type = Column(String, nullable=False, index=True)
    state_dimension = Column(String, nullable=False, index=True)
    previous_state = Column(String, nullable=True)
    new_state = Column(String, nullable=False)
    event_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    performed_by = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    reason = Column(Text, nullable=True)
    workflow_instance_id = Column(
        String,
        ForeignKey("symployee_workflow_instances.workflow_instance_id"),
        nullable=True,
        index=True,
    )
    transmittal_id = Column(String, nullable=True)
    approval_id = Column(
        String,
        ForeignKey("symployee_approval_records.approval_id"),
        nullable=True,
        index=True,
    )
    metadata_json = Column(JSON, default=dict)


class SymployeeAIRecommendation(AuditColumnsMixin, Base):
    __tablename__ = "symployee_ai_recommendations"

    recommendation_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    symployee_id = Column(String, ForeignKey("symployee_definitions.symployee_id"), nullable=False, index=True)
    identity_id = Column(String, ForeignKey("symployee_document_identities.identity_id"), nullable=False, index=True)
    version_id = Column(String, ForeignKey("symployee_document_versions.version_id"), nullable=True, index=True)
    recommendation_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="NEEDS_REVIEW", index=True)
    lifecycle_action_type = Column(String, nullable=True, index=True)
    lifecycle_state_dimension = Column(String, nullable=True, index=True)
    lifecycle_target_state = Column(String, nullable=True, index=True)
    recommendation_json = Column(JSON, default=dict)
    lifecycle_context_json = Column(JSON, default=dict)
    confidence_score = Column(Float, nullable=True)
    model_name = Column(String, nullable=True)
    model_provider = Column(String, nullable=True)
    prompt_profile_code = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    policy_code = Column(String, nullable=True)
    policy_version_no = Column(Integer, nullable=True)
    source_evidence_json = Column(JSON, default=dict)
    approval_outcome = Column(String, nullable=True)


class SymployeeApprovalRecord(AuditColumnsMixin, Base):
    __tablename__ = "symployee_approval_records"

    approval_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    approval_subject_type = Column(String, nullable=False, index=True)
    approval_subject_id = Column(String, nullable=False, index=True)
    decision = Column(String, nullable=False, index=True)
    approver_user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    comments = Column(Text, nullable=True)
    policy_code = Column(String, nullable=True)
    policy_version_no = Column(Integer, nullable=True)


class SymployeeOverrideRecord(AuditColumnsMixin, Base):
    __tablename__ = "symployee_override_records"

    override_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    override_subject_type = Column(String, nullable=False, index=True)
    override_subject_id = Column(String, nullable=False, index=True)
    related_recommendation_id = Column(String, ForeignKey("symployee_ai_recommendations.recommendation_id"), nullable=True, index=True)
    overridden_by_user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    reason_code = Column(String, nullable=False)
    reason_text = Column(Text, nullable=True)
    before_state_json = Column(JSON, default=dict)
    after_state_json = Column(JSON, default=dict)
    requires_second_approval = Column(Boolean, nullable=False, default=False)
    finalized_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default="EFFECTIVE", index=True)


class SymployeeTransmittal(AuditColumnsMixin, Base):
    __tablename__ = "symployee_transmittals"

    transmittal_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    transmittal_number = Column(String, nullable=False, index=True)
    direction = Column(String, nullable=False, index=True)
    purpose_code = Column(String, nullable=False, index=True)
    transmittal_status = Column(String, nullable=False, default="DRAFT", index=True)
    sender_org = Column(String, nullable=True)
    recipient_org = Column(String, nullable=True)
    response_required = Column(Boolean, nullable=False, default=False)
    response_due_at = Column(DateTime(timezone=True), nullable=True, index=True)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    prepared_by = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    issued_by = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    workflow_instance_id = Column(
        String,
        ForeignKey("symployee_workflow_instances.workflow_instance_id"),
        nullable=True,
        index=True,
    )
    subject = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "transmittal_number",
            name="uq_symployee_transmittal_number",
        ),
    )


class SymployeeConnectorCommand(AuditColumnsMixin, Base):
    __tablename__ = "symployee_connector_commands"

    command_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    agent_id = Column(String, nullable=True, index=True)
    repository_id = Column(String, ForeignKey("repositories.repository_id"), nullable=False, index=True)
    identity_id = Column(String, ForeignKey("symployee_document_identities.identity_id"), nullable=False, index=True)
    version_id = Column(String, ForeignKey("symployee_document_versions.version_id"), nullable=True, index=True)
    command_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="PENDING_APPROVAL", index=True)
    approval_status = Column(String, nullable=False, default="PENDING_APPROVAL", index=True)
    payload_json = Column(JSON, default=dict)
    policy_code = Column(String, nullable=True)
    policy_version_no = Column(Integer, nullable=True)
    source_recommendation_id = Column(String, ForeignKey("symployee_ai_recommendations.recommendation_id"), nullable=True, index=True)
    lifecycle_event_id = Column(String, ForeignKey("symployee_document_lifecycle_events.event_id"), nullable=True, index=True)
    transmittal_id = Column(String, ForeignKey("symployee_transmittals.transmittal_id"), nullable=True, index=True)
    disposition_case_id = Column(String, ForeignKey("symployee_disposition_cases.disposition_case_id"), nullable=True, index=True)
    idempotency_key = Column(String, nullable=True, index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)


class SymployeeIdempotencyRecord(AuditColumnsMixin, Base):
    __tablename__ = "symployee_idempotency_records"

    idempotency_record_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    scope_type = Column(String, nullable=False, index=True)
    scope_key = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=False, index=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    resolution_status = Column(String, nullable=False, default="accepted", index=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "scope_type",
            "idempotency_key",
            name="uq_symployee_idempotency_scope_key",
        ),
    )
