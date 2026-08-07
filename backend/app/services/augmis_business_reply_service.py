from __future__ import annotations

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
    BusinessDevelopmentLead,
    BusinessDevelopmentMiniSolution,
    BusinessDevelopmentOpportunity,
    BusinessDevelopmentOpportunityAIAssessment,
    BusinessDevelopmentOutreachDraft,
    BusinessDevelopmentProspect,
    BusinessDevelopmentReply,
    BusinessDevelopmentReplyAIAnalysis,
    BusinessDevelopmentReplyResponseDraft,
)
from app.models.augmis_business_models import (
    AugmisBusinessReplyAnalysisResponse,
    AugmisBusinessReplyAnalysisResult,
    AugmisBusinessReplyAnalysisSummary,
    AugmisBusinessReplyCreateRequest,
    AugmisBusinessReplyResponseContent,
    AugmisBusinessReplyResponseDraftResponse,
    AugmisBusinessReplyResponseDraftSummary,
    AugmisBusinessReplyResponseDraftUpdateRequest,
    AugmisBusinessReplyResponseGenerateRequest,
    AugmisBusinessReplySummary,
    AugmisBusinessReplyUpdateRequest,
    AugmisBusinessStatusActionRequest,
)
from app.services.ai_service import client as openai_client
from app.services.audit_service import create_audit_log
from app.services.augmis_business_generation_service import (
    _extract_json_object,
    _serialize_usage_metadata,
    _sanitize_text_list,
)
from app.services.augmis_business_reply_prompts import (
    PROMPT_BUNDLE_VERSION,
    REPLY_ANALYSIS_PROMPT_VERSION,
    REPLY_RESPONSE_GENERATION_PROMPT_VERSION,
    build_reply_analysis_prompt,
    build_reply_response_generation_prompt,
)
from app.services.augmis_business_service import (
    _clean_text,
    _create_activity_row,
    _now,
    _require_contact,
    _require_lead,
    _require_opportunity,
    _require_prospect,
    _serialize_datetime,
    serialize_contact,
    serialize_lead,
    serialize_opportunity,
    serialize_prospect,
)
from app.services.subscription_service import add_ai_token_usage, validate_usage_limit
from app.services.token_usage_service import estimate_ai_usage_tokens


ModelT = TypeVar("ModelT", bound=BaseModel)
REPLY_SCHEMA_TABLES = (
    "bd_replies",
    "bd_reply_ai_analyses",
    "bd_reply_response_drafts",
)


def _is_missing_reply_schema_error(error: Exception) -> bool:
    message = str(error)
    return any(
        f'relation "{table}" does not exist' in message or f"no such table: {table}" in message
        for table in REPLY_SCHEMA_TABLES
    )


def _raise_reply_schema_missing(error: Exception) -> None:
    if not _is_missing_reply_schema_error(error):
        raise error
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "AUGMIS Business reply tables are not initialized yet. "
            "Apply the Phase 4C Alembic migration and retry."
        ),
    ) from error


def _require_openai_api_key() -> None:
    if not str(settings.OPENAI_API_KEY or "").strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI reply processing is unavailable because the OpenAI API key is not configured.",
        )


def _determine_reply_status(result: AugmisBusinessReplyAnalysisResult) -> str:
    if (
        result.questions_from_prospect
        or result.objections
        or result.requested_actions
        or result.recommended_task is not None
        or result.recommended_pipeline_stage is not None
        or result.intent
        in {
            "meeting_requested",
            "demo_requested",
            "proposal_requested",
            "pricing_requested",
            "technical_questions",
            "procurement_process",
            "legal_compliance",
            "objection",
            "defer",
            "referral",
            "wrong_contact",
        }
    ):
        return "action_required"
    return "analyzed"


