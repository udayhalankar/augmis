from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, TypeVar
from uuid import uuid4

from fastapi import HTTPException, status
from openai import APITimeoutError, OpenAIError, RateLimitError
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db_models import (
    BusinessDevelopmentExperienceItem,
    BusinessDevelopmentOpportunity,
    BusinessDevelopmentOpportunityAIAssessment,
    BusinessDevelopmentOpportunityExperienceMatch,
)
from app.models.augmis_business_models import (
    AugmisBusinessBuyerRolesResult,
    AugmisBusinessExperienceMatchEnvelope,
    AugmisBusinessExperienceMatchResult,
    AugmisBusinessOpportunityAIAssessmentResponse,
    AugmisBusinessOpportunityAIAssessmentSummary,
    AugmisBusinessQualificationResult,
    AugmisBusinessRequirementExtractionResult,
)
from app.services.ai_service import client as openai_client
from app.services.audit_service import create_audit_log
from app.services.subscription_service import add_ai_token_usage, validate_usage_limit
from app.services.token_usage_service import estimate_ai_usage_tokens
from app.services.augmis_business_ai_prompts import (
    BUYER_ROLE_IDENTIFICATION_PROMPT_VERSION,
    EXPERIENCE_MATCHING_PROMPT_VERSION,
    OPPORTUNITY_QUALIFICATION_PROMPT_VERSION,
    PROMPT_BUNDLE_VERSION,
    REQUIREMENT_EXTRACTION_PROMPT_VERSION,
    build_buyer_role_prompt,
    build_experience_matching_prompt,
    build_opportunity_qualification_prompt,
    build_requirement_extraction_prompt,
)


logger = logging.getLogger(__name__)
ModelT = TypeVar("ModelT", bound=BaseModel)
AI_SCHEMA_TABLES = (
    "bd_opportunity_ai_assessments",
    "bd_opportunity_experience_matches",
)

QUALIFICATION_WEIGHTS = {
    "experience_relevance": 0.25,
    "technology_match": 0.15,
    "budget_attractiveness": 0.15,
    "delivery_feasibility": 0.15,
    "buyer_accessibility": 0.10,
    "deadline_feasibility": 0.10,
    "market_payment_risk": 0.10,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _coerce_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _extract_json_object(raw_content: str) -> dict[str, Any]:
    text = str(raw_content or "").strip()
    if not text:
        raise ValueError("Model returned empty content")

    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if fenced_match:
        text = fenced_match.group(1)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Model response did not contain a valid JSON object")
        data = json.loads(text[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("Model response must be a JSON object")
    return data


def _is_missing_ai_schema_error(error: Exception) -> bool:
    message = str(error)
    return any(
        f'relation "{table}" does not exist' in message or f"no such table: {table}" in message
        for table in AI_SCHEMA_TABLES
    )


def _raise_ai_schema_missing(error: Exception) -> None:
    if not _is_missing_ai_schema_error(error):
        raise error
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "AUGMIS Business AI assessment tables are not initialized yet. "
            "Apply the Phase 4A Alembic migration and retry."
        ),
    ) from error


def _require_openai_api_key() -> None:
    if not str(settings.OPENAI_API_KEY or "").strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assessment is unavailable because the OpenAI API key is not configured.",
        )


def _sanitize_text_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        cleaned = " ".join(str(raw or "").strip().split())
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _normalized_tokens(*values: Any) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            for item in value:
                tokens.update(_normalized_tokens(item))
            continue
        normalized = (
            str(value)
            .lower()
            .replace("_", " ")
            .replace("-", " ")
            .replace("/", " ")
        )
        for token in normalized.split():
            token = token.strip(" ,.;:()[]{}")
            if len(token) >= 3:
                tokens.add(token)
    return tokens


def _serialize_opportunity_payload(row: BusinessDevelopmentOpportunity) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "organization": row.organization_name,
        "source_type": row.source_type,
        "source_name": row.source_name,
        "source_url": row.source_url,
        "raw_summary": row.raw_summary,
        "requirement_summary": row.requirement_summary,
        "business_problem": row.business_problem,
        "expected_deliverables": row.expected_deliverables_json or [],
        "required_technologies": row.required_technologies_json or [],
        "country": row.country,
        "region": row.region,
        "industry": row.industry,
        "published_budget": row.published_budget,
        "published_currency": row.published_currency,
        "estimated_value_min": row.estimated_value_min,
        "estimated_value_max": row.estimated_value_max,
        "estimated_currency": row.estimated_currency,
        "closing_date": _serialize_datetime(row.closing_at),
        "published_date": _serialize_datetime(row.published_at),
        "source_evidence": row.source_evidence_json or [],
    }


