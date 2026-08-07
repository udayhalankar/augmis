from __future__ import annotations

import json
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
    BusinessDevelopmentContact,
    BusinessDevelopmentExperienceItem,
    BusinessDevelopmentLead,
    BusinessDevelopmentLeadExperienceMatch,
    BusinessDevelopmentMiniSolution,
    BusinessDevelopmentOpportunity,
    BusinessDevelopmentOpportunityAIAssessment,
    BusinessDevelopmentOpportunityExperienceMatch,
    BusinessDevelopmentOutreachDraft,
    BusinessDevelopmentProspect,
)
from app.models.augmis_business_models import (
    AugmisBusinessMiniSolutionContent,
    AugmisBusinessMiniSolutionGenerateRequest,
    AugmisBusinessMiniSolutionResponse,
    AugmisBusinessMiniSolutionSummary,
    AugmisBusinessMiniSolutionUpdateRequest,
    AugmisBusinessOutreachDraftResponse,
    AugmisBusinessOutreachDraftSummary,
    AugmisBusinessOutreachDraftUpdateRequest,
    AugmisBusinessOutreachGenerateRequest,
    AugmisBusinessOutreachGenerationResult,
    AugmisBusinessStatusActionRequest,
    VERIFIED_CONTACT_STATUSES,
)
from app.services.ai_service import client as openai_client
from app.services.audit_service import create_audit_log
from app.services.augmis_business_ai_service import (
    _serialize_assessment_response,
    _serialize_experience_match_row,
    _serialize_opportunity_payload,
    get_latest_opportunity_ai_assessment,
)
from app.services.augmis_business_generation_prompts import (
    MINI_SOLUTION_GENERATION_PROMPT_VERSION,
    OUTREACH_GENERATION_PROMPT_VERSION,
    PROMPT_BUNDLE_VERSION,
    build_mini_solution_generation_prompt,
    build_outreach_generation_prompt,
)
from app.services.augmis_business_service import (
    serialize_contact,
    serialize_lead,
    serialize_opportunity,
    serialize_prospect,
)
from app.services.subscription_service import add_ai_token_usage, validate_usage_limit
from app.services.token_usage_service import estimate_ai_usage_tokens


ModelT = TypeVar("ModelT", bound=BaseModel)
GENERATION_SCHEMA_TABLES = (
    "bd_outreach_drafts",
    "bd_mini_solutions",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


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


def _sanitize_text_list(values: list[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        cleaned = " ".join(str(raw or "").strip().split())
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _is_missing_generation_schema_error(error: Exception) -> bool:
    message = str(error)
    return any(
        f'relation "{table}" does not exist' in message or f"no such table: {table}" in message
        for table in GENERATION_SCHEMA_TABLES
    )


def _raise_generation_schema_missing(error: Exception) -> None:
    if not _is_missing_generation_schema_error(error):
        raise error
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "AUGMIS Business outreach and mini-solution tables are not initialized yet. "
            "Apply the Phase 4B Alembic migration and retry."
        ),
    ) from error


def _require_openai_api_key() -> None:
    if not str(settings.OPENAI_API_KEY or "").strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI generation is unavailable because the OpenAI API key is not configured.",
        )


