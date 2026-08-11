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


class BusinessDevelopmentExperienceItem(Base):
    __tablename__ = "bd_experience_items"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False, default="")
    business_problems_json = Column(JSON, nullable=False, default=list)
    features_json = Column(JSON, nullable=False, default=list)
    technologies_json = Column(JSON, nullable=False, default=list)
    industries_json = Column(JSON, nullable=False, default=list)
    keywords_json = Column(JSON, nullable=False, default=list)
    reusable_capabilities_json = Column(JSON, nullable=False, default=list)
    confidentiality_safe_summary = Column(Text, nullable=False, default="")
    status = Column(String, nullable=False, default="active", index=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_bd_experience_item_tenant_name"),
        Index("ix_bd_experience_items_tenant_category", "tenant_id", "category"),
    )


class BusinessDevelopmentOpportunity(Base):
    __tablename__ = "bd_opportunities"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    external_id = Column(String, nullable=True)
    source_type = Column(String, nullable=False, index=True)
    source_name = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    title = Column(String, nullable=False)
    organization_name = Column(String, nullable=False, index=True)
    organization_domain = Column(String, nullable=True, index=True)
    country = Column(String, nullable=True, index=True)
    region = Column(String, nullable=True, index=True)
    industry = Column(String, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    closing_at = Column(DateTime(timezone=True), nullable=True, index=True)
    raw_summary = Column(Text, nullable=True)
    requirement_summary = Column(Text, nullable=False)
    business_problem = Column(Text, nullable=True)
    expected_deliverables_json = Column(JSON, nullable=False, default=list)
    required_technologies_json = Column(JSON, nullable=False, default=list)
    published_budget = Column(Float, nullable=True)
    published_currency = Column(String, nullable=True)
    estimated_value_min = Column(Float, nullable=True)
    estimated_value_max = Column(Float, nullable=True)
    estimated_currency = Column(String, nullable=True)
    fit_score = Column(Float, nullable=True, index=True)
    confidence_score = Column(Float, nullable=True)
    ai_recommendation = Column(Text, nullable=True)
    opportunity_status = Column(String, nullable=False, default="new", index=True)
    source_evidence_json = Column(JSON, nullable=False, default=list)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source_type",
            "external_id",
            name="uq_bd_opportunity_tenant_source_external",
        ),
        Index("ix_bd_opportunities_tenant_status", "tenant_id", "opportunity_status"),
        Index("ix_bd_opportunities_tenant_closing", "tenant_id", "closing_at"),
        Index("ix_bd_opportunities_tenant_fit", "tenant_id", "fit_score"),
        Index("ix_bd_opportunities_tenant_domain", "tenant_id", "organization_domain"),
        Index("ix_bd_opportunities_tenant_source_url", "tenant_id", "source_url"),
    )


class BusinessDevelopmentProspect(Base):
    __tablename__ = "bd_prospects"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    organization_name = Column(String, nullable=False, index=True)
    organization_domain = Column(String, nullable=True, index=True)
    website_url = Column(String, nullable=True)
    country = Column(String, nullable=True, index=True)
    region = Column(String, nullable=True, index=True)
    city = Column(String, nullable=True, index=True)
    industry = Column(String, nullable=True, index=True)
    organization_type = Column(String, nullable=True, index=True)
    employee_range = Column(String, nullable=True)
    general_email = Column(String, nullable=True, index=True)
    general_phone = Column(String, nullable=True)
    prospect_status = Column(String, nullable=False, default="active", index=True)
    estimated_account_potential_min = Column(Float, nullable=True)
    estimated_account_potential_max = Column(Float, nullable=True)
    estimated_currency = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    source_opportunity_id = Column(String, ForeignKey("bd_opportunities.id"), nullable=True, index=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "organization_name",
            "organization_domain",
            name="uq_bd_prospect_tenant_name_domain",
        ),
        Index("ix_bd_prospects_tenant_status", "tenant_id", "prospect_status"),
        Index("ix_bd_prospects_tenant_domain", "tenant_id", "organization_domain"),
    )