def _shortlist_experience_items(
    opportunity: BusinessDevelopmentOpportunity,
    experience_items: list[BusinessDevelopmentExperienceItem],
    limit: int = 5,
) -> list[dict[str, Any]]:
    opportunity_tokens = _normalized_tokens(
        opportunity.title,
        opportunity.organization_name,
        opportunity.requirement_summary,
        opportunity.raw_summary,
        opportunity.business_problem,
        opportunity.expected_deliverables_json,
        opportunity.required_technologies_json,
        opportunity.industry,
        opportunity.country,
        opportunity.region,
    )
    scored: list[tuple[int, BusinessDevelopmentExperienceItem]] = []
    for item in experience_items:
        item_tokens = _normalized_tokens(
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
        )
        overlap = len(opportunity_tokens & item_tokens)
        technology_overlap = len(
            _normalized_tokens(opportunity.required_technologies_json)
            & _normalized_tokens(item.technologies_json)
        )
        industry_overlap = len(
            _normalized_tokens(opportunity.industry) & _normalized_tokens(item.industries_json)
        )
        category_overlap = 1 if item.category.lower() in " ".join(sorted(opportunity_tokens)) else 0
        score = overlap * 5 + technology_overlap * 8 + industry_overlap * 4 + category_overlap * 3
        scored.append((score, item))

    scored.sort(key=lambda pair: (pair[0], pair[1].created_at or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    shortlisted = [item for _score, item in scored[:limit]]
    if not shortlisted:
        shortlisted = experience_items[:limit]

    return [
        {
            "experience_item_id": row.id,
            "name": row.name,
            "category": row.category,
            "description": row.description,
            "business_problems": row.business_problems_json or [],
            "features": row.features_json or [],
            "technologies": row.technologies_json or [],
            "industries": row.industries_json or [],
            "keywords": row.keywords_json or [],
            "reusable_capabilities": row.reusable_capabilities_json or [],
            "confidentiality_safe_summary": row.confidentiality_safe_summary,
        }
        for row in shortlisted
    ]


def _calculate_fit_score(qualification: AugmisBusinessQualificationResult) -> float:
    weighted_total = 0.0
    for component_name, weight in QUALIFICATION_WEIGHTS.items():
        component = getattr(qualification, component_name)
        weighted_total += float(component.score) * weight
    return round(weighted_total, 2)


def _serialize_usage_metadata(
    *,
    response_usage: Any,
    prompt: str,
    answer: str,
) -> dict[str, Any]:
    input_tokens = getattr(response_usage, "prompt_tokens", None)
    output_tokens = getattr(response_usage, "completion_tokens", None)
    total_tokens = getattr(response_usage, "total_tokens", None)
    if total_tokens is None:
        total_tokens = estimate_ai_usage_tokens(prompt, "", answer)
    if input_tokens is None or output_tokens is None:
        estimated_input = estimate_ai_usage_tokens(prompt, "", "")
        input_tokens = input_tokens or estimated_input
        output_tokens = output_tokens or max(0, total_tokens - input_tokens)
    return {
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "total_tokens": int(total_tokens or 0),
        "estimated_cost_usd": None,
    }


def _run_json_agent(
    *,
    tenant_id: str,
    user_id: str,
    opportunity_id: str,
    agent_type: str,
    prompt_version: str,
    prompt: str,
    response_model: type[ModelT],
    db: Session,
) -> tuple[ModelT, dict[str, Any]]:
    _require_openai_api_key()
    validate_usage_limit(tenant_id, "ai_tokens", db)

    started_at = _now()
    last_error: Exception | None = None
    max_attempts = 2

    for attempt in range(1, max_attempts + 1):
        try:
            response = openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a controlled AUGMIS Business AI engine. Return JSON only.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.1,
            )
            raw_content = response.choices[0].message.content or ""
            payload = _extract_json_object(raw_content)
            parsed = response_model.model_validate(payload)
            usage = _serialize_usage_metadata(
                response_usage=getattr(response, "usage", None),
                prompt=prompt,
                answer=raw_content,
            )
            add_ai_token_usage(tenant_id, usage["total_tokens"], db)
            completed_at = _now()
            run_metadata = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "opportunity_id": opportunity_id,
                "agent_type": agent_type,
                "provider": "openai",
                "model": settings.OPENAI_MODEL,
                "prompt_version": prompt_version,
                "started_at": _serialize_datetime(started_at),
                "completed_at": _serialize_datetime(completed_at),
                "status": "success",
                **usage,
                "error_message": None,
            }
            create_audit_log(
                db=db,
                tenant_id=tenant_id,
                user_id=user_id,
                event_type="AI_RUN",
                event_category="AI",
                description=f"AUGMIS Business AI agent completed: {agent_type}",
                resource_type="bd_opportunity",
                resource_id=opportunity_id,
                metadata=run_metadata,
            )
            return parsed, run_metadata
        except ValidationError as exc:
            last_error = exc
            break
        except ValueError as exc:
            last_error = exc
            break
        except (APITimeoutError, RateLimitError, OpenAIError) as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            time.sleep(0.6 * attempt)
        except Exception as exc:  # pragma: no cover - safety net
            last_error = exc
            if attempt >= max_attempts:
                break
            time.sleep(0.6 * attempt)

    completed_at = _now()
    error_message = str(last_error or "Unknown AI error")
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="AI_RUN",
        event_category="AI",
        description=f"AUGMIS Business AI agent failed: {agent_type}",
        resource_type="bd_opportunity",
        resource_id=opportunity_id,
        metadata={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "opportunity_id": opportunity_id,
            "agent_type": agent_type,
            "provider": "openai",
            "model": settings.OPENAI_MODEL,
            "prompt_version": prompt_version,
            "started_at": _serialize_datetime(started_at),
            "completed_at": _serialize_datetime(completed_at),
            "status": "failed",
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "estimated_cost_usd": None,
            "error_message": error_message,
        },
    )

    if isinstance(last_error, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI agent returned invalid structured output for {agent_type}.",
        ) from last_error
    if isinstance(last_error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI agent returned invalid JSON output for {agent_type}.",
        ) from last_error
    if isinstance(last_error, APITimeoutError):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"AI assessment timed out during {agent_type}.",
        ) from last_error
    if isinstance(last_error, RateLimitError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assessment is temporarily rate limited. Please try again.",
        ) from last_error
    if isinstance(last_error, OpenAIError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assessment is temporarily unavailable. Please try again.",
        ) from last_error
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="AI assessment failed unexpectedly.",
    ) from last_error