def _serialize_usage_metadata(*, response_usage: Any, prompt: str, answer: str) -> dict[str, Any]:
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
    lead_id: str | None,
    generation_type: str,
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
                        "content": "You are a controlled AUGMIS Business AI generation engine. Return JSON only.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.2,
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
                "lead_id": lead_id,
                "generation_type": generation_type,
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
                description=f"AUGMIS Business AI generation completed: {generation_type}",
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
        except Exception as exc:  # pragma: no cover
            last_error = exc
            if attempt >= max_attempts:
                break
            time.sleep(0.6 * attempt)

    completed_at = _now()
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="AI_RUN",
        event_category="AI",
        description=f"AUGMIS Business AI generation failed: {generation_type}",
        resource_type="bd_opportunity",
        resource_id=opportunity_id,
        metadata={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "opportunity_id": opportunity_id,
            "lead_id": lead_id,
            "generation_type": generation_type,
            "provider": "openai",
            "model": settings.OPENAI_MODEL,
            "prompt_version": prompt_version,
            "started_at": _serialize_datetime(started_at),
            "completed_at": _serialize_datetime(completed_at),
            "status": "failed",
            "error_message": str(last_error or "Unknown AI error"),
        },
    )
    if isinstance(last_error, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI agent returned invalid structured output for {generation_type}.",
        ) from last_error
    if isinstance(last_error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI agent returned invalid JSON output for {generation_type}.",
        ) from last_error
    if isinstance(last_error, APITimeoutError):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"AI generation timed out during {generation_type}.",
        ) from last_error
    if isinstance(last_error, RateLimitError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI generation is temporarily rate limited. Please try again.",
        ) from last_error
    if isinstance(last_error, OpenAIError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI generation is temporarily unavailable. Please try again.",
        ) from last_error
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="AI generation failed unexpectedly.",
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return row


