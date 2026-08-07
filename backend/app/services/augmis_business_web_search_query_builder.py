from __future__ import annotations

from collections import OrderedDict
from typing import Any


COMMERCIAL_INTENT_TERMS = [
    "RFP",
    "RFQ",
    "tender",
    '"request for proposal"',
    '"request for quotation"',
    '"seeking vendor"',
    '"implementation partner"',
    '"software development services"',
]

CONCEPT_GROUPS: dict[str, tuple[str, ...]] = {
    "workflow": ("workflow", "approval", "approvals", "forms", "business process", "digitisation"),
    "dashboards": ("dashboard", "reporting", "analytics", "statistics", "portal"),
    "documents": ("document management", "records management", "document control", "opentext", "otcs"),
    "inspection": ("inspection", "quality", "hse", "audit system", "readiness"),
    "custom_development": ("custom software", "web application", "application development", "portal development", "mvp"),
    "integration": ("integration", "api", "automation", "fastapi", "react", "next.js", "node.js", "python", ".net"),
}

FALLBACK_QUERY_FAMILIES = [
    '"request for proposal" "web application development"',
    'tender "workflow automation"',
    '"software development services" dashboard',
    '"custom software development" procurement',
    '"document management system" RFP',
    '"inspection management system" tender',
]


def _normalize_terms(values: list[str] | None) -> list[str]:
    seen: OrderedDict[str, None] = OrderedDict()
    for value in values or []:
        normalized = " ".join(str(value or "").strip().lower().split())
        if normalized:
            seen[normalized] = None
    return list(seen.keys())


def _pick_concepts(profile: dict[str, Any]) -> list[str]:
    terms = _normalize_terms(
        list(profile.get("include_keywords_json") or [])
        + list(profile.get("include_technologies_json") or [])
        + list(profile.get("include_capabilities_json") or [])
    )
    matched: list[str] = []
    for concept, vocabulary in CONCEPT_GROUPS.items():
        if any(any(token in term for token in vocabulary) for term in terms):
            matched.append(concept)
    if not matched:
        matched = ["custom_development", "workflow", "dashboards"]
    return matched


def _concept_phrase(concept: str) -> str:
    mapping = {
        "workflow": '"workflow automation"',
        "dashboards": 'dashboard OR reporting OR analytics',
        "documents": '"document management" OR "records management" OR "document control"',
        "inspection": '"inspection management" OR "quality system" OR "HSE system"',
        "custom_development": '"custom software development" OR "web application development"',
        "integration": '"API integration" OR automation OR FastAPI OR React',
    }
    return mapping[concept]


def build_web_search_queries(
    *,
    profile: dict[str, Any],
    maximum_queries: int,
) -> list[str]:
    maximum = max(1, maximum_queries)
    countries = _normalize_terms(profile.get("target_countries_json"))
    regions = _normalize_terms(profile.get("target_regions_json"))
    concepts = _pick_concepts(profile)
    queries: OrderedDict[str, None] = OrderedDict()

    primary_intents = COMMERCIAL_INTENT_TERMS[:1]
    secondary_intents = COMMERCIAL_INTENT_TERMS[1:4]

    for concept in concepts:
        concept_phrase = _concept_phrase(concept)
        for intent in primary_intents:
            query = f"{intent} {concept_phrase}"
            queries[" ".join(query.split())] = None
            if len(queries) >= maximum:
                return list(queries.keys())

    geography_terms = countries[:2] or regions[:1]
    if geography_terms:
        for concept in concepts[: max(1, min(len(concepts), maximum // 2 or 1))]:
            concept_phrase = _concept_phrase(concept)
            for geography in geography_terms:
                query = f'{concept_phrase} {"RFP" if " " not in geography else "tender"} "{geography}"'
                queries[" ".join(query.split())] = None
                if len(queries) >= maximum:
                    return list(queries.keys())

    for concept in concepts:
        concept_phrase = _concept_phrase(concept)
        for intent in secondary_intents:
            query = f"{intent} {concept_phrase}"
            queries[" ".join(query.split())] = None
            if len(queries) >= maximum:
                return list(queries.keys())

    for query in FALLBACK_QUERY_FAMILIES:
        queries[" ".join(query.split())] = None
        if len(queries) >= maximum:
            break

    return list(queries.keys())[:maximum]