def _reply_preview(message: str, limit: int = 140) -> str:
    text = " ".join(str(message or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


def _serialize_assessment_context(row: BusinessDevelopmentOpportunityAIAssessment | None) -> dict[str, Any] | None:
    if row is None:
        return None
    qualification = row.qualification_json or {}
    return {
        "recommendation": row.recommendation,
        "fit_score": row.final_fit_score,
        "qualification_summary": qualification.get("explanation"),
        "risks": _sanitize_text_list(qualification.get("risks") or row.risks_json or []),
        "missing_information": _sanitize_text_list(
            qualification.get("missing_information") or row.missing_information_json or []
        ),
        "confidence_score": row.confidence_score,
    }


def _serialize_reply_analysis_summary(
    row: BusinessDevelopmentReplyAIAnalysis,
) -> dict[str, Any]:
    return AugmisBusinessReplyAnalysisSummary(
        id=row.id,
        reply_id=row.reply_id,
        analysis_version=row.analysis_version,
        provider=row.provider,
        model=row.model,
        prompt_bundle_version=row.prompt_bundle_version,
        intent=row.intent,
        sentiment=row.sentiment,
        engagement_level=row.engagement_level,
        urgency=row.urgency,
        objection_category=row.objection_category,
        recommended_pipeline_stage=row.recommended_pipeline_stage,
        recommended_next_action=row.recommended_next_action,
        confidence_score=row.confidence_score,
        created_by=row.created_by,
        created_at=row.created_at,
    ).model_dump(mode="json")


def _serialize_reply_analysis_response(
    row: BusinessDevelopmentReplyAIAnalysis,
) -> dict[str, Any]:
    return AugmisBusinessReplyAnalysisResponse(
        **_serialize_reply_analysis_summary(row),
        analysis_json=AugmisBusinessReplyAnalysisResult.model_validate(row.analysis_json or {}),
    ).model_dump(mode="json")


def _serialize_reply_response_summary(
    row: BusinessDevelopmentReplyResponseDraft,
) -> dict[str, Any]:
    return AugmisBusinessReplyResponseDraftSummary(
        id=row.id,
        reply_id=row.reply_id,
        opportunity_id=row.opportunity_id,
        lead_id=row.lead_id,
        prospect_id=row.prospect_id,
        contact_id=row.contact_id,
        analysis_id=row.analysis_id,
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


def _serialize_reply_response(
    row: BusinessDevelopmentReplyResponseDraft,
) -> dict[str, Any]:
    return AugmisBusinessReplyResponseDraftResponse(
        **_serialize_reply_response_summary(row),
        body=row.body,
        structured_content_json=AugmisBusinessReplyResponseContent.model_validate(
            row.structured_content_json or {}
        ),
    ).model_dump(mode="json")


def _latest_reply_analysis_rows(
    db: Session,
    tenant_id: str,
    reply_ids: list[str],
) -> dict[str, BusinessDevelopmentReplyAIAnalysis]:
    if not reply_ids:
        return {}
    rows = (
        db.query(BusinessDevelopmentReplyAIAnalysis)
        .filter(
            BusinessDevelopmentReplyAIAnalysis.tenant_id == tenant_id,
            BusinessDevelopmentReplyAIAnalysis.reply_id.in_(reply_ids),
        )
        .order_by(
            BusinessDevelopmentReplyAIAnalysis.reply_id.asc(),
            BusinessDevelopmentReplyAIAnalysis.analysis_version.desc(),
            BusinessDevelopmentReplyAIAnalysis.created_at.desc(),
        )
        .all()
    )
    latest: dict[str, BusinessDevelopmentReplyAIAnalysis] = {}
    for row in rows:
        latest.setdefault(row.reply_id, row)
    return latest


def _latest_reply_response_rows(
    db: Session,
    tenant_id: str,
    reply_ids: list[str],
) -> dict[str, BusinessDevelopmentReplyResponseDraft]:
    if not reply_ids:
        return {}
    rows = (
        db.query(BusinessDevelopmentReplyResponseDraft)
        .filter(
            BusinessDevelopmentReplyResponseDraft.tenant_id == tenant_id,
            BusinessDevelopmentReplyResponseDraft.reply_id.in_(reply_ids),
        )
        .order_by(
            BusinessDevelopmentReplyResponseDraft.reply_id.asc(),
            BusinessDevelopmentReplyResponseDraft.generation_version.desc(),
            BusinessDevelopmentReplyResponseDraft.created_at.desc(),
        )
        .all()
    )
    latest: dict[str, BusinessDevelopmentReplyResponseDraft] = {}
    for row in rows:
        latest.setdefault(row.reply_id, row)
    return latest


def _serialize_reply(
    row: BusinessDevelopmentReply,
    *,
    lead: BusinessDevelopmentLead | None = None,
    prospect: BusinessDevelopmentProspect | None = None,
    contact: BusinessDevelopmentContact | None = None,
    latest_analysis: BusinessDevelopmentReplyAIAnalysis | None = None,
    latest_response: BusinessDevelopmentReplyResponseDraft | None = None,
) -> dict[str, Any]:
    return AugmisBusinessReplySummary(
        id=row.id,
        opportunity_id=row.opportunity_id,
        lead_id=row.lead_id,
        prospect_id=row.prospect_id,
        contact_id=row.contact_id,
        outreach_id=row.outreach_id,
        channel=row.channel,
        subject=row.subject,
        raw_message=row.raw_message,
        sender_display=row.sender_display,
        received_at=row.received_at,
        reply_status=row.reply_status,
        notes=row.notes,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
        lead_title=lead.title if lead else None,
        prospect_name=prospect.organization_name if prospect else None,
        contact_name=(contact.full_name or contact.job_title or contact.email or contact.phone)
        if contact
        else None,
        latest_intent=latest_analysis.intent if latest_analysis else None,
        latest_engagement_level=latest_analysis.engagement_level if latest_analysis else None,
        latest_urgency=latest_analysis.urgency if latest_analysis else None,
        latest_sentiment=latest_analysis.sentiment if latest_analysis else None,
        latest_analysis_id=latest_analysis.id if latest_analysis else None,
        latest_analysis_created_at=latest_analysis.created_at if latest_analysis else None,
        latest_response_id=latest_response.id if latest_response else None,
        latest_response_status=latest_response.status if latest_response else None,
        latest_response_created_at=latest_response.created_at if latest_response else None,
    ).model_dump(mode="json")


def _require_reply(db: Session, tenant_id: str, reply_id: str) -> BusinessDevelopmentReply:
    row = (
        db.query(BusinessDevelopmentReply)
        .filter(
            BusinessDevelopmentReply.tenant_id == tenant_id,
            BusinessDevelopmentReply.id == reply_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reply not found")
    return row


def _require_reply_analysis(
    db: Session, tenant_id: str, analysis_id: str
) -> BusinessDevelopmentReplyAIAnalysis:
    row = (
        db.query(BusinessDevelopmentReplyAIAnalysis)
        .filter(
            BusinessDevelopmentReplyAIAnalysis.tenant_id == tenant_id,
            BusinessDevelopmentReplyAIAnalysis.id == analysis_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reply analysis not found")
    return row


def _require_reply_response(
    db: Session, tenant_id: str, response_id: str
) -> BusinessDevelopmentReplyResponseDraft:
    row = (
        db.query(BusinessDevelopmentReplyResponseDraft)
        .filter(
            BusinessDevelopmentReplyResponseDraft.tenant_id == tenant_id,
            BusinessDevelopmentReplyResponseDraft.id == response_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reply response not found")
    return row


def _resolve_reply_context(
    db: Session, tenant_id: str, reply: BusinessDevelopmentReply
) -> dict[str, Any]:
    lead = _require_lead(db, tenant_id, reply.lead_id)
    prospect = _require_prospect(db, tenant_id, lead.prospect_id)
    opportunity = _require_opportunity(db, tenant_id, lead.opportunity_id)
    contact = _require_contact(db, tenant_id, reply.contact_id) if reply.contact_id else None

    latest_assessment = (
        db.query(BusinessDevelopmentOpportunityAIAssessment)
        .filter(
            BusinessDevelopmentOpportunityAIAssessment.tenant_id == tenant_id,
            BusinessDevelopmentOpportunityAIAssessment.opportunity_id == opportunity.id,
        )
        .order_by(
            BusinessDevelopmentOpportunityAIAssessment.assessment_version.desc(),
            BusinessDevelopmentOpportunityAIAssessment.created_at.desc(),
        )
        .first()
    )
    latest_outreach = (
        db.query(BusinessDevelopmentOutreachDraft)
        .filter(
            BusinessDevelopmentOutreachDraft.tenant_id == tenant_id,
            BusinessDevelopmentOutreachDraft.lead_id == lead.id,
            BusinessDevelopmentOutreachDraft.status.in_(["approved", "reviewed"]),
        )
        .order_by(
            BusinessDevelopmentOutreachDraft.generation_version.desc(),
            BusinessDevelopmentOutreachDraft.created_at.desc(),
        )
        .first()
    )
    latest_solution = (
        db.query(BusinessDevelopmentMiniSolution)
        .filter(
            BusinessDevelopmentMiniSolution.tenant_id == tenant_id,
            BusinessDevelopmentMiniSolution.lead_id == lead.id,
            BusinessDevelopmentMiniSolution.status.in_(["approved", "reviewed", "draft"]),
        )
        .order_by(
            BusinessDevelopmentMiniSolution.generation_version.desc(),
            BusinessDevelopmentMiniSolution.created_at.desc(),
        )
        .first()
    )
    latest_analysis = (
        db.query(BusinessDevelopmentReplyAIAnalysis)
        .filter(
            BusinessDevelopmentReplyAIAnalysis.tenant_id == tenant_id,
            BusinessDevelopmentReplyAIAnalysis.reply_id == reply.id,
        )
        .order_by(
            BusinessDevelopmentReplyAIAnalysis.analysis_version.desc(),
            BusinessDevelopmentReplyAIAnalysis.created_at.desc(),
        )
        .first()
    )
    return {
        "reply": reply,
        "lead": lead,
        "prospect": prospect,
        "opportunity": opportunity,
        "contact": contact,
        "latest_assessment": latest_assessment,
        "latest_outreach": latest_outreach,
        "latest_solution": latest_solution,
        "latest_analysis": latest_analysis,
    }


def _build_reply_analysis_context(context: dict[str, Any]) -> dict[str, Any]:
    reply: BusinessDevelopmentReply = context["reply"]
    lead: BusinessDevelopmentLead = context["lead"]
    prospect: BusinessDevelopmentProspect = context["prospect"]
    opportunity: BusinessDevelopmentOpportunity = context["opportunity"]
    contact: BusinessDevelopmentContact | None = context["contact"]
    latest_assessment = context["latest_assessment"]
    latest_outreach = context["latest_outreach"]
    latest_solution = context["latest_solution"]
    return {
        "reply": {
            "subject": reply.subject,
            "raw_message": reply.raw_message,
            "sender_display": reply.sender_display,
            "channel": reply.channel,
            "received_at": _serialize_datetime(reply.received_at),
            "notes": reply.notes,
        },
        "lead": {
            "id": lead.id,
            "title": lead.title,
            "current_stage": lead.lead_stage,
            "status": lead.lead_status,
            "priority": lead.priority,
            "probability": lead.probability_pct,
            "next_action": None,
        },
        "prospect": {
            "organization_name": prospect.organization_name,
            "industry": prospect.industry,
            "country": prospect.country,
        },
        "contact": serialize_contact(contact) if contact else None,
        "opportunity": {
            "title": opportunity.title,
            "organization_name": opportunity.organization_name,
            "requirement_summary": opportunity.requirement_summary,
            "business_problem": opportunity.business_problem,
            "expected_deliverables_json": opportunity.expected_deliverables_json or [],
        },
        "ai_assessment": _serialize_assessment_context(latest_assessment),
        "latest_outreach": {
            "outreach_type": latest_outreach.outreach_type,
            "tone": latest_outreach.tone,
            "subject": latest_outreach.subject,
            "body": latest_outreach.body,
            "status": latest_outreach.status,
        }
        if latest_outreach
        else None,
        "latest_mini_solution": {
            "title": latest_solution.title,
            "status": latest_solution.status,
            "solution_json": latest_solution.solution_json,
        }
        if latest_solution
        else None,
    }


def _build_reply_response_context(context: dict[str, Any]) -> dict[str, Any]:
    reply_payload = _build_reply_analysis_context(context)
    latest_analysis = context["latest_analysis"]
    reply_payload["latest_reply_analysis"] = (
        _serialize_reply_analysis_response(latest_analysis) if latest_analysis else None
    )
    return reply_payload


def _run_json_agent(
    *,
    tenant_id: str,
    user_id: str,
    lead_id: str,
    reply_id: str,
    ai_run_type: str,
    prompt_version: str,
    prompt: str,
    response_model: type[ModelT],
    db: Session,
) -> tuple[ModelT, dict[str, Any]]:
    _require_openai_api_key()
    validate_usage_limit(tenant_id, "ai_tokens", db)
    started_at = _now()
    max_attempts = 2
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a controlled AUGMIS Business AI engine. Return JSON only.",
                    },
                    {"role": "user", "content": prompt},
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
                "lead_id": lead_id,
                "reply_id": reply_id,
                "ai_run_type": ai_run_type,
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
                description=f"AUGMIS Business reply AI completed: {ai_run_type}",
                resource_type="bd_reply",
                resource_id=reply_id,
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
        description=f"AUGMIS Business reply AI failed: {ai_run_type}",
        resource_type="bd_reply",
        resource_id=reply_id,
        metadata={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "lead_id": lead_id,
            "reply_id": reply_id,
            "ai_run_type": ai_run_type,
            "provider": "openai",
            "model": settings.OPENAI_MODEL,
            "prompt_version": prompt_version,
            "started_at": _serialize_datetime(started_at),
            "completed_at": _serialize_datetime(completed_at),
            "status": "failed",
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": estimate_ai_usage_tokens(prompt, "", ""),
            "estimated_cost_usd": None,
            "error_message": str(last_error or "Unknown AI error"),
        },
    )
    if isinstance(last_error, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI returned an invalid structured reply result: {last_error.errors()}",
        ) from last_error
    if isinstance(last_error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI returned malformed JSON: {last_error}",
        ) from last_error
    if isinstance(last_error, APITimeoutError):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI reply processing timed out. Retry in a moment.",
        ) from last_error
    if isinstance(last_error, RateLimitError):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI reply processing hit a rate limit. Retry in a moment.",
        ) from last_error
    if isinstance(last_error, OpenAIError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI provider error during reply processing: {last_error}",
        ) from last_error
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unexpected AI reply processing error: {last_error}",
    ) from last_error


def create_reply(
    db: Session,
    tenant_id: str,
    current_user: dict,
    payload: AugmisBusinessReplyCreateRequest,
) -> dict[str, Any]:
    try:
        lead = _require_lead(db, tenant_id, payload.lead_id)
        prospect = _require_prospect(db, tenant_id, lead.prospect_id)
        contact = None
        if payload.contact_id:
            contact = _require_contact(db, tenant_id, payload.contact_id)
            if contact.prospect_id != lead.prospect_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reply contact must belong to the same prospect as the lead",
                )
        if payload.outreach_id:
            outreach = (
                db.query(BusinessDevelopmentOutreachDraft)
                .filter(
                    BusinessDevelopmentOutreachDraft.tenant_id == tenant_id,
                    BusinessDevelopmentOutreachDraft.id == payload.outreach_id,
                )
                .first()
            )
            if not outreach or outreach.lead_id != lead.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Referenced outreach draft not found for this lead",
                )

        row = BusinessDevelopmentReply(
            id=f"BD-RPY-{str(uuid4())[:12].upper()}",
            tenant_id=tenant_id,
            opportunity_id=lead.opportunity_id,
            lead_id=lead.id,
            prospect_id=lead.prospect_id,
            contact_id=payload.contact_id,
            outreach_id=payload.outreach_id,
            channel=payload.channel,
            subject=_clean_text(payload.subject),
            raw_message=payload.raw_message.strip(),
            sender_display=_clean_text(payload.sender_display),
            received_at=payload.received_at.astimezone(timezone.utc),
            reply_status="received",
            notes=_clean_text(payload.notes),
            created_by=current_user["user_id"],
            updated_at=_now(),
        )
        db.add(row)
        activity = _create_activity_row(
            tenant_id=tenant_id,
            current_user=current_user,
            activity_type="reply_recorded",
            subject=f"Reply recorded for {lead.title}",
            description=_reply_preview(row.raw_message),
            lead_id=lead.id,
            opportunity_id=lead.opportunity_id,
            prospect_id=lead.prospect_id,
            contact_id=row.contact_id,
            activity_at=row.received_at,
            direction="inbound",
            metadata_json={"reply_id": row.id, "channel": row.channel},
        )
        db.add(activity)
        db.commit()
        db.refresh(row)
    except DBAPIError as exc:
        db.rollback()
        _raise_reply_schema_missing(exc)

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="CREATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Recorded inbound reply {row.id}",
        resource_type="bd_reply",
        resource_id=row.id,
        metadata={"lead_id": row.lead_id, "channel": row.channel},
    )
    return {
        "success": True,
        "data": _serialize_reply(row, lead=lead, prospect=prospect, contact=contact),
    }


def update_reply(
    db: Session,
    tenant_id: str,
    reply_id: str,
    current_user: dict,
    payload: AugmisBusinessReplyUpdateRequest,
) -> dict[str, Any]:
    try:
        row = _require_reply(db, tenant_id, reply_id)
        lead = _require_lead(db, tenant_id, row.lead_id)
        changes = payload.model_dump(exclude_unset=True)
        if "contact_id" in changes and changes["contact_id"]:
            contact = _require_contact(db, tenant_id, changes["contact_id"])
            if contact.prospect_id != lead.prospect_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reply contact must belong to the same prospect as the lead",
                )
        for key, value in changes.items():
            if key == "received_at" and value is not None:
                setattr(row, key, value.astimezone(timezone.utc))
            elif isinstance(value, str) or value is None:
                setattr(row, key, _clean_text(value) if key not in {"channel", "reply_status"} else value)
            else:
                setattr(row, key, value)
        row.updated_at = _now()
        db.commit()
        db.refresh(row)
    except DBAPIError as exc:
        db.rollback()
        _raise_reply_schema_missing(exc)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated reply {row.id}",
        resource_type="bd_reply",
        resource_id=row.id,
        metadata={"updated_fields": sorted(changes.keys())},
    )
    context = _resolve_reply_context(db, tenant_id, row)
    return {
        "success": True,
        "data": _serialize_reply(
            row,
            lead=context["lead"],
            prospect=context["prospect"],
            contact=context["contact"],
            latest_analysis=context["latest_analysis"],
            latest_response=_latest_reply_response_rows(db, tenant_id, [row.id]).get(row.id),
        ),
    }