def _require_lead(db: Session, tenant_id: str, lead_id: str) -> BusinessDevelopmentLead:
    row = (
        db.query(BusinessDevelopmentLead)
        .filter(
            BusinessDevelopmentLead.tenant_id == tenant_id,
            BusinessDevelopmentLead.id == lead_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return row


def _require_contact(db: Session, tenant_id: str, contact_id: str) -> BusinessDevelopmentContact:
    row = (
        db.query(BusinessDevelopmentContact)
        .filter(
            BusinessDevelopmentContact.tenant_id == tenant_id,
            BusinessDevelopmentContact.id == contact_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return row


def _serialize_contact_notice(contact: BusinessDevelopmentContact | None) -> str | None:
    if not contact:
        return None
    if contact.full_name and contact.verification_status not in VERIFIED_CONTACT_STATUSES:
        return (
            f"Contact name is {contact.verification_status or 'unverified'} and must be reviewed "
            "before external use."
        )
    return None


def _get_latest_assessment_row(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
) -> BusinessDevelopmentOpportunityAIAssessment | None:
    return (
        db.query(BusinessDevelopmentOpportunityAIAssessment)
        .filter(
            BusinessDevelopmentOpportunityAIAssessment.tenant_id == tenant_id,
            BusinessDevelopmentOpportunityAIAssessment.opportunity_id == opportunity_id,
        )
        .order_by(BusinessDevelopmentOpportunityAIAssessment.assessment_version.desc())
        .first()
    )


def _get_assessment_payload(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
) -> tuple[dict[str, Any] | None, BusinessDevelopmentOpportunityAIAssessment | None]:
    try:
        result = get_latest_opportunity_ai_assessment(db, tenant_id, opportunity_id)
        row = _get_latest_assessment_row(db, tenant_id, opportunity_id)
        return result["data"], row
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            return None, None
        raise


def _list_opportunity_match_rows(
    db: Session,
    tenant_id: str,
    assessment_id: str | None,
) -> list[BusinessDevelopmentOpportunityExperienceMatch]:
    if not assessment_id:
        return []
    return (
        db.query(BusinessDevelopmentOpportunityExperienceMatch)
        .filter(
            BusinessDevelopmentOpportunityExperienceMatch.tenant_id == tenant_id,
            BusinessDevelopmentOpportunityExperienceMatch.assessment_id == assessment_id,
        )
        .order_by(BusinessDevelopmentOpportunityExperienceMatch.match_score.desc().nullslast())
        .all()
    )


def _list_lead_match_rows(
    db: Session,
    tenant_id: str,
    lead_id: str | None,
) -> list[BusinessDevelopmentLeadExperienceMatch]:
    if not lead_id:
        return []
    return (
        db.query(BusinessDevelopmentLeadExperienceMatch)
        .filter(
            BusinessDevelopmentLeadExperienceMatch.tenant_id == tenant_id,
            BusinessDevelopmentLeadExperienceMatch.lead_id == lead_id,
        )
        .order_by(BusinessDevelopmentLeadExperienceMatch.created_at.asc())
        .all()
    )


def _serialize_safe_experience_item(row: BusinessDevelopmentExperienceItem) -> dict[str, Any]:
    return {
        "experience_item_id": row.id,
        "name": row.name,
        "category": row.category,
        "technologies": row.technologies_json or [],
        "reusable_capabilities": row.reusable_capabilities_json or [],
        "safe_summary": row.confidentiality_safe_summary,
    }


def _resolve_context(
    db: Session,
    tenant_id: str,
    *,
    opportunity_id: str,
    lead_id: str | None = None,
    prospect_id: str | None = None,
    contact_id: str | None = None,
) -> dict[str, Any]:
    opportunity = _require_opportunity(db, tenant_id, opportunity_id)

    lead = _require_lead(db, tenant_id, lead_id) if lead_id else None
    if lead and lead.opportunity_id != opportunity.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lead does not belong to the selected opportunity",
        )

    if lead:
        prospect = (
            db.query(BusinessDevelopmentProspect)
            .filter(
                BusinessDevelopmentProspect.tenant_id == tenant_id,
                BusinessDevelopmentProspect.id == lead.prospect_id,
            )
            .first()
        )
        contact = (
            db.query(BusinessDevelopmentContact)
            .filter(
                BusinessDevelopmentContact.tenant_id == tenant_id,
                BusinessDevelopmentContact.id == lead.primary_contact_id,
            )
            .first()
        )
    else:
        prospect = None
        if prospect_id:
            prospect = (
                db.query(BusinessDevelopmentProspect)
                .filter(
                    BusinessDevelopmentProspect.tenant_id == tenant_id,
                    BusinessDevelopmentProspect.id == prospect_id,
                )
                .first()
            )
        if not prospect:
            prospect = (
                db.query(BusinessDevelopmentProspect)
                .filter(
                    BusinessDevelopmentProspect.tenant_id == tenant_id,
                    BusinessDevelopmentProspect.source_opportunity_id == opportunity.id,
                )
                .order_by(BusinessDevelopmentProspect.created_at.asc())
                .first()
            )
        contact = _require_contact(db, tenant_id, contact_id) if contact_id else None
        if not contact and prospect:
            contact = (
                db.query(BusinessDevelopmentContact)
                .filter(
                    BusinessDevelopmentContact.tenant_id == tenant_id,
                    BusinessDevelopmentContact.prospect_id == prospect.id,
                )
                .order_by(BusinessDevelopmentContact.is_primary.desc(), BusinessDevelopmentContact.created_at.asc())
                .first()
            )

    if contact and prospect and contact.prospect_id != prospect.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact does not belong to the selected prospect",
        )

    assessment_payload, assessment_row = _get_assessment_payload(db, tenant_id, opportunity.id)
    opportunity_match_rows = _list_opportunity_match_rows(
        db,
        tenant_id,
        assessment_row.id if assessment_row else None,
    )
    lead_match_rows = _list_lead_match_rows(db, tenant_id, lead.id if lead else None)

    experience_ids = {
        row.experience_item_id for row in opportunity_match_rows
    } | {row.experience_item_id for row in lead_match_rows}
    experience_items = (
        db.query(BusinessDevelopmentExperienceItem)
        .filter(
            BusinessDevelopmentExperienceItem.tenant_id == tenant_id,
            BusinessDevelopmentExperienceItem.id.in_(list(experience_ids) or [""]),
        )
        .all()
    )
    item_by_id = {row.id: row for row in experience_items}

    experience_matches = []
    for row in opportunity_match_rows:
        if row.experience_item_id not in item_by_id:
            continue
        payload = _serialize_experience_match_row(row, item_by_id).model_dump(mode="json")
        payload["safe_summary"] = item_by_id[row.experience_item_id].confidentiality_safe_summary
        experience_matches.append(payload)
    for row in lead_match_rows:
        item = item_by_id.get(row.experience_item_id)
        if not item:
            continue
        experience_matches.append(
            {
                "experience_item_id": row.experience_item_id,
                "name": item.name,
                "category": item.category,
                "match_score": row.relevance_score or 0,
                "matching_capabilities": item.reusable_capabilities_json or [],
                "matching_technologies": item.technologies_json or [],
                "business_problem_similarity": row.match_notes or "",
                "explanation": row.match_notes or "",
                "safe_summary": item.confidentiality_safe_summary,
            }
        )

    return {
        "opportunity": opportunity,
        "opportunity_payload": serialize_opportunity(opportunity),
        "lead": lead,
        "lead_payload": serialize_lead(lead) if lead else None,
        "prospect": prospect,
        "prospect_payload": serialize_prospect(prospect) if prospect else None,
        "contact": contact,
        "contact_payload": serialize_contact(contact) if contact else None,
        "assessment_payload": assessment_payload,
        "assessment_row": assessment_row,
        "experience_matches": experience_matches,
        "experience_catalogue": [
            _serialize_safe_experience_item(row) for row in experience_items
        ],
    }


def _build_generation_context_payload(
    context: dict[str, Any],
    *,
    tone: str,
    outreach_type: str | None = None,
) -> dict[str, Any]:
    opportunity = context["opportunity_payload"]
    assessment = context["assessment_payload"]
    lead = context["lead_payload"]
    prospect = context["prospect_payload"]
    contact = context["contact_payload"]

    return {
        "requested_tone": tone,
        "requested_outreach_type": outreach_type,
        "opportunity": opportunity,
        "lead": lead,
        "prospect": prospect,
        "contact": contact,
        "contact_verification_notice": _serialize_contact_notice(context["contact"]),
        "assessment": assessment,
        "experience_matches": context["experience_matches"],
        "experience_catalogue": context["experience_catalogue"],
    }


def _validate_outreach_named_contact(
    result: AugmisBusinessOutreachGenerationResult,
    contact: BusinessDevelopmentContact | None,
) -> None:
    if not result.content.uses_named_contact:
        return
    if not contact or not contact.full_name:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI outreach output referenced a named contact that does not exist in stored data.",
        )
    if result.content.contact_name_used and result.content.contact_name_used.strip().lower() != contact.full_name.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI outreach output referenced a contact name that does not match stored data.",
        )


