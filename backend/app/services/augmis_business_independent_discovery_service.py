from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
import re
from typing import Any
from urllib import robotparser
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree

from fastapi import HTTPException, status
import requests
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db_models import (
    BusinessDevelopmentConnector,
    BusinessDevelopmentSearchProfile,
    BusinessDevelopmentWebDomain,
    BusinessDevelopmentWebFrontier,
    BusinessDevelopmentWebPage,
    BusinessDevelopmentWebSeed,
)
from app.models.augmis_business_models import (
    AugmisBusinessDiscoveredOpportunityCandidate,
    AugmisBusinessWebFetchTestRequest,
    AugmisBusinessWebDomainUpdateRequest,
    AugmisBusinessWebSeedCreateRequest,
    AugmisBusinessWebSeedUpdateRequest,
)
from app.services.audit_service import create_audit_log
from app.services.augmis_business_web_fetcher import (
    SafeWebFetchError,
    WebFetchRuntimePolicy,
    extract_text_from_webpage,
    fetch_public_text_resource,
    fetch_public_webpage,
    validate_public_http_url,
)


INDEPENDENT_WEB_CONNECTOR_TYPE = "independent_web_discovery"
INDEPENDENT_WEB_CONNECTOR_NAME = "AUGMIS Independent Web Discovery"
INDEPENDENT_WEB_SOURCE_NAME = "AUGMIS Web"
TRACKING_QUERY_PREFIXES = ("utm_", "fbclid", "gclid", "mc_", "ref", "source")
TRUSTED_PORTAL_TERMS = (
    "procurement",
    "tender",
    "vendor",
    "supplier",
    "rfp",
    "rfq",
    "eoi",
    "bid",
)
POSITIVE_URL_TERMS = TRUSTED_PORTAL_TERMS + (
    "opportunity",
    "consultancy",
    "software",
    "digital",
    "technology",
    "workflow",
    "records",
    "document",
    "integration",
    "analytics",
    "dashboard",
    "jobs",
    "careers",
)
NEGATIVE_URL_TERMS = (
    "privacy",
    "terms",
    "cookies",
    "gallery",
    "media",
    "login",
    "logout",
    "cart",
    "checkout",
    "tag",
    "archive",
)
OPPORTUNITY_TERMS = (
    "request for proposal",
    "rfp",
    "request for quotation",
    "rfq",
    "expression of interest",
    "eoi",
    "invitation to tender",
    "procurement notice",
    "vendor opportunity",
    "call for consultants",
    "software development contract",
    "digital transformation",
    "system implementation",
    "workflow automation",
    "document management",
    "records management",
    "dashboard",
    "analytics",
    "integration services",
)
NEGATIVE_CONTENT_TERMS = (
    "privacy policy",
    "cookie policy",
    "terms and conditions",
    "photo gallery",
    "press release",
    "blog post",
)
JOB_TERMS = ("job", "career", "vacancy", "hiring", "employment")
STALE_SESSION_TERMS = (
    "stale session",
    "session expired",
    "your session has expired",
    "invalid session",
)
PROCUREMENT_HOME_TERMS = (
    "eprocurement system",
    "epublishing system",
    "government eprocurement system",
    "tender home",
    "procurement portal",
    "vendor portal",
)
PROCUREMENT_LIST_TERMS = (
    "active tenders",
    "latest tenders",
    "published bids",
    "tender search",
    "browse tenders",
    "corrigendum",
    "standard bidding documents",
    "bid schedule",
)
PROCUREMENT_DETAIL_TERMS = (
    "deadline",
    "closing date",
    "bid opening",
    "emd",
    "tender fee",
    "scope of work",
    "eligibility",
    "pre-bid",
    "reference number",
    "tender id",
    "notice inviting tender",
)
DYNAMIC_CONTENT_TERMS = (
    "enable javascript",
    "javascript required",
    "loading...",
    "please wait",
    "single page application",
)
SESSION_BOUND_QUERY_KEYS = {
    "jsessionid",
    "sessionid",
    "phpsessid",
    "aspsessionid",
    "asp.net_sessionid",
    "sid",
    "session",
}
SESSION_BOUND_VALUE_HINTS = ("jsessionid", "sessionid", "phpsessid", "aspsessionid")
CONTACT_PATH_HINTS = (
    "/contact",
    "/contact-us",
)
EMAIL_PATTERN = re.compile(r"\b([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,5}\d{2,4}")
DATE_PATTERNS = (
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),
    re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"),
    re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b"),
)
BUDGET_PATTERNS = (
    re.compile(r"\b(USD|EUR|GBP|SAR|INR|AED)\s?([\d,]+(?:\.\d{1,2})?)\b", re.IGNORECASE),
    re.compile(r"([$€£])\s?([\d,]+(?:\.\d{1,2})?)"),
)
DEFAULT_RECRAWL_HOURS_BY_FREQUENCY = {
    "daily": 24,
    "weekly": 24 * 7,
    "monthly": 24 * 30,
    "manual": 24 * 30,
}
DEFAULT_PAGE_RECRAWL_HOURS_BY_TYPE = {
    "procurement_list": 24,
    "procurement_detail": 24,
    "rfp": 24,
    "rfq": 24,
    "eoi": 24,
    "tender": 24,
    "career_list": 72,
    "job_detail": 72,
    "contact": 24 * 30,
    "organization": 24 * 30,
    "unknown": settings.AUGMIS_WEB_DISCOVERY_DEFAULT_RECRAWL_HOURS,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _slugify_label(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    return re.sub(r"[^a-z0-9]+", "-", cleaned.lower()).strip("-") or None


def _serialize_datetime(value: datetime | None) -> str | None:
    normalized = _as_utc(value)
    return normalized.isoformat() if normalized else None


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def canonicalize_url(url: str) -> tuple[str, str]:
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Seed URL must use http or https.")
    if not parts.hostname:
        raise HTTPException(status_code=400, detail="Seed URL hostname is missing.")
    scheme = parts.scheme.lower()
    hostname = parts.hostname.lower()
    port = parts.port
    netloc = hostname
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{hostname}:{port}"
    path = parts.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=False)
        if not any(key.lower().startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES)
    ]
    query = urlencode(filtered_query, doseq=True)
    canonical = urlunsplit((scheme, netloc, path, query, ""))
    return canonical, hostname


def _content_hash(value: str | None) -> str | None:
    if not value:
        return None
    return sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def _fingerprint(value: str) -> str:
    return sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:24]


def _as_public_url(url: str) -> tuple[str, str]:
    canonical, domain = canonicalize_url(url)
    validate_public_http_url(canonical)
    return canonical, domain


def _same_origin_referer(parent_url: str | None, target_url: str) -> str | None:
    if not parent_url:
        return None
    parent_host = (urlsplit(parent_url).hostname or "").lower()
    target_host = (urlsplit(target_url).hostname or "").lower()
    if parent_host and parent_host == target_host:
        return parent_url
    return None


def _session_bound_url_reasons(url: str) -> list[str]:
    parts = urlsplit(url)
    reasons: list[str] = []
    lowered_path = parts.path.lower()
    lowered_query = parts.query.lower()
    if ";jsessionid=" in lowered_path:
        reasons.append("path_jsessionid")
    parsed_query = [(key.lower(), value.lower()) for key, value in parse_qsl(parts.query, keep_blank_values=True)]
    for key, value in parsed_query:
        if key in SESSION_BOUND_QUERY_KEYS and (len(value) >= 8 or any(hint in value for hint in SESSION_BOUND_VALUE_HINTS) or bool(re.search(r"[0-9_-]{4,}", value))):
            reasons.append(f"query_{key}")
        if any(hint in value for hint in SESSION_BOUND_VALUE_HINTS):
            reasons.append(f"value_{key or 'session'}")
    if "sessionexpired" in lowered_query or "stalesession" in lowered_query:
        reasons.append("query_session_expired")
    return list(dict.fromkeys(reasons))[:6]


def _diagnostic_message(code: str) -> str:
    return {
        "ROBOTS_DENIED": "Robots policy denied this URL.",
        "SESSION_BOUND_URL": "URL appears bound to a transient public session and will not be retried as a durable link.",
    }.get(code, code.replace("_", " ").title())


def _record_failure_metric(
    metrics: dict[str, Any],
    *,
    frontier: BusinessDevelopmentWebFrontier,
    diagnostic: dict[str, Any],
) -> None:
    code = str(diagnostic.get("error_code") or frontier.error_code or "UNKNOWN_FETCH_ERROR")
    counts = dict(metrics.get("fetch_failure_counts") or {})
    counts[code] = int(counts.get(code, 0) or 0) + 1
    metrics["fetch_failure_counts"] = counts
    samples = list(metrics.get("fetch_failure_samples") or [])
    if len([item for item in samples if item.get("error_code") == code]) < 3:
        samples.append(
            {
                "error_code": code,
                "url": frontier.canonical_url,
                "domain": frontier.domain,
                "depth": frontier.depth,
                "parent_url": frontier.parent_url,
                "retryable": bool(diagnostic.get("retryable")),
                "http_status": diagnostic.get("http_status"),
                "message": diagnostic.get("error_message") or frontier.error_message,
            }
        )
    metrics["fetch_failure_samples"] = samples[-24:]


