from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


TED_NOTICE_TYPE_PRESETS: dict[str, tuple[str, ...]] = {
    "competition_only": (
        "cn-standard",
        "cn-social",
        "cn-desg",
        "subco",
        "pin-cfc-standard",
        "pin-cfc-social",
        "qu-sy",
    ),
    "competition_and_results": (
        "cn-standard",
        "cn-social",
        "cn-desg",
        "subco",
        "pin-cfc-standard",
        "pin-cfc-social",
        "qu-sy",
        "can-standard",
        "can-social",
        "can-desg",
        "can-tran",
    ),
    "all_supported": (),
}

TED_SOFTWARE_SERVICE_CPV_MAP: list[dict[str, str]] = [
    {"code": "48170000", "label": "Compliance software package"},
    {"code": "48211000", "label": "Platform interconnectivity software package"},
    {"code": "48311000", "label": "Document management software package"},
    {"code": "48311100", "label": "Document management system"},
    {"code": "48331000", "label": "Project management software package"},
    {"code": "48422000", "label": "Software package suites"},
    {"code": "48442000", "label": "Financial systems software package"},
    {"code": "48612000", "label": "Database-management system"},
    {"code": "48783000", "label": "Content management software package"},
    {"code": "48810000", "label": "Information systems"},
    {"code": "72212170", "label": "Compliance software development services"},
    {"code": "72212200", "label": "Networking, Internet and intranet software development services"},
    {"code": "72212311", "label": "Document management software development services"},
    {"code": "72212445", "label": "Customer Relation Management software development services"},
    {"code": "72212451", "label": "Enterprise resource planning software development services"},
    {"code": "72212461", "label": "Analytical or scientific software development services"},
    {"code": "72212463", "label": "Statistical software development services"},
    {"code": "72212482", "label": "Business intelligence software development services"},
    {"code": "72221000", "label": "Business analysis consultancy services"},
    {"code": "72222000", "label": "Information systems or technology strategic review and planning services"},
    {"code": "72222300", "label": "Information technology services"},
    {"code": "72223000", "label": "Information technology requirements review services"},
    {"code": "72224100", "label": "System implementation planning services"},
    {"code": "72227000", "label": "Software integration consultancy services"},
    {"code": "72230000", "label": "Custom software development services"},
    {"code": "72232000", "label": "Development of transaction processing and custom software"},
    {"code": "72240000", "label": "Systems analysis and programming services"},
    {"code": "72243000", "label": "Programming services"},
    {"code": "72245000", "label": "Contract systems analysis and programming services"},
    {"code": "72254000", "label": "Software testing"},
    {"code": "72262000", "label": "Software development services"},
    {"code": "72263000", "label": "Software implementation services"},
    {"code": "72265000", "label": "Software configuration services"},
    {"code": "72266000", "label": "Software consultancy services"},
    {"code": "72267100", "label": "Maintenance of information technology software"},
    {"code": "72300000", "label": "Data services"},
    {"code": "72316000", "label": "Data analysis services"},
    {"code": "72320000", "label": "Database services"},
    {"code": "72322000", "label": "Data management services"},
    {"code": "72413000", "label": "World wide web (www) site design services"},
    {"code": "72414000", "label": "Web search engine providers"},
    {"code": "72420000", "label": "Internet development services"},
    {"code": "72421000", "label": "Internet or intranet client application development services"},
    {"code": "72422000", "label": "Internet or intranet server application development services"},
    {"code": "72512000", "label": "Document management services"},
    {"code": "72513000", "label": "Office automation services"},
]

EU_EEA_COUNTRY_CODES: dict[str, str] = {
    "austria": "AUT",
    "belgium": "BEL",
    "bulgaria": "BGR",
    "croatia": "HRV",
    "cyprus": "CYP",
    "czech republic": "CZE",
    "czechia": "CZE",
    "denmark": "DNK",
    "estonia": "EST",
    "finland": "FIN",
    "france": "FRA",
    "germany": "DEU",
    "greece": "GRC",
    "hungary": "HUN",
    "iceland": "ISL",
    "ireland": "IRL",
    "italy": "ITA",
    "latvia": "LVA",
    "liechtenstein": "LIE",
    "lithuania": "LTU",
    "luxembourg": "LUX",
    "malta": "MLT",
    "netherlands": "NLD",
    "norway": "NOR",
    "poland": "POL",
    "portugal": "PRT",
    "romania": "ROU",
    "slovakia": "SVK",
    "slovenia": "SVN",
    "spain": "ESP",
    "sweden": "SWE",
}

TED_DEFAULT_GROUP_KEYS = (
    "workflow_automation",
    "analytics_reporting",
    "document_records",
    "integration_platforms",
    "inspection_compliance",
)


