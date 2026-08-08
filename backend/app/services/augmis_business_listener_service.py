from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from math import ceil
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import and_, asc, case, desc, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, object_session

from app.core.config import settings
from app.db_models import (
    BusinessDevelopmentConnector,
    BusinessDevelopmentConnectorRun,
    BusinessDevelopmentDiscoveredOpportunity,
    BusinessDevelopmentExperienceItem,
    BusinessDevelopmentOpportunity,
    BusinessDevelopmentSearchProfile,
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
from app.services.augmis_business_search_provider_service import (
    ensure_builtin_search_providers,
    resolve_search_provider_by_code,
)
from app.services.augmis_business_discovery_translation_service import (
    get_latest_translation_row,
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


DEFAULT_PROFILE_NAME = "Default AUGMIS Discovery Profile"
FIXTURE_CONNECTOR_TYPE = "fixture_opportunity_connector"
FIXTURE_CONNECTOR_NAME = "Fixture Opportunity Listener"
WEB_SEARCH_CONNECTOR_TYPE = "generic_web_search"
WEB_SEARCH_CONNECTOR_NAME = "Web Opportunity Search"
TED_CONNECTOR_TYPE = "ted_procurement"
TED_CONNECTOR_NAME = "TED European Procurement"
CONNECTOR_TEST_LABEL = "TEST / FIXTURE"
CONNECTOR_PRODUCTION_LABEL = "PRODUCTION"

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
SCHEDULE_RETRY_DELAYS_MINUTES = (5, 15)
SCHEDULE_STALE_RUN_THRESHOLD_MINUTES = 120
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
    cleaned = WHITESPACE_PATTERN.sub(" ", value).strip()
    return cleaned or None


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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
    if (source_type or "").strip().lower() == "public_procurement":
        return TED_IRRELEVANT_THRESHOLD
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
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported connector type: {connector_type}",
    )


@dataclass
class IngestionOutcome:
    row: BusinessDevelopmentDiscoveredOpportunity
    outcome: str
    duplicate_of_id: str | None = None


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


def _get_connector_implementation(connector_type: str) -> BaseOpportunityConnector:
    if connector_type == FIXTURE_CONNECTOR_TYPE:
        return FixtureOpportunityConnector()
    if connector_type == WEB_SEARCH_CONNECTOR_TYPE:
        return WebOpportunitySearchConnector()
    if connector_type == TED_CONNECTOR_TYPE:
        return TedProcurementConnector()
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
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "connector_id": row.connector_id,
        "connector_run_id": row.connector_run_id,
        "external_id": row.external_id,
        "source_type": row.source_type,
        "source_name": row.source_name,
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
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "search_profile_id": row.search_profile_id,
        "connector_type": row.connector_type,
        "name": row.name,
        "source_category": row.source_category,
        "status": row.status,
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
        "capability_flags_json": row.capability_flags_json or {},
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
    summary = {
        "active_connectors": sum(1 for row in rows if row.enabled),
        "last_scan": _serialize_datetime(latest_run.started_at) if latest_run else None,
        "discoveries_today": today_discoveries,
        "new_discoveries": new_discoveries,
        "failed_runs": failed_runs,
    }
    return {"success": True, "data": [_serialize_connector(row) for row in rows], "summary": summary}


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
        if row.connector_type == WEB_SEARCH_CONNECTOR_TYPE
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


def _calculate_preliminary_relevance(
    candidate: AugmisBusinessDiscoveredOpportunityCandidate,
    profile: BusinessDevelopmentSearchProfile | None,
) -> tuple[float, list[str], list[str]]:
    if candidate.source_type == "public_procurement":
        return _calculate_ted_preliminary_relevance(candidate)

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
    row.raw_summary = _clean_text(candidate.raw_summary)
    row.requirement_summary = _clean_text(candidate.requirement_summary)
    row.raw_content_json = candidate.raw_content_json or candidate.source_metadata or {}
    row.raw_text = _clean_text(candidate.raw_text)
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
    row.updated_at = _now()
    if row.discovery_status in {"imported", "shortlisted", "rejected"}:
        return
    row.discovery_status = (
        "irrelevant"
        if relevance_score < _preliminary_irrelevant_threshold(row.source_type)
        else "new"
    )


def ingest_discovered_opportunity(
    db: Session,
    tenant_id: str,
    connector: BusinessDevelopmentConnector,
    connector_run: BusinessDevelopmentConnectorRun,
    candidate: AugmisBusinessDiscoveredOpportunityCandidate,
    search_profile: BusinessDevelopmentSearchProfile | None,
) -> IngestionOutcome:
    canonical_url, source_domain = _normalize_url(candidate.source_url)
    normalized_title = _normalize_title(candidate.title)
    normalized_organization_name = _normalize_text(candidate.organization_name)
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
    discovery_status = "new"
    duplicate_of_id = None
    if duplicate_of:
        discovery_status = "duplicate"
        duplicate_of_id = duplicate_of.id
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
            return IngestionOutcome(
                row=duplicate_of,
                outcome="duplicate",
                duplicate_of_id=duplicate_of_id,
            )
        relevance_reasons = duplicate_reasons
    elif relevance_score < _preliminary_irrelevant_threshold(candidate.source_type):
        discovery_status = "irrelevant"
        relevance_reasons = ["Low preliminary match based on deterministic filtering.", *relevance_reasons]
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
        raw_summary=_clean_text(candidate.raw_summary),
        requirement_summary=_clean_text(candidate.requirement_summary),
        raw_content_json=candidate.raw_content_json or candidate.source_metadata or {},
        raw_text=_clean_text(candidate.raw_text),
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
    return IngestionOutcome(row=row, outcome=outcome, duplicate_of_id=duplicate_of_id)


def run_connector_scan(
    db: Session,
    tenant_id: str,
    connector_id: str,
    current_user: dict,
    payload: AugmisBusinessConnectorScanRequest | None = None,
) -> dict[str, Any]:
    connector = _require_connector(db, tenant_id, connector_id)
    if not connector.enabled:
        raise HTTPException(status_code=400, detail="Connector is disabled")
    overlapping = (
        db.query(BusinessDevelopmentConnectorRun)
        .filter(
            BusinessDevelopmentConnectorRun.tenant_id == tenant_id,
            BusinessDevelopmentConnectorRun.connector_id == connector.id,
            BusinessDevelopmentConnectorRun.status == "running",
        )
        .first()
    )
    if overlapping:
        raise HTTPException(status_code=409, detail="A scan is already in progress for this connector.")
    run_type = (payload.run_type if payload else "manual")
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
        status="running",
        started_at=started_at,
        initiated_by=current_user["user_id"],
        run_metadata_json={"connector_type": connector.connector_type},
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
    search_profile = (
        _require_search_profile(db, tenant_id, connector.search_profile_id)
        if connector.search_profile_id
        else ensure_default_search_profile(db, tenant_id, current_user)
    )
    implementation = _get_connector_implementation(connector.connector_type)
    try:
        credential = (
            resolve_provider_credential(
                db,
                tenant_id,
                str((connector.configuration_json or {}).get("provider", "tavily") or "tavily"),
            )
            if connector.connector_type == WEB_SEARCH_CONNECTOR_TYPE
            else None
        )
        candidates = implementation.discover(
            connector=connector,
            search_profile=search_profile,
            credential=credential,
        )
        run.run_metadata_json = {
            **(run.run_metadata_json or {}),
            **(implementation.last_run_metadata or {}),
        }
        run.items_filtered += int((implementation.last_run_metadata or {}).get("filtered_candidates", 0) or 0)
        ingested_rows = []
        for candidate in candidates:
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
                ingested_rows.append(_serialize_discovery(outcome.row))
            except Exception as exc:
                run.items_failed += 1
                messages = list((run.run_metadata_json or {}).get("item_errors", []))
                messages.append(str(exc))
                run.run_metadata_json = {**(run.run_metadata_json or {}), "item_errors": messages[-10:]}
        run.completed_at = _now()
        run.status = "partial" if run.items_failed else "completed"
        connector.active_run_id = None
        connector.status = "ready" if connector.enabled else "disabled"
        connector.last_success_at = run.completed_at if run.status in {"completed", "partial"} else connector.last_success_at
        connector.last_error_at = run.completed_at if run.items_failed else None
        connector.last_error_message = (
            "Some discovery items failed ingestion." if run.items_failed else None
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
                anchor_utc=connector.last_scheduled_run_at or due_reference or run.started_at,
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
            description=f"Initiated connector scan for {connector.name}",
            resource_type="bd_connector_run",
            resource_id=run.id,
            metadata={"connector_id": connector.id, "status": run.status},
        )
        return {
            "success": True,
            "data": {
                "connector": _serialize_connector(connector),
                "run": _serialize_connector_run(run),
                "discoveries": ingested_rows,
            },
        }
    except Exception as exc:
        db.rollback()
        run = (
            db.query(BusinessDevelopmentConnectorRun)
            .filter(
                BusinessDevelopmentConnectorRun.id == run.id,
                BusinessDevelopmentConnectorRun.tenant_id == tenant_id,
            )
            .first()
        )
        connector = _require_connector(db, tenant_id, connector.id)
        error_summary = str(exc) or "Connector scan failed"
        if isinstance(exc, TedApiError):
            diagnostic = exc.to_diagnostic()
            error_summary = _ted_error_summary(exc)
            run_metadata = dict(run.run_metadata_json or {}) if run else {}
            run_metadata["provider_error"] = diagnostic
            if run:
                run.run_metadata_json = run_metadata
        if run:
            run.status = "failed"
            run.completed_at = _now()
            run.error_summary = error_summary
        connector.active_run_id = None
        connector.last_error_at = _now()
        connector.last_error_message = error_summary
        if connector.enabled:
            connector.status = "attention"
        else:
            connector.status = "disabled"
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
                    anchor_utc=connector.last_scheduled_run_at or due_reference or run.started_at,
                )
        db.commit()
        if isinstance(exc, TedApiError):
            raise HTTPException(status_code=502, detail=error_summary) from exc
        raise HTTPException(status_code=500, detail=error_summary) from exc


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
        ).filter(BusinessDevelopmentConnector.source_category == source_category)
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
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return {"success": True, "data": _serialize_discovery(row)}


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