def _serialize_outreach_summary(row: BusinessDevelopmentOutreachDraft) -> dict[str, Any]:
    return AugmisBusinessOutreachDraftSummary(
        id=row.id,
        opportunity_id=row.opportunity_id,
        lead_id=row.lead_id,
        prospect_id=row.prospect_id,
        contact_id=row.contact_id,
        outreach_type=row.outreach_type,
        tone=row.tone,
        subject=row.subject,
        generation_version=row.generation_version,
        provider=row.provider,
        model=row.model,
        prompt_bundle_version=row.prompt_bundle_version,
        status=row.status,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    ).model_dump(mode="json")


def _serialize_outreach_response(row: BusinessDevelopmentOutreachDraft) -> dict[str, Any]:
    return AugmisBusinessOutreachDraftResponse(
        **_serialize_outreach_summary(row),
        body=row.body,
        structured_content_json=AugmisBusinessOutreachGenerationResult.model_validate(
            row.structured_content_json or {}
        ),
    ).model_dump(mode="json")


def _serialize_mini_solution_summary(row: BusinessDevelopmentMiniSolution) -> dict[str, Any]:
    return AugmisBusinessMiniSolutionSummary(
        id=row.id,
        opportunity_id=row.opportunity_id,
        lead_id=row.lead_id,
        assessment_id=row.assessment_id,
        title=row.title,
        generation_version=row.generation_version,
        provider=row.provider,
        model=row.model,
        prompt_bundle_version=row.prompt_bundle_version,
        status=row.status,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    ).model_dump(mode="json")


def _serialize_mini_solution_response(row: BusinessDevelopmentMiniSolution) -> dict[str, Any]:
    return AugmisBusinessMiniSolutionResponse(
        **_serialize_mini_solution_summary(row),
        solution_json=AugmisBusinessMiniSolutionContent.model_validate(row.solution_json or {}),
    ).model_dump(mode="json")


