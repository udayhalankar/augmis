from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db_models import BusinessDevelopmentDiscoveredOpportunity, BusinessDevelopmentExperienceItem

GENERIC_MATCH_TERMS = {
    "app",
    "application",
    "business",
    "dashboard",
    "data",
    "digital",
    "enterprise",
    "management",
    "platform",
    "portal",
    "project",
    "report",
    "reporting",
    "software",
    "solution",
    "system",
    "workflow",
}


def _normalize_tokens(*values: Any) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, dict):
            for nested in value.values():
                tokens.update(_normalize_tokens(nested))
            continue
        if isinstance(value, (list, tuple, set)):
            for nested in value:
                tokens.update(_normalize_tokens(nested))
            continue
        normalized = (
            str(value)
            .lower()
            .replace("_", " ")
            .replace("-", " ")
            .replace("/", " ")
        )
        for token in normalized.split():
            cleaned = token.strip(" ,.;:()[]{}<>|")
            if len(cleaned) >= 3:
                tokens.add(cleaned)
    return tokens


def _normalize_phrases(values: list[str] | None) -> set[str]:
    phrases: set[str] = set()
    for raw in values or []:
        cleaned = " ".join(str(raw or "").strip().lower().split())
        if cleaned:
            phrases.add(cleaned)
    return phrases


def _discovery_payload_tokens(discovery: BusinessDevelopmentDiscoveredOpportunity) -> dict[str, set[str]]:
    raw_content = discovery.raw_content_json or {}
    skills = raw_content.get("skills") or raw_content.get("tags") or raw_content.get("cpv_codes") or []
    metadata_values = [
        raw_content.get("project_type"),
        raw_content.get("engagement_type"),
        raw_content.get("employment_type"),
        raw_content.get("category"),
        raw_content.get("notice_type"),
        raw_content.get("procedure_type"),
        raw_content.get("contract_nature"),
    ]
    full_text = _normalize_tokens(
        discovery.title,
        discovery.organization_name,
        discovery.requirement_summary,
        discovery.raw_summary,
        discovery.raw_text,
        discovery.industry,
        discovery.country,
        discovery.region,
        skills,
        metadata_values,
    )
    return {
        "full": full_text,
        "skills": _normalize_tokens(skills),
        "industry": _normalize_tokens(discovery.industry),
        "category": _normalize_tokens(metadata_values),
        "title": _normalize_tokens(discovery.title),
    }


def _item_payload(item: BusinessDevelopmentExperienceItem) -> dict[str, set[str]]:
    return {
        "full": _normalize_tokens(
            item.name,
            item.category,
            item.description,
            item.business_problems_json,
            item.features_json,
            item.technologies_json,
            item.industries_json,
            item.keywords_json,
            item.reusable_capabilities_json,
            item.confidentiality_safe_summary,
        ),
        "technologies": _normalize_tokens(item.technologies_json),
        "industries": _normalize_tokens(item.industries_json),
        "keywords": _normalize_tokens(item.keywords_json),
        "capabilities": _normalize_tokens(
            item.features_json,
            item.reusable_capabilities_json,
            item.business_problems_json,
        ),
        "phrases": _normalize_phrases(
            [
                item.name,
                item.category,
                *(item.keywords_json or []),
                *(item.reusable_capabilities_json or []),
                *(item.technologies_json or []),
            ]
        ),
    }


def list_active_experience_items(db: Session, tenant_id: str) -> list[BusinessDevelopmentExperienceItem]:
    return (
        db.query(BusinessDevelopmentExperienceItem)
        .filter(
            BusinessDevelopmentExperienceItem.tenant_id == tenant_id,
            BusinessDevelopmentExperienceItem.status == "active",
        )
        .order_by(BusinessDevelopmentExperienceItem.created_at.asc(), BusinessDevelopmentExperienceItem.name.asc())
        .all()
    )