def _retry_delay_for_diagnostic(diagnostic: dict[str, Any], *, attempt_number: int) -> timedelta | None:
    code = str(diagnostic.get("error_code") or "")
    if not diagnostic.get("retryable"):
        return None
    retry_after = str(diagnostic.get("retry_after") or "").strip()
    if retry_after.isdigit():
        return timedelta(seconds=max(1, min(int(retry_after), 86_400)))
    if code == "HTTP_429":
        return timedelta(hours=24)
    if code == "HTTP_5XX":
        return timedelta(minutes=min(60, 5 * max(1, attempt_number)))
    if code in {"CONNECTION_TIMEOUT", "READ_TIMEOUT", "CONNECTION_RESET", "DNS_FAILURE", "DECOMPRESSION_ERROR"}:
        return timedelta(minutes=min(60, 10 * max(1, attempt_number)))
    return timedelta(hours=12)


def _apply_frontier_failure(
    frontier: BusinessDevelopmentWebFrontier,
    *,
    diagnostic: dict[str, Any],
    domain_row: BusinessDevelopmentWebDomain,
    metrics: dict[str, Any],
    detail_link_queued: bool,
) -> None:
    frontier.status = "failed"
    frontier.error_code = str(diagnostic.get("error_code") or "UNKNOWN_FETCH_ERROR")
    frontier.error_message = str(diagnostic.get("error_message") or _diagnostic_message(frontier.error_code))
    frontier.http_status = int(diagnostic.get("http_status")) if diagnostic.get("http_status") is not None else None
    frontier.diagnostic_json = diagnostic
    frontier.retry_count += 1
    retry_delay = _retry_delay_for_diagnostic(diagnostic, attempt_number=int(frontier.retry_count or 1))
    frontier.next_fetch_at = (_now() + retry_delay) if retry_delay else None
    domain_row.error_count += 1
    domain_row.status = "attention"
    metrics["errors"] += 1
    metrics["stale_or_error_pages"] += 1
    _record_failure_metric(metrics, frontier=frontier, diagnostic=diagnostic)
    if detail_link_queued:
        metrics["detail_links_fetch_failed"] += 1


def _allowed_domain_mode(config: dict[str, Any]) -> str:
    return str(config.get("allowed_domain_mode", "approved_only") or "approved_only").strip().lower()


def _runtime_policy(config: dict[str, Any]) -> WebFetchRuntimePolicy:
    return WebFetchRuntimePolicy(
        fetch_source_page=True,
        max_fetch_bytes=_clamp(
            int(config.get("max_fetch_bytes", settings.AUGMIS_WEB_FETCH_MAX_BYTES) or settings.AUGMIS_WEB_FETCH_MAX_BYTES),
            25_000,
            settings.AUGMIS_WEB_FETCH_MAX_BYTES,
        ),
        fetch_timeout_seconds=_clamp(
            int(config.get("request_timeout_seconds", settings.AUGMIS_WEB_FETCH_TIMEOUT_SECONDS) or settings.AUGMIS_WEB_FETCH_TIMEOUT_SECONDS),
            3,
            30,
        ),
        max_extracted_text_chars=_clamp(
            int(config.get("max_extracted_text_chars", 40_000) or 40_000),
            2_000,
            100_000,
        ),
        max_redirects=_clamp(
            int(config.get("max_redirects", settings.AUGMIS_WEB_FETCH_MAX_REDIRECTS) or settings.AUGMIS_WEB_FETCH_MAX_REDIRECTS),
            0,
            5,
        ),
        user_agent=settings.AUGMIS_WEB_DISCOVERY_USER_AGENT,
    )


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, Any]] = []
        self.title: str | None = None
        self.h1: str | None = None
        self.meta: dict[str, str] = {}
        self._current_link: dict[str, Any] | None = None
        self._capture_title = False
        self._capture_h1 = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value for key, value in attrs}
        tag = tag.lower()
        if tag == "a":
            href = attributes.get("href")
            if href:
                self._current_link = {
                    "href": href,
                    "text": "",
                    "nofollow": "nofollow" in str(attributes.get("rel") or "").lower(),
                }
        elif tag == "title":
            self._capture_title = True
        elif tag == "h1" and not self.h1:
            self._capture_h1 = True
        elif tag == "meta":
            key = (attributes.get("property") or attributes.get("name") or "").strip().lower()
            value = (attributes.get("content") or "").strip()
            if key and value and key not in self.meta:
                self.meta[key] = value

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self._current_link:
            self._current_link["text"] = _clean_text(self._current_link["text"])
            self.links.append(self._current_link)
            self._current_link = None
        elif tag == "title":
            self._capture_title = False
        elif tag == "h1":
            self._capture_h1 = False

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            next_title = f"{self.title or ''} {data}".strip()
            self.title = _clean_text(next_title)
        if self._capture_h1:
            next_h1 = f"{self.h1 or ''} {data}".strip()
            self.h1 = _clean_text(next_h1)
        if self._current_link is not None:
            self._current_link["text"] = f"{self._current_link['text']} {data}".strip()


@dataclass
class RobotsPolicy:
    allowed: bool
    crawl_delay_seconds: int
    status: str
    robots_url: str | None
    fetched_at: datetime | None
    parser: robotparser.RobotFileParser | None


@dataclass
class PageParseResult:
    canonical_url: str
    domain: str
    title: str | None
    h1: str | None
    text: str
    html: str
    links: list[dict[str, Any]]
    meta: dict[str, str]
    page_type: str
    type_reasons: list[str]
    published_at: datetime | None
    closing_at: datetime | None
    budget_min: float | None
    budget_max: float | None
    currency: str | None
    organization_name: str | None
    country: str | None
    contact_routes: list[dict[str, Any]]
    application_url: str | None
    reference_number: str | None


def _limited_codes(values: list[str], *, limit: int = 8) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned:
            continue
        normalized = cleaned.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(cleaned)
        if len(unique) >= limit:
            break
    return unique


def _page_detail_signal_count(title: str | None, url: str, text: str) -> int:
    searchable = " ".join(filter(None, [title or "", url, text[:5000]])).lower()
    score = sum(1 for term in PROCUREMENT_DETAIL_TERMS if term in searchable)
    if re.search(r"\b(?:tender|bid|reference|rfp|rfq|eoi)[\s#:.-]{0,4}[a-z0-9/-]{3,}\b", searchable):
        score += 1
    if re.search(r"\b(?:deadline|closing|published)\s*[:\-]?\s*\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", searchable):
        score += 1
    return score


def _seed_recheck_interval_hours(seed: BusinessDevelopmentWebSeed) -> int:
    return DEFAULT_RECRAWL_HOURS_BY_FREQUENCY.get(seed.crawl_frequency, settings.AUGMIS_WEB_DISCOVERY_DEFAULT_RECRAWL_HOURS)


def _page_recheck_interval_hours(page_type: str) -> int:
    return DEFAULT_PAGE_RECRAWL_HOURS_BY_TYPE.get(page_type, settings.AUGMIS_WEB_DISCOVERY_DEFAULT_RECRAWL_HOURS)


def _extract_dates(text: str) -> list[datetime]:
    dates: list[datetime] = []
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            try:
                if pattern.pattern.startswith("\\b(\\d{4})"):
                    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                else:
                    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                dates.append(datetime(year, month, day, tzinfo=timezone.utc))
            except ValueError:
                continue
    return sorted({item for item in dates})


def _extract_budget(text: str) -> tuple[float | None, float | None, str | None]:
    for pattern in BUDGET_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        currency = match.group(1).upper()
        if currency == "$":
            currency = "USD"
        elif currency == "€":
            currency = "EUR"
        elif currency == "£":
            currency = "GBP"
        value = float(match.group(2).replace(",", ""))
        return value, value, currency
    return None, None, None