class BusinessDevelopmentContact(Base):
    __tablename__ = "bd_contacts"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    prospect_id = Column(String, ForeignKey("bd_prospects.id"), nullable=False, index=True)
    full_name = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True, index=True)
    phone = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    department = Column(String, nullable=True)
    buyer_role = Column(String, nullable=True, index=True)
    linkedin_url = Column(String, nullable=True)
    company_profile_url = Column(String, nullable=True)
    contact_source = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    evidence_text = Column(Text, nullable=True)
    verification_status = Column(String, nullable=False, default="unverified", index=True)
    confidence_score = Column(Float, nullable=True)
    contact_status = Column(String, nullable=False, default="active", index=True)
    is_primary = Column(Boolean, nullable=False, default=False, index=True)
    notes = Column(Text, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "prospect_id",
            "email",
            name="uq_bd_contact_tenant_prospect_email",
        ),
        Index("ix_bd_contacts_tenant_status", "tenant_id", "contact_status"),
    )


class BusinessDevelopmentLead(Base):
    __tablename__ = "bd_leads"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    opportunity_id = Column(String, ForeignKey("bd_opportunities.id"), nullable=False, index=True)
    prospect_id = Column(String, ForeignKey("bd_prospects.id"), nullable=False, index=True)
    primary_contact_id = Column(String, ForeignKey("bd_contacts.id"), nullable=True, index=True)
    title = Column(String, nullable=False, index=True)
    lead_stage = Column(String, nullable=False, default="new", index=True)
    lead_status = Column(String, nullable=False, default="active", index=True)
    priority = Column(String, nullable=False, default="medium", index=True)
    source_type = Column(String, nullable=True, index=True)
    source_name = Column(String, nullable=True)
    estimated_value = Column(Float, nullable=True)
    weighted_value = Column(Float, nullable=True)
    probability_pct = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_bd_leads_tenant_stage", "tenant_id", "lead_stage"),
        Index("ix_bd_leads_tenant_status", "tenant_id", "lead_status"),
        Index("ix_bd_leads_tenant_opportunity", "tenant_id", "opportunity_id"),
    )


class BusinessDevelopmentLeadExperienceMatch(Base):
    __tablename__ = "bd_lead_experience_matches"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    lead_id = Column(String, ForeignKey("bd_leads.id"), nullable=False, index=True)
    experience_item_id = Column(String, ForeignKey("bd_experience_items.id"), nullable=False, index=True)
    relevance_score = Column(Float, nullable=True)
    match_notes = Column(Text, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "lead_id",
            "experience_item_id",
            name="uq_bd_lead_experience_match",
        ),
    )


class BusinessDevelopmentTask(Base):
    __tablename__ = "bd_tasks"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    lead_id = Column(String, ForeignKey("bd_leads.id"), nullable=False, index=True)
    opportunity_id = Column(String, ForeignKey("bd_opportunities.id"), nullable=True, index=True)
    prospect_id = Column(String, ForeignKey("bd_prospects.id"), nullable=True, index=True)
    assigned_user_id = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String, nullable=False, default="follow_up", index=True)
    task_status = Column(String, nullable=False, default="open", index=True)
    priority = Column(String, nullable=False, default="medium", index=True)
    due_at = Column(DateTime(timezone=True), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    completed_by = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    completion_notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_bd_tasks_tenant_status", "tenant_id", "task_status"),
        Index("ix_bd_tasks_tenant_due", "tenant_id", "due_at"),
        Index("ix_bd_tasks_tenant_priority", "tenant_id", "priority"),
    )


class BusinessDevelopmentActivity(Base):
    __tablename__ = "bd_activities"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    lead_id = Column(String, ForeignKey("bd_leads.id"), nullable=True, index=True)
    opportunity_id = Column(String, ForeignKey("bd_opportunities.id"), nullable=True, index=True)
    prospect_id = Column(String, ForeignKey("bd_prospects.id"), nullable=True, index=True)
    contact_id = Column(String, ForeignKey("bd_contacts.id"), nullable=True, index=True)
    activity_type = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    activity_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    direction = Column(String, nullable=True, index=True)
    outcome = Column(String, nullable=True, index=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_bd_activities_tenant_type", "tenant_id", "activity_type"),
        Index("ix_bd_activities_tenant_activity_at", "tenant_id", "activity_at"),
    )