def list_replies(
    db: Session,
    tenant_id: str,
    *,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    status_filter: str | None = None,
    intent: str | None = None,
    lead_id: str | None = None,
) -> dict[str, Any]:
    try:
        rows = (
            db.query(BusinessDevelopmentReply)
            .filter(BusinessDevelopmentReply.tenant_id == tenant_id)
            .order_by(BusinessDevelopmentReply.received_at.desc(), BusinessDevelopmentReply.created_at.desc())
            .all()
        )
    except DBAPIError as exc:
        _raise_reply_schema_missing(exc)
    latest_analysis_map = _latest_reply_analysis_rows(db, tenant_id, [row.id for row in rows])
    latest_response_map = _latest_reply_response_rows(db, tenant_id, [row.id for row in rows])

    filtered: list[BusinessDevelopmentReply] = []
    for row in rows:
        latest_analysis = latest_analysis_map.get(row.id)
        haystacks = [
            row.subject or "",
            row.raw_message or "",
            row.sender_display or "",
            row.id,
        ]
        if lead_id and row.lead_id != lead_id:
            continue
        if status_filter and row.reply_status != status_filter.strip().lower():
            continue
        if intent and (not latest_analysis or latest_analysis.intent != intent.strip().lower()):
            continue
        if search and search.strip():
            needle = search.strip().lower()
            if not any(needle in candidate.lower() for candidate in haystacks):
                continue
        filtered.append(row)

    total = len(filtered)
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 100)
    start = (safe_page - 1) * safe_page_size
    page_rows = filtered[start : start + safe_page_size]

    lead_map = {
        row.id: row
        for row in db.query(BusinessDevelopmentLead)
        .filter(BusinessDevelopmentLead.tenant_id == tenant_id)
        .all()
    }
    prospect_map = {
        row.id: row
        for row in db.query(BusinessDevelopmentProspect)
        .filter(BusinessDevelopmentProspect.tenant_id == tenant_id)
        .all()
    }
    contact_map = {
        row.id: row
        for row in db.query(BusinessDevelopmentContact)
        .filter(BusinessDevelopmentContact.tenant_id == tenant_id)
        .all()
    }

    summary = {
        "unreviewed_replies": sum(1 for row in filtered if row.reply_status == "received"),
        "action_required": sum(1 for row in filtered if row.reply_status == "action_required"),
        "positive_high_engagement": sum(
            1
            for row in filtered
            if (analysis := latest_analysis_map.get(row.id))
            and analysis.sentiment == "positive"
            and analysis.engagement_level == "high"
        ),
        "objections": sum(
            1
            for row in filtered
            if (analysis := latest_analysis_map.get(row.id))
            and analysis.intent == "objection"
        ),
        "meetings_or_proposals": sum(
            1
            for row in filtered
            if (analysis := latest_analysis_map.get(row.id))
            and analysis.intent in {"meeting_requested", "proposal_requested", "demo_requested"}
        ),
    }
    return {
        "success": True,
        "data": [
            _serialize_reply(
                row,
                lead=lead_map.get(row.lead_id),
                prospect=prospect_map.get(row.prospect_id) if row.prospect_id else None,
                contact=contact_map.get(row.contact_id) if row.contact_id else None,
                latest_analysis=latest_analysis_map.get(row.id),
                latest_response=latest_response_map.get(row.id),
            )
            for row in page_rows
        ],
        "summary": summary,
        "pagination": {
            "page": safe_page,
            "page_size": safe_page_size,
            "total": total,
            "total_pages": (total + safe_page_size - 1) // safe_page_size if total else 0,
        },
    }


