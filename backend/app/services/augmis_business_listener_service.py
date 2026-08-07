from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from math import ceil
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
from app.services.augmis_business_service import create_opportunity, serialize_opportunity
from app.services.augmis_business_web_fetcher import (
    SafeWebFetchError,
    WebFetchRuntimePolicy,
    default_web_fetch_runtime_policy,
    extract_text_from_webpage,
    fetch_public_webpage,
)
from app.services.augmis_business_web_search_provider import get_web_search_provider
from app.services.augmis_business_web_search_query_builder import build_web_search_queries


DEFAULT_PROFILE_NAME = "Default AUGMIS Discovery Profile"
FIXTURE_CONNECTOR_TYPE = "fixture_opportunity_connector"
FIXTURE_CONNECTOR_NAME = "Fixture Opportunity Listener"
WEB_SEARCH_CONNECTOR_TYPE = "generic_web_search"
WEB_SEARCH_CONNECTOR_NAME = "Web Opportunity Search"
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


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = WHITESPACE_PATTERN.sub(" ", value).strip()
    return cleaned or None


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


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
                    "provider_options": ["tavily", "brave"],
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
        provider_name = str(config.get("provider", "tavily") or "tavily").strip().lower()
        if provider_name not in {"tavily", "brave"}:
            raise HTTPException(status_code=400, detail="provider must be one of: tavily, brave")
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
        provider = get_web_search_provider(provider_name, api_key=credential.api_key)
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


def _get_connector_implementation(connector_type: str) -> BaseOpportunityConnector:
    if connector_type == FIXTURE_CONNECTOR_TYPE:
        return FixtureOpportunityConnector()
    if connector_type == WEB_SEARCH_CONNECTOR_TYPE:
        return WebOpportunitySearchConnector()
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
        "relevance_reasons_json": row.relevance_reasons_json or [],
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
    if row.connector_type == WEB_SEARCH_CONNECTOR_TYPE:
        metadata_payload["default_provider"] = "tavily"
        metadata_payload["supported_providers"] = ["tavily", "brave"]
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
        "schedule_expression": row.schedule_expression,
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
    ensure_fixture_connector(db, tenant_id, current_user)
    ensure_web_search_connector(db, tenant_id, current_user)
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
    failed_runs = (
        db.query(func.count(BusinessDevelopmentConnectorRun.id))
        .filter(
            BusinessDevelopmentConnectorRun.tenant_id == tenant_id,
            BusinessDevelopmentConnectorRun.status == "failed",
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
    if payload.search_profile_id:
        _require_search_profile(db, tenant_id, payload.search_profile_id)
    row = BusinessDevelopmentConnector(
        id=f"BD-CNX-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        created_by=current_user["user_id"],
        status="ready" if payload.enabled else "disabled",
        updated_at=_now(),
        **payload.model_dump(),
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
    for key, value in changes.items():
        setattr(row, key, value)
    if "enabled" in changes:
        row.status = "ready" if row.enabled else "disabled"
    row.updated_at = _now()
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
        metadata={"updated_fields": sorted(changes.keys())},
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
        relevance_reasons = [f"Duplicate detected by {duplicate_reason}.", *relevance_reasons]
        # A repeated scan of the same connector/external_id should be counted as a duplicate,
        # not inserted again, because this pair is intentionally unique per tenant.
        if duplicate_reason == "external_id":
            connector_run.items_duplicate += 1
            connector_run.items_found += 1
            return IngestionOutcome(
                row=duplicate_of,
                outcome="duplicate",
                duplicate_of_id=duplicate_of_id,
            )
    elif relevance_score < 25:
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
        raise HTTPException(status_code=409, detail="Connector scan already in progress")
    run_type = (payload.run_type if payload else "manual")
    run = BusinessDevelopmentConnectorRun(
        id=f"BD-RUN-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        connector_id=connector.id,
        run_type=run_type,
        status="running",
        started_at=_now(),
        initiated_by=current_user["user_id"],
        run_metadata_json={"connector_type": connector.connector_type},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    connector.last_scan_at = run.started_at
    connector.status = "running"
    db.commit()
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
        connector.status = "ready" if connector.enabled else "disabled"
        connector.last_success_at = run.completed_at if run.status in {"completed", "partial"} else connector.last_success_at
        connector.last_error_at = run.completed_at if run.items_failed else None
        connector.last_error_message = (
            "Some discovery items failed ingestion." if run.items_failed else None
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
        if run:
            run.status = "failed"
            run.completed_at = _now()
            run.error_summary = str(exc)
        connector.status = "error"
        connector.last_error_at = _now()
        connector.last_error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc) or "Connector scan failed") from exc


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
    rows = (
        query.order_by(
            BusinessDevelopmentDiscoveredOpportunity.discovered_at.desc(),
            BusinessDevelopmentDiscoveredOpportunity.created_at.desc(),
        )
        .offset((page - 1) * page_size)
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


def run_due_listener_scans(db: Session) -> dict[str, Any]:
    now = _now()
    connectors = (
        db.query(BusinessDevelopmentConnector)
        .filter(
            BusinessDevelopmentConnector.enabled == True,
            BusinessDevelopmentConnector.schedule_enabled == True,
            BusinessDevelopmentConnector.schedule_expression.isnot(None),
        )
        .all()
    )
    due: list[BusinessDevelopmentConnector] = []
    for connector in connectors:
        try:
            minutes = int((connector.schedule_expression or "").strip())
        except ValueError:
            continue
        if connector.last_scan_at is None or connector.last_scan_at + timedelta(minutes=minutes) <= now:
            due.append(connector)
    results = []
    for connector in due:
        system_user = {"tenant_id": connector.tenant_id, "user_id": None}
        try:
            result = run_connector_scan(
                db,
                connector.tenant_id,
                connector.id,
                current_user=system_user,
                payload=AugmisBusinessConnectorScanRequest(run_type="scheduled"),
            )
            results.append({"connector_id": connector.id, "status": result["data"]["run"]["status"]})
        except HTTPException as exc:
            results.append({"connector_id": connector.id, "status": "failed", "error": exc.detail})
    return {"due_count": len(due), "results": results}
