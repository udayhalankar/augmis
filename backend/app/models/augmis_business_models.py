from __future__ import annotations

from datetime import datetime
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator


CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
ALLOWED_BUYER_ROLES = {
    "economic_buyer",
    "operational_owner",
    "technical_evaluator",
    "procurement_contact",
    "influencer",
    "general_contact",
    "unknown",
}
ALLOWED_VERIFICATION_STATUSES = {
    "published_by_buyer",
    "official_company_website",
    "public_professional_profile",
    "licensed_enrichment",
    "provider_verified",
    "pattern_inferred",
    "unverified",
    "rejected",
}
ALLOWED_OUTREACH_TYPES = {
    "initial_email",
    "linkedin_message",
    "executive_intro",
    "follow_up_email",
    "procurement_clarification",
}
ALLOWED_OUTREACH_TONES = {
    "concise",
    "consultative",
    "executive",
    "technical",
    "procurement",
}
ALLOWED_GENERATION_STATUSES = {
    "draft",
    "reviewed",
    "approved",
    "rejected",
    "superseded",
}
ALLOWED_REPLY_CHANNELS = {
    "email",
    "linkedin",
    "phone_summary",
    "meeting_note",
    "website_message",
    "procurement_portal",
    "other",
}
ALLOWED_REPLY_STATUSES = {
    "received",
    "analyzed",
    "action_required",
    "responded",
    "archived",
}
ALLOWED_REPLY_INTENTS = {
    "interested",
    "needs_more_information",
    "meeting_requested",
    "demo_requested",
    "proposal_requested",
    "pricing_requested",
    "technical_questions",
    "procurement_process",
    "legal_compliance",
    "objection",
    "defer",
    "not_interested",
    "wrong_contact",
    "referral",
    "out_of_office",
    "neutral",
    "unclear",
}
ALLOWED_REPLY_SENTIMENTS = {"positive", "neutral", "negative", "mixed", "unclear"}
ALLOWED_REPLY_ENGAGEMENT_LEVELS = {"high", "medium", "low", "none", "unclear"}
ALLOWED_REPLY_URGENCY_LEVELS = {"urgent", "high", "normal", "low"}
ALLOWED_REPLY_OBJECTION_CATEGORIES = {
    "price",
    "budget",
    "timing",
    "technical_fit",
    "security",
    "compliance",
    "integration",
    "internal_priority",
    "incumbent_vendor",
    "resource_constraints",
    "authority",
    "procurement",
    "unclear_value",
    "other",
}
VERIFIED_CONTACT_STATUSES = {
    "published_by_buyer",
    "official_company_website",
    "provider_verified",
}
ALLOWED_REPLY_RESPONSE_STRATEGIES = {
    "concise",
    "consultative",
    "technical",
    "executive",
    "objection_handling",
    "procurement",
}
ALLOWED_REPLY_TASK_TYPES = {
    "research",
    "contact",
    "follow_up",
    "discovery",
    "proposal",
    "review",
    "general",
}
ALLOWED_CONNECTOR_SOURCE_CATEGORIES = {
    "fixture",
    "manual",
    "rss",
    "api",
    "search",
    "procurement",
    "marketplace",
    "company_source",
}
ALLOWED_CONNECTOR_STATUSES = {"configured", "ready", "running", "error", "disabled", "attention"}
ALLOWED_CONNECTOR_RUN_TYPES = {"manual", "scheduled", "retry", "test"}
ALLOWED_CONNECTOR_RUN_STATUSES = {"queued", "running", "completed", "partial", "failed", "cancelled"}
ALLOWED_CONNECTOR_SCHEDULE_TYPES = {"manual", "hourly_interval", "daily", "weekly"}
ALLOWED_CONNECTOR_SCHEDULE_WEEKDAYS = set(range(7))
ALLOWED_SEARCH_PROVIDER_TYPES = {"builtin", "generic_rest"}
ALLOWED_SEARCH_PROVIDER_CREDENTIAL_TYPES = {"api_key", "bearer_token"}
ALLOWED_SEARCH_PROVIDER_AUTH_TYPES = {"api_key_header", "bearer_token"}
ALLOWED_SEARCH_PROVIDER_HTTP_METHODS = {"get", "post"}
ALLOWED_DISCOVERY_STATUSES = {
    "new",
    "reviewing",
    "shortlisted",
    "rejected",
    "duplicate",
    "imported",
    "expired",
    "irrelevant",
}
ALLOWED_WEB_SEED_TYPES = {
    "domain",
    "url",
    "sitemap",
    "procurement_portal",
    "career_portal",
    "target_account",
    "industry_directory",
    "government_portal",
    "university",
    "public_organization",
}
ALLOWED_WEB_SEED_SCOPES = {"same_domain", "approved_domains", "cross_domain_trusted"}
ALLOWED_WEB_SEED_FREQUENCIES = {"daily", "weekly", "monthly", "manual"}
ALLOWED_WEB_DOMAIN_APPROVAL_STATUSES = {"approved", "pending_review", "ignored"}


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _validate_email(value: str | None, label: str) -> str | None:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise ValueError(f"{label} must be a valid email address")
    return normalized


def _validate_currency(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    normalized = normalized.upper()
    if not CURRENCY_PATTERN.match(normalized):
        raise ValueError("Currency must be a 3-letter uppercase code")
    return normalized


def _validate_timezone_name(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    try:
        ZoneInfo(normalized)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Unknown timezone") from exc
    return normalized


def _validate_non_negative(value: float | None, label: str) -> float | None:
    if value is None:
        return None
    if value < 0:
        raise ValueError(f"{label} must be non-negative")
    return value


class AugmisBusinessOpportunityCreateRequest(BaseModel):
    external_id: str | None = None
    source_type: str = Field(min_length=1, max_length=100)
    source_name: str = Field(min_length=1, max_length=255)
    source_url: str | None = None
    title: str = Field(min_length=1, max_length=500)
    organization_name: str = Field(min_length=1, max_length=255)
    organization_domain: str | None = None
    country: str | None = None
    region: str | None = None
    industry: str | None = None
    published_at: datetime | None = None
    closing_at: datetime | None = None
    raw_summary: str | None = None
    requirement_summary: str = Field(min_length=1)
    business_problem: str | None = None
    expected_deliverables_json: list[str] = Field(default_factory=list)
    required_technologies_json: list[str] = Field(default_factory=list)
    published_budget: float | None = None
    published_currency: str | None = None
    estimated_value_min: float | None = None
    estimated_value_max: float | None = None
    estimated_currency: str | None = None
    fit_score: float | None = None
    confidence_score: float | None = None
    ai_recommendation: str | None = None
    opportunity_status: str = Field(default="new", min_length=1, max_length=50)
    source_evidence_json: list[dict[str, str]] = Field(default_factory=list)


class AugmisBusinessOpportunityUpdateRequest(BaseModel):
    external_id: str | None = None
    source_type: str | None = Field(default=None, min_length=1, max_length=100)
    source_name: str | None = Field(default=None, min_length=1, max_length=255)
    source_url: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=500)
    organization_name: str | None = Field(default=None, min_length=1, max_length=255)
    organization_domain: str | None = None
    country: str | None = None
    region: str | None = None
    industry: str | None = None
    published_at: datetime | None = None
    closing_at: datetime | None = None
    raw_summary: str | None = None
    requirement_summary: str | None = Field(default=None, min_length=1)
    business_problem: str | None = None
    expected_deliverables_json: list[str] | None = None
    required_technologies_json: list[str] | None = None
    published_budget: float | None = None
    published_currency: str | None = None
    estimated_value_min: float | None = None
    estimated_value_max: float | None = None
    estimated_currency: str | None = None
    fit_score: float | None = None
    confidence_score: float | None = None
    ai_recommendation: str | None = None
    opportunity_status: str | None = Field(default=None, min_length=1, max_length=50)
    source_evidence_json: list[dict[str, str]] | None = None


class AugmisBusinessProspectCreateRequest(BaseModel):
    organization_name: str = Field(min_length=1, max_length=255)
    organization_domain: str | None = Field(default=None, max_length=255)
    website_url: str | None = Field(default=None, max_length=500)
    country: str | None = Field(default=None, max_length=120)
    region: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, max_length=150)
    organization_type: str | None = Field(default=None, max_length=120)
    employee_range: str | None = Field(default=None, max_length=120)
    general_email: str | None = Field(default=None, max_length=255)
    general_phone: str | None = Field(default=None, max_length=100)
    prospect_status: str = Field(default="active", min_length=1, max_length=50)
    estimated_account_potential_min: float | None = None
    estimated_account_potential_max: float | None = None
    estimated_currency: str | None = Field(default=None, max_length=3)
    notes: str | None = None
    source_opportunity_id: str | None = None

    @field_validator("general_email")
    @classmethod
    def validate_general_email(cls, value: str | None) -> str | None:
        return _validate_email(value, "General email")

    @field_validator("estimated_currency")
    @classmethod
    def validate_estimated_currency(cls, value: str | None) -> str | None:
        return _validate_currency(value)

    @field_validator("estimated_account_potential_min")
    @classmethod
    def validate_potential_min(cls, value: float | None) -> float | None:
        return _validate_non_negative(value, "Estimated account potential minimum")

    @field_validator("estimated_account_potential_max")
    @classmethod
    def validate_potential_max(cls, value: float | None) -> float | None:
        return _validate_non_negative(value, "Estimated account potential maximum")

    @model_validator(mode="after")
    def validate_potential_range(self):
        if (
            self.estimated_account_potential_min is not None
            and self.estimated_account_potential_max is not None
            and self.estimated_account_potential_min > self.estimated_account_potential_max
        ):
            raise ValueError(
                "Estimated account potential minimum must not exceed maximum"
            )
        return self