def _next_outreach_version(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
    lead_id: str | None,
    outreach_type: str,
) -> int:
    current = (
        db.query(BusinessDevelopmentOutreachDraft.generation_version)
        .filter(
            BusinessDevelopmentOutreachDraft.tenant_id == tenant_id,
            BusinessDevelopmentOutreachDraft.opportunity_id == opportunity_id,
            BusinessDevelopmentOutreachDraft.lead_id == lead_id,
            BusinessDevelopmentOutreachDraft.outreach_type == outreach_type,
        )
        .order_by(BusinessDevelopmentOutreachDraft.generation_version.desc())
        .first()
    )
    return (current[0] if current else 0) + 1


def _next_mini_solution_version(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
    lead_id: str | None,
) -> int:
    current = (
        db.query(BusinessDevelopmentMiniSolution.generation_version)
        .filter(
            BusinessDevelopmentMiniSolution.tenant_id == tenant_id,
            BusinessDevelopmentMiniSolution.opportunity_id == opportunity_id,
            BusinessDevelopmentMiniSolution.lead_id == lead_id,
        )
        .order_by(BusinessDevelopmentMiniSolution.generation_version.desc())
        .first()
    )
    return (current[0] if current else 0) + 1


def _supersede_previous_outreach(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
    lead_id: str | None,
    outreach_type: str,
) -> None:
    (
        db.query(BusinessDevelopmentOutreachDraft)
        .filter(
            BusinessDevelopmentOutreachDraft.tenant_id == tenant_id,
            BusinessDevelopmentOutreachDraft.opportunity_id == opportunity_id,
            BusinessDevelopmentOutreachDraft.lead_id == lead_id,
            BusinessDevelopmentOutreachDraft.outreach_type == outreach_type,
            BusinessDevelopmentOutreachDraft.status.in_(["draft", "reviewed", "approved"]),
        )
        .update(
            {
                BusinessDevelopmentOutreachDraft.status: "superseded",
                BusinessDevelopmentOutreachDraft.updated_at: _now(),
            },
            synchronize_session=False,
        )
    )


def _supersede_previous_mini_solutions(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
    lead_id: str | None,
) -> None:
    (
        db.query(BusinessDevelopmentMiniSolution)
        .filter(
            BusinessDevelopmentMiniSolution.tenant_id == tenant_id,
            BusinessDevelopmentMiniSolution.opportunity_id == opportunity_id,
            BusinessDevelopmentMiniSolution.lead_id == lead_id,
            BusinessDevelopmentMiniSolution.status.in_(["draft", "reviewed", "approved"]),
        )
        .update(
            {
                BusinessDevelopmentMiniSolution.status: "superseded",
                BusinessDevelopmentMiniSolution.updated_at: _now(),
            },
            synchronize_session=False,
        )
    )