def _require_opportunity(db: Session, tenant_id: str, opportunity_id: str) -> BusinessDevelopmentOpportunity:
    row = (
        db.query(BusinessDevelopmentOpportunity)
        .filter(
            BusinessDevelopmentOpportunity.tenant_id == tenant_id,
            BusinessDevelopmentOpportunity.id == opportunity_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )
    return row


def _serialize_experience_match_row(
    row: BusinessDevelopmentOpportunityExperienceMatch,
    item_by_id: dict[str, BusinessDevelopmentExperienceItem],
) -> AugmisBusinessExperienceMatchResult:
    item = item_by_id[row.experience_item_id]
    return AugmisBusinessExperienceMatchResult(
        experience_item_id=row.experience_item_id,
        name=item.name,
        category=item.category,
        match_score=row.match_score or 0,
        matching_capabilities=row.matching_capabilities_json or [],
        matching_technologies=row.matching_technologies_json or [],
        business_problem_similarity=row.business_problem_similarity or "",
        explanation=row.explanation or "",
    )


def _serialize_assessment_response(
    row: BusinessDevelopmentOpportunityAIAssessment,
    match_rows: list[BusinessDevelopmentOpportunityExperienceMatch],
    item_by_id: dict[str, BusinessDevelopmentExperienceItem],
) -> dict[str, Any]:
    matches = [
        _serialize_experience_match_row(match_row, item_by_id).model_dump(mode="json")
        for match_row in match_rows
        if match_row.experience_item_id in item_by_id
    ]
    payload = AugmisBusinessOpportunityAIAssessmentResponse(
        id=row.id,
        opportunity_id=row.opportunity_id,
        assessment_version=row.assessment_version,
        provider=row.provider,
        model=row.model,
        prompt_bundle_version=row.prompt_bundle_version,
        final_fit_score=row.final_fit_score,
        confidence_score=row.confidence_score,
        recommendation=row.recommendation,
        created_at=row.created_at,
        requirement_extraction_json=AugmisBusinessRequirementExtractionResult.model_validate(
            row.requirement_extraction_json or {}
        ),
        qualification_json=AugmisBusinessQualificationResult.model_validate(
            row.qualification_json or {}
        ),
        buyer_roles_json=AugmisBusinessBuyerRolesResult.model_validate(row.buyer_roles_json or {}),
        risks_json=row.risks_json or [],
        missing_information_json=row.missing_information_json or [],
        experience_matches=[
            AugmisBusinessExperienceMatchResult.model_validate(match_payload)
            for match_payload in matches
        ],
        ai_run_summary_json=row.ai_run_summary_json or {},
    )
    return payload.model_dump(mode="json")


def _list_active_experience_items(db: Session, tenant_id: str) -> list[BusinessDevelopmentExperienceItem]:
    return (
        db.query(BusinessDevelopmentExperienceItem)
        .filter(
            BusinessDevelopmentExperienceItem.tenant_id == tenant_id,
            BusinessDevelopmentExperienceItem.status == "active",
        )
        .order_by(BusinessDevelopmentExperienceItem.created_at.asc())
        .all()
    )


def assess_opportunity_ai(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
    current_user: dict,
) -> dict[str, Any]:
    opportunity = _require_opportunity(db, tenant_id, opportunity_id)
    opportunity_payload = _serialize_opportunity_payload(opportunity)

    requirement_result, requirement_run = _run_json_agent(
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        opportunity_id=opportunity_id,
        agent_type="requirement_extraction",
        prompt_version=REQUIREMENT_EXTRACTION_PROMPT_VERSION,
        prompt=build_requirement_extraction_prompt(opportunity_payload),
        response_model=AugmisBusinessRequirementExtractionResult,
        db=db,
    )

    experience_items = _list_active_experience_items(db, tenant_id)
    shortlisted_items = _shortlist_experience_items(opportunity, experience_items, limit=5)
    matches_payload = []
    experience_run: dict[str, Any] = {
        "tenant_id": tenant_id,
        "user_id": current_user["user_id"],
        "opportunity_id": opportunity_id,
        "agent_type": "experience_matching",
        "provider": "openai",
        "model": settings.OPENAI_MODEL,
        "prompt_version": EXPERIENCE_MATCHING_PROMPT_VERSION,
        "started_at": _serialize_datetime(_now()),
        "completed_at": _serialize_datetime(_now()),
        "status": "success",
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": None,
        "error_message": None,
    }
    if shortlisted_items:
        experience_model, experience_run = _run_json_agent(
            tenant_id=tenant_id,
            user_id=current_user["user_id"],
            opportunity_id=opportunity_id,
            agent_type="experience_matching",
            prompt_version=EXPERIENCE_MATCHING_PROMPT_VERSION,
            prompt=build_experience_matching_prompt(
                opportunity_payload,
                requirement_result.model_dump(mode="json"),
                shortlisted_items,
            ),
            response_model=AugmisBusinessExperienceMatchEnvelope,
            db=db,
        )
        matches_payload = experience_model.model_dump(mode="json").get("matches", [])

    qualification_result, qualification_run = _run_json_agent(
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        opportunity_id=opportunity_id,
        agent_type="opportunity_qualification",
        prompt_version=OPPORTUNITY_QUALIFICATION_PROMPT_VERSION,
        prompt=build_opportunity_qualification_prompt(
            opportunity_payload,
            requirement_result.model_dump(mode="json"),
            matches_payload,
        ),
        response_model=AugmisBusinessQualificationResult,
        db=db,
    )

    buyer_roles_result, buyer_run = _run_json_agent(
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        opportunity_id=opportunity_id,
        agent_type="buyer_role_identification",
        prompt_version=BUYER_ROLE_IDENTIFICATION_PROMPT_VERSION,
        prompt=build_buyer_role_prompt(
            opportunity_payload,
            requirement_result.model_dump(mode="json"),
        ),
        response_model=AugmisBusinessBuyerRolesResult,
        db=db,
    )

    final_fit_score = _calculate_fit_score(qualification_result)
    recommendation = qualification_result.recommendation
    closing_at = _coerce_utc_datetime(opportunity.closing_at)
    if closing_at and closing_at < _now():
        recommendation = "expired"

    confidence_score = round(
        (
            requirement_result.confidence
            + qualification_result.confidence
            + buyer_roles_result.economic_buyer.confidence
            + buyer_roles_result.operational_owner.confidence
            + buyer_roles_result.technical_evaluator.confidence
            + buyer_roles_result.procurement_contact.confidence
        )
        / 6,
        2,
    )

    try:
        current_version = (
            db.query(BusinessDevelopmentOpportunityAIAssessment.assessment_version)
            .filter(
                BusinessDevelopmentOpportunityAIAssessment.tenant_id == tenant_id,
                BusinessDevelopmentOpportunityAIAssessment.opportunity_id == opportunity_id,
            )
            .order_by(BusinessDevelopmentOpportunityAIAssessment.assessment_version.desc())
            .first()
        )
    except DBAPIError as exc:
        _raise_ai_schema_missing(exc)
    next_version = (current_version[0] if current_version else 0) + 1

    assessment_row = BusinessDevelopmentOpportunityAIAssessment(
        id=f"BD-AIA-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        opportunity_id=opportunity_id,
        assessment_version=next_version,
        provider="openai",
        model=settings.OPENAI_MODEL,
        prompt_bundle_version=PROMPT_BUNDLE_VERSION,
        requirement_extraction_json=requirement_result.model_dump(mode="json"),
        qualification_json=qualification_result.model_dump(mode="json"),
        buyer_roles_json=buyer_roles_result.model_dump(mode="json"),
        final_fit_score=final_fit_score,
        confidence_score=confidence_score,
        recommendation=recommendation,
        risks_json=_sanitize_text_list(qualification_result.risks)
        + _sanitize_text_list(qualification_result.delivery_profile.key_delivery_risks),
        missing_information_json=_sanitize_text_list(
            requirement_result.missing_information + qualification_result.missing_information
        ),
        ai_run_summary_json={
            "requirement_extraction": requirement_run,
            "experience_matching": experience_run,
            "opportunity_qualification": qualification_run,
            "buyer_role_identification": buyer_run,
        },
        created_by=current_user["user_id"],
        updated_at=_now(),
    )
    try:
        db.add(assessment_row)
        db.flush()
    except DBAPIError as exc:
        db.rollback()
        _raise_ai_schema_missing(exc)

    shortlist_item_ids = {item["experience_item_id"] for item in shortlisted_items}
    item_by_id = {
        row.id: row
        for row in experience_items
        if row.id in shortlist_item_ids or not shortlisted_items
    }
    match_rows: list[BusinessDevelopmentOpportunityExperienceMatch] = []
    for match_payload in matches_payload:
        match_model = AugmisBusinessExperienceMatchResult.model_validate(match_payload)
        if match_model.experience_item_id not in item_by_id:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experience item not found: {match_model.experience_item_id}",
            )
        row = BusinessDevelopmentOpportunityExperienceMatch(
            id=f"BD-OXM-{str(uuid4())[:12].upper()}",
            tenant_id=tenant_id,
            opportunity_id=opportunity_id,
            assessment_id=assessment_row.id,
            experience_item_id=match_model.experience_item_id,
            match_score=match_model.match_score,
            matching_capabilities_json=_sanitize_text_list(match_model.matching_capabilities),
            matching_technologies_json=_sanitize_text_list(match_model.matching_technologies),
            business_problem_similarity=match_model.business_problem_similarity,
            explanation=match_model.explanation,
        )
        try:
            db.add(row)
        except DBAPIError as exc:
            db.rollback()
            _raise_ai_schema_missing(exc)
        match_rows.append(row)

    opportunity.fit_score = final_fit_score
    opportunity.confidence_score = confidence_score
    opportunity.ai_recommendation = recommendation
    opportunity.updated_at = _now()
    try:
        db.commit()
        db.refresh(assessment_row)
    except DBAPIError as exc:
        db.rollback()
        _raise_ai_schema_missing(exc)

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="AI_ASSESSMENT_CREATED",
        event_category="AI",
        description="AUGMIS Business opportunity AI assessment completed",
        resource_type="bd_opportunity",
        resource_id=opportunity_id,
        metadata={
            "assessment_id": assessment_row.id,
            "assessment_version": assessment_row.assessment_version,
            "provider": assessment_row.provider,
            "model": assessment_row.model,
            "prompt_bundle_version": assessment_row.prompt_bundle_version,
            "final_fit_score": assessment_row.final_fit_score,
            "confidence_score": assessment_row.confidence_score,
            "recommendation": assessment_row.recommendation,
            "experience_matches_count": len(match_rows),
        },
    )

    return {
        "success": True,
        "data": _serialize_assessment_response(assessment_row, match_rows, item_by_id),
    }