def get_reply(db: Session, tenant_id: str, reply_id: str) -> dict[str, Any]:
    row = _require_reply(db, tenant_id, reply_id)
    context = _resolve_reply_context(db, tenant_id, row)
    latest_response = _latest_reply_response_rows(db, tenant_id, [row.id]).get(row.id)
    return {
        "success": True,
        "data": {
            **_serialize_reply(
                row,
                lead=context["lead"],
                prospect=context["prospect"],
                contact=context["contact"],
                latest_analysis=context["latest_analysis"],
                latest_response=latest_response,
            ),
            "lead": serialize_lead(
                context["lead"],
                prospect=context["prospect"],
                primary_contact=context["contact"]
                if context["contact"] and context["lead"].primary_contact_id == context["contact"].id
                else (_require_contact(db, tenant_id, context["lead"].primary_contact_id) if context["lead"].primary_contact_id else None),
                opportunity=context["opportunity"],
                experience_matches=[],
            ),
            "prospect": serialize_prospect(context["prospect"]),
            "contact": serialize_contact(context["contact"]) if context["contact"] else None,
            "opportunity": serialize_opportunity(context["opportunity"]),
        },
    }


def _next_reply_analysis_version(db: Session, tenant_id: str, reply_id: str) -> int:
    row = (
        db.query(BusinessDevelopmentReplyAIAnalysis)
        .filter(
            BusinessDevelopmentReplyAIAnalysis.tenant_id == tenant_id,
            BusinessDevelopmentReplyAIAnalysis.reply_id == reply_id,
        )
        .order_by(BusinessDevelopmentReplyAIAnalysis.analysis_version.desc())
        .first()
    )
    return 1 if not row else row.analysis_version + 1