@dataclass(frozen=True)
class TedQueryGroupDefinition:
    key: str
    label: str
    primary_terms: tuple[str, ...]
    match_terms: tuple[str, ...]
    cpv_codes: tuple[str, ...]


@dataclass(frozen=True)
class TedSearchQuerySpec:
    key: str
    label: str
    query: str
    primary_term: str
    cpv_codes: tuple[str, ...]


TED_QUERY_GROUP_DEFINITIONS: tuple[TedQueryGroupDefinition, ...] = (
    TedQueryGroupDefinition(
        key="workflow_automation",
        label="Workflow Automation",
        primary_terms=("workflow", "automation", "approval", "task tracking"),
        match_terms=(
            "workflow",
            "workflow automation",
            "automation",
            "approval",
            "approval workflow",
            "work management",
            "task tracking",
            "tracking",
            "service workflow",
            "status workflow",
        ),
        cpv_codes=("48810000", "72222300", "72230000", "72262000", "72513000"),
    ),
    TedQueryGroupDefinition(
        key="analytics_reporting",
        label="Analytics and Reporting",
        primary_terms=("analytics", "reporting", "dashboard", "analysis"),
        match_terms=(
            "analytics",
            "analysis",
            "reporting",
            "dashboard",
            "dashboards",
            "kpi",
            "kpi dashboard",
            "statistics",
            "visual analytics",
            "monitoring dashboards",
        ),
        cpv_codes=("48810000", "72212461", "72212463", "72212482", "72316000", "72320000"),
    ),
    TedQueryGroupDefinition(
        key="document_records",
        label="Document and Records",
        primary_terms=("document management", "records management", "document control", "records"),
        match_terms=(
            "document management",
            "records management",
            "document control",
            "document services",
            "document migration",
            "records",
            "ecm",
            "content systems",
            "correspondence management",
        ),
        cpv_codes=("48311000", "48311100", "48783000", "72212311", "72512000"),
    ),
    TedQueryGroupDefinition(
        key="integration_platforms",
        label="Integration and Platforms",
        primary_terms=("integration", "api integration", "portal", "erp"),
        match_terms=(
            "integration",
            "api integration",
            "api integrations",
            "system integration",
            "erp",
            "data migration",
            "portal",
            "enterprise systems",
            "enterprise platforms",
        ),
        cpv_codes=("48211000", "72212200", "72227000", "72421000", "72422000", "72230000"),
    ),
    TedQueryGroupDefinition(
        key="inspection_compliance",
        label="Inspection and Compliance",
        primary_terms=("inspection", "compliance", "laboratory", "calibration"),
        match_terms=(
            "inspection",
            "compliance",
            "compliance review",
            "calibration",
            "laboratory",
            "quality assurance",
            "readiness",
            "environmental monitoring",
        ),
        cpv_codes=("48170000", "48810000", "72212170", "72221000", "72222000"),
    ),
)


def _normalize_terms(values: list[str] | None) -> list[str]:
    seen: OrderedDict[str, None] = OrderedDict()
    for value in values or []:
        normalized = " ".join(str(value or "").strip().lower().split())
        if normalized:
            seen[normalized] = None
    return list(seen.keys())


def _profile_term_set(profile: dict[str, Any]) -> set[str]:
    terms = _normalize_terms(
        list(profile.get("target_industries_json") or [])
        + list(profile.get("include_keywords_json") or [])
        + list(profile.get("include_technologies_json") or [])
        + list(profile.get("include_capabilities_json") or [])
    )
    return set(terms)


