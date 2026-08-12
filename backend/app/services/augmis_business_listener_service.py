from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import and_, asc, case, desc, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, object_session

from app.core.config import settings
from app.core.database import SessionLocal
from app.db_models import (
    BusinessDevelopmentConnector,
    BusinessDevelopmentConnectorRun,
    BusinessDevelopmentDiscoveredOpportunity,
    BusinessDevelopmentExperienceItem,
    BusinessDevelopmentOpportunity,
    BusinessDevelopmentSearchProfile,
    BusinessDevelopmentWebPage,
)
from app.models.augmis_business_models import (
    AugmisBusinessConnectorCreateRequest,
    AugmisBusinessConnectorMetadata,
    AugmisBusinessConnectorScanRequest,
    AugmisBusinessConnectorUpdateRequest,
    AugmisBusinessDiscoveredOpportunityCandidate,
    AugmisBusinessDiscoveryUpdateRequest,
    AugmisBusinessOpportunityCreateRequest,
    AugmisBusinessSearchProfileCreateRequest,
    AugmisBusinessSearchProfileUpdateRequest,
)
from app.services.audit_service import create_audit_log
from app.services.augmis_business_connector_credential_service import (
    ResolvedProviderCredential,
    resolve_provider_credential,
    test_connector_credential,
)
from app.services.augmis_business_external_work_client import (
    ExternalWorkOpportunity,
    ExternalWorkProviderError,
    get_external_work_provider,
)
from app.services.augmis_business_search_provider_service import (
    ensure_builtin_search_providers,
    resolve_search_provider_by_code,
)
from app.services.augmis_business_discovery_translation_service import (
    get_latest_translation_row,
)
from app.services.augmis_business_commercial_intelligence_service import (
    refresh_discovery_commercial_intelligence,
    serialize_discovery_commercial_intelligence,
)
from app.services.augmis_business_freelancer_client import (
    FREELANCER_API_VERSION,
    FreelancerApiError,
    FreelancerClient,
)
from app.services.augmis_business_freelancer_mock_data import (
    FREELANCER_MOCK_FIXTURE_VERSION,
    freelancer_mock_projects,
)
from app.services.augmis_business_freelancer_query_builder import (
    FreelancerQuerySpec,
    build_freelancer_search_specs,
)
from app.services.augmis_business_service import create_opportunity, serialize_opportunity
from app.services.augmis_business_ted_client import (
    TED_SEARCH_RESULT_FIELDS,
    TedApiError,
    TedNotice,
    TedSearchClient,
)
from app.services.augmis_business_ted_query_builder import (
    TED_NOTICE_TYPE_PRESETS,
    TED_SOFTWARE_SERVICE_CPV_MAP,
    build_ted_search_query_specs,
    ted_country_scope_codes,
)
from app.services.augmis_business_web_fetcher import (
    SafeWebFetchError,
    WebFetchRuntimePolicy,
    default_web_fetch_runtime_policy,
    extract_text_from_webpage,
    fetch_public_webpage,
)
from app.services.augmis_business_web_search_provider import get_web_search_provider
from app.services.augmis_business_web_search_query_builder import build_web_search_queries
from app.services.augmis_business_translation_utils import (
    detect_discovery_language,
    is_english_language,
    language_label,
)
from app.services.augmis_business_source_content_service import (
    build_normalized_discovery_content,
)
from app.services.augmis_business_independent_discovery_service import (
    CRAWL_ENGINE_AUGMIS_NATIVE,
    CRAWL_ENGINE_SCRAPY,
    INDEPENDENT_WEB_CONNECTOR_NAME,
    INDEPENDENT_WEB_CONNECTOR_TYPE,
    INDEPENDENT_WEB_SOURCE_NAME,
    IndependentWebDiscoveryEngine,
    connector_crawl_engine,
    crawl_engine_display,
)


DEFAULT_PROFILE_NAME = "Default AUGMIS Discovery Profile"
FIXTURE_CONNECTOR_TYPE = "fixture_opportunity_connector"
FIXTURE_CONNECTOR_NAME = "Fixture Opportunity Listener"
WEB_SEARCH_CONNECTOR_TYPE = "generic_web_search"
WEB_SEARCH_CONNECTOR_NAME = "Web Opportunity Search"
TED_CONNECTOR_TYPE = "ted_procurement"
TED_CONNECTOR_NAME = "TED European Procurement"
FREELANCER_CONNECTOR_TYPE = "freelancer_marketplace"
FREELANCER_CONNECTOR_NAME = "Freelancer Marketplace"
ACTIVE_CONNECTOR_RUN_STATUSES = {"queued", "running", "retrying"}
RUN_STAGE_LABELS = {
    "PREPARING": "Preparing scan",
    "SELECTING_SEEDS": "Selecting seeds",
    "STARTING_SCRAPY": "Starting Scrapy",
    "ROBOTS_AND_FRONTIER": "Preparing robots and frontier",
    "FETCHING": "Fetching pages",
    "PARSING": "Parsing pages",
    "FOLLOWING_LISTINGS": "Following procurement listings",
    "EXTRACTING": "Extracting opportunity signals",
    "VALIDATING": "Validating candidates",
    "INGESTING": "Ingesting discoveries",
    "FINALIZING": "Finalizing run",
    "COMPLETED": "Completed",
    "FAILED": "Failed",
}
REMOTEOK_CONNECTOR_TYPE = "remote_job_feed"
REMOTEOK_CONNECTOR_NAME = "Remote OK"
ARBEITNOW_CONNECTOR_TYPE = "job_board_api"
ARBEITNOW_CONNECTOR_NAME = "Arbeitnow"
REMOTIVE_CONNECTOR_TYPE = "remote_job_api"
REMOTIVE_CONNECTOR_NAME = "Remotive"
ADZUNA_CONNECTOR_TYPE = "job_search_api"
ADZUNA_CONNECTOR_NAME = "Adzuna"
CONNECTOR_TEST_LABEL = "TEST / FIXTURE"
CONNECTOR_PRODUCTION_LABEL = "PRODUCTION"
CONNECTOR_TEST_MODE_LABEL = "TEST / MOCK"
EMPLOYMENT_CONTRACT_SOURCE_TYPE = "employment_contract"