def get_latest_opportunity_ai_assessment(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
) -> dict[str, Any]:
    _require_opportunity(db, tenant_id, opportunity_id)
    try:
        assessment = (
            db.query(BusinessDevelopmentOpportunityAIAssessment)
            .filter(
                BusinessDevelopmentOpportunityAIAssessment.tenant_id == tenant_id,
                BusinessDevelopmentOpportunityAIAssessment.opportunity_id == opportunity_id,
            )
            .order_by(BusinessDevelopmentOpportunityAIAssessment.assessment_version.desc())
            .first()
        )
    except DBAPIError as exc:
        _raise_ai_schema_missing(exc)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI assessment not found for this opportunity",
        )
    try:
        match_rows = (
            db.query(BusinessDevelopmentOpportunityExperienceMatch)
            .filter(
                BusinessDevelopmentOpportunityExperienceMatch.tenant_id == tenant_id,
                BusinessDevelopmentOpportunityExperienceMatch.assessment_id == assessment.id,
            )
            .order_by(BusinessDevelopmentOpportunityExperienceMatch.match_score.desc().nullslast())
            .all()
        )
    except DBAPIError as exc:
        _raise_ai_schema_missing(exc)
    item_ids = [row.experience_item_id for row in match_rows]
    item_by_id = {
        row.id: row
        for row in db.query(BusinessDevelopmentExperienceItem)
        .filter(
            BusinessDevelopmentExperienceItem.tenant_id == tenant_id,
            BusinessDevelopmentExperienceItem.id.in_(item_ids or [""]),
        )
        .all()
    }
    return {
        "success": True,
        "data": _serialize_assessment_response(assessment, match_rows, item_by_id),
    }