def _quote_term(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    if '"' in cleaned:
        cleaned = cleaned.replace('"', "")
    if " " in cleaned or "-" in cleaned:
        return f'"{cleaned}"'
    return cleaned


def _country_code(value: str) -> str | None:
    cleaned = " ".join(str(value or "").strip().lower().split())
    if not cleaned:
        return None
    if cleaned.upper() in EU_EEA_COUNTRY_CODES.values():
        return cleaned.upper()
    return EU_EEA_COUNTRY_CODES.get(cleaned)


def ted_country_scope_codes(
    *,
    profile: dict[str, Any],
    configuration: dict[str, Any],
) -> list[str]:
    scope_mode = str(configuration.get("country_scope_mode", "search_profile") or "search_profile").strip().lower()
    if scope_mode == "eu_eea":
        return sorted(set(EU_EEA_COUNTRY_CODES.values()))
    if scope_mode == "selected":
        selected = configuration.get("selected_countries_json") or []
        return [code for code in (_country_code(item) for item in selected) if code]
    countries = profile.get("target_countries_json") or []
    return [code for code in (_country_code(item) for item in countries) if code]


def ted_notice_type_codes(configuration: dict[str, Any]) -> tuple[str, ...]:
    mode = str(configuration.get("notice_type_mode", "competition_only") or "competition_only").strip().lower()
    return TED_NOTICE_TYPE_PRESETS.get(mode, TED_NOTICE_TYPE_PRESETS["competition_only"])


def ted_cpv_codes(configuration: dict[str, Any]) -> list[str]:
    scope = str(configuration.get("cpv_scope", "broad_software_services") or "broad_software_services").strip().lower()
    if scope != "broad_software_services":
        return []
    return [item["code"] for item in TED_SOFTWARE_SERVICE_CPV_MAP]


def _publication_date_clause(*, configuration: dict[str, Any], now: datetime | None = None) -> str:
    today = now or datetime.now(timezone.utc)
    lookback_days = int(configuration.get("lookback_days", 7) or 7)
    published_from = (today - timedelta(days=lookback_days)).strftime("%Y%m%d")
    published_to = today.strftime("%Y%m%d")
    return f"publication-date = ({published_from} <> {published_to})"


def _notice_type_clause(configuration: dict[str, Any]) -> str:
    notice_type_codes = ted_notice_type_codes(configuration)
    return f"notice-type IN ({' '.join(notice_type_codes)})" if notice_type_codes else ""


def _country_clause(*, profile: dict[str, Any], configuration: dict[str, Any]) -> str:
    scope_mode = str(configuration.get("country_scope_mode", "search_profile") or "search_profile").strip().lower()
    if scope_mode == "eu_eea":
        return ""
    country_codes = ted_country_scope_codes(profile=profile, configuration=configuration)
    if not country_codes:
        return ""
    countries = " ".join(country_codes)
    return f"(buyer-country IN ({countries}) OR place-of-performance IN ({countries}))"


def _ft_exclusion_clause(profile: dict[str, Any]) -> str:
    excluded_terms = _normalize_terms(profile.get("exclude_keywords_json"))[:8]
    if excluded_terms:
        return f"FT !~ ({' '.join(_quote_term(term) for term in excluded_terms if _quote_term(term))})"
    return ""


def _select_query_groups(profile: dict[str, Any]) -> list[TedQueryGroupDefinition]:
    profile_terms = _profile_term_set(profile)
    selected = [
        group
        for group in TED_QUERY_GROUP_DEFINITIONS
        if profile_terms.intersection(group.match_terms)
    ]
    if selected:
        return selected[:5]
    return [
        group
        for group in TED_QUERY_GROUP_DEFINITIONS
        if group.key in TED_DEFAULT_GROUP_KEYS
    ]


def _primary_term_for_group(group: TedQueryGroupDefinition, profile: dict[str, Any]) -> str:
    profile_terms = _profile_term_set(profile)
    for term in group.primary_terms:
        if term in profile_terms:
            return term
    return group.primary_terms[0]


def build_ted_search_query_specs(
    *,
    profile: dict[str, Any],
    configuration: dict[str, Any],
    now: datetime | None = None,
) -> list[TedSearchQuerySpec]:
    publication_clause = _publication_date_clause(configuration=configuration, now=now)
    notice_type_clause = _notice_type_clause(configuration)
    country_clause = _country_clause(profile=profile, configuration=configuration)
    exclusion_clause = _ft_exclusion_clause(profile)
    specs: list[TedSearchQuerySpec] = []
    for group in _select_query_groups(profile):
        primary_term = _primary_term_for_group(group, profile)
        parts = [
            publication_clause,
            notice_type_clause,
            f"classification-cpv IN ({' '.join(group.cpv_codes)})",
            country_clause,
            f"FT ~ ({_quote_term(primary_term)})",
            exclusion_clause,
        ]
        specs.append(
            TedSearchQuerySpec(
                key=group.key,
                label=group.label,
                query=" AND ".join(part for part in parts if part),
                primary_term=primary_term,
                cpv_codes=group.cpv_codes,
            )
        )
    return specs


def build_ted_search_query(
    *,
    profile: dict[str, Any],
    configuration: dict[str, Any],
    now: datetime | None = None,
) -> str:
    specs = build_ted_search_query_specs(profile=profile, configuration=configuration, now=now)
    return specs[0].query if specs else _publication_date_clause(configuration=configuration, now=now)


def build_ted_search_query_variants(
    *,
    profile: dict[str, Any],
    configuration: dict[str, Any],
    now: datetime | None = None,
) -> list[str]:
    return [spec.query for spec in build_ted_search_query_specs(profile=profile, configuration=configuration, now=now)]