WEB_SEARCH_FETCH_MAX_BYTES_MIN = 25_000
WEB_SEARCH_FETCH_MAX_BYTES_MAX = 1_000_000
WEB_SEARCH_FETCH_TIMEOUT_MIN = 3
WEB_SEARCH_FETCH_TIMEOUT_MAX = 30
WEB_SEARCH_EXTRACTED_TEXT_MIN = 5_000
WEB_SEARCH_EXTRACTED_TEXT_MAX = 100_000
WEB_SEARCH_REDIRECTS_MIN = 0
WEB_SEARCH_REDIRECTS_MAX = 5
WEB_SEARCH_MAX_SOURCE_FETCHES_MIN = 0
WEB_SEARCH_MAX_SOURCE_FETCHES_MAX = 100
URL_SCHEME_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")
JOB_TERMS = ("job", "career", "vacancy", "hiring", "recruiter", "internship", "full-time")
NEWS_TERMS = ("news", "press release", "blog", "article", "tutorial", "documentation", "wikipedia")
BUYING_INTENT_TERMS = ("rfp", "rfq", "tender", "proposal", "vendor", "supplier", "quotation", "procurement")
TED_RELEVANCE_BANDS = (
    ("strong", 80.0),
    ("good", 65.0),
    ("possible", 50.0),
    ("weak", 35.0),
    ("low", 0.0),
)
DEFAULT_IRRELEVANT_THRESHOLD = 25.0
TED_CLOSING_SOON_DAYS = 14
TED_IRRELEVANT_THRESHOLD = 35.0
FREELANCER_IRRELEVANT_THRESHOLD = 35.0
EXTERNAL_WORK_IRRELEVANT_THRESHOLD = 35.0
VALIDITY_CONFIRMED_THRESHOLD = 85
VALIDITY_LIKELY_THRESHOLD = 70
VALIDITY_REVIEW_THRESHOLD = 50
VALIDITY_CLASS_CONFIRMED = "CONFIRMED_OPPORTUNITY"
VALIDITY_CLASS_LIKELY = "LIKELY_OPPORTUNITY"
VALIDITY_CLASS_LISTING = "OPPORTUNITY_LISTING"
VALIDITY_CLASS_INFORMATIONAL = "INFORMATIONAL_CONTENT"
VALIDITY_CLASS_MARKETING = "PRODUCT_MARKETING"
VALIDITY_CLASS_NEWS = "NEWS_CONTENT"
VALIDITY_CLASS_EXPIRED = "EXPIRED_CLOSED"
VALIDITY_CLASS_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
VALIDITY_CLASS_UNKNOWN = "UNKNOWN"
ACTIONABILITY_ACTIONABLE = "ACTIONABLE"
ACTIONABILITY_PARTIAL = "PARTIALLY_ACTIONABLE"
ACTIONABILITY_RESEARCH = "RESEARCH_REQUIRED"
ACTIONABILITY_PLATFORM_ONLY = "PLATFORM_ONLY"
ACTIONABILITY_NOT = "NOT_ACTIONABLE"
INFORMATIONAL_CONTENT_TERMS = (
    "how to",
    "guide",
    "use case",
    "use cases",
    "best practice",
    "best practices",
    "everything you need to know",
    "examples",
    "strategies",
    "blog",
    "article",
    "whitepaper",
    "tutorial",
)
PRODUCT_MARKETING_TERMS = (
    "pricing",
    "book a demo",
    "request a demo",
    "schedule a demo",
    "product features",
    "feature overview",
    "solution overview",
    "platform overview",
    "why choose",
    "software",
    "tracker",
    "automation strategies",
)
PROCUREMENT_NOTICE_TERMS = (
    "request for proposal",
    "rfp",
    "request for quotation",
    "rfq",
    "expression of interest",
    "eoi",
    "invitation to tender",
    "request for bid",
    "tender notice",
    "notice inviting tender",
)
PROCUREMENT_SCOPE_TERMS = (
    "implementation",
    "workflow",
    "records management",
    "document management",
    "integration",
    "training",
    "deliverable",
    "scope of work",
    "services",
    "system",
    "platform",
)
SUBMISSION_ROUTE_TERMS = (
    "submit proposal",
    "submit bid",
    "apply now",
    "tender portal",
    "procurement portal",
    "bid submission",
    "application form",
)
LISTING_TERMS = (
    "tenders by organisation",
    "tenders by organization",
    "active tenders",
    "browse tenders",
    "latest tenders",
    "open opportunities",
    "current vacancies",
    "open roles",
    "all jobs",
)
EXPIRY_TERMS = (
    "closed",
    "deadline passed",
    "expired",
    "award notice",
    "contract awarded",
)
REFERENCE_PATTERNS = (
    re.compile(r"\b(?:reference|ref|notice|tender|rfp|rfq|eoi|bid)\s*(?:number|no\.?|id)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/_-]{2,})", re.IGNORECASE),
    re.compile(r"\b(?:tender|rfp|rfq|eoi|bid)-\d{2,}(?:[-/][A-Z0-9]+)*\b", re.IGNORECASE),
)
TED_HIGH_RELEVANCE_CPV: dict[str, str] = {
    "48170000": "Compliance software package",
    "48211000": "Platform interconnectivity software package",
    "48311000": "Document management software package",
    "48311100": "Document management system",
    "48612000": "Database-management system",
    "48810000": "Information systems",
    "72212170": "Compliance software development services",
    "72212311": "Document management software development services",
    "72212445": "Customer Relation Management software development services",
    "72212451": "Enterprise resource planning software development services",
    "72212461": "Analytical or scientific software development services",
    "72212463": "Statistical software development services",
    "72212482": "Business intelligence software development services",
    "72222300": "Information technology services",
    "72223000": "Information technology requirements review services",
    "72224100": "System implementation planning services",
    "72227000": "Software integration consultancy services",
    "72230000": "Custom software development services",
    "72240000": "Systems analysis and programming services",
    "72243000": "Programming services",
    "72245000": "Contract systems analysis and programming services",
    "72262000": "Software development services",
    "72263000": "Software implementation services",
    "72265000": "Software configuration services",
    "72266000": "Software consultancy services",
    "72267100": "Maintenance of information technology software",
    "72316000": "Data analysis services",
    "72320000": "Database services",
    "72322000": "Data management services",
    "72421000": "Internet or intranet client application development services",
    "72422000": "Internet or intranet server application development services",
    "72512000": "Document management services",
    "72513000": "Office automation services",
}
TED_MEDIUM_RELEVANCE_CPV: dict[str, str] = {
    "48000000": "Software package and information systems",
    "48180000": "Medical software package",
    "48422000": "Software package suites",
    "48442000": "Financial systems software package",
    "48783000": "Content management software package",
    "48814000": "Medical information systems",
    "72212200": "Networking, Internet and intranet software development services",
    "72221000": "Business analysis consultancy services",
    "72222000": "Information systems or technology strategic review and planning services",
    "72224000": "Project management consultancy services",
    "72300000": "Data services",
    "72413000": "World wide web (www) site design services",
    "72420000": "Internet development services",
    "72611000": "Technical computer support services",
}
TED_LOW_RELEVANCE_CPV: dict[str, str] = {
    "22450000": "Security-type printed matter",
    "30000000": "Office and computing machinery, equipment and supplies except furniture and software packages",
    "30200000": "Computer equipment and supplies",
    "34000000": "Transport equipment and auxiliary products to transportation",
    "45000000": "Construction work",
    "45200000": "Works for complete or part construction and civil engineering work",
    "45233100": "Construction work for highways, roads",
    "55500000": "Canteen and catering services",
    "71000000": "Architectural, construction, engineering and inspection services",
    "71322000": "Engineering design services for the construction of civil engineering works",
    "72100000": "Hardware consultancy services",
    "79111000": "Legal advisory services",
    "79410000": "Business and management consultancy services",
    "79411000": "General management consultancy services",
    "79420000": "Management-related services",
    "79620000": "Supply services of personnel including temporary staff",
    "79710000": "Security services",
    "79713000": "Guard services",
    "90910000": "Cleaning services",
}
TED_POSITIVE_DIMENSIONS: tuple[dict[str, Any], ...] = (
    {"name": "Software / Digital Solution", "title_terms": ("software", "system", "platform", "application", "digital", "solution", "sap", "erp", "his", "pki", "devops"), "body_terms": ("software", "system", "platform", "application", "digital", "solution", "devops"), "title_weight": 12.0, "body_weight": 6.0},
    {"name": "Workflow / Process Automation", "title_terms": ("workflow", "automation", "approval", "process"), "body_terms": ("workflow", "workflow automation", "automation", "approval workflow", "process automation"), "title_weight": 10.0, "body_weight": 5.0},
    {"name": "Document & Records Management", "title_terms": ("document", "records", "archive", "archival"), "body_terms": ("document management", "records management", "document control", "repository", "archiv"), "title_weight": 10.0, "body_weight": 5.0},
    {"name": "Data / Analytics / Dashboarding", "title_terms": ("analytics", "dashboard", "reporting", "business intelligence", "data"), "body_terms": ("analytics", "dashboard", "reporting", "business intelligence", "data analysis"), "title_weight": 10.0, "body_weight": 5.0},
    {"name": "AI / Intelligent Automation", "title_terms": ("artificial intelligence", "machine learning", "intelligent"), "body_terms": ("artificial intelligence", "machine learning", "intelligent automation"), "title_weight": 8.0, "body_weight": 4.0},
    {"name": "Integration / API / Enterprise Systems", "title_terms": ("integration", "api", "erp", "sap", "intranet", "internet"), "body_terms": ("integration", "api integration", "system integration", "erp", "sap", "intranet", "internet"), "title_weight": 10.0, "body_weight": 5.0},
    {"name": "Inspection / Compliance / Audit / Governance", "title_terms": ("inspection", "compliance", "audit", "governance", "verification"), "body_terms": ("inspection", "compliance", "audit", "governance", "verification", "risk management"), "title_weight": 8.0, "body_weight": 4.0},
    {"name": "Portal / Case / Request / Service Management", "title_terms": ("portal", "case", "request", "service", "access"), "body_terms": ("portal", "case management", "request", "service management", "access management"), "title_weight": 8.0, "body_weight": 4.0},
    {"name": "Custom Application / Digital Transformation", "title_terms": ("custom", "transformation", "renewal", "upgrade", "modernisation", "modernization"), "body_terms": ("custom software", "digital transformation", "upgrade", "implementation", "rollout"), "title_weight": 9.0, "body_weight": 4.0},
)
TED_NEGATIVE_SIGNAL_RULES: tuple[dict[str, Any], ...] = (
    {"name": "Construction works", "terms": ("construction", "civil engineering", "railway", "road", "building works", "robot budowlanych"), "cpv_codes": ("45000000", "45200000", "45233100"), "penalty": 30.0},
    {"name": "Legal advisory", "terms": ("legal advisory", "legal services", "doradztwo prawne", "jogi tanácsadás"), "cpv_codes": ("79111000",), "penalty": 28.0},
    {"name": "Hardware-only procurement", "terms": ("hardware", "equipment", "printer", "glukometr", "device"), "cpv_codes": ("30000000", "30200000"), "penalty": 22.0},
    {"name": "Vehicles and transport equipment", "terms": ("vehicle", "fleet", "bus", "rail rolling stock"), "cpv_codes": ("34000000",), "penalty": 24.0},
    {"name": "Catering or cleaning", "terms": ("catering", "cleaning", "canteen"), "cpv_codes": ("55500000", "90910000"), "penalty": 24.0},
    {"name": "Recruitment or personnel supply", "terms": ("recruitment", "temporary staff", "personnel supply", "labour hire"), "cpv_codes": ("79620000",), "penalty": 20.0},
    {"name": "Security guarding", "terms": ("guard services", "security guarding", "alarm monitoring"), "cpv_codes": ("79710000", "79713000"), "penalty": 22.0},
    {"name": "Generic management consulting", "terms": ("management consultancy", "general management consultancy", "specialist support"), "cpv_codes": ("79410000", "79411000", "79420000"), "penalty": 16.0},
)
TED_BUYER_QUALITY_TERMS = (
    "ministry",
    "municipality",
    "city",
    "county",
    "authority",
    "agency",
    "department",
    "commission",
    "hospital",
    "university",
    "transport",
    "rail",
    "utility",
    "water",
    "energy",
    "defence",
    "health",
    "regulator",
)
FREELANCER_NEGATIVE_SIGNAL_RULES: tuple[dict[str, Any], ...] = (
    {"name": "Design-only work", "terms": ("logo design", "graphic design", "brochure", "banner design", "photoshop"), "penalty": 30.0},
    {"name": "Data entry or scraping", "terms": ("data entry", "copy paste", "lead scraping", "web scraping list", "captcha"), "penalty": 26.0},
    {"name": "SEO or social posting", "terms": ("seo", "social media posting", "instagram", "facebook ads", "backlinks"), "penalty": 24.0},
    {"name": "Content-only work", "terms": ("article writing", "blog writing", "translation job", "video editing"), "penalty": 24.0},
    {"name": "Academic or spam work", "terms": ("assignment", "homework", "exam", "bulk account creation", "crypto trading"), "penalty": 28.0},
)
SCHEDULE_RETRY_DELAYS_MINUTES = (5, 15)
SCHEDULE_STALE_RUN_THRESHOLD_MINUTES = 120
SCRAPY_STOP_GRACE_SECONDS = 8
SCRAPY_STOP_KILL_TIMEOUT_SECONDS = 5
SCHEDULE_LABELS = {
    "manual": "Manual",
    "hourly_interval": "Every {hours} hour{suffix}",
    "daily": "Daily · {time}",
    "weekly": "Weekly · {weekday} · {time}",
}
WEEKDAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
TRANSIENT_ERROR_HINTS = (
    "timeout",
    "timed out",
    "too many requests",
    "rate limit",
    "http 429",
    "http 502",
    "http 503",
    "http 504",
    "connection reset",
    "temporary",
    "temporarily",
    "network",
    "service unavailable",
)
NON_RETRYABLE_ERROR_HINTS = (
    "not configured",
    "credential",
    "disabled",
    "validation",
    "invalid schedule",
    "unknown timezone",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = WHITESPACE_PATTERN.sub(" ", value.replace("\x00", "")).strip()
    return cleaned or None


def _limited_unique_strings(values: list[str], *, limit: int = 8) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned:
            continue
        normalized = cleaned.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        items.append(cleaned)
        if len(items) >= limit:
            break
    return items


def _contains_any_term(value: str, terms: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(term in lowered for term in terms)


def _match_terms(value: str, terms: tuple[str, ...], *, limit: int = 6) -> list[str]:
    lowered = value.lower()
    matches = [term for term in terms if term in lowered]
    return _limited_unique_strings(matches, limit=limit)


def _extract_reference_hint(value: str) -> str | None:
    for pattern in REFERENCE_PATTERNS:
        match = pattern.search(value)
        if match:
            extracted = _clean_text(match.group(1) if match.lastindex else match.group(0))
            if extracted and extracted.lower() not in {"number", "id", "no"}:
                return extracted
    return None


def _extract_validity_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    validity = payload.get("opportunity_validity")
    return dict(validity) if isinstance(validity, dict) else {}


def _validity_band(score: int) -> str:
    if score >= VALIDITY_CONFIRMED_THRESHOLD:
        return "confirmed"
    if score >= VALIDITY_LIKELY_THRESHOLD:
        return "likely"
    if score >= VALIDITY_REVIEW_THRESHOLD:
        return "review"
    return "not_opportunity"


def _opportunity_validity_payload(
    candidate: AugmisBusinessDiscoveredOpportunityCandidate,
) -> dict[str, Any]:
    source_metadata = dict(candidate.source_metadata or {})
    raw_content = dict(candidate.raw_content_json or {})
    page_type = str(raw_content.get("page_type") or source_metadata.get("opportunity_class") or "").strip().lower()
    title = _clean_text(candidate.title) or ""
    summary = _clean_text(candidate.requirement_summary or candidate.raw_summary or "") or ""
    raw_text = _clean_text(candidate.raw_text or "") or ""
    searchable = " ".join(part for part in [title, summary, raw_text[:6000]] if part).lower()
    provider = str(raw_content.get("provider") or source_metadata.get("provider") or "").strip().lower()
    organization_name = _clean_text(candidate.organization_name)
    reference_number = _clean_text(
        str(source_metadata.get("reference_number") or raw_content.get("reference_number") or _extract_reference_hint(searchable) or "")
    )
    application_url = _clean_text(
        str(source_metadata.get("application_url") or raw_content.get("application_url") or "")
    )
    contact_routes = source_metadata.get("contact_routes") or raw_content.get("contact_routes") or []
    evidence_entries = list(candidate.evidence or [])
    procurement_doc_url = _clean_text(str(raw_content.get("document_url") or source_metadata.get("document_url") or ""))
    procurement_intent_terms = _match_terms(searchable, PROCUREMENT_NOTICE_TERMS)
    informational_terms = _match_terms(searchable, INFORMATIONAL_CONTENT_TERMS)
    marketing_terms = _match_terms(searchable, PRODUCT_MARKETING_TERMS)
    listing_terms = _match_terms(searchable, LISTING_TERMS)
    news_terms = _match_terms(searchable, NEWS_TERMS)
    expiry_terms = _match_terms(searchable, EXPIRY_TERMS)
    scope_terms = _match_terms(searchable, PROCUREMENT_SCOPE_TERMS)
    submission_terms = _match_terms(searchable, SUBMISSION_ROUTE_TERMS)
    has_detail_page = page_type in {"procurement_detail", "rfp", "rfq", "eoi", "tender", "job_detail"}
    is_listing_page = page_type in {"procurement_list", "career_list"} or bool(listing_terms)
    has_contact = any(isinstance(item, dict) and _clean_text(str(item.get("value") or "")) for item in contact_routes) or any(
        isinstance(item, dict) and str(item.get("type") or "").lower() == "contact_evidence"
        for item in evidence_entries
    )
    has_submission_route = bool(application_url) and (
        _contains_any_term(application_url, ("apply", "submit", "tender", "bid", "procurement", "jobs", "career", "project"))
        or bool(submission_terms)
    )
    if not has_submission_route and candidate.source_type in {"employment_contract", "marketplace_project"}:
        has_submission_route = bool(_clean_text(candidate.source_url))
    has_reference = bool(reference_number)
    has_buyer = bool(organization_name)
    closing_at = _as_utc(candidate.closing_date)
    is_expired = False
    if closing_at is not None and closing_at < _now():
        is_expired = True
    elif expiry_terms:
        is_expired = True

    score = 0
    positive_evidence: list[str] = []
    negative_evidence: list[str] = []
    reason_codes: list[str] = []

    if candidate.source_type == "public_procurement" or procurement_intent_terms:
        score += 25
        positive_evidence.append("Explicit procurement notice wording detected.")
        reason_codes.append("procurement_intent")
    elif candidate.source_type == "employment_contract":
        score += 18
        positive_evidence.append("Specific employment or contract opportunity context detected.")
        reason_codes.append("employment_intent")
    elif candidate.source_type == "marketplace_project":
        score += 18
        positive_evidence.append("Marketplace project context detected.")
        reason_codes.append("marketplace_intent")

    if has_buyer:
        score += 15
        positive_evidence.append(f"Specific buyer or issuer identified: {organization_name}.")
        reason_codes.append("buyer_identified")
    if scope_terms or len(summary) >= 90:
        score += 20
        positive_evidence.append("Specific requirement or scope evidence detected.")
        reason_codes.append("scope_detected")
    if has_reference:
        score += 10
        positive_evidence.append(f"Reference or notice identifier detected: {reference_number}.")
        reason_codes.append("reference_detected")
    if closing_at is not None:
        score += 8
        positive_evidence.append(
            f"Closing or expiry date detected: {closing_at.date().isoformat()}."
        )
        reason_codes.append("deadline_detected")
    if has_submission_route:
        score += 10
        positive_evidence.append("Submission or application route is available.")
        reason_codes.append("submission_route")
    if has_detail_page:
        score += 7
        positive_evidence.append("Detail-page structure detected.")
        reason_codes.append("detail_page")
    if has_contact or procurement_doc_url:
        score += 5
        positive_evidence.append("Supporting contact or document evidence is available.")
        reason_codes.append("supporting_contact_or_document")

    if informational_terms:
        score -= min(30, 8 * len(informational_terms))
        negative_evidence.append(f"Informational content signals detected: {', '.join(informational_terms)}.")
        reason_codes.append("informational_content")
    if marketing_terms:
        score -= min(28, 9 * len(marketing_terms))
        negative_evidence.append(f"Product-marketing signals detected: {', '.join(marketing_terms)}.")
        reason_codes.append("product_marketing")
    if news_terms and candidate.source_type == "web_discovery":
        score -= 18
        negative_evidence.append(f"News or article signals detected: {', '.join(news_terms)}.")
        reason_codes.append("news_content")
    if is_listing_page:
        score -= 22
        negative_evidence.append("Listing page detected; this is not one actionable opportunity.")
        reason_codes.append("listing_page")
    if is_expired:
        score -= 45
        negative_evidence.append("Opportunity appears expired or already closed.")
        reason_codes.append("expired_or_closed")
    if not has_buyer:
        score -= 12
        negative_evidence.append("No specific buyer, issuer, employer, or client was identified.")
        reason_codes.append("missing_buyer")
    if not has_submission_route and candidate.source_type != "marketplace_project":
        score -= 10
        negative_evidence.append("No submission or application route was identified.")
        reason_codes.append("missing_submission_route")

    score = max(0, min(100, score))
    band = _validity_band(score)

    validity_class = VALIDITY_CLASS_UNKNOWN
    if is_expired:
        validity_class = VALIDITY_CLASS_EXPIRED
    elif is_listing_page:
        validity_class = VALIDITY_CLASS_LISTING
    elif marketing_terms and score < VALIDITY_REVIEW_THRESHOLD:
        validity_class = VALIDITY_CLASS_MARKETING
    elif (informational_terms or news_terms) and score < VALIDITY_REVIEW_THRESHOLD:
        validity_class = VALIDITY_CLASS_INFORMATIONAL if informational_terms else VALIDITY_CLASS_NEWS
    elif score >= VALIDITY_CONFIRMED_THRESHOLD:
        validity_class = VALIDITY_CLASS_CONFIRMED
    elif score >= VALIDITY_LIKELY_THRESHOLD:
        validity_class = VALIDITY_CLASS_LIKELY
    elif score >= VALIDITY_REVIEW_THRESHOLD:
        validity_class = VALIDITY_CLASS_INSUFFICIENT
    elif candidate.source_type == "public_procurement" and (has_reference or closing_at or has_submission_route):
        validity_class = VALIDITY_CLASS_INSUFFICIENT
    elif candidate.source_type == "web_discovery":
        validity_class = VALIDITY_CLASS_INFORMATIONAL if informational_terms else VALIDITY_CLASS_MARKETING if marketing_terms else VALIDITY_CLASS_UNKNOWN
    else:
        validity_class = VALIDITY_CLASS_INSUFFICIENT

    actionability = ACTIONABILITY_NOT
    if validity_class == VALIDITY_CLASS_EXPIRED:
        actionability = ACTIONABILITY_NOT
    elif validity_class in {VALIDITY_CLASS_INFORMATIONAL, VALIDITY_CLASS_MARKETING, VALIDITY_CLASS_NEWS, VALIDITY_CLASS_LISTING, VALIDITY_CLASS_UNKNOWN}:
        actionability = ACTIONABILITY_NOT
    elif candidate.source_type == "marketplace_project":
        actionability = ACTIONABILITY_PLATFORM_ONLY
    elif has_submission_route and not is_expired:
        actionability = ACTIONABILITY_ACTIONABLE
    elif has_buyer and (has_reference or scope_terms or has_detail_page):
        actionability = ACTIONABILITY_RESEARCH
    else:
        actionability = ACTIONABILITY_PARTIAL

    eligible_for_inbox = validity_class in {VALIDITY_CLASS_CONFIRMED, VALIDITY_CLASS_LIKELY} and not is_expired
    review_candidate = band == "review" and validity_class == VALIDITY_CLASS_INSUFFICIENT
    if validity_class in {VALIDITY_CLASS_INFORMATIONAL, VALIDITY_CLASS_MARKETING, VALIDITY_CLASS_NEWS, VALIDITY_CLASS_LISTING, VALIDITY_CLASS_EXPIRED, VALIDITY_CLASS_UNKNOWN}:
        eligible_for_inbox = False

    return {
        "validity_score": score,
        "validity_band": band,
        "validity_class": validity_class,
        "actionability": actionability,
        "eligible_for_inbox": eligible_for_inbox,
        "review_candidate": review_candidate,
        "positive_evidence": _limited_unique_strings(positive_evidence, limit=5),
        "negative_evidence": _limited_unique_strings(negative_evidence, limit=5),
        "reason_codes": _limited_unique_strings(reason_codes, limit=10),
        "source_url": candidate.source_url,
        "page_type": page_type or None,
        "provider": provider or None,
        "reference_number": reference_number,
        "application_url": application_url,
        "has_submission_route": has_submission_route,
        "has_buyer": has_buyer,
        "is_expired": is_expired,
    }


def _validity_filter_reason(validity: dict[str, Any]) -> str:
    validity_class = str(validity.get("validity_class") or VALIDITY_CLASS_UNKNOWN)
    return f"validity:{validity_class.lower()}"


def _normalized_content_payload(
    requirement_summary: str | None,
    raw_summary: str | None,
    raw_text: str | None,
) -> tuple[str | None, str | None, str | None, dict[str, Any]]:
    normalized = build_normalized_discovery_content(
        requirement_value=requirement_summary,
        summary_value=raw_summary,
        full_text_value=raw_text,
    )
    normalized_requirement = _clean_text(
        str((normalized.get("requirement") or {}).get("plain_text") or "")
    )
    normalized_summary = _clean_text(
        str((normalized.get("summary") or {}).get("plain_text") or "")
    )
    normalized_full_text = _clean_text(
        str((normalized.get("full_text") or {}).get("plain_text") or "")
    )
    return normalized_requirement, normalized_summary, normalized_full_text, normalized


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _independent_run_crawl_engine(
    *,
    connector: BusinessDevelopmentConnector,
    payload: AugmisBusinessConnectorScanRequest | None = None,
    run: BusinessDevelopmentConnectorRun | None = None,
) -> str:
    if run is not None:
        metadata_engine = str((run.run_metadata_json or {}).get("crawl_engine") or "").strip().lower()
        if metadata_engine:
            return connector_crawl_engine(connector.configuration_json or {}, metadata_engine)
    if payload is not None and payload.crawl_engine:
        return connector_crawl_engine(connector.configuration_json or {}, payload.crawl_engine)
    return connector_crawl_engine(connector.configuration_json or {})


def _scrapy_subprocess_python() -> Path:
    return Path(__file__).resolve().parents[2] / ".venv" / "Scripts" / "python.exe"


def _scrapy_stop_file(run_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"augmis_scrapy_stop_{run_id}.signal"


def _is_connector_run_cancelled(tenant_id: str, run_id: str) -> bool:
    check_db = SessionLocal()
    try:
        run = (
            check_db.query(BusinessDevelopmentConnectorRun)
            .filter(
                BusinessDevelopmentConnectorRun.tenant_id == tenant_id,
                BusinessDevelopmentConnectorRun.id == run_id,
            )
            .first()
        )
        return bool(run and run.status == "cancelled")
    finally:
        check_db.close()


def _schedule_timezone_name(
    schedule_timezone: str | None,
) -> str:
    return (schedule_timezone or settings.CONNECTOR_SYNC_SCHEDULER_TIMEZONE or "UTC").strip() or "UTC"


def _parse_schedule_time_local(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    hour_text, minute_text = value.split(":", 1)
    return int(hour_text), int(minute_text)


def _build_schedule_expression(
    *,
    schedule_enabled: bool,
    schedule_type: str,
    schedule_interval_minutes: int | None,
    schedule_day_of_week: int | None,
    schedule_time_local: str | None,
) -> str | None:
    if not schedule_enabled:
        return "Manual"
    if schedule_type == "hourly_interval" and schedule_interval_minutes:
        hours = max(1, schedule_interval_minutes // 60)
        return SCHEDULE_LABELS["hourly_interval"].format(hours=hours, suffix="" if hours == 1 else "s")
    if schedule_type == "daily" and schedule_time_local:
        return SCHEDULE_LABELS["daily"].format(time=schedule_time_local)
    if schedule_type == "weekly" and schedule_time_local and schedule_day_of_week in range(7):
        return SCHEDULE_LABELS["weekly"].format(weekday=WEEKDAY_LABELS[schedule_day_of_week], time=schedule_time_local)
    return "Manual"


def _compute_next_run_at(
    *,
    schedule_type: str,
    schedule_interval_minutes: int | None,
    schedule_day_of_week: int | None,
    schedule_time_local: str | None,
    schedule_timezone: str | None,
    after_utc: datetime,
    anchor_utc: datetime | None = None,
) -> datetime | None:
    if schedule_type == "manual":
        return None
    current_utc = _as_utc(after_utc) or _now()
    if schedule_type == "hourly_interval":
        interval_minutes = schedule_interval_minutes or 60
        interval = timedelta(minutes=interval_minutes)
        anchor = _as_utc(anchor_utc) or current_utc
        next_run = anchor
        while next_run <= current_utc:
            next_run = next_run + interval
        return next_run
    local_zone = ZoneInfo(_schedule_timezone_name(schedule_timezone))
    local_now = current_utc.astimezone(local_zone)
    parsed_time = _parse_schedule_time_local(schedule_time_local) or (7, 0)
    if schedule_type == "daily":
        candidate = local_now.replace(
            hour=parsed_time[0],
            minute=parsed_time[1],
            second=0,
            microsecond=0,
        )
        if candidate <= local_now:
            candidate = candidate + timedelta(days=1)
        return candidate.astimezone(timezone.utc)
    if schedule_type == "weekly":
        weekday = schedule_day_of_week if schedule_day_of_week in range(7) else 0
        days_ahead = (weekday - local_now.weekday()) % 7
        candidate = (local_now + timedelta(days=days_ahead)).replace(
            hour=parsed_time[0],
            minute=parsed_time[1],
            second=0,
            microsecond=0,
        )
        if candidate <= local_now:
            candidate = candidate + timedelta(days=7)
        return candidate.astimezone(timezone.utc)
    return None


def _validate_schedule_configuration(
    *,
    schedule_enabled: bool,
    schedule_type: str,
    schedule_interval_minutes: int | None,
    schedule_day_of_week: int | None,
    schedule_time_local: str | None,
    schedule_timezone: str | None,
):
    normalized_type = (schedule_type or "manual").strip().lower()
    if not schedule_enabled:
        return
    if normalized_type == "manual":
        raise HTTPException(status_code=400, detail="Enabled schedules must use an automatic schedule type.")
    if normalized_type == "hourly_interval":
        if schedule_interval_minutes is None or schedule_interval_minutes < 60 or schedule_interval_minutes % 60 != 0:
            raise HTTPException(status_code=400, detail="Hourly interval schedules must use whole-hour intervals of at least 1 hour.")
        return
    if normalized_type == "daily":
        if not schedule_time_local:
            raise HTTPException(status_code=400, detail="Daily schedules require a local time.")
        _parse_schedule_time_local(schedule_time_local)
        _ = ZoneInfo(_schedule_timezone_name(schedule_timezone))
        return
    if normalized_type == "weekly":
        if schedule_day_of_week not in range(7):
            raise HTTPException(status_code=400, detail="Weekly schedules require a valid weekday.")
        if not schedule_time_local:
            raise HTTPException(status_code=400, detail="Weekly schedules require a local time.")
        _parse_schedule_time_local(schedule_time_local)
        _ = ZoneInfo(_schedule_timezone_name(schedule_timezone))
        return
    raise HTTPException(status_code=400, detail="Unsupported connector schedule type.")


def _is_retryable_scan_error(error_summary: str | None) -> bool:
    lowered = str(error_summary or "").strip().lower()
    if not lowered:
        return False
    if any(hint in lowered for hint in NON_RETRYABLE_ERROR_HINTS):
        return False
    return any(hint in lowered for hint in TRANSIENT_ERROR_HINTS)


def _run_audit_action(run_type: str) -> str:
    if run_type == "scheduled":
        return "connector_scheduled_scan_started"
    if run_type == "retry":
        return "connector_scan_retry_started"
    return "connector_manual_scan_started"


def _normalize_text(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    return cleaned.lower()


def _normalize_title(value: str) -> str:
    return _normalize_text(value) or value.strip().lower()


def _normalize_url(value: str | None) -> tuple[str | None, str | None]:
    cleaned = _clean_text(value)
    if not cleaned:
        return None, None
    if not URL_SCHEME_PATTERN.match(cleaned):
        return cleaned, None
    parts = urlsplit(cleaned)
    hostname = parts.hostname.lower() if parts.hostname else None
    path = parts.path.rstrip("/") or "/"
    normalized = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))
    return normalized, hostname


def _normalize_country_or_region(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    return cleaned


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _contains_any_phrase(text: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) for term in terms)


def _ted_candidate_cpv_codes(candidate: AugmisBusinessDiscoveredOpportunityCandidate) -> list[str]:
    raw = candidate.raw_content_json or candidate.source_metadata or {}
    cpv_codes = raw.get("cpv_codes") or []
    seen: set[str] = set()
    normalized: list[str] = []
    for item in cpv_codes if isinstance(cpv_codes, list) else []:
        code = str(item or "").strip()
        if code and code not in seen:
            seen.add(code)
            normalized.append(code)
    return normalized


def _ted_relevance_band(score: float | None) -> str:
    if score is None:
        return "unknown"
    for label, threshold in TED_RELEVANCE_BANDS:
        if score >= threshold:
            return label
    return "low"


def _ted_closing_status(closing_date: datetime | None, now: datetime | None = None) -> str:
    if closing_date is None:
        return "unknown"
    current = now or _now()
    if closing_date.tzinfo is None:
        closing_date = closing_date.replace(tzinfo=timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    if closing_date < current:
        return "expired"
    if closing_date <= current + timedelta(days=TED_CLOSING_SOON_DAYS):
        return "closing_soon"
    return "open"


def _preliminary_irrelevant_threshold(source_type: str | None) -> float:
    normalized = (source_type or "").strip().lower()
    if normalized == "public_procurement":
        return TED_IRRELEVANT_THRESHOLD
    if normalized == "marketplace_project":
        return FREELANCER_IRRELEVANT_THRESHOLD
    return DEFAULT_IRRELEVANT_THRESHOLD


def _ted_title_and_body(candidate: AugmisBusinessDiscoveredOpportunityCandidate) -> tuple[str, str]:
    title_text = _normalize_text(candidate.title) or ""
    body_parts = [
        _normalize_text(candidate.requirement_summary) or "",
        _normalize_text(candidate.raw_summary) or "",
        _normalize_text(candidate.raw_text) or "",
    ]
    body_text = " ".join(part for part in body_parts if part)
    return title_text, body_text


def _split_relevance_reasons(reasons: list[str]) -> tuple[list[str], list[str]]:
    positives = [reason.removeprefix("Matched signal: ").strip() for reason in reasons if reason.startswith("Matched signal: ")]
    negatives = [reason.removeprefix("Negative signal: ").strip() for reason in reasons if reason.startswith("Negative signal: ")]
    return positives, negatives


def _fingerprint(*parts: str | None) -> str | None:
    normalized = [part.strip().lower() for part in parts if part and part.strip()]
    if not normalized:
        return None
    return sha256("||".join(normalized).encode("utf-8")).hexdigest()


def _searchable_text(candidate: AugmisBusinessDiscoveredOpportunityCandidate) -> str:
    pieces = [
        candidate.title,
        candidate.organization_name,
        candidate.requirement_summary,
        candidate.raw_summary,
        candidate.raw_text,
        candidate.country,
        candidate.region,
        candidate.industry,
    ]
    return " ".join(part for part in [_normalize_text(piece) for piece in pieces] if part)


def _serialize_search_profile(row: BusinessDevelopmentSearchProfile) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "name": row.name,
        "enabled": row.enabled,
        "target_regions_json": row.target_regions_json or [],
        "target_countries_json": row.target_countries_json or [],
        "target_industries_json": row.target_industries_json or [],
        "include_keywords_json": row.include_keywords_json or [],
        "include_technologies_json": row.include_technologies_json or [],
        "include_capabilities_json": row.include_capabilities_json or [],
        "exclude_keywords_json": row.exclude_keywords_json or [],
        "excluded_domains_json": row.excluded_domains_json or [],
        "excluded_categories_json": row.excluded_categories_json or [],
        "minimum_budget": row.minimum_budget,
        "currencies_json": row.currencies_json or [],
        "allow_budget_unknown": row.allow_budget_unknown,
        "solo_feasibility_preference": row.solo_feasibility_preference,
        "small_team_allowed": row.small_team_allowed,
        "max_delivery_months": row.max_delivery_months,
        "max_age_days": row.max_age_days,
        "created_by": row.created_by,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def _connector_metadata_for_type(connector_type: str) -> AugmisBusinessConnectorMetadata:
    if connector_type == FIXTURE_CONNECTOR_TYPE:
        return AugmisBusinessConnectorMetadata(
            connector_type=FIXTURE_CONNECTOR_TYPE,
            name=FIXTURE_CONNECTOR_NAME,
            source_category="fixture",
            description="Deterministic local fixture connector used to validate listener scans and discovery workflows.",
            capabilities=["discover", "test_connection", "validate_config"],
            configuration_schema={
                "properties": {
                    "dataset": {"type": "string", "default": "default"},
                    "include_duplicates": {"type": "boolean", "default": True},
                }
            },
            supports_scheduled_scan=False,
            supports_manual_scan=True,
            supports_incremental_scan=False,
            status="ready",
            is_test_connector=True,
        )
    if connector_type == WEB_SEARCH_CONNECTOR_TYPE:
        return AugmisBusinessConnectorMetadata(
            connector_type=WEB_SEARCH_CONNECTOR_TYPE,
            name=WEB_SEARCH_CONNECTOR_NAME,
            source_category="search",
            description="Production web-search connector for publicly available software-development and digital-transformation opportunities.",
            capabilities=["discover", "test_connection", "validate_config", "health_check"],
            configuration_schema={
                "properties": {
                    "provider": {"type": "string", "default": "tavily"},
                    "results_per_query": {"type": "integer", "default": 10},
                    "maximum_queries_per_scan": {"type": "integer", "default": 10},
                    "recency_days": {"type": "integer", "default": 30},
                    "language": {"type": "string", "default": "en"},
                    "max_candidate_results": {"type": "integer", "default": 100},
                    "max_source_fetches_per_scan": {"type": "integer", "default": 30},
                    "fetch_source_page": {"type": "boolean", "default": True},
                    "max_fetch_bytes": {"type": "integer", "default": 100000},
                    "fetch_timeout_seconds": {"type": "integer", "default": 10},
                    "max_extracted_text_chars": {"type": "integer", "default": 30000},
                    "max_redirects": {"type": "integer", "default": 3},
                }
            },
            supports_scheduled_scan=True,
            supports_manual_scan=True,
            supports_incremental_scan=False,
            status="ready",
            is_test_connector=False,
        )
    if connector_type == TED_CONNECTOR_TYPE:
        return AugmisBusinessConnectorMetadata(
            connector_type=TED_CONNECTOR_TYPE,
            name=TED_CONNECTOR_NAME,
            source_category="procurement",
            description="Official EU public procurement opportunities from Tenders Electronic Daily.",
            capabilities=["discover", "test_connection", "validate_config", "health_check"],
            configuration_schema={
                "properties": {
                    "lookback_days": {"type": "integer", "default": 7},
                    "maximum_notices_per_scan": {"type": "integer", "default": 50},
                    "notice_type_mode": {"type": "string", "default": "competition_only"},
                    "country_scope_mode": {"type": "string", "default": "search_profile"},
                    "selected_countries_json": {"type": "array", "default": []},
                    "cpv_scope": {"type": "string", "default": "broad_software_services"},
                }
            },
            supports_scheduled_scan=True,
            supports_manual_scan=True,
            supports_incremental_scan=False,
            status="ready",
            is_test_connector=False,
        )
    if connector_type == FREELANCER_CONNECTOR_TYPE:
        return AugmisBusinessConnectorMetadata(
            connector_type=FREELANCER_CONNECTOR_TYPE,
            name=FREELANCER_CONNECTOR_NAME,
            source_category="marketplace",
            description="Official Freelancer.com marketplace projects discovered through the authenticated Freelancer API.",
            capabilities=["discover", "test_connection", "validate_config", "health_check"],
            configuration_schema={
                "properties": {
                    "provider": {"type": "string", "default": "freelancer"},
                    "mode": {"type": "string", "default": "production"},
                    "lookback_hours": {"type": "integer", "default": 24},
                    "maximum_projects_per_scan": {"type": "integer", "default": 50},
                    "maximum_query_groups": {"type": "integer", "default": 5},
                    "project_type": {"type": "string", "default": "all"},
                    "project_status": {"type": "string", "default": "active"},
                    "minimum_budget": {"type": "number", "default": None},
                    "maximum_budget": {"type": "number", "default": None},
                    "maximum_existing_bids": {"type": "integer", "default": None},
                }
            },
            supports_scheduled_scan=True,
            supports_manual_scan=True,
            supports_incremental_scan=False,
            status="ready",
            is_test_connector=False,
        )
    if connector_type == REMOTEOK_CONNECTOR_TYPE:
        return AugmisBusinessConnectorMetadata(
            connector_type=REMOTEOK_CONNECTOR_TYPE,
            name=REMOTEOK_CONNECTOR_NAME,
            source_category="api",
            description="Official Remote OK public JSON feed for remote technical roles.",
            capabilities=["discover", "test_connection", "validate_config", "health_check"],
            configuration_schema={"properties": {"maximum_results": {"type": "integer", "default": 50}}},
            supports_scheduled_scan=True,
            supports_manual_scan=True,
            supports_incremental_scan=False,
            status="ready",
            is_test_connector=False,
        )
    if connector_type == ARBEITNOW_CONNECTOR_TYPE:
        return AugmisBusinessConnectorMetadata(
            connector_type=ARBEITNOW_CONNECTOR_TYPE,
            name=ARBEITNOW_CONNECTOR_NAME,
            source_category="api",
            description="Official Arbeitnow public job board API for European opportunities.",
            capabilities=["discover", "test_connection", "validate_config", "health_check"],
            configuration_schema={"properties": {"remote_only": {"type": "boolean", "default": True}, "maximum_results": {"type": "integer", "default": 50}}},
            supports_scheduled_scan=True,
            supports_manual_scan=True,
            supports_incremental_scan=False,
            status="ready",
            is_test_connector=False,
        )
    if connector_type == REMOTIVE_CONNECTOR_TYPE:
        return AugmisBusinessConnectorMetadata(
            connector_type=REMOTIVE_CONNECTOR_TYPE,
            name=REMOTIVE_CONNECTOR_NAME,
            source_category="api",
            description="Official Remotive public jobs API with provider attribution preserved.",
            capabilities=["discover", "test_connection", "validate_config", "health_check"],
            configuration_schema={"properties": {"maximum_results": {"type": "integer", "default": 50}, "search_keyword": {"type": "string", "default": ""}, "category": {"type": "string", "default": ""}}},
            supports_scheduled_scan=True,
            supports_manual_scan=True,
            supports_incremental_scan=False,
            status="ready",
            is_test_connector=False,
        )
    if connector_type == ADZUNA_CONNECTOR_TYPE:
        return AugmisBusinessConnectorMetadata(
            connector_type=ADZUNA_CONNECTOR_TYPE,
            name=ADZUNA_CONNECTOR_NAME,
            source_category="api",
            description="Official Adzuna jobs API using tenant-scoped encrypted app credentials.",
            capabilities=["discover", "test_connection", "validate_config", "health_check"],
            configuration_schema={"properties": {"maximum_results": {"type": "integer", "default": 25}, "search_keyword": {"type": "string", "default": "software developer"}, "target_countries_json": {"type": "array", "default": ["gb"]}}},
            supports_scheduled_scan=True,
            supports_manual_scan=True,
            supports_incremental_scan=False,
            status="ready",
            is_test_connector=False,
        )
    if connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE:
        return AugmisBusinessConnectorMetadata(
            connector_type=INDEPENDENT_WEB_CONNECTOR_TYPE,
            name=INDEPENDENT_WEB_CONNECTOR_NAME,
            source_category="company_source",
            description="First-party AUGMIS crawler and vertical discovery index for public commercial opportunity pages. No third-party search API is required.",
            capabilities=["discover", "validate_config", "health_check", "seed_registry", "domain_registry"],
            configuration_schema={
                "properties": {
                    "maximum_seeds_per_run": {"type": "integer", "default": 5},
                    "maximum_domains_per_run": {"type": "integer", "default": 5},
                    "maximum_pages_per_domain": {"type": "integer", "default": 25},
                    "maximum_total_pages_per_run": {"type": "integer", "default": 100},
                    "maximum_depth": {"type": "integer", "default": 2},
                    "request_timeout_seconds": {"type": "integer", "default": 15},
                    "per_domain_delay_seconds": {"type": "integer", "default": 2},
                    "recrawl_interval_hours": {"type": "integer", "default": 168},
                    "allowed_domain_mode": {"type": "string", "default": "approved_only"},
                    "max_html_response_bytes": {"type": "integer", "default": 2000000},
                    "max_extracted_text_chars": {"type": "integer", "default": 40000},
                    "maximum_links_per_page": {"type": "integer", "default": 40},
                    "maximum_run_duration_seconds": {"type": "integer", "default": 180},
                }
            },
            supports_scheduled_scan=True,
            supports_manual_scan=True,
            supports_incremental_scan=True,
            status="ready",
            is_test_connector=False,
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported connector type: {connector_type}",
    )


@dataclass
class IngestionOutcome:
    row: BusinessDevelopmentDiscoveredOpportunity | None
    outcome: str
    duplicate_of_id: str | None = None


class ConnectorRunCancelledError(Exception):
    pass


class BaseOpportunityConnector:
    metadata: AugmisBusinessConnectorMetadata
    last_run_metadata: dict[str, Any]

    def __init__(self) -> None:
        self.last_run_metadata = {}

    def validate_config(self, config: dict[str, Any]) -> None:
        return None

    def test_connection(self, config: dict[str, Any]) -> dict[str, Any]:
        self.validate_config(config)
        return {"success": True, "message": "Connector configuration is valid."}

    def discover(
        self,
        *,
        connector: BusinessDevelopmentConnector,
        search_profile: BusinessDevelopmentSearchProfile | None,
        credential: ResolvedProviderCredential | None = None,
    ) -> list[AugmisBusinessDiscoveredOpportunityCandidate]:
        raise NotImplementedError

    def health_check(self, config: dict[str, Any]) -> dict[str, Any]:
        return self.test_connection(config)


class FixtureOpportunityConnector(BaseOpportunityConnector):
    metadata = _connector_metadata_for_type(FIXTURE_CONNECTOR_TYPE)

    def discover(
        self,
        *,
        connector: BusinessDevelopmentConnector,
        search_profile: BusinessDevelopmentSearchProfile | None,
        credential: ResolvedProviderCredential | None = None,
    ) -> list[AugmisBusinessDiscoveredOpportunityCandidate]:
        del credential
        now = _now()
        include_duplicates = bool((connector.configuration_json or {}).get("include_duplicates", True))
        records = [
            AugmisBusinessDiscoveredOpportunityCandidate(
                external_id="FIX-001",
                source_type="fixture",
                source_name=CONNECTOR_TEST_LABEL,
                source_url="https://fixture.example/opportunities/workflow-modernisation",
                source_country="Saudi Arabia",
                title="Workflow Modernisation and Field Operations Dashboard",
                organization_name="Acme Utilities",
                published_date=now - timedelta(days=2),
                closing_date=now + timedelta(days=18),
                country="Saudi Arabia",
                region="Middle East",
                industry="Utilities",
                requirement_summary="Build a workflow application and executive dashboard for field operations and approvals.",
                raw_summary="Seeking a custom application for workflow modernisation, approvals, field inspections, and reporting dashboards.",
                raw_text="Custom application, workflow approvals, reporting dashboard, inspection management, records tracking.",
                budget_min=90000,
                budget_max=140000,
                currency="USD",
                evidence=[{"type": "fixture", "label": "Seeded fixture"}],
                source_metadata={"fixture": True, "dataset": "default"},
                raw_content_json={"fixture": True, "source_payload_version": 1},
                retrieval_timestamp=now,
            ),
            AugmisBusinessDiscoveredOpportunityCandidate(
                external_id="FIX-002",
                source_type="fixture",
                source_name=CONNECTOR_TEST_LABEL,
                source_url="https://fixture.example/opportunities/records-portal",
                source_country="Kenya",
                title="Document and Records Portal for Inspection Readiness",
                organization_name="Nile Logistics Authority",
                published_date=now - timedelta(days=4),
                closing_date=now + timedelta(days=24),
                country="Kenya",
                region="Africa",
                industry="Logistics",
                requirement_summary="Portal, forms, records management, and reporting for inspection readiness.",
                raw_summary="Request for a document portal with forms, records retention, reporting, and workflow routing.",
                raw_text="records management, document portal, workflow routing, reporting, approval forms",
                budget_min=60000,
                budget_max=110000,
                currency="USD",
                evidence=[{"type": "fixture", "label": "Seeded fixture"}],
                source_metadata={"fixture": True, "dataset": "default"},
                raw_content_json={"fixture": True, "source_payload_version": 1},
                retrieval_timestamp=now,
            ),
        ]
        if include_duplicates:
            records.append(
                AugmisBusinessDiscoveredOpportunityCandidate(
                    external_id="FIX-001-DUP",
                    source_type="fixture",
                    source_name=CONNECTOR_TEST_LABEL,
                    source_url="https://fixture.example/opportunities/workflow-modernisation",
                    source_country="Saudi Arabia",
                    title="Workflow Modernisation and Field Operations Dashboard",
                    organization_name="Acme Utilities",
                    published_date=now - timedelta(days=2),
                    closing_date=now + timedelta(days=18),
                    country="Saudi Arabia",
                    region="Middle East",
                    industry="Utilities",
                    requirement_summary="Duplicate seeded fixture to validate deterministic deduplication.",
                    raw_summary="Duplicate seeded fixture to validate deterministic deduplication.",
                    raw_text="workflow approvals, dashboard, duplicate seeded fixture",
                    budget_min=90000,
                    budget_max=140000,
                    currency="USD",
                    evidence=[{"type": "fixture", "label": "Duplicate seeded fixture"}],
                    source_metadata={"fixture": True, "dataset": "default", "duplicate": True},
                    raw_content_json={"fixture": True, "source_payload_version": 1, "duplicate": True},
                    retrieval_timestamp=now,
                )
            )
        return records


def _freelancer_mock_fixture_candidates() -> list[AugmisBusinessDiscoveredOpportunityCandidate]:
    now = _now()
    client = FreelancerClient(access_token="mock-token")
    candidates: list[AugmisBusinessDiscoveredOpportunityCandidate] = []
    for payload in freelancer_mock_projects():
        project = client._normalize_project(payload)
        project_url = _freelancer_project_url(project.raw_project, project.project_id, project.seo_url)
        requirement_summary = (project.description or project.title)[:4000]
        candidates.append(
            AugmisBusinessDiscoveredOpportunityCandidate(
                external_id=project.project_id,
                source_type="marketplace_project",
                source_name="Freelancer - Mock",
                source_url=project_url,
                source_country=project.client_country,
                title=project.title,
                organization_name=project.client_username or "Marketplace Client",
                published_date=project.posted_at,
                closing_date=project.bid_end_at,
                country=project.client_country,
                region=project.client_location,
                industry="Freelance Marketplace",
                requirement_summary=requirement_summary,
                raw_summary=(project.description or project.title)[:1000],
                raw_text=" ".join(
                    part
                    for part in [project.title, project.description or "", " ".join(project.skills), " ".join(project.categories)]
                    if part
                )[:20000],
                budget_min=project.budget_min,
                budget_max=project.budget_max,
                currency=project.currency_code,
                evidence=[
                    {"type": "fixture", "provider": "freelancer", "fixture_version": FREELANCER_MOCK_FIXTURE_VERSION},
                    {"type": "project_id", "project_id": project.project_id},
                ],
                source_metadata={
                    "provider": "freelancer",
                    "provider_project_id": project.project_id,
                    "opportunity_class": "freelance_marketplace",
                    "project_type": project.project_type,
                    "project_status": project.status,
                    "skills": project.skills,
                    "categories": project.categories,
                    "bid_count": project.bid_count,
                    "client_country": project.client_country,
                    "client_location": project.client_location,
                    "client_rating": project.client_rating,
                    "client_review_count": project.client_review_count,
                    "client_payment_verified": project.client_payment_verified,
                    "client_projects_posted": project.client_projects_posted,
                    "client_projects_completed": project.client_projects_completed,
                    "source_trust": "mock_fixture",
                    "fixture_mode": True,
                    "fixture_version": FREELANCER_MOCK_FIXTURE_VERSION,
                },
                raw_content_json={
                    "provider": "freelancer",
                    "provider_project_id": project.project_id,
                    "provider_version": FREELANCER_API_VERSION,
                    "fixture_mode": True,
                    "fixture_version": FREELANCER_MOCK_FIXTURE_VERSION,
                    "project_url": project_url,
                    "project_type": project.project_type,
                    "project_status": project.status,
                    "skills": project.skills,
                    "categories": project.categories,
                    "bid_count": project.bid_count,
                    "bid_avg": project.bid_avg,
                    "client_country": project.client_country,
                    "client_location": project.client_location,
                    "client_rating": project.client_rating,
                    "client_review_count": project.client_review_count,
                    "client_payment_verified": project.client_payment_verified,
                    "client_projects_posted": project.client_projects_posted,
                    "client_projects_completed": project.client_projects_completed,
                    "client_username": project.client_username,
                    "source_trust": "mock_fixture",
                    "provider_result": project.raw_project,
                },
                retrieval_timestamp=now,
            )
        )
    return candidates


def _classify_source_trust(domain: str | None) -> str:
    if not domain:
        return "unknown"
    lowered = domain.lower()
    if lowered.endswith(".gov") or lowered.endswith(".gov.uk") or lowered.endswith(".gob") or lowered.endswith(".go.ke"):
        return "government"
    if any(token in lowered for token in ("tender", "procurement", "rfp", "rfq")):
        return "procurement_portal"
    if any(token in lowered for token in ("news", "media", "press")):
        return "news_media"
    return "organization_website"


def _commercial_signal_summary(text: str) -> tuple[bool, list[str], list[str]]:
    lowered = text.lower()
    positive = [term for term in BUYING_INTENT_TERMS if term in lowered]
    negative = [term for term in JOB_TERMS + NEWS_TERMS if term in lowered]
    if negative and not positive:
        return False, positive, negative
    return bool(positive or "software" in lowered or "application" in lowered), positive, negative


def _bounded_int(
    config: dict[str, Any],
    key: str,
    default: int,
    minimum: int,
    maximum: int,
    label: str,
) -> int:
    try:
        value = int(config.get(key, default) or default)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{label} must be between {minimum} and {maximum}") from exc
    if value < minimum or value > maximum:
        raise HTTPException(status_code=400, detail=f"{label} must be between {minimum} and {maximum}")
    return value


def _effective_web_search_runtime_policy(config: dict[str, Any]) -> WebFetchRuntimePolicy:
    defaults = default_web_fetch_runtime_policy()
    _bounded_int(config, "results_per_query", 10, 1, 20, "results_per_query")
    _bounded_int(config, "maximum_queries_per_scan", 10, 1, 20, "maximum_queries_per_scan")
    _bounded_int(config, "max_candidate_results", 100, 1, 200, "max_candidate_results")
    _bounded_int(
        config,
        "max_source_fetches_per_scan",
        30,
        WEB_SEARCH_MAX_SOURCE_FETCHES_MIN,
        WEB_SEARCH_MAX_SOURCE_FETCHES_MAX,
        "max_source_fetches_per_scan",
    )
    return WebFetchRuntimePolicy(
        fetch_source_page=bool(config.get("fetch_source_page", True)),
        max_fetch_bytes=_bounded_int(
            config,
            "max_fetch_bytes",
            defaults.max_fetch_bytes,
            WEB_SEARCH_FETCH_MAX_BYTES_MIN,
            WEB_SEARCH_FETCH_MAX_BYTES_MAX,
            "max_fetch_bytes",
        ),
        fetch_timeout_seconds=_bounded_int(
            config,
            "fetch_timeout_seconds",
            defaults.fetch_timeout_seconds,
            WEB_SEARCH_FETCH_TIMEOUT_MIN,
            WEB_SEARCH_FETCH_TIMEOUT_MAX,
            "fetch_timeout_seconds",
        ),
        max_extracted_text_chars=_bounded_int(
            config,
            "max_extracted_text_chars",
            defaults.max_extracted_text_chars,
            WEB_SEARCH_EXTRACTED_TEXT_MIN,
            WEB_SEARCH_EXTRACTED_TEXT_MAX,
            "max_extracted_text_chars",
        ),
        max_redirects=_bounded_int(
            config,
            "max_redirects",
            defaults.max_redirects,
            WEB_SEARCH_REDIRECTS_MIN,
            WEB_SEARCH_REDIRECTS_MAX,
            "max_redirects",
        ),
    )


def _effective_max_source_fetches_per_scan(config: dict[str, Any]) -> int:
    return _bounded_int(
        config,
        "max_source_fetches_per_scan",
        30,
        WEB_SEARCH_MAX_SOURCE_FETCHES_MIN,
        WEB_SEARCH_MAX_SOURCE_FETCHES_MAX,
        "max_source_fetches_per_scan",
    )


def _classify_fetch_error_code(message: str | None) -> str | None:
    if not message:
        return None
    lowered = message.lower()
    if "configured fetch limit" in lowered:
        return "max_bytes_exceeded"
    if "timed out" in lowered:
        return "timeout"
    if "maximum redirects" in lowered:
        return "max_redirects_exceeded"
    if "unsupported source content type" in lowered:
        return "unsupported_content_type"
    if "private or local network" in lowered or "localhost" in lowered:
        return "blocked_target"
    return "fetch_failed"


class WebOpportunitySearchConnector(BaseOpportunityConnector):
    metadata = _connector_metadata_for_type(WEB_SEARCH_CONNECTOR_TYPE)

    def __init__(self) -> None:
        super().__init__()

    def validate_config(self, config: dict[str, Any]) -> None:
        _effective_web_search_runtime_policy(config)

    def discover(
        self,
        *,
        connector: BusinessDevelopmentConnector,
        search_profile: BusinessDevelopmentSearchProfile | None,
        credential: ResolvedProviderCredential | None = None,
    ) -> list[AugmisBusinessDiscoveredOpportunityCandidate]:
        configuration = connector.configuration_json or {}
        self.validate_config(configuration)
        provider_name = str(configuration.get("provider", "tavily") or "tavily").strip().lower()
        if not credential or not credential.api_key:
            raise HTTPException(status_code=400, detail=f"{provider_name.title()} API key is not configured.")
        session = object_session(connector)
        if session is None:
            raise HTTPException(status_code=500, detail="Connector session is unavailable.")
        provider_row = resolve_search_provider_by_code(db=session, tenant_id=connector.tenant_id, provider_code=provider_name)
        provider = get_web_search_provider(
            provider_name,
            api_key=credential.api_key,
            provider_type=provider_row.provider_type,
            configuration=provider_row.configuration_json or {},
            adapter_code=provider_row.adapter_code,
        )
        profile_payload = _serialize_search_profile(search_profile) if search_profile else {}
        maximum_queries = int(configuration.get("maximum_queries_per_scan", 10) or 10)
        results_per_query = int(configuration.get("results_per_query", 10) or 10)
        max_candidate_results = int(configuration.get("max_candidate_results", 100) or 100)
        max_source_fetches_per_scan = _effective_max_source_fetches_per_scan(configuration)
        recency_days = int(configuration.get("recency_days", 30) or 30)
        language = str(configuration.get("language", "en") or "en").strip().lower()
        runtime_policy = _effective_web_search_runtime_policy(configuration)
        countries = profile_payload.get("target_countries_json") or []
        selected_country = countries[0] if countries else None
        queries = build_web_search_queries(profile=profile_payload, maximum_queries=maximum_queries)

        aggregated: dict[str, dict[str, Any]] = {}
        api_result_count = 0
        fetch_count = 0
        fetch_attempted_count = 0
        fetch_failures = 0
        fetch_skipped_due_limit = 0
        accepted_count = 0
        filtered_count = 0
        provider_usage: dict[str, Any] = {}

        for query in queries:
            provider_response = provider.search(
                query=query,
                count=results_per_query,
                country=selected_country,
                language=language,
                freshness_days=recency_days,
                exclude_domains=list(profile_payload.get("excluded_domains_json") or []),
            )
            api_result_count += provider_response["raw_count"]
            if isinstance(provider_response.get("usage"), dict):
                provider_usage = provider_response["usage"]
            for result in provider_response["results"]:
                canonical_url, source_domain = _normalize_url(result.url)
                key = canonical_url or result.url
                existing = aggregated.get(key)
                query_matches = list((existing or {}).get("queries_matched") or [])
                if query not in query_matches:
                    query_matches.append(query)
                rank = min(result.rank, int((existing or {}).get("best_rank") or result.rank))
                aggregated[key] = {
                    "result": result,
                    "canonical_url": canonical_url or result.url,
                    "source_domain": source_domain or result.source_domain,
                    "queries_matched": query_matches,
                    "best_rank": rank,
                    "snippet": result.snippet,
                }

        candidates: list[AugmisBusinessDiscoveredOpportunityCandidate] = []
        excluded_domains = {item.lower() for item in (profile_payload.get("excluded_domains_json") or [])}
        for item in sorted(aggregated.values(), key=lambda entry: (entry["best_rank"], entry["canonical_url"])):
            if len(candidates) >= max_candidate_results:
                break
            result = item["result"]
            domain = item["source_domain"]
            if domain and any(domain == blocked or domain.endswith(f".{blocked}") for blocked in excluded_domains):
                filtered_count += 1
                continue

            snippet = result.snippet or ""
            accepted, positive_terms, negative_terms = _commercial_signal_summary(
                " ".join(part for part in [result.title, snippet] if part)
            )
            if not accepted:
                filtered_count += 1
                continue

            source_body = None
            fetch_error = None
            fetch_error_code = None
            fetch_url = item["canonical_url"]
            extracted_text = snippet
            if runtime_policy.fetch_source_page:
                if fetch_attempted_count >= max_source_fetches_per_scan:
                    fetch_skipped_due_limit += 1
                    fetch_error_code = "source_fetch_limit_reached"
                    fetch_error = "Source retrieval was skipped because this scan reached the configured source-fetch limit."
                else:
                    fetch_attempted_count += 1
                    try:
                        fetched = fetch_public_webpage(fetch_url, policy=runtime_policy)
                        fetch_count += 1
                        source_body = str(fetched["body"] or "")
                        extracted_text = extract_text_from_webpage(
                            source_body,
                            max_chars=runtime_policy.max_extracted_text_chars,
                        )
                    except SafeWebFetchError as exc:
                        fetch_failures += 1
                        fetch_error = str(exc)
                        fetch_error_code = _classify_fetch_error_code(fetch_error)

            full_text = " ".join(part for part in [result.title, snippet, extracted_text] if part)
            accepted, positive_terms, negative_terms = _commercial_signal_summary(full_text)
            if not accepted:
                filtered_count += 1
                continue

            evidence = [
                {
                    "type": "search_result",
                    "provider": provider.name,
                    "query": query_text,
                    "rank": index + 1,
                    "snippet": snippet,
                    "score": result.provider_metadata.get("score"),
                }
                for index, query_text in enumerate(item["queries_matched"])
            ]
            if source_body and extracted_text:
                evidence.append(
                    {
                        "type": "fetched_source_excerpt",
                        "provider": provider.name,
                        "text": extracted_text[:1200],
                    }
                )

            candidate = AugmisBusinessDiscoveredOpportunityCandidate(
                external_id=f"{provider.name}:{sha256(fetch_url.encode('utf-8')).hexdigest()[:24]}",
                source_type="web_search",
                source_name=WEB_SEARCH_CONNECTOR_NAME,
                source_url=fetch_url,
                source_country=selected_country,
                title=result.title,
                organization_name=None,
                published_date=None,
                closing_date=None,
                country=selected_country,
                region=(profile_payload.get("target_regions_json") or [None])[0],
                industry=(profile_payload.get("target_industries_json") or [None])[0],
                requirement_summary=snippet or extracted_text[:800] if extracted_text else snippet,
                raw_summary=snippet,
                raw_text=extracted_text[:20000] if extracted_text else snippet,
                budget_min=None,
                budget_max=None,
                currency=None,
                evidence=evidence,
                source_metadata={
                    "provider": provider.name,
                    "queries_matched": item["queries_matched"],
                    "best_rank": item["best_rank"],
                    "search_snippet": snippet,
                    "fetched_source_available": bool(source_body),
                    "positive_terms": positive_terms,
                    "negative_terms": negative_terms,
                    "source_trust": _classify_source_trust(domain),
                    "fetch_error": fetch_error,
                    "fetch_error_code": fetch_error_code,
                    "partial_source_retrieval": bool(fetch_error and not source_body),
                },
                raw_content_json={
                    "provider_result": result.provider_metadata,
                    "provider": provider.name,
                    "queries_matched": item["queries_matched"],
                    "best_rank": item["best_rank"],
                    "source_trust": _classify_source_trust(domain),
                    "positive_terms": positive_terms,
                    "negative_terms": negative_terms,
                    "fetch_error": fetch_error,
                    "fetch_error_code": fetch_error_code,
                    "partial_source_retrieval": bool(fetch_error and not source_body),
                    "fetched_source_available": bool(source_body),
                    "search_result_title": result.title,
                    "search_result_snippet": snippet,
                    "fetched_source_html": source_body[:10000] if source_body else None,
                    "fetched_source_text": extracted_text[: runtime_policy.max_extracted_text_chars] if extracted_text and source_body else None,
                },
                retrieval_timestamp=_now(),
            )
            candidates.append(candidate)
            accepted_count += 1

        self.last_run_metadata = {
            "provider": provider.name,
            "queries_executed": queries,
            "query_count": len(queries),
            "api_call_count": len(queries),
            "api_result_count": api_result_count,
            "provider_usage": provider_usage,
            "same_scan_unique_sources": len(aggregated),
            "fetch_source_page": runtime_policy.fetch_source_page,
            "source_pages_fetched": fetch_count,
            "source_pages_attempted": fetch_attempted_count,
            "source_pages_skipped_due_limit": fetch_skipped_due_limit,
            "fetch_failures": fetch_failures,
            "accepted_candidates": accepted_count,
            "filtered_candidates": filtered_count,
            "max_candidate_results": max_candidate_results,
            "results_per_query": results_per_query,
            "recency_days": recency_days,
            "maximum_queries_per_scan": maximum_queries,
            "max_source_fetches_per_scan": max_source_fetches_per_scan,
            "max_fetch_bytes": runtime_policy.max_fetch_bytes,
            "fetch_timeout_seconds": runtime_policy.fetch_timeout_seconds,
            "max_extracted_text_chars": runtime_policy.max_extracted_text_chars,
            "max_redirects": runtime_policy.max_redirects,
        }
        return candidates


TED_LOOKBACK_OPTIONS = {1, 3, 7, 14, 30}
TED_MAX_NOTICE_OPTIONS = {25, 50, 100, 200}
TED_NOTICE_TYPE_OPTIONS = set(TED_NOTICE_TYPE_PRESETS.keys())
TED_COUNTRY_SCOPE_OPTIONS = {"search_profile", "eu_eea", "selected"}
TED_CPV_SCOPE_OPTIONS = {"broad_software_services"}


def _extract_ted_notice_version(value: str | None) -> int | None:
    if not value:
        return None
    digits = "".join(character for character in value if character.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _ted_notice_country(notice: TedNotice) -> str | None:
    if notice.place_of_performance:
        return notice.place_of_performance[0]
    return notice.buyer_country


def _ted_notice_summary(notice: TedNotice) -> str:
    parts = [notice.summary, notice.lot_summary]
    joined = " ".join(part.strip() for part in parts if part and part.strip())
    return joined or notice.title


def _ted_error_summary(exc: TedApiError) -> str:
    return exc.user_message or "TED rejected the search request."


def _ted_notice_dedupe_key(notice: TedNotice) -> str:
    return notice.stable_identifier or notice.official_notice_url or notice.title.strip().lower()


class TedProcurementConnector(BaseOpportunityConnector):
    metadata = _connector_metadata_for_type(TED_CONNECTOR_TYPE)

    def __init__(self, *, client: TedSearchClient | None = None) -> None:
        super().__init__()
        self.client = client or TedSearchClient()

    def validate_config(self, config: dict[str, Any]) -> None:
        lookback_days = int(config.get("lookback_days", 7) or 7)
        maximum_notices = int(config.get("maximum_notices_per_scan", 50) or 50)
        notice_type_mode = str(config.get("notice_type_mode", "competition_only") or "competition_only").strip().lower()
        country_scope_mode = str(config.get("country_scope_mode", "search_profile") or "search_profile").strip().lower()
        cpv_scope = str(config.get("cpv_scope", "broad_software_services") or "broad_software_services").strip().lower()
        if lookback_days not in TED_LOOKBACK_OPTIONS:
            raise HTTPException(status_code=400, detail="lookback_days must be one of 1, 3, 7, 14, or 30")
        if maximum_notices not in TED_MAX_NOTICE_OPTIONS:
            raise HTTPException(status_code=400, detail="maximum_notices_per_scan must be one of 25, 50, 100, or 200")
        if notice_type_mode not in TED_NOTICE_TYPE_OPTIONS:
            raise HTTPException(status_code=400, detail="notice_type_mode is invalid")
        if country_scope_mode not in TED_COUNTRY_SCOPE_OPTIONS:
            raise HTTPException(status_code=400, detail="country_scope_mode is invalid")
        if cpv_scope not in TED_CPV_SCOPE_OPTIONS:
            raise HTTPException(status_code=400, detail="cpv_scope is invalid")

    def test_connection(self, config: dict[str, Any]) -> dict[str, Any]:
        self.validate_config(config)
        today = _now()
        queries = [
            f"publication-date = ({today.strftime('%Y%m%d')} <> {today.strftime('%Y%m%d')})",
            f"publication-date = ({today.strftime('%Y%m%d')} <> {today.strftime('%Y%m%d')}) AND FT ~ (software)",
        ]
        last_error = None
        result = None
        for query in queries:
            try:
                result = self.client.search_notices(query=query, page=1, limit=1)
                last_error = None
                break
            except TedApiError as exc:
                last_error = _ted_error_summary(exc)
        if result is None:
            return {"success": False, "message": last_error or "TED query was rejected."}
        return {
            "success": True,
            "message": f"TED API reachable. Parsed {len(result['items'])} notice(s) from a bounded test request.",
        }

    def discover(
        self,
        *,
        connector: BusinessDevelopmentConnector,
        search_profile: BusinessDevelopmentSearchProfile | None,
        credential: ResolvedProviderCredential | None = None,
    ) -> list[AugmisBusinessDiscoveredOpportunityCandidate]:
        del credential
        configuration = connector.configuration_json or {}
        self.validate_config(configuration)
        profile_payload = _serialize_search_profile(search_profile) if search_profile else {}
        query_specs = build_ted_search_query_specs(
            profile=profile_payload,
            configuration=configuration,
            now=_now(),
        )
        maximum_notices = int(configuration.get("maximum_notices_per_scan", 50) or 50)

        notices: list[TedNotice] = []
        invalid_items = 0
        api_calls = 0
        raw_results_fetched = 0
        selected_query = None
        executed_queries: list[str] = []
        query_diagnostics: list[dict[str, Any]] = []
        last_exception: TedApiError | None = None
        per_query_limit = max(5, ceil(maximum_notices / max(len(query_specs), 1)))
        for query_spec in query_specs:
            try:
                local_notices: list[TedNotice] = []
                local_invalid = 0
                local_raw_results = 0
                remaining = per_query_limit
                page = 1
                while remaining > 0:
                    page_size = min(25, remaining)
                    result = self.client.search_notices(query=query_spec.query, page=page, limit=page_size)
                    api_calls += 1
                    batch_items = list(result["items"])
                    local_notices.extend(batch_items)
                    local_invalid += int(result["invalid_items"] or 0)
                    local_raw_results += len(batch_items)
                    remaining -= len(batch_items)
                    if not batch_items or len(batch_items) < page_size:
                        break
                    page += 1
                if local_notices and selected_query is None:
                    selected_query = query_spec.query
                executed_queries.append(query_spec.query)
                raw_results_fetched += local_raw_results
                notices.extend(local_notices)
                invalid_items += local_invalid
                query_diagnostics.append(
                    {
                        "key": query_spec.key,
                        "label": query_spec.label,
                        "query": query_spec.query,
                        "primary_term": query_spec.primary_term,
                        "cpv_codes": list(query_spec.cpv_codes),
                        "raw_results": local_raw_results,
                        "normalized": len(local_notices),
                        "invalid_items": local_invalid,
                    }
                )
                if len(notices) >= maximum_notices:
                    notices = notices[:maximum_notices]
                    break
            except TedApiError as exc:
                last_exception = exc
                query_diagnostics.append(
                    {
                        "key": query_spec.key,
                        "label": query_spec.label,
                        "query": query_spec.query,
                        "primary_term": query_spec.primary_term,
                        "cpv_codes": list(query_spec.cpv_codes),
                        "error": _ted_error_summary(exc),
                    }
                )
        if not executed_queries:
            if last_exception is not None:
                raise last_exception
            raise TedApiError("TED query was rejected.")

        deduped_notices: list[TedNotice] = []
        seen_notice_keys: set[str] = set()
        for notice in notices:
            dedupe_key = _ted_notice_dedupe_key(notice)
            if dedupe_key in seen_notice_keys:
                continue
            seen_notice_keys.add(dedupe_key)
            deduped_notices.append(notice)

        candidates: list[AugmisBusinessDiscoveredOpportunityCandidate] = []
        notices_with_deadline = 0
        notices_with_buyer = 0
        notices_with_value = 0
        for notice in deduped_notices[:maximum_notices]:
            country = _ted_notice_country(notice)
            summary = _ted_notice_summary(notice)
            cpv_text = ", ".join(notice.cpv_codes)
            if notice.deadline:
                notices_with_deadline += 1
            if notice.buyer_name:
                notices_with_buyer += 1
            if notice.estimated_value is not None:
                notices_with_value += 1
            evidence = [
                {"type": "ted_notice", "publication_number": notice.publication_number},
                {"type": "ted_notice_identifier", "identifier": notice.notice_identifier},
                {"type": "ted_buyer", "buyer": notice.buyer_name or "Not available"},
                {"type": "ted_deadline", "deadline": notice.deadline.isoformat() if notice.deadline else None},
                {"type": "ted_cpv", "cpv_codes": notice.cpv_codes},
                {"type": "ted_notice_type", "notice_type": notice.notice_type},
                {"type": "ted_procedure_type", "procedure_type": notice.procedure_type},
                {"type": "ted_value", "estimated_value": notice.estimated_value, "currency": notice.estimated_currency},
                {"type": "ted_url", "url": notice.official_notice_url},
            ]
            candidate = AugmisBusinessDiscoveredOpportunityCandidate(
                external_id=notice.stable_identifier or notice.official_notice_url or notice.title,
                source_type="public_procurement",
                source_name="TED",
                source_url=notice.official_notice_url,
                source_country=notice.buyer_country,
                title=notice.title,
                organization_name=notice.buyer_name,
                published_date=notice.publication_date,
                closing_date=notice.deadline,
                country=country,
                region=None,
                industry="Public Procurement",
                requirement_summary=summary[:2000],
                raw_summary=summary[:1000],
                raw_text=" ".join(
                    part
                    for part in [
                        notice.title,
                        summary,
                        notice.buyer_name or "",
                        notice.notice_type or "",
                        notice.procedure_type or "",
                        notice.contract_nature or "",
                        cpv_text,
                    ]
                    if part
                )[:20000],
                budget_min=notice.estimated_value,
                budget_max=notice.estimated_value,
                currency=notice.estimated_currency,
                evidence=evidence,
                source_metadata={
                    "provider": "ted",
                    "source_trust": "official_procurement_api",
                    "publication_number": notice.publication_number,
                    "notice_identifier": notice.notice_identifier,
                    "notice_version": notice.notice_version,
                    "notice_type": notice.notice_type,
                    "procedure_type": notice.procedure_type,
                    "contract_nature": notice.contract_nature,
                    "cpv_codes": notice.cpv_codes,
                    "official_language": notice.official_language,
                    "buyer_country": notice.buyer_country,
                    "place_of_performance": notice.place_of_performance,
                    "estimated_value": notice.estimated_value,
                    "estimated_currency": notice.estimated_currency,
                },
                raw_content_json={
                    "provider": "ted",
                    "ted_notice": notice.raw_notice,
                    "publication_number": notice.publication_number,
                    "notice_identifier": notice.notice_identifier,
                    "notice_version": notice.notice_version,
                    "notice_type": notice.notice_type,
                    "procedure_type": notice.procedure_type,
                    "contract_nature": notice.contract_nature,
                    "cpv_codes": notice.cpv_codes,
                    "official_language": notice.official_language,
                    "buyer_country": notice.buyer_country,
                    "place_of_performance": notice.place_of_performance,
                    "estimated_value": notice.estimated_value,
                    "estimated_currency": notice.estimated_currency,
                    "ted_summary": summary,
                    "source_trust": "official_procurement_api",
                },
                retrieval_timestamp=_now(),
            )
            candidates.append(candidate)

        self.last_run_metadata = {
            "provider": "TED",
            "queries_executed": executed_queries,
            "query_count": len(executed_queries),
            "api_call_count": api_calls,
            "api_result_count": raw_results_fetched,
            "raw_results_fetched": raw_results_fetched,
            "accepted_candidates": len(candidates),
            "filtered_candidates": 0,
            "same_scan_unique_sources": len({candidate.external_id for candidate in candidates if candidate.external_id}),
            "notices_received": len(deduped_notices),
            "notices_normalized": len(candidates),
            "invalid": invalid_items,
            "notices_with_deadline": notices_with_deadline,
            "notices_with_buyer": notices_with_buyer,
            "notices_with_value": notices_with_value,
            "query_text": selected_query,
            "query_diagnostics": query_diagnostics,
            "result_fields": list(TED_SEARCH_RESULT_FIELDS),
            "query_variants_attempted": len(query_specs),
            "lookback_days": configuration.get("lookback_days", 7),
            "maximum_notices_per_scan": maximum_notices,
            "country_scope_codes": ted_country_scope_codes(profile=profile_payload, configuration=configuration),
            "cpv_codes": [item["code"] for item in TED_SOFTWARE_SERVICE_CPV_MAP],
        }
        return candidates


FREELANCER_LOOKBACK_OPTIONS = {6, 12, 24, 72, 168, 336, 720}
FREELANCER_MAX_PROJECT_OPTIONS = {10, 25, 50, 100, 200}
FREELANCER_PROJECT_TYPE_OPTIONS = {"all", "fixed", "hourly"}
FREELANCER_PROJECT_STATUS_OPTIONS = {"active"}


def _freelancer_project_url(project: dict[str, Any], project_id: str, seo_url: str | None) -> str:
    if seo_url:
        if URL_SCHEME_PATTERN.match(seo_url):
            return seo_url
        return f"https://www.freelancer.com{seo_url if seo_url.startswith('/') else f'/{seo_url}'}"
    return f"https://www.freelancer.com/projects/{project_id}"


def _freelancer_budget_label(candidate: AugmisBusinessDiscoveredOpportunityCandidate) -> str | None:
    if candidate.budget_min is None and candidate.budget_max is None:
        return None
    currency = candidate.currency or ""
    if candidate.budget_min is not None and candidate.budget_max is not None:
        return f"{candidate.budget_min:.0f} - {candidate.budget_max:.0f} {currency}".strip()
    value = candidate.budget_max if candidate.budget_max is not None else candidate.budget_min
    return f"{value:.0f} {currency}".strip() if value is not None else None


def _freelancer_client_quality_points(raw: dict[str, Any], reasons: list[str]) -> float:
    score = 5.0
    if raw.get("client_payment_verified") is True:
        score += 2.0
        reasons.append("Matched signal: Client payment is verified.")
    rating = raw.get("client_rating")
    if isinstance(rating, (int, float)) and rating >= 4.0:
        score += 2.0
        reasons.append("Matched signal: Client hiring reputation appears healthy.")
    reviews = raw.get("client_review_count")
    if isinstance(reviews, (int, float)) and reviews >= 10:
        score += 1.0
        reasons.append("Matched signal: Client has prior marketplace review history.")
    return min(10.0, score)


def _freelancer_freshness_points(candidate: AugmisBusinessDiscoveredOpportunityCandidate, reasons: list[str]) -> float:
    if not candidate.published_date:
        return 5.0
    age = _now() - candidate.published_date
    hours = age.total_seconds() / 3600
    if hours <= 6:
        reasons.append("Matched signal: Project was posted within the last 6 hours.")
        return 10.0
    if hours <= 24:
        reasons.append("Matched signal: Project was posted within the last 24 hours.")
        return 8.0
    if hours <= 72:
        reasons.append("Matched signal: Project is still fresh within the last 3 days.")
        return 6.0
    return 3.0


def _calculate_freelancer_preliminary_relevance(
    candidate: AugmisBusinessDiscoveredOpportunityCandidate,
    profile: BusinessDevelopmentSearchProfile | None,
) -> tuple[float, list[str], list[str]]:
    searchable = _searchable_text(candidate)
    raw = candidate.raw_content_json or candidate.source_metadata or {}
    skills = [str(item).strip() for item in raw.get("skills", []) if str(item).strip()] if isinstance(raw.get("skills"), list) else []
    categories = [str(item).strip() for item in raw.get("categories", []) if str(item).strip()] if isinstance(raw.get("categories"), list) else []
    include_terms: set[str] = set()
    exclude_terms: set[str] = set()
    if profile:
        include_terms.update(_normalize_text(item) for item in (profile.include_keywords_json or []) if _normalize_text(item))
        include_terms.update(_normalize_text(item) for item in (profile.include_technologies_json or []) if _normalize_text(item))
        include_terms.update(_normalize_text(item) for item in (profile.include_capabilities_json or []) if _normalize_text(item))
        exclude_terms.update(_normalize_text(item) for item in (profile.exclude_keywords_json or []) if _normalize_text(item))
    skill_matches = sorted({skill for skill in skills if (_normalize_text(skill) or "") in include_terms})
    term_matches = sorted({term for term in include_terms if term and term in searchable})
    matched_terms = list(dict.fromkeys(skill_matches + term_matches))
    reasons: list[str] = []
    score = 0.0
    software_skill_terms = {
        "python",
        "react.js",
        "next.js",
        "fastapi",
        "postgresql",
        "api",
        "automation",
        "artificial intelligence",
        "machine learning",
        "web development",
    }
    generic_skill_matches = sorted(
        {
            skill
            for skill in skills
            if (_normalize_text(skill) or "") in software_skill_terms
        }
    )

    tech_points = min(30.0, len(matched_terms) * 6.0)
    if tech_points:
        score += tech_points
        reasons.append(f"Matched signal: {len(matched_terms)} technology or capability terms align with the search profile.")
    elif generic_skill_matches:
        fallback_skill_points = min(24.0, len(generic_skill_matches) * 6.0)
        score += fallback_skill_points
        reasons.append("Matched signal: Project skills align with AUGMIS software-delivery capabilities.")

    domain_terms = (
        "document management",
        "records management",
        "workflow",
        "dashboard",
        "analytics",
        "ai",
        "automation",
        "integration",
        "compliance",
        "inspection",
        "portal",
        "case management",
        "custom software",
        "digital transformation",
    )
    domain_hits = [term for term in domain_terms if _contains_any_phrase(searchable, (term,))]
    if domain_hits:
        score += min(25.0, len(domain_hits) * 5.0)
        reasons.append("Matched signal: Requirement language fits AUGMIS software-delivery focus areas.")
    elif generic_skill_matches:
        score += 8.0
        reasons.append("Matched signal: Technical skills suggest a custom software or integration delivery project.")
    if len(generic_skill_matches) >= 3 and len(domain_hits) >= 2:
        score += 10.0
        reasons.append("Matched signal: Strong alignment across software stack and AUGMIS delivery domains.")

    if profile and profile.minimum_budget is not None:
        if candidate.budget_max is not None and candidate.budget_max >= profile.minimum_budget:
            score += 15.0
            reasons.append("Matched signal: Published budget meets the active minimum threshold.")
        elif candidate.budget_max is None and profile.allow_budget_unknown:
            score += 8.0
            reasons.append("Matched signal: Budget is unknown but the profile allows unknown budgets.")
        else:
            score += 2.0
            reasons.append("Negative signal: Published budget appears below the active threshold.")
    else:
        score += 10.0 if candidate.budget_max is not None else 7.0
        if candidate.budget_max is not None:
            reasons.append("Matched signal: Budget information is available for operator review.")

    score += _freelancer_freshness_points(candidate, reasons)

    bid_count = raw.get("bid_count")
    if isinstance(bid_count, (int, float)):
        if bid_count <= 5:
            score += 10.0
            reasons.append("Matched signal: Existing competition is still low.")
        elif bid_count <= 15:
            score += 7.0
            reasons.append("Matched signal: Existing competition is manageable.")
        elif bid_count <= 30:
            score += 4.0
        else:
            score += 1.0
            reasons.append("Negative signal: Existing competition is already high.")
    else:
        score += 5.0

    score += _freelancer_client_quality_points(raw, reasons)

    excluded_hits = sorted(term for term in exclude_terms if term and term in searchable)
    if excluded_hits:
        score -= min(24.0, len(excluded_hits) * 8.0)
        reasons.append("Negative signal: Search-profile excluded terms were detected.")
    for rule in FREELANCER_NEGATIVE_SIGNAL_RULES:
        if _contains_any_phrase(searchable, tuple(_normalize_text(term) or term for term in rule["terms"])):
            score -= rule["penalty"]
            reasons.append(f"Negative signal: {rule['name']} reduces software-opportunity relevance.")

    final_score = round(max(0.0, min(100.0, score)), 1)
    if not reasons:
        reasons.append("Negative signal: No strong marketplace relevance signals were detected.")
    return final_score, reasons, matched_terms or generic_skill_matches or skills[:5] or categories[:5]


class FreelancerMarketplaceConnector(BaseOpportunityConnector):
    metadata = _connector_metadata_for_type(FREELANCER_CONNECTOR_TYPE)

    def validate_config(self, config: dict[str, Any]) -> None:
        lookback_hours = int(config.get("lookback_hours", 24) or 24)
        maximum_projects = int(config.get("maximum_projects_per_scan", 50) or 50)
        maximum_query_groups = int(config.get("maximum_query_groups", 5) or 5)
        project_type = str(config.get("project_type", "all") or "all").strip().lower()
        project_status = str(config.get("project_status", "active") or "active").strip().lower()
        mode = str(config.get("mode", "production") or "production").strip().lower()
        if lookback_hours not in FREELANCER_LOOKBACK_OPTIONS:
            raise HTTPException(status_code=400, detail="lookback_hours must be one of 6, 12, 24, 72, 168, 336, or 720")
        if maximum_projects not in FREELANCER_MAX_PROJECT_OPTIONS:
            raise HTTPException(status_code=400, detail="maximum_projects_per_scan must be one of 10, 25, 50, 100, or 200")
        if maximum_query_groups < 1 or maximum_query_groups > 8:
            raise HTTPException(status_code=400, detail="maximum_query_groups must be between 1 and 8")
        if project_type not in FREELANCER_PROJECT_TYPE_OPTIONS:
            raise HTTPException(status_code=400, detail="project_type is invalid")
        if project_status not in FREELANCER_PROJECT_STATUS_OPTIONS:
            raise HTTPException(status_code=400, detail="project_status is invalid")
        if mode not in {"production", "mock"}:
            raise HTTPException(status_code=400, detail="mode must be either production or mock")

    def test_connection(self, config: dict[str, Any]) -> dict[str, Any]:
        self.validate_config(config)
        if str(config.get("mode", "production") or "production").strip().lower() == "mock":
            return {
                "success": True,
                "provider": "freelancer",
                "message": f"Mock provider available. Fixture version {FREELANCER_MOCK_FIXTURE_VERSION}. No external request performed.",
            }
        return {"success": False, "message": "Freelancer access token is required to test this connector."}

    def discover(
        self,
        *,
        connector: BusinessDevelopmentConnector,
        search_profile: BusinessDevelopmentSearchProfile | None,
        credential: ResolvedProviderCredential | None = None,
    ) -> list[AugmisBusinessDiscoveredOpportunityCandidate]:
        configuration = connector.configuration_json or {}
        self.validate_config(configuration)
        mode = str(configuration.get("mode", "production") or "production").strip().lower()
        if mode == "mock":
            candidates = _freelancer_mock_fixture_candidates()
            score_samples = []
            for candidate in candidates:
                score, _, _ = _calculate_freelancer_preliminary_relevance(candidate, search_profile)
                score_samples.append(_ted_relevance_band(score))
            self.last_run_metadata = {
                "provider": "Freelancer",
                "mode": CONNECTOR_TEST_MODE_LABEL,
                "fixture_mode": True,
                "fixture_version": FREELANCER_MOCK_FIXTURE_VERSION,
                "api_call_count": 0,
                "query_count": 1,
                "raw_results_fetched": len(candidates),
                "accepted_candidates": len(candidates),
                "filtered_candidates": 0,
                "same_scan_unique_sources": len(candidates),
                "score_bands": score_samples,
            }
            return candidates
        if not credential or not credential.api_key:
            raise HTTPException(status_code=400, detail="Freelancer access token is not configured.")
        client = FreelancerClient(access_token=credential.api_key)
        profile_payload = _serialize_search_profile(search_profile) if search_profile else {}
        maximum_projects = int(configuration.get("maximum_projects_per_scan", 50) or 50)
        maximum_groups = int(configuration.get("maximum_query_groups", 5) or 5)
        lookback_hours = int(configuration.get("lookback_hours", 24) or 24)
        min_budget = configuration.get("minimum_budget")
        max_budget = configuration.get("maximum_budget")
        max_bids = configuration.get("maximum_existing_bids")
        project_type = str(configuration.get("project_type", "all") or "all").strip().lower()
        specs = build_freelancer_search_specs(profile=profile_payload, maximum_groups=maximum_groups)
        per_query_limit = max(1, min(50, ceil(maximum_projects / max(1, len(specs)))))
        grouped_candidates: list[AugmisBusinessDiscoveredOpportunityCandidate] = []
        api_calls = 0
        raw_results = 0
        filtered_bid_count = 0
        query_diagnostics: list[dict[str, Any]] = []
        job_id_cache: dict[str, int] = {}

        for spec in specs:
            resolved_job_ids: list[int] = []
            missing_skill_names = [name for name in spec.skill_names if name.lower() not in job_id_cache]
            if missing_skill_names:
                job_id_cache.update(client.resolve_job_ids(list(missing_skill_names)))
                api_calls += 1
            resolved_job_ids = [job_id_cache[name.lower()] for name in spec.skill_names if name.lower() in job_id_cache]
            result = client.search_projects(
                query=spec.query,
                limit=per_query_limit,
                project_type=None if project_type == "all" else project_type,
                job_ids=resolved_job_ids,
                min_budget=float(min_budget) if isinstance(min_budget, (int, float)) else None,
                max_budget=float(max_budget) if isinstance(max_budget, (int, float)) else None,
                max_bid_count=int(max_bids) if isinstance(max_bids, (int, float)) else None,
            )
            api_calls += int(result["api_call_count"] or 0)
            raw_results += int(result["raw_count"] or 0)
            filtered_bid_count += int(result["filtered_bid_count"] or 0)
            query_projects = 0
            for project in result["projects"]:
                if project.status and project.status != "active":
                    continue
                if project.posted_at and project.posted_at < (_now() - timedelta(hours=lookback_hours)):
                    continue
                project_url = _freelancer_project_url(project.raw_project, project.project_id, project.seo_url)
                requirement_summary = (project.description or project.title)[:4000]
                summary_text = (project.description or "")[:1000] or project.title
                evidence = [
                    {"type": "marketplace_provider", "provider": "Freelancer"},
                    {"type": "project_id", "project_id": project.project_id},
                    {"type": "project_type", "project_type": project.project_type},
                    {"type": "budget", "value": _freelancer_budget_label(AugmisBusinessDiscoveredOpportunityCandidate(
                        external_id=project.project_id,
                        source_type="marketplace_project",
                        source_name="Freelancer",
                        source_url=project_url,
                        title=project.title,
                        organization_name=project.client_username or "Marketplace Client",
                        requirement_summary=requirement_summary,
                        budget_min=project.budget_min,
                        budget_max=project.budget_max,
                        currency=project.currency_code,
                    ))},
                    {"type": "skills", "skills": project.skills},
                    {"type": "bid_count", "bid_count": project.bid_count},
                ]
                grouped_candidates.append(
                    AugmisBusinessDiscoveredOpportunityCandidate(
                        external_id=project.project_id,
                        source_type="marketplace_project",
                        source_name="Freelancer",
                        source_url=project_url,
                        source_country=project.client_country,
                        title=project.title,
                        organization_name=project.client_username or "Marketplace Client",
                        published_date=project.posted_at,
                        closing_date=project.bid_end_at,
                        country=project.client_country,
                        region=project.client_location,
                        industry="Freelance Marketplace",
                        requirement_summary=requirement_summary,
                        raw_summary=summary_text,
                        raw_text=" ".join(part for part in [project.title, project.description or "", " ".join(project.skills), " ".join(project.categories)] if part)[:20000],
                        budget_min=project.budget_min,
                        budget_max=project.budget_max,
                        currency=project.currency_code,
                        evidence=evidence,
                        source_metadata={
                            "provider": "freelancer",
                            "provider_project_id": project.project_id,
                            "project_type": project.project_type,
                            "project_status": project.status,
                            "skills": project.skills,
                            "categories": project.categories,
                            "bid_count": project.bid_count,
                            "client_country": project.client_country,
                            "client_location": project.client_location,
                            "client_rating": project.client_rating,
                            "client_review_count": project.client_review_count,
                            "client_payment_verified": project.client_payment_verified,
                            "client_projects_posted": project.client_projects_posted,
                            "client_projects_completed": project.client_projects_completed,
                            "queries_matched": [spec.label],
                            "source_trust": "official_marketplace_api",
                        },
                        raw_content_json={
                            "provider": "freelancer",
                            "provider_project_id": project.project_id,
                            "project_url": project_url,
                            "project_type": project.project_type,
                            "project_status": project.status,
                            "skills": project.skills,
                            "categories": project.categories,
                            "bid_count": project.bid_count,
                            "bid_avg": project.bid_avg,
                            "client_country": project.client_country,
                            "client_location": project.client_location,
                            "client_rating": project.client_rating,
                            "client_review_count": project.client_review_count,
                            "client_payment_verified": project.client_payment_verified,
                            "client_projects_posted": project.client_projects_posted,
                            "client_projects_completed": project.client_projects_completed,
                            "client_username": project.client_username,
                            "source_trust": "official_marketplace_api",
                            "queries_matched": [spec.label],
                            "provider_version": FREELANCER_API_VERSION,
                            "provider_result": project.raw_project,
                        },
                        retrieval_timestamp=_now(),
                    )
                )
                query_projects += 1
            query_diagnostics.append(
                {
                    "key": spec.key,
                    "label": spec.label,
                    "query": spec.query,
                    "skills": list(spec.skill_names),
                    "raw_results": result["raw_count"],
                    "normalized": query_projects,
                    "filtered_bids": result["filtered_bid_count"],
                }
            )

        deduped: list[AugmisBusinessDiscoveredOpportunityCandidate] = []
        seen_ids: set[str] = set()
        for candidate in grouped_candidates:
            if candidate.external_id in seen_ids:
                continue
            seen_ids.add(candidate.external_id)
            deduped.append(candidate)
            if len(deduped) >= maximum_projects:
                break

        self.last_run_metadata = {
            "provider": "Freelancer",
            "mode": CONNECTOR_PRODUCTION_LABEL,
            "query_count": len(specs),
            "queries_executed": [spec.query for spec in specs],
            "api_call_count": api_calls,
            "api_result_count": raw_results,
            "raw_results_fetched": raw_results,
            "accepted_candidates": len(deduped),
            "filtered_candidates": 0,
            "filtered_bid_count": filtered_bid_count,
            "same_scan_unique_sources": len(deduped),
            "maximum_projects_per_scan": maximum_projects,
            "lookback_hours": lookback_hours,
            "project_type": project_type,
            "query_diagnostics": query_diagnostics,
        }
        return deduped


class ExternalWorkConnector(BaseOpportunityConnector):
    def __init__(self, connector_type: str, provider_code: str, provider_name: str) -> None:
        super().__init__()
        self.metadata = _connector_metadata_for_type(connector_type)
        self.connector_type = connector_type
        self.provider_code = provider_code
        self.provider_name = provider_name

    def validate_config(self, config: dict[str, Any]) -> None:
        maximum_results = int(config.get("maximum_results", 50) or 50)
        if maximum_results < 1 or maximum_results > 100:
            raise HTTPException(status_code=400, detail="maximum_results must be between 1 and 100")
        if self.provider_code == "adzuna":
            countries = [str(code).strip().lower() for code in (config.get("target_countries_json") or []) if str(code).strip()]
            if len(countries) > 5:
                raise HTTPException(status_code=400, detail="target_countries_json cannot contain more than 5 countries")

    def test_connection(self, config: dict[str, Any]) -> dict[str, Any]:
        self.validate_config(config)
        provider = get_external_work_provider(self.provider_code)
        return provider.test_connection(config)

    def discover(
        self,
        *,
        connector: BusinessDevelopmentConnector,
        search_profile: BusinessDevelopmentSearchProfile | None,
        credential: ResolvedProviderCredential | None = None,
    ) -> list[AugmisBusinessDiscoveredOpportunityCandidate]:
        configuration = connector.configuration_json or {}
        self.validate_config(configuration)
        provider = get_external_work_provider(self.provider_code)
        if self.provider_code == "adzuna" and (not credential or not credential.credential_payload):
            raise HTTPException(status_code=400, detail="Adzuna credentials are not configured.")
        opportunities = provider.search_opportunities(
            configuration,
            credential_payload=credential.credential_payload if credential else None,
            max_results=int(configuration.get("maximum_results", 50) or 50),
        )
        candidates = [_external_work_candidate(item) for item in opportunities]
        self.last_run_metadata = {
            "provider": self.provider_name,
            "mode": CONNECTOR_PRODUCTION_LABEL,
            "query_count": 1,
            "api_call_count": len(configuration.get("target_countries_json") or []) or 1 if self.provider_code == "adzuna" else 1,
            "raw_results_fetched": len(opportunities),
            "accepted_candidates": len(candidates),
            "filtered_candidates": 0,
            "same_scan_unique_sources": len(candidates),
            "countries_searched": configuration.get("target_countries_json") or [],
        }
        return candidates


class IndependentWebDiscoveryConnector(BaseOpportunityConnector):
    metadata = _connector_metadata_for_type(INDEPENDENT_WEB_CONNECTOR_TYPE)

    def validate_config(self, config: dict[str, Any]) -> None:
        maximum_domains_per_run = int(config.get("maximum_domains_per_run", 5) or 5)
        maximum_pages_per_domain = int(config.get("maximum_pages_per_domain", 25) or 25)
        maximum_total_pages_per_run = int(config.get("maximum_total_pages_per_run", 100) or 100)
        maximum_depth = int(config.get("maximum_depth", 2) or 2)
        request_timeout_seconds = int(config.get("request_timeout_seconds", 15) or 15)
        per_domain_delay_seconds = int(config.get("per_domain_delay_seconds", 2) or 2)
        max_html_response_bytes = int(
            config.get(
                "max_html_response_bytes",
                settings.AUGMIS_WEB_DISCOVERY_DEFAULT_MAX_HTML_RESPONSE_BYTES,
            )
            or settings.AUGMIS_WEB_DISCOVERY_DEFAULT_MAX_HTML_RESPONSE_BYTES
        )
        if maximum_domains_per_run < 1 or maximum_domains_per_run > settings.AUGMIS_WEB_DISCOVERY_MAX_DOMAINS_PER_RUN:
            raise HTTPException(status_code=400, detail="maximum_domains_per_run is out of bounds.")
        if maximum_pages_per_domain < 1 or maximum_pages_per_domain > settings.AUGMIS_WEB_DISCOVERY_MAX_PAGES_PER_DOMAIN:
            raise HTTPException(status_code=400, detail="maximum_pages_per_domain is out of bounds.")
        if maximum_total_pages_per_run < 1 or maximum_total_pages_per_run > settings.AUGMIS_WEB_DISCOVERY_MAX_TOTAL_PAGES_PER_RUN:
            raise HTTPException(status_code=400, detail="maximum_total_pages_per_run is out of bounds.")
        if maximum_depth < 0 or maximum_depth > settings.AUGMIS_WEB_DISCOVERY_MAX_DEPTH:
            raise HTTPException(status_code=400, detail="maximum_depth is out of bounds.")
        if request_timeout_seconds < 3 or request_timeout_seconds > 30:
            raise HTTPException(status_code=400, detail="request_timeout_seconds is out of bounds.")
        if per_domain_delay_seconds < settings.AUGMIS_WEB_DISCOVERY_MIN_DOMAIN_DELAY_SECONDS or per_domain_delay_seconds > settings.AUGMIS_WEB_DISCOVERY_MAX_DOMAIN_DELAY_SECONDS:
            raise HTTPException(status_code=400, detail="per_domain_delay_seconds is out of bounds.")
        if max_html_response_bytes < 500_000 or max_html_response_bytes > settings.AUGMIS_WEB_DISCOVERY_MAX_HTML_RESPONSE_BYTES:
            raise HTTPException(status_code=400, detail="max_html_response_bytes must be between 500000 and 5000000.")

    def discover(
        self,
        *,
        connector: BusinessDevelopmentConnector,
        search_profile: BusinessDevelopmentSearchProfile | None,
        credential: ResolvedProviderCredential | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        run_type: str = "manual",
    ) -> list[AugmisBusinessDiscoveredOpportunityCandidate]:
        del credential
        session = object_session(connector)
        if session is None:
            raise HTTPException(status_code=500, detail="Connector session is unavailable.")
        engine = IndependentWebDiscoveryEngine(
            session,
            connector,
            search_profile,
            progress_callback=progress_callback,
            run_type=run_type,
        )
        candidates, metadata = engine.run()
        self.last_run_metadata = metadata
        return candidates


def _get_connector_implementation(connector_type: str) -> BaseOpportunityConnector:
    if connector_type == FIXTURE_CONNECTOR_TYPE:
        return FixtureOpportunityConnector()
    if connector_type == WEB_SEARCH_CONNECTOR_TYPE:
        return WebOpportunitySearchConnector()
    if connector_type == TED_CONNECTOR_TYPE:
        return TedProcurementConnector()
    if connector_type == FREELANCER_CONNECTOR_TYPE:
        return FreelancerMarketplaceConnector()
    if connector_type == REMOTEOK_CONNECTOR_TYPE:
        return ExternalWorkConnector(REMOTEOK_CONNECTOR_TYPE, "remoteok", "Remote OK")
    if connector_type == ARBEITNOW_CONNECTOR_TYPE:
        return ExternalWorkConnector(ARBEITNOW_CONNECTOR_TYPE, "arbeitnow", "Arbeitnow")
    if connector_type == REMOTIVE_CONNECTOR_TYPE:
        return ExternalWorkConnector(REMOTIVE_CONNECTOR_TYPE, "remotive", "Remotive")
    if connector_type == ADZUNA_CONNECTOR_TYPE:
        return ExternalWorkConnector(ADZUNA_CONNECTOR_TYPE, "adzuna", "Adzuna")
    if connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE:
        return IndependentWebDiscoveryConnector()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported connector type: {connector_type}",
    )


def _serialize_connector_run(row: BusinessDevelopmentConnectorRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "connector_id": row.connector_id,
        "run_type": row.run_type,
        "status": row.status,
        "attempt_number": row.attempt_number,
        "max_attempts": row.max_attempts,
        "retry_of_run_id": row.retry_of_run_id,
        "next_retry_at": _serialize_datetime(row.next_retry_at),
        "started_at": _serialize_datetime(row.started_at),
        "completed_at": _serialize_datetime(row.completed_at),
        "items_found": row.items_found,
        "items_new": row.items_new,
        "items_duplicate": row.items_duplicate,
        "items_filtered": row.items_filtered,
        "items_failed": row.items_failed,
        "error_summary": row.error_summary,
        "run_metadata_json": row.run_metadata_json or {},
        "initiated_by": row.initiated_by,
        "created_at": _serialize_datetime(row.created_at),
    }


def _discovery_source_identity(row: BusinessDevelopmentDiscoveredOpportunity) -> dict[str, Any]:
    raw = row.raw_content_json or {}
    session = object_session(row)
    connector = (
        session.query(BusinessDevelopmentConnector)
        .filter(
            BusinessDevelopmentConnector.tenant_id == row.tenant_id,
            BusinessDevelopmentConnector.id == row.connector_id,
        )
        .first()
        if session is not None
        else None
    )
    connector_type = connector.connector_type if connector else None
    provider_key = str(raw.get("provider") or "").strip().lower() or None
    display_source = row.source_name or row.source_type
    if connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE or provider_key == "augmis_internal":
        provider_key = "augmis_internal"
        display_source = INDEPENDENT_WEB_SOURCE_NAME
    elif connector_type == TED_CONNECTOR_TYPE or provider_key == "ted" or (row.source_name or "").strip().upper() == "TED":
        provider_key = "ted"
        display_source = "TED"
    elif connector_type == WEB_SEARCH_CONNECTOR_TYPE:
        provider_key = provider_key or "web_search"
        display_source = row.source_name or WEB_SEARCH_CONNECTOR_NAME
    elif connector_type == FREELANCER_CONNECTOR_TYPE:
        provider_key = provider_key or "freelancer"
        display_source = row.source_name or "Freelancer"
    elif connector_type == REMOTEOK_CONNECTOR_TYPE:
        provider_key = provider_key or "remoteok"
        display_source = row.source_name or REMOTEOK_CONNECTOR_NAME
    elif connector_type == ARBEITNOW_CONNECTOR_TYPE:
        provider_key = provider_key or "arbeitnow"
        display_source = row.source_name or ARBEITNOW_CONNECTOR_NAME
    elif connector_type == REMOTIVE_CONNECTOR_TYPE:
        provider_key = provider_key or "remotive"
        display_source = row.source_name or REMOTIVE_CONNECTOR_NAME
    elif connector_type == ADZUNA_CONNECTOR_TYPE:
        provider_key = provider_key or "adzuna"
        display_source = row.source_name or ADZUNA_CONNECTOR_NAME
    elif row.source_name:
        provider_key = provider_key or _normalize_text(row.source_name)
    return {
        "source_provider_key": provider_key,
        "source_provider_name": row.source_name,
        "source_connector_type": connector_type,
        "display_source": display_source,
    }


def _serialize_discovery(row: BusinessDevelopmentDiscoveredOpportunity) -> dict[str, Any]:
    relevance_band = _ted_relevance_band(row.preliminary_relevance_score)
    closing_status = _ted_closing_status(row.closing_date)
    positive_reasons, negative_reasons = _split_relevance_reasons(row.relevance_reasons_json or [])
    source_language_code = detect_discovery_language(row)
    session = object_session(row)
    active_translation_row = (
        get_latest_translation_row(session, row.tenant_id, row.id)
        if session is not None
        else None
    )
    source_identity = _discovery_source_identity(row)
    validity = _extract_validity_payload(row.raw_content_json or {})
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "connector_id": row.connector_id,
        "connector_run_id": row.connector_run_id,
        "external_id": row.external_id,
        "source_type": row.source_type,
        "source_name": row.source_name,
        **source_identity,
        "source_url": row.source_url,
        "canonical_source_url": row.canonical_source_url,
        "source_domain": row.source_domain,
        "source_country": row.source_country,
        "title": row.title,
        "normalized_title": row.normalized_title,
        "organization_name": row.organization_name,
        "normalized_organization_name": row.normalized_organization_name,
        "published_date": _serialize_datetime(row.published_date),
        "closing_date": _serialize_datetime(row.closing_date),
        "raw_summary": row.raw_summary,
        "requirement_summary": row.requirement_summary,
        "normalized_content_json": row.normalized_content_json or {},
        "raw_content_json": row.raw_content_json or {},
        "raw_text": row.raw_text,
        "country": row.country,
        "region": row.region,
        "industry": row.industry,
        "budget_min": row.budget_min,
        "budget_max": row.budget_max,
        "currency": row.currency,
        "discovered_at": _serialize_datetime(row.discovered_at),
        "retrieval_timestamp": _serialize_datetime(row.retrieval_timestamp),
        "discovery_status": row.discovery_status,
        "duplicate_of_discovery_id": row.duplicate_of_discovery_id,
        "possible_duplicate_of_discovery_id": row.possible_duplicate_of_discovery_id,
        "imported_opportunity_id": row.imported_opportunity_id,
        "preliminary_relevance_score": row.preliminary_relevance_score,
        "validity_score": validity.get("validity_score"),
        "validity_band": validity.get("validity_band"),
        "validity_class": validity.get("validity_class"),
        "actionability": validity.get("actionability"),
        "validity_positive_evidence": validity.get("positive_evidence") or [],
        "validity_negative_evidence": validity.get("negative_evidence") or [],
        "validity_reason_codes": validity.get("reason_codes") or [],
        "validity_eligible_for_inbox": bool(validity.get("eligible_for_inbox")),
        **serialize_discovery_commercial_intelligence(row),
        "source_language_code": source_language_code,
        "source_language_label": language_label(source_language_code),
        "source_language_is_english": is_english_language(source_language_code),
        "translation_required": not is_english_language(source_language_code),
        "active_translation": None
        if active_translation_row is None
        else {
            "id": active_translation_row.id,
            "tenant_id": active_translation_row.tenant_id,
            "discovery_id": active_translation_row.discovery_id,
            "translation_version": active_translation_row.translation_version,
            "source_language": active_translation_row.source_language,
            "source_language_label": language_label(active_translation_row.source_language),
            "target_language": active_translation_row.target_language,
            "translated_title": active_translation_row.translated_title,
            "translated_summary": active_translation_row.translated_summary,
            "translated_description": active_translation_row.translated_description,
            "translated_detail_json": active_translation_row.translated_detail_json or {},
            "provider": active_translation_row.provider,
            "model": active_translation_row.model,
            "prompt_bundle_version": active_translation_row.prompt_bundle_version,
            "prompt_version": active_translation_row.prompt_version,
            "usage_json": active_translation_row.usage_json or {},
            "created_by": active_translation_row.created_by,
            "created_at": _serialize_datetime(active_translation_row.created_at),
            "updated_at": _serialize_datetime(active_translation_row.updated_at),
        },
        "relevance_band": relevance_band,
        "closing_status": closing_status,
        "relevance_reasons_json": row.relevance_reasons_json or [],
        "positive_relevance_reasons": positive_reasons,
        "negative_relevance_reasons": negative_reasons,
        "matched_keywords_json": row.matched_keywords_json or [],
        "evidence_json": row.evidence_json or [],
        "normalized_search_text": row.normalized_search_text,
        "url_fingerprint": row.url_fingerprint,
        "composite_fingerprint": row.composite_fingerprint,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def _serialize_connector(row: BusinessDevelopmentConnector) -> dict[str, Any]:
    metadata = _connector_metadata_for_type(row.connector_type)
    metadata_payload = metadata.model_dump(mode="json")
    schedule_timezone = _schedule_timezone_name(row.schedule_timezone)
    session = object_session(row)
    provider_code = str((row.configuration_json or {}).get("provider", "tavily") or "tavily")
    effective_status = row.status
    capability_flags = dict(row.capability_flags_json or {})
    if row.connector_type == FREELANCER_CONNECTOR_TYPE:
        mode = str((row.configuration_json or {}).get("mode", "production") or "production").strip().lower()
        capability_flags["mode"] = CONNECTOR_TEST_MODE_LABEL if mode == "mock" else CONNECTOR_PRODUCTION_LABEL
        if mode == "mock":
            effective_status = "ready" if row.enabled and row.active_run_id is None else row.status
        elif session is not None:
            credential = resolve_provider_credential(session, row.tenant_id, "freelancer")
            if not credential.api_key:
                effective_status = "attention"
                capability_flags["authorization_state"] = "required"
    elif row.connector_type == ADZUNA_CONNECTOR_TYPE and session is not None:
        credential = resolve_provider_credential(session, row.tenant_id, "adzuna")
        if not credential.credential_payload:
            effective_status = "attention"
            capability_flags["authorization_state"] = "required"
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "search_profile_id": row.search_profile_id,
        "connector_type": row.connector_type,
        "name": row.name,
        "source_category": row.source_category,
        "status": effective_status,
        "enabled": row.enabled,
        "schedule_enabled": row.schedule_enabled,
        "schedule_expression": row.schedule_expression
        or _build_schedule_expression(
            schedule_enabled=row.schedule_enabled,
            schedule_type=row.schedule_type,
            schedule_interval_minutes=row.schedule_interval_minutes,
            schedule_day_of_week=row.schedule_day_of_week,
            schedule_time_local=row.schedule_time_local,
        ),
        "schedule_type": row.schedule_type,
        "schedule_interval_minutes": row.schedule_interval_minutes,
        "schedule_day_of_week": row.schedule_day_of_week,
        "schedule_time_local": row.schedule_time_local,
        "schedule_timezone": schedule_timezone,
        "next_run_at": _serialize_datetime(row.next_run_at),
        "last_scheduled_run_at": _serialize_datetime(row.last_scheduled_run_at),
        "schedule_retry_count": row.schedule_retry_count or 0,
        "active_run_id": row.active_run_id,
        "schedule_updated_by": row.schedule_updated_by,
        "schedule_updated_at": _serialize_datetime(row.schedule_updated_at),
        "configuration_json": row.configuration_json or {},
        "search_criteria_json": row.search_criteria_json or {},
        "capability_flags_json": capability_flags,
        "last_scan_at": _serialize_datetime(row.last_scan_at),
        "last_success_at": _serialize_datetime(row.last_success_at),
        "last_error_at": _serialize_datetime(row.last_error_at),
        "last_error_message": row.last_error_message,
        "created_by": row.created_by,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
        "metadata": metadata_payload,
    }


def _require_search_profile(db: Session, tenant_id: str, profile_id: str) -> BusinessDevelopmentSearchProfile:
    row = (
        db.query(BusinessDevelopmentSearchProfile)
        .filter(
            BusinessDevelopmentSearchProfile.id == profile_id,
            BusinessDevelopmentSearchProfile.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search profile not found")
    return row


def _require_connector(db: Session, tenant_id: str, connector_id: str) -> BusinessDevelopmentConnector:
    row = (
        db.query(BusinessDevelopmentConnector)
        .filter(
            BusinessDevelopmentConnector.id == connector_id,
            BusinessDevelopmentConnector.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")
    return row


def _apply_schedule_defaults(
    row: BusinessDevelopmentConnector,
    *,
    schedule_enabled: bool,
    schedule_type: str,
    schedule_interval_minutes: int | None,
    schedule_day_of_week: int | None,
    schedule_time_local: str | None,
    schedule_timezone: str | None,
    effective_now: datetime,
):
    normalized_type = (schedule_type or "manual").strip().lower()
    normalized_timezone = _schedule_timezone_name(schedule_timezone)
    row.schedule_enabled = schedule_enabled and normalized_type != "manual"
    row.schedule_type = normalized_type if row.schedule_enabled else "manual"
    row.schedule_interval_minutes = schedule_interval_minutes if row.schedule_enabled and normalized_type == "hourly_interval" else None
    row.schedule_day_of_week = schedule_day_of_week if row.schedule_enabled and normalized_type == "weekly" else None
    row.schedule_time_local = schedule_time_local if row.schedule_enabled and normalized_type in {"daily", "weekly"} else None
    row.schedule_timezone = normalized_timezone if row.schedule_enabled else normalized_timezone
    row.schedule_expression = _build_schedule_expression(
        schedule_enabled=row.schedule_enabled,
        schedule_type=row.schedule_type,
        schedule_interval_minutes=row.schedule_interval_minutes,
        schedule_day_of_week=row.schedule_day_of_week,
        schedule_time_local=row.schedule_time_local,
    )
    if row.schedule_enabled:
        row.next_run_at = _compute_next_run_at(
            schedule_type=row.schedule_type,
            schedule_interval_minutes=row.schedule_interval_minutes,
            schedule_day_of_week=row.schedule_day_of_week,
            schedule_time_local=row.schedule_time_local,
            schedule_timezone=row.schedule_timezone,
            after_utc=effective_now,
            anchor_utc=row.last_scheduled_run_at,
        )
    else:
        row.next_run_at = None
        row.last_scheduled_run_at = None
        row.schedule_retry_count = 0
        row.schedule_retry_run_id = None


def _claim_connector_run(
    db: Session,
    *,
    connector: BusinessDevelopmentConnector,
    tenant_id: str,
    run_id: str,
    started_at: datetime,
    due_reference: datetime | None = None,
) -> bool:
    updated = (
        db.query(BusinessDevelopmentConnector)
        .filter(
            BusinessDevelopmentConnector.id == connector.id,
            BusinessDevelopmentConnector.tenant_id == tenant_id,
            BusinessDevelopmentConnector.active_run_id.is_(None),
        )
        .update(
            {
                "active_run_id": run_id,
                "status": "running",
                "last_scan_at": started_at,
                "last_scheduled_run_at": due_reference or connector.last_scheduled_run_at,
                "next_run_at": None if due_reference else connector.next_run_at,
                "updated_at": started_at,
            },
            synchronize_session=False,
        )
    )
    if not updated:
        db.rollback()
        return False
    db.flush()
    return True


def _candidate_from_discovery_row(
    row: BusinessDevelopmentDiscoveredOpportunity,
) -> AugmisBusinessDiscoveredOpportunityCandidate:
    raw_content = dict(row.raw_content_json or {})
    source_metadata = dict(raw_content.get("source_metadata") or {})
    if not source_metadata:
        source_metadata = {
            key: raw_content.get(key)
            for key in (
                "provider",
                "opportunity_class",
                "contact_routes",
                "application_url",
                "reference_number",
                "crawl_source",
                "seed_name",
            )
            if raw_content.get(key) is not None
        }
    if raw_content.get("crawler_diagnostics") is not None:
        source_metadata["crawler_diagnostics"] = raw_content.get("crawler_diagnostics")
    return AugmisBusinessDiscoveredOpportunityCandidate(
        external_id=row.external_id,
        source_type=row.source_type,
        source_name=row.source_name,
        source_url=row.source_url,
        source_country=row.source_country,
        title=row.title,
        organization_name=row.organization_name,
        published_date=row.published_date,
        closing_date=row.closing_date,
        country=row.country,
        region=row.region,
        industry=row.industry,
        requirement_summary=row.requirement_summary,
        raw_summary=row.raw_summary,
        raw_text=row.raw_text,
        budget_min=row.budget_min,
        budget_max=row.budget_max,
        currency=row.currency,
        evidence=list(row.evidence_json or []),
        source_metadata=source_metadata,
        raw_content_json=raw_content,
        retrieval_timestamp=row.retrieval_timestamp,
    )


def _apply_validity_to_discovery_row(
    db: Session,
    row: BusinessDevelopmentDiscoveredOpportunity,
) -> dict[str, Any]:
    row.published_date = _as_utc(row.published_date)
    row.closing_date = _as_utc(row.closing_date)
    row.retrieval_timestamp = _as_utc(row.retrieval_timestamp)
    candidate = _candidate_from_discovery_row(row)
    validity = _opportunity_validity_payload(candidate)
    raw_content = dict(row.raw_content_json or {})
    raw_content["opportunity_validity"] = validity
    crawler = raw_content.get("crawler_diagnostics") if isinstance(raw_content.get("crawler_diagnostics"), dict) else {}
    raw_content["crawler_diagnostics"] = {
        **crawler,
        "validity_score": validity.get("validity_score"),
        "validity_class": validity.get("validity_class"),
    }
    row.raw_content_json = raw_content
    row.updated_at = _now()
    refresh_discovery_commercial_intelligence(db, row)
    if row.discovery_status not in {"imported", "shortlisted", "rejected"}:
        if not validity.get("eligible_for_inbox"):
            row.discovery_status = "irrelevant"
        elif (row.preliminary_relevance_score or 0.0) < _preliminary_irrelevant_threshold(row.source_type):
            row.discovery_status = "irrelevant"
        else:
            row.discovery_status = "new"
    return validity


def _require_discovery(
    db: Session, tenant_id: str, discovery_id: str
) -> BusinessDevelopmentDiscoveredOpportunity:
    row = (
        db.query(BusinessDevelopmentDiscoveredOpportunity)
        .filter(
            BusinessDevelopmentDiscoveredOpportunity.id == discovery_id,
            BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery not found")
    return row


def _derive_default_profile_values(db: Session, tenant_id: str) -> dict[str, Any]:
    experience_items = (
        db.query(BusinessDevelopmentExperienceItem)
        .filter(BusinessDevelopmentExperienceItem.tenant_id == tenant_id)
        .all()
    )
    include_keywords: set[str] = set()
    include_technologies: set[str] = set()
    include_capabilities: set[str] = set()
    for item in experience_items:
        include_keywords.update(item.keywords_json or [])
        include_technologies.update(item.technologies_json or [])
        include_capabilities.update(item.reusable_capabilities_json or [])
        include_capabilities.update(item.features_json or [])
    return {
        "target_regions_json": [],
        "target_countries_json": [],
        "target_industries_json": sorted({value for item in experience_items for value in (item.industries_json or [])}),
        "include_keywords_json": sorted(include_keywords),
        "include_technologies_json": sorted(include_technologies),
        "include_capabilities_json": sorted(include_capabilities),
        "exclude_keywords_json": ["jobs", "recruitment", "hardware supply", "vehicle purchase"],
        "excluded_domains_json": [],
        "excluded_categories_json": [],
        "minimum_budget": None,
        "currencies_json": ["USD", "EUR", "GBP"],
        "allow_budget_unknown": True,
        "solo_feasibility_preference": "solo_with_support",
        "small_team_allowed": True,
        "max_delivery_months": None,
        "max_age_days": 30,
    }


def ensure_default_search_profile(
    db: Session,
    tenant_id: str,
    current_user: dict | None = None,
) -> BusinessDevelopmentSearchProfile:
    row = (
        db.query(BusinessDevelopmentSearchProfile)
        .filter(
            BusinessDevelopmentSearchProfile.tenant_id == tenant_id,
            BusinessDevelopmentSearchProfile.name == DEFAULT_PROFILE_NAME,
        )
        .first()
    )
    if row:
        return row
    defaults = _derive_default_profile_values(db, tenant_id)
    row = BusinessDevelopmentSearchProfile(
        id=f"BD-SRP-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        name=DEFAULT_PROFILE_NAME,
        enabled=True,
        created_by=(current_user or {}).get("user_id"),
        updated_at=_now(),
        **defaults,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def ensure_fixture_connector(
    db: Session,
    tenant_id: str,
    current_user: dict | None = None,
) -> BusinessDevelopmentConnector:
    row = (
        db.query(BusinessDevelopmentConnector)
        .filter(
            BusinessDevelopmentConnector.tenant_id == tenant_id,
            BusinessDevelopmentConnector.connector_type == FIXTURE_CONNECTOR_TYPE,
        )
        .first()
    )
    if row:
        return row
    profile = ensure_default_search_profile(db, tenant_id, current_user)
    row = BusinessDevelopmentConnector(
        id=f"BD-CNX-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        search_profile_id=profile.id,
        connector_type=FIXTURE_CONNECTOR_TYPE,
        name=FIXTURE_CONNECTOR_NAME,
        source_category="fixture",
        status="ready",
        enabled=True,
        schedule_enabled=False,
        schedule_expression=None,
        schedule_type="manual",
        schedule_timezone=_schedule_timezone_name(None),
        configuration_json={"dataset": "default", "include_duplicates": True},
        search_criteria_json={},
        capability_flags_json={"test_label": CONNECTOR_TEST_LABEL},
        created_by=(current_user or {}).get("user_id"),
        updated_at=_now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def ensure_web_search_connector(
    db: Session,
    tenant_id: str,
    current_user: dict | None = None,
) -> BusinessDevelopmentConnector:
    row = (
        db.query(BusinessDevelopmentConnector)
        .filter(
            BusinessDevelopmentConnector.tenant_id == tenant_id,
            BusinessDevelopmentConnector.connector_type == WEB_SEARCH_CONNECTOR_TYPE,
        )
        .first()
    )
    if row:
        return row
    profile = ensure_default_search_profile(db, tenant_id, current_user)
    row = BusinessDevelopmentConnector(
        id=f"BD-CNX-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        search_profile_id=profile.id,
        connector_type=WEB_SEARCH_CONNECTOR_TYPE,
        name=WEB_SEARCH_CONNECTOR_NAME,
        source_category="search",
        status="ready",
        enabled=True,
        schedule_enabled=False,
        schedule_expression=None,
        schedule_type="manual",
        schedule_timezone=_schedule_timezone_name(None),
        configuration_json={
            "provider": "tavily",
            "results_per_query": 10,
            "maximum_queries_per_scan": 10,
            "recency_days": 30,
            "language": "en",
            "max_candidate_results": 100,
            "max_source_fetches_per_scan": 30,
            "fetch_source_page": True,
            "max_fetch_bytes": 100000,
            "fetch_timeout_seconds": 10,
            "max_extracted_text_chars": 30000,
            "max_redirects": 3,
        },
        search_criteria_json={},
        capability_flags_json={"mode": CONNECTOR_PRODUCTION_LABEL},
        created_by=(current_user or {}).get("user_id"),
        updated_at=_now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def ensure_ted_connector(
    db: Session,
    tenant_id: str,
    current_user: dict | None = None,
) -> BusinessDevelopmentConnector:
    row = (
        db.query(BusinessDevelopmentConnector)
        .filter(
            BusinessDevelopmentConnector.tenant_id == tenant_id,
            BusinessDevelopmentConnector.connector_type == TED_CONNECTOR_TYPE,
        )
        .first()
    )
    if row:
        return row
    profile = ensure_default_search_profile(db, tenant_id, current_user)
    row = BusinessDevelopmentConnector(
        id=f"BD-CNX-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        search_profile_id=profile.id,
        connector_type=TED_CONNECTOR_TYPE,
        name=TED_CONNECTOR_NAME,
        source_category="procurement",
        status="ready",
        enabled=True,
        schedule_enabled=False,
        schedule_expression=None,
        schedule_type="manual",
        schedule_timezone=_schedule_timezone_name(None),
        configuration_json={
            "lookback_days": 7,
            "maximum_notices_per_scan": 50,
            "notice_type_mode": "competition_only",
            "country_scope_mode": "search_profile",
            "selected_countries_json": [],
            "cpv_scope": "broad_software_services",
        },
        search_criteria_json={},
        capability_flags_json={"mode": CONNECTOR_PRODUCTION_LABEL, "provider_label": "TED"},
        created_by=(current_user or {}).get("user_id"),
        updated_at=_now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def ensure_freelancer_connector(
    db: Session,
    tenant_id: str,
    current_user: dict | None = None,
) -> BusinessDevelopmentConnector:
    row = (
        db.query(BusinessDevelopmentConnector)
        .filter(
            BusinessDevelopmentConnector.tenant_id == tenant_id,
            BusinessDevelopmentConnector.connector_type == FREELANCER_CONNECTOR_TYPE,
        )
        .first()
    )
    if row:
        return row
    profile = ensure_default_search_profile(db, tenant_id, current_user)
    row = BusinessDevelopmentConnector(
        id=f"BD-CNX-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        search_profile_id=profile.id,
        connector_type=FREELANCER_CONNECTOR_TYPE,
        name=FREELANCER_CONNECTOR_NAME,
        source_category="marketplace",
        status="ready",
        enabled=True,
        schedule_enabled=False,
        schedule_expression=None,
        schedule_type="manual",
        schedule_timezone=_schedule_timezone_name(None),
        configuration_json={
            "provider": "freelancer",
            "mode": "production",
            "lookback_hours": 24,
            "maximum_projects_per_scan": 50,
            "maximum_query_groups": 5,
            "project_type": "all",
            "project_status": "active",
            "minimum_budget": None,
            "maximum_budget": None,
            "maximum_existing_bids": None,
        },
        search_criteria_json={},
        capability_flags_json={"mode": CONNECTOR_PRODUCTION_LABEL, "provider_label": "Freelancer", "mock_available": True},
        created_by=(current_user or {}).get("user_id"),
        updated_at=_now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _ensure_external_work_connector(
    db: Session,
    tenant_id: str,
    current_user: dict | None,
    *,
    connector_type: str,
    name: str,
    provider: str,
    category_label: str,
    configuration_json: dict[str, Any],
) -> BusinessDevelopmentConnector:
    row = (
        db.query(BusinessDevelopmentConnector)
        .filter(
            BusinessDevelopmentConnector.tenant_id == tenant_id,
            BusinessDevelopmentConnector.connector_type == connector_type,
        )
        .first()
    )
    if row:
        return row
    profile = ensure_default_search_profile(db, tenant_id, current_user)
    row = BusinessDevelopmentConnector(
        id=f"BD-CNX-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        search_profile_id=profile.id,
        connector_type=connector_type,
        name=name,
        source_category="api",
        status="ready",
        enabled=True,
        schedule_enabled=False,
        schedule_expression=None,
        schedule_type="manual",
        schedule_timezone=_schedule_timezone_name(None),
        configuration_json=configuration_json,
        search_criteria_json={},
        capability_flags_json={"mode": CONNECTOR_PRODUCTION_LABEL, "provider_label": category_label},
        created_by=(current_user or {}).get("user_id"),
        updated_at=_now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def ensure_remoteok_connector(db: Session, tenant_id: str, current_user: dict | None = None) -> BusinessDevelopmentConnector:
    return _ensure_external_work_connector(
        db,
        tenant_id,
        current_user,
        connector_type=REMOTEOK_CONNECTOR_TYPE,
        name=REMOTEOK_CONNECTOR_NAME,
        provider="remoteok",
        category_label="Remote OK",
        configuration_json={"provider": "remoteok", "maximum_results": 50},
    )


def ensure_arbeitnow_connector(db: Session, tenant_id: str, current_user: dict | None = None) -> BusinessDevelopmentConnector:
    return _ensure_external_work_connector(
        db,
        tenant_id,
        current_user,
        connector_type=ARBEITNOW_CONNECTOR_TYPE,
        name=ARBEITNOW_CONNECTOR_NAME,
        provider="arbeitnow",
        category_label="Arbeitnow",
        configuration_json={"provider": "arbeitnow", "remote_only": True, "maximum_results": 50},
    )


def ensure_remotive_connector(db: Session, tenant_id: str, current_user: dict | None = None) -> BusinessDevelopmentConnector:
    return _ensure_external_work_connector(
        db,
        tenant_id,
        current_user,
        connector_type=REMOTIVE_CONNECTOR_TYPE,
        name=REMOTIVE_CONNECTOR_NAME,
        provider="remotive",
        category_label="Remotive",
        configuration_json={"provider": "remotive", "maximum_results": 50, "search_keyword": "", "category": ""},
    )


def ensure_adzuna_connector(db: Session, tenant_id: str, current_user: dict | None = None) -> BusinessDevelopmentConnector:
    return _ensure_external_work_connector(
        db,
        tenant_id,
        current_user,
        connector_type=ADZUNA_CONNECTOR_TYPE,
        name=ADZUNA_CONNECTOR_NAME,
        provider="adzuna",
        category_label="Adzuna",
        configuration_json={"provider": "adzuna", "maximum_results": 25, "search_keyword": "software developer", "target_countries_json": ["gb"]},
    )


def ensure_independent_web_connector(
    db: Session,
    tenant_id: str,
    current_user: dict | None = None,
) -> BusinessDevelopmentConnector:
    row = (
        db.query(BusinessDevelopmentConnector)
        .filter(
            BusinessDevelopmentConnector.tenant_id == tenant_id,
            BusinessDevelopmentConnector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE,
        )
        .first()
    )
    if row:
        return row
    profile = ensure_default_search_profile(db, tenant_id, current_user)
    row = BusinessDevelopmentConnector(
        id=f"BD-CNX-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        search_profile_id=profile.id,
        connector_type=INDEPENDENT_WEB_CONNECTOR_TYPE,
        name=INDEPENDENT_WEB_CONNECTOR_NAME,
        source_category="company_source",
        status="ready",
        enabled=True,
        schedule_enabled=False,
        schedule_expression=None,
        schedule_type="manual",
        schedule_timezone=_schedule_timezone_name(None),
        configuration_json={
            "crawl_engine": CRAWL_ENGINE_AUGMIS_NATIVE,
            "maximum_seeds_per_run": 5,
            "maximum_domains_per_run": 5,
            "maximum_pages_per_domain": 25,
            "maximum_total_pages_per_run": 100,
            "maximum_depth": 2,
            "request_timeout_seconds": 15,
            "per_domain_delay_seconds": 2,
            "recrawl_interval_hours": 168,
            "allowed_domain_mode": "approved_only",
            "max_html_response_bytes": settings.AUGMIS_WEB_DISCOVERY_DEFAULT_MAX_HTML_RESPONSE_BYTES,
            "max_extracted_text_chars": 40000,
            "maximum_links_per_page": 40,
            "maximum_run_duration_seconds": 180,
        },
        search_criteria_json={},
        capability_flags_json={
            "mode": CONNECTOR_PRODUCTION_LABEL,
            "provider_label": "AUGMIS Internal",
            "credential_state": "none_required",
        },
        created_by=(current_user or {}).get("user_id"),
        updated_at=_now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_search_profiles(db: Session, tenant_id: str, current_user: dict | None = None) -> dict[str, Any]:
    ensure_default_search_profile(db, tenant_id, current_user)
    rows = (
        db.query(BusinessDevelopmentSearchProfile)
        .filter(BusinessDevelopmentSearchProfile.tenant_id == tenant_id)
        .order_by(BusinessDevelopmentSearchProfile.created_at.asc())
        .all()
    )
    return {"success": True, "data": [_serialize_search_profile(row) for row in rows]}


def create_search_profile(
    db: Session,
    tenant_id: str,
    current_user: dict,
    payload: AugmisBusinessSearchProfileCreateRequest,
) -> dict[str, Any]:
    row = BusinessDevelopmentSearchProfile(
        id=f"BD-SRP-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        created_by=current_user["user_id"],
        updated_at=_now(),
        **payload.model_dump(),
    )
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Search profile conflicts with an existing tenant record")
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="CREATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Created search profile {row.name}",
        resource_type="bd_search_profile",
        resource_id=row.id,
        metadata={},
    )
    return {"success": True, "data": _serialize_search_profile(row)}


def update_search_profile(
    db: Session,
    tenant_id: str,
    profile_id: str,
    current_user: dict,
    payload: AugmisBusinessSearchProfileUpdateRequest,
) -> dict[str, Any]:
    row = _require_search_profile(db, tenant_id, profile_id)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(row, key, value)
    row.updated_at = _now()
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Search profile conflicts with an existing tenant record")
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated search profile {row.name}",
        resource_type="bd_search_profile",
        resource_id=row.id,
        metadata={"updated_fields": sorted(changes.keys())},
    )
    return {"success": True, "data": _serialize_search_profile(row)}


def list_connectors(
    db: Session,
    tenant_id: str,
    current_user: dict | None = None,
) -> dict[str, Any]:
    ensure_builtin_search_providers(db)
    ensure_fixture_connector(db, tenant_id, current_user)
    ensure_web_search_connector(db, tenant_id, current_user)
    ensure_ted_connector(db, tenant_id, current_user)
    ensure_freelancer_connector(db, tenant_id, current_user)
    ensure_remoteok_connector(db, tenant_id, current_user)
    ensure_arbeitnow_connector(db, tenant_id, current_user)
    ensure_remotive_connector(db, tenant_id, current_user)
    ensure_adzuna_connector(db, tenant_id, current_user)
    ensure_independent_web_connector(db, tenant_id, current_user)
    rows = (
        db.query(BusinessDevelopmentConnector)
        .filter(BusinessDevelopmentConnector.tenant_id == tenant_id)
        .order_by(BusinessDevelopmentConnector.created_at.asc())
        .all()
    )
    today_start = datetime.combine(_now().date(), datetime.min.time(), tzinfo=timezone.utc)
    today_discoveries = (
        db.query(func.count(BusinessDevelopmentDiscoveredOpportunity.id))
        .filter(
            BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id,
            BusinessDevelopmentDiscoveredOpportunity.created_at >= today_start,
        )
        .scalar()
        or 0
    )
    new_discoveries = (
        db.query(func.count(BusinessDevelopmentDiscoveredOpportunity.id))
        .filter(
            BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id,
            BusinessDevelopmentDiscoveredOpportunity.discovery_status == "new",
        )
        .scalar()
        or 0
    )
    failed_window_start = _now() - timedelta(days=1)
    failed_runs = (
        db.query(func.count(BusinessDevelopmentConnectorRun.id))
        .filter(
            BusinessDevelopmentConnectorRun.tenant_id == tenant_id,
            BusinessDevelopmentConnectorRun.status == "failed",
            BusinessDevelopmentConnectorRun.started_at >= failed_window_start,
        )
        .scalar()
        or 0
    )
    latest_run = (
        db.query(BusinessDevelopmentConnectorRun)
        .filter(BusinessDevelopmentConnectorRun.tenant_id == tenant_id)
        .order_by(BusinessDevelopmentConnectorRun.started_at.desc())
        .first()
    )
    serialized_rows = [_serialize_connector(row) for row in rows]
    summary = {
        "active_connectors": sum(1 for row in serialized_rows if row["enabled"] and row["status"] in {"ready", "running", "configured"}),
        "last_scan": _serialize_datetime(latest_run.started_at) if latest_run else None,
        "discoveries_today": today_discoveries,
        "new_discoveries": new_discoveries,
        "failed_runs": failed_runs,
    }
    return {"success": True, "data": serialized_rows, "summary": summary}


def create_connector(
    db: Session,
    tenant_id: str,
    current_user: dict,
    payload: AugmisBusinessConnectorCreateRequest,
) -> dict[str, Any]:
    implementation = _get_connector_implementation(payload.connector_type)
    implementation.validate_config(payload.configuration_json)
    if payload.connector_type == WEB_SEARCH_CONNECTOR_TYPE:
        resolve_search_provider_by_code(
            db,
            tenant_id,
            str((payload.configuration_json or {}).get("provider", "tavily") or "tavily"),
        )
    if payload.search_profile_id:
        _require_search_profile(db, tenant_id, payload.search_profile_id)
    _validate_schedule_configuration(
        schedule_enabled=payload.schedule_enabled,
        schedule_type=payload.schedule_type,
        schedule_interval_minutes=payload.schedule_interval_minutes,
        schedule_day_of_week=payload.schedule_day_of_week,
        schedule_time_local=payload.schedule_time_local,
        schedule_timezone=payload.schedule_timezone,
    )
    effective_now = _now()
    row = BusinessDevelopmentConnector(
        id=f"BD-CNX-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        created_by=current_user["user_id"],
        status="ready" if payload.enabled else "disabled",
        updated_at=effective_now,
        **payload.model_dump(),
    )
    _apply_schedule_defaults(
        row,
        schedule_enabled=payload.schedule_enabled,
        schedule_type=payload.schedule_type,
        schedule_interval_minutes=payload.schedule_interval_minutes,
        schedule_day_of_week=payload.schedule_day_of_week,
        schedule_time_local=payload.schedule_time_local,
        schedule_timezone=payload.schedule_timezone,
        effective_now=effective_now,
    )
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Connector conflicts with an existing tenant record")
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="CREATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Created connector {row.name}",
        resource_type="bd_connector",
        resource_id=row.id,
        metadata={"connector_type": row.connector_type},
    )
    return {"success": True, "data": _serialize_connector(row)}


def get_connector(db: Session, tenant_id: str, connector_id: str) -> dict[str, Any]:
    row = _require_connector(db, tenant_id, connector_id)
    return {"success": True, "data": _serialize_connector(row)}


def update_connector(
    db: Session,
    tenant_id: str,
    connector_id: str,
    current_user: dict,
    payload: AugmisBusinessConnectorUpdateRequest,
) -> dict[str, Any]:
    row = _require_connector(db, tenant_id, connector_id)
    changes = payload.model_dump(exclude_unset=True)
    if "search_profile_id" in changes and changes["search_profile_id"]:
        _require_search_profile(db, tenant_id, changes["search_profile_id"])
    if "configuration_json" in changes:
        _get_connector_implementation(row.connector_type).validate_config(changes["configuration_json"])
        if row.connector_type == WEB_SEARCH_CONNECTOR_TYPE:
            resolve_search_provider_by_code(
                db,
                tenant_id,
                str((changes["configuration_json"] or {}).get("provider", "tavily") or "tavily"),
            )
    old_schedule = {
        "schedule_enabled": row.schedule_enabled,
        "schedule_type": row.schedule_type,
        "schedule_interval_minutes": row.schedule_interval_minutes,
        "schedule_day_of_week": row.schedule_day_of_week,
        "schedule_time_local": row.schedule_time_local,
        "schedule_timezone": _schedule_timezone_name(row.schedule_timezone),
        "next_run_at": _serialize_datetime(row.next_run_at),
    }
    for key, value in changes.items():
        setattr(row, key, value)
    effective_now = _now()
    schedule_enabled = changes.get("schedule_enabled", row.schedule_enabled)
    schedule_type = changes.get("schedule_type", row.schedule_type)
    schedule_interval_minutes = changes.get("schedule_interval_minutes", row.schedule_interval_minutes)
    schedule_day_of_week = changes.get("schedule_day_of_week", row.schedule_day_of_week)
    schedule_time_local = changes.get("schedule_time_local", row.schedule_time_local)
    schedule_timezone = changes.get("schedule_timezone", row.schedule_timezone)
    _validate_schedule_configuration(
        schedule_enabled=bool(schedule_enabled),
        schedule_type=str(schedule_type or "manual"),
        schedule_interval_minutes=schedule_interval_minutes,
        schedule_day_of_week=schedule_day_of_week,
        schedule_time_local=schedule_time_local,
        schedule_timezone=schedule_timezone,
    )
    _apply_schedule_defaults(
        row,
        schedule_enabled=bool(schedule_enabled),
        schedule_type=str(schedule_type or "manual"),
        schedule_interval_minutes=schedule_interval_minutes,
        schedule_day_of_week=schedule_day_of_week,
        schedule_time_local=schedule_time_local,
        schedule_timezone=schedule_timezone,
        effective_now=effective_now,
    )
    if "schedule_enabled" in changes or "schedule_type" in changes or "schedule_interval_minutes" in changes or "schedule_day_of_week" in changes or "schedule_time_local" in changes or "schedule_timezone" in changes:
        row.schedule_updated_by = current_user["user_id"]
        row.schedule_updated_at = effective_now
    if "enabled" in changes:
        row.status = "ready" if row.enabled and row.active_run_id is None else "disabled"
    elif row.active_run_id is None:
        row.status = "ready" if row.enabled else "disabled"
    row.updated_at = effective_now
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Connector conflicts with an existing tenant record")
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated connector {row.name}",
        resource_type="bd_connector",
        resource_id=row.id,
        metadata={
            "updated_fields": sorted(changes.keys()),
            "old_schedule": old_schedule,
            "new_schedule": {
                "schedule_enabled": row.schedule_enabled,
                "schedule_type": row.schedule_type,
                "schedule_interval_minutes": row.schedule_interval_minutes,
                "schedule_day_of_week": row.schedule_day_of_week,
                "schedule_time_local": row.schedule_time_local,
                "schedule_timezone": row.schedule_timezone,
                "next_run_at": _serialize_datetime(row.next_run_at),
            },
        },
    )
    return {"success": True, "data": _serialize_connector(row)}


def set_connector_provider(
    db: Session,
    tenant_id: str,
    connector_id: str,
    current_user: dict,
    provider_code: str,
) -> dict[str, Any]:
    row = _require_connector(db, tenant_id, connector_id)
    if row.connector_type != WEB_SEARCH_CONNECTOR_TYPE:
        raise HTTPException(status_code=400, detail="Provider selection is not supported for this connector.")
    provider = resolve_search_provider_by_code(db, tenant_id, provider_code)
    row.configuration_json = {**(row.configuration_json or {}), "provider": provider.provider_code}
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Changed connector provider for {row.name}",
        resource_type="bd_connector",
        resource_id=row.id,
        metadata={"provider_code": provider.provider_code},
    )
    return {"success": True, "data": _serialize_connector(row)}


def test_connector(
    db: Session,
    tenant_id: str,
    current_user: dict,
    connector_id: str,
) -> dict[str, Any]:
    row = _require_connector(db, tenant_id, connector_id)
    provider_name = str((row.configuration_json or {}).get("provider", "tavily") or "tavily")
    result = (
        test_connector_credential(db, tenant_id, provider_name, current_user)["data"]["result"]
        if row.connector_type in {WEB_SEARCH_CONNECTOR_TYPE, FREELANCER_CONNECTOR_TYPE, ADZUNA_CONNECTOR_TYPE}
        else _get_connector_implementation(row.connector_type).test_connection(row.configuration_json or {})
    )
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="TEST",
        event_category="AUGMIS_BUSINESS",
        description=f"Tested connector {row.name}",
        resource_type="bd_connector",
        resource_id=row.id,
        metadata={"connector_type": row.connector_type, "success": result.get("success")},
    )
    return {"success": True, "data": {"connector": _serialize_connector(row), "result": result}}


def list_connector_runs(
    db: Session,
    tenant_id: str,
    connector_id: str,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    _require_connector(db, tenant_id, connector_id)
    query = db.query(BusinessDevelopmentConnectorRun).filter(
        BusinessDevelopmentConnectorRun.tenant_id == tenant_id,
        BusinessDevelopmentConnectorRun.connector_id == connector_id,
    )
    total = query.count()
    rows = (
        query.order_by(BusinessDevelopmentConnectorRun.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "success": True,
        "data": [_serialize_connector_run(row) for row in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": ceil(total / page_size) if total else 1,
        },
    }


def get_connector_run(
    db: Session,
    tenant_id: str,
    connector_id: str,
    run_id: str,
) -> dict[str, Any]:
    _require_connector(db, tenant_id, connector_id)
    row = (
        db.query(BusinessDevelopmentConnectorRun)
        .filter(
            BusinessDevelopmentConnectorRun.tenant_id == tenant_id,
            BusinessDevelopmentConnectorRun.connector_id == connector_id,
            BusinessDevelopmentConnectorRun.id == run_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Connector run not found.")
    return {"success": True, "data": _serialize_connector_run(row)}


def stop_connector_run(
    db: Session,
    tenant_id: str,
    connector_id: str,
    run_id: str,
    current_user: dict,
) -> dict[str, Any]:
    connector = _require_connector(db, tenant_id, connector_id)
    run = (
        db.query(BusinessDevelopmentConnectorRun)
        .filter(
            BusinessDevelopmentConnectorRun.tenant_id == tenant_id,
            BusinessDevelopmentConnectorRun.connector_id == connector_id,
            BusinessDevelopmentConnectorRun.id == run_id,
        )
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Connector run not found.")
    if run.status not in ACTIVE_CONNECTOR_RUN_STATUSES:
        raise HTTPException(status_code=409, detail=f"Connector run is already {run.status}.")
    message = "Connector scan was stopped by operator."
    run.status = "cancelled"
    run.completed_at = _now()
    run.error_summary = message
    run.run_metadata_json = _run_stop_metadata(connector=connector, run=run, message=message)
    if connector.active_run_id == run.id:
        connector.active_run_id = None
    connector.status = "ready" if connector.enabled else "disabled"
    connector.last_error_message = None
    db.commit()
    db.refresh(run)
    db.refresh(connector)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="RUN",
        event_category="AUGMIS_BUSINESS",
        description=f"Stopped connector scan for {connector.name}",
        resource_type="bd_connector_run",
        resource_id=run.id,
        metadata={"connector_id": connector.id, "status": run.status},
    )
    return {"success": True, "data": {"connector": _serialize_connector(connector), "run": _serialize_connector_run(run)}}


def _find_duplicate(
    db: Session,
    tenant_id: str,
    connector_id: str,
    candidate: AugmisBusinessDiscoveredOpportunityCandidate,
    canonical_url: str | None,
    source_domain: str | None,
) -> tuple[BusinessDevelopmentDiscoveredOpportunity | None, str | None]:
    if candidate.external_id:
        existing = (
            db.query(BusinessDevelopmentDiscoveredOpportunity)
            .filter(
                BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id,
                BusinessDevelopmentDiscoveredOpportunity.connector_id == connector_id,
                BusinessDevelopmentDiscoveredOpportunity.external_id == candidate.external_id,
            )
            .first()
        )
        if existing:
            return existing, "external_id"
    if canonical_url:
        existing = (
            db.query(BusinessDevelopmentDiscoveredOpportunity)
            .filter(
                BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id,
                BusinessDevelopmentDiscoveredOpportunity.canonical_source_url == canonical_url,
            )
            .order_by(BusinessDevelopmentDiscoveredOpportunity.created_at.asc())
            .first()
        )
        if existing:
            return existing, "canonical_url"
    composite = _fingerprint(
        _normalize_text(candidate.organization_name),
        _normalize_title(candidate.title),
        candidate.closing_date.date().isoformat() if candidate.closing_date else None,
        source_domain,
    )
    if composite:
        existing = (
            db.query(BusinessDevelopmentDiscoveredOpportunity)
            .filter(
                BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id,
                BusinessDevelopmentDiscoveredOpportunity.composite_fingerprint == composite,
            )
            .order_by(BusinessDevelopmentDiscoveredOpportunity.created_at.asc())
            .first()
        )
        if existing:
            return existing, "composite"
    return None, None


def _external_work_candidate(opportunity: ExternalWorkOpportunity) -> AugmisBusinessDiscoveredOpportunityCandidate:
    description = (opportunity.description or "")[:4000]
    tags = [tag for tag in opportunity.tags if tag]
    skills = [skill for skill in opportunity.skills if skill]
    remote_label = "Remote" if opportunity.remote else "On-site / hybrid"
    return AugmisBusinessDiscoveredOpportunityCandidate(
        external_id=opportunity.external_id,
        source_type=EMPLOYMENT_CONTRACT_SOURCE_TYPE,
        source_name=opportunity.source_name,
        source_url=opportunity.source_url,
        source_country=opportunity.country,
        title=opportunity.title,
        organization_name=opportunity.company_name or "Employer",
        published_date=opportunity.posted_at,
        closing_date=opportunity.expires_at,
        country=opportunity.country,
        region=opportunity.location or opportunity.region,
        industry=opportunity.category,
        requirement_summary=description or opportunity.title,
        raw_summary=description[:1000] or opportunity.title,
        raw_text=" ".join(
            part
            for part in [
                opportunity.title,
                opportunity.description or "",
                " ".join(tags),
                " ".join(skills),
                opportunity.category or "",
                opportunity.employment_type or "",
                opportunity.engagement_type or "",
            ]
            if part
        )[:20000],
        budget_min=opportunity.salary_min,
        budget_max=opportunity.salary_max,
        currency=opportunity.salary_currency,
        evidence=[
            {"type": "provider", "value": opportunity.source_name},
            {"type": "external_id", "value": opportunity.external_id},
            {"type": "remote", "value": remote_label},
        ],
        source_metadata={
            "provider": opportunity.provider,
            "opportunity_class": "employment_contract",
            "engagement_type": opportunity.engagement_type,
            "employment_type": opportunity.employment_type,
            "remote": opportunity.remote,
            "location": opportunity.location,
            "company_name": opportunity.company_name,
            "company_url": opportunity.company_url,
            "salary_period": opportunity.salary_period,
            "category": opportunity.category,
            "tags": tags,
            "skills": skills,
            "source_trust": "official_public_api",
        },
        raw_content_json={
            "provider": opportunity.provider,
            "external_id": opportunity.external_id,
            "provider_url": opportunity.source_url,
            "company_name": opportunity.company_name,
            "company_url": opportunity.company_url,
            "location": opportunity.location,
            "remote": opportunity.remote,
            "engagement_type": opportunity.engagement_type,
            "employment_type": opportunity.employment_type,
            "salary_period": opportunity.salary_period,
            "category": opportunity.category,
            "tags": tags,
            "skills": skills,
            "provider_result": opportunity.raw_payload,
        },
        retrieval_timestamp=_now(),
    )


def _calculate_preliminary_relevance(
    candidate: AugmisBusinessDiscoveredOpportunityCandidate,
    profile: BusinessDevelopmentSearchProfile | None,
) -> tuple[float, list[str], list[str]]:
    if candidate.source_type == "public_procurement":
        raw = candidate.raw_content_json or candidate.source_metadata or {}
        if candidate.source_name == INDEPENDENT_WEB_CONNECTOR_NAME or raw.get("provider") == "augmis_internal":
            return _calculate_independent_procurement_preliminary_relevance(candidate, profile)
        return _calculate_ted_preliminary_relevance(candidate)
    if candidate.source_type == "marketplace_project":
        return _calculate_freelancer_preliminary_relevance(candidate, profile)
    if candidate.source_type == EMPLOYMENT_CONTRACT_SOURCE_TYPE:
        return _calculate_external_work_preliminary_relevance(candidate, profile)

    searchable = _searchable_text(candidate)
    if not searchable:
        return 0.0, ["No searchable discovery text available."], []
    include_terms = set()
    exclude_terms = set()
    industries = set()
    countries = set()
    if profile:
        include_terms.update(_normalize_text(item) for item in (profile.include_keywords_json or []) if _normalize_text(item))
        include_terms.update(_normalize_text(item) for item in (profile.include_technologies_json or []) if _normalize_text(item))
        include_terms.update(_normalize_text(item) for item in (profile.include_capabilities_json or []) if _normalize_text(item))
        exclude_terms.update(_normalize_text(item) for item in (profile.exclude_keywords_json or []) if _normalize_text(item))
        industries.update(_normalize_text(item) for item in (profile.target_industries_json or []) if _normalize_text(item))
        countries.update(_normalize_text(item) for item in (profile.target_countries_json or []) if _normalize_text(item))
    matched_terms = sorted(term for term in include_terms if term in searchable)
    reasons: list[str] = []
    score = 20.0
    if matched_terms:
        score += min(55.0, len(matched_terms) * 9.0)
        reasons.append(f"Matched {len(matched_terms)} configured capability terms.")
    if industries and _normalize_text(candidate.industry) in industries:
        score += 10.0
        reasons.append("Industry matches the active search profile.")
    if countries and _normalize_text(candidate.country) in countries:
        score += 10.0
        reasons.append("Country matches the active search profile.")
    if profile and profile.minimum_budget is not None:
        if candidate.budget_max is None and not profile.allow_budget_unknown:
            score = max(0.0, score - 25.0)
            reasons.append("Budget is unknown and the active profile requires a known budget.")
        elif candidate.budget_max is not None and candidate.budget_max < profile.minimum_budget:
            score = max(0.0, score - 20.0)
            reasons.append("Published budget is below the configured threshold.")
    excluded_hits = sorted(term for term in exclude_terms if term in searchable)
    if excluded_hits:
        score = max(0.0, score - min(45.0, len(excluded_hits) * 15.0))
        reasons.append("Excluded terms were detected in the source content.")
    return round(max(0.0, min(100.0, score)), 1), reasons, matched_terms


def _calculate_independent_procurement_preliminary_relevance(
    candidate: AugmisBusinessDiscoveredOpportunityCandidate,
    profile: BusinessDevelopmentSearchProfile | None,
) -> tuple[float, list[str], list[str]]:
    score, reasons, matched = _calculate_ted_preliminary_relevance(candidate)
    raw = candidate.raw_content_json or candidate.source_metadata or {}
    crawler = raw.get("crawler_diagnostics") if isinstance(raw.get("crawler_diagnostics"), dict) else {}
    page_type = str(raw.get("page_type") or candidate.source_metadata.get("opportunity_class") or "").lower()
    detail_signal_count = int(crawler.get("detail_signal_count", 0) or 0)
    contact_routes = raw.get("contact_routes") if isinstance(raw.get("contact_routes"), list) else []
    searchable = _searchable_text(candidate)
    if page_type in {"procurement_detail", "rfp", "rfq", "eoi"}:
        score += 12.0 + min(8.0, detail_signal_count * 2.0)
        reasons.append("Matched signal: Independent crawl captured a procurement-detail page with explicit notice structure.")
    elif page_type == "tender":
        score += 6.0 + min(6.0, detail_signal_count * 2.0)
        reasons.append("Matched signal: Independent crawl captured a tender page with usable notice structure.")
    if raw.get("reference_number"):
        score += 4.0
        reasons.append("Matched signal: Reference number was extracted from the source page.")
    if raw.get("application_url"):
        score += 4.0
        reasons.append("Matched signal: Application or submission route was detected.")
    if candidate.closing_date:
        score += 4.0
        reasons.append("Matched signal: Closing date was extracted from the page.")
    if contact_routes:
        score += min(3.0, float(len(contact_routes)))
        reasons.append("Matched signal: Official contact routes were extracted from the source page.")
    if profile:
        include_terms = sorted(
            {
                _normalize_text(item)
                for item in [
                    *(profile.include_keywords_json or []),
                    *(profile.include_technologies_json or []),
                    *(profile.include_capabilities_json or []),
                ]
                if _normalize_text(item)
            }
        )
        exclude_terms = sorted({_normalize_text(item) for item in (profile.exclude_keywords_json or []) if _normalize_text(item)})
        matched_terms = [term for term in include_terms if term in searchable]
        excluded_hits = [term for term in exclude_terms if term in searchable]
        if matched_terms:
            score += min(18.0, float(len(matched_terms)) * 4.0)
            reasons.append("Matched signal: tenant profile capability terms were found in the independent procurement notice.")
            matched.extend(matched_terms[:5])
        if excluded_hits:
            score -= min(45.0, float(len(excluded_hits)) * 15.0)
            reasons.append("Negative signal: tenant profile excluded terms were found in the independent procurement notice.")
    return round(max(0.0, min(100.0, score)), 1), reasons, list(dict.fromkeys(matched))


EXTERNAL_WORK_TECH_TERMS = ("python", "fastapi", "node", "react", "next.js", "postgresql", ".net", "api", "ai", "openai", "automation")
EXTERNAL_WORK_DOMAIN_TERMS = ("workflow", "document management", "records management", "inspection", "dashboard", "analytics", "enterprise", "integration", "portal", "case management", "digital transformation")
EXTERNAL_WORK_CONTRACT_TERMS = ("contract", "freelance", "consulting", "part-time", "project", "remote")
EXTERNAL_WORK_NEGATIVE_TERMS = ("sales", "telemarketing", "customer service", "recruiting", "hr", "manual data entry", "content writing", "social media marketing", "seo", "graphic design", "warehouse", "driving", "logistics")


def _calculate_external_work_preliminary_relevance(
    candidate: AugmisBusinessDiscoveredOpportunityCandidate,
    profile: BusinessDevelopmentSearchProfile | None,
) -> tuple[float, list[str], list[str]]:
    searchable = _searchable_text(candidate)
    metadata = candidate.source_metadata or {}
    score = 10.0
    reasons: list[str] = []
    matched: list[str] = []

    tech_hits = [term for term in EXTERNAL_WORK_TECH_TERMS if term in searchable]
    if tech_hits:
        score += min(35.0, 10.0 + (len(tech_hits) * 5.0))
        reasons.append("Matched signal: technical stack evidence detected.")
        matched.extend(tech_hits[:5])

    domain_hits = [term for term in EXTERNAL_WORK_DOMAIN_TERMS if term in searchable]
    if domain_hits:
        score += min(25.0, 10.0 + (len(domain_hits) * 4.0))
        reasons.append("Matched signal: AUGMIS business domain evidence detected.")
        matched.extend(domain_hits[:4])

    engagement_text = " ".join(
        part for part in [str(metadata.get("engagement_type") or ""), str(metadata.get("employment_type") or ""), searchable] if part
    )
    engagement_hits = [term for term in EXTERNAL_WORK_CONTRACT_TERMS if term in engagement_text]
    if engagement_hits:
        score += min(15.0, 8.0 + (len(engagement_hits) * 2.5))
        reasons.append("Matched signal: contract / remote engagement is commercially suitable.")
    elif "full_time" in engagement_text or "full-time" in engagement_text:
        score += 4.0
        reasons.append("Full-time technical role retained as a possible business-development target.")

    if candidate.budget_min is not None or candidate.budget_max is not None:
        score += 7.0
        reasons.append("Compensation details were available.")

    if metadata.get("remote"):
        score += 5.0
        reasons.append("Remote delivery suitability detected.")

    if candidate.published_date:
        age_days = (_now() - candidate.published_date).total_seconds() / 86400
        if age_days <= 3:
            score += 10.0
            reasons.append("Fresh posting detected.")
        elif age_days <= 10:
            score += 6.0
            reasons.append("Recently posted opportunity detected.")

    if profile:
        include_terms = [
            _normalize_text(item)
            for item in (profile.include_keywords_json or []) + (profile.include_technologies_json or []) + (profile.include_capabilities_json or [])
            if _normalize_text(item)
        ]
        profile_hits = [term for term in include_terms if term in searchable]
        if profile_hits:
            score += min(12.0, len(profile_hits) * 3.0)
            reasons.append("Matched signal: tenant search-profile terms detected.")
            matched.extend(profile_hits[:4])

    negative_hits = [term for term in EXTERNAL_WORK_NEGATIVE_TERMS if term in searchable]
    if negative_hits:
        score -= min(40.0, 10.0 + (len(negative_hits) * 6.0))
        reasons.append("Negative signal: non-target employment pattern detected.")

    score = round(max(0.0, min(100.0, score)), 1)
    return score, reasons, sorted(set(matched))


def _calculate_ted_preliminary_relevance(
    candidate: AugmisBusinessDiscoveredOpportunityCandidate,
) -> tuple[float, list[str], list[str]]:
    title_text, body_text = _ted_title_and_body(candidate)
    searchable = " ".join(part for part in [title_text, body_text] if part)
    cpv_codes = _ted_candidate_cpv_codes(candidate)
    high_cpv_hits = sorted(code for code in cpv_codes if code in TED_HIGH_RELEVANCE_CPV)
    medium_cpv_hits = sorted(code for code in cpv_codes if code in TED_MEDIUM_RELEVANCE_CPV)
    low_cpv_hits = sorted(code for code in cpv_codes if code in TED_LOW_RELEVANCE_CPV)

    score = 5.0
    reasons: list[str] = []
    matched_signals: list[str] = []

    if high_cpv_hits:
        score += 34.0 + min(10.0, max(0, len(high_cpv_hits) - 1) * 4.0)
        reasons.append("Matched signal: High-relevance software / IT CPV detected.")
        matched_signals.extend(high_cpv_hits[:4])
        if medium_cpv_hits:
            score += min(6.0, len(medium_cpv_hits) * 3.0)
            reasons.append("Matched signal: Supporting medium-relevance digital CPV detected.")
    elif medium_cpv_hits:
        score += 20.0 + min(6.0, max(0, len(medium_cpv_hits) - 1) * 3.0)
        reasons.append("Matched signal: Medium-relevance digital / IT CPV detected.")
        matched_signals.extend(medium_cpv_hits[:4])

    digital_title_signal = False
    digital_body_signal = False
    dimension_matches = 0
    for dimension in TED_POSITIVE_DIMENSIONS:
        title_hit = _contains_any(title_text, dimension["title_terms"])
        body_hit = _contains_any(body_text, dimension["body_terms"])
        if title_hit:
            score += dimension["title_weight"]
            reasons.append(f"Matched signal: {dimension['name']} is explicit in the title.")
            matched_signals.append(dimension["name"])
            dimension_matches += 1
            digital_title_signal = True
            if body_hit:
                score += max(2.0, dimension["body_weight"] - 1.0)
                reasons.append(f"Matched signal: {dimension['name']} is reinforced in the notice detail.")
        elif body_hit:
            score += dimension["body_weight"]
            reasons.append(f"Matched signal: {dimension['name']} is supported by the notice detail.")
            matched_signals.append(dimension["name"])
            dimension_matches += 1
            digital_body_signal = True

    if candidate.organization_name and _contains_any_phrase(_normalize_text(candidate.organization_name) or "", TED_BUYER_QUALITY_TERMS):
        score += 5.0
        reasons.append("Matched signal: Buyer appears to be a public-sector or institutional organisation.")

    structured = candidate.raw_content_json or candidate.source_metadata or {}
    contract_nature = " ".join(str(item).lower() for item in (structured.get("contract_nature") or [])) if isinstance(structured.get("contract_nature"), list) else str(structured.get("contract_nature") or "").lower()
    notice_type = str(structured.get("notice_type") or "").lower()
    if "service" in contract_nature:
        score += 5.0
        reasons.append("Matched signal: Structured procurement metadata indicates a service-oriented opportunity.")
    elif structured.get("procedure_type") and dimension_matches >= 1:
        score += 2.0
        reasons.append("Matched signal: Structured procurement metadata supports a scoped digital delivery.")
    if _contains_any_phrase(searchable, BUYING_INTENT_TERMS):
        score += 5.0
        reasons.append("Matched signal: Buyer procurement intent is explicit in the notice.")

    if high_cpv_hits and dimension_matches >= 2:
        score += 8.0
        reasons.append("Matched signal: Multiple digital solution signals align across CPV and notice language.")
    elif high_cpv_hits and dimension_matches >= 1:
        score += 4.0
        reasons.append("Matched signal: CPV evidence is reinforced by notice wording.")
    elif len(high_cpv_hits) >= 2 and medium_cpv_hits:
        score += 6.0
        reasons.append("Matched signal: Multiple digital CPVs support cross-language relevance.")

    strong_digital_evidence = bool(high_cpv_hits or (digital_title_signal and dimension_matches >= 1) or dimension_matches >= 3)
    for rule in TED_NEGATIVE_SIGNAL_RULES:
        cpv_rule_hit = any(code in low_cpv_hits for code in rule["cpv_codes"])
        text_rule_hit = _contains_any_phrase(title_text, rule["terms"]) or _contains_any_phrase(body_text, rule["terms"])
        if not (cpv_rule_hit or text_rule_hit):
            continue
        penalty = rule["penalty"] / 2 if strong_digital_evidence else rule["penalty"]
        score -= penalty
        reasons.append(f"Negative signal: {rule['name']} reduces commercial fit.")

    if low_cpv_hits and not (high_cpv_hits or medium_cpv_hits):
        penalty = 8.0 if strong_digital_evidence else 14.0
        score -= penalty
        reasons.append("Negative signal: CPV profile is primarily outside software / digital delivery.")

    closing_status = _ted_closing_status(candidate.closing_date)
    if closing_status == "expired":
        score -= 18.0
        reasons.append("Negative signal: Opportunity is already expired.")
    elif closing_status == "closing_soon":
        reasons.append("Matched signal: Opportunity is still open but closing soon.")
    elif closing_status == "unknown":
        reasons.append("Matched signal: Closing date is not published.")

    final_score = round(max(0.0, min(100.0, score)), 1)
    if not reasons:
        reasons.append("Negative signal: No strong digital relevance signals were detected.")
    deduped_signals = list(dict.fromkeys(matched_signals))
    return final_score, reasons, deduped_signals


def _refresh_existing_discovery_from_candidate(
    row: BusinessDevelopmentDiscoveredOpportunity,
    candidate: AugmisBusinessDiscoveredOpportunityCandidate,
    *,
    canonical_url: str | None,
    source_domain: str | None,
    relevance_score: float,
    relevance_reasons: list[str],
    matched_keywords: list[str],
) -> None:
    normalized_requirement, normalized_summary, normalized_full_text, normalized_content = _normalized_content_payload(
        candidate.requirement_summary,
        candidate.raw_summary,
        candidate.raw_text,
    )
    row.source_url = _clean_text(candidate.source_url)
    row.canonical_source_url = canonical_url
    row.source_domain = source_domain
    row.source_country = _normalize_country_or_region(candidate.source_country)
    row.title = _clean_text(candidate.title) or candidate.title
    row.normalized_title = _normalize_title(candidate.title)
    row.organization_name = _clean_text(candidate.organization_name)
    row.normalized_organization_name = _normalize_text(candidate.organization_name)
    row.published_date = candidate.published_date
    row.closing_date = candidate.closing_date
    row.raw_summary = normalized_summary
    row.requirement_summary = normalized_requirement
    row.normalized_content_json = normalized_content
    row.raw_content_json = candidate.raw_content_json or candidate.source_metadata or {}
    row.raw_text = normalized_full_text
    row.country = _normalize_country_or_region(candidate.country)
    row.region = _normalize_country_or_region(candidate.region)
    row.industry = _clean_text(candidate.industry)
    row.budget_min = candidate.budget_min
    row.budget_max = candidate.budget_max
    row.currency = _clean_text(candidate.currency)
    row.retrieval_timestamp = candidate.retrieval_timestamp or _now()
    row.preliminary_relevance_score = relevance_score
    row.relevance_reasons_json = relevance_reasons
    row.matched_keywords_json = matched_keywords
    row.evidence_json = candidate.evidence or []
    row.normalized_search_text = _searchable_text(candidate)
    row.url_fingerprint = _fingerprint(canonical_url)
    row.composite_fingerprint = _fingerprint(
        row.normalized_organization_name,
        row.normalized_title,
        candidate.closing_date.date().isoformat() if candidate.closing_date else None,
        source_domain,
    )
    row.raw_content_json = {
        **(candidate.raw_content_json or candidate.source_metadata or {}),
        "source_metadata": dict(candidate.source_metadata or {}),
        "opportunity_validity": _opportunity_validity_payload(candidate),
    }
    session = object_session(row)
    if session is not None:
        _apply_validity_to_discovery_row(session, row)
    else:
        row.updated_at = _now()


def _update_independent_page_candidate_decision(
    db: Session,
    *,
    tenant_id: str,
    connector_id: str,
    canonical_url: str | None,
    page_type: str | None,
    decision: str,
    reason_codes: list[str],
    validity: dict[str, Any] | None = None,
) -> None:
    if not canonical_url:
        return
    page = (
        db.query(BusinessDevelopmentWebPage)
        .filter(
            BusinessDevelopmentWebPage.tenant_id == tenant_id,
            BusinessDevelopmentWebPage.connector_id == connector_id,
            BusinessDevelopmentWebPage.canonical_url == canonical_url,
        )
        .first()
    )
    if page is None:
        return
    source_metadata = dict(page.source_metadata_json or {})
    source_metadata["candidate_decision"] = {
        "decision": decision,
        "page_type": page_type,
        "reason_codes": list(dict.fromkeys(reason_codes))[:8],
        "opportunity_validity": dict(validity or {}),
    }
    page.source_metadata_json = source_metadata
    candidate_payload = dict(page.opportunity_candidate_json or {})
    candidate_payload["candidate_decision"] = source_metadata["candidate_decision"]
    page.opportunity_candidate_json = candidate_payload


def ingest_discovered_opportunity(
    db: Session,
    tenant_id: str,
    connector: BusinessDevelopmentConnector,
    connector_run: BusinessDevelopmentConnectorRun,
    candidate: AugmisBusinessDiscoveredOpportunityCandidate,
    search_profile: BusinessDevelopmentSearchProfile | None,
) -> IngestionOutcome:
    normalized_requirement, normalized_summary, normalized_full_text, normalized_content = _normalized_content_payload(
        candidate.requirement_summary,
        candidate.raw_summary,
        candidate.raw_text,
    )
    candidate = candidate.model_copy(
        update={
            "requirement_summary": normalized_requirement,
            "raw_summary": normalized_summary,
            "raw_text": normalized_full_text,
        }
    )
    canonical_url, source_domain = _normalize_url(candidate.source_url)
    normalized_title = _normalize_title(candidate.title)
    normalized_organization_name = _normalize_text(candidate.organization_name)
    validity = _opportunity_validity_payload(candidate)
    validity_reason_codes = [str(code) for code in validity.get("reason_codes") or [] if _clean_text(str(code))]
    duplicate_of, duplicate_reason = _find_duplicate(
        db,
        tenant_id,
        connector.id,
        candidate,
        canonical_url,
        source_domain,
    )
    relevance_score, relevance_reasons, matched_keywords = _calculate_preliminary_relevance(
        candidate,
        search_profile,
    )
    candidate_raw_content = dict(candidate.raw_content_json or candidate.source_metadata or {})
    candidate_diagnostics = candidate_raw_content.get("crawler_diagnostics") if isinstance(candidate_raw_content.get("crawler_diagnostics"), dict) else {}
    candidate_raw_content["source_metadata"] = dict(candidate.source_metadata or {})
    candidate_raw_content["opportunity_validity"] = validity
    discovery_status = "new"
    duplicate_of_id = None
    outcome_reason_codes: list[str] = []
    if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE and not validity.get("eligible_for_inbox"):
        outcome_reason_codes.append(_validity_filter_reason(validity))
        outcome_reason_codes.extend(validity_reason_codes)
        candidate_raw_content["crawler_diagnostics"] = {
            **candidate_diagnostics,
            "discovery_status": "irrelevant",
            "reason_codes": list(dict.fromkeys(outcome_reason_codes))[:8],
            "relevance_score": relevance_score,
            "validity_score": validity.get("validity_score"),
            "validity_class": validity.get("validity_class"),
        }
        connector_run.items_filtered += 1
        connector_run.items_found += 1
        _update_independent_page_candidate_decision(
            db,
            tenant_id=tenant_id,
            connector_id=connector.id,
            canonical_url=canonical_url,
            page_type=str(candidate_raw_content.get("page_type") or ""),
            decision="validity_rejected",
            reason_codes=outcome_reason_codes,
            validity=validity,
        )
        run_metadata = dict(connector_run.run_metadata_json or {})
        filter_reason_counts = dict(run_metadata.get("filter_reason_counts") or {})
        for code in list(dict.fromkeys(outcome_reason_codes))[:8]:
            filter_reason_counts[code] = int(filter_reason_counts.get(code, 0) or 0) + 1
        candidate_outcomes = list(run_metadata.get("candidate_outcomes") or [])
        candidate_outcomes.append(
            {
                "title": candidate.title,
                "source_url": candidate.source_url,
                "page_type": str(candidate_raw_content.get("page_type") or ""),
                "discovery_status": "irrelevant",
                "relevance_score": relevance_score,
                "reason_codes": list(dict.fromkeys(outcome_reason_codes))[:8],
                "validity_score": validity.get("validity_score"),
                "validity_class": validity.get("validity_class"),
            }
        )
        run_metadata["filter_reason_counts"] = filter_reason_counts
        run_metadata["candidate_outcomes"] = candidate_outcomes[-20:]
        connector_run.run_metadata_json = run_metadata
        return IngestionOutcome(row=None, outcome="filtered", duplicate_of_id=None)
    if duplicate_of:
        discovery_status = "duplicate"
        duplicate_of_id = duplicate_of.id
        outcome_reason_codes.append(f"duplicate:{duplicate_reason or 'matched'}")
        duplicate_reasons = [f"Duplicate detected by {duplicate_reason}.", *relevance_reasons]
        # A repeated scan of the same connector/external_id should be counted as a duplicate,
        # not inserted again, because this pair is intentionally unique per tenant.
        if duplicate_reason == "external_id":
            candidate_notice_version = _extract_ted_notice_version(
                str((candidate.raw_content_json or {}).get("notice_version") or "")
            )
            existing_notice_version = _extract_ted_notice_version(
                str((duplicate_of.raw_content_json or {}).get("notice_version") or "")
            )
            if candidate.source_type == "public_procurement" and (
                existing_notice_version is None
                or candidate_notice_version is None
                or candidate_notice_version >= existing_notice_version
            ):
                _refresh_existing_discovery_from_candidate(
                    duplicate_of,
                    candidate,
                    canonical_url=canonical_url,
                    source_domain=source_domain,
                    relevance_score=relevance_score,
                    relevance_reasons=relevance_reasons,
                    matched_keywords=matched_keywords,
                )
            connector_run.items_duplicate += 1
            connector_run.items_found += 1
            if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE:
                _update_independent_page_candidate_decision(
                    db,
                    tenant_id=tenant_id,
                    connector_id=connector.id,
                    canonical_url=canonical_url,
                    page_type=str(candidate_raw_content.get("page_type") or ""),
                    decision="duplicate",
                    reason_codes=["duplicate:external_id", *(candidate_diagnostics.get("reason_codes") or [])],
                    validity=validity,
                )
            return IngestionOutcome(
                row=duplicate_of,
                outcome="duplicate",
                duplicate_of_id=duplicate_of_id,
            )
        relevance_reasons = duplicate_reasons
    elif relevance_score < _preliminary_irrelevant_threshold(candidate.source_type):
        discovery_status = "irrelevant"
        outcome_reason_codes.append("low_preliminary_relevance")
        relevance_reasons = ["Low preliminary match based on deterministic filtering.", *relevance_reasons]
    else:
        outcome_reason_codes.append("accepted_preliminary_relevance")
    outcome_reason_codes.extend(validity_reason_codes)
    if candidate_diagnostics.get("reason_codes"):
        outcome_reason_codes.extend(
            str(code) for code in candidate_diagnostics.get("reason_codes") if _clean_text(str(code))
        )
    candidate_raw_content["crawler_diagnostics"] = {
        **candidate_diagnostics,
        "discovery_status": discovery_status,
        "reason_codes": list(dict.fromkeys(outcome_reason_codes))[:8],
        "relevance_score": relevance_score,
        "validity_score": validity.get("validity_score"),
        "validity_class": validity.get("validity_class"),
    }
    row = BusinessDevelopmentDiscoveredOpportunity(
        id=f"BD-DSC-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        connector_id=connector.id,
        connector_run_id=connector_run.id,
        external_id=candidate.external_id,
        source_type=candidate.source_type,
        source_name=candidate.source_name,
        source_url=_clean_text(candidate.source_url),
        canonical_source_url=canonical_url,
        source_domain=source_domain,
        source_country=_normalize_country_or_region(candidate.source_country),
        title=_clean_text(candidate.title) or candidate.title,
        normalized_title=normalized_title,
        organization_name=_clean_text(candidate.organization_name),
        normalized_organization_name=normalized_organization_name,
        published_date=candidate.published_date,
        closing_date=candidate.closing_date,
        raw_summary=normalized_summary,
        requirement_summary=normalized_requirement,
        normalized_content_json=normalized_content,
        raw_content_json=candidate_raw_content,
        raw_text=normalized_full_text,
        country=_normalize_country_or_region(candidate.country),
        region=_normalize_country_or_region(candidate.region),
        industry=_clean_text(candidate.industry),
        budget_min=candidate.budget_min,
        budget_max=candidate.budget_max,
        currency=_clean_text(candidate.currency),
        discovered_at=_now(),
        retrieval_timestamp=candidate.retrieval_timestamp or _now(),
        discovery_status=discovery_status,
        duplicate_of_discovery_id=duplicate_of_id,
        preliminary_relevance_score=relevance_score,
        relevance_reasons_json=relevance_reasons,
        matched_keywords_json=matched_keywords,
        evidence_json=candidate.evidence or [],
        normalized_search_text=_searchable_text(candidate),
        url_fingerprint=_fingerprint(canonical_url),
        composite_fingerprint=_fingerprint(
            normalized_organization_name,
            normalized_title,
            candidate.closing_date.date().isoformat() if candidate.closing_date else None,
            source_domain,
        ),
        updated_at=_now(),
    )
    db.add(row)
    db.flush()
    refresh_discovery_commercial_intelligence(db, row)
    if discovery_status == "duplicate":
        connector_run.items_duplicate += 1
        outcome = "duplicate"
    elif discovery_status == "irrelevant":
        connector_run.items_filtered += 1
        outcome = "filtered"
    else:
        connector_run.items_new += 1
        outcome = "new"
    connector_run.items_found += 1
    if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE:
        _update_independent_page_candidate_decision(
            db,
            tenant_id=tenant_id,
            connector_id=connector.id,
            canonical_url=canonical_url,
            page_type=str(candidate_raw_content.get("page_type") or ""),
            decision=discovery_status,
            reason_codes=outcome_reason_codes,
            validity=validity,
        )
        run_metadata = dict(connector_run.run_metadata_json or {})
        filter_reason_counts = dict(run_metadata.get("filter_reason_counts") or {})
        candidate_outcomes = list(run_metadata.get("candidate_outcomes") or [])
        if discovery_status == "irrelevant":
            for code in list(dict.fromkeys(outcome_reason_codes))[:8]:
                filter_reason_counts[code] = int(filter_reason_counts.get(code, 0) or 0) + 1
        candidate_outcomes.append(
            {
                "title": row.title,
                "source_url": row.source_url,
                "page_type": str(candidate_raw_content.get("page_type") or ""),
                "discovery_status": discovery_status,
                "relevance_score": relevance_score,
                "reason_codes": list(dict.fromkeys(outcome_reason_codes))[:8],
                "validity_score": validity.get("validity_score"),
                "validity_class": validity.get("validity_class"),
            }
        )
        run_metadata["filter_reason_counts"] = filter_reason_counts
        run_metadata["candidate_outcomes"] = candidate_outcomes[-20:]
        connector_run.run_metadata_json = run_metadata
    return IngestionOutcome(row=row, outcome=outcome, duplicate_of_id=duplicate_of_id)


def _independent_run_progress_snapshot(
    *,
    connector: BusinessDevelopmentConnector,
    run: BusinessDevelopmentConnectorRun,
    stage: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = dict(run.run_metadata_json or {})
    snapshot.update(extra or {})
    crawl_engine = _independent_run_crawl_engine(connector=connector, payload=None, run=run)
    snapshot["connector_type"] = connector.connector_type
    snapshot["crawl_engine"] = crawl_engine
    snapshot["crawl_engine_display"] = crawl_engine_display(crawl_engine)
    snapshot["stage"] = stage
    snapshot["stage_label"] = str(snapshot.get("stage_label") or RUN_STAGE_LABELS.get(stage, stage.replace("_", " ").title()))
    snapshot["elapsed_seconds"] = max(0, int((_now() - (_as_utc(run.started_at) or _now())).total_seconds()))
    max_total_pages = int((connector.configuration_json or {}).get("maximum_total_pages_per_run", 100) or 100)
    pages_fetched = int(snapshot.get("pages_fetched", 0) or 0)
    snapshot["current_batch_label"] = "Current Batch"
    snapshot["batch_progress_current"] = pages_fetched
    snapshot["batch_progress_total"] = max_total_pages
    snapshot["max_html_response_bytes"] = int(
        (connector.configuration_json or {}).get(
            "max_html_response_bytes",
            settings.AUGMIS_WEB_DISCOVERY_DEFAULT_MAX_HTML_RESPONSE_BYTES,
        )
        or settings.AUGMIS_WEB_DISCOVERY_DEFAULT_MAX_HTML_RESPONSE_BYTES
    )
    snapshot["progress_percent"] = 100 if stage in {"COMPLETED", "FAILED"} else min(99, int((pages_fetched / max(1, max_total_pages)) * 100))
    current_url = str(snapshot.get("current_url") or "").strip()
    snapshot["current_url"] = current_url[:240] if current_url else None
    return snapshot


def _persist_connector_run_progress(
    *,
    tenant_id: str,
    connector_id: str,
    run_id: str,
    stage: str,
    extra: dict[str, Any] | None = None,
) -> None:
    progress_db = SessionLocal()
    try:
        run = (
            progress_db.query(BusinessDevelopmentConnectorRun)
            .filter(
                BusinessDevelopmentConnectorRun.tenant_id == tenant_id,
                BusinessDevelopmentConnectorRun.connector_id == connector_id,
                BusinessDevelopmentConnectorRun.id == run_id,
            )
            .first()
        )
        if run is None:
            return
        if run.status == "cancelled":
            raise ConnectorRunCancelledError("Connector scan was stopped by operator.")
        connector = _require_connector(progress_db, tenant_id, connector_id)
        run.run_metadata_json = _independent_run_progress_snapshot(
            connector=connector,
            run=run,
            stage=stage,
            extra=extra,
        )
        if run.status == "queued" and stage not in {"FAILED", "COMPLETED"}:
            run.status = "running"
        if stage == "FAILED":
            run.status = "failed"
        progress_db.commit()
    finally:
        progress_db.close()


def _independent_run_outcome_metadata(
    *,
    run: BusinessDevelopmentConnectorRun,
    metadata: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    run_type = str(metadata.get("run_type") or run.run_type or "manual").strip().lower()
    raw_status = str(metadata.get("status") or "").strip().lower()
    pages_fetched = int(metadata.get("pages_fetched", 0) or 0)
    detail_pages = int(metadata.get("detail_pages", 0) or 0)
    candidates_created = int(metadata.get("opportunity_candidates", 0) or 0)
    pending_frontier_count = int(metadata.get("pending_frontier_count", 0) or 0)
    seeds_selected = int(metadata.get("seeds_selected", 0) or 0)
    requests_attempted = int(metadata.get("requests_attempted", metadata.get("pages_attempted", 0)) or 0)
    responses_received = int(metadata.get("responses_received", metadata.get("pages_fetched", 0)) or 0)

    metadata["candidates_created"] = candidates_created
    metadata["candidates_accepted"] = max(0, int(run.items_found or 0) - int(run.items_filtered or 0))
    metadata["new_discoveries"] = int(run.items_new or 0)
    metadata["duplicates"] = int(run.items_duplicate or 0)
    metadata["filtered"] = int(run.items_filtered or 0)

    summary_fragments: list[str] = []
    if int(metadata.get("attachments_skipped", 0) or 0):
        summary_fragments.append(f"Attachments skipped: {int(metadata.get('attachments_skipped', 0) or 0)}")
    if int(metadata.get("oversized_html_skipped", 0) or 0):
        summary_fragments.append(f"Oversized HTML: {int(metadata.get('oversized_html_skipped', 0) or 0)}")
    metadata["skip_summary"] = " · ".join(summary_fragments) if summary_fragments else None

    if raw_status == "no_due_work":
        metadata["batch_outcome"] = "NO_SCHEDULED_WORK"
        metadata["outcome_title"] = "No Scheduled Work"
        metadata["outcome_message"] = "No scan executed — no scheduled seeds are currently due."
        return metadata, "completed"
    if raw_status == "no_enabled_seeds":
        metadata["batch_outcome"] = "NO_ENABLED_SEEDS"
        metadata["outcome_title"] = "No Enabled Seeds"
        metadata["outcome_message"] = (
            "Manual scan did not run — no enabled seeds were available."
            if run_type == "manual"
            else "No scan executed — no enabled seeds were available."
        )
        return metadata, "failed" if run_type == "manual" else "completed"
    if run_type == "manual" and seeds_selected > 0 and requests_attempted == 0:
        metadata["batch_outcome"] = "MANUAL_SCAN_NO_REQUESTS"
        metadata["execution_anomaly"] = "MANUAL_SCAN_NO_REQUESTS"
        metadata["outcome_title"] = "Execution Anomaly"
        metadata["outcome_message"] = "Manual scan did not run — selected seeds did not produce any crawl requests."
        return metadata, "failed"
    if requests_attempted > 0 and responses_received == 0:
        metadata["batch_outcome"] = "FETCH_FAILED"
        metadata["outcome_title"] = "Fetch Failed"
        metadata["outcome_message"] = f"Scan attempted {requests_attempted} URLs, but no pages were successfully fetched."
        return metadata, "failed"
    if pending_frontier_count > 0:
        metadata["batch_outcome"] = "BATCH_COMPLETE_MORE_PENDING"
        metadata["outcome_title"] = "Batch Complete"
        metadata["outcome_message"] = (
            f"Batch Complete — {pages_fetched} pages fetched, "
            f"{pending_frontier_count} URLs still pending, {int(run.items_new or 0)} new opportunities."
        )
        return metadata, "partial" if run.items_failed else "completed"
    if candidates_created == 0 and detail_pages == 0:
        metadata["batch_outcome"] = "CRAWL_COMPLETE"
        metadata["outcome_title"] = "Completed"
        metadata["outcome_message"] = f"Completed — {pages_fetched} pages fetched, no valid opportunities found."
        return metadata, "partial" if run.items_failed else "completed"

    metadata["batch_outcome"] = "CRAWL_COMPLETE"
    metadata["outcome_title"] = "Crawl Complete"
    metadata["outcome_message"] = (
        f"Crawl Complete — {pages_fetched} pages fetched, "
        f"{candidates_created} candidates, {int(run.items_new or 0)} new opportunities."
    )
    return metadata, "partial" if run.items_failed else "completed"


def _build_independent_progress_callback(
    *,
    tenant_id: str,
    connector_id: str,
    run_id: str,
) -> Callable[[dict[str, Any]], None]:
    def callback(snapshot: dict[str, Any]) -> None:
        _persist_connector_run_progress(
            tenant_id=tenant_id,
            connector_id=connector_id,
            run_id=run_id,
            stage=str(snapshot.get("stage") or "FETCHING").upper(),
            extra=snapshot,
        )

    return callback


def _execute_scrapy_independent_scan(
    *,
    db: Session,
    tenant_id: str,
    connector: BusinessDevelopmentConnector,
    run: BusinessDevelopmentConnectorRun,
    current_user: dict,
) -> tuple[list[AugmisBusinessDiscoveredOpportunityCandidate], dict[str, Any]]:
    del db, current_user
    stop_file = _scrapy_stop_file(run.id)
    try:
        stop_file.unlink(missing_ok=True)
        python_executable = _scrapy_subprocess_python()
        if not python_executable.exists():
            raise HTTPException(status_code=500, detail=f"Scrapy worker interpreter was not found at {python_executable}.")
        process = subprocess.Popen(
            [
                str(python_executable),
                "-m",
                "app.scrapy_augmis.runner",
                "--tenant-id",
                tenant_id,
                "--connector-id",
                connector.id,
                "--run-id",
                run.id,
                "--stop-file",
                str(stop_file),
            ],
            cwd=str(python_executable.parent.parent.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        cancelled = False
        while True:
            try:
                process.wait(timeout=1)
                break
            except subprocess.TimeoutExpired:
                if not _is_connector_run_cancelled(tenant_id, run.id):
                    continue
                cancelled = True
                stop_file.touch(exist_ok=True)
                try:
                    process.wait(timeout=SCRAPY_STOP_GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=SCRAPY_STOP_KILL_TIMEOUT_SECONDS)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=SCRAPY_STOP_KILL_TIMEOUT_SECONDS)
                break
        stdout, stderr = process.communicate()
        if cancelled:
            raise ConnectorRunCancelledError("Connector scan was stopped by operator.")
        if process.returncode != 0:
            error_output = (stderr or stdout or "").strip().splitlines()
            summary = error_output[-1] if error_output else "Scrapy crawl worker failed."
            raise HTTPException(status_code=500, detail=summary)
        payload = json.loads((stdout or "").strip().splitlines()[-1])
        candidates = [
            AugmisBusinessDiscoveredOpportunityCandidate.model_validate(item)
            for item in list(payload.get("candidates") or [])
        ]
        metadata = dict(payload.get("metadata") or {})
        metadata.setdefault("crawl_engine", CRAWL_ENGINE_SCRAPY)
        metadata.setdefault("crawl_engine_display", crawl_engine_display(CRAWL_ENGINE_SCRAPY))
        return candidates, metadata
    finally:
        stop_file.unlink(missing_ok=True)


def _run_stop_metadata(
    *,
    connector: BusinessDevelopmentConnector,
    run: BusinessDevelopmentConnectorRun,
    message: str,
) -> dict[str, Any]:
    if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE:
        snapshot = _independent_run_progress_snapshot(
            connector=connector,
            run=run,
            stage="FAILED",
            extra={
                **(run.run_metadata_json or {}),
                "stage_label": "Stopped",
                "failure_message": message,
                "outcome_message": f"Stopped — {message}",
            },
        )
        snapshot["stage"] = "STOPPED"
        return snapshot
    return {**(run.run_metadata_json or {})}


def _raise_if_connector_run_cancelled(
    *,
    tenant_id: str,
    connector_id: str,
    run_id: str,
) -> None:
    check_db = SessionLocal()
    try:
        run = (
            check_db.query(BusinessDevelopmentConnectorRun)
            .filter(
                BusinessDevelopmentConnectorRun.tenant_id == tenant_id,
                BusinessDevelopmentConnectorRun.connector_id == connector_id,
                BusinessDevelopmentConnectorRun.id == run_id,
            )
            .first()
        )
        if run is not None and run.status == "cancelled":
            raise ConnectorRunCancelledError("Connector scan was stopped by operator.")
    finally:
        check_db.close()


def _create_connector_run(
    db: Session,
    tenant_id: str,
    connector_id: str,
    current_user: dict,
    payload: AugmisBusinessConnectorScanRequest | None = None,
    *,
    initial_status: str = "running",
) -> tuple[BusinessDevelopmentConnector, BusinessDevelopmentConnectorRun]:
    connector = _require_connector(db, tenant_id, connector_id)
    if not connector.enabled:
        raise HTTPException(status_code=400, detail="Connector is disabled")
    overlapping = (
        db.query(BusinessDevelopmentConnectorRun)
        .filter(
            BusinessDevelopmentConnectorRun.tenant_id == tenant_id,
            BusinessDevelopmentConnectorRun.connector_id == connector.id,
            BusinessDevelopmentConnectorRun.status.in_(ACTIVE_CONNECTOR_RUN_STATUSES),
        )
        .first()
    )
    if overlapping:
        raise HTTPException(status_code=409, detail="A scan is already in progress for this connector.")
    run_type = payload.run_type if payload else "manual"
    crawl_engine = (
        _independent_run_crawl_engine(connector=connector, payload=payload)
        if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE
        else None
    )
    started_at = _now()
    due_reference = _as_utc(connector.next_run_at) if run_type in {"scheduled", "retry"} else None
    attempt_number = 1
    max_attempts = 3 if run_type in {"scheduled", "retry"} else 1
    retry_of_run_id = None
    if run_type == "retry":
        attempt_number = max(2, int(connector.schedule_retry_count or 0) + 1)
        retry_of_run_id = connector.schedule_retry_run_id
    run = BusinessDevelopmentConnectorRun(
        id=f"BD-RUN-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        connector_id=connector.id,
        run_type=run_type,
        attempt_number=attempt_number,
        max_attempts=max_attempts,
        retry_of_run_id=retry_of_run_id,
        status=initial_status,
        started_at=started_at,
        initiated_by=current_user["user_id"],
        run_metadata_json={
            "connector_type": connector.connector_type,
            **(
                {
                    "crawl_engine": crawl_engine,
                    "crawl_engine_display": crawl_engine_display(crawl_engine),
                }
                if crawl_engine
                else {}
            ),
        },
    )
    if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE:
        run.run_metadata_json = _independent_run_progress_snapshot(
            connector=connector,
            run=run,
            stage="PREPARING",
            extra={
                "stage_label": RUN_STAGE_LABELS["PREPARING"],
                "crawl_engine": crawl_engine,
                "crawl_engine_display": crawl_engine_display(crawl_engine),
            },
        )
    if not _claim_connector_run(
        db,
        connector=connector,
        tenant_id=tenant_id,
        run_id=run.id,
        started_at=started_at,
        due_reference=due_reference,
    ):
        raise HTTPException(status_code=409, detail="A scan is already in progress for this connector.")
    db.add(run)
    db.commit()
    db.refresh(run)
    connector = _require_connector(db, tenant_id, connector.id)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="RUN",
        event_category="AUGMIS_BUSINESS",
        description=f"Started {run_type} connector scan for {connector.name}",
        resource_type="bd_connector_run",
        resource_id=run.id,
        metadata={"connector_id": connector.id, "run_type": run_type, "attempt_number": run.attempt_number, "action": _run_audit_action(run_type)},
    )
    return connector, run


def _execute_connector_scan(
    db: Session,
    tenant_id: str,
    connector_id: str,
    current_user: dict,
    payload: AugmisBusinessConnectorScanRequest | None = None,
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    connector = _require_connector(db, tenant_id, connector_id)
    run = (
        db.query(BusinessDevelopmentConnectorRun)
        .filter(
            BusinessDevelopmentConnectorRun.tenant_id == tenant_id,
            BusinessDevelopmentConnectorRun.connector_id == connector.id,
            BusinessDevelopmentConnectorRun.id == run_id,
        )
        .first()
        if run_id
        else None
    )
    if run is None:
        connector, run = _create_connector_run(db, tenant_id, connector_id, current_user, payload)
    elif run.status == "cancelled":
        return {"success": True, "data": {"connector": _serialize_connector(connector), "run": _serialize_connector_run(run), "discoveries": []}}
    _raise_if_connector_run_cancelled(tenant_id=tenant_id, connector_id=connector.id, run_id=run.id)
    run_type = run.run_type or (payload.run_type if payload else "manual")
    search_profile = (
        _require_search_profile(db, tenant_id, connector.search_profile_id)
        if connector.search_profile_id
        else ensure_default_search_profile(db, tenant_id, current_user)
    )
    implementation = _get_connector_implementation(connector.connector_type)
    crawl_engine = (
        _independent_run_crawl_engine(connector=connector, payload=payload, run=run)
        if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE
        else None
    )
    progress_callback = (
        _build_independent_progress_callback(tenant_id=tenant_id, connector_id=connector.id, run_id=run.id)
        if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE
        else None
    )
    try:
        credential = (
            resolve_provider_credential(
                db,
                tenant_id,
                str((connector.configuration_json or {}).get("provider", "tavily") or "tavily"),
            )
            if connector.connector_type in {WEB_SEARCH_CONNECTOR_TYPE, FREELANCER_CONNECTOR_TYPE, ADZUNA_CONNECTOR_TYPE}
            else None
        )
        if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE and crawl_engine == CRAWL_ENGINE_SCRAPY:
            candidates, scrapy_metadata = _execute_scrapy_independent_scan(
                db=db,
                tenant_id=tenant_id,
                connector=connector,
                run=run,
                current_user=current_user,
            )
            implementation.last_run_metadata = scrapy_metadata
        else:
            candidates = (
                implementation.discover(
                    connector=connector,
                    search_profile=search_profile,
                    credential=credential,
                    progress_callback=progress_callback,
                    run_type=run_type,
                )
                if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE
                else implementation.discover(
                    connector=connector,
                    search_profile=search_profile,
                    credential=credential,
                )
            )
        run.run_metadata_json = {
            **(run.run_metadata_json or {}),
            **(implementation.last_run_metadata or {}),
        }
        run.items_filtered += int((implementation.last_run_metadata or {}).get("filtered_candidates", 0) or 0)
        if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE:
            run.run_metadata_json = _independent_run_progress_snapshot(
                connector=connector,
                run=run,
                stage="INGESTING",
                extra={**(run.run_metadata_json or {}), "stage_label": RUN_STAGE_LABELS["INGESTING"]},
            )
            db.commit()
            db.refresh(run)
        ingested_rows = []
        for index, candidate in enumerate(candidates, start=1):
            _raise_if_connector_run_cancelled(tenant_id=tenant_id, connector_id=connector.id, run_id=run.id)
            if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE:
                run.run_metadata_json = _independent_run_progress_snapshot(
                    connector=connector,
                    run=run,
                    stage="INGESTING",
                    extra={
                        **(run.run_metadata_json or {}),
                        "stage_label": RUN_STAGE_LABELS["INGESTING"],
                        "candidate_ingestion_current": index,
                        "candidate_ingestion_total": len(candidates),
                    },
                )
                db.commit()
                db.refresh(run)
            try:
                with db.begin_nested():
                    outcome = ingest_discovered_opportunity(
                        db,
                        tenant_id,
                        connector,
                        run,
                        AugmisBusinessDiscoveredOpportunityCandidate.model_validate(candidate),
                        search_profile,
                    )
                if outcome.row is not None:
                    ingested_rows.append(_serialize_discovery(outcome.row))
            except Exception as exc:
                run.items_failed += 1
                messages = list((run.run_metadata_json or {}).get("item_errors", []))
                messages.append(str(exc))
                run.run_metadata_json = {**(run.run_metadata_json or {}), "item_errors": messages[-10:]}
        _raise_if_connector_run_cancelled(tenant_id=tenant_id, connector_id=connector.id, run_id=run.id)
        if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE:
            run_metadata = dict(run.run_metadata_json or {})
            run_metadata, final_run_status = _independent_run_outcome_metadata(run=run, metadata=run_metadata)
            run.run_metadata_json = _independent_run_progress_snapshot(
                connector=connector,
                run=run,
                stage="FINALIZING",
                extra={**run_metadata, "stage_label": RUN_STAGE_LABELS["FINALIZING"]},
            )
        run.completed_at = _now()
        run.status = final_run_status if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE else ("partial" if run.items_failed else "completed")
        if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE:
            completed_stage = "FAILED" if run.status == "failed" else "COMPLETED"
            run.run_metadata_json = _independent_run_progress_snapshot(
                connector=connector,
                run=run,
                stage=completed_stage,
                extra={**(run.run_metadata_json or {}), "stage_label": RUN_STAGE_LABELS[completed_stage]},
            )
        connector.active_run_id = None
        connector.status = "ready" if connector.enabled else "disabled"
        connector.last_success_at = run.completed_at if run.status in {"completed", "partial"} else connector.last_success_at
        connector.last_error_at = run.completed_at if run.status == "failed" or run.items_failed else None
        connector.last_error_message = (
            str((run.run_metadata_json or {}).get("outcome_message") or "Connector scan failed.")
            if run.status == "failed"
            else ("Some discovery items failed ingestion." if run.items_failed else None)
        )
        if run_type in {"scheduled", "retry"} and connector.schedule_enabled:
            connector.schedule_retry_count = 0
            connector.schedule_retry_run_id = None
            connector.next_run_at = _compute_next_run_at(
                schedule_type=connector.schedule_type,
                schedule_interval_minutes=connector.schedule_interval_minutes,
                schedule_day_of_week=connector.schedule_day_of_week,
                schedule_time_local=connector.schedule_time_local,
                schedule_timezone=connector.schedule_timezone,
                after_utc=run.completed_at,
                anchor_utc=connector.last_scheduled_run_at or _as_utc(connector.next_run_at) or run.started_at,
            )
        db.commit()
        db.refresh(run)
        db.refresh(connector)
        create_audit_log(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user["user_id"],
            event_type="RUN",
            event_category="AUGMIS_BUSINESS",
            description=f"Completed connector scan for {connector.name}",
            resource_type="bd_connector_run",
            resource_id=run.id,
            metadata={"connector_id": connector.id, "status": run.status},
        )
        return {"success": True, "data": {"connector": _serialize_connector(connector), "run": _serialize_connector_run(run), "discoveries": ingested_rows}}
    except ConnectorRunCancelledError as exc:
        db.rollback()
        run = (
            db.query(BusinessDevelopmentConnectorRun)
            .filter(BusinessDevelopmentConnectorRun.id == run.id, BusinessDevelopmentConnectorRun.tenant_id == tenant_id)
            .first()
        )
        connector = _require_connector(db, tenant_id, connector.id)
        message = str(exc) or "Connector scan was stopped by operator."
        if run:
            run.status = "cancelled"
            run.completed_at = run.completed_at or _now()
            run.error_summary = message
            run.run_metadata_json = _run_stop_metadata(connector=connector, run=run, message=message)
        if connector.active_run_id == run.id:
            connector.active_run_id = None
        connector.status = "ready" if connector.enabled else "disabled"
        connector.last_error_message = None
        db.commit()
        db.refresh(run)
        db.refresh(connector)
        return {"success": True, "data": {"connector": _serialize_connector(connector), "run": _serialize_connector_run(run), "discoveries": []}}
    except Exception as exc:
        db.rollback()
        run = (
            db.query(BusinessDevelopmentConnectorRun)
            .filter(BusinessDevelopmentConnectorRun.id == run.id, BusinessDevelopmentConnectorRun.tenant_id == tenant_id)
            .first()
        )
        connector = _require_connector(db, tenant_id, connector.id)
        error_summary = _ted_error_summary(exc) if isinstance(exc, TedApiError) else (str(exc) or "Connector scan failed")
        if isinstance(exc, TedApiError) and run:
            run_metadata = dict(run.run_metadata_json or {})
            run_metadata["provider_error"] = exc.to_diagnostic()
            run.run_metadata_json = run_metadata
        if run:
            run.status = "failed"
            run.completed_at = _now()
            run.error_summary = error_summary
            if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE:
                run.run_metadata_json = _independent_run_progress_snapshot(
                    connector=connector,
                    run=run,
                    stage="FAILED",
                    extra={
                        **(run.run_metadata_json or {}),
                        "stage_label": RUN_STAGE_LABELS["FAILED"],
                        "failure_message": error_summary,
                        "outcome_message": f"Failed — {int((run.run_metadata_json or {}).get('pages_fetched', 0) or 0)} pages fetched before failure. {error_summary}",
                    },
                )
        connector.active_run_id = None
        connector.last_error_at = _now()
        connector.last_error_message = error_summary
        connector.status = "attention" if connector.enabled else "disabled"
        if run and run_type in {"scheduled", "retry"} and connector.schedule_enabled:
            retry_allowed = _is_retryable_scan_error(error_summary) and run.attempt_number < run.max_attempts
            if retry_allowed:
                retry_delay = SCHEDULE_RETRY_DELAYS_MINUTES[min(run.attempt_number - 1, len(SCHEDULE_RETRY_DELAYS_MINUTES) - 1)]
                retry_at = _now() + timedelta(minutes=retry_delay)
                run.next_retry_at = retry_at
                connector.schedule_retry_count = run.attempt_number
                connector.schedule_retry_run_id = run.id
                connector.next_run_at = retry_at
            else:
                connector.schedule_retry_count = 0
                connector.schedule_retry_run_id = None
                connector.next_run_at = _compute_next_run_at(
                    schedule_type=connector.schedule_type,
                    schedule_interval_minutes=connector.schedule_interval_minutes,
                    schedule_day_of_week=connector.schedule_day_of_week,
                    schedule_time_local=connector.schedule_time_local,
                    schedule_timezone=connector.schedule_timezone,
                    after_utc=_now(),
                    anchor_utc=connector.last_scheduled_run_at or run.started_at,
                )
        db.commit()
        if isinstance(exc, TedApiError):
            raise HTTPException(status_code=502, detail=error_summary) from exc
        raise HTTPException(status_code=500, detail=error_summary) from exc


def execute_connector_scan_in_background(
    tenant_id: str,
    connector_id: str,
    current_user: dict,
    payload: AugmisBusinessConnectorScanRequest | None,
    run_id: str,
) -> None:
    db = SessionLocal()
    try:
        _execute_connector_scan(db, tenant_id, connector_id, current_user, payload, run_id=run_id)
    except Exception:
        pass
    finally:
        db.close()


def start_connector_scan(
    db: Session,
    tenant_id: str,
    connector_id: str,
    current_user: dict,
    payload: AugmisBusinessConnectorScanRequest | None = None,
) -> dict[str, Any]:
    connector = _require_connector(db, tenant_id, connector_id)
    run_type = payload.run_type if payload else "manual"
    if connector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE and run_type == "manual":
        connector, run = _create_connector_run(
            db,
            tenant_id,
            connector_id,
            current_user,
            payload,
            initial_status="queued",
        )
        return {"success": True, "data": {"connector": _serialize_connector(connector), "run": _serialize_connector_run(run), "discoveries": []}}
    return _execute_connector_scan(db, tenant_id, connector_id, current_user, payload)


def run_connector_scan(
    db: Session,
    tenant_id: str,
    connector_id: str,
    current_user: dict,
    payload: AugmisBusinessConnectorScanRequest | None = None,
) -> dict[str, Any]:
    return _execute_connector_scan(db, tenant_id, connector_id, current_user, payload)


def list_discoveries(
    db: Session,
    tenant_id: str,
    *,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    status_filter: str | None = None,
    connector_id: str | None = None,
    source_category: str | None = None,
    country: str | None = None,
    minimum_preliminary_score: float | None = None,
    relevance_band: str | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
) -> dict[str, Any]:
    query = db.query(BusinessDevelopmentDiscoveredOpportunity).filter(
        BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id
    )
    if status_filter:
        query = query.filter(BusinessDevelopmentDiscoveredOpportunity.discovery_status == status_filter)
    if connector_id:
        query = query.filter(BusinessDevelopmentDiscoveredOpportunity.connector_id == connector_id)
    if source_category:
        query = query.join(
            BusinessDevelopmentConnector,
            BusinessDevelopmentConnector.id == BusinessDevelopmentDiscoveredOpportunity.connector_id,
        )
        if source_category in {"remoteok", "arbeitnow", "remotive", "adzuna"}:
            query = query.filter(BusinessDevelopmentDiscoveredOpportunity.source_name.ilike(f"%{source_category}%"))
        else:
            query = query.filter(BusinessDevelopmentConnector.source_category == source_category)
    if country:
        query = query.filter(BusinessDevelopmentDiscoveredOpportunity.country == country)
    if minimum_preliminary_score is not None:
        query = query.filter(
            BusinessDevelopmentDiscoveredOpportunity.preliminary_relevance_score >= minimum_preliminary_score
        )
    if relevance_band:
        normalized_band = str(relevance_band).strip().lower()
        band_ranges = {
            "strong": (80.0, None),
            "good": (65.0, 79.9),
            "possible": (50.0, 64.9),
            "weak": (35.0, 49.9),
            "low": (None, 34.9),
        }
        bounds = band_ranges.get(normalized_band)
        if bounds:
            minimum, maximum = bounds
            if minimum is not None:
                query = query.filter(BusinessDevelopmentDiscoveredOpportunity.preliminary_relevance_score >= minimum)
            if maximum is not None:
                query = query.filter(BusinessDevelopmentDiscoveredOpportunity.preliminary_relevance_score <= maximum)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                BusinessDevelopmentDiscoveredOpportunity.title.ilike(pattern),
                BusinessDevelopmentDiscoveredOpportunity.organization_name.ilike(pattern),
                BusinessDevelopmentDiscoveredOpportunity.requirement_summary.ilike(pattern),
                BusinessDevelopmentDiscoveredOpportunity.raw_summary.ilike(pattern),
            )
        )
    total = query.count()
    normalized_sort_by = str(sort_by or "").strip().lower()
    normalized_sort_order = "asc" if str(sort_order or "").strip().lower() == "asc" else "desc"
    if normalized_sort_by == "highest_match":
        order_fn = asc if normalized_sort_order == "asc" else desc
        query = query.order_by(
            order_fn(BusinessDevelopmentDiscoveredOpportunity.preliminary_relevance_score).nullslast(),
            BusinessDevelopmentDiscoveredOpportunity.discovered_at.desc(),
        )
    elif normalized_sort_by == "lowest_match":
        query = query.order_by(
            asc(BusinessDevelopmentDiscoveredOpportunity.preliminary_relevance_score).nullslast(),
            BusinessDevelopmentDiscoveredOpportunity.discovered_at.desc(),
        )
    elif normalized_sort_by == "closing_soon":
        now = _now()
        closing_rank = case(
            (
                BusinessDevelopmentDiscoveredOpportunity.closing_date.is_(None),
                2,
            ),
            (
                BusinessDevelopmentDiscoveredOpportunity.closing_date < now,
                1,
            ),
            else_=0,
        )
        query = query.order_by(
            closing_rank.asc(),
            BusinessDevelopmentDiscoveredOpportunity.closing_date.asc().nullslast(),
            BusinessDevelopmentDiscoveredOpportunity.discovered_at.desc(),
        )
    else:
        query = query.order_by(
            BusinessDevelopmentDiscoveredOpportunity.discovered_at.desc(),
            BusinessDevelopmentDiscoveredOpportunity.created_at.desc(),
        )
    rows = (
        query.offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "success": True,
        "data": [_serialize_discovery(row) for row in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": ceil(total / page_size) if total else 1,
        },
    }


def get_discovery(db: Session, tenant_id: str, discovery_id: str) -> dict[str, Any]:
    row = _require_discovery(db, tenant_id, discovery_id)
    duplicates = []
    if row.duplicate_of_discovery_id:
        duplicate = _require_discovery(db, tenant_id, row.duplicate_of_discovery_id)
        duplicates.append(_serialize_discovery(duplicate))
    related_duplicates = (
        db.query(BusinessDevelopmentDiscoveredOpportunity)
        .filter(
            BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id,
            BusinessDevelopmentDiscoveredOpportunity.duplicate_of_discovery_id == row.id,
        )
        .order_by(BusinessDevelopmentDiscoveredOpportunity.created_at.asc())
        .all()
    )
    return {
        "success": True,
        "data": _serialize_discovery(row),
        "duplicates": [_serialize_discovery(item) for item in related_duplicates] + duplicates,
    }


def update_discovery(
    db: Session,
    tenant_id: str,
    discovery_id: str,
    current_user: dict,
    payload: AugmisBusinessDiscoveryUpdateRequest,
) -> dict[str, Any]:
    row = _require_discovery(db, tenant_id, discovery_id)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(row, key, value)
    if {
        "requirement_summary",
        "budget_min",
        "budget_max",
        "currency",
        "country",
        "region",
        "industry",
    } & set(changes.keys()):
        normalized_requirement, normalized_summary, normalized_full_text, normalized_content = _normalized_content_payload(
            row.requirement_summary,
            row.raw_summary,
            row.raw_text,
        )
        row.requirement_summary = normalized_requirement
        row.raw_summary = normalized_summary
        row.raw_text = normalized_full_text
        row.normalized_content_json = normalized_content
    if {
        "requirement_summary",
        "country",
        "region",
        "industry",
        "budget_min",
        "budget_max",
        "currency",
    } & set(changes.keys()):
        refresh_discovery_commercial_intelligence(db, row)
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return {"success": True, "data": _serialize_discovery(row)}


def reprocess_discovery_content(
    db: Session,
    tenant_id: str,
    current_user: dict,
    *,
    limit: int = 100,
) -> dict[str, Any]:
    bounded_limit = max(1, min(int(limit or 100), 250))
    rows = (
        db.query(BusinessDevelopmentDiscoveredOpportunity)
        .filter(BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id)
        .order_by(BusinessDevelopmentDiscoveredOpportunity.discovered_at.desc())
        .limit(bounded_limit)
        .all()
    )
    processed: list[dict[str, Any]] = []
    for row in rows:
        normalized_requirement, normalized_summary, normalized_full_text, normalized_content = _normalized_content_payload(
            row.requirement_summary,
            row.raw_summary,
            row.raw_text,
        )
        row.requirement_summary = normalized_requirement
        row.raw_summary = normalized_summary
        row.raw_text = normalized_full_text
        row.normalized_content_json = normalized_content
        row.updated_at = _now()
        processed.append(
            {
                "id": row.id,
                "title": row.title,
                "detected_format": str((normalized_content.get("requirement") or {}).get("detected_format") or "text"),
            }
        )
    db.commit()
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description="Reprocessed discovery content normalization",
        resource_type="bd_discovery",
        resource_id=None,
        metadata={"count": len(processed), "limit": bounded_limit},
    )
    return {"success": True, "data": {"count": len(processed), "limit": bounded_limit, "items": processed}}


def recalculate_independent_discovery_validity(
    db: Session,
    tenant_id: str,
    current_user: dict,
    *,
    limit: int = 100,
) -> dict[str, Any]:
    bounded_limit = max(1, min(int(limit or 100), 250))
    rows = (
        db.query(BusinessDevelopmentDiscoveredOpportunity)
        .join(
            BusinessDevelopmentConnector,
            BusinessDevelopmentConnector.id == BusinessDevelopmentDiscoveredOpportunity.connector_id,
        )
        .filter(
            BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id,
            BusinessDevelopmentConnector.connector_type == INDEPENDENT_WEB_CONNECTOR_TYPE,
        )
        .order_by(BusinessDevelopmentDiscoveredOpportunity.discovered_at.desc())
        .limit(bounded_limit)
        .all()
    )
    processed: list[dict[str, Any]] = []
    for row in rows:
        old_status = row.discovery_status
        validity = _apply_validity_to_discovery_row(db, row)
        processed.append(
            {
                "id": row.id,
                "title": row.title,
                "old_status": old_status,
                "new_status": row.discovery_status,
                "validity_score": validity.get("validity_score"),
                "validity_band": validity.get("validity_band"),
                "validity_class": validity.get("validity_class"),
                "actionability": validity.get("actionability"),
                "eligible_for_inbox": bool(validity.get("eligible_for_inbox")),
            }
        )
    db.commit()
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description="Recalculated independent discovery validity and actionability",
        resource_type="bd_discovery",
        resource_id=None,
        metadata={"count": len(processed), "limit": bounded_limit, "connector_type": INDEPENDENT_WEB_CONNECTOR_TYPE},
    )
    return {"success": True, "data": {"count": len(processed), "limit": bounded_limit, "items": processed}}


def shortlist_discovery(
    db: Session,
    tenant_id: str,
    discovery_id: str,
    current_user: dict,
) -> dict[str, Any]:
    row = _require_discovery(db, tenant_id, discovery_id)
    row.discovery_status = "shortlisted"
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Shortlisted discovery {row.title}",
        resource_type="bd_discovery",
        resource_id=row.id,
        metadata={"status": row.discovery_status},
    )
    return {"success": True, "data": _serialize_discovery(row)}


def reject_discovery(
    db: Session,
    tenant_id: str,
    discovery_id: str,
    current_user: dict,
) -> dict[str, Any]:
    row = _require_discovery(db, tenant_id, discovery_id)
    row.discovery_status = "rejected"
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Rejected discovery {row.title}",
        resource_type="bd_discovery",
        resource_id=row.id,
        metadata={"status": row.discovery_status},
    )
    return {"success": True, "data": _serialize_discovery(row)}


def list_discovery_duplicates(
    db: Session,
    tenant_id: str,
    discovery_id: str,
) -> dict[str, Any]:
    row = _require_discovery(db, tenant_id, discovery_id)
    items = (
        db.query(BusinessDevelopmentDiscoveredOpportunity)
        .filter(
            BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id,
            or_(
                BusinessDevelopmentDiscoveredOpportunity.id == row.duplicate_of_discovery_id,
                BusinessDevelopmentDiscoveredOpportunity.duplicate_of_discovery_id == row.id,
                BusinessDevelopmentDiscoveredOpportunity.possible_duplicate_of_discovery_id == row.id,
            ),
        )
        .all()
    )
    return {"success": True, "data": [_serialize_discovery(item) for item in items]}


def import_discovery_as_opportunity(
    db: Session,
    tenant_id: str,
    discovery_id: str,
    current_user: dict,
) -> dict[str, Any]:
    row = _require_discovery(db, tenant_id, discovery_id)
    if row.imported_opportunity_id:
        raise HTTPException(status_code=409, detail="Discovery has already been imported")
    if row.discovery_status == "duplicate":
        raise HTTPException(status_code=409, detail="Duplicate discovery cannot be imported directly")
    existing_opportunity = None
    if row.external_id:
        existing_opportunity = (
            db.query(BusinessDevelopmentOpportunity)
            .filter(
                BusinessDevelopmentOpportunity.tenant_id == tenant_id,
                BusinessDevelopmentOpportunity.external_id == row.external_id,
                BusinessDevelopmentOpportunity.source_type == row.source_type,
            )
            .first()
        )
    if existing_opportunity:
        raise HTTPException(status_code=409, detail="Matching opportunity already exists for this source record")
    opportunity_payload = AugmisBusinessOpportunityCreateRequest(
        external_id=row.external_id,
        source_type=row.source_type,
        source_name=row.source_name,
        source_url=row.source_url,
        title=row.title,
        organization_name=row.organization_name or row.source_name,
        country=row.country,
        region=row.region,
        industry=row.industry,
        published_at=row.published_date,
        closing_at=row.closing_date,
        raw_summary=row.raw_summary,
        requirement_summary=row.requirement_summary or row.raw_summary or row.title,
        business_problem=None,
        expected_deliverables_json=[],
        required_technologies_json=[],
        published_budget=row.budget_max,
        published_currency=row.currency,
        estimated_value_min=row.budget_min,
        estimated_value_max=row.budget_max,
        estimated_currency=row.currency,
        fit_score=None,
        confidence_score=None,
        ai_recommendation=None,
        opportunity_status="new",
        source_evidence_json=[{"label": item.get("label", ""), "type": str(item.get("type", ""))} for item in (row.evidence_json or [])],
    )
    try:
        result = create_opportunity(db, tenant_id, current_user, opportunity_payload, commit=False)
        row.imported_opportunity_id = result["data"]["id"]
        row.discovery_status = "imported"
        row.updated_at = _now()
        db.commit()
        db.refresh(row)
    except Exception:
        db.rollback()
        raise
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="IMPORT",
        event_category="AUGMIS_BUSINESS",
        description=f"Imported discovery {row.title} as an opportunity",
        resource_type="bd_discovery",
        resource_id=row.id,
        metadata={"opportunity_id": row.imported_opportunity_id},
    )
    return {"success": True, "data": {"discovery": _serialize_discovery(row), "opportunity": result["data"]}}


def recover_stale_connector_runs(db: Session) -> dict[str, int]:
    stale_before = _now() - timedelta(minutes=SCHEDULE_STALE_RUN_THRESHOLD_MINUTES)
    stale_runs = (
        db.query(BusinessDevelopmentConnectorRun)
        .filter(
            BusinessDevelopmentConnectorRun.status == "running",
            BusinessDevelopmentConnectorRun.started_at < stale_before,
        )
        .all()
    )
    recovered = 0
    for run in stale_runs:
        connector = _require_connector(db, run.tenant_id, run.connector_id)
        run.status = "failed"
        run.completed_at = _now()
        run.error_summary = "Connector run was interrupted and recovered as stale after backend restart."
        if connector.active_run_id == run.id:
            connector.active_run_id = None
        connector.last_error_at = _now()
        connector.last_error_message = run.error_summary
        connector.status = "attention" if connector.enabled else "disabled"
        if connector.schedule_enabled and run.run_type in {"scheduled", "retry"}:
            connector.schedule_retry_count = 0
            connector.schedule_retry_run_id = None
            connector.next_run_at = _compute_next_run_at(
                schedule_type=connector.schedule_type,
                schedule_interval_minutes=connector.schedule_interval_minutes,
                schedule_day_of_week=connector.schedule_day_of_week,
                schedule_time_local=connector.schedule_time_local,
                schedule_timezone=connector.schedule_timezone,
                after_utc=_now(),
                anchor_utc=connector.last_scheduled_run_at or run.started_at,
            )
        recovered += 1
    if recovered:
        db.commit()
    return {"recovered": recovered}


def initialize_listener_schedule_state(db: Session) -> dict[str, int]:
    recovered = recover_stale_connector_runs(db)["recovered"]
    initialized = 0
    connectors = (
        db.query(BusinessDevelopmentConnector)
        .filter(
            BusinessDevelopmentConnector.enabled == True,
            BusinessDevelopmentConnector.schedule_enabled == True,
        )
        .all()
    )
    now = _now()
    for connector in connectors:
        if connector.schedule_type == "manual":
            connector.schedule_enabled = False
            connector.next_run_at = None
            initialized += 1
            continue
        if connector.next_run_at is None:
            connector.next_run_at = _compute_next_run_at(
                schedule_type=connector.schedule_type,
                schedule_interval_minutes=connector.schedule_interval_minutes,
                schedule_day_of_week=connector.schedule_day_of_week,
                schedule_time_local=connector.schedule_time_local,
                schedule_timezone=connector.schedule_timezone,
                after_utc=now,
                anchor_utc=connector.last_scheduled_run_at,
            )
            initialized += 1
    if initialized:
        db.commit()
    return {"recovered": recovered, "initialized": initialized}


def run_due_listener_scans(db: Session) -> dict[str, Any]:
    now = _now()
    connectors = (
        db.query(BusinessDevelopmentConnector)
        .filter(
            BusinessDevelopmentConnector.enabled == True,
            BusinessDevelopmentConnector.schedule_enabled == True,
            BusinessDevelopmentConnector.active_run_id.is_(None),
            BusinessDevelopmentConnector.next_run_at.isnot(None),
            BusinessDevelopmentConnector.next_run_at <= now,
        )
        .order_by(BusinessDevelopmentConnector.next_run_at.asc())
        .all()
    )
    results = []
    for connector in connectors:
        system_user = {"tenant_id": connector.tenant_id, "user_id": None}
        run_type = "retry" if (connector.schedule_retry_count or 0) > 0 else "scheduled"
        try:
            result = run_connector_scan(
                db,
                connector.tenant_id,
                connector.id,
                current_user=system_user,
                payload=AugmisBusinessConnectorScanRequest(run_type=run_type),
            )
            results.append({"connector_id": connector.id, "status": result["data"]["run"]["status"], "run_type": run_type})
        except HTTPException as exc:
            results.append({"connector_id": connector.id, "status": "failed", "run_type": run_type, "error": exc.detail})
    return {"due_count": len(connectors), "results": results}