def generate_outreach_for_opportunity(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
    current_user: dict,
    payload: AugmisBusinessOutreachGenerateRequest,
) -> dict[str, Any]:
    context = _resolve_context(
        db,
        tenant_id,
        opportunity_id=opportunity_id,
        lead_id=payload.lead_id,
        prospect_id=payload.prospect_id,
        contact_id=payload.contact_id,
    )
    prompt = build_outreach_generation_prompt(
        context_payload=_build_generation_context_payload(
            context, tone=payload.tone, outreach_type=payload.outreach_type
        ),
        outreach_type=payload.outreach_type,
        tone=payload.tone,
    )
    result, run_metadata = _run_json_agent(
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        opportunity_id=opportunity_id,
        lead_id=context["lead"].id if context["lead"] else None,
        generation_type=f"outreach:{payload.outreach_type}",
        prompt_version=OUTREACH_GENERATION_PROMPT_VERSION,
        prompt=prompt,
        response_model=AugmisBusinessOutreachGenerationResult,
        db=db,
    )
    _validate_outreach_named_contact(result, context["contact"])

    version = _next_outreach_version(
        db, tenant_id, opportunity_id, context["lead"].id if context["lead"] else None, payload.outreach_type
    )
    row = BusinessDevelopmentOutreachDraft(
        id=f"BD-OUT-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        opportunity_id=opportunity_id,
        lead_id=context["lead"].id if context["lead"] else None,
        prospect_id=context["prospect"].id if context["prospect"] else None,
        contact_id=context["contact"].id if context["contact"] else None,
        outreach_type=payload.outreach_type,
        tone=payload.tone,
        subject=result.content.recommended_subject,
        body=result.content.full_message,
        structured_content_json=result.model_dump(mode="json"),
        generation_version=version,
        provider="openai",
        model=settings.OPENAI_MODEL,
        prompt_bundle_version=PROMPT_BUNDLE_VERSION,
        status="draft",
        created_by=current_user["user_id"],
        updated_at=_now(),
    )
    try:
        _supersede_previous_outreach(
            db, tenant_id, opportunity_id, context["lead"].id if context["lead"] else None, payload.outreach_type
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    except DBAPIError as exc:
        db.rollback()
        _raise_generation_schema_missing(exc)

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="AI_OUTREACH_CREATED",
        event_category="AI",
        description=f"Generated outreach draft for {payload.outreach_type}",
        resource_type="bd_outreach_draft",
        resource_id=row.id,
        metadata={
            "opportunity_id": opportunity_id,
            "lead_id": row.lead_id,
            "generation_version": row.generation_version,
            "tone": row.tone,
            "provider": row.provider,
            "model": row.model,
            "prompt_bundle_version": row.prompt_bundle_version,
            "run": run_metadata,
        },
    )
    return {"success": True, "data": _serialize_outreach_response(row)}


def generate_outreach_for_lead(
    db: Session,
    tenant_id: str,
    lead_id: str,
    current_user: dict,
    payload: AugmisBusinessOutreachGenerateRequest,
) -> dict[str, Any]:
    lead = _require_lead(db, tenant_id, lead_id)
    patched_payload = payload.model_copy(update={"lead_id": lead.id})
    return generate_outreach_for_opportunity(
        db,
        tenant_id,
        lead.opportunity_id,
        current_user,
        patched_payload,
    )


def list_outreach_for_opportunity(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
) -> dict[str, Any]:
    _require_opportunity(db, tenant_id, opportunity_id)
    try:
        rows = (
            db.query(BusinessDevelopmentOutreachDraft)
            .filter(
                BusinessDevelopmentOutreachDraft.tenant_id == tenant_id,
                BusinessDevelopmentOutreachDraft.opportunity_id == opportunity_id,
            )
            .order_by(
                BusinessDevelopmentOutreachDraft.created_at.desc(),
                BusinessDevelopmentOutreachDraft.generation_version.desc(),
            )
            .all()
        )
    except DBAPIError as exc:
        _raise_generation_schema_missing(exc)
    return {"success": True, "data": [_serialize_outreach_summary(row) for row in rows]}