class BusinessDevelopmentSearchProfile(Base):
    __tablename__ = "bd_search_profiles"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    target_regions_json = Column(JSON, nullable=False, default=list)
    target_countries_json = Column(JSON, nullable=False, default=list)
    target_industries_json = Column(JSON, nullable=False, default=list)
    include_keywords_json = Column(JSON, nullable=False, default=list)
    include_technologies_json = Column(JSON, nullable=False, default=list)
    include_capabilities_json = Column(JSON, nullable=False, default=list)
    exclude_keywords_json = Column(JSON, nullable=False, default=list)
    excluded_domains_json = Column(JSON, nullable=False, default=list)
    excluded_categories_json = Column(JSON, nullable=False, default=list)
    minimum_budget = Column(Float, nullable=True)
    currencies_json = Column(JSON, nullable=False, default=list)
    allow_budget_unknown = Column(Boolean, nullable=False, default=True)
    solo_feasibility_preference = Column(String, nullable=True)
    small_team_allowed = Column(Boolean, nullable=False, default=True)
    max_delivery_months = Column(Integer, nullable=True)
    max_age_days = Column(Integer, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_bd_search_profile_tenant_name"),
        Index("ix_bd_search_profiles_tenant_enabled", "tenant_id", "enabled"),
    )


class BusinessDevelopmentConnector(Base):
    __tablename__ = "bd_connectors"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    search_profile_id = Column(
        String,
        ForeignKey("bd_search_profiles.id"),
        nullable=True,
        index=True,
    )
    connector_type = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    source_category = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="configured", index=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    schedule_enabled = Column(Boolean, nullable=False, default=False, index=True)
    schedule_expression = Column(String, nullable=True)
    schedule_type = Column(String, nullable=False, default="manual", index=True)
    schedule_interval_minutes = Column(Integer, nullable=True)
    schedule_day_of_week = Column(Integer, nullable=True)
    schedule_time_local = Column(String, nullable=True)
    schedule_timezone = Column(String, nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_scheduled_run_at = Column(DateTime(timezone=True), nullable=True)
    schedule_retry_count = Column(Integer, nullable=False, default=0)
    schedule_retry_run_id = Column(String, nullable=True)
    active_run_id = Column(String, nullable=True, index=True)
    schedule_updated_by = Column(String, nullable=True)
    schedule_updated_at = Column(DateTime(timezone=True), nullable=True)
    configuration_json = Column(JSON, nullable=False, default=dict)
    search_criteria_json = Column(JSON, nullable=False, default=dict)
    capability_flags_json = Column(JSON, nullable=False, default=dict)
    last_scan_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)
    last_error_message = Column(Text, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_bd_connector_tenant_name"),
        Index("ix_bd_connectors_tenant_type", "tenant_id", "connector_type"),
        Index("ix_bd_connectors_tenant_status", "tenant_id", "status"),
    )


class BusinessDevelopmentSearchProvider(Base):
    __tablename__ = "bd_search_providers"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=True, index=True)
    provider_code = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    provider_type = Column(String, nullable=False, index=True)
    adapter_code = Column(String, nullable=True, index=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    credential_type = Column(String, nullable=False, default="api_key")
    configuration_json = Column(JSON, nullable=False, default=dict)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_bd_search_providers_scope_code", "tenant_id", "provider_code"),
        Index("ix_bd_search_providers_scope_enabled", "tenant_id", "enabled"),
    )


class BusinessDevelopmentConnectorSecret(Base):
    __tablename__ = "bd_connector_secrets"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    connector_id = Column(String, ForeignKey("bd_connectors.id"), nullable=True, index=True)
    provider = Column(String, nullable=False, index=True)
    credential_type = Column(String, nullable=False, default="api_key", index=True)
    encrypted_value = Column(Text, nullable=False)
    key_version = Column(String, nullable=False, default="v1")
    status = Column(String, nullable=False, default="active", index=True)
    last_four = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by = Column(String, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    last_test_status = Column(String, nullable=True)
    last_test_error = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "provider",
            "credential_type",
            name="uq_bd_connector_secret_tenant_provider_type",
        ),
        Index("ix_bd_connector_secrets_tenant_provider", "tenant_id", "provider"),
    )