def match_discovery_experience(
    db: Session,
    tenant_id: str,
    discovery: BusinessDevelopmentDiscoveredOpportunity,
    *,
    limit: int = 3,
) -> dict[str, Any]:
    items = list_active_experience_items(db, tenant_id)
    discovery_tokens = _discovery_payload_tokens(discovery)
    discovery_text = " ".join(sorted(discovery_tokens["full"]))
    scored: list[dict[str, Any]] = []

    for item in items:
        item_tokens = _item_payload(item)
        keyword_hits = sorted(
            token for token in (discovery_tokens["full"] & item_tokens["keywords"]) if token not in GENERIC_MATCH_TERMS
        )
        technology_hits = sorted(discovery_tokens["skills"] & item_tokens["technologies"])
        industry_hits = sorted(discovery_tokens["industry"] & item_tokens["industries"])
        capability_hits = sorted(
            token
            for token in (discovery_tokens["full"] & item_tokens["capabilities"])
            if token not in GENERIC_MATCH_TERMS
        )
        phrase_hits = sorted(
            phrase for phrase in item_tokens["phrases"] if len(phrase) > 4 and phrase in discovery_text
        )

        weighted_score = (
            len(keyword_hits) * 4
            + len(technology_hits) * 8
            + len(industry_hits) * 6
            + len(capability_hits) * 6
            + len(phrase_hits) * 5
        )
        signal_groups = sum(
            1
            for hits in [keyword_hits, technology_hits, industry_hits, capability_hits, phrase_hits]
            if hits
        )
        if signal_groups <= 1 and len(keyword_hits) <= 1 and len(technology_hits) <= 1:
            weighted_score = min(weighted_score, 12)
        elif signal_groups == 2:
            weighted_score += 6
        elif signal_groups >= 3:
            weighted_score += 14

        match_score = round(min(100.0, weighted_score * 2.1), 1)
        if match_score <= 0:
            continue

        if match_score >= 75:
            relevance_label = "strong"
        elif match_score >= 50:
            relevance_label = "moderate"
        elif match_score >= 30:
            relevance_label = "possible"
        else:
            relevance_label = "weak"

        reasons: list[str] = []
        if technology_hits:
            reasons.append(f"Technology overlap: {', '.join(technology_hits[:3])}.")
        if capability_hits:
            reasons.append(f"Capability overlap: {', '.join(capability_hits[:3])}.")
        if industry_hits:
            reasons.append(f"Industry overlap: {', '.join(industry_hits[:2])}.")
        if phrase_hits:
            reasons.append(f"Named pattern overlap: {', '.join(phrase_hits[:2])}.")
        if not reasons and keyword_hits:
            reasons.append(f"Keyword overlap: {', '.join(keyword_hits[:3])}.")

        scored.append(
            {
                "experience_item_id": item.id,
                "name": item.name,
                "category": item.category,
                "match_score": match_score,
                "relevance_label": relevance_label,
                "matching_signals": {
                    "keywords": keyword_hits[:5],
                    "technologies": technology_hits[:5],
                    "industries": industry_hits[:3],
                    "capabilities": capability_hits[:5],
                    "phrases": phrase_hits[:3],
                },
                "reasons": reasons,
            }
        )

    scored.sort(key=lambda row: (row["match_score"], row["name"]), reverse=True)
    top_matches = scored[:limit]
    overall_score = 0.0
    if top_matches:
        weighted = sum(
            match["match_score"] * weight
            for match, weight in zip(top_matches, [1.0, 0.75, 0.5], strict=False)
        )
        total_weight = sum([1.0, 0.75, 0.5][: len(top_matches)])
        overall_score = round(weighted / total_weight, 1)

    return {
        "score": overall_score,
        "matches": top_matches,
        "matched_experience_ids": [match["experience_item_id"] for match in top_matches],
        "matched_experience_reasons": [
            f"{match['name']}: {match['reasons'][0]}" for match in top_matches if match["reasons"]
        ],
    }