class AugmisBusinessProspectUpdateRequest(BaseModel):
    organization_name: str | None = Field(default=None, min_length=1, max_length=255)
    organization_domain: str | None = Field(default=None, max_length=255)
    website_url: str | None = Field(default=None, max_length=500)
    country: str | None = Field(default=None, max_length=120)
    region: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, max_length=150)
    organization_type: str | None = Field(default=None, max_length=120)
    employee_range: str | None = Field(default=None, max_length=120)
    general_email: str | None = Field(default=None, max_length=255)
    general_phone: str | None = Field(default=None, max_length=100)
    prospect_status: str | None = Field(default=None, min_length=1, max_length=50)
    estimated_account_potential_min: float | None = None
    estimated_account_potential_max: float | None = None
    estimated_currency: str | None = Field(default=None, max_length=3)
    notes: str | None = None

    @field_validator("general_email")
    @classmethod
    def validate_general_email(cls, value: str | None) -> str | None:
        return _validate_email(value, "General email")

    @field_validator("estimated_currency")
    @classmethod
    def validate_estimated_currency(cls, value: str | None) -> str | None:
        return _validate_currency(value)

    @field_validator("estimated_account_potential_min")
    @classmethod
    def validate_potential_min(cls, value: float | None) -> float | None:
        return _validate_non_negative(value, "Estimated account potential minimum")

    @field_validator("estimated_account_potential_max")
    @classmethod
    def validate_potential_max(cls, value: float | None) -> float | None:
        return _validate_non_negative(value, "Estimated account potential maximum")

    @model_validator(mode="after")
    def validate_potential_range(self):
        if (
            self.estimated_account_potential_min is not None
            and self.estimated_account_potential_max is not None
            and self.estimated_account_potential_min > self.estimated_account_potential_max
        ):
            raise ValueError(
                "Estimated account potential minimum must not exceed maximum"
            )
        return self


class AugmisBusinessContactCreateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=100)
    job_title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    buyer_role: str | None = Field(default=None, max_length=50)
    linkedin_url: str | None = Field(default=None, max_length=500)
    company_profile_url: str | None = Field(default=None, max_length=500)
    contact_source: str | None = Field(default=None, max_length=120)
    source_url: str | None = Field(default=None, max_length=500)
    evidence_text: str | None = None
    verification_status: str = Field(default="unverified", min_length=1, max_length=50)
    confidence_score: float | None = None
    contact_status: str = Field(default="active", min_length=1, max_length=50)
    is_primary: bool = False
    notes: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return _validate_email(value, "Contact email")

    @field_validator("buyer_role")
    @classmethod
    def validate_buyer_role(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        normalized = normalized.lower()
        if normalized not in ALLOWED_BUYER_ROLES:
            raise ValueError(f"Invalid buyer role: {value}")
        return normalized

    @field_validator("verification_status")
    @classmethod
    def validate_verification_status(cls, value: str) -> str:
        normalized = str(value or "unverified").strip().lower()
        if normalized not in ALLOWED_VERIFICATION_STATUSES:
            raise ValueError(f"Invalid verification status: {value}")
        return normalized

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value < 0 or value > 100:
            raise ValueError("Confidence score must be between 0 and 100")
        return value

    @model_validator(mode="after")
    def validate_contact_presence(self):
        if not any(
            [
                _normalize_optional_text(self.full_name),
                _normalize_optional_text(self.job_title),
                _normalize_optional_text(self.email),
                _normalize_optional_text(self.phone),
            ]
        ):
            raise ValueError(
                "At least one of full_name, job_title, email, or phone must be provided"
            )
        return self


class AugmisBusinessContactUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=100)
    job_title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    buyer_role: str | None = Field(default=None, max_length=50)
    linkedin_url: str | None = Field(default=None, max_length=500)
    company_profile_url: str | None = Field(default=None, max_length=500)
    contact_source: str | None = Field(default=None, max_length=120)
    source_url: str | None = Field(default=None, max_length=500)
    evidence_text: str | None = None
    verification_status: str | None = Field(default=None, min_length=1, max_length=50)
    confidence_score: float | None = None
    contact_status: str | None = Field(default=None, min_length=1, max_length=50)
    is_primary: bool | None = None
    notes: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return _validate_email(value, "Contact email")

    @field_validator("buyer_role")
    @classmethod
    def validate_buyer_role(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        normalized = normalized.lower()
        if normalized not in ALLOWED_BUYER_ROLES:
            raise ValueError(f"Invalid buyer role: {value}")
        return normalized

    @field_validator("verification_status")
    @classmethod
    def validate_verification_status(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        normalized = normalized.lower()
        if normalized not in ALLOWED_VERIFICATION_STATUSES:
            raise ValueError(f"Invalid verification status: {value}")
        return normalized

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value < 0 or value > 100:
            raise ValueError("Confidence score must be between 0 and 100")
        return value


class AugmisBusinessLeadUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    primary_contact_id: str | None = None
    priority: str | None = Field(default=None, min_length=1, max_length=50)
    lead_status: str | None = Field(default=None, min_length=1, max_length=50)
    estimated_value: float | None = None
    probability_pct: float | None = None
    notes: str | None = None


class AugmisBusinessLeadStageUpdateRequest(BaseModel):
    lead_stage: str = Field(min_length=1, max_length=50)


class AugmisBusinessActivityCreateRequest(BaseModel):
    activity_type: str = Field(min_length=1, max_length=100)
    subject: str = Field(min_length=1, max_length=255)
    description: str | None = None
    activity_at: datetime | None = None
    direction: str | None = None
    outcome: str | None = None
    contact_id: str | None = None
    metadata_json: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AugmisBusinessTaskCreateRequest(BaseModel):
    lead_id: str = Field(min_length=1)
    opportunity_id: str | None = None
    prospect_id: str | None = None
    assigned_user_id: str | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    task_type: str = Field(default="follow_up", min_length=1, max_length=100)
    priority: str = Field(default="medium", min_length=1, max_length=50)
    due_at: datetime | None = None
    metadata_json: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AugmisBusinessTaskUpdateRequest(BaseModel):
    assigned_user_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    task_type: str | None = Field(default=None, min_length=1, max_length=100)
    task_status: str | None = Field(default=None, min_length=1, max_length=50)
    priority: str | None = Field(default=None, min_length=1, max_length=50)
    due_at: datetime | None = None
    metadata_json: dict[str, str | int | float | bool | None] | None = None


class AugmisBusinessTaskCompleteRequest(BaseModel):
    completion_notes: str | None = None


class AugmisBusinessExperienceMatchInput(BaseModel):
    experience_item_id: str = Field(min_length=1)
    relevance_score: float | None = None
    match_notes: str | None = None


class AugmisBusinessBuildLeadRequest(BaseModel):
    contact_id: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    contact_job_title: str | None = None
    lead_title: str | None = None
    lead_priority: str = Field(default="medium", min_length=1, max_length=50)
    lead_stage: str = Field(default="new", min_length=1, max_length=50)
    lead_notes: str | None = None
    probability_pct: float | None = None
    selected_experience_matches: list[AugmisBusinessExperienceMatchInput] = Field(default_factory=list)
    first_task_title: str | None = None
    first_task_description: str | None = None
    first_task_priority: str = Field(default="medium", min_length=1, max_length=50)
    first_task_due_at: datetime | None = None
    assigned_user_id: str | None = None


class AugmisBusinessRequirementBudgetInfo(BaseModel):
    value: float | None = None
    currency: str | None = None
    source_supported: bool = False

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str | None) -> str | None:
        return _validate_currency(value)

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: float | None) -> float | None:
        return _validate_non_negative(value, "Budget value")