class BusinessDevelopmentConnectorRun(Base):
    __tablename__ = "bd_connector_runs"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    connector_id = Column(String, ForeignKey("bd_connectors.id"), nullable=False, index=True)
    run_type = Column(String, nullable=False, default="manual", index=True)
    status = Column(String, nullable=False, default="queued", index=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    max_attempts = Column(Integer, nullable=False, default=1)
    retry_of_run_id = Column(String, ForeignKey("bd_connector_runs.id"), nullable=True, index=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    items_found = Column(Integer, nullable=False, default=0)
    items_new = Column(Integer, nullable=False, default=0)
    items_duplicate = Column(Integer, nullable=False, default=0)
    items_filtered = Column(Integer, nullable=False, default=0)
    items_failed = Column(Integer, nullable=False, default=0)
    error_summary = Column(Text, nullable=True)
    run_metadata_json = Column(JSON, nullable=False, default=dict)
    initiated_by = Column(String, ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index(
            "ix_bd_connector_runs_tenant_connector_started",
            "tenant_id",
            "connector_id",
            "started_at",
        ),
        Index("ix_bd_connector_runs_tenant_status_started", "tenant_id", "status", "started_at"),
    )


class BusinessDevelopmentDiscoveredOpportunity(Base):
    __tablename__ = "bd_discovered_opportunities"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    connector_id = Column(String, ForeignKey("bd_connectors.id"), nullable=False, index=True)
    connector_run_id = Column(String, ForeignKey("bd_connector_runs.id"), nullable=True, index=True)
    external_id = Column(String, nullable=True)
    source_type = Column(String, nullable=False, index=True)
    source_name = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    canonical_source_url = Column(String, nullable=True)
    source_domain = Column(String, nullable=True, index=True)
    source_country = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False)
    normalized_title = Column(String, nullable=False)
    organization_name = Column(String, nullable=True, index=True)
    normalized_organization_name = Column(String, nullable=True, index=True)
    published_date = Column(DateTime(timezone=True), nullable=True, index=True)
    closing_date = Column(DateTime(timezone=True), nullable=True, index=True)
    raw_summary = Column(Text, nullable=True)
    requirement_summary = Column(Text, nullable=True)
    normalized_content_json = Column(JSON, nullable=False, default=dict)
    raw_content_json = Column(JSON, nullable=False, default=dict)
    raw_text = Column(Text, nullable=True)
    country = Column(String, nullable=True, index=True)
    region = Column(String, nullable=True, index=True)
    industry = Column(String, nullable=True, index=True)
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    currency = Column(String, nullable=True, index=True)
    discovered_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    retrieval_timestamp = Column(DateTime(timezone=True), nullable=True)
    discovery_status = Column(String, nullable=False, default="new", index=True)
    duplicate_of_discovery_id = Column(
        String,
        ForeignKey("bd_discovered_opportunities.id"),
        nullable=True,
        index=True,
    )
    possible_duplicate_of_discovery_id = Column(
        String,
        ForeignKey("bd_discovered_opportunities.id"),
        nullable=True,
        index=True,
    )
    imported_opportunity_id = Column(
        String,
        ForeignKey("bd_opportunities.id"),
        nullable=True,
        index=True,
    )
    preliminary_relevance_score = Column(Float, nullable=True, index=True)
    commercial_priority_score = Column(Float, nullable=True, index=True)
    commercial_priority_band = Column(String, nullable=True, index=True)
    commercial_recommendation = Column(String, nullable=True, index=True)
    commercial_component_scores_json = Column(JSON, nullable=False, default=dict)
    commercial_recommendation_reasons_json = Column(JSON, nullable=False, default=list)
    commercial_risks_json = Column(JSON, nullable=False, default=list)
    experience_match_score = Column(Float, nullable=True)
    matched_experience_ids_json = Column(JSON, nullable=False, default=list)
    matched_experience_reasons_json = Column(JSON, nullable=False, default=list)
    matched_experience_summary_json = Column(JSON, nullable=False, default=list)
    delivery_feasibility_score = Column(Float, nullable=True)
    delivery_complexity = Column(String, nullable=True, index=True)
    delivery_model = Column(String, nullable=True)
    urgency_status = Column(String, nullable=True, index=True)
    data_quality_status = Column(String, nullable=True)
    intelligence_updated_at = Column(DateTime(timezone=True), nullable=True)
    relevance_reasons_json = Column(JSON, nullable=False, default=list)
    matched_keywords_json = Column(JSON, nullable=False, default=list)
    evidence_json = Column(JSON, nullable=False, default=list)
    normalized_search_text = Column(Text, nullable=True)
    url_fingerprint = Column(String, nullable=True, index=True)
    composite_fingerprint = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "connector_id",
            "external_id",
            name="uq_bd_discovery_tenant_connector_external",
        ),
        Index("ix_bd_discoveries_tenant_status", "tenant_id", "discovery_status"),
        Index("ix_bd_discoveries_tenant_connector", "tenant_id", "connector_id"),
        Index("ix_bd_discoveries_tenant_discovered", "tenant_id", "discovered_at"),
        Index("ix_bd_discoveries_tenant_closing", "tenant_id", "closing_date"),
        Index("ix_bd_discoveries_tenant_imported", "tenant_id", "imported_opportunity_id"),
        Index(
            "ix_bd_discoveries_tenant_priority",
            "tenant_id",
            "commercial_priority_score",
            "commercial_recommendation",
        ),
    )


