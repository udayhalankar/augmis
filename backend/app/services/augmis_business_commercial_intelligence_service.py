from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import case, desc, func, or_
from sqlalchemy.orm import Session

from app.db_models import (
    BusinessDevelopmentConnector,
    BusinessDevelopmentDiscoveryAIAssessment,
    BusinessDevelopmentDiscoveredOpportunity,
    BusinessDevelopmentSearchProfile,
)
from app.services.augmis_business_experience_match_service import match_discovery_experience
from app.services.audit_service import create_audit_log

PRIORITY_BANDS = [
    (85, "A"),
    (70, "B"),
    (55, "C"),
    (40, "D"),
    (0, "E"),
]

STRATEGIC_TERMS = (
    "workflow",
    "document",
    "records",
    "approval",
    "inspection",
    "dashboard",
    "analytics",
    "automation",
    "portal",
    "integration",
    "compliance",
    "case management",
)
FULL_TIME_TERMS = ("full time", "full-time", "permanent", "employee")
CONTRACT_TERMS = ("contract", "freelance", "consulting", "project", "statement of work", "fixed-price")
REMOTE_TERMS = ("remote", "hybrid", "distributed")
HIGH_COMPLEXITY_TERMS = (
    "erp replacement",
    "nationwide",
    "multi-country",
    "24x7",
    "hardware deployment",
    "field operations",
    "framework agreement",
    "consortium",
)
POSITIVE_DELIVERY_TERMS = (
    "dashboard",
    "portal",
    "workflow",
    "web app",
    "integration",
    "automation",
    "document management",
    "mvp",
    "proof of concept",
    "api",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(str(value).strip().split())
    return cleaned or None


def _discovery_text(discovery: BusinessDevelopmentDiscoveredOpportunity) -> str:
    raw_content = discovery.raw_content_json or {}
    values = [
        discovery.title,
        discovery.organization_name,
        discovery.requirement_summary,
        discovery.raw_summary,
        discovery.raw_text,
        discovery.industry,
        discovery.country,
        discovery.region,
        raw_content.get("project_type"),
        raw_content.get("engagement_type"),
        raw_content.get("employment_type"),
        raw_content.get("notice_type"),
        raw_content.get("procedure_type"),
        raw_content.get("contract_nature"),
        raw_content.get("skills"),
        raw_content.get("tags"),
        raw_content.get("cpv_codes"),
    ]
    return " ".join(str(value).lower() for value in values if value)


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _score_technical_fit(discovery: BusinessDevelopmentDiscoveredOpportunity, text: str) -> tuple[float, str]:
    preliminary = float(discovery.preliminary_relevance_score or 0.0)
    if preliminary >= 80:
        score = 17.0
        reason = "Very strong preliminary relevance already indicates clear solution alignment."
    elif preliminary >= 65:
        score = 14.0
        reason = "Strong preliminary relevance indicates solid technical alignment."
    elif preliminary >= 50:
        score = 10.0
        reason = "Moderate preliminary relevance indicates possible technical alignment."
    elif preliminary >= 35:
        score = 6.0
        reason = "Weak preliminary relevance reduces technical confidence."
    else:
        score = 2.0
        reason = "Low preliminary relevance provides limited technical confidence."
    if _contains_any(text, POSITIVE_DELIVERY_TERMS):
        score = min(20.0, score + 2.0)
        reason = f"{reason} Delivery-oriented solution terms reinforce the fit."
    return round(score, 1), reason


def _score_commercial_value(discovery: BusinessDevelopmentDiscoveredOpportunity) -> tuple[float, str]:
    value = discovery.budget_max or discovery.budget_min
    if value is None:
        return 7.0, "Budget or commercial value is unknown, so this stays neutral."
    source_type = discovery.source_type
    if source_type == "marketplace_project":
        if value >= 5000:
            return 14.0, "Marketplace budget is attractive for targeted pursuit."
        if value >= 2500:
            return 11.0, "Marketplace budget is commercially workable."
        if value >= 1000:
            return 8.0, "Marketplace budget is usable but not especially strong."
        return 4.0, "Marketplace budget is low for likely delivery effort."
    if source_type == "public_procurement":
        if value >= 750000:
            return 12.0, "Procurement value is large, but likely delivery scale may require partners."
        if value >= 100000:
            return 13.0, "Procurement value is commercially attractive."
        if value >= 25000:
            return 10.0, "Procurement value is moderate."
        return 6.0, "Procurement value appears relatively small."
    if value >= 120000:
        return 13.0, "Published compensation is commercially strong."
    if value >= 60000:
        return 10.0, "Published compensation is reasonable."
    if value >= 20000:
        return 8.0, "Published compensation is modest."
    return 5.0, "Published compensation is comparatively low."


def _score_delivery_feasibility(
    discovery: BusinessDevelopmentDiscoveredOpportunity,
    text: str,
) -> tuple[float, str, str, str]:
    score = 8.0
    delivery_model = "solo_ai_assisted"
    positive_hits = sum(1 for phrase in POSITIVE_DELIVERY_TERMS if phrase in text)
    negative_hits = sum(1 for phrase in HIGH_COMPLEXITY_TERMS if phrase in text)
    score += min(5.0, positive_hits * 1.4)
    score -= min(7.0, negative_hits * 2.0)

    published_value = discovery.budget_max or 0.0
    if discovery.source_type == "public_procurement" and published_value >= 750000:
        score -= 2.5
        delivery_model = "partner_likely"
    elif discovery.source_type == "public_procurement" and published_value >= 100000:
        delivery_model = "small_team"
    elif discovery.source_type == "marketplace_project":
        score += 1.0

    if score >= 12:
        complexity = "low"
    elif score >= 9:
        complexity = "medium"
    elif score >= 6:
        complexity = "high"
        if delivery_model == "solo_ai_assisted":
            delivery_model = "small_team"
    else:
        complexity = "very_high"
        delivery_model = "partner_likely"

    reason = (
        "Scope looks deliverable by a focused solo or compact team model."
        if score >= 9
        else "Scope contains scale or complexity signals that reduce delivery confidence."
    )
    return round(max(0.0, min(15.0, score)), 1), complexity, delivery_model, reason


def _score_engagement(discovery: BusinessDevelopmentDiscoveredOpportunity, text: str) -> tuple[float, str]:
    if discovery.source_type == "marketplace_project":
        return 9.0, "Marketplace projects are directly aligned to project-based pursuit."
    if _contains_any(text, CONTRACT_TERMS) or _contains_any(text, REMOTE_TERMS):
        return 9.0, "Contract or remote wording improves engagement suitability."
    if _contains_any(text, FULL_TIME_TERMS):
        return 4.0, "Permanent full-time employment is less aligned to the current operating model."
    if discovery.source_type == "public_procurement":
        return 7.0, "Formal procurement is suitable but typically heavier to pursue."
    return 6.0, "Engagement suitability is neutral due to limited source detail."


def _score_competition(discovery: BusinessDevelopmentDiscoveredOpportunity) -> tuple[float, str]:
    raw_content = discovery.raw_content_json or {}
    if discovery.source_type == "marketplace_project":
        bid_count = raw_content.get("bid_count")
        if isinstance(bid_count, (int, float)):
            if bid_count <= 5:
                return 9.0, "Current bid count is still accessible."
            if bid_count <= 15:
                return 6.0, "Competition is present but still manageable."
            if bid_count <= 30:
                return 4.0, "Competition is already meaningful."
            return 2.0, "High bid count reduces accessibility."
        return 5.0, "Marketplace competition is unknown, so accessibility stays neutral."
    if discovery.source_type == "public_procurement":
        procedure = str(raw_content.get("procedure_type") or "").lower()
        if "open" in procedure:
            return 6.0, "Open procurement is accessible, though still competitive."
        if procedure:
            return 4.0, "Structured procurement burden reduces accessibility."
        return 5.0, "Procurement accessibility is neutral with limited burden detail."
    text = _discovery_text(discovery)
    if _contains_any(text, REMOTE_TERMS):
        return 6.0, "Remote accessibility improves ability to engage quickly."
    return 5.0, "Competition signals are limited, so accessibility stays neutral."


def _score_urgency(discovery: BusinessDevelopmentDiscoveredOpportunity) -> tuple[float, str, str]:
    now = _now()
    if discovery.closing_date:
        if discovery.closing_date < now:
            return 0.0, "expired", "Deadline has already passed."
        days_to_close = max(0, (discovery.closing_date - now).days)
        if days_to_close <= 2:
            return 2.0, "very_high", "Deadline is extremely close."
        if days_to_close <= 7:
            return 4.0, "high", "Deadline is close but still actionable."
        return 5.0, "normal", "Deadline window is still workable."
    if discovery.published_date:
        age_days = max(0, (now - discovery.published_date).days)
        if age_days <= 3:
            return 4.0, "normal", "Posting is fresh."
        if age_days <= 10:
            return 3.0, "normal", "Posting is still recent."
    return 3.0, "unknown", "Deadline is unknown, so urgency stays neutral."


def _score_buyer_quality(discovery: BusinessDevelopmentDiscoveredOpportunity, text: str) -> tuple[float, str]:
    raw_content = discovery.raw_content_json or {}
    if discovery.source_type == "public_procurement":
        org = (discovery.organization_name or "").lower()
        if any(term in org for term in ("authority", "municip", "university", "utility", "health", "ministry")):
            return 5.0, "Buyer appears to be a formal public or institutional body."
        return 4.0, "Public procurement source provides reasonable buyer confidence."
    if discovery.source_type == "marketplace_project":
        payment_verified = raw_content.get("client_payment_verified")
        rating = raw_content.get("client_rating")
        reviews = raw_content.get("client_review_count")
        score = 3.0
        if payment_verified:
            score += 1.0
        if isinstance(rating, (int, float)) and rating >= 4:
            score += 0.5
        if isinstance(reviews, (int, float)) and reviews >= 10:
            score += 0.5
        return min(5.0, score), "Marketplace client metadata provides limited but usable buyer quality signals."
    if raw_content.get("company_url") or raw_content.get("company_name") or discovery.organization_name:
        return 3.5, "Company metadata is present."
    return 3.0, "Buyer or employer quality is mostly unknown, so this stays neutral."


def _score_source_confidence(discovery: BusinessDevelopmentDiscoveredOpportunity) -> tuple[float, str]:
    if discovery.source_type == "public_procurement":
        return 3.0, "Official procurement feed provides very high source confidence."
    if discovery.source_type in {"marketplace_project", "employment_contract"}:
        return 2.6, "Structured provider feed provides high source confidence."
    return 1.8, "Generic web discovery remains medium confidence until reviewed."


def _score_strategic_fit(
    discovery: BusinessDevelopmentDiscoveredOpportunity,
    text: str,
    profile: BusinessDevelopmentSearchProfile | None,
) -> tuple[float, str]:
    strategic_hits = sum(1 for term in STRATEGIC_TERMS if term in text)
    profile_hits = 0
    if profile:
        configured = (
            list(profile.include_keywords_json or [])
            + list(profile.include_technologies_json or [])
            + list(profile.include_capabilities_json or [])
        )
        profile_hits = sum(1 for value in configured if str(value).strip().lower() in text)
    if strategic_hits >= 3 or profile_hits >= 2:
        return 2.0, "Discovery aligns strongly to the current AUGMIS solution direction."
    if strategic_hits >= 1 or profile_hits >= 1:
        return 1.2, "Discovery partially aligns to the current AUGMIS solution direction."
    return 0.6, "Discovery has limited explicit strategic-fit evidence."


def _data_quality(discovery: BusinessDevelopmentDiscoveredOpportunity) -> str:
    completed = sum(
        1
        for value in [
            discovery.title,
            discovery.requirement_summary,
            discovery.organization_name,
            discovery.budget_max or discovery.budget_min,
            discovery.closing_date,
            discovery.raw_content_json.get("skills") if isinstance(discovery.raw_content_json, dict) else None,
            discovery.source_url,
        ]
        if value not in (None, "", [])
    )
    if completed >= 6:
        return "high"
    if completed >= 4:
        return "medium"
    return "low"


def _priority_band(score: float) -> str:
    for minimum, band in PRIORITY_BANDS:
        if score >= minimum:
            return band
    return "E"


def _recommendation(
    score: float,
    urgency_status: str,
    delivery_feasibility_score: float,
    engagement_score: float,
) -> str:
    if urgency_status == "expired":
        return "skip"
    if score >= 70 and delivery_feasibility_score >= 8 and engagement_score >= 5:
        return "pursue"
    if score < 50 or engagement_score <= 2:
        return "skip"
    return "watch"


def _reasons_and_risks(
    component_scores: dict[str, float],
    experience_matches: dict[str, Any],
    urgency_status: str,
    value_reason: str,
    delivery_reason: str,
    source_reason: str,
) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    risks: list[str] = []
    if component_scores["technical_fit"] >= 14:
        reasons.append("Strong solution-fit alignment to current AUGMIS delivery strengths.")
    if component_scores["experience_evidence"] >= 10 and experience_matches["matches"]:
        reasons.append(f"{len(experience_matches['matches'])} relevant experience items support this discovery.")
    if component_scores["engagement_suitability"] >= 8:
        reasons.append("Engagement format is suitable for project-oriented pursuit.")
    if component_scores["source_confidence"] >= 2.5:
        reasons.append(source_reason)
    if component_scores["commercial_value"] >= 10:
        reasons.append(value_reason)
    if component_scores["delivery_feasibility"] < 8:
        risks.append(delivery_reason)
    if urgency_status == "very_high":
        risks.append("Response window is very short.")
    if component_scores["competition_accessibility"] <= 4:
        risks.append("Accessibility or competition signals reduce pursuit confidence.")
    if component_scores["commercial_value"] <= 5:
        risks.append(value_reason)
    return reasons[:6], risks[:6]


def _resolve_search_profile(
    db: Session,
    discovery: BusinessDevelopmentDiscoveredOpportunity,
) -> BusinessDevelopmentSearchProfile | None:
    connector = (
        db.query(BusinessDevelopmentConnector)
        .filter(
            BusinessDevelopmentConnector.id == discovery.connector_id,
            BusinessDevelopmentConnector.tenant_id == discovery.tenant_id,
        )
        .first()
    )
    if connector and connector.search_profile_id:
        return (
            db.query(BusinessDevelopmentSearchProfile)
            .filter(
                BusinessDevelopmentSearchProfile.id == connector.search_profile_id,
                BusinessDevelopmentSearchProfile.tenant_id == discovery.tenant_id,
            )
            .first()
        )
    return (
        db.query(BusinessDevelopmentSearchProfile)
        .filter(
            BusinessDevelopmentSearchProfile.tenant_id == discovery.tenant_id,
            BusinessDevelopmentSearchProfile.enabled.is_(True),
        )
        .order_by(BusinessDevelopmentSearchProfile.created_at.asc())
        .first()
    )


def serialize_discovery_commercial_intelligence(
    discovery: BusinessDevelopmentDiscoveredOpportunity,
) -> dict[str, Any]:
    return {
        "commercial_priority_score": discovery.commercial_priority_score,
        "commercial_priority_band": discovery.commercial_priority_band,
        "commercial_recommendation": discovery.commercial_recommendation,
        "commercial_component_scores_json": discovery.commercial_component_scores_json or {},
        "commercial_recommendation_reasons_json": discovery.commercial_recommendation_reasons_json or [],
        "commercial_risks_json": discovery.commercial_risks_json or [],
        "experience_match_score": discovery.experience_match_score,
        "matched_experience_ids_json": discovery.matched_experience_ids_json or [],
        "matched_experience_reasons_json": discovery.matched_experience_reasons_json or [],
        "matched_experience_summary_json": discovery.matched_experience_summary_json or [],
        "delivery_feasibility_score": discovery.delivery_feasibility_score,
        "delivery_complexity": discovery.delivery_complexity,
        "delivery_model": discovery.delivery_model,
        "urgency_status": discovery.urgency_status,
        "data_quality_status": discovery.data_quality_status,
        "intelligence_updated_at": _serialize_datetime(discovery.intelligence_updated_at),
    }


def refresh_discovery_commercial_intelligence(
    db: Session,
    discovery: BusinessDevelopmentDiscoveredOpportunity,
) -> dict[str, Any]:
    if discovery.tenant_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discovery tenant scope is required")
    text = _discovery_text(discovery)
    profile = _resolve_search_profile(db, discovery)
    experience_matches = match_discovery_experience(db, discovery.tenant_id, discovery, limit=3)
    technical_fit, technical_reason = _score_technical_fit(discovery, text)
    commercial_value, value_reason = _score_commercial_value(discovery)
    delivery_feasibility, delivery_complexity, delivery_model, delivery_reason = _score_delivery_feasibility(discovery, text)
    engagement_suitability, engagement_reason = _score_engagement(discovery, text)
    competition_accessibility, competition_reason = _score_competition(discovery)
    urgency_score, urgency_status, urgency_reason = _score_urgency(discovery)
    buyer_quality, buyer_reason = _score_buyer_quality(discovery, text)
    source_confidence, source_reason = _score_source_confidence(discovery)
    strategic_fit, strategic_reason = _score_strategic_fit(discovery, text, profile)

    component_scores = {
        "technical_fit": technical_fit,
        "experience_evidence": round(min(15.0, (experience_matches["score"] / 100.0) * 15.0), 1),
        "commercial_value": commercial_value,
        "delivery_feasibility": delivery_feasibility,
        "engagement_suitability": engagement_suitability,
        "competition_accessibility": competition_accessibility,
        "urgency": urgency_score,
        "buyer_quality": buyer_quality,
        "source_confidence": source_confidence,
        "strategic_fit": strategic_fit,
    }
    total_score = round(min(100.0, sum(component_scores.values())), 1)
    recommendation = _recommendation(
        total_score,
        urgency_status,
        delivery_feasibility,
        engagement_suitability,
    )
    reasons, risks = _reasons_and_risks(
        component_scores,
        experience_matches,
        urgency_status,
        value_reason,
        delivery_reason,
        source_reason,
    )
    reason_map = {
        "technical_fit": technical_reason,
        "experience_evidence": (
            "Deterministic experience overlap is strong."
            if experience_matches["score"] >= 75
            else "Deterministic experience overlap is moderate or limited."
        ),
        "commercial_value": value_reason,
        "delivery_feasibility": delivery_reason,
        "engagement_suitability": engagement_reason,
        "competition_accessibility": competition_reason,
        "urgency": urgency_reason,
        "buyer_quality": buyer_reason,
        "source_confidence": source_reason,
        "strategic_fit": strategic_reason,
    }

    discovery.commercial_priority_score = total_score
    discovery.commercial_priority_band = _priority_band(total_score)
    discovery.commercial_recommendation = recommendation
    discovery.commercial_component_scores_json = {
        name: {
            "score": value,
            "reason": reason_map[name],
        }
        for name, value in component_scores.items()
    }
    discovery.commercial_recommendation_reasons_json = reasons
    discovery.commercial_risks_json = risks
    discovery.experience_match_score = experience_matches["score"]
    discovery.matched_experience_ids_json = experience_matches["matched_experience_ids"]
    discovery.matched_experience_reasons_json = experience_matches["matched_experience_reasons"]
    discovery.matched_experience_summary_json = experience_matches["matches"]
    discovery.delivery_feasibility_score = delivery_feasibility
    discovery.delivery_complexity = delivery_complexity
    discovery.delivery_model = delivery_model
    discovery.urgency_status = urgency_status
    discovery.data_quality_status = _data_quality(discovery)
    discovery.intelligence_updated_at = _now()
    return serialize_discovery_commercial_intelligence(discovery)


def recalculate_discovery_priorities(
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
    for row in rows:
        refresh_discovery_commercial_intelligence(db, row)
        row.updated_at = _now()
    db.commit()
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description="AUGMIS Business commercial priorities recalculated",
        resource_type="bd_discovery",
        resource_id=None,
        metadata={"count": len(rows), "limit": bounded_limit},
    )
    return {
        "success": True,
        "data": {
            "count": len(rows),
            "limit": bounded_limit,
            "items": [
                {
                    "id": row.id,
                    "title": _clean_text(row.title) or row.id,
                    **serialize_discovery_commercial_intelligence(row),
                }
                for row in rows
            ],
        },
    }


def _opportunity_class(source_type: str) -> str:
    if source_type == "public_procurement":
        return "procurement"
    if source_type == "marketplace_project":
        return "marketplace"
    if source_type == "employment_contract":
        return "contract_job"
    return "web_search"


def get_discovery_commercial_intelligence(
    db: Session,
    tenant_id: str,
    discovery_id: str,
) -> dict[str, Any]:
    discovery = (
        db.query(BusinessDevelopmentDiscoveredOpportunity)
        .filter(
            BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id,
            BusinessDevelopmentDiscoveredOpportunity.id == discovery_id,
        )
        .first()
    )
    if not discovery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery not found")
    refresh_discovery_commercial_intelligence(db, discovery)
    latest_assessment = (
        db.query(BusinessDevelopmentDiscoveryAIAssessment)
        .filter(
            BusinessDevelopmentDiscoveryAIAssessment.tenant_id == tenant_id,
            BusinessDevelopmentDiscoveryAIAssessment.discovery_id == discovery_id,
        )
        .order_by(BusinessDevelopmentDiscoveryAIAssessment.analysis_version.desc())
        .first()
    )
    also_seen_on = (
        db.query(BusinessDevelopmentDiscoveredOpportunity.source_name)
        .filter(
            BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id,
            BusinessDevelopmentDiscoveredOpportunity.id != discovery.id,
            or_(
                BusinessDevelopmentDiscoveredOpportunity.canonical_source_url
                == discovery.canonical_source_url,
                BusinessDevelopmentDiscoveredOpportunity.composite_fingerprint
                == discovery.composite_fingerprint,
            ),
        )
        .limit(3)
        .all()
        if discovery.canonical_source_url or discovery.composite_fingerprint
        else []
    )
    return {
        "success": True,
        "data": {
            **serialize_discovery_commercial_intelligence(discovery),
            "opportunity_class": _opportunity_class(discovery.source_type),
            "latest_deep_assessment": None
            if latest_assessment is None
            else {
                "id": latest_assessment.id,
                "analysis_version": latest_assessment.analysis_version,
                "recommendation": latest_assessment.recommendation,
                "recommendation_confidence": latest_assessment.recommendation_confidence,
                "created_at": _serialize_datetime(latest_assessment.created_at),
            },
            "also_seen_on": [row[0] for row in also_seen_on if row[0]],
        },
    }


def get_daily_deal_desk(
    db: Session,
    tenant_id: str,
    *,
    limit: int = 10,
    recommendation: str | None = None,
    source_category: str | None = None,
    priority_band: str | None = None,
    opportunity_class: str | None = None,
) -> dict[str, Any]:
    bounded_limit = max(1, min(int(limit or 10), 20))
    query = db.query(BusinessDevelopmentDiscoveredOpportunity).filter(
        BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id,
        BusinessDevelopmentDiscoveredOpportunity.discovery_status != "duplicate",
    )
    if recommendation and recommendation != "all":
        query = query.filter(BusinessDevelopmentDiscoveredOpportunity.commercial_recommendation == recommendation)
    if priority_band and priority_band != "all":
        query = query.filter(BusinessDevelopmentDiscoveredOpportunity.commercial_priority_band == priority_band)
    if opportunity_class and opportunity_class != "all":
        class_map = {
            "procurement": ["public_procurement"],
            "marketplace": ["marketplace_project"],
            "contract_job": ["employment_contract"],
            "web_search": ["search", "manual", "web_search"],
        }
        query = query.filter(BusinessDevelopmentDiscoveredOpportunity.source_type.in_(class_map.get(opportunity_class, [])))
    if source_category and source_category != "all":
        query = query.join(
            BusinessDevelopmentConnector,
            BusinessDevelopmentConnector.id == BusinessDevelopmentDiscoveredOpportunity.connector_id,
        ).filter(BusinessDevelopmentConnector.source_category == source_category)

    rows = (
        query.order_by(
            desc(func.coalesce(BusinessDevelopmentDiscoveredOpportunity.commercial_priority_score, 0)),
            desc(
                func.coalesce(
                    BusinessDevelopmentDiscoveredOpportunity.delivery_feasibility_score,
                    0,
                )
            ),
            BusinessDevelopmentDiscoveredOpportunity.closing_date.asc().nullslast(),
            desc(func.coalesce(BusinessDevelopmentDiscoveredOpportunity.preliminary_relevance_score, 0)),
            BusinessDevelopmentDiscoveredOpportunity.discovered_at.desc(),
        )
        .limit(bounded_limit)
        .all()
    )
    for row in rows:
        if row.commercial_priority_score is None:
            refresh_discovery_commercial_intelligence(db, row)

    now = _now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    closing_soon_cutoff = now + timedelta(days=7)
    summary_rows = (
        db.query(
            func.count(BusinessDevelopmentDiscoveredOpportunity.id),
            func.sum(case((BusinessDevelopmentDiscoveredOpportunity.commercial_recommendation == "pursue", 1), else_=0)),
            func.sum(case((BusinessDevelopmentDiscoveredOpportunity.commercial_recommendation == "watch", 1), else_=0)),
            func.sum(case((BusinessDevelopmentDiscoveredOpportunity.commercial_recommendation == "skip", 1), else_=0)),
            func.sum(case((BusinessDevelopmentDiscoveredOpportunity.commercial_priority_band == "A", 1), else_=0)),
            func.sum(case((BusinessDevelopmentDiscoveredOpportunity.commercial_priority_band == "B", 1), else_=0)),
            func.sum(
                case(
                    (
                        (BusinessDevelopmentDiscoveredOpportunity.closing_date.is_not(None))
                        & (BusinessDevelopmentDiscoveredOpportunity.closing_date >= now)
                        & (BusinessDevelopmentDiscoveredOpportunity.closing_date <= closing_soon_cutoff),
                        1,
                    ),
                    else_=0,
                )
            ),
        )
        .filter(
            BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id,
            BusinessDevelopmentDiscoveredOpportunity.discovered_at >= day_start,
        )
        .first()
    )
    ai_assessed_today = (
        db.query(func.count(BusinessDevelopmentDiscoveryAIAssessment.id))
        .filter(
            BusinessDevelopmentDiscoveryAIAssessment.tenant_id == tenant_id,
            BusinessDevelopmentDiscoveryAIAssessment.created_at >= day_start,
        )
        .scalar()
        or 0
    )
    summary_count = summary_rows or (0, 0, 0, 0, 0, 0, 0)
    return {
        "success": True,
        "data": {
            "discoveries_today": int(summary_count[0] or 0),
            "pursue": int(summary_count[1] or 0),
            "watch": int(summary_count[2] or 0),
            "skip": int(summary_count[3] or 0),
            "priority_a": int(summary_count[4] or 0),
            "priority_b": int(summary_count[5] or 0),
            "closing_soon": int(summary_count[6] or 0),
            "ai_assessed_today": int(ai_assessed_today),
            "items": [
                {
                    "id": row.id,
                    "title": row.title,
                    "organization_name": row.organization_name,
                    "source_type": row.source_type,
                    "source_name": row.source_name,
                    "closing_date": _serialize_datetime(row.closing_date),
                    "published_date": _serialize_datetime(row.published_date),
                    "preliminary_relevance_score": row.preliminary_relevance_score,
                    **serialize_discovery_commercial_intelligence(row),
                    "top_experience_match": (row.matched_experience_summary_json or [None])[0],
                }
                for row in rows
            ],
            "limit": bounded_limit,
        },
    }