def _require_outreach_draft(
    db: Session,
    tenant_id: str,
    outreach_id: str,
) -> BusinessDevelopmentOutreachDraft:
    row = (
        db.query(BusinessDevelopmentOutreachDraft)
        .filter(
            BusinessDevelopmentOutreachDraft.tenant_id == tenant_id,
            BusinessDevelopmentOutreachDraft.id == outreach_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outreach draft not found")
    return row


def get_outreach_draft(db: Session, tenant_id: str, outreach_id: str) -> dict[str, Any]:
    return {"success": True, "data": _serialize_outreach_response(_require_outreach_draft(db, tenant_id, outreach_id))}


def update_outreach_draft(
    db: Session,
    tenant_id: str,
    outreach_id: str,
    current_user: dict,
    payload: AugmisBusinessOutreachDraftUpdateRequest,
) -> dict[str, Any]:
    row = _require_outreach_draft(db, tenant_id, outreach_id)
    if payload.subject is not None:
        row.subject = payload.subject.strip() or None
    if payload.body is not None:
        row.body = payload.body
    if payload.structured_content_json is not None:
        _validate_outreach_named_contact(
            payload.structured_content_json,
            _require_contact(db, tenant_id, row.contact_id) if row.contact_id else None,
        )
        row.structured_content_json = payload.structured_content_json.model_dump(mode="json")
        if payload.subject is None:
            row.subject = payload.structured_content_json.content.recommended_subject
        if payload.body is None:
            row.body = payload.structured_content_json.content.full_message
    if payload.status is not None:
        row.status = payload.status
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated outreach draft {row.id}",
        resource_type="bd_outreach_draft",
        resource_id=row.id,
    )
    return {"success": True, "data": _serialize_outreach_response(row)}


def approve_outreach_draft(
    db: Session,
    tenant_id: str,
    outreach_id: str,
    current_user: dict,
    payload: AugmisBusinessStatusActionRequest,
) -> dict[str, Any]:
    row = _require_outreach_draft(db, tenant_id, outreach_id)
    row.status = "approved"
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="APPROVE",
        event_category="AUGMIS_BUSINESS",
        description=f"Approved outreach draft {row.id}",
        resource_type="bd_outreach_draft",
        resource_id=row.id,
        metadata={"notes": payload.notes},
    )
    return {"success": True, "data": _serialize_outreach_response(row)}


def reject_outreach_draft(
    db: Session,
    tenant_id: str,
    outreach_id: str,
    current_user: dict,
    payload: AugmisBusinessStatusActionRequest,
) -> dict[str, Any]:
    row = _require_outreach_draft(db, tenant_id, outreach_id)
    row.status = "rejected"
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="REJECT",
        event_category="AUGMIS_BUSINESS",
        description=f"Rejected outreach draft {row.id}",
        resource_type="bd_outreach_draft",
        resource_id=row.id,
        metadata={"notes": payload.notes},
    )
    return {"success": True, "data": _serialize_outreach_response(row)}


def generate_mini_solution_for_opportunity(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
    current_user: dict,
    payload: AugmisBusinessMiniSolutionGenerateRequest,
) -> dict[str, Any]:
    context = _resolve_context(
        db,
        tenant_id,
        opportunity_id=opportunity_id,
        lead_id=payload.lead_id,
    )
    prompt = build_mini_solution_generation_prompt(
        context_payload=_build_generation_context_payload(context, tone=payload.tone),
        tone=payload.tone,
    )
    result, run_metadata = _run_json_agent(
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        opportunity_id=opportunity_id,
        lead_id=context["lead"].id if context["lead"] else None,
        generation_type="mini_solution",
        prompt_version=MINI_SOLUTION_GENERATION_PROMPT_VERSION,
        prompt=prompt,
        response_model=AugmisBusinessMiniSolutionContent,
        db=db,
    )
    version = _next_mini_solution_version(
        db, tenant_id, opportunity_id, context["lead"].id if context["lead"] else None
    )
    row = BusinessDevelopmentMiniSolution(
        id=f"BD-MSL-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        opportunity_id=opportunity_id,
        lead_id=context["lead"].id if context["lead"] else None,
        assessment_id=context["assessment_row"].id if context["assessment_row"] else None,
        title=result.title,
        solution_json=result.model_dump(mode="json"),
        generation_version=version,
        provider="openai",
        model=settings.OPENAI_MODEL,
        prompt_bundle_version=PROMPT_BUNDLE_VERSION,
        status="draft",
        created_by=current_user["user_id"],
        updated_at=_now(),
    )
    try:
        _supersede_previous_mini_solutions(
            db, tenant_id, opportunity_id, context["lead"].id if context["lead"] else None
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    except DBAPIError as exc:
        db.rollback()
        _raise_generation_schema_missing(exc)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="AI_MINI_SOLUTION_CREATED",
        event_category="AI",
        description=f"Generated mini solution {row.id}",
        resource_type="bd_mini_solution",
        resource_id=row.id,
        metadata={
            "opportunity_id": opportunity_id,
            "lead_id": row.lead_id,
            "generation_version": row.generation_version,
            "provider": row.provider,
            "model": row.model,
            "prompt_bundle_version": row.prompt_bundle_version,
            "run": run_metadata,
        },
    )
    return {"success": True, "data": _serialize_mini_solution_response(row)}