def _extract_reference_number(text: str) -> str | None:
    patterns = (
        r"\b(?:reference|ref|notice|tender|rfp|rfq|eoi)\s*(?:number|no\.?|id)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/_-]{3,})",
        r"\b([A-Z]{2,6}-\d{2,6}(?:[-/]\d{1,6})?)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _source_trust_for_domain(domain: str) -> str:
    if domain.endswith(".gov") or domain.endswith(".gov.uk") or domain.endswith(".gob.es") or domain.endswith(".edu"):
        return "public"
    if any(domain.endswith(suffix) for suffix in (".org", ".int", ".eu")):
        return "institutional"
    return "public_web"


def _detect_country(text: str) -> str | None:
    countries = (
        "United Kingdom",
        "United States",
        "Saudi Arabia",
        "Germany",
        "France",
        "Spain",
        "Italy",
        "Poland",
        "Netherlands",
        "Belgium",
        "Sweden",
        "Norway",
        "Portugal",
        "Ireland",
        "UAE",
        "India",
    )
    lowered = text.lower()
    for country in countries:
        if country.lower() in lowered:
            return country
    return None


def _page_type(title: str | None, url: str, text: str, meta: dict[str, str]) -> tuple[str, list[str]]:
    searchable = " ".join(filter(None, [title or "", url, text[:4000], meta.get("og:type"), meta.get("description")]))
    lowered = searchable.lower()
    reasons: list[str] = []
    positive_score = sum(2 for term in OPPORTUNITY_TERMS if term in lowered)
    detail_signal_count = _page_detail_signal_count(title, url, text)
    contact_url = any(term in url.lower() for term in ("/contact", "/contact-us"))
    has_explicit_opportunity_signal = any(
        term in lowered
        for term in (
            "request for proposal",
            "rfp",
            "request for quotation",
            "rfq",
            "expression of interest",
            "eoi",
            "invitation to tender",
            "tender",
            "procurement notice",
            "call for tenders",
        )
    )
    if contact_url or ("contact us" in lowered and not has_explicit_opportunity_signal and positive_score < 2):
        reasons.append("Detected contact route.")
        return "contact", reasons
    if any(term in lowered for term in STALE_SESSION_TERMS):
        reasons.append("Session-expired or stale-session page detected.")
        return "stale_session", reasons
    if any(term in lowered for term in DYNAMIC_CONTENT_TERMS):
        reasons.append("Dynamic-content shell detected without usable detail text.")
        return "dynamic_content_only", reasons
    if any(term in lowered for term in NEGATIVE_CONTENT_TERMS):
        reasons.append("Negative content signals dominate the page.")
        return "irrelevant", reasons
    if "vendor registration" in lowered:
        reasons.append("Vendor registration terms detected.")
        return "vendor_registration", reasons
    portal_signal = any(term in lowered for term in PROCUREMENT_HOME_TERMS)
    listing_signal = any(term in lowered for term in PROCUREMENT_LIST_TERMS)
    if (portal_signal or listing_signal) and detail_signal_count <= 1:
        reasons.append("Procurement portal or listing signals dominate detail signals.")
        return "procurement_list", reasons
    if any(term in lowered for term in ("request for proposal", "rfp")):
        if portal_signal and detail_signal_count <= 1:
            reasons.append("RFP term appears on a generic procurement portal/listing page.")
            return "procurement_list", reasons
        reasons.append("RFP terms detected.")
        return "rfp", reasons
    if any(term in lowered for term in ("request for quotation", "rfq")):
        if portal_signal and detail_signal_count <= 1:
            reasons.append("RFQ term appears on a generic procurement portal/listing page.")
            return "procurement_list", reasons
        reasons.append("RFQ terms detected.")
        return "rfq", reasons
    if any(term in lowered for term in ("expression of interest", "eoi")):
        if portal_signal and detail_signal_count <= 1:
            reasons.append("EOI term appears on a generic procurement portal/listing page.")
            return "procurement_list", reasons
        reasons.append("EOI terms detected.")
        return "eoi", reasons
    if any(term in lowered for term in ("invitation to tender", "tender", "procurement notice", "call for tenders")):
        reasons.append("Tender or procurement terms detected.")
        return ("procurement_detail" if positive_score >= 2 else "tender"), reasons
    if any(term in lowered for term in JOB_TERMS):
        reasons.append("Career or job terms detected.")
        return ("job_detail" if "apply" in lowered or "job description" in lowered else "career_list"), reasons
    if positive_score >= 2:
        reasons.append("Opportunity language matched deterministic signals.")
        return "opportunity", reasons
    if any(term in lowered for term in ("about us", "department", "ministry", "authority", "organization")):
        reasons.append("Organization context signals detected.")
        return "organization", reasons
    return "unknown", reasons


def _extract_contact_routes(canonical_url: str, text: str, links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for email in EMAIL_PATTERN.findall(text)[:5]:
        normalized = email.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        local_part = normalized.split("@", 1)[0]
        contact_level = "DIRECT_CONTACT" if "." in local_part or "-" in local_part else "ROLE_CONTACT"
        routes.append(
            {
                "type": "email",
                "value": normalized,
                "contact_level": contact_level,
                "confidence": "high",
                "source_url": canonical_url,
                "evidence_text": normalized,
            }
        )
    for phone in PHONE_PATTERN.findall(text)[:3]:
        normalized = _clean_text(phone)
        if not normalized or len(re.sub(r"\D", "", normalized)) < 7 or normalized in seen:
            continue
        seen.add(normalized)
        routes.append(
            {
                "type": "phone",
                "value": normalized,
                "contact_level": "OFFICIAL_CHANNEL",
                "confidence": "medium",
                "source_url": canonical_url,
                "evidence_text": normalized,
            }
        )
    for link in links:
        href = str(link.get("href") or "")
        anchor = str(link.get("text") or "")
        lowered = f"{href} {anchor}".lower()
        if any(hint in lowered for hint in CONTACT_PATH_HINTS):
            absolute = urljoin(canonical_url, href)
            if absolute in seen:
                continue
            seen.add(absolute)
            routes.append(
                {
                    "type": "contact_url",
                    "value": absolute,
                    "contact_level": "OFFICIAL_CHANNEL",
                    "confidence": "medium",
                    "source_url": canonical_url,
                    "evidence_text": anchor or href,
                }
            )
    return routes


def _extract_parsed_page(final_url: str, html: str, policy: WebFetchRuntimePolicy) -> PageParseResult:
    extractor = LinkExtractor()
    extractor.feed(html)
    text = extract_text_from_webpage(html, max_chars=policy.max_extracted_text_chars)
    title = _clean_text(extractor.title or extractor.meta.get("og:title") or extractor.h1)
    canonical_url, domain = canonicalize_url(final_url)
    page_type, reasons = _page_type(title, canonical_url, text, extractor.meta)
    dates = _extract_dates(" ".join(filter(None, [title or "", text[:6000]])))
    published_at = dates[0] if dates else None
    closing_at = dates[-1] if len(dates) >= 2 else None
    budget_min, budget_max, currency = _extract_budget(text[:6000])
    organization_name = (
        _clean_text(extractor.meta.get("og:site_name"))
        or _clean_text(re.sub(r"[-|].*$", "", title or ""))
        or domain.split(".")[0].replace("-", " ").title()
    )
    links = extractor.links
    contact_routes = _extract_contact_routes(canonical_url, text[:12000], links)
    application_url = None
    for link in links:
        href = str(link.get("href") or "")
        anchor = str(link.get("text") or "").lower()
        if any(term in anchor for term in ("apply", "submit", "register", "procurement portal", "vendor portal")):
            application_url = urljoin(canonical_url, href)
            break
    return PageParseResult(
        canonical_url=canonical_url,
        domain=domain,
        title=title,
        h1=extractor.h1,
        text=text,
        html=html[: min(len(html), 80_000)],
        links=links,
        meta=extractor.meta,
        page_type=page_type,
        type_reasons=reasons,
        published_at=published_at,
        closing_at=closing_at,
        budget_min=budget_min,
        budget_max=budget_max,
        currency=currency,
        organization_name=organization_name,
        country=_detect_country(text),
        contact_routes=contact_routes,
        application_url=application_url,
        reference_number=_extract_reference_number(text[:6000]),
    )


def _search_profile_terms(search_profile: BusinessDevelopmentSearchProfile | None) -> tuple[list[str], list[str]]:
    if not search_profile:
        return [], []
    include = [
        *list(search_profile.include_keywords_json or []),
        *list(search_profile.include_technologies_json or []),
        *list(search_profile.include_capabilities_json or []),
    ]
    exclude = list(search_profile.exclude_keywords_json or [])
    return [_clean_text(item) or "" for item in include if _clean_text(item)], [_clean_text(item) or "" for item in exclude if _clean_text(item)]


def _priority_for_url(
    url: str,
    *,
    anchor_text: str | None,
    context: str | None,
    seed_priority: int,
    search_profile: BusinessDevelopmentSearchProfile | None,
) -> float:
    searchable = " ".join(filter(None, [url, anchor_text, context])).lower()
    include_terms, exclude_terms = _search_profile_terms(search_profile)
    score = float(seed_priority)
    for term in POSITIVE_URL_TERMS:
        if term in searchable:
            score += 6.0
    for term in NEGATIVE_URL_TERMS:
        if term in searchable:
            score -= 10.0
    for term in include_terms[:20]:
        if term.lower() in searchable:
            score += 8.0
    for term in exclude_terms[:20]:
        if term.lower() in searchable:
            score -= 12.0
    return max(0.0, score)


def _build_candidate(
    page: PageParseResult,
    *,
    search_profile: BusinessDevelopmentSearchProfile | None,
    seed: BusinessDevelopmentWebSeed | None,
) -> tuple[AugmisBusinessDiscoveredOpportunityCandidate | None, dict[str, Any]]:
    searchable = " ".join(filter(None, [page.title or "", page.text[:6000]])).lower()
    diagnostics: dict[str, Any] = {
        "eligible": False,
        "source_type": "web_discovery",
        "page_type": page.page_type,
        "reason_codes": [],
        "reason_details": [],
        "detail_signal_count": _page_detail_signal_count(page.title, page.canonical_url, page.text),
    }
    if page.page_type in {"stale_session", "procurement_list", "contact", "irrelevant", "vendor_registration", "organization", "unknown"}:
        diagnostics["reason_codes"] = _limited_codes([f"page_type:{page.page_type}"])
        diagnostics["reason_details"] = _limited_codes(page.type_reasons[:4] or [f"Page classified as {page.page_type}."])
        return None, diagnostics
    if not any(term in searchable for term in OPPORTUNITY_TERMS):
        diagnostics["reason_codes"] = ["missing_opportunity_terms"]
        diagnostics["reason_details"] = ["Opportunity terms were not strong enough to form a candidate."]
        return None, diagnostics
    if any(term in searchable for term in NEGATIVE_CONTENT_TERMS):
        diagnostics["reason_codes"] = ["negative_content"]
        diagnostics["reason_details"] = ["Negative content terms dominated the page text."]
        return None, diagnostics
    include_terms, exclude_terms = _search_profile_terms(search_profile)
    if exclude_terms and any(term.lower() in searchable for term in exclude_terms):
        diagnostics["reason_codes"] = ["profile_excluded_term"]
        diagnostics["reason_details"] = ["Tenant profile exclude terms were detected in the page text."]
        return None, diagnostics
    if page.page_type in {"rfp", "rfq", "eoi", "tender"} and not (
        diagnostics["detail_signal_count"] >= 1 or page.reference_number or page.closing_at or page.budget_max or page.application_url
    ):
        diagnostics["reason_codes"] = ["weak_procurement_detail"]
        diagnostics["reason_details"] = ["Procurement intent was present, but notice-detail signals were too weak to create a candidate."]
        return None, diagnostics
    title = page.title or page.h1 or "Untitled opportunity"
    requirement_summary = _clean_text(page.text[:900]) or title
    evidence = [
        {
            "type": "crawl_page",
            "label": "Independent web discovery",
            "source_url": page.canonical_url,
            "page_type": page.page_type,
            "reasons": page.type_reasons[:5],
        }
    ]
    for route in page.contact_routes[:5]:
        evidence.append(
            {
                "type": "contact_evidence",
                "source_url": route.get("source_url"),
                "value": route.get("value"),
                "contact_level": route.get("contact_level"),
                "confidence": route.get("confidence"),
            }
        )
    source_type = "web_discovery"
    if page.page_type in {"procurement_detail", "rfp", "rfq", "eoi", "tender"}:
        source_type = "public_procurement"
    elif page.page_type in {"job_detail", "career_list"}:
        source_type = "employment_contract"
    diagnostics["eligible"] = True
    diagnostics["source_type"] = source_type
    diagnostics["reason_codes"] = ["candidate_ready"]
    diagnostics["reason_details"] = _limited_codes(page.type_reasons[:4] or ["Candidate passed deterministic crawler eligibility."])
    raw_content_json = {
        "provider": "augmis_internal",
        "page_type": page.page_type,
        "reference_number": page.reference_number,
        "contact_routes": page.contact_routes[:10],
        "application_url": page.application_url,
        "crawl_reasons": page.type_reasons[:10],
        "source_seed_name": seed.name if seed else None,
        "crawler_diagnostics": diagnostics,
    }
    candidate = AugmisBusinessDiscoveredOpportunityCandidate(
        external_id=f"AWD-{_fingerprint(page.canonical_url)}",
        source_type=source_type,
        source_name=INDEPENDENT_WEB_SOURCE_NAME,
        source_url=page.canonical_url,
        source_country=page.country or (seed.country if seed else None),
        title=title[:500],
        organization_name=(page.organization_name or (seed.organization_name if seed else None)),
        published_date=page.published_at,
        closing_date=page.closing_at,
        country=page.country or (seed.country if seed else None),
        industry=seed.industry if seed else None,
        requirement_summary=requirement_summary,
        raw_summary=_clean_text(page.text[:400]),
        raw_text=page.text[:12000],
        budget_min=page.budget_min,
        budget_max=page.budget_max,
        currency=page.currency,
        evidence=evidence,
        source_metadata={
            "provider": "augmis_internal",
            "opportunity_class": page.page_type,
            "contact_routes": page.contact_routes[:10],
            "contact_source_level": page.contact_routes[0]["contact_level"] if page.contact_routes else "NO_PUBLIC_CONTACT",
            "application_url": page.application_url,
            "reference_number": page.reference_number,
            "crawl_source": "independent_seeded_web",
            "seed_name": seed.name if seed else None,
            "crawler_diagnostics": diagnostics,
        },
        raw_content_json=raw_content_json,
        retrieval_timestamp=_now(),
    )
    return candidate, diagnostics


def _is_likely_detail_link(url: str, anchor_text: str | None, context: str | None) -> bool:
    searchable = " ".join(filter(None, [url, anchor_text or "", context or ""])).lower()
    if any(term in searchable for term in ("tender", "rfp", "rfq", "eoi", "bid", "notice", "corrigendum")):
        return True
    if re.search(r"\b(?:tender|bid|rfp|rfq|eoi)[\s#:/._-]*[a-z0-9]{2,}\b", searchable):
        return True
    if re.search(r"\b\d{4}[-/]\d{2,}\b", searchable):
        return True
    return False


def _serialize_seed(row: BusinessDevelopmentWebSeed) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "connector_id": row.connector_id,
        "name": row.name,
        "seed_url": row.seed_url,
        "seed_type": row.seed_type,
        "enabled": row.enabled,
        "crawl_scope": row.crawl_scope,
        "max_depth": row.max_depth,
        "max_pages": row.max_pages,
        "crawl_frequency": row.crawl_frequency,
        "priority": row.priority,
        "country": row.country,
        "industry": row.industry,
        "organization_name": row.organization_name,
        "notes": row.notes,
        "last_crawled_at": _serialize_datetime(row.last_crawled_at),
        "next_crawl_at": _serialize_datetime(row.next_crawl_at),
        "created_by": row.created_by,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def _serialize_domain(row: BusinessDevelopmentWebDomain) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "connector_id": row.connector_id,
        "seed_id": row.seed_id,
        "domain": row.domain,
        "source": row.source,
        "proposed_type": row.proposed_type,
        "trust_source_type": row.trust_source_type,
        "enabled": row.enabled,
        "approval_status": row.approval_status,
        "robots_status": row.robots_status,
        "robots_crawl_delay_seconds": row.robots_crawl_delay_seconds,
        "robots_fetched_at": _serialize_datetime(row.robots_fetched_at),
        "robots_url": row.robots_url,
        "found_from_url": row.found_from_url,
        "found_context": row.found_context,
        "pages_indexed": row.pages_indexed,
        "opportunities_found": row.opportunities_found,
        "error_count": row.error_count,
        "last_crawl_at": _serialize_datetime(row.last_crawl_at),
        "next_crawl_at": _serialize_datetime(row.next_crawl_at),
        "status": row.status,
        "created_by": row.created_by,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def _serialize_page(row: BusinessDevelopmentWebPage) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "connector_id": row.connector_id,
        "seed_id": row.seed_id,
        "domain_id": row.domain_id,
        "url": row.url,
        "canonical_url": row.canonical_url,
        "domain": row.domain,
        "title": row.title,
        "plain_text": row.plain_text,
        "safe_html": row.safe_html,
        "language": row.language,
        "page_type": row.page_type,
        "published_at": _serialize_datetime(row.published_at),
        "last_modified_at": _serialize_datetime(row.last_modified_at),
        "content_hash": row.content_hash,
        "first_seen_at": _serialize_datetime(row.first_seen_at),
        "last_seen_at": _serialize_datetime(row.last_seen_at),
        "last_changed_at": _serialize_datetime(row.last_changed_at),
        "http_status": row.http_status,
        "source_metadata_json": row.source_metadata_json or {},
        "contact_routes_json": row.contact_routes_json or [],
        "opportunity_candidate_json": row.opportunity_candidate_json or {},
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def _require_connector(db: Session, tenant_id: str, connector_id: str) -> BusinessDevelopmentConnector:
    row = (
        db.query(BusinessDevelopmentConnector)
        .filter(
            BusinessDevelopmentConnector.tenant_id == tenant_id,
            BusinessDevelopmentConnector.id == connector_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Connector not found.")
    if row.connector_type != INDEPENDENT_WEB_CONNECTOR_TYPE:
        raise HTTPException(status_code=400, detail="Connector is not the independent web discovery engine.")
    return row


def _require_seed(db: Session, tenant_id: str, connector_id: str, seed_id: str) -> BusinessDevelopmentWebSeed:
    row = (
        db.query(BusinessDevelopmentWebSeed)
        .filter(
            BusinessDevelopmentWebSeed.tenant_id == tenant_id,
            BusinessDevelopmentWebSeed.connector_id == connector_id,
            BusinessDevelopmentWebSeed.id == seed_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Seed not found.")
    return row


def _require_domain(db: Session, tenant_id: str, connector_id: str, domain_id: str) -> BusinessDevelopmentWebDomain:
    row = (
        db.query(BusinessDevelopmentWebDomain)
        .filter(
            BusinessDevelopmentWebDomain.tenant_id == tenant_id,
            BusinessDevelopmentWebDomain.connector_id == connector_id,
            BusinessDevelopmentWebDomain.id == domain_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Domain not found.")
    return row


def list_web_seeds(db: Session, tenant_id: str, connector_id: str) -> dict[str, Any]:
    _require_connector(db, tenant_id, connector_id)
    rows = (
        db.query(BusinessDevelopmentWebSeed)
        .filter(
            BusinessDevelopmentWebSeed.tenant_id == tenant_id,
            BusinessDevelopmentWebSeed.connector_id == connector_id,
        )
        .order_by(desc(BusinessDevelopmentWebSeed.priority), asc(BusinessDevelopmentWebSeed.name))
        .all()
    )
    return {"success": True, "data": [_serialize_seed(row) for row in rows]}


def create_web_seed(
    db: Session,
    tenant_id: str,
    connector_id: str,
    current_user: dict,
    payload: AugmisBusinessWebSeedCreateRequest,
) -> dict[str, Any]:
    _require_connector(db, tenant_id, connector_id)
    canonical_url, _ = _as_public_url(payload.seed_url)
    row = BusinessDevelopmentWebSeed(
        id=f"BD-WSEED-{_fingerprint(canonical_url)}",
        tenant_id=tenant_id,
        connector_id=connector_id,
        name=payload.name,
        seed_url=canonical_url,
        seed_type=payload.seed_type,
        enabled=payload.enabled,
        crawl_scope=payload.crawl_scope,
        max_depth=payload.max_depth,
        max_pages=payload.max_pages,
        crawl_frequency=payload.crawl_frequency,
        priority=payload.priority,
        country=payload.country,
        industry=payload.industry,
        organization_name=payload.organization_name,
        notes=payload.notes,
        next_crawl_at=_now(),
        created_by=current_user["user_id"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="CREATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Added independent discovery seed {row.name}",
        resource_type="bd_web_seed",
        resource_id=row.id,
        metadata={"connector_id": connector_id, "seed_url": row.seed_url},
    )
    return {"success": True, "data": _serialize_seed(row)}


def update_web_seed(
    db: Session,
    tenant_id: str,
    connector_id: str,
    seed_id: str,
    current_user: dict,
    payload: AugmisBusinessWebSeedUpdateRequest,
) -> dict[str, Any]:
    row = _require_seed(db, tenant_id, connector_id, seed_id)
    changes = payload.model_dump(exclude_unset=True)
    if "seed_url" in changes and changes["seed_url"]:
        canonical_url, _ = _as_public_url(str(changes["seed_url"]))
        changes["seed_url"] = canonical_url
    for key, value in changes.items():
        setattr(row, key, value)
    if row.enabled and row.next_crawl_at is None:
        row.next_crawl_at = _now()
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated independent discovery seed {row.name}",
        resource_type="bd_web_seed",
        resource_id=row.id,
        metadata={"connector_id": connector_id, "changes": sorted(changes.keys())},
    )
    return {"success": True, "data": _serialize_seed(row)}


def delete_web_seed(
    db: Session,
    tenant_id: str,
    connector_id: str,
    seed_id: str,
    current_user: dict,
) -> dict[str, Any]:
    row = _require_seed(db, tenant_id, connector_id, seed_id)
    seed_name = row.name
    db.delete(row)
    db.commit()
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="DELETE",
        event_category="AUGMIS_BUSINESS",
        description=f"Deleted independent discovery seed {seed_name}",
        resource_type="bd_web_seed",
        resource_id=seed_id,
        metadata={"connector_id": connector_id},
    )
    return {"success": True, "deleted": 1}


def list_web_domains(db: Session, tenant_id: str, connector_id: str) -> dict[str, Any]:
    _require_connector(db, tenant_id, connector_id)
    rows = (
        db.query(BusinessDevelopmentWebDomain)
        .filter(
            BusinessDevelopmentWebDomain.tenant_id == tenant_id,
            BusinessDevelopmentWebDomain.connector_id == connector_id,
        )
        .order_by(desc(BusinessDevelopmentWebDomain.opportunities_found), asc(BusinessDevelopmentWebDomain.domain))
        .all()
    )
    return {"success": True, "data": [_serialize_domain(row) for row in rows]}


def update_web_domain(
    db: Session,
    tenant_id: str,
    connector_id: str,
    domain_id: str,
    current_user: dict,
    payload: AugmisBusinessWebDomainUpdateRequest,
) -> dict[str, Any]:
    row = _require_domain(db, tenant_id, connector_id, domain_id)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated domain policy for {row.domain}",
        resource_type="bd_web_domain",
        resource_id=row.id,
        metadata={"connector_id": connector_id, "changes": sorted(changes.keys())},
    )
    return {"success": True, "data": _serialize_domain(row)}


def recrawl_web_domain(
    db: Session,
    tenant_id: str,
    connector_id: str,
    domain_id: str,
    current_user: dict,
) -> dict[str, Any]:
    row = _require_domain(db, tenant_id, connector_id, domain_id)
    row.next_crawl_at = _now()
    row.status = "queued"
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="RUN",
        event_category="AUGMIS_BUSINESS",
        description=f"Queued manual domain recrawl for {row.domain}",
        resource_type="bd_web_domain",
        resource_id=row.id,
        metadata={"connector_id": connector_id},
    )
    return {"success": True, "data": _serialize_domain(row)}


def list_web_pages(
    db: Session,
    tenant_id: str,
    connector_id: str,
    *,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
) -> dict[str, Any]:
    _require_connector(db, tenant_id, connector_id)
    query = db.query(BusinessDevelopmentWebPage).filter(
        BusinessDevelopmentWebPage.tenant_id == tenant_id,
        BusinessDevelopmentWebPage.connector_id == connector_id,
    )
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            (BusinessDevelopmentWebPage.title.ilike(pattern))
            | (BusinessDevelopmentWebPage.domain.ilike(pattern))
            | (BusinessDevelopmentWebPage.canonical_url.ilike(pattern))
        )
    total = query.count()
    rows = (
        query.order_by(desc(BusinessDevelopmentWebPage.last_seen_at))
        .offset(max(page - 1, 0) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "success": True,
        "data": [_serialize_page(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def test_web_fetch_url(
    db: Session,
    tenant_id: str,
    connector_id: str,
    payload: AugmisBusinessWebFetchTestRequest,
) -> dict[str, Any]:
    connector = _require_connector(db, tenant_id, connector_id)
    if connector.connector_type != INDEPENDENT_WEB_CONNECTOR_TYPE:
        raise HTTPException(status_code=400, detail="URL fetch testing is only supported for the independent web discovery connector.")
    policy = _runtime_policy(dict(connector.configuration_json or {}))
    canonical_url, domain = _as_public_url(payload.url)
    referer = _same_origin_referer(payload.parent_url, canonical_url)
    robots_status = "not_checked"
    robots_allowed = None
    try:
        robots_row = BusinessDevelopmentWebDomain(
            id="diagnostic-domain",
            tenant_id=tenant_id,
            connector_id=connector_id,
            domain=domain,
            robots_status="unknown",
        )
        robots = _fetch_robots(robots_row, policy)
        if robots.parser:
            robots_allowed = bool(robots.parser.can_fetch(settings.AUGMIS_WEB_DISCOVERY_USER_AGENT, canonical_url))
            robots_status = "allowed" if robots_allowed else "denied"
        else:
            robots_allowed = True
            robots_status = robots.status
    except Exception:
        robots_allowed = None
        robots_status = "unavailable"

    if robots_allowed is False:
        return {
            "success": True,
            "data": {
                "url": canonical_url,
                "allowed_by_policy": True,
                "robots_status": robots_status,
                "robots_allowed": False,
                "fetch_decision": "FAILED",
                "failure_code": "ROBOTS_DENIED",
                "failure_reason": _diagnostic_message("ROBOTS_DENIED"),
            },
        }

    session_bound_reasons = _session_bound_url_reasons(canonical_url)
    if session_bound_reasons:
        return {
            "success": True,
            "data": {
                "url": canonical_url,
                "allowed_by_policy": True,
                "robots_status": robots_status,
                "robots_allowed": robots_allowed,
                "fetch_decision": "SESSION_BOUND_URL",
                "failure_code": "SESSION_BOUND_URL",
                "failure_reason": "URL appears bound to a transient public session and is not a durable follow-up target.",
                "session_bound_reasons": session_bound_reasons,
            },
        }

    session = requests.Session()
    try:
        result = fetch_public_webpage(canonical_url, policy=policy, session=session, referer=referer)
        html = str(result.get("body") or "")
        parsed = _extract_parsed_page(str(result.get("url") or canonical_url), html, policy)
        return {
            "success": True,
            "data": {
                "url": canonical_url,
                "allowed_by_policy": True,
                "robots_status": robots_status,
                "robots_allowed": robots_allowed,
                "http_status": result.get("status_code"),
                "final_url": result.get("final_url") or result.get("url"),
                "redirect_count": result.get("redirect_count"),
                "redirect_chain": result.get("redirect_chain") or [],
                "content_type": result.get("content_type"),
                "response_bytes": result.get("response_bytes") or result.get("bytes_read"),
                "server": result.get("server"),
                "retry_after": result.get("retry_after"),
                "dns_result": result.get("dns_result") or [],
                "page_title": parsed.title,
                "page_type": parsed.page_type,
                "fetch_decision": "FETCHABLE" if parsed.page_type not in {"stale_session", "dynamic_content_only"} else parsed.page_type.upper(),
                "failure_code": None,
                "failure_reason": None,
            },
        }
    except SafeWebFetchError as exc:
        diagnostic = exc.to_diagnostic()
        return {
            "success": True,
            "data": {
                "url": canonical_url,
                "allowed_by_policy": True,
                "robots_status": robots_status,
                "robots_allowed": robots_allowed,
                "fetch_decision": "FAILED",
                "failure_code": diagnostic.get("error_code"),
                "failure_reason": diagnostic.get("error_message"),
                **diagnostic,
            },
        }
    finally:
        session.close()


def _ensure_domain(
    db: Session,
    *,
    tenant_id: str,
    connector_id: str,
    seed: BusinessDevelopmentWebSeed | None,
    domain: str,
    source: str,
    found_from_url: str | None,
    found_context: str | None,
    default_approval: str = "approved",
) -> BusinessDevelopmentWebDomain:
    row = (
        db.query(BusinessDevelopmentWebDomain)
        .filter(
            BusinessDevelopmentWebDomain.tenant_id == tenant_id,
            BusinessDevelopmentWebDomain.connector_id == connector_id,
            BusinessDevelopmentWebDomain.domain == domain,
        )
        .first()
    )
    if row:
        return row
    row = BusinessDevelopmentWebDomain(
        id=f"BD-WDOM-{_fingerprint(f'{tenant_id}:{connector_id}:{domain}')}",
        tenant_id=tenant_id,
        connector_id=connector_id,
        seed_id=seed.id if seed else None,
        domain=domain,
        source=source,
        proposed_type=seed.seed_type if seed else None,
        trust_source_type=_source_trust_for_domain(domain),
        approval_status=default_approval,
        found_from_url=found_from_url,
        found_context=_clean_text(found_context),
        next_crawl_at=_now(),
    )
    db.add(row)
    db.flush()
    return row


def _enqueue_frontier_url(
    db: Session,
    *,
    tenant_id: str,
    connector_id: str,
    seed: BusinessDevelopmentWebSeed | None,
    domain_row: BusinessDevelopmentWebDomain | None,
    url: str,
    parent_url: str | None,
    anchor_text: str | None,
    context: str | None,
    depth: int,
    priority: float,
) -> BusinessDevelopmentWebFrontier | None:
    try:
        canonical_url, domain = _as_public_url(url)
    except Exception:
        return None
    row = (
        db.query(BusinessDevelopmentWebFrontier)
        .filter(
            BusinessDevelopmentWebFrontier.tenant_id == tenant_id,
            BusinessDevelopmentWebFrontier.connector_id == connector_id,
            BusinessDevelopmentWebFrontier.canonical_url == canonical_url,
        )
        .first()
    )
    if row:
        if row.priority < priority:
            row.priority = priority
        next_fetch_at = _as_utc(row.next_fetch_at) or _now()
        if row.status in {"failed", "skipped", "blocked", "robots_denied"} and next_fetch_at <= _now():
            row.status = "queued"
            row.next_fetch_at = _now()
        return row
    row = BusinessDevelopmentWebFrontier(
        id=f"BD-WFR-{_fingerprint(f'{tenant_id}:{connector_id}:{canonical_url}')}",
        tenant_id=tenant_id,
        connector_id=connector_id,
        seed_id=seed.id if seed else None,
        domain_id=domain_row.id if domain_row else None,
        url=canonical_url,
        canonical_url=canonical_url,
        domain=domain,
        parent_url=parent_url,
        anchor_text=_clean_text(anchor_text),
        link_context=_clean_text(context),
        depth=depth,
        priority=priority,
        status="queued",
        next_fetch_at=_now(),
    )
    db.add(row)
    db.flush()
    return row


def _fetch_robots(domain_row: BusinessDevelopmentWebDomain, policy: WebFetchRuntimePolicy) -> RobotsPolicy:
    robots_url = f"https://{domain_row.domain}/robots.txt"
    fetched_at = _now()
    try:
        result = fetch_public_text_resource(robots_url, policy=policy)
        parser = robotparser.RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(str(result.get("body") or "").splitlines())
        crawl_delay = parser.crawl_delay(settings.AUGMIS_WEB_DISCOVERY_USER_AGENT) or parser.crawl_delay("*") or settings.AUGMIS_WEB_DISCOVERY_MIN_DOMAIN_DELAY_SECONDS
        crawl_delay = _clamp(int(crawl_delay), settings.AUGMIS_WEB_DISCOVERY_MIN_DOMAIN_DELAY_SECONDS, settings.AUGMIS_WEB_DISCOVERY_MAX_DOMAIN_DELAY_SECONDS)
        domain_row.robots_status = "fetched"
        domain_row.robots_fetched_at = fetched_at
        domain_row.robots_crawl_delay_seconds = crawl_delay
        domain_row.robots_url = robots_url
        return RobotsPolicy(True, crawl_delay, "fetched", robots_url, fetched_at, parser)
    except SafeWebFetchError:
        domain_row.robots_status = "unavailable"
        domain_row.robots_fetched_at = fetched_at
        domain_row.robots_crawl_delay_seconds = settings.AUGMIS_WEB_DISCOVERY_MIN_DOMAIN_DELAY_SECONDS
        domain_row.robots_url = robots_url
        return RobotsPolicy(True, domain_row.robots_crawl_delay_seconds, "unavailable", robots_url, fetched_at, None)


def _robots_policy_for_frontier(
    db: Session,
    *,
    tenant_id: str,
    connector_id: str,
    seed: BusinessDevelopmentWebSeed | None,
    domain: str,
    found_from_url: str | None,
    found_context: str | None,
    policy: WebFetchRuntimePolicy,
) -> tuple[BusinessDevelopmentWebDomain, RobotsPolicy]:
    domain_row = _ensure_domain(
        db,
        tenant_id=tenant_id,
        connector_id=connector_id,
        seed=seed,
        domain=domain,
        source="seed" if seed else "crawl",
        found_from_url=found_from_url,
        found_context=found_context,
        default_approval="approved" if seed else "pending_review",
    )
    robots_fetched_at = _as_utc(domain_row.robots_fetched_at)
    needs_refresh = robots_fetched_at is None or robots_fetched_at < (_now() - timedelta(days=7))
    robots = _fetch_robots(domain_row, policy) if needs_refresh else RobotsPolicy(
        True,
        domain_row.robots_crawl_delay_seconds or settings.AUGMIS_WEB_DISCOVERY_MIN_DOMAIN_DELAY_SECONDS,
        domain_row.robots_status,
        domain_row.robots_url,
        robots_fetched_at,
        None,
    )
    return domain_row, robots


class IndependentWebDiscoveryEngine:
    def __init__(
        self,
        db: Session,
        connector: BusinessDevelopmentConnector,
        search_profile: BusinessDevelopmentSearchProfile | None,
    ) -> None:
        self.db = db
        self.connector = connector
        self.search_profile = search_profile
        self.config = dict(connector.configuration_json or {})
        self.policy = _runtime_policy(self.config)
        self.started_at = _now()
        self.metrics = {
            "provider": "augmis_internal",
            "seeds_processed": 0,
            "domains_visited": 0,
            "urls_queued": 0,
            "pages_attempted": 0,
            "pages_fetched": 0,
            "pages_unchanged": 0,
            "pages_changed": 0,
            "robots_denied": 0,
            "pages_blocked": 0,
            "opportunity_candidates": 0,
            "opportunity_like_pages": 0,
            "detail_pages": 0,
            "listing_pages": 0,
            "unknown_pages": 0,
            "stale_or_error_pages": 0,
            "dynamic_content_only_pages": 0,
            "new_discovered_domains": 0,
            "duplicates": 0,
            "contacts_found": 0,
            "errors": 0,
            "classification_counts": {},
            "candidate_visibility_counts": {},
            "candidate_exclusion_reason_counts": {},
            "fetch_failure_counts": {},
            "fetch_failure_samples": [],
            "detail_links_discovered": 0,
            "detail_links_queued": 0,
            "detail_links_skipped_depth": 0,
            "detail_links_skipped_domain_policy": 0,
            "detail_links_fetch_failed": 0,
            "detail_links_robots_denied": 0,
        }
        self.visited_domains: set[str] = set()
        self.seed_by_id: dict[str, BusinessDevelopmentWebSeed] = {}
        self.listing_detail_links_discovered: set[str] = set()
        self.listing_detail_links_queued: set[str] = set()
        self.http_sessions: dict[str, requests.Session] = {}

    def _session_for_domain(self, domain: str) -> requests.Session:
        session = self.http_sessions.get(domain)
        if session is None:
            session = requests.Session()
            self.http_sessions[domain] = session
        return session

    def _close_sessions(self) -> None:
        for session in self.http_sessions.values():
            session.close()
        self.http_sessions.clear()

    def validate_config(self) -> None:
        if int(self.config.get("maximum_domains_per_run", 5) or 5) < 1:
            raise HTTPException(status_code=400, detail="Independent web discovery requires at least one domain per run.")

    def _max_domains_per_run(self) -> int:
        return _clamp(
            int(self.config.get("maximum_domains_per_run", 5) or 5),
            1,
            settings.AUGMIS_WEB_DISCOVERY_MAX_DOMAINS_PER_RUN,
        )

    def _max_pages_per_domain(self) -> int:
        return _clamp(
            int(self.config.get("maximum_pages_per_domain", 25) or 25),
            1,
            settings.AUGMIS_WEB_DISCOVERY_MAX_PAGES_PER_DOMAIN,
        )

    def _max_total_pages(self) -> int:
        return _clamp(
            int(self.config.get("maximum_total_pages_per_run", 100) or 100),
            1,
            settings.AUGMIS_WEB_DISCOVERY_MAX_TOTAL_PAGES_PER_RUN,
        )

    def _max_depth(self) -> int:
        return _clamp(
            int(self.config.get("maximum_depth", 2) or 2),
            0,
            settings.AUGMIS_WEB_DISCOVERY_MAX_DEPTH,
        )

    def _max_links_per_page(self) -> int:
        return _clamp(
            int(self.config.get("maximum_links_per_page", 40) or 40),
            1,
            settings.AUGMIS_WEB_DISCOVERY_MAX_LINKS_PER_PAGE,
        )

    def _run_duration_limit(self) -> int:
        return _clamp(
            int(self.config.get("maximum_run_duration_seconds", 180) or 180),
            30,
            settings.AUGMIS_WEB_DISCOVERY_MAX_RUN_DURATION_SECONDS,
        )

    def _domain_delay(self, domain_row: BusinessDevelopmentWebDomain) -> int:
        configured = _clamp(
            int(self.config.get("per_domain_delay_seconds", settings.AUGMIS_WEB_DISCOVERY_MIN_DOMAIN_DELAY_SECONDS) or settings.AUGMIS_WEB_DISCOVERY_MIN_DOMAIN_DELAY_SECONDS),
            settings.AUGMIS_WEB_DISCOVERY_MIN_DOMAIN_DELAY_SECONDS,
            settings.AUGMIS_WEB_DISCOVERY_MAX_DOMAIN_DELAY_SECONDS,
        )
        robots_delay = domain_row.robots_crawl_delay_seconds or configured
        return max(configured, robots_delay)

    def _seed_rows(self) -> list[BusinessDevelopmentWebSeed]:
        rows = (
            self.db.query(BusinessDevelopmentWebSeed)
            .filter(
                BusinessDevelopmentWebSeed.tenant_id == self.connector.tenant_id,
                BusinessDevelopmentWebSeed.connector_id == self.connector.id,
                BusinessDevelopmentWebSeed.enabled.is_(True),
            )
            .order_by(desc(BusinessDevelopmentWebSeed.priority), asc(BusinessDevelopmentWebSeed.next_crawl_at))
            .all()
        )
        self.seed_by_id = {row.id: row for row in rows}
        return rows

    def _seed_frontier(self, seed: BusinessDevelopmentWebSeed) -> None:
        canonical_url, domain = _as_public_url(seed.seed_url)
        domain_row = _ensure_domain(
            self.db,
            tenant_id=self.connector.tenant_id,
            connector_id=self.connector.id,
            seed=seed,
            domain=domain,
            source="seed",
            found_from_url=canonical_url,
            found_context=seed.name,
            default_approval="approved",
        )
        _enqueue_frontier_url(
            self.db,
            tenant_id=self.connector.tenant_id,
            connector_id=self.connector.id,
            seed=seed,
            domain_row=domain_row,
            url=canonical_url,
            parent_url=None,
            anchor_text=seed.name,
            context=seed.notes,
            depth=0,
            priority=float(seed.priority),
        )
        if seed.seed_type == "sitemap" or canonical_url.endswith("sitemap.xml"):
            self._queue_sitemap(seed, domain_row, canonical_url)
        self.metrics["seeds_processed"] += 1

    def _queue_sitemap(self, seed: BusinessDevelopmentWebSeed, domain_row: BusinessDevelopmentWebDomain, sitemap_url: str) -> None:
        try:
            result = fetch_public_text_resource(sitemap_url, policy=self.policy)
            root = ElementTree.fromstring(str(result.get("body") or ""))
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            urls = [node.text for node in root.findall(".//sm:loc", ns) if node.text][: self._max_pages_per_domain()]
            for discovered_url in urls:
                _enqueue_frontier_url(
                    self.db,
                    tenant_id=self.connector.tenant_id,
                    connector_id=self.connector.id,
                    seed=seed,
                    domain_row=domain_row,
                    url=discovered_url,
                    parent_url=sitemap_url,
                    anchor_text="sitemap",
                    context="Sitemap discovery",
                    depth=1,
                    priority=float(seed.priority) + 12.0,
                )
                self.metrics["urls_queued"] += 1
        except Exception:
            self.metrics["errors"] += 1

    def _pick_frontier(self) -> BusinessDevelopmentWebFrontier | None:
        rows = (
            self.db.query(BusinessDevelopmentWebFrontier)
            .filter(
                BusinessDevelopmentWebFrontier.tenant_id == self.connector.tenant_id,
                BusinessDevelopmentWebFrontier.connector_id == self.connector.id,
                BusinessDevelopmentWebFrontier.status == "queued",
                (BusinessDevelopmentWebFrontier.next_fetch_at.is_(None) | (BusinessDevelopmentWebFrontier.next_fetch_at <= _now())),
            )
            .order_by(desc(BusinessDevelopmentWebFrontier.priority), asc(BusinessDevelopmentWebFrontier.discovered_at))
            .limit(50)
            .all()
        )
        domain_page_counts = {
            domain: count
            for domain, count in (
                self.db.query(
                    BusinessDevelopmentWebPage.domain,
                    func.count(BusinessDevelopmentWebPage.id),
                )
                .filter(
                    BusinessDevelopmentWebPage.tenant_id == self.connector.tenant_id,
                    BusinessDevelopmentWebPage.connector_id == self.connector.id,
                )
                .group_by(BusinessDevelopmentWebPage.domain)
                .all()
            )
        }
        for frontier in rows:
            if frontier.depth > self._max_depth():
                frontier.status = "blocked"
                frontier.error_code = "DEPTH_LIMIT"
                continue
            if domain_page_counts.get(frontier.domain, 0) >= self._max_pages_per_domain():
                frontier.status = "blocked"
                frontier.error_code = "DOMAIN_PAGE_LIMIT"
                continue
            domain_row = (
                self.db.query(BusinessDevelopmentWebDomain)
                .filter(
                    BusinessDevelopmentWebDomain.tenant_id == self.connector.tenant_id,
                    BusinessDevelopmentWebDomain.connector_id == self.connector.id,
                    BusinessDevelopmentWebDomain.domain == frontier.domain,
                )
                .first()
            )
            if domain_row and (not domain_row.enabled or domain_row.approval_status == "ignored"):
                frontier.status = "blocked"
                frontier.error_code = "DOMAIN_DISABLED"
                continue
            if domain_row and frontier.depth > 0 and domain_row.approval_status == "pending_review":
                frontier.status = "blocked"
                frontier.error_code = "DOMAIN_PENDING_REVIEW"
                continue
            last_crawl_at = _as_utc(domain_row.last_crawl_at) if domain_row else None
            if domain_row and last_crawl_at:
                wait_until = last_crawl_at + timedelta(seconds=self._domain_delay(domain_row))
                if wait_until > _now():
                    frontier.next_fetch_at = wait_until
                    continue
            return frontier
        self.db.flush()
        return None

    def _store_page(
        self,
        *,
        frontier: BusinessDevelopmentWebFrontier,
        domain_row: BusinessDevelopmentWebDomain,
        parsed: PageParseResult,
        content_hash: str | None,
        candidate: AugmisBusinessDiscoveredOpportunityCandidate | None,
        candidate_diagnostics: dict[str, Any],
    ) -> None:
        page = (
            self.db.query(BusinessDevelopmentWebPage)
            .filter(
                BusinessDevelopmentWebPage.tenant_id == self.connector.tenant_id,
                BusinessDevelopmentWebPage.connector_id == self.connector.id,
                BusinessDevelopmentWebPage.canonical_url == parsed.canonical_url,
            )
            .first()
        )
        now = _now()
        if page is None:
            page = BusinessDevelopmentWebPage(
                id=f"BD-WPG-{_fingerprint(f'{self.connector.tenant_id}:{self.connector.id}:{parsed.canonical_url}')}",
                tenant_id=self.connector.tenant_id,
                connector_id=self.connector.id,
                seed_id=frontier.seed_id,
                domain_id=domain_row.id,
                url=frontier.url,
                canonical_url=parsed.canonical_url,
                domain=parsed.domain,
                first_seen_at=now,
            )
            self.db.add(page)
        changed = page.content_hash != content_hash
        page.url = frontier.url
        page.seed_id = frontier.seed_id
        page.domain_id = domain_row.id
        page.title = parsed.title
        page.plain_text = parsed.text[:15000]
        page.safe_html = parsed.html
        page.page_type = parsed.page_type
        page.published_at = parsed.published_at
        page.content_hash = content_hash
        page.last_seen_at = now
        page.last_changed_at = now if changed else page.last_changed_at
        page.http_status = frontier.http_status
        page.source_metadata_json = {
            "classification_reasons": parsed.type_reasons,
            "classification_reason_codes": _limited_codes([f"page_type:{parsed.page_type}"]),
            "application_url": parsed.application_url,
            "reference_number": parsed.reference_number,
            "crawl_status": frontier.status,
            "candidate_visibility": candidate_diagnostics,
            "meta": {key: value for key, value in parsed.meta.items() if key in {"description", "og:description", "og:site_name", "og:type"}},
        }
        page.contact_routes_json = parsed.contact_routes[:20]
        page.opportunity_candidate_json = {
            **({} if candidate is None else candidate.model_dump(mode="json")),
            "candidate_visibility": candidate_diagnostics,
        }
        if changed:
            self.metrics["pages_changed"] += 1
        else:
            self.metrics["pages_unchanged"] += 1

    def _discover_links(
        self,
        *,
        frontier: BusinessDevelopmentWebFrontier,
        parsed: PageParseResult,
        seed: BusinessDevelopmentWebSeed | None,
    ) -> None:
        processed = 0
        for link in parsed.links:
            href = str(link.get("href") or "").strip()
            if not href or href.startswith("#") or href.lower().startswith(("mailto:", "tel:", "javascript:", "data:")):
                continue
            absolute = urljoin(parsed.canonical_url, href)
            try:
                canonical_url, target_domain = _as_public_url(absolute)
            except Exception:
                continue
            detail_link = parsed.page_type == "procurement_list" and _is_likely_detail_link(
                canonical_url,
                str(link.get("text") or ""),
                parsed.title,
            )
            if detail_link and canonical_url not in self.listing_detail_links_discovered:
                self.listing_detail_links_discovered.add(canonical_url)
                self.metrics["detail_links_discovered"] += 1
            if frontier.depth + 1 > min(self._max_depth(), seed.max_depth if seed else self._max_depth()):
                if detail_link:
                    self.metrics["detail_links_skipped_depth"] += 1
                continue
            same_domain = target_domain == frontier.domain
            if not same_domain:
                allowed = False
                if seed and seed.crawl_scope == "cross_domain_trusted":
                    lowered = f"{canonical_url} {link.get('text') or ''}".lower()
                    allowed = any(term in lowered for term in TRUSTED_PORTAL_TERMS)
                if not allowed:
                    existing_domain = _ensure_domain(
                        self.db,
                        tenant_id=self.connector.tenant_id,
                        connector_id=self.connector.id,
                        seed=seed,
                        domain=target_domain,
                        source="crawl",
                        found_from_url=parsed.canonical_url,
                        found_context=link.get("text"),
                        default_approval="pending_review",
                    )
                    if existing_domain.approval_status == "pending_review":
                        self.metrics["new_discovered_domains"] += 1
                    if detail_link:
                        self.metrics["detail_links_skipped_domain_policy"] += 1
                    continue
            target_domain_row = _ensure_domain(
                self.db,
                tenant_id=self.connector.tenant_id,
                connector_id=self.connector.id,
                seed=seed,
                domain=target_domain,
                source="seed" if same_domain else "crawl",
                found_from_url=parsed.canonical_url,
                found_context=link.get("text"),
                default_approval="approved" if same_domain else "pending_review",
            )
            enqueued = _enqueue_frontier_url(
                self.db,
                tenant_id=self.connector.tenant_id,
                connector_id=self.connector.id,
                seed=seed,
                domain_row=target_domain_row,
                url=canonical_url,
                parent_url=parsed.canonical_url,
                anchor_text=str(link.get("text") or ""),
                context=parsed.title,
                depth=frontier.depth + 1,
                priority=_priority_for_url(
                    canonical_url,
                    anchor_text=str(link.get("text") or ""),
                    context=parsed.title,
                    seed_priority=seed.priority if seed else 50,
                    search_profile=self.search_profile,
                ),
            )
            if enqueued is not None:
                self.metrics["urls_queued"] += 1
                if detail_link and canonical_url not in self.listing_detail_links_queued:
                    self.listing_detail_links_queued.add(canonical_url)
                    self.metrics["detail_links_queued"] += 1
            processed += 1
            if processed >= self._max_links_per_page():
                break

    def run(self) -> tuple[list[AugmisBusinessDiscoveredOpportunityCandidate], dict[str, Any]]:
        self.validate_config()
        seeds = self._seed_rows()
        if not seeds:
            return [], {**self.metrics, "status": "no_seeds"}
        max_seeds = _clamp(int(self.config.get("maximum_seeds_per_run", 5) or 5), 1, len(seeds))
        for seed in seeds[:max_seeds]:
            next_crawl_at = _as_utc(seed.next_crawl_at)
            if next_crawl_at and next_crawl_at > _now():
                continue
            self._seed_frontier(seed)
        self.db.flush()
        discoveries: list[AugmisBusinessDiscoveredOpportunityCandidate] = []
        try:
            while self.metrics["pages_fetched"] < self._max_total_pages():
                if (_now() - self.started_at).total_seconds() >= self._run_duration_limit():
                    break
                frontier = self._pick_frontier()
                if frontier is None:
                    break
                seed = self.seed_by_id.get(frontier.seed_id) if frontier.seed_id else None
                domain_row, robots = _robots_policy_for_frontier(
                    self.db,
                    tenant_id=self.connector.tenant_id,
                    connector_id=self.connector.id,
                    seed=seed,
                    domain=frontier.domain,
                    found_from_url=frontier.parent_url,
                    found_context=frontier.anchor_text,
                    policy=self.policy,
                )
                if robots.parser and not robots.parser.can_fetch(settings.AUGMIS_WEB_DISCOVERY_USER_AGENT, frontier.canonical_url):
                    frontier.status = "robots_denied"
                    frontier.error_code = "ROBOTS_DENIED"
                    frontier.error_message = _diagnostic_message("ROBOTS_DENIED")
                    frontier.diagnostic_json = {
                        "error_code": "ROBOTS_DENIED",
                        "error_message": frontier.error_message,
                        "http_status": None,
                        "final_url": frontier.canonical_url,
                        "redirect_count": 0,
                        "content_type": None,
                        "response_bytes": None,
                        "exception_class": None,
                        "attempted_at": _now().isoformat(),
                        "retryable": False,
                        "server": None,
                        "retry_after": None,
                    }
                    frontier.next_fetch_at = None
                    domain_row.robots_status = "denied"
                    self.metrics["robots_denied"] += 1
                    if frontier.canonical_url in self.listing_detail_links_queued:
                        self.metrics["detail_links_robots_denied"] += 1
                    self.db.flush()
                    continue
                frontier.status = "fetching"
                frontier.last_attempted_at = _now()
                self.metrics["pages_attempted"] += 1
                detail_link_queued = frontier.canonical_url in self.listing_detail_links_queued
                session_bound_reasons = _session_bound_url_reasons(frontier.canonical_url)
                if session_bound_reasons:
                    _apply_frontier_failure(
                        frontier,
                        diagnostic={
                            "error_code": "SESSION_BOUND_URL",
                            "error_message": "URL appears bound to a transient public session and will not be retried as a durable link.",
                            "http_status": None,
                            "final_url": frontier.canonical_url,
                            "redirect_count": 0,
                            "content_type": None,
                            "response_bytes": None,
                            "exception_class": None,
                            "attempted_at": _now().isoformat(),
                            "retryable": False,
                            "server": None,
                            "retry_after": None,
                            "session_bound_reasons": session_bound_reasons,
                        },
                        domain_row=domain_row,
                        metrics=self.metrics,
                        detail_link_queued=detail_link_queued,
                    )
                    self.db.flush()
                    continue
                try:
                    result = fetch_public_webpage(
                        frontier.canonical_url,
                        policy=self.policy,
                        session=self._session_for_domain(frontier.domain),
                        referer=_same_origin_referer(frontier.parent_url, frontier.canonical_url),
                    )
                    html = str(result.get("body") or "")
                    frontier.http_status = int(result.get("status_code") or 200)
                    frontier.last_fetched_at = _now()
                    frontier.status = "fetched"
                    frontier.error_code = None
                    frontier.error_message = None
                    frontier.diagnostic_json = {
                        "error_code": None,
                        "error_message": None,
                        "http_status": frontier.http_status,
                        "final_url": result.get("final_url") or result.get("url") or frontier.canonical_url,
                        "redirect_count": int(result.get("redirect_count") or 0),
                        "redirect_chain": list(result.get("redirect_chain") or [])[:8],
                        "content_type": result.get("content_type"),
                        "response_bytes": result.get("response_bytes") or result.get("bytes_read"),
                        "exception_class": None,
                        "attempted_at": frontier.last_fetched_at.isoformat(),
                        "retryable": False,
                        "server": result.get("server"),
                        "retry_after": result.get("retry_after"),
                        "dns_result": list(result.get("dns_result") or [])[:8],
                    }
                    frontier.next_fetch_at = None
                    domain_row.last_crawl_at = frontier.last_fetched_at
                    domain_row.status = "ready"
                    self.visited_domains.add(frontier.domain)
                    self.metrics["pages_fetched"] += 1
                    parsed = _extract_parsed_page(str(result.get("url") or frontier.canonical_url), html, self.policy)
                    if parsed.page_type in {"procurement_list"}:
                        self.metrics["listing_pages"] += 1
                        self.metrics["opportunity_like_pages"] += 1
                    elif parsed.page_type in {"procurement_detail", "tender", "rfp", "rfq", "eoi"}:
                        self.metrics["detail_pages"] += 1
                        self.metrics["opportunity_like_pages"] += 1
                    elif parsed.page_type in {"stale_session", "dynamic_content_only"}:
                        self.metrics["stale_or_error_pages"] += 1
                        if parsed.page_type == "dynamic_content_only":
                            self.metrics["dynamic_content_only_pages"] += 1
                    elif parsed.page_type == "unknown":
                        self.metrics["unknown_pages"] += 1
                    content_hash = _content_hash(parsed.text)
                    candidate, candidate_diagnostics = _build_candidate(parsed, search_profile=self.search_profile, seed=seed)
                    visibility_key = "eligible" if candidate_diagnostics.get("eligible") else "excluded"
                    self.metrics["candidate_visibility_counts"][visibility_key] = int(
                        self.metrics["candidate_visibility_counts"].get(visibility_key, 0)
                    ) + 1
                    if not candidate_diagnostics.get("eligible"):
                        for code in candidate_diagnostics.get("reason_codes") or []:
                            self.metrics["candidate_exclusion_reason_counts"][code] = int(
                                self.metrics["candidate_exclusion_reason_counts"].get(code, 0)
                            ) + 1
                    if candidate:
                        discoveries.append(candidate)
                        domain_row.opportunities_found += 1
                        self.metrics["opportunity_candidates"] += 1
                        self.metrics["contacts_found"] += len(parsed.contact_routes)
                    domain_row.pages_indexed += 1
                    self.metrics["classification_counts"][parsed.page_type] = int(self.metrics["classification_counts"].get(parsed.page_type, 0)) + 1
                    self._store_page(
                        frontier=frontier,
                        domain_row=domain_row,
                        parsed=parsed,
                        content_hash=content_hash,
                        candidate=candidate,
                        candidate_diagnostics=candidate_diagnostics,
                    )
                    self._discover_links(frontier=frontier, parsed=parsed, seed=seed)
                    if seed:
                        seed.last_crawled_at = _now()
                        seed.next_crawl_at = _now() + timedelta(hours=_seed_recheck_interval_hours(seed))
                    domain_row.next_crawl_at = _now() + timedelta(hours=_page_recheck_interval_hours(parsed.page_type))
                except SafeWebFetchError as exc:
                    diagnostic = exc.to_diagnostic()
                    _apply_frontier_failure(
                        frontier,
                        diagnostic=diagnostic,
                        domain_row=domain_row,
                        metrics=self.metrics,
                        detail_link_queued=detail_link_queued,
                    )
                    if frontier.error_code == "BODY_TOO_LARGE":
                        self.metrics["pages_blocked"] += 1
                except Exception as exc:
                    _apply_frontier_failure(
                        frontier,
                        diagnostic={
                            "error_code": "UNKNOWN_FETCH_ERROR",
                            "error_message": "Unexpected fetch failure.",
                            "http_status": None,
                            "final_url": frontier.canonical_url,
                            "redirect_count": 0,
                            "content_type": None,
                            "response_bytes": None,
                            "exception_class": type(exc).__name__,
                            "attempted_at": _now().isoformat(),
                            "retryable": False,
                            "server": None,
                            "retry_after": None,
                        },
                        domain_row=domain_row,
                        metrics=self.metrics,
                        detail_link_queued=detail_link_queued,
                    )
                self.db.flush()
                if len(self.visited_domains) >= self._max_domains_per_run():
                    break
            metrics = {
                **self.metrics,
                "domains_visited": len(self.visited_domains),
                "duration_seconds": int((_now() - self.started_at).total_seconds()),
                "status": "completed",
            }
            return discoveries, metrics
        finally:
            self._close_sessions()