class AugmisBusinessRequirementExtractionResult(BaseModel):
    requirement_summary: str
    business_problem: str | None = None
    required_deliverables: list[str] = Field(default_factory=list)
    required_technologies: list[str] = Field(default_factory=list)
    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    timeline_constraints: list[str] = Field(default_factory=list)
    eligibility_constraints: list[str] = Field(default_factory=list)
    budget_information: AugmisBusinessRequirementBudgetInfo = Field(
        default_factory=AugmisBusinessRequirementBudgetInfo
    )
    missing_information: list[str] = Field(default_factory=list)
    source_evidence: list[str] = Field(default_factory=list)
    confidence: float = 0

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if value < 0 or value > 100:
            raise ValueError("Confidence must be between 0 and 100")
        return value


class AugmisBusinessDeliveryFeasibilityResult(BaseModel):
    delivery_model: str
    reasoning: str
    complexity_score: float
    estimated_delivery_weeks: float | None = None
    key_delivery_risks: list[str] = Field(default_factory=list)

    @field_validator("delivery_model")
    @classmethod
    def validate_delivery_model(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        allowed = {"solo", "solo_with_support", "small_team", "partner_required"}
        if normalized not in allowed:
            raise ValueError(f"Invalid delivery model: {value}")
        return normalized

    @field_validator("complexity_score", "estimated_delivery_weeks")
    @classmethod
    def validate_non_negative_metric(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value < 0 or value > 1000:
            raise ValueError("Metric must be non-negative")
        return value


class AugmisBusinessQualificationComponentScore(BaseModel):
    score: float
    explanation: str

    @field_validator("score")
    @classmethod
    def validate_score(cls, value: float) -> float:
        if value < 0 or value > 100:
            raise ValueError("Component score must be between 0 and 100")
        return value


class AugmisBusinessQualificationResult(BaseModel):
    experience_relevance: AugmisBusinessQualificationComponentScore
    technology_match: AugmisBusinessQualificationComponentScore
    budget_attractiveness: AugmisBusinessQualificationComponentScore
    delivery_feasibility: AugmisBusinessQualificationComponentScore
    buyer_accessibility: AugmisBusinessQualificationComponentScore
    deadline_feasibility: AugmisBusinessQualificationComponentScore
    market_payment_risk: AugmisBusinessQualificationComponentScore
    delivery_profile: AugmisBusinessDeliveryFeasibilityResult
    recommendation: str
    explanation: str
    risks: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    confidence: float

    @field_validator("recommendation")
    @classmethod
    def validate_recommendation(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        allowed = {
            "pursue",
            "review",
            "partner_required",
            "low_priority",
            "reject",
            "expired",
            "insufficient_information",
        }
        if normalized not in allowed:
            raise ValueError(f"Invalid recommendation: {value}")
        return normalized

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if value < 0 or value > 100:
            raise ValueError("Confidence must be between 0 and 100")
        return value


class AugmisBusinessBuyerRoleRecommendation(BaseModel):
    role: str
    reason: str
    confidence: float

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Role is required")
        lower_value = normalized.lower()
        if "@" in lower_value:
            raise ValueError("Buyer role must not contain contact details")
        allowed_keywords = {
            "director",
            "manager",
            "head",
            "chief",
            "cio",
            "cto",
            "founder",
            "procurement",
            "operations",
            "engineering",
            "transformation",
            "quality",
            "hse",
            "applications",
            "excellence",
            "owner",
            "evaluator",
            "buyer",
            "officer",
            "lead",
            "administrator",
            "admin",
        }
        if not any(keyword in lower_value for keyword in allowed_keywords):
            raise ValueError("Buyer role must be a stakeholder role, not a named contact")
        return normalized

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if value < 0 or value > 100:
            raise ValueError("Confidence must be between 0 and 100")
        return value


class AugmisBusinessBuyerRolesResult(BaseModel):
    economic_buyer: AugmisBusinessBuyerRoleRecommendation
    operational_owner: AugmisBusinessBuyerRoleRecommendation
    technical_evaluator: AugmisBusinessBuyerRoleRecommendation
    procurement_contact: AugmisBusinessBuyerRoleRecommendation


class AugmisBusinessExperienceMatchResult(BaseModel):
    experience_item_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    match_score: float
    matching_capabilities: list[str] = Field(default_factory=list)
    matching_technologies: list[str] = Field(default_factory=list)
    business_problem_similarity: str
    explanation: str

    @field_validator("match_score")
    @classmethod
    def validate_match_score(cls, value: float) -> float:
        if value < 0 or value > 100:
            raise ValueError("Match score must be between 0 and 100")
        return value


class AugmisBusinessExperienceMatchEnvelope(BaseModel):
    matches: list[AugmisBusinessExperienceMatchResult] = Field(default_factory=list)


class AugmisBusinessOpportunityAIAssessmentSummary(BaseModel):
    id: str
    opportunity_id: str
    assessment_version: int
    provider: str
    model: str
    prompt_bundle_version: str
    final_fit_score: float | None = None
    confidence_score: float | None = None
    recommendation: str | None = None
    created_at: datetime | None = None


class AugmisBusinessOpportunityAIAssessmentResponse(
    AugmisBusinessOpportunityAIAssessmentSummary
):
    requirement_extraction_json: AugmisBusinessRequirementExtractionResult
    qualification_json: AugmisBusinessQualificationResult
    buyer_roles_json: AugmisBusinessBuyerRolesResult
    risks_json: list[str] = Field(default_factory=list)
    missing_information_json: list[str] = Field(default_factory=list)
    experience_matches: list[AugmisBusinessExperienceMatchResult] = Field(default_factory=list)
    ai_run_summary_json: dict[str, object] = Field(default_factory=dict)


class AugmisBusinessOutreachGenerateRequest(BaseModel):
    outreach_type: str = Field(min_length=1, max_length=80)
    tone: str = Field(default="consultative", min_length=1, max_length=50)
    lead_id: str | None = None
    prospect_id: str | None = None
    contact_id: str | None = None

    @field_validator("outreach_type")
    @classmethod
    def validate_outreach_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_OUTREACH_TYPES:
            raise ValueError(f"Invalid outreach type: {value}")
        return normalized

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, value: str) -> str:
        normalized = str(value or "consultative").strip().lower()
        if normalized not in ALLOWED_OUTREACH_TONES:
            raise ValueError(f"Invalid outreach tone: {value}")
        return normalized


class AugmisBusinessOutreachTargetSummary(BaseModel):
    organization_name: str
    contact_name: str | None = None
    contact_job_title: str | None = None
    buyer_role: str | None = None
    department: str | None = None
    verification_status: str | None = None
    contact_verification_notice: str | None = None


class AugmisBusinessOutreachContent(BaseModel):
    subject_options: list[str] = Field(default_factory=list)
    recommended_subject: str | None = None
    opening: str
    body: str
    call_to_action: str
    full_message: str
    personalization_points: list[str] = Field(default_factory=list)
    claims_used: list[str] = Field(default_factory=list)
    facts_requiring_verification: list[str] = Field(default_factory=list)
    tone: str
    uses_named_contact: bool = False
    contact_name_used: str | None = None

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_OUTREACH_TONES:
            raise ValueError(f"Invalid outreach tone: {value}")
        return normalized

    @model_validator(mode="after")
    def validate_named_contact_usage(self):
        if self.uses_named_contact and not _normalize_optional_text(self.contact_name_used):
            raise ValueError("contact_name_used is required when uses_named_contact is true")
        return self


class AugmisBusinessOutreachGenerationResult(BaseModel):
    outreach_type: str
    target_summary: AugmisBusinessOutreachTargetSummary
    content: AugmisBusinessOutreachContent

    @field_validator("outreach_type")
    @classmethod
    def validate_outreach_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_OUTREACH_TYPES:
            raise ValueError(f"Invalid outreach type: {value}")
        return normalized


class AugmisBusinessOutreachDraftSummary(BaseModel):
    id: str
    opportunity_id: str
    lead_id: str | None = None
    prospect_id: str | None = None
    contact_id: str | None = None
    outreach_type: str
    tone: str
    subject: str | None = None
    generation_version: int
    provider: str
    model: str
    prompt_bundle_version: str
    status: str
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("outreach_type")
    @classmethod
    def validate_summary_outreach_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_OUTREACH_TYPES:
            raise ValueError(f"Invalid outreach type: {value}")
        return normalized

    @field_validator("tone")
    @classmethod
    def validate_summary_tone(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_OUTREACH_TONES:
            raise ValueError(f"Invalid outreach tone: {value}")
        return normalized

    @field_validator("status")
    @classmethod
    def validate_summary_status(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_GENERATION_STATUSES:
            raise ValueError(f"Invalid generation status: {value}")
        return normalized


class AugmisBusinessOutreachDraftResponse(AugmisBusinessOutreachDraftSummary):
    body: str
    structured_content_json: AugmisBusinessOutreachGenerationResult


class AugmisBusinessOutreachDraftUpdateRequest(BaseModel):
    subject: str | None = None
    body: str | None = None
    structured_content_json: AugmisBusinessOutreachGenerationResult | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        normalized = normalized.lower()
        if normalized not in ALLOWED_GENERATION_STATUSES:
            raise ValueError(f"Invalid generation status: {value}")
        return normalized


class AugmisBusinessStatusActionRequest(BaseModel):
    notes: str | None = None


class AugmisBusinessDiscoveryQuestion(BaseModel):
    question: str
    category: str
    priority: str
    why_it_matters: str

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in {"high", "medium", "low"}:
            raise ValueError(f"Invalid discovery question priority: {value}")
        return normalized


class AugmisBusinessEstimatedDelivery(BaseModel):
    weeks_min: float | None = None
    weeks_max: float | None = None
    confidence: float = 0
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("weeks_min", "weeks_max")
    @classmethod
    def validate_week_values(cls, value: float | None) -> float | None:
        return _validate_non_negative(value, "Estimated delivery weeks")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if value < 0 or value > 100:
            raise ValueError("Confidence must be between 0 and 100")
        return value

    @model_validator(mode="after")
    def validate_range(self):
        if (
            self.weeks_min is not None
            and self.weeks_max is not None
            and self.weeks_min > self.weeks_max
        ):
            raise ValueError("weeks_min must not exceed weeks_max")
        return self


class AugmisBusinessSolutionModule(BaseModel):
    name: str
    purpose: str
    key_features: list[str] = Field(default_factory=list)


class AugmisBusinessExperienceReference(BaseModel):
    experience_item_id: str
    name: str
    category: str
    relevant_capabilities: list[str] = Field(default_factory=list)
    matching_technologies: list[str] = Field(default_factory=list)
    safe_summary: str


class AugmisBusinessMiniSolutionContent(BaseModel):
    title: str
    executive_summary: str
    problem_understanding: str
    proposed_solution: str
    solution_modules: list[AugmisBusinessSolutionModule] = Field(default_factory=list)
    suggested_workflow: list[str] = Field(default_factory=list)
    suggested_user_roles: list[str] = Field(default_factory=list)
    suggested_technology_stack: list[str] = Field(default_factory=list)
    integration_points: list[str] = Field(default_factory=list)
    delivery_approach: list[str] = Field(default_factory=list)
    estimated_delivery: AugmisBusinessEstimatedDelivery = Field(
        default_factory=AugmisBusinessEstimatedDelivery
    )
    experience_references: list[AugmisBusinessExperienceReference] = Field(
        default_factory=list
    )
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    discovery_questions: list[AugmisBusinessDiscoveryQuestion] = Field(default_factory=list)
    next_step: str


class AugmisBusinessMiniSolutionSummary(BaseModel):
    id: str
    opportunity_id: str
    lead_id: str | None = None
    assessment_id: str | None = None
    title: str
    generation_version: int
    provider: str
    model: str
    prompt_bundle_version: str
    status: str
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_GENERATION_STATUSES:
            raise ValueError(f"Invalid generation status: {value}")
        return normalized


class AugmisBusinessMiniSolutionResponse(AugmisBusinessMiniSolutionSummary):
    solution_json: AugmisBusinessMiniSolutionContent


class AugmisBusinessMiniSolutionGenerateRequest(BaseModel):
    lead_id: str | None = None
    tone: str = Field(default="consultative", min_length=1, max_length=50)

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, value: str) -> str:
        normalized = str(value or "consultative").strip().lower()
        if normalized not in ALLOWED_OUTREACH_TONES:
            raise ValueError(f"Invalid solution tone: {value}")
        return normalized


class AugmisBusinessMiniSolutionUpdateRequest(BaseModel):
    title: str | None = None
    solution_json: AugmisBusinessMiniSolutionContent | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        normalized = normalized.lower()
        if normalized not in ALLOWED_GENERATION_STATUSES:
            raise ValueError(f"Invalid generation status: {value}")
        return normalized


class AugmisBusinessReplyCreateRequest(BaseModel):
    lead_id: str = Field(min_length=1)
    contact_id: str | None = None
    outreach_id: str | None = None
    channel: str = Field(min_length=1, max_length=80)
    subject: str | None = Field(default=None, max_length=500)
    raw_message: str = Field(min_length=1)
    sender_display: str | None = Field(default=None, max_length=255)
    received_at: datetime
    notes: str | None = None

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_REPLY_CHANNELS:
            raise ValueError(f"Invalid reply channel: {value}")
        return normalized


class AugmisBusinessReplyUpdateRequest(BaseModel):
    contact_id: str | None = None
    outreach_id: str | None = None
    channel: str | None = Field(default=None, min_length=1, max_length=80)
    subject: str | None = Field(default=None, max_length=500)
    raw_message: str | None = Field(default=None, min_length=1)
    sender_display: str | None = Field(default=None, max_length=255)
    received_at: datetime | None = None
    reply_status: str | None = Field(default=None, min_length=1, max_length=80)
    notes: str | None = None

    @field_validator("channel")
    @classmethod
    def validate_optional_channel(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        normalized = normalized.lower()
        if normalized not in ALLOWED_REPLY_CHANNELS:
            raise ValueError(f"Invalid reply channel: {value}")
        return normalized

    @field_validator("reply_status")
    @classmethod
    def validate_reply_status(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        normalized = normalized.lower()
        if normalized not in ALLOWED_REPLY_STATUSES:
            raise ValueError(f"Invalid reply status: {value}")
        return normalized


class AugmisBusinessReplySummary(BaseModel):
    id: str
    opportunity_id: str | None = None
    lead_id: str
    prospect_id: str | None = None
    contact_id: str | None = None
    outreach_id: str | None = None
    channel: str
    subject: str | None = None
    raw_message: str
    sender_display: str | None = None
    received_at: datetime | None = None
    reply_status: str
    notes: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    lead_title: str | None = None
    prospect_name: str | None = None
    contact_name: str | None = None
    latest_intent: str | None = None
    latest_engagement_level: str | None = None
    latest_urgency: str | None = None
    latest_sentiment: str | None = None
    latest_analysis_id: str | None = None
    latest_analysis_created_at: datetime | None = None
    latest_response_id: str | None = None
    latest_response_status: str | None = None
    latest_response_created_at: datetime | None = None

    @field_validator("channel")
    @classmethod
    def validate_summary_channel(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_REPLY_CHANNELS:
            raise ValueError(f"Invalid reply channel: {value}")
        return normalized

    @field_validator("reply_status")
    @classmethod
    def validate_summary_reply_status(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_REPLY_STATUSES:
            raise ValueError(f"Invalid reply status: {value}")
        return normalized


class AugmisBusinessReplyObjection(BaseModel):
    category: str
    concern: str
    evidence: str
    suggested_response_approach: str

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_REPLY_OBJECTION_CATEGORIES:
            raise ValueError(f"Invalid objection category: {value}")
        return normalized


class AugmisBusinessReplyRecommendedTask(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    task_type: str = Field(min_length=1, max_length=100)
    priority: str = Field(min_length=1, max_length=50)
    due_in_days: int | None = Field(default=None, ge=1, le=30)
    reason: str | None = Field(default=None, min_length=1)

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_REPLY_TASK_TYPES:
            raise ValueError(f"Invalid recommended task type: {value}")
        return normalized

    @field_validator("priority")
    @classmethod
    def validate_task_priority(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in {"high", "medium", "low"}:
            raise ValueError(f"Invalid recommended task priority: {value}")
        return normalized

    @model_validator(mode="after")
    def fill_defaults(self):
        if _normalize_optional_text(self.title) is None:
            task_label = str(self.task_type or "follow_up").replace("_", " ").strip() or "follow up"
            self.title = f"{task_label.capitalize()} on inbound reply"
        if _normalize_optional_text(self.reason) is None:
            self.reason = "AI recommended a follow-up task based on the inbound reply."
        return self


class AugmisBusinessReplyAnalysisResult(BaseModel):
    intent: str
    sentiment: str
    engagement_level: str
    urgency: str
    summary: str
    key_points: list[str] = Field(default_factory=list)
    questions_from_prospect: list[str] = Field(default_factory=list)
    objections: list[AugmisBusinessReplyObjection] = Field(default_factory=list)
    buying_signals: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    requested_actions: list[str] = Field(default_factory=list)
    recommended_next_action: str
    recommended_pipeline_stage: str | None = None
    recommended_probability: float | None = None
    recommended_task: AugmisBusinessReplyRecommendedTask | None = None
    response_strategy: str
    confidence: float

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_REPLY_INTENTS:
            raise ValueError(f"Invalid reply intent: {value}")
        return normalized

    @field_validator("sentiment")
    @classmethod
    def validate_sentiment(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_REPLY_SENTIMENTS:
            raise ValueError(f"Invalid reply sentiment: {value}")
        return normalized

    @field_validator("engagement_level")
    @classmethod
    def validate_engagement_level(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_REPLY_ENGAGEMENT_LEVELS:
            raise ValueError(f"Invalid reply engagement level: {value}")
        return normalized

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_REPLY_URGENCY_LEVELS:
            raise ValueError(f"Invalid reply urgency: {value}")
        return normalized

    @field_validator("recommended_pipeline_stage")
    @classmethod
    def validate_pipeline_stage(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        normalized = normalized.lower()
        if normalized not in {
            "new",
            "qualified",
            "proposal",
            "negotiation",
            "closed_won",
            "closed_lost",
        }:
            raise ValueError(f"Invalid recommended pipeline stage: {value}")
        return normalized

    @field_validator("recommended_probability", "confidence")
    @classmethod
    def validate_probability(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value < 0 or value > 100:
            raise ValueError("Probability and confidence must be between 0 and 100")
        return value

    @field_validator("response_strategy")
    @classmethod
    def validate_response_strategy(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_REPLY_RESPONSE_STRATEGIES:
            raise ValueError(f"Invalid response strategy: {value}")
        return normalized


class AugmisBusinessReplyAnalysisSummary(BaseModel):
    id: str
    reply_id: str
    analysis_version: int
    provider: str
    model: str
    prompt_bundle_version: str
    intent: str
    sentiment: str
    engagement_level: str
    urgency: str
    objection_category: str | None = None
    recommended_pipeline_stage: str | None = None
    recommended_next_action: str
    confidence_score: float
    created_by: str | None = None
    created_at: datetime | None = None


class AugmisBusinessReplyAnalysisResponse(AugmisBusinessReplyAnalysisSummary):
    analysis_json: AugmisBusinessReplyAnalysisResult


class AugmisBusinessReplyResponseGenerateRequest(BaseModel):
    strategy: str = Field(default="consultative", min_length=1, max_length=50)

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, value: str) -> str:
        normalized = str(value or "consultative").strip().lower()
        if normalized not in ALLOWED_REPLY_RESPONSE_STRATEGIES:
            raise ValueError(f"Invalid response strategy: {value}")
        return normalized


class AugmisBusinessReplyResponseContent(BaseModel):
    subject: str | None = None
    opening: str
    response_body: str
    call_to_action: str
    full_message: str
    questions_answered: list[str] = Field(default_factory=list)
    questions_not_answered: list[str] = Field(default_factory=list)
    facts_requiring_verification: list[str] = Field(default_factory=list)
    recommended_attachments: list[str] = Field(default_factory=list)
    tone: str

    @field_validator("tone")
    @classmethod
    def validate_response_tone(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_REPLY_RESPONSE_STRATEGIES:
            raise ValueError(f"Invalid response tone: {value}")
        return normalized


class AugmisBusinessReplyResponseDraftSummary(BaseModel):
    id: str
    reply_id: str
    opportunity_id: str | None = None
    lead_id: str
    prospect_id: str | None = None
    contact_id: str | None = None
    analysis_id: str | None = None
    tone: str
    subject: str | None = None
    generation_version: int
    provider: str
    model: str
    prompt_bundle_version: str
    status: str
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("tone")
    @classmethod
    def validate_draft_tone(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_REPLY_RESPONSE_STRATEGIES:
            raise ValueError(f"Invalid response tone: {value}")
        return normalized

    @field_validator("status")
    @classmethod
    def validate_draft_status(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_GENERATION_STATUSES:
            raise ValueError(f"Invalid generation status: {value}")
        return normalized


class AugmisBusinessReplyResponseDraftResponse(AugmisBusinessReplyResponseDraftSummary):
    body: str
    structured_content_json: AugmisBusinessReplyResponseContent


class AugmisBusinessReplyResponseDraftUpdateRequest(BaseModel):
    subject: str | None = None
    body: str | None = None
    structured_content_json: AugmisBusinessReplyResponseContent | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_response_status(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        normalized = normalized.lower()
        if normalized not in ALLOWED_GENERATION_STATUSES:
            raise ValueError(f"Invalid generation status: {value}")
        return normalized


class AugmisBusinessSearchProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    target_regions_json: list[str] = Field(default_factory=list)
    target_countries_json: list[str] = Field(default_factory=list)
    target_industries_json: list[str] = Field(default_factory=list)
    include_keywords_json: list[str] = Field(default_factory=list)
    include_technologies_json: list[str] = Field(default_factory=list)
    include_capabilities_json: list[str] = Field(default_factory=list)
    exclude_keywords_json: list[str] = Field(default_factory=list)
    excluded_domains_json: list[str] = Field(default_factory=list)
    excluded_categories_json: list[str] = Field(default_factory=list)
    minimum_budget: float | None = None
    currencies_json: list[str] = Field(default_factory=list)
    allow_budget_unknown: bool = True
    solo_feasibility_preference: str | None = None
    small_team_allowed: bool = True
    max_delivery_months: int | None = Field(default=None, ge=1)
    max_age_days: int | None = Field(default=None, ge=1)

    @field_validator("currencies_json")
    @classmethod
    def validate_currencies(cls, value: list[str]) -> list[str]:
        return [_validate_currency(item) for item in value if _validate_currency(item)]

    @field_validator("minimum_budget")
    @classmethod
    def validate_minimum_budget(cls, value: float | None) -> float | None:
        return _validate_non_negative(value, "Minimum budget")


class AugmisBusinessSearchProfileCreateRequest(AugmisBusinessSearchProfileBase):
    pass


class AugmisBusinessSearchProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None
    target_regions_json: list[str] | None = None
    target_countries_json: list[str] | None = None
    target_industries_json: list[str] | None = None
    include_keywords_json: list[str] | None = None
    include_technologies_json: list[str] | None = None
    include_capabilities_json: list[str] | None = None
    exclude_keywords_json: list[str] | None = None
    excluded_domains_json: list[str] | None = None
    excluded_categories_json: list[str] | None = None
    minimum_budget: float | None = None
    currencies_json: list[str] | None = None
    allow_budget_unknown: bool | None = None
    solo_feasibility_preference: str | None = None
    small_team_allowed: bool | None = None
    max_delivery_months: int | None = Field(default=None, ge=1)
    max_age_days: int | None = Field(default=None, ge=1)

    @field_validator("currencies_json")
    @classmethod
    def validate_optional_currencies(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [_validate_currency(item) for item in value if _validate_currency(item)]

    @field_validator("minimum_budget")
    @classmethod
    def validate_optional_minimum_budget(cls, value: float | None) -> float | None:
        return _validate_non_negative(value, "Minimum budget")


class AugmisBusinessSearchProfileResponse(AugmisBusinessSearchProfileBase):
    id: str
    tenant_id: str
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AugmisBusinessConnectorMetadata(BaseModel):
    connector_type: str
    name: str
    source_category: str
    description: str
    capabilities: list[str] = Field(default_factory=list)
    configuration_schema: dict[str, object] = Field(default_factory=dict)
    supports_scheduled_scan: bool = False
    supports_manual_scan: bool = True
    supports_incremental_scan: bool = False
    status: str = "ready"
    is_test_connector: bool = False


class AugmisBusinessConnectorBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    connector_type: str = Field(min_length=1, max_length=120)
    source_category: str = Field(min_length=1, max_length=120)
    enabled: bool = True
    schedule_enabled: bool = False
    schedule_expression: str | None = Field(default=None, max_length=255)
    schedule_type: str = Field(default="manual", min_length=1, max_length=50)
    schedule_interval_minutes: int | None = Field(default=None, ge=60, le=10080)
    schedule_day_of_week: int | None = Field(default=None, ge=0, le=6)
    schedule_time_local: str | None = Field(default=None, max_length=5)
    schedule_timezone: str | None = Field(default=None, max_length=64)
    configuration_json: dict[str, object] = Field(default_factory=dict)
    search_criteria_json: dict[str, object] = Field(default_factory=dict)
    capability_flags_json: dict[str, object] = Field(default_factory=dict)
    search_profile_id: str | None = None

    @field_validator("source_category")
    @classmethod
    def validate_source_category(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_CONNECTOR_SOURCE_CATEGORIES:
            raise ValueError(f"Invalid source category: {value}")
        return normalized

    @field_validator("schedule_type")
    @classmethod
    def validate_schedule_type(cls, value: str) -> str:
        normalized = str(value or "manual").strip().lower()
        if normalized not in ALLOWED_CONNECTOR_SCHEDULE_TYPES:
            raise ValueError(f"Invalid schedule type: {value}")
        return normalized

    @field_validator("schedule_time_local")
    @classmethod
    def validate_schedule_time_local(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        if not re.fullmatch(r"^([01]\d|2[0-3]):[0-5]\d$", normalized):
            raise ValueError("Schedule time must use HH:MM 24-hour format")
        return normalized

    @field_validator("schedule_timezone")
    @classmethod
    def validate_schedule_timezone(cls, value: str | None) -> str | None:
        return _validate_timezone_name(value)

    @model_validator(mode="after")
    def validate_schedule_fields(self):
        schedule_type = (self.schedule_type or "manual").lower()
        if not self.schedule_enabled or schedule_type == "manual":
            return self
        if schedule_type == "hourly_interval":
            if self.schedule_interval_minutes is None:
                raise ValueError("Hourly interval schedules require an interval in minutes")
            if self.schedule_interval_minutes < 60:
                raise ValueError("Automatic schedules cannot run more frequently than hourly")
        elif schedule_type == "daily":
            if not self.schedule_time_local:
                raise ValueError("Daily schedules require a local time")
        elif schedule_type == "weekly":
            if self.schedule_day_of_week not in ALLOWED_CONNECTOR_SCHEDULE_WEEKDAYS:
                raise ValueError("Weekly schedules require a valid weekday")
            if not self.schedule_time_local:
                raise ValueError("Weekly schedules require a local time")
        return self


class AugmisBusinessConnectorCreateRequest(AugmisBusinessConnectorBase):
    pass


class AugmisBusinessConnectorUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None
    schedule_enabled: bool | None = None
    schedule_expression: str | None = Field(default=None, max_length=255)
    schedule_type: str | None = Field(default=None, min_length=1, max_length=50)
    schedule_interval_minutes: int | None = Field(default=None, ge=60, le=10080)
    schedule_day_of_week: int | None = Field(default=None, ge=0, le=6)
    schedule_time_local: str | None = Field(default=None, max_length=5)
    schedule_timezone: str | None = Field(default=None, max_length=64)
    configuration_json: dict[str, object] | None = None
    search_criteria_json: dict[str, object] | None = None
    capability_flags_json: dict[str, object] | None = None
    search_profile_id: str | None = None
    status: str | None = Field(default=None, min_length=1, max_length=50)

    @field_validator("status")
    @classmethod
    def validate_connector_status(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        normalized = normalized.lower()
        if normalized not in ALLOWED_CONNECTOR_STATUSES:
            raise ValueError(f"Invalid connector status: {value}")
        return normalized

    @field_validator("schedule_type")
    @classmethod
    def validate_optional_schedule_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value or "manual").strip().lower()
        if normalized not in ALLOWED_CONNECTOR_SCHEDULE_TYPES:
            raise ValueError(f"Invalid schedule type: {value}")
        return normalized

    @field_validator("schedule_time_local")
    @classmethod
    def validate_optional_schedule_time_local(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        if not re.fullmatch(r"^([01]\d|2[0-3]):[0-5]\d$", normalized):
            raise ValueError("Schedule time must use HH:MM 24-hour format")
        return normalized

    @field_validator("schedule_timezone")
    @classmethod
    def validate_optional_schedule_timezone(cls, value: str | None) -> str | None:
        return _validate_timezone_name(value)


class AugmisBusinessConnectorCredentialWriteRequest(BaseModel):
    api_key: str | None = Field(default=None, min_length=8, max_length=512)
    app_id: str | None = Field(default=None, min_length=2, max_length=256)
    app_key: str | None = Field(default=None, min_length=8, max_length=512)

    @field_validator("api_key", "app_key")
    @classmethod
    def validate_api_key(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        if len(normalized) < 8:
            raise ValueError("API key is too short")
        return normalized

    @model_validator(mode="after")
    def validate_any_credential(self):
        if self.api_key or (self.app_id and self.app_key):
            return self
        raise ValueError("Either api_key or app_id/app_key is required")


class AugmisBusinessConnectorCredentialTestRequest(BaseModel):
    api_key: str | None = Field(default=None, max_length=512)
    app_id: str | None = Field(default=None, max_length=256)
    app_key: str | None = Field(default=None, max_length=512)

    @field_validator("api_key", "app_key")
    @classmethod
    def validate_optional_api_key(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        if len(normalized) < 8:
            raise ValueError("API key is too short")
        return normalized


class AugmisBusinessConnectorCredentialStatusResponse(BaseModel):
    provider: str
    credential_type: str = "api_key"
    configured: bool
    credential_source: str
    masked_hint: str | None = None
    last_updated_at: datetime | None = None
    last_tested_at: datetime | None = None
    last_test_status: str | None = None
    last_test_error: str | None = None
    storage_available: bool = True
    storage_message: str | None = None


class AugmisBusinessSearchProviderBase(BaseModel):
    provider_code: str = Field(min_length=2, max_length=120)
    display_name: str = Field(min_length=1, max_length=255)
    provider_type: str = Field(min_length=1, max_length=50)
    adapter_code: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    enabled: bool = True
    credential_type: str = Field(default="api_key", min_length=1, max_length=50)
    configuration_json: dict[str, object] = Field(default_factory=dict)

    @field_validator("provider_code")
    @classmethod
    def validate_provider_code(cls, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9-]+", "-", str(value or "").strip().lower()).strip("-")
        if len(normalized) < 2:
            raise ValueError("Provider code must contain at least 2 letters or numbers")
        return normalized

    @field_validator("provider_type")
    @classmethod
    def validate_provider_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_SEARCH_PROVIDER_TYPES:
            raise ValueError(f"Invalid provider type: {value}")
        return normalized

    @field_validator("credential_type")
    @classmethod
    def validate_credential_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_SEARCH_PROVIDER_CREDENTIAL_TYPES:
            raise ValueError(f"Invalid credential type: {value}")
        return normalized


class AugmisBusinessSearchProviderCreateRequest(AugmisBusinessSearchProviderBase):
    pass


class AugmisBusinessSearchProviderUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    enabled: bool | None = None
    credential_type: str | None = Field(default=None, min_length=1, max_length=50)
    configuration_json: dict[str, object] | None = None

    @field_validator("credential_type")
    @classmethod
    def validate_optional_credential_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_SEARCH_PROVIDER_CREDENTIAL_TYPES:
            raise ValueError(f"Invalid credential type: {value}")
        return normalized


class AugmisBusinessConnectorProviderUpdateRequest(BaseModel):
    provider_code: str = Field(min_length=2, max_length=120)

    @field_validator("provider_code")
    @classmethod
    def validate_provider_code(cls, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9-]+", "-", str(value or "").strip().lower()).strip("-")
        if len(normalized) < 2:
            raise ValueError("Provider code must contain at least 2 letters or numbers")
        return normalized


class AugmisBusinessSearchProviderResponse(BaseModel):
    id: str
    tenant_id: str | None = None
    provider_code: str
    display_name: str
    provider_type: str
    adapter_code: str | None = None
    description: str | None = None
    enabled: bool
    credential_type: str
    configuration_json: dict[str, object] = Field(default_factory=dict)
    credential_configured: bool = False
    credential_source: str = "none"
    connection_status: str = "not_tested"
    last_tested_at: datetime | None = None
    last_test_error: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AugmisBusinessConnectorResponse(BaseModel):
    id: str
    tenant_id: str
    search_profile_id: str | None = None
    connector_type: str
    name: str
    source_category: str
    status: str
    enabled: bool
    schedule_enabled: bool
    schedule_expression: str | None = None
    schedule_type: str = "manual"
    schedule_interval_minutes: int | None = None
    schedule_day_of_week: int | None = None
    schedule_time_local: str | None = None
    schedule_timezone: str | None = None
    next_run_at: datetime | None = None
    last_scheduled_run_at: datetime | None = None
    schedule_retry_count: int = 0
    active_run_id: str | None = None
    schedule_updated_by: str | None = None
    schedule_updated_at: datetime | None = None
    configuration_json: dict[str, object] = Field(default_factory=dict)
    search_criteria_json: dict[str, object] = Field(default_factory=dict)
    capability_flags_json: dict[str, object] = Field(default_factory=dict)
    last_scan_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_message: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: AugmisBusinessConnectorMetadata | None = None


class AugmisBusinessConnectorRunResponse(BaseModel):
    id: str
    tenant_id: str
    connector_id: str
    run_type: str
    status: str
    attempt_number: int = 1
    max_attempts: int = 1
    retry_of_run_id: str | None = None
    next_retry_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    items_found: int
    items_new: int
    items_duplicate: int
    items_filtered: int
    items_failed: int
    error_summary: str | None = None
    run_metadata_json: dict[str, object] = Field(default_factory=dict)
    initiated_by: str | None = None
    created_at: datetime | None = None


class AugmisBusinessConnectorScanRequest(BaseModel):
    run_type: str = Field(default="manual", min_length=1, max_length=50)

    @field_validator("run_type")
    @classmethod
    def validate_run_type(cls, value: str) -> str:
        normalized = str(value or "manual").strip().lower()
        if normalized not in ALLOWED_CONNECTOR_RUN_TYPES:
            raise ValueError(f"Invalid run type: {value}")
        return normalized


class AugmisBusinessWebSeedBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    seed_url: str = Field(min_length=8, max_length=2000)
    seed_type: str = Field(min_length=1, max_length=80)
    enabled: bool = True
    crawl_scope: str = Field(default="same_domain", min_length=1, max_length=80)
    max_depth: int = Field(default=2, ge=0, le=10)
    max_pages: int = Field(default=25, ge=1, le=500)
    crawl_frequency: str = Field(default="weekly", min_length=1, max_length=30)
    priority: int = Field(default=50, ge=0, le=100)
    country: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, max_length=120)
    organization_name: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("seed_type")
    @classmethod
    def validate_seed_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_WEB_SEED_TYPES:
            raise ValueError(f"Invalid seed type: {value}")
        return normalized

    @field_validator("crawl_scope")
    @classmethod
    def validate_crawl_scope(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_WEB_SEED_SCOPES:
            raise ValueError(f"Invalid crawl scope: {value}")
        return normalized

    @field_validator("crawl_frequency")
    @classmethod
    def validate_crawl_frequency(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_WEB_SEED_FREQUENCIES:
            raise ValueError(f"Invalid crawl frequency: {value}")
        return normalized


class AugmisBusinessWebSeedCreateRequest(AugmisBusinessWebSeedBase):
    pass


class AugmisBusinessWebSeedUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    seed_url: str | None = Field(default=None, min_length=8, max_length=2000)
    seed_type: str | None = Field(default=None, min_length=1, max_length=80)
    enabled: bool | None = None
    crawl_scope: str | None = Field(default=None, min_length=1, max_length=80)
    max_depth: int | None = Field(default=None, ge=0, le=10)
    max_pages: int | None = Field(default=None, ge=1, le=500)
    crawl_frequency: str | None = Field(default=None, min_length=1, max_length=30)
    priority: int | None = Field(default=None, ge=0, le=100)
    country: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, max_length=120)
    organization_name: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("seed_type")
    @classmethod
    def validate_optional_seed_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_WEB_SEED_TYPES:
            raise ValueError(f"Invalid seed type: {value}")
        return normalized

    @field_validator("crawl_scope")
    @classmethod
    def validate_optional_crawl_scope(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_WEB_SEED_SCOPES:
            raise ValueError(f"Invalid crawl scope: {value}")
        return normalized

    @field_validator("crawl_frequency")
    @classmethod
    def validate_optional_crawl_frequency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_WEB_SEED_FREQUENCIES:
            raise ValueError(f"Invalid crawl frequency: {value}")
        return normalized


class AugmisBusinessWebSeedResponse(BaseModel):
    id: str
    tenant_id: str
    connector_id: str
    name: str
    seed_url: str
    seed_type: str
    enabled: bool
    crawl_scope: str
    max_depth: int
    max_pages: int
    crawl_frequency: str
    priority: int
    country: str | None = None
    industry: str | None = None
    organization_name: str | None = None
    notes: str | None = None
    last_crawled_at: datetime | None = None
    next_crawl_at: datetime | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AugmisBusinessWebDomainUpdateRequest(BaseModel):
    enabled: bool | None = None
    approval_status: str | None = Field(default=None, min_length=1, max_length=50)
    proposed_type: str | None = Field(default=None, max_length=80)
    next_crawl_at: datetime | None = None

    @field_validator("approval_status")
    @classmethod
    def validate_domain_approval_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_WEB_DOMAIN_APPROVAL_STATUSES:
            raise ValueError(f"Invalid approval status: {value}")
        return normalized


class AugmisBusinessWebDomainResponse(BaseModel):
    id: str
    tenant_id: str
    connector_id: str
    seed_id: str | None = None
    domain: str
    source: str | None = None
    proposed_type: str | None = None
    trust_source_type: str | None = None
    enabled: bool
    approval_status: str
    robots_status: str
    robots_crawl_delay_seconds: int | None = None
    robots_fetched_at: datetime | None = None
    robots_url: str | None = None
    found_from_url: str | None = None
    found_context: str | None = None
    pages_indexed: int
    opportunities_found: int
    error_count: int
    last_crawl_at: datetime | None = None
    next_crawl_at: datetime | None = None
    status: str
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AugmisBusinessWebPageResponse(BaseModel):
    id: str
    tenant_id: str
    connector_id: str
    seed_id: str | None = None
    domain_id: str | None = None
    url: str
    canonical_url: str
    domain: str
    title: str | None = None
    plain_text: str | None = None
    safe_html: str | None = None
    language: str | None = None
    page_type: str
    published_at: datetime | None = None
    last_modified_at: datetime | None = None
    content_hash: str | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    last_changed_at: datetime | None = None
    http_status: int | None = None
    source_metadata_json: dict[str, object] = Field(default_factory=dict)
    contact_routes_json: list[dict[str, object]] = Field(default_factory=list)
    opportunity_candidate_json: dict[str, object] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AugmisBusinessDiscoveredOpportunityCandidate(BaseModel):
    external_id: str | None = None
    source_type: str = Field(min_length=1, max_length=100)
    source_name: str = Field(min_length=1, max_length=255)
    source_url: str | None = None
    source_country: str | None = None
    title: str = Field(min_length=1, max_length=500)
    organization_name: str | None = Field(default=None, max_length=255)
    published_date: datetime | None = None
    closing_date: datetime | None = None
    country: str | None = None
    region: str | None = None
    industry: str | None = None
    requirement_summary: str | None = None
    raw_summary: str | None = None
    raw_text: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    currency: str | None = None
    evidence: list[dict[str, object]] = Field(default_factory=list)
    source_metadata: dict[str, object] = Field(default_factory=dict)
    raw_content_json: dict[str, object] = Field(default_factory=dict)
    retrieval_timestamp: datetime | None = None

    @field_validator("currency")
    @classmethod
    def validate_candidate_currency(cls, value: str | None) -> str | None:
        return _validate_currency(value)

    @field_validator("budget_min")
    @classmethod
    def validate_budget_min(cls, value: float | None) -> float | None:
        return _validate_non_negative(value, "Budget minimum")

    @field_validator("budget_max")
    @classmethod
    def validate_budget_max(cls, value: float | None) -> float | None:
        return _validate_non_negative(value, "Budget maximum")


class AugmisBusinessDiscoveryManualCreateRequest(BaseModel):
    source_url: str | None = None
    title: str = Field(min_length=1, max_length=500)
    organization_name: str | None = Field(default=None, max_length=255)
    source_name: str = Field(default="Manual Discovery", min_length=1, max_length=255)
    source_type: str = Field(default="manual", min_length=1, max_length=100)
    requirement_summary: str | None = None
    raw_summary: str | None = None
    raw_text: str | None = None
    country: str | None = None
    region: str | None = None
    industry: str | None = None
    published_date: datetime | None = None
    closing_date: datetime | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    currency: str | None = None


class AugmisBusinessDiscoveryUpdateRequest(BaseModel):
    discovery_status: str | None = Field(default=None, min_length=1, max_length=50)
    requirement_summary: str | None = None
    country: str | None = None
    region: str | None = None
    industry: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    currency: str | None = None

    @field_validator("discovery_status")
    @classmethod
    def validate_discovery_status(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return None
        normalized = normalized.lower()
        if normalized not in ALLOWED_DISCOVERY_STATUSES:
            raise ValueError(f"Invalid discovery status: {value}")
        return normalized

    @field_validator("currency")
    @classmethod
    def validate_discovery_currency(cls, value: str | None) -> str | None:
        return _validate_currency(value)


class AugmisBusinessDiscoveryExperienceMatchSummary(BaseModel):
    experience_item_id: str
    name: str
    category: str
    match_score: float
    relevance_label: str
    matching_signals: dict[str, list[str]] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)


class AugmisBusinessCommercialComponentDetail(BaseModel):
    score: float
    reason: str


class AugmisBusinessDiscoveryIntelligenceResponse(BaseModel):
    commercial_priority_score: float | None = None
    commercial_priority_band: str | None = None
    commercial_recommendation: str | None = None
    commercial_component_scores_json: dict[str, AugmisBusinessCommercialComponentDetail] = Field(
        default_factory=dict
    )
    commercial_recommendation_reasons_json: list[str] = Field(default_factory=list)
    commercial_risks_json: list[str] = Field(default_factory=list)
    experience_match_score: float | None = None
    matched_experience_ids_json: list[str] = Field(default_factory=list)
    matched_experience_reasons_json: list[str] = Field(default_factory=list)
    matched_experience_summary_json: list[AugmisBusinessDiscoveryExperienceMatchSummary] = Field(
        default_factory=list
    )
    delivery_feasibility_score: float | None = None
    delivery_complexity: str | None = None
    delivery_model: str | None = None
    urgency_status: str | None = None
    data_quality_status: str | None = None
    intelligence_updated_at: datetime | None = None


class AugmisBusinessDiscoveryAssessmentScore(BaseModel):
    score: float
    reason: str


class AugmisBusinessDiscoveryAssessmentEffort(BaseModel):
    level: str
    reason: str

    @field_validator("level")
    @classmethod
    def validate_effort_level(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        allowed = {"very_low", "low", "medium", "high", "very_high", "insufficient_information"}
        if normalized not in allowed:
            raise ValueError(f"Invalid effort level: {value}")
        return normalized


class AugmisBusinessDiscoveryDeepAssessmentResult(BaseModel):
    executive_summary: str
    recommendation: str
    recommendation_confidence: float
    solution_fit: AugmisBusinessDiscoveryAssessmentScore
    commercial_attractiveness: AugmisBusinessDiscoveryAssessmentScore
    delivery_feasibility: AugmisBusinessDiscoveryAssessmentScore
    estimated_effort: AugmisBusinessDiscoveryAssessmentEffort
    experience_matches: list[str] = Field(default_factory=list)
    key_requirements: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    suggested_next_action: str
    questions_to_clarify: list[str] = Field(default_factory=list)

    @field_validator("recommendation")
    @classmethod
    def validate_assessment_recommendation(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in {"pursue", "watch", "skip"}:
            raise ValueError(f"Invalid recommendation: {value}")
        return normalized

    @field_validator("recommendation_confidence")
    @classmethod
    def validate_assessment_confidence(cls, value: float) -> float:
        if value < 0 or value > 100:
            raise ValueError("Recommendation confidence must be between 0 and 100")
        return value


class AugmisBusinessDiscoveryAIAssessmentHistoryItem(BaseModel):
    id: str
    discovery_id: str
    analysis_version: int
    provider: str
    model: str
    recommendation: str | None = None
    recommendation_confidence: float | None = None
    commercial_score: float | None = None
    created_at: datetime | None = None


class AugmisBusinessDiscoveryAIAssessmentResponse(
    AugmisBusinessDiscoveryAIAssessmentHistoryItem
):
    prompt_bundle_version: str
    prompt_version: str
    delivery_feasibility_score: float | None = None
    executive_summary: str | None = None
    analysis_json: AugmisBusinessDiscoveryDeepAssessmentResult
    usage_json: dict[str, object] = Field(default_factory=dict)
    created_by: str | None = None


class AugmisBusinessDiscoveryResponse(BaseModel):
    id: str
    tenant_id: str
    connector_id: str
    connector_run_id: str | None = None
    external_id: str | None = None
    source_type: str
    source_name: str
    source_url: str | None = None
    canonical_source_url: str | None = None
    source_domain: str | None = None
    source_country: str | None = None
    title: str
    normalized_title: str
    organization_name: str | None = None
    normalized_organization_name: str | None = None
    published_date: datetime | None = None
    closing_date: datetime | None = None
    raw_summary: str | None = None
    requirement_summary: str | None = None
    normalized_content_json: dict[str, object] = Field(default_factory=dict)
    raw_content_json: dict[str, object] = Field(default_factory=dict)
    raw_text: str | None = None
    country: str | None = None
    region: str | None = None
    industry: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    currency: str | None = None
    discovered_at: datetime | None = None
    retrieval_timestamp: datetime | None = None
    discovery_status: str
    duplicate_of_discovery_id: str | None = None
    possible_duplicate_of_discovery_id: str | None = None
    imported_opportunity_id: str | None = None
    preliminary_relevance_score: float | None = None
    commercial_priority_score: float | None = None
    commercial_priority_band: str | None = None
    commercial_recommendation: str | None = None
    commercial_component_scores_json: dict[str, object] = Field(default_factory=dict)
    commercial_recommendation_reasons_json: list[str] = Field(default_factory=list)
    commercial_risks_json: list[str] = Field(default_factory=list)
    experience_match_score: float | None = None
    matched_experience_ids_json: list[str] = Field(default_factory=list)
    matched_experience_reasons_json: list[str] = Field(default_factory=list)
    matched_experience_summary_json: list[dict[str, object]] = Field(default_factory=list)
    delivery_feasibility_score: float | None = None
    delivery_complexity: str | None = None
    delivery_model: str | None = None
    urgency_status: str | None = None
    data_quality_status: str | None = None
    intelligence_updated_at: datetime | None = None
    source_language_code: str | None = None
    source_language_label: str | None = None
    source_language_is_english: bool = False
    translation_required: bool = False
    active_translation: dict[str, object] | None = None
    relevance_reasons_json: list[str] = Field(default_factory=list)
    matched_keywords_json: list[str] = Field(default_factory=list)
    evidence_json: list[dict[str, object]] = Field(default_factory=list)
    normalized_search_text: str | None = None
    url_fingerprint: str | None = None
    composite_fingerprint: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AugmisBusinessDiscoveryImportResponse(BaseModel):
    discovery: AugmisBusinessDiscoveryResponse
    opportunity: dict[str, object]


class AugmisBusinessDiscoveryTranslationResponse(BaseModel):
    id: str
    tenant_id: str
    discovery_id: str
    translation_version: int
    source_language: str
    source_language_label: str
    target_language: str
    translated_title: str | None = None
    translated_summary: str | None = None
    translated_description: str | None = None
    translated_detail_json: dict[str, object] = Field(default_factory=dict)
    provider: str
    model: str
    prompt_bundle_version: str
    prompt_version: str
    usage_json: dict[str, object] = Field(default_factory=dict)
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AugmisBusinessDiscoveryTranslationRequest(BaseModel):
    force: bool = False