def analyze_reply(
    db: Session,
    tenant_id: str,
    reply_id: str,
    current_user: dict,
) -> dict[str, Any]:
    row = _require_reply(db, tenant_id, reply_id)
    context = _resolve_reply_context(db, tenant_id, row)
    prompt = build_reply_analysis_prompt(_build_reply_analysis_context(context))
    result, _run_summary = _run_json_agent(
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        lead_id=row.lead_id,
        reply_id=row.id,
        ai_run_type="reply_analysis",
        prompt_version=REPLY_ANALYSIS_PROMPT_VERSION,
        prompt=prompt,
        response_model=AugmisBusinessReplyAnalysisResult,
        db=db,
    )
    version = _next_reply_analysis_version(db, tenant_id, row.id)
    analysis_row = BusinessDevelopmentReplyAIAnalysis(
        id=f"BD-RAN-{version}-{row.id[-8:]}",
        tenant_id=tenant_id,
        reply_id=row.id,
        analysis_version=version,
        provider="openai",
        model=settings.OPENAI_MODEL,
        prompt_bundle_version=PROMPT_BUNDLE_VERSION,
        intent=result.intent,
        sentiment=result.sentiment,
        engagement_level=result.engagement_level,
        urgency=result.urgency,
        objection_category=result.objections[0].category if result.objections else None,
        recommended_pipeline_stage=result.recommended_pipeline_stage,
        recommended_next_action=result.recommended_next_action,
        analysis_json=result.model_dump(mode="json"),
        confidence_score=result.confidence,
        created_by=current_user["user_id"],
    )
    row.reply_status = _determine_reply_status(result)
    row.updated_at = _now()
    activity = _create_activity_row(
        tenant_id=tenant_id,
        current_user=current_user,
        activity_type="reply_analyzed",
        subject=f"Reply analyzed for {context['lead'].title}",
        description=result.summary,
        lead_id=row.lead_id,
        opportunity_id=row.opportunity_id,
        prospect_id=row.prospect_id,
        contact_id=row.contact_id,
        metadata_json={
            "reply_id": row.id,
            "analysis_id": analysis_row.id,
            "intent": result.intent,
            "engagement_level": result.engagement_level,
        },
    )
    try:
        db.add(analysis_row)
        db.add(activity)
        db.commit()
        db.refresh(analysis_row)
        db.refresh(row)
    except DBAPIError as exc:
        db.rollback()
        _raise_reply_schema_missing(exc)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="CREATE",
        event_category="AI",
        description=f"Analyzed reply {row.id}",
        resource_type="bd_reply_analysis",
        resource_id=analysis_row.id,
        metadata={"reply_id": row.id, "analysis_version": analysis_row.analysis_version},
    )
    return {"success": True, "data": _serialize_reply_analysis_response(analysis_row)}