class BusinessDevelopmentWebSeed(Base):
    __tablename__ = "bd_web_seeds"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    connector_id = Column(String, ForeignKey("bd_connectors.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    seed_url = Column(String, nullable=False)
    seed_type = Column(String, nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    crawl_scope = Column(String, nullable=False, default="same_domain")
    max_depth = Column(Integer, nullable=False, default=2)
    max_pages = Column(Integer, nullable=False, default=25)
    crawl_frequency = Column(String, nullable=False, default="weekly", index=True)
    priority = Column(Integer, nullable=False, default=50, index=True)
    country = Column(String, nullable=True, index=True)
    industry = Column(String, nullable=True, index=True)
    organization_name = Column(String, nullable=True, index=True)
    notes = Column(Text, nullable=True)
    last_crawled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    next_crawl_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "connector_id", "seed_url", name="uq_bd_web_seed_tenant_connector_url"),
        Index("ix_bd_web_seeds_tenant_connector_priority", "tenant_id", "connector_id", "priority"),
    )


class BusinessDevelopmentWebDomain(Base):
    __tablename__ = "bd_web_domains"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    connector_id = Column(String, ForeignKey("bd_connectors.id"), nullable=False, index=True)
    seed_id = Column(String, ForeignKey("bd_web_seeds.id"), nullable=True, index=True)
    domain = Column(String, nullable=False, index=True)
    source = Column(String, nullable=True)
    proposed_type = Column(String, nullable=True, index=True)
    trust_source_type = Column(String, nullable=True, index=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    approval_status = Column(String, nullable=False, default="approved", index=True)
    robots_status = Column(String, nullable=False, default="unknown", index=True)
    robots_crawl_delay_seconds = Column(Integer, nullable=True)
    robots_fetched_at = Column(DateTime(timezone=True), nullable=True)
    robots_url = Column(String, nullable=True)
    found_from_url = Column(String, nullable=True)
    found_context = Column(Text, nullable=True)
    pages_indexed = Column(Integer, nullable=False, default=0)
    opportunities_found = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    last_crawl_at = Column(DateTime(timezone=True), nullable=True, index=True)
    next_crawl_at = Column(DateTime(timezone=True), nullable=True, index=True)
    status = Column(String, nullable=False, default="ready", index=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "connector_id", "domain", name="uq_bd_web_domain_tenant_connector_domain"),
        Index("ix_bd_web_domains_tenant_connector_status", "tenant_id", "connector_id", "status"),
    )


class BusinessDevelopmentWebFrontier(Base):
    __tablename__ = "bd_web_frontier"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    connector_id = Column(String, ForeignKey("bd_connectors.id"), nullable=False, index=True)
    seed_id = Column(String, ForeignKey("bd_web_seeds.id"), nullable=True, index=True)
    domain_id = Column(String, ForeignKey("bd_web_domains.id"), nullable=True, index=True)
    url = Column(String, nullable=False)
    canonical_url = Column(String, nullable=False)
    domain = Column(String, nullable=False, index=True)
    parent_url = Column(String, nullable=True)
    anchor_text = Column(String, nullable=True)
    link_context = Column(Text, nullable=True)
    depth = Column(Integer, nullable=False, default=0, index=True)
    priority = Column(Float, nullable=False, default=0, index=True)
    status = Column(String, nullable=False, default="queued", index=True)
    discovered_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    last_attempted_at = Column(DateTime(timezone=True), nullable=True)
    last_fetched_at = Column(DateTime(timezone=True), nullable=True)
    next_fetch_at = Column(DateTime(timezone=True), nullable=True, index=True)
    http_status = Column(Integer, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    content_hash = Column(String, nullable=True, index=True)
    error_code = Column(String, nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    diagnostic_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "connector_id", "canonical_url", name="uq_bd_web_frontier_tenant_connector_canonical"),
        Index("ix_bd_web_frontier_tenant_connector_status_priority", "tenant_id", "connector_id", "status", "priority"),
    )


class BusinessDevelopmentWebPage(Base):
    __tablename__ = "bd_web_pages"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    connector_id = Column(String, ForeignKey("bd_connectors.id"), nullable=False, index=True)
    seed_id = Column(String, ForeignKey("bd_web_seeds.id"), nullable=True, index=True)
    domain_id = Column(String, ForeignKey("bd_web_domains.id"), nullable=True, index=True)
    url = Column(String, nullable=False)
    canonical_url = Column(String, nullable=False)
    domain = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    plain_text = Column(Text, nullable=True)
    safe_html = Column(Text, nullable=True)
    language = Column(String, nullable=True, index=True)
    page_type = Column(String, nullable=False, default="unknown", index=True)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_modified_at = Column(DateTime(timezone=True), nullable=True)
    content_hash = Column(String, nullable=True, index=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    last_changed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    http_status = Column(Integer, nullable=True)
    source_metadata_json = Column(JSON, nullable=False, default=dict)
    contact_routes_json = Column(JSON, nullable=False, default=list)
    opportunity_candidate_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "connector_id", "canonical_url", name="uq_bd_web_page_tenant_connector_canonical"),
        Index("ix_bd_web_pages_tenant_connector_type", "tenant_id", "connector_id", "page_type"),
        Index("ix_bd_web_pages_tenant_domain_changed", "tenant_id", "domain", "last_changed_at"),
    )