def list_opportunity_ai_assessment_history(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
) -> dict[str, Any]:
    _require_opportunity(db, tenant_id, opportunity_id)
    try:
        rows = (
            db.query(BusinessDevelopmentOpportunityAIAssessment)
            .filter(
                BusinessDevelopmentOpportunityAIAssessment.tenant_id == tenant_id,
                BusinessDevelopmentOpportunityAIAssessment.opportunity_id == opportunity_id,
            )
            .order_by(BusinessDevelopmentOpportunityAIAssessment.assessment_version.desc())
            .all()
        )
    except DBAPIError as exc:
        _raise_ai_schema_missing(exc)
    summaries = [
        AugmisBusinessOpportunityAIAssessmentSummary(
            id=row.id,
            opportunity_id=row.opportunity_id,
            assessment_version=row.assessment_version,
            provider=row.provider,
            model=row.model,
            prompt_bundle_version=row.prompt_bundle_version,
            final_fit_score=row.final_fit_score,
            confidence_score=row.confidence_score,
            recommendation=row.recommendation,
            created_at=row.created_at,
        ).model_dump(mode="json")
        for row in rows
    ]
    return {"success": True, "data": summaries}


def list_latest_opportunity_experience_matches(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
) -> dict[str, Any]:
    try:
        latest = (
            db.query(BusinessDevelopmentOpportunityAIAssessment)
            .filter(
                BusinessDevelopmentOpportunityAIAssessment.tenant_id == tenant_id,
                BusinessDevelopmentOpportunityAIAssessment.opportunity_id == opportunity_id,
            )
            .order_by(BusinessDevelopmentOpportunityAIAssessment.assessment_version.desc())
            .first()
        )
    except DBAPIError as exc:
        _raise_ai_schema_missing(exc)
    if not latest:
        return {"success": True, "data": []}
    try:
        match_rows = (
            db.query(BusinessDevelopmentOpportunityExperienceMatch)
            .filter(
                BusinessDevelopmentOpportunityExperienceMatch.tenant_id == tenant_id,
                BusinessDevelopmentOpportunityExperienceMatch.assessment_id == latest.id,
            )
            .order_by(BusinessDevelopmentOpportunityExperienceMatch.match_score.desc().nullslast())
            .all()
        )
    except DBAPIError as exc:
        _raise_ai_schema_missing(exc)
    item_ids = [row.experience_item_id for row in match_rows]
    item_by_id = {
        row.id: row
        for row in db.query(BusinessDevelopmentExperienceItem)
        .filter(
            BusinessDevelopmentExperienceItem.tenant_id == tenant_id,
            BusinessDevelopmentExperienceItem.id.in_(item_ids or [""]),
        )
        .all()
    }
    return {
        "success": True,
        "data": [
            _serialize_experience_match_row(row, item_by_id).model_dump(mode="json")
            for row in match_rows
            if row.experience_item_id in item_by_id
        ],
    }