def generate_mini_solution_for_lead(
    db: Session,
    tenant_id: str,
    lead_id: str,
    current_user: dict,
    payload: AugmisBusinessMiniSolutionGenerateRequest,
) -> dict[str, Any]:
    lead = _require_lead(db, tenant_id, lead_id)
    patched_payload = payload.model_copy(update={"lead_id": lead.id})
    return generate_mini_solution_for_opportunity(
        db,
        tenant_id,
        lead.opportunity_id,
        current_user,
        patched_payload,
    )


def list_mini_solutions_for_opportunity(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
) -> dict[str, Any]:
    _require_opportunity(db, tenant_id, opportunity_id)
    try:
        rows = (
            db.query(BusinessDevelopmentMiniSolution)
            .filter(
                BusinessDevelopmentMiniSolution.tenant_id == tenant_id,
                BusinessDevelopmentMiniSolution.opportunity_id == opportunity_id,
            )
            .order_by(
                BusinessDevelopmentMiniSolution.created_at.desc(),
                BusinessDevelopmentMiniSolution.generation_version.desc(),
            )
            .all()
        )
    except DBAPIError as exc:
        _raise_generation_schema_missing(exc)
    return {"success": True, "data": [_serialize_mini_solution_summary(row) for row in rows]}


def _require_mini_solution(
    db: Session,
    tenant_id: str,
    solution_id: str,
) -> BusinessDevelopmentMiniSolution:
    row = (
        db.query(BusinessDevelopmentMiniSolution)
        .filter(
            BusinessDevelopmentMiniSolution.tenant_id == tenant_id,
            BusinessDevelopmentMiniSolution.id == solution_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mini solution not found")
    return row


def get_mini_solution(db: Session, tenant_id: str, solution_id: str) -> dict[str, Any]:
    return {"success": True, "data": _serialize_mini_solution_response(_require_mini_solution(db, tenant_id, solution_id))}


def update_mini_solution(
    db: Session,
    tenant_id: str,
    solution_id: str,
    current_user: dict,
    payload: AugmisBusinessMiniSolutionUpdateRequest,
) -> dict[str, Any]:
    row = _require_mini_solution(db, tenant_id, solution_id)
    if payload.title is not None:
        row.title = payload.title
    if payload.solution_json is not None:
        row.solution_json = payload.solution_json.model_dump(mode="json")
        if payload.title is None:
            row.title = payload.solution_json.title
    if payload.status is not None:
        row.status = payload.status
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated mini solution {row.id}",
        resource_type="bd_mini_solution",
        resource_id=row.id,
    )
    return {"success": True, "data": _serialize_mini_solution_response(row)}


def approve_mini_solution(
    db: Session,
    tenant_id: str,
    solution_id: str,
    current_user: dict,
    payload: AugmisBusinessStatusActionRequest,
) -> dict[str, Any]:
    row = _require_mini_solution(db, tenant_id, solution_id)
    row.status = "approved"
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="APPROVE",
        event_category="AUGMIS_BUSINESS",
        description=f"Approved mini solution {row.id}",
        resource_type="bd_mini_solution",
        resource_id=row.id,
        metadata={"notes": payload.notes},
    )
    return {"success": True, "data": _serialize_mini_solution_response(row)}


def reject_mini_solution(
    db: Session,
    tenant_id: str,
    solution_id: str,
    current_user: dict,
    payload: AugmisBusinessStatusActionRequest,
) -> dict[str, Any]:
    row = _require_mini_solution(db, tenant_id, solution_id)
    row.status = "rejected"
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="REJECT",
        event_category="AUGMIS_BUSINESS",
        description=f"Rejected mini solution {row.id}",
        resource_type="bd_mini_solution",
        resource_id=row.id,
        metadata={"notes": payload.notes},
    )
    return {"success": True, "data": _serialize_mini_solution_response(row)}