class BusinessDevelopmentDiscoveryTranslation(Base):
    __tablename__ = "bd_discovery_translations"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    discovery_id = Column(
        String,
        ForeignKey("bd_discovered_opportunities.id"),
        nullable=False,
        index=True,
    )
    translation_version = Column(Integer, nullable=False)
    source_language = Column(String, nullable=False, index=True)
    target_language = Column(String, nullable=False, index=True, server_default="en")
    source_content_hash = Column(String, nullable=False, index=True)
    translated_title = Column(Text, nullable=True)
    translated_summary = Column(Text, nullable=True)
    translated_description = Column(Text, nullable=True)
    translated_detail_json = Column(JSON, nullable=False, default=dict)
    provider = Column(String, nullable=False, server_default="openai")
    model = Column(String, nullable=False)
    prompt_bundle_version = Column(String, nullable=False, server_default="phase5c4_v1")
    prompt_version = Column(String, nullable=False, server_default="discovery_translation_v1")
    usage_json = Column(JSON, nullable=False, default=dict)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "discovery_id",
            "translation_version",
            name="uq_bd_discovery_translation_version",
        ),
        Index(
            "ix_bd_discovery_translations_tenant_discovery_created",
            "tenant_id",
            "discovery_id",
            "created_at",
        ),
        Index(
            "ix_bd_discovery_translations_tenant_discovery_target_hash",
            "tenant_id",
            "discovery_id",
            "target_language",
            "source_content_hash",
        ),
    )


class BusinessDevelopmentDiscoveryAIAssessment(Base):
    __tablename__ = "bd_discovery_ai_assessments"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    discovery_id = Column(
        String,
        ForeignKey("bd_discovered_opportunities.id"),
        nullable=False,
        index=True,
    )
    analysis_version = Column(Integer, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt_bundle_version = Column(String, nullable=False, default="phase5f_v1")
    prompt_version = Column(String, nullable=False, default="discovery_deep_assess_v1")
    recommendation = Column(String, nullable=True, index=True)
    recommendation_confidence = Column(Float, nullable=True)
    commercial_score = Column(Float, nullable=True)
    delivery_feasibility_score = Column(Float, nullable=True)
    executive_summary = Column(Text, nullable=True)
    analysis_json = Column(JSON, nullable=False, default=dict)
    usage_json = Column(JSON, nullable=False, default=dict)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "discovery_id",
            "analysis_version",
            name="uq_bd_discovery_ai_assessment_version",
        ),
        Index(
            "ix_bd_discovery_ai_assessments_tenant_discovery_created",
            "tenant_id",
            "discovery_id",
            "created_at",
        ),
    )


