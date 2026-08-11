from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FreelancerQueryGroupDefinition:
    key: str
    label: str
    query_terms: tuple[str, ...]
    skill_terms: tuple[str, ...]


@dataclass(frozen=True)
class FreelancerQuerySpec:
    key: str
    label: str
    query: str
    skill_names: tuple[str, ...]


FREELANCER_QUERY_GROUP_DEFINITIONS: tuple[FreelancerQueryGroupDefinition, ...] = (
    FreelancerQueryGroupDefinition(
        key="workflow_automation",
        label="Workflow Automation",
        query_terms=("workflow automation", "approval workflow", "business process automation", "workflow platform"),
        skill_terms=("Python", "Automation", "API", "Workflow", "Web Development"),
    ),
    FreelancerQueryGroupDefinition(
        key="document_records",
        label="Document Management",
        query_terms=("document management", "records management", "document control", "approval workflow"),
        skill_terms=("Python", "PostgreSQL", "React.js", "API", "Web Development"),
    ),
    FreelancerQueryGroupDefinition(
        key="analytics_reporting",
        label="Dashboard and Reporting",
        query_terms=("dashboard reporting", "analytics platform", "business intelligence dashboard", "data reporting"),
        skill_terms=("Python", "Data Analytics", "PostgreSQL", "React.js", "API"),
    ),
    FreelancerQueryGroupDefinition(
        key="ai_automation",
        label="AI and Intelligent Automation",
        query_terms=("AI automation", "OpenAI workflow", "intelligent automation", "chatbot platform"),
        skill_terms=("Artificial Intelligence", "Machine Learning", "Python", "Automation", "API"),
    ),
    FreelancerQueryGroupDefinition(
        key="integration_platforms",
        label="API Integration",
        query_terms=("API integration", "enterprise integration", "custom web application", "digital transformation"),
        skill_terms=("API", "Python", "React.js", "Next.js", "PostgreSQL", "FastAPI"),
    ),
    FreelancerQueryGroupDefinition(
        key="inspection_compliance",
        label="Inspection and Compliance Systems",
        query_terms=("inspection management system", "compliance workflow", "audit platform", "case management portal"),
        skill_terms=("Python", "React.js", "PostgreSQL", "API", "Web Development"),
    ),
)


def _normalize_terms(values: list[str] | None) -> list[str]:
    seen: OrderedDict[str, None] = OrderedDict()
    for value in values or []:
        normalized = " ".join(str(value or "").split()).strip().lower()
        if normalized:
            seen[normalized] = None
    return list(seen.keys())


def _profile_terms(profile: dict[str, Any]) -> set[str]:
    return set(
        _normalize_terms(
            list(profile.get("target_industries_json") or [])
            + list(profile.get("include_keywords_json") or [])
            + list(profile.get("include_technologies_json") or [])
            + list(profile.get("include_capabilities_json") or [])
        )
    )


def build_freelancer_search_specs(
    *,
    profile: dict[str, Any],
    maximum_groups: int,
) -> list[FreelancerQuerySpec]:
    terms = _profile_terms(profile)
    if not terms:
        return [
            FreelancerQuerySpec(
                key=group.key,
                label=group.label,
                query=group.query_terms[0],
                skill_names=group.skill_terms,
            )
            for group in FREELANCER_QUERY_GROUP_DEFINITIONS[: max(1, maximum_groups)]
        ]
    specs: list[FreelancerQuerySpec] = []
    for group in FREELANCER_QUERY_GROUP_DEFINITIONS:
        match_score = 0
        for term in group.query_terms + group.skill_terms:
            lowered = term.lower()
            if any(lowered in profile_term or profile_term in lowered for profile_term in terms):
                match_score += 1
        if match_score or not specs:
            specs.append(
                FreelancerQuerySpec(
                    key=group.key,
                    label=group.label,
                    query=group.query_terms[0],
                    skill_names=group.skill_terms,
                )
            )
    if not specs:
        specs = [
            FreelancerQuerySpec(
                key=group.key,
                label=group.label,
                query=group.query_terms[0],
                skill_names=group.skill_terms,
            )
            for group in FREELANCER_QUERY_GROUP_DEFINITIONS[:3]
        ]
    return specs[: max(1, maximum_groups)]