def get_latest_reply_analysis(db: Session, tenant_id: str, reply_id: str) -> dict[str, Any]:
    _require_reply(db, tenant_id, reply_id)
    row = (
        db.query(BusinessDevelopmentReplyAIAnalysis)
        .filter(
            BusinessDevelopmentReplyAIAnalysis.tenant_id == tenant_id,
            BusinessDevelopmentReplyAIAnalysis.reply_id == reply_id,
        )
        .order_by(
            BusinessDevelopmentReplyAIAnalysis.analysis_version.desc(),
            BusinessDevelopmentReplyAIAnalysis.created_at.desc(),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reply analysis not found")
    return {"success": True, "data": _serialize_reply_analysis_response(row)}


def list_reply_analyses(db: Session, tenant_id: str, reply_id: str) -> dict[str, Any]:
    _require_reply(db, tenant_id, reply_id)
    rows = (
        db.query(BusinessDevelopmentReplyAIAnalysis)
        .filter(
            BusinessDevelopmentReplyAIAnalysis.tenant_id == tenant_id,
            BusinessDevelopmentReplyAIAnalysis.reply_id == reply_id,
        )
        .order_by(
            BusinessDevelopmentReplyAIAnalysis.analysis_version.desc(),
            BusinessDevelopmentReplyAIAnalysis.created_at.desc(),
        )
        .all()
    )
    return {"success": True, "data": [_serialize_reply_analysis_summary(row) for row in rows]}


def _next_reply_response_version(db: Session, tenant_id: str, reply_id: str) -> int:
    row = (
        db.query(BusinessDevelopmentReplyResponseDraft)
        .filter(
            BusinessDevelopmentReplyResponseDraft.tenant_id == tenant_id,
            BusinessDevelopmentReplyResponseDraft.reply_id == reply_id,
        )
        .order_by(BusinessDevelopmentReplyResponseDraft.generation_version.desc())
        .first()
    )
    return 1 if not row else row.generation_version + 1


def _supersede_previous_reply_responses(db: Session, tenant_id: str, reply_id: str) -> None:
    rows = (
        db.query(BusinessDevelopmentReplyResponseDraft)
        .filter(
            BusinessDevelopmentReplyResponseDraft.tenant_id == tenant_id,
            BusinessDevelopmentReplyResponseDraft.reply_id == reply_id,
            BusinessDevelopmentReplyResponseDraft.status.in_(["draft", "reviewed"]),
        )
        .all()
    )
    for row in rows:
        row.status = "superseded"
        row.updated_at = _now()


def generate_reply_response(
    db: Session,
    tenant_id: str,
    reply_id: str,
    current_user: dict,
    payload: AugmisBusinessReplyResponseGenerateRequest,
) -> dict[str, Any]:
    reply = _require_reply(db, tenant_id, reply_id)
    context = _resolve_reply_context(db, tenant_id, reply)
    if not context["latest_analysis"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analyze the reply before generating a response draft.",
        )
    prompt = build_reply_response_generation_prompt(
        _build_reply_response_context(context), strategy=payload.strategy
    )
    result, _run_summary = _run_json_agent(
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        lead_id=reply.lead_id,
        reply_id=reply.id,
        ai_run_type="reply_response_generation",
        prompt_version=REPLY_RESPONSE_GENERATION_PROMPT_VERSION,
        prompt=prompt,
        response_model=AugmisBusinessReplyResponseContent,
        db=db,
    )
    version = _next_reply_response_version(db, tenant_id, reply.id)
    row = BusinessDevelopmentReplyResponseDraft(
        id=f"BD-RRD-{version}-{reply.id[-8:]}",
        tenant_id=tenant_id,
        reply_id=reply.id,
        opportunity_id=reply.opportunity_id,
        lead_id=reply.lead_id,
        prospect_id=reply.prospect_id,
        contact_id=reply.contact_id,
        analysis_id=context["latest_analysis"].id,
        tone=payload.strategy,
        subject=_clean_text(result.subject),
        body=result.full_message.strip(),
        structured_content_json=result.model_dump(mode="json"),
        generation_version=version,
        provider="openai",
        model=settings.OPENAI_MODEL,
        prompt_bundle_version=PROMPT_BUNDLE_VERSION,
        status="draft",
        created_by=current_user["user_id"],
        updated_at=_now(),
    )
    activity = _create_activity_row(
        tenant_id=tenant_id,
        current_user=current_user,
        activity_type="reply_response_generated",
        subject=f"Response draft generated for {context['lead'].title}",
        description=_reply_preview(result.full_message),
        lead_id=reply.lead_id,
        opportunity_id=reply.opportunity_id,
        prospect_id=reply.prospect_id,
        contact_id=reply.contact_id,
        metadata_json={"reply_id": reply.id, "response_id": row.id, "strategy": payload.strategy},
    )
    try:
        _supersede_previous_reply_responses(db, tenant_id, reply.id)
        db.add(row)
        db.add(activity)
        db.commit()
        db.refresh(row)
    except DBAPIError as exc:
        db.rollback()
        _raise_reply_schema_missing(exc)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="CREATE",
        event_category="AI",
        description=f"Generated reply response draft {row.id}",
        resource_type="bd_reply_response_draft",
        resource_id=row.id,
        metadata={"reply_id": reply.id, "generation_version": row.generation_version},
    )
    return {"success": True, "data": _serialize_reply_response(row)}


def list_reply_responses(db: Session, tenant_id: str, reply_id: str) -> dict[str, Any]:
    _require_reply(db, tenant_id, reply_id)
    rows = (
        db.query(BusinessDevelopmentReplyResponseDraft)
        .filter(
            BusinessDevelopmentReplyResponseDraft.tenant_id == tenant_id,
            BusinessDevelopmentReplyResponseDraft.reply_id == reply_id,
        )
        .order_by(
            BusinessDevelopmentReplyResponseDraft.generation_version.desc(),
            BusinessDevelopmentReplyResponseDraft.created_at.desc(),
        )
        .all()
    )
    return {"success": True, "data": [_serialize_reply_response_summary(row) for row in rows]}


def get_reply_response(db: Session, tenant_id: str, response_id: str) -> dict[str, Any]:
    return {
        "success": True,
        "data": _serialize_reply_response(_require_reply_response(db, tenant_id, response_id)),
    }


def update_reply_response(
    db: Session,
    tenant_id: str,
    response_id: str,
    current_user: dict,
    payload: AugmisBusinessReplyResponseDraftUpdateRequest,
) -> dict[str, Any]:
    row = _require_reply_response(db, tenant_id, response_id)
    changes = payload.model_dump(exclude_unset=True)
    if "subject" in changes:
        row.subject = _clean_text(changes["subject"])
    if "body" in changes and changes["body"] is not None:
        row.body = changes["body"].strip()
    if "structured_content_json" in changes and changes["structured_content_json"] is not None:
        structured_payload = changes["structured_content_json"]
        row.structured_content_json = AugmisBusinessReplyResponseContent.model_validate(
            structured_payload
        ).model_dump(mode="json")
    if "status" in changes and changes["status"] is not None:
        row.status = changes["status"]
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated reply response draft {row.id}",
        resource_type="bd_reply_response_draft",
        resource_id=row.id,
        metadata={"updated_fields": sorted(changes.keys())},
    )
    return {"success": True, "data": _serialize_reply_response(row)}


def approve_reply_response(
    db: Session,
    tenant_id: str,
    response_id: str,
    current_user: dict,
    payload: AugmisBusinessStatusActionRequest | None = None,
) -> dict[str, Any]:
    row = _require_reply_response(db, tenant_id, response_id)
    row.status = "approved"
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Approved reply response draft {row.id}",
        resource_type="bd_reply_response_draft",
        resource_id=row.id,
        metadata={"notes": payload.notes if payload else None},
    )
    return {"success": True, "data": _serialize_reply_response(row)}


def reject_reply_response(
    db: Session,
    tenant_id: str,
    response_id: str,
    current_user: dict,
    payload: AugmisBusinessStatusActionRequest | None = None,
) -> dict[str, Any]:
    row = _require_reply_response(db, tenant_id, response_id)
    row.status = "rejected"
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Rejected reply response draft {row.id}",
        resource_type="bd_reply_response_draft",
        resource_id=row.id,
        metadata={"notes": payload.notes if payload else None},
    )
    return {"success": True, "data": _serialize_reply_response(row)}