class BusinessDevelopmentOpportunityAIAssessment(Base):
    __tablename__ = "bd_opportunity_ai_assessments"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    opportunity_id = Column(String, ForeignKey("bd_opportunities.id"), nullable=False, index=True)
    assessment_version = Column(Integer, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt_bundle_version = Column(String, nullable=False, default="phase4a_v1")
    requirement_extraction_json = Column(JSON, nullable=False, default=dict)
    qualification_json = Column(JSON, nullable=False, default=dict)
    buyer_roles_json = Column(JSON, nullable=False, default=dict)
    final_fit_score = Column(Float, nullable=True, index=True)
    confidence_score = Column(Float, nullable=True)
    recommendation = Column(String, nullable=True, index=True)
    risks_json = Column(JSON, nullable=False, default=list)
    missing_information_json = Column(JSON, nullable=False, default=list)
    ai_run_summary_json = Column(JSON, nullable=False, default=dict)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "opportunity_id",
            "assessment_version",
            name="uq_bd_opportunity_ai_assessment_version",
        ),
        Index(
            "ix_bd_opportunity_ai_assessments_tenant_opportunity_created",
            "tenant_id",
            "opportunity_id",
            "created_at",
        ),
    )


class BusinessDevelopmentOpportunityExperienceMatch(Base):
    __tablename__ = "bd_opportunity_experience_matches"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    opportunity_id = Column(String, ForeignKey("bd_opportunities.id"), nullable=False, index=True)
    assessment_id = Column(
        String,
        ForeignKey("bd_opportunity_ai_assessments.id"),
        nullable=False,
        index=True,
    )
    experience_item_id = Column(String, ForeignKey("bd_experience_items.id"), nullable=False, index=True)
    match_score = Column(Float, nullable=True)
    matching_capabilities_json = Column(JSON, nullable=False, default=list)
    matching_technologies_json = Column(JSON, nullable=False, default=list)
    business_problem_similarity = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "assessment_id",
            "experience_item_id",
            name="uq_bd_opportunity_assessment_experience_match",
        ),
        Index(
            "ix_bd_opportunity_experience_matches_tenant_opportunity_score",
            "tenant_id",
            "opportunity_id",
            "match_score",
        ),
    )


class BusinessDevelopmentOutreachDraft(Base):
    __tablename__ = "bd_outreach_drafts"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    opportunity_id = Column(String, ForeignKey("bd_opportunities.id"), nullable=False, index=True)
    lead_id = Column(String, ForeignKey("bd_leads.id"), nullable=True, index=True)
    prospect_id = Column(String, ForeignKey("bd_prospects.id"), nullable=True, index=True)
    contact_id = Column(String, ForeignKey("bd_contacts.id"), nullable=True, index=True)
    outreach_type = Column(String, nullable=False, index=True)
    tone = Column(String, nullable=False, index=True)
    subject = Column(Text, nullable=True)
    body = Column(Text, nullable=False)
    structured_content_json = Column(JSON, nullable=False, default=dict)
    generation_version = Column(Integer, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt_bundle_version = Column(String, nullable=False, default="phase4b_v1")
    status = Column(String, nullable=False, default="draft", index=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "opportunity_id",
            "lead_id",
            "outreach_type",
            "generation_version",
            name="uq_bd_outreach_draft_generation_version",
        ),
        Index(
            "ix_bd_outreach_drafts_tenant_scope_created",
            "tenant_id",
            "opportunity_id",
            "lead_id",
            "created_at",
        ),
    )


class BusinessDevelopmentMiniSolution(Base):
    __tablename__ = "bd_mini_solutions"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    opportunity_id = Column(String, ForeignKey("bd_opportunities.id"), nullable=False, index=True)
    lead_id = Column(String, ForeignKey("bd_leads.id"), nullable=True, index=True)
    assessment_id = Column(
        String,
        ForeignKey("bd_opportunity_ai_assessments.id"),
        nullable=True,
        index=True,
    )
    title = Column(String, nullable=False)
    solution_json = Column(JSON, nullable=False, default=dict)
    generation_version = Column(Integer, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt_bundle_version = Column(String, nullable=False, default="phase4b_v1")
    status = Column(String, nullable=False, default="draft", index=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "opportunity_id",
            "lead_id",
            "generation_version",
            name="uq_bd_mini_solution_generation_version",
        ),
        Index(
            "ix_bd_mini_solutions_tenant_scope_created",
            "tenant_id",
            "opportunity_id",
            "lead_id",
            "created_at",
        ),
    )


class BusinessDevelopmentReply(Base):
    __tablename__ = "bd_replies"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    opportunity_id = Column(String, ForeignKey("bd_opportunities.id"), nullable=True, index=True)
    lead_id = Column(String, ForeignKey("bd_leads.id"), nullable=False, index=True)
    prospect_id = Column(String, ForeignKey("bd_prospects.id"), nullable=True, index=True)
    contact_id = Column(String, ForeignKey("bd_contacts.id"), nullable=True, index=True)
    outreach_id = Column(String, ForeignKey("bd_outreach_drafts.id"), nullable=True, index=True)
    channel = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=True)
    raw_message = Column(Text, nullable=False)
    sender_display = Column(String, nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=False, index=True)
    reply_status = Column(String, nullable=False, default="received", index=True)
    notes = Column(Text, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_bd_replies_tenant_received", "tenant_id", "received_at"),
        Index("ix_bd_replies_tenant_status", "tenant_id", "reply_status"),
        Index("ix_bd_replies_tenant_lead", "tenant_id", "lead_id"),
    )


class BusinessDevelopmentReplyAIAnalysis(Base):
    __tablename__ = "bd_reply_ai_analyses"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    reply_id = Column(String, ForeignKey("bd_replies.id"), nullable=False, index=True)
    analysis_version = Column(Integer, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt_bundle_version = Column(String, nullable=False, default="phase4c_v1")
    intent = Column(String, nullable=False, index=True)
    sentiment = Column(String, nullable=False, index=True)
    engagement_level = Column(String, nullable=False, index=True)
    urgency = Column(String, nullable=False, index=True)
    objection_category = Column(String, nullable=True, index=True)
    recommended_pipeline_stage = Column(String, nullable=True, index=True)
    recommended_next_action = Column(Text, nullable=False)
    analysis_json = Column(JSON, nullable=False, default=dict)
    confidence_score = Column(Float, nullable=False)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "reply_id",
            "analysis_version",
            name="uq_bd_reply_ai_analysis_version",
        ),
        Index(
            "ix_bd_reply_ai_analyses_tenant_reply_created",
            "tenant_id",
            "reply_id",
            "created_at",
        ),
    )


class BusinessDevelopmentReplyResponseDraft(Base):
    __tablename__ = "bd_reply_response_drafts"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    reply_id = Column(String, ForeignKey("bd_replies.id"), nullable=False, index=True)
    opportunity_id = Column(String, ForeignKey("bd_opportunities.id"), nullable=True, index=True)
    lead_id = Column(String, ForeignKey("bd_leads.id"), nullable=False, index=True)
    prospect_id = Column(String, ForeignKey("bd_prospects.id"), nullable=True, index=True)
    contact_id = Column(String, ForeignKey("bd_contacts.id"), nullable=True, index=True)
    analysis_id = Column(String, ForeignKey("bd_reply_ai_analyses.id"), nullable=True, index=True)
    tone = Column(String, nullable=False, index=True)
    subject = Column(Text, nullable=True)
    body = Column(Text, nullable=False)
    structured_content_json = Column(JSON, nullable=False, default=dict)
    generation_version = Column(Integer, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt_bundle_version = Column(String, nullable=False, default="phase4c_v1")
    status = Column(String, nullable=False, default="draft", index=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "reply_id",
            "generation_version",
            name="uq_bd_reply_response_generation_version",
        ),
        Index(
            "ix_bd_reply_response_drafts_tenant_reply_created",
            "tenant_id",
            "reply_id",
            "created_at",
        ),
    )


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
