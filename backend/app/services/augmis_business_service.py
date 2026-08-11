from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from math import ceil
import re
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import and_, asc, case, desc, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db_models import (
    BusinessDevelopmentActivity,
    BusinessDevelopmentContact,
    BusinessDevelopmentExperienceItem,
    BusinessDevelopmentLead,
    BusinessDevelopmentLeadExperienceMatch,
    BusinessDevelopmentOpportunity,
    BusinessDevelopmentProspect,
    BusinessDevelopmentTask,
    User,
)
from app.models.augmis_business_models import (
    AugmisBusinessActivityCreateRequest,
    AugmisBusinessBuildLeadRequest,
    AugmisBusinessContactCreateRequest,
    AugmisBusinessContactUpdateRequest,
    AugmisBusinessLeadStageUpdateRequest,
    AugmisBusinessLeadUpdateRequest,
    AugmisBusinessOpportunityCreateRequest,
    AugmisBusinessOpportunityUpdateRequest,
    AugmisBusinessProspectCreateRequest,
    AugmisBusinessProspectUpdateRequest,
    AugmisBusinessTaskCompleteRequest,
    AugmisBusinessTaskCreateRequest,
    AugmisBusinessTaskUpdateRequest,
)
from app.services.audit_service import create_audit_log


ACTIVE_OPPORTUNITY_STATUSES = {"new", "under_review", "qualified"}
ALLOWED_OPPORTUNITY_STATUSES = {
    "draft",
    "new",
    "under_review",
    "qualified",
    "converted",
    "dismissed",
    "expired",
}
ALLOWED_PROSPECT_STATUSES = {"active", "inactive", "archived"}
ALLOWED_CONTACT_STATUSES = {"active", "inactive", "archived"}
ALLOWED_LEAD_STAGES = {"new", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"}
ACTIVE_LEAD_STAGES = {"new", "qualified", "proposal", "negotiation"}
ALLOWED_LEAD_STATUSES = {"active", "won", "lost", "archived"}
ALLOWED_TASK_STATUSES = {"open", "in_progress", "completed", "cancelled"}
OPEN_TASK_STATUSES = {"open", "in_progress"}
ALLOWED_PRIORITIES = {"high", "medium", "low"}
LEAD_STAGE_PROBABILITIES = {
    "new": 15.0,
    "qualified": 35.0,
    "proposal": 60.0,
    "negotiation": 80.0,
    "closed_won": 100.0,
    "closed_lost": 0.0,
}
ALLOWED_SORT_FIELDS = {
    "closing_at": BusinessDevelopmentOpportunity.closing_at,
    "published_at": BusinessDevelopmentOpportunity.published_at,
    "created_at": BusinessDevelopmentOpportunity.created_at,
    "fit_score": BusinessDevelopmentOpportunity.fit_score,
    "title": BusinessDevelopmentOpportunity.title,
    "organization_name": BusinessDevelopmentOpportunity.organization_name,
    "opportunity_status": BusinessDevelopmentOpportunity.opportunity_status,
}
ALLOWED_PROSPECT_SORT_FIELDS = {
    "name": BusinessDevelopmentProspect.organization_name,
    "organization_name": BusinessDevelopmentProspect.organization_name,
    "country": BusinessDevelopmentProspect.country,
    "industry": BusinessDevelopmentProspect.industry,
    "potential": BusinessDevelopmentProspect.estimated_account_potential_min,
    "estimated_account_potential_min": BusinessDevelopmentProspect.estimated_account_potential_min,
    "created_at": BusinessDevelopmentProspect.created_at,
    "updated_at": BusinessDevelopmentProspect.updated_at,
    "status": BusinessDevelopmentProspect.prospect_status,
    "prospect_status": BusinessDevelopmentProspect.prospect_status,
}
ALLOWED_LEAD_SORT_FIELDS = {
    "title": BusinessDevelopmentLead.title,
    "stage": BusinessDevelopmentLead.lead_stage,
    "lead_stage": BusinessDevelopmentLead.lead_stage,
    "status": BusinessDevelopmentLead.lead_status,
    "lead_status": BusinessDevelopmentLead.lead_status,
    "priority": BusinessDevelopmentLead.priority,
    "estimated_value": BusinessDevelopmentLead.estimated_value,
    "created_at": BusinessDevelopmentLead.created_at,
    "updated_at": BusinessDevelopmentLead.updated_at,
}
ALLOWED_TASK_SORT_FIELDS = {
    "title": BusinessDevelopmentTask.title,
    "priority": BusinessDevelopmentTask.priority,
    "due_at": BusinessDevelopmentTask.due_at,
    "status": BusinessDevelopmentTask.task_status,
    "task_status": BusinessDevelopmentTask.task_status,
    "assignee": BusinessDevelopmentTask.assigned_user_id,
    "assigned_user_id": BusinessDevelopmentTask.assigned_user_id,
    "created_at": BusinessDevelopmentTask.created_at,
    "updated_at": BusinessDevelopmentTask.updated_at,
}
DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_lookup_text(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    return " ".join(cleaned.split()).lower()


def _normalize_domain_for_match(value: str | None) -> str | None:
    normalized = _normalize_lookup_text(value)
    if normalized is None:
        return None
    if " " in normalized:
        return None
    if not DOMAIN_PATTERN.match(normalized):
        return None
    return normalized


def _normalize_status(value: str) -> str:
    status_value = str(value or "new").strip().lower()
    if status_value not in ALLOWED_OPPORTUNITY_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid opportunity status: {value}",
        )
    return status_value


def _normalize_prospect_status(value: str) -> str:
    status_value = str(value or "active").strip().lower()
    if status_value not in ALLOWED_PROSPECT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid prospect status: {value}",
        )
    return status_value


def _normalize_contact_status(value: str) -> str:
    status_value = str(value or "active").strip().lower()
    if status_value not in ALLOWED_CONTACT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid contact status: {value}",
        )
    return status_value


def _normalize_lead_stage(value: str) -> str:
    stage_value = str(value or "new").strip().lower()
    if stage_value not in ALLOWED_LEAD_STAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid lead stage: {value}",
        )
    return stage_value


def _normalize_lead_status(value: str) -> str:
    status_value = str(value or "active").strip().lower()
    if status_value not in ALLOWED_LEAD_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid lead status: {value}",
        )
    return status_value


def _normalize_task_status(value: str) -> str:
    status_value = str(value or "open").strip().lower()
    if status_value not in ALLOWED_TASK_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task status: {value}",
        )
    return status_value


def _normalize_priority(value: str) -> str:
    priority_value = str(value or "medium").strip().lower()
    if priority_value not in ALLOWED_PRIORITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid priority: {value}",
        )
    return priority_value


def _validate_contact_fields(
    full_name: str | None,
    email: str | None,
    job_title: str | None = None,
    phone: str | None = None,
) -> None:
    if not any(
        [
            _clean_text(full_name),
            _clean_text(job_title),
            _clean_text(email),
            _clean_text(phone),
        ]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of full_name, job_title, email, or phone must be provided",
        )
    if email:
        candidate = email.strip()
        if "@" not in candidate or candidate.startswith("@") or candidate.endswith("@"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contact email must be a valid email address",
            )


def _contact_display_name(row: BusinessDevelopmentContact) -> str:
    return row.full_name or row.job_title or row.email or row.phone or row.id


def _end_of_day(target_date: date) -> datetime:
    return datetime.combine(target_date, time(17, 0), tzinfo=timezone.utc)


def calculate_working_day_due_at(start_at: datetime, priority: str) -> datetime:
    normalized_priority = _normalize_priority(priority)
    working_days = {"high": 2, "medium": 4, "low": 7}[normalized_priority]
    current = start_at.astimezone(timezone.utc).date()
    added = 0
    while added < working_days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return _end_of_day(current)


def _resolve_probability_pct(stage: str, override: float | None = None) -> float:
    if override is not None:
        if override < 0 or override > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Probability must be between 0 and 100",
            )
        return float(override)
    return LEAD_STAGE_PROBABILITIES[stage]


def _estimate_opportunity_value(opportunity: BusinessDevelopmentOpportunity) -> float | None:
    return (
        opportunity.estimated_value_max
        or opportunity.estimated_value_min
        or opportunity.published_budget
    )


def serialize_experience_item(row: BusinessDevelopmentExperienceItem) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "name": row.name,
        "category": row.category,
        "description": row.description,
        "business_problems_json": row.business_problems_json or [],
        "features_json": row.features_json or [],
        "technologies_json": row.technologies_json or [],
        "industries_json": row.industries_json or [],
        "keywords_json": row.keywords_json or [],
        "reusable_capabilities_json": row.reusable_capabilities_json or [],
        "confidentiality_safe_summary": row.confidentiality_safe_summary,
        "status": row.status,
        "created_by": row.created_by,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def serialize_opportunity(row: BusinessDevelopmentOpportunity) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "external_id": row.external_id,
        "source_type": row.source_type,
        "source_name": row.source_name,
        "source_url": row.source_url,
        "title": row.title,
        "organization_name": row.organization_name,
        "organization_domain": row.organization_domain,
        "country": row.country,
        "region": row.region,
        "industry": row.industry,
        "published_at": _serialize_datetime(row.published_at),
        "closing_at": _serialize_datetime(row.closing_at),
        "raw_summary": row.raw_summary,
        "requirement_summary": row.requirement_summary,
        "business_problem": row.business_problem,
        "expected_deliverables_json": row.expected_deliverables_json or [],
        "required_technologies_json": row.required_technologies_json or [],
        "published_budget": row.published_budget,
        "published_currency": row.published_currency,
        "estimated_value_min": row.estimated_value_min,
        "estimated_value_max": row.estimated_value_max,
        "estimated_currency": row.estimated_currency,
        "fit_score": row.fit_score,
        "confidence_score": row.confidence_score,
        "ai_recommendation": row.ai_recommendation,
        "opportunity_status": row.opportunity_status,
        "source_evidence_json": row.source_evidence_json or [],
        "created_by": row.created_by,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def serialize_prospect(row: BusinessDevelopmentProspect) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "organization_name": row.organization_name,
        "organization_domain": row.organization_domain,
        "website_url": row.website_url,
        "country": row.country,
        "region": row.region,
        "city": row.city,
        "industry": row.industry,
        "organization_type": row.organization_type,
        "employee_range": row.employee_range,
        "general_email": row.general_email,
        "general_phone": row.general_phone,
        "prospect_status": row.prospect_status,
        "estimated_account_potential_min": row.estimated_account_potential_min,
        "estimated_account_potential_max": row.estimated_account_potential_max,
        "estimated_currency": row.estimated_currency,
        "notes": row.notes,
        "source_opportunity_id": row.source_opportunity_id,
        "created_by": row.created_by,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def serialize_contact(row: BusinessDevelopmentContact) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "prospect_id": row.prospect_id,
        "full_name": row.full_name,
        "email": row.email,
        "phone": row.phone,
        "job_title": row.job_title,
        "department": row.department,
        "buyer_role": row.buyer_role,
        "linkedin_url": row.linkedin_url,
        "company_profile_url": row.company_profile_url,
        "contact_source": row.contact_source,
        "source_url": row.source_url,
        "evidence_text": row.evidence_text,
        "verification_status": row.verification_status,
        "confidence_score": row.confidence_score,
        "contact_status": row.contact_status,
        "is_primary": row.is_primary,
        "notes": row.notes,
        "created_by": row.created_by,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def serialize_lead_experience_match(row: BusinessDevelopmentLeadExperienceMatch) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "lead_id": row.lead_id,
        "experience_item_id": row.experience_item_id,
        "relevance_score": row.relevance_score,
        "match_notes": row.match_notes,
        "created_by": row.created_by,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def serialize_task(row: BusinessDevelopmentTask) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "lead_id": row.lead_id,
        "opportunity_id": row.opportunity_id,
        "prospect_id": row.prospect_id,
        "assigned_user_id": row.assigned_user_id,
        "title": row.title,
        "description": row.description,
        "task_type": row.task_type,
        "task_status": row.task_status,
        "priority": row.priority,
        "due_at": _serialize_datetime(row.due_at),
        "completed_at": _serialize_datetime(row.completed_at),
        "completed_by": row.completed_by,
        "completion_notes": row.completion_notes,
        "metadata_json": row.metadata_json or {},
        "created_by": row.created_by,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def serialize_assignable_user(row: User) -> dict[str, Any]:
    return {
        "user_id": row.user_id,
        "name": row.name,
        "email": row.email,
        "role": row.role,
        "status": row.status,
    }


def serialize_activity(row: BusinessDevelopmentActivity) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "lead_id": row.lead_id,
        "opportunity_id": row.opportunity_id,
        "prospect_id": row.prospect_id,
        "contact_id": row.contact_id,
        "activity_type": row.activity_type,
        "subject": row.subject,
        "description": row.description,
        "activity_at": _serialize_datetime(row.activity_at),
        "direction": row.direction,
        "outcome": row.outcome,
        "metadata_json": row.metadata_json or {},
        "created_by": row.created_by,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def serialize_lead(
    row: BusinessDevelopmentLead,
    *,
    prospect: BusinessDevelopmentProspect | None = None,
    primary_contact: BusinessDevelopmentContact | None = None,
    opportunity: BusinessDevelopmentOpportunity | None = None,
    experience_matches: list[BusinessDevelopmentLeadExperienceMatch] | None = None,
) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "opportunity_id": row.opportunity_id,
        "prospect_id": row.prospect_id,
        "primary_contact_id": row.primary_contact_id,
        "title": row.title,
        "lead_stage": row.lead_stage,
        "lead_status": row.lead_status,
        "priority": row.priority,
        "source_type": row.source_type,
        "source_name": row.source_name,
        "estimated_value": row.estimated_value,
        "weighted_value": row.weighted_value,
        "probability_pct": row.probability_pct,
        "notes": row.notes,
        "converted_at": _serialize_datetime(row.converted_at),
        "created_by": row.created_by,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
        "prospect": serialize_prospect(prospect) if prospect else None,
        "primary_contact": serialize_contact(primary_contact) if primary_contact else None,
        "opportunity": serialize_opportunity(opportunity) if opportunity else None,
        "experience_matches": [
            serialize_lead_experience_match(item) for item in (experience_matches or [])
        ],
    }


def list_experience_items(
    db: Session,
    tenant_id: str,
    category: str | None = None,
    status_filter: str | None = None,
) -> dict[str, Any]:
    query = db.query(BusinessDevelopmentExperienceItem).filter(
        BusinessDevelopmentExperienceItem.tenant_id == tenant_id
    )

    if category:
        query = query.filter(BusinessDevelopmentExperienceItem.category == category)
    if status_filter:
        query = query.filter(BusinessDevelopmentExperienceItem.status == status_filter)

    rows = (
        query.order_by(
            BusinessDevelopmentExperienceItem.category.asc(),
            BusinessDevelopmentExperienceItem.name.asc(),
        )
        .all()
    )

    return {"success": True, "data": [serialize_experience_item(row) for row in rows]}


def _apply_opportunity_filters(
    query,
    tenant_id: str,
    search: str | None,
    status_filter: str | None,
    source_type: str | None,
    country: str | None,
    region: str | None,
    organization: str | None,
    published_from: datetime | None,
    published_to: datetime | None,
    closing_from: datetime | None,
    closing_to: datetime | None,
):
    query = query.filter(BusinessDevelopmentOpportunity.tenant_id == tenant_id)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                BusinessDevelopmentOpportunity.title.ilike(pattern),
                BusinessDevelopmentOpportunity.organization_name.ilike(pattern),
                BusinessDevelopmentOpportunity.source_name.ilike(pattern),
                BusinessDevelopmentOpportunity.requirement_summary.ilike(pattern),
                BusinessDevelopmentOpportunity.business_problem.ilike(pattern),
            )
        )

    if status_filter:
        query = query.filter(BusinessDevelopmentOpportunity.opportunity_status == status_filter)
    if source_type:
        query = query.filter(BusinessDevelopmentOpportunity.source_type == source_type)
    if country:
        query = query.filter(BusinessDevelopmentOpportunity.country == country)
    if region:
        query = query.filter(BusinessDevelopmentOpportunity.region == region)
    if organization:
        query = query.filter(
            BusinessDevelopmentOpportunity.organization_name.ilike(f"%{organization.strip()}%")
        )
    if published_from:
        query = query.filter(BusinessDevelopmentOpportunity.published_at >= published_from)
    if published_to:
        query = query.filter(BusinessDevelopmentOpportunity.published_at <= published_to)
    if closing_from:
        query = query.filter(BusinessDevelopmentOpportunity.closing_at >= closing_from)
    if closing_to:
        query = query.filter(BusinessDevelopmentOpportunity.closing_at <= closing_to)

    return query


def _apply_opportunity_sorting(query, sort_by: str | None, sort_order: str | None):
    normalized_order = "desc" if str(sort_order or "").lower() == "desc" else "asc"
    normalized_sort_by = str(sort_by or "").lower()

    if normalized_sort_by in ALLOWED_SORT_FIELDS:
        column = ALLOWED_SORT_FIELDS[normalized_sort_by]
        order_fn = desc if normalized_order == "desc" else asc
        return query.order_by(order_fn(column).nullslast(), desc(BusinessDevelopmentOpportunity.created_at))

    active_closing_rank = case(
        (
            and_(
                BusinessDevelopmentOpportunity.closing_at.is_not(None),
                BusinessDevelopmentOpportunity.opportunity_status.in_(ACTIVE_OPPORTUNITY_STATUSES),
            ),
            0,
        ),
        else_=1,
    )
    active_closing_date = case(
        (
            and_(
                BusinessDevelopmentOpportunity.closing_at.is_not(None),
                BusinessDevelopmentOpportunity.opportunity_status.in_(ACTIVE_OPPORTUNITY_STATUSES),
            ),
            BusinessDevelopmentOpportunity.closing_at,
        ),
        else_=None,
    )

    return query.order_by(
        active_closing_rank.asc(),
        active_closing_date.asc().nullslast(),
        BusinessDevelopmentOpportunity.created_at.desc(),
    )


def _apply_prospect_sorting(query, sort_by: str | None, sort_order: str | None):
    normalized_order = "desc" if str(sort_order or "").lower() == "desc" else "asc"
    normalized_sort_by = str(sort_by or "").lower()
    column = ALLOWED_PROSPECT_SORT_FIELDS.get(normalized_sort_by)
    if column is None:
        return query.order_by(
            BusinessDevelopmentProspect.organization_name.asc(),
            BusinessDevelopmentProspect.created_at.desc(),
        )
    order_fn = desc if normalized_order == "desc" else asc
    return query.order_by(order_fn(column).nullslast(), BusinessDevelopmentProspect.created_at.desc())


def _apply_lead_sorting(query, sort_by: str | None, sort_order: str | None):
    normalized_order = "desc" if str(sort_order or "").lower() == "desc" else "asc"
    normalized_sort_by = str(sort_by or "").lower()
    column = ALLOWED_LEAD_SORT_FIELDS.get(normalized_sort_by)
    if column is None:
        return query.order_by(
            BusinessDevelopmentLead.updated_at.desc(),
            BusinessDevelopmentLead.created_at.desc(),
        )
    order_fn = desc if normalized_order == "desc" else asc
    return query.order_by(order_fn(column).nullslast(), BusinessDevelopmentLead.created_at.desc())


def _apply_task_sorting(query, sort_by: str | None, sort_order: str | None):
    normalized_order = "desc" if str(sort_order or "").lower() == "desc" else "asc"
    normalized_sort_by = str(sort_by or "").lower()
    column = ALLOWED_TASK_SORT_FIELDS.get(normalized_sort_by)
    if column is None:
        return query.order_by(
            BusinessDevelopmentTask.due_at.asc().nullslast(),
            BusinessDevelopmentTask.created_at.desc(),
        )
    order_fn = desc if normalized_order == "desc" else asc
    return query.order_by(order_fn(column).nullslast(), BusinessDevelopmentTask.created_at.desc())


def list_opportunities(
    db: Session,
    tenant_id: str,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    status_filter: str | None = None,
    source_type: str | None = None,
    country: str | None = None,
    region: str | None = None,
    organization: str | None = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    closing_from: datetime | None = None,
    closing_to: datetime | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
) -> dict[str, Any]:
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 100)

    base_query = _apply_opportunity_filters(
        db.query(BusinessDevelopmentOpportunity),
        tenant_id=tenant_id,
        search=search,
        status_filter=status_filter,
        source_type=source_type,
        country=country,
        region=region,
        organization=organization,
        published_from=published_from,
        published_to=published_to,
        closing_from=closing_from,
        closing_to=closing_to,
    )

    total = base_query.count()
    total_pages = ceil(total / safe_page_size) if total else 0

    rows = (
        _apply_opportunity_sorting(base_query, sort_by=sort_by, sort_order=sort_order)
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )

    return {
        "success": True,
        "data": [serialize_opportunity(row) for row in rows],
        "pagination": {
            "page": safe_page,
            "page_size": safe_page_size,
            "total": total,
            "total_pages": total_pages,
        },
    }


def _require_opportunity(db: Session, tenant_id: str, opportunity_id: str) -> BusinessDevelopmentOpportunity:
    row = (
        db.query(BusinessDevelopmentOpportunity)
        .filter(
            BusinessDevelopmentOpportunity.id == opportunity_id,
            BusinessDevelopmentOpportunity.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return row


def _require_prospect(db: Session, tenant_id: str, prospect_id: str) -> BusinessDevelopmentProspect:
    row = (
        db.query(BusinessDevelopmentProspect)
        .filter(
            BusinessDevelopmentProspect.id == prospect_id,
            BusinessDevelopmentProspect.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    return row


def _require_contact(db: Session, tenant_id: str, contact_id: str) -> BusinessDevelopmentContact:
    row = (
        db.query(BusinessDevelopmentContact)
        .filter(
            BusinessDevelopmentContact.id == contact_id,
            BusinessDevelopmentContact.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return row


def _require_lead(db: Session, tenant_id: str, lead_id: str) -> BusinessDevelopmentLead:
    row = (
        db.query(BusinessDevelopmentLead)
        .filter(
            BusinessDevelopmentLead.id == lead_id,
            BusinessDevelopmentLead.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return row


def _require_task(db: Session, tenant_id: str, task_id: str) -> BusinessDevelopmentTask:
    row = (
        db.query(BusinessDevelopmentTask)
        .filter(
            BusinessDevelopmentTask.id == task_id,
            BusinessDevelopmentTask.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return row


def _validate_assigned_user_id(
    db: Session,
    tenant_id: str,
    assigned_user_id: str | None,
) -> str | None:
    normalized_user_id = _clean_text(assigned_user_id)
    if normalized_user_id is None:
        return None

    user = (
        db.query(User)
        .filter(
            User.user_id == normalized_user_id,
            User.tenant_id == tenant_id,
        )
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assigned user not found for tenant: {normalized_user_id}",
        )
    return normalized_user_id


def _find_duplicate_prospect(
    db: Session,
    tenant_id: str,
    organization_name: str,
    organization_domain: str | None,
    country: str | None = None,
    exclude_id: str | None = None,
) -> BusinessDevelopmentProspect | None:
    query = db.query(BusinessDevelopmentProspect).filter(
        BusinessDevelopmentProspect.tenant_id == tenant_id
    )
    if exclude_id:
        query = query.filter(BusinessDevelopmentProspect.id != exclude_id)

    normalized_name = _normalize_lookup_text(organization_name)
    normalized_domain = _normalize_domain_for_match(organization_domain)
    normalized_country = _normalize_lookup_text(country)
    candidates = query.all()

    if normalized_domain:
        for candidate in candidates:
            if _normalize_domain_for_match(candidate.organization_domain) == normalized_domain:
                return candidate

    if normalized_name and normalized_country:
        for candidate in candidates:
            if (
                _normalize_lookup_text(candidate.organization_name) == normalized_name
                and _normalize_lookup_text(candidate.country) == normalized_country
            ):
                return candidate
    return None


def _enforce_primary_contact(db: Session, tenant_id: str, prospect_id: str, contact_id: str) -> None:
    (
        db.query(BusinessDevelopmentContact)
        .filter(
            BusinessDevelopmentContact.tenant_id == tenant_id,
            BusinessDevelopmentContact.prospect_id == prospect_id,
            BusinessDevelopmentContact.id != contact_id,
        )
        .update({"is_primary": False}, synchronize_session=False)
    )


def _serialize_lead_with_related(db: Session, tenant_id: str, lead: BusinessDevelopmentLead) -> dict[str, Any]:
    prospect = _require_prospect(db, tenant_id, lead.prospect_id)
    opportunity = _require_opportunity(db, tenant_id, lead.opportunity_id)
    primary_contact = (
        _require_contact(db, tenant_id, lead.primary_contact_id) if lead.primary_contact_id else None
    )
    experience_matches = (
        db.query(BusinessDevelopmentLeadExperienceMatch)
        .filter(
            BusinessDevelopmentLeadExperienceMatch.tenant_id == tenant_id,
            BusinessDevelopmentLeadExperienceMatch.lead_id == lead.id,
        )
        .order_by(BusinessDevelopmentLeadExperienceMatch.created_at.asc())
        .all()
    )
    return serialize_lead(
        lead,
        prospect=prospect,
        primary_contact=primary_contact,
        opportunity=opportunity,
        experience_matches=experience_matches,
    )


def _list_prospect_contacts_rows(
    db: Session, tenant_id: str, prospect_id: str
) -> list[BusinessDevelopmentContact]:
    return (
        db.query(BusinessDevelopmentContact)
        .filter(
            BusinessDevelopmentContact.tenant_id == tenant_id,
            BusinessDevelopmentContact.prospect_id == prospect_id,
        )
        .order_by(
            BusinessDevelopmentContact.is_primary.desc(),
            BusinessDevelopmentContact.full_name.asc().nullslast(),
            BusinessDevelopmentContact.job_title.asc().nullslast(),
        )
        .all()
    )


def _create_activity_row(
    *,
    tenant_id: str,
    current_user: dict,
    activity_type: str,
    subject: str,
    description: str | None,
    lead_id: str | None = None,
    opportunity_id: str | None = None,
    prospect_id: str | None = None,
    contact_id: str | None = None,
    activity_at: datetime | None = None,
    direction: str | None = None,
    outcome: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> BusinessDevelopmentActivity:
    return BusinessDevelopmentActivity(
        id=f"BD-ACT-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        lead_id=lead_id,
        opportunity_id=opportunity_id,
        prospect_id=prospect_id,
        contact_id=contact_id,
        activity_type=activity_type.strip().lower(),
        subject=subject.strip(),
        description=_clean_text(description),
        activity_at=activity_at or _now(),
        direction=_clean_text(direction),
        outcome=_clean_text(outcome),
        metadata_json=metadata_json or {},
        created_by=current_user["user_id"],
        updated_at=_now(),
    )


def create_opportunity(
    db: Session,
    tenant_id: str,
    current_user: dict,
    payload: AugmisBusinessOpportunityCreateRequest,
    *,
    commit: bool = True,
) -> dict[str, Any]:
    row = BusinessDevelopmentOpportunity(
        id=f"BD-OPP-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        external_id=payload.external_id,
        source_type=payload.source_type.strip(),
        source_name=payload.source_name.strip(),
        source_url=payload.source_url,
        title=payload.title.strip(),
        organization_name=payload.organization_name.strip(),
        organization_domain=payload.organization_domain,
        country=payload.country,
        region=payload.region,
        industry=payload.industry,
        published_at=payload.published_at,
        closing_at=payload.closing_at,
        raw_summary=payload.raw_summary,
        requirement_summary=payload.requirement_summary.strip(),
        business_problem=payload.business_problem,
        expected_deliverables_json=payload.expected_deliverables_json,
        required_technologies_json=payload.required_technologies_json,
        published_budget=payload.published_budget,
        published_currency=payload.published_currency,
        estimated_value_min=payload.estimated_value_min,
        estimated_value_max=payload.estimated_value_max,
        estimated_currency=payload.estimated_currency,
        fit_score=payload.fit_score,
        confidence_score=payload.confidence_score,
        ai_recommendation=payload.ai_recommendation,
        opportunity_status=_normalize_status(payload.opportunity_status),
        source_evidence_json=payload.source_evidence_json,
        created_by=current_user["user_id"],
        updated_at=_now(),
    )

    try:
        db.add(row)
        if commit:
            db.commit()
            db.refresh(row)
        else:
            db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Opportunity conflicts with an existing tenant record",
        )

    if commit:
        create_audit_log(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user["user_id"],
            event_type="CREATE",
            event_category="AUGMIS_BUSINESS",
            description=f"Created opportunity {row.title}",
            resource_type="bd_opportunity",
            resource_id=row.id,
            metadata={"source_type": row.source_type, "status": row.opportunity_status},
        )

    return {"success": True, "data": serialize_opportunity(row)}


def get_opportunity(db: Session, tenant_id: str, opportunity_id: str) -> dict[str, Any]:
    row = _require_opportunity(db, tenant_id, opportunity_id)
    return {"success": True, "data": serialize_opportunity(row)}


def update_opportunity(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
    current_user: dict,
    payload: AugmisBusinessOpportunityUpdateRequest,
) -> dict[str, Any]:
    row = _require_opportunity(db, tenant_id, opportunity_id)
    changes = payload.model_dump(exclude_unset=True)

    if "opportunity_status" in changes:
        changes["opportunity_status"] = _normalize_status(str(changes["opportunity_status"]))

    for key, value in changes.items():
        setattr(row, key, value)

    row.updated_at = _now()

    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Opportunity conflicts with an existing tenant record",
        )

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated opportunity {row.title}",
        resource_type="bd_opportunity",
        resource_id=row.id,
        metadata={"updated_fields": sorted(changes.keys())},
    )

    return {"success": True, "data": serialize_opportunity(row)}


def delete_opportunity(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
    current_user: dict,
) -> dict[str, Any]:
    row = _require_opportunity(db, tenant_id, opportunity_id)
    lead_count = (
        db.query(func.count(BusinessDevelopmentLead.id))
        .filter(
            BusinessDevelopmentLead.tenant_id == tenant_id,
            BusinessDevelopmentLead.opportunity_id == opportunity_id,
        )
        .scalar()
        or 0
    )
    if lead_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete an opportunity that has converted leads",
        )

    deleted_snapshot = {"id": row.id, "title": row.title, "source_type": row.source_type}
    db.delete(row)
    db.commit()

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="DELETE",
        event_category="AUGMIS_BUSINESS",
        description=f"Deleted opportunity {deleted_snapshot['title']}",
        resource_type="bd_opportunity",
        resource_id=deleted_snapshot["id"],
        metadata={"source_type": deleted_snapshot["source_type"]},
    )

    return {"success": True, "deleted": 1, "data": deleted_snapshot}


def list_prospects(
    db: Session,
    tenant_id: str,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    status_filter: str | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
) -> dict[str, Any]:
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 100)
    query = db.query(BusinessDevelopmentProspect).filter(
        BusinessDevelopmentProspect.tenant_id == tenant_id
    )

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                BusinessDevelopmentProspect.organization_name.ilike(pattern),
                BusinessDevelopmentProspect.organization_domain.ilike(pattern),
                BusinessDevelopmentProspect.industry.ilike(pattern),
            )
        )
    if status_filter:
        query = query.filter(
            BusinessDevelopmentProspect.prospect_status == _normalize_prospect_status(status_filter)
        )

    total = query.count()
    total_pages = ceil(total / safe_page_size) if total else 0
    rows = (
        _apply_prospect_sorting(query, sort_by=sort_by, sort_order=sort_order)
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return {
        "success": True,
        "data": [serialize_prospect(row) for row in rows],
        "pagination": {
            "page": safe_page,
            "page_size": safe_page_size,
            "total": total,
            "total_pages": total_pages,
        },
    }


def create_prospect(
    db: Session,
    tenant_id: str,
    current_user: dict,
    payload: AugmisBusinessProspectCreateRequest,
) -> dict[str, Any]:
    duplicate = _find_duplicate_prospect(
        db,
        tenant_id,
        payload.organization_name,
        payload.organization_domain,
        payload.country,
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A matching prospect already exists for this tenant",
        )

    if payload.source_opportunity_id:
        _require_opportunity(db, tenant_id, payload.source_opportunity_id)

    row = BusinessDevelopmentProspect(
        id=f"BD-PRS-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        organization_name=payload.organization_name.strip(),
        organization_domain=_clean_text(payload.organization_domain),
        website_url=_clean_text(payload.website_url),
        country=_clean_text(payload.country),
        region=_clean_text(payload.region),
        city=_clean_text(payload.city),
        industry=_clean_text(payload.industry),
        organization_type=_clean_text(payload.organization_type),
        employee_range=_clean_text(payload.employee_range),
        general_email=_clean_text(payload.general_email),
        general_phone=_clean_text(payload.general_phone),
        prospect_status=_normalize_prospect_status(payload.prospect_status),
        estimated_account_potential_min=payload.estimated_account_potential_min,
        estimated_account_potential_max=payload.estimated_account_potential_max,
        estimated_currency=_clean_text(payload.estimated_currency),
        notes=_clean_text(payload.notes),
        source_opportunity_id=payload.source_opportunity_id,
        created_by=current_user["user_id"],
        updated_at=_now(),
    )

    try:
        db.add(row)
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Prospect conflicts with an existing tenant record",
        )

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="CREATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Created prospect {row.organization_name}",
        resource_type="bd_prospect",
        resource_id=row.id,
        metadata={"status": row.prospect_status},
    )

    return {"success": True, "data": serialize_prospect(row)}


def get_prospect(db: Session, tenant_id: str, prospect_id: str) -> dict[str, Any]:
    row = _require_prospect(db, tenant_id, prospect_id)
    contacts = _list_prospect_contacts_rows(db, tenant_id, prospect_id)
    data = serialize_prospect(row)
    data["contacts"] = [serialize_contact(contact) for contact in contacts]
    return {"success": True, "data": data}


def update_prospect(
    db: Session,
    tenant_id: str,
    prospect_id: str,
    current_user: dict,
    payload: AugmisBusinessProspectUpdateRequest,
) -> dict[str, Any]:
    row = _require_prospect(db, tenant_id, prospect_id)
    changes = payload.model_dump(exclude_unset=True)

    next_name = changes.get("organization_name", row.organization_name)
    next_domain = changes.get("organization_domain", row.organization_domain)
    duplicate = _find_duplicate_prospect(
        db,
        tenant_id,
        next_name,
        next_domain,
        changes.get("country", row.country),
        exclude_id=prospect_id,
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A matching prospect already exists for this tenant",
        )

    if "prospect_status" in changes:
        changes["prospect_status"] = _normalize_prospect_status(str(changes["prospect_status"]))

    for key, value in changes.items():
        setattr(row, key, _clean_text(value) if isinstance(value, str) or value is None else value)

    row.updated_at = _now()

    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Prospect conflicts with an existing tenant record",
        )

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated prospect {row.organization_name}",
        resource_type="bd_prospect",
        resource_id=row.id,
        metadata={"updated_fields": sorted(changes.keys())},
    )

    return {"success": True, "data": serialize_prospect(row)}


def create_contact(
    db: Session,
    tenant_id: str,
    prospect_id: str,
    current_user: dict,
    payload: AugmisBusinessContactCreateRequest,
) -> dict[str, Any]:
    _require_prospect(db, tenant_id, prospect_id)
    _validate_contact_fields(payload.full_name, payload.email, payload.job_title, payload.phone)

    row = BusinessDevelopmentContact(
        id=f"BD-CON-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        prospect_id=prospect_id,
        full_name=_clean_text(payload.full_name),
        email=_clean_text(payload.email),
        phone=_clean_text(payload.phone),
        job_title=_clean_text(payload.job_title),
        department=_clean_text(payload.department),
        buyer_role=_clean_text(payload.buyer_role),
        linkedin_url=_clean_text(payload.linkedin_url),
        company_profile_url=_clean_text(payload.company_profile_url),
        contact_source=_clean_text(payload.contact_source),
        source_url=_clean_text(payload.source_url),
        evidence_text=_clean_text(payload.evidence_text),
        verification_status=_clean_text(payload.verification_status) or "unverified",
        confidence_score=payload.confidence_score,
        contact_status=_normalize_contact_status(payload.contact_status),
        is_primary=bool(payload.is_primary),
        notes=_clean_text(payload.notes),
        created_by=current_user["user_id"],
        updated_at=_now(),
    )

    try:
        db.add(row)
        db.flush()
        if row.is_primary:
            _enforce_primary_contact(db, tenant_id, prospect_id, row.id)
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contact conflicts with an existing tenant record",
        )

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="CREATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Created contact {_contact_display_name(row)}",
        resource_type="bd_contact",
        resource_id=row.id,
        metadata={"prospect_id": prospect_id},
    )

    return {"success": True, "data": serialize_contact(row)}


def update_contact(
    db: Session,
    tenant_id: str,
    contact_id: str,
    current_user: dict,
    payload: AugmisBusinessContactUpdateRequest,
) -> dict[str, Any]:
    row = _require_contact(db, tenant_id, contact_id)
    changes = payload.model_dump(exclude_unset=True)
    full_name = changes.get("full_name", row.full_name)
    email = changes.get("email", row.email)
    job_title = changes.get("job_title", row.job_title)
    phone = changes.get("phone", row.phone)
    _validate_contact_fields(full_name, email, job_title, phone)

    if "contact_status" in changes:
        changes["contact_status"] = _normalize_contact_status(str(changes["contact_status"]))

    for key, value in changes.items():
        setattr(row, key, _clean_text(value) if isinstance(value, str) or value is None else value)

    row.updated_at = _now()

    try:
        db.flush()
        if row.is_primary:
            _enforce_primary_contact(db, tenant_id, row.prospect_id, row.id)
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contact conflicts with an existing tenant record",
        )

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated contact {_contact_display_name(row)}",
        resource_type="bd_contact",
        resource_id=row.id,
        metadata={"updated_fields": sorted(changes.keys())},
    )

    return {"success": True, "data": serialize_contact(row)}


def delete_contact(
    db: Session,
    tenant_id: str,
    contact_id: str,
    current_user: dict,
) -> dict[str, Any]:
    row = _require_contact(db, tenant_id, contact_id)
    linked_lead = (
        db.query(BusinessDevelopmentLead.id)
        .filter(
            BusinessDevelopmentLead.tenant_id == tenant_id,
            BusinessDevelopmentLead.primary_contact_id == contact_id,
        )
        .first()
    )
    linked_activity = (
        db.query(BusinessDevelopmentActivity.id)
        .filter(
            BusinessDevelopmentActivity.tenant_id == tenant_id,
            BusinessDevelopmentActivity.contact_id == contact_id,
        )
        .first()
    )
    if linked_lead or linked_activity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Contact cannot be deleted because it is referenced by active business "
                "records. Reassign any lead primary contact first."
            ),
        )

    snapshot = {
        "id": row.id,
        "prospect_id": row.prospect_id,
        "full_name": row.full_name,
        "job_title": row.job_title,
    }
    db.delete(row)
    db.commit()

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="DELETE",
        event_category="AUGMIS_BUSINESS",
        description=f"Deleted contact {snapshot['full_name'] or snapshot['job_title'] or snapshot['id']}",
        resource_type="bd_contact",
        resource_id=snapshot["id"],
        metadata={"prospect_id": snapshot["prospect_id"]},
    )

    return {"success": True, "deleted": 1, "data": snapshot}


def list_prospect_contacts(db: Session, tenant_id: str, prospect_id: str) -> dict[str, Any]:
    _require_prospect(db, tenant_id, prospect_id)
    rows = _list_prospect_contacts_rows(db, tenant_id, prospect_id)
    return {"success": True, "data": [serialize_contact(row) for row in rows]}


def _serialize_prospect_related_opportunity(
    row: BusinessDevelopmentOpportunity,
) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "organization_name": row.organization_name,
        "source_type": row.source_type,
        "source_name": row.source_name,
        "country": row.country,
        "region": row.region,
        "industry": row.industry,
        "opportunity_status": row.opportunity_status,
        "estimated_value_min": row.estimated_value_min,
        "estimated_value_max": row.estimated_value_max,
        "estimated_currency": row.estimated_currency,
        "closing_at": _serialize_datetime(row.closing_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def list_prospect_opportunities(db: Session, tenant_id: str, prospect_id: str) -> dict[str, Any]:
    prospect = _require_prospect(db, tenant_id, prospect_id)
    opportunity_map: dict[str, BusinessDevelopmentOpportunity] = {}

    if prospect.source_opportunity_id:
        direct_opportunity = (
            db.query(BusinessDevelopmentOpportunity)
            .filter(
                BusinessDevelopmentOpportunity.tenant_id == tenant_id,
                BusinessDevelopmentOpportunity.id == prospect.source_opportunity_id,
            )
            .first()
        )
        if direct_opportunity:
            opportunity_map[direct_opportunity.id] = direct_opportunity

    lead_rows = (
        db.query(BusinessDevelopmentLead.opportunity_id, BusinessDevelopmentOpportunity)
        .join(
            BusinessDevelopmentOpportunity,
            and_(
                BusinessDevelopmentOpportunity.id == BusinessDevelopmentLead.opportunity_id,
                BusinessDevelopmentOpportunity.tenant_id == BusinessDevelopmentLead.tenant_id,
            ),
        )
        .filter(
            BusinessDevelopmentLead.tenant_id == tenant_id,
            BusinessDevelopmentLead.prospect_id == prospect_id,
        )
        .all()
    )
    for _, opportunity in lead_rows:
        opportunity_map[opportunity.id] = opportunity

    rows = sorted(
        opportunity_map.values(),
        key=lambda row: row.updated_at or row.created_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return {"success": True, "data": [_serialize_prospect_related_opportunity(row) for row in rows]}


def _serialize_prospect_related_lead(
    row: BusinessDevelopmentLead,
    opportunity: BusinessDevelopmentOpportunity | None,
    next_task: BusinessDevelopmentTask | None,
) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "lead_stage": row.lead_stage,
        "lead_status": row.lead_status,
        "priority": row.priority,
        "opportunity_id": row.opportunity_id,
        "opportunity_title": opportunity.title if opportunity else None,
        "estimated_value": row.estimated_value,
        "estimated_currency": opportunity.estimated_currency if opportunity else None,
        "probability_pct": row.probability_pct,
        "next_action": next_task.title if next_task else None,
        "next_action_due_at": _serialize_datetime(next_task.due_at) if next_task else None,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def list_prospect_leads(db: Session, tenant_id: str, prospect_id: str) -> dict[str, Any]:
    _require_prospect(db, tenant_id, prospect_id)
    rows = (
        db.query(BusinessDevelopmentLead)
        .filter(
            BusinessDevelopmentLead.tenant_id == tenant_id,
            BusinessDevelopmentLead.prospect_id == prospect_id,
        )
        .order_by(BusinessDevelopmentLead.updated_at.desc(), BusinessDevelopmentLead.created_at.desc())
        .all()
    )
    lead_data = []
    for row in rows:
        opportunity = (
            db.query(BusinessDevelopmentOpportunity)
            .filter(
                BusinessDevelopmentOpportunity.tenant_id == tenant_id,
                BusinessDevelopmentOpportunity.id == row.opportunity_id,
            )
            .first()
        )
        next_task = (
            db.query(BusinessDevelopmentTask)
            .filter(
                BusinessDevelopmentTask.tenant_id == tenant_id,
                BusinessDevelopmentTask.lead_id == row.id,
                BusinessDevelopmentTask.task_status.in_(OPEN_TASK_STATUSES),
            )
            .order_by(
                case((BusinessDevelopmentTask.due_at.is_(None), 1), else_=0),
                BusinessDevelopmentTask.due_at.asc(),
                BusinessDevelopmentTask.created_at.asc(),
            )
            .first()
        )
        lead_data.append(_serialize_prospect_related_lead(row, opportunity, next_task))
    return {"success": True, "data": lead_data}


def list_prospect_activities(db: Session, tenant_id: str, prospect_id: str) -> dict[str, Any]:
    _require_prospect(db, tenant_id, prospect_id)
    rows = (
        db.query(BusinessDevelopmentActivity)
        .filter(
            BusinessDevelopmentActivity.tenant_id == tenant_id,
            BusinessDevelopmentActivity.prospect_id == prospect_id,
        )
        .order_by(BusinessDevelopmentActivity.created_at.desc())
        .all()
    )
    return {
        "success": True,
        "data": [
            {
                "id": row.id,
                "activity_type": row.activity_type,
                "activity_summary": row.subject,
                "activity_details_json": {
                    "description": row.description,
                    "direction": row.direction,
                    "outcome": row.outcome,
                    "metadata_json": row.metadata_json or {},
                },
                "performed_by": row.created_by,
                "created_at": _serialize_datetime(row.created_at),
            }
            for row in rows
        ],
    }


def list_leads(
    db: Session,
    tenant_id: str,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    stage: str | None = None,
    status_filter: str | None = None,
    prospect_id: str | None = None,
    opportunity_id: str | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
) -> dict[str, Any]:
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 100)

    query = db.query(BusinessDevelopmentLead).filter(BusinessDevelopmentLead.tenant_id == tenant_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(BusinessDevelopmentLead.title.ilike(pattern))
    if stage:
        query = query.filter(BusinessDevelopmentLead.lead_stage == _normalize_lead_stage(stage))
    if status_filter:
        query = query.filter(BusinessDevelopmentLead.lead_status == _normalize_lead_status(status_filter))
    if prospect_id:
        query = query.filter(BusinessDevelopmentLead.prospect_id == prospect_id)
    if opportunity_id:
        query = query.filter(BusinessDevelopmentLead.opportunity_id == opportunity_id)

    total = query.count()
    total_pages = ceil(total / safe_page_size) if total else 0
    rows = (
        _apply_lead_sorting(query, sort_by=sort_by, sort_order=sort_order)
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return {
        "success": True,
        "data": [_serialize_lead_with_related(db, tenant_id, row) for row in rows],
        "pagination": {
            "page": safe_page,
            "page_size": safe_page_size,
            "total": total,
            "total_pages": total_pages,
        },
    }


def get_lead(db: Session, tenant_id: str, lead_id: str) -> dict[str, Any]:
    row = _require_lead(db, tenant_id, lead_id)
    return {"success": True, "data": _serialize_lead_with_related(db, tenant_id, row)}


def update_lead(
    db: Session,
    tenant_id: str,
    lead_id: str,
    current_user: dict,
    payload: AugmisBusinessLeadUpdateRequest,
) -> dict[str, Any]:
    row = _require_lead(db, tenant_id, lead_id)
    changes = payload.model_dump(exclude_unset=True)

    if "priority" in changes:
        changes["priority"] = _normalize_priority(str(changes["priority"]))
    if "lead_status" in changes:
        changes["lead_status"] = _normalize_lead_status(str(changes["lead_status"]))
    if "probability_pct" in changes:
        changes["probability_pct"] = _resolve_probability_pct(row.lead_stage, changes["probability_pct"])
    if "primary_contact_id" in changes and changes["primary_contact_id"]:
        contact = _require_contact(db, tenant_id, changes["primary_contact_id"])
        if contact.prospect_id != row.prospect_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Primary contact must belong to the same prospect as the lead",
            )

    for key, value in changes.items():
        setattr(row, key, _clean_text(value) if isinstance(value, str) or value is None else value)

    if "estimated_value" in changes or "probability_pct" in changes:
        row.weighted_value = (
            (row.estimated_value or 0) * ((row.probability_pct or 0) / 100.0)
            if row.estimated_value is not None and row.probability_pct is not None
            else None
        )
    row.updated_at = _now()

    db.commit()
    db.refresh(row)

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated lead {row.title}",
        resource_type="bd_lead",
        resource_id=row.id,
        metadata={"updated_fields": sorted(changes.keys())},
    )

    return {"success": True, "data": _serialize_lead_with_related(db, tenant_id, row)}


def update_lead_stage(
    db: Session,
    tenant_id: str,
    lead_id: str,
    current_user: dict,
    payload: AugmisBusinessLeadStageUpdateRequest,
) -> dict[str, Any]:
    row = _require_lead(db, tenant_id, lead_id)
    row.lead_stage = _normalize_lead_stage(payload.lead_stage)
    if row.lead_stage == "closed_won":
        row.lead_status = "won"
    elif row.lead_stage == "closed_lost":
        row.lead_status = "lost"
    elif row.lead_status in {"won", "lost"}:
        row.lead_status = "active"
    row.probability_pct = _resolve_probability_pct(row.lead_stage)
    row.weighted_value = (
        (row.estimated_value or 0) * ((row.probability_pct or 0) / 100.0)
        if row.estimated_value is not None
        else None
    )
    row.updated_at = _now()
    db.commit()
    db.refresh(row)

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated lead stage for {row.title}",
        resource_type="bd_lead",
        resource_id=row.id,
        metadata={"lead_stage": row.lead_stage, "lead_status": row.lead_status},
    )

    return {"success": True, "data": _serialize_lead_with_related(db, tenant_id, row)}


def list_lead_activities(db: Session, tenant_id: str, lead_id: str) -> dict[str, Any]:
    _require_lead(db, tenant_id, lead_id)
    rows = (
        db.query(BusinessDevelopmentActivity)
        .filter(
            BusinessDevelopmentActivity.tenant_id == tenant_id,
            BusinessDevelopmentActivity.lead_id == lead_id,
        )
        .order_by(BusinessDevelopmentActivity.activity_at.desc(), BusinessDevelopmentActivity.created_at.desc())
        .all()
    )
    return {"success": True, "data": [serialize_activity(row) for row in rows]}


def create_lead_activity(
    db: Session,
    tenant_id: str,
    lead_id: str,
    current_user: dict,
    payload: AugmisBusinessActivityCreateRequest,
) -> dict[str, Any]:
    lead = _require_lead(db, tenant_id, lead_id)
    contact_id = payload.contact_id
    if contact_id:
        contact = _require_contact(db, tenant_id, contact_id)
        if contact.prospect_id != lead.prospect_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Activity contact must belong to the same prospect as the lead",
            )

    row = _create_activity_row(
        tenant_id=tenant_id,
        current_user=current_user,
        activity_type=payload.activity_type,
        subject=payload.subject,
        description=payload.description,
        lead_id=lead.id,
        opportunity_id=lead.opportunity_id,
        prospect_id=lead.prospect_id,
        contact_id=contact_id,
        activity_at=payload.activity_at,
        direction=payload.direction,
        outcome=payload.outcome,
        metadata_json=payload.metadata_json,
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
        description=f"Created activity {row.subject}",
        resource_type="bd_activity",
        resource_id=row.id,
        metadata={"lead_id": lead.id, "activity_type": row.activity_type},
    )

    return {"success": True, "data": serialize_activity(row)}


def list_lead_tasks(db: Session, tenant_id: str, lead_id: str) -> dict[str, Any]:
    _require_lead(db, tenant_id, lead_id)
    rows = (
        db.query(BusinessDevelopmentTask)
        .filter(
            BusinessDevelopmentTask.tenant_id == tenant_id,
            BusinessDevelopmentTask.lead_id == lead_id,
        )
        .order_by(BusinessDevelopmentTask.due_at.asc().nullslast(), BusinessDevelopmentTask.created_at.desc())
        .all()
    )
    return {"success": True, "data": [serialize_task(row) for row in rows]}


def list_tasks(
    db: Session,
    tenant_id: str,
    page: int = 1,
    page_size: int = 25,
    status_filter: str | None = None,
    priority: str | None = None,
    lead_id: str | None = None,
    assigned_user_id: str | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
) -> dict[str, Any]:
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 100)
    query = db.query(BusinessDevelopmentTask).filter(BusinessDevelopmentTask.tenant_id == tenant_id)
    if status_filter:
        query = query.filter(BusinessDevelopmentTask.task_status == _normalize_task_status(status_filter))
    if priority:
        query = query.filter(BusinessDevelopmentTask.priority == _normalize_priority(priority))
    if lead_id:
        query = query.filter(BusinessDevelopmentTask.lead_id == lead_id)
    if assigned_user_id:
        query = query.filter(BusinessDevelopmentTask.assigned_user_id == assigned_user_id)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                BusinessDevelopmentTask.title.ilike(pattern),
                BusinessDevelopmentTask.description.ilike(pattern),
            )
        )

    total = query.count()
    total_pages = ceil(total / safe_page_size) if total else 0
    rows = (
        _apply_task_sorting(query, sort_by=sort_by, sort_order=sort_order)
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return {
        "success": True,
        "data": [serialize_task(row) for row in rows],
        "pagination": {
            "page": safe_page,
            "page_size": safe_page_size,
            "total": total,
            "total_pages": total_pages,
        },
    }


def list_assignable_users(
    db: Session,
    tenant_id: str,
    *,
    search: str | None = None,
    user_ids: list[str] | None = None,
    include_inactive: bool = False,
    limit: int = 25,
) -> dict[str, Any]:
    safe_limit = min(max(limit, 1), 100)
    query = db.query(User).filter(User.tenant_id == tenant_id)

    if not include_inactive:
        query = query.filter(User.status == "ACTIVE")

    normalized_user_ids = sorted(
        {
            candidate
            for candidate in (_clean_text(item) for item in (user_ids or []))
            if candidate is not None
        }
    )
    if normalized_user_ids:
        query = query.filter(User.user_id.in_(normalized_user_ids))

    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.name.ilike(pattern),
                User.email.ilike(pattern),
                User.user_id.ilike(pattern),
            )
        )

    rows = (
        query.order_by(
            case((User.status == "ACTIVE", 0), else_=1),
            asc(User.name),
            asc(User.email),
            asc(User.user_id),
        )
        .limit(safe_limit)
        .all()
    )
    return {
        "success": True,
        "data": [serialize_assignable_user(row) for row in rows],
    }


def create_task(
    db: Session,
    tenant_id: str,
    current_user: dict,
    payload: AugmisBusinessTaskCreateRequest,
) -> dict[str, Any]:
    lead = _require_lead(db, tenant_id, payload.lead_id)
    if payload.opportunity_id and payload.opportunity_id != lead.opportunity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task opportunity must match the referenced lead",
        )
    if payload.prospect_id and payload.prospect_id != lead.prospect_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task prospect must match the referenced lead",
        )

    normalized_priority = _normalize_priority(payload.priority)
    assigned_user_id = _validate_assigned_user_id(db, tenant_id, payload.assigned_user_id)
    due_at = payload.due_at or calculate_working_day_due_at(_now(), normalized_priority)
    row = BusinessDevelopmentTask(
        id=f"BD-TSK-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        lead_id=lead.id,
        opportunity_id=lead.opportunity_id,
        prospect_id=lead.prospect_id,
        assigned_user_id=assigned_user_id,
        title=payload.title.strip(),
        description=_clean_text(payload.description),
        task_type=payload.task_type.strip().lower(),
        task_status="open",
        priority=normalized_priority,
        due_at=due_at,
        metadata_json=payload.metadata_json,
        created_by=current_user["user_id"],
        updated_at=_now(),
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
        description=f"Created task {row.title}",
        resource_type="bd_task",
        resource_id=row.id,
        metadata={"lead_id": row.lead_id, "priority": row.priority},
    )

    return {"success": True, "data": serialize_task(row)}


def update_task(
    db: Session,
    tenant_id: str,
    task_id: str,
    current_user: dict,
    payload: AugmisBusinessTaskUpdateRequest,
) -> dict[str, Any]:
    row = _require_task(db, tenant_id, task_id)
    changes = payload.model_dump(exclude_unset=True)

    if "priority" in changes:
        changes["priority"] = _normalize_priority(str(changes["priority"]))
    if "task_status" in changes:
        changes["task_status"] = _normalize_task_status(str(changes["task_status"]))
    if "assigned_user_id" in changes:
        changes["assigned_user_id"] = _validate_assigned_user_id(
            db,
            tenant_id,
            changes["assigned_user_id"],
        )

    for key, value in changes.items():
        setattr(row, key, _clean_text(value) if isinstance(value, str) or value is None else value)

    row.updated_at = _now()
    db.commit()
    db.refresh(row)

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated task {row.title}",
        resource_type="bd_task",
        resource_id=row.id,
        metadata={"updated_fields": sorted(changes.keys())},
    )

    return {"success": True, "data": serialize_task(row)}


def complete_task(
    db: Session,
    tenant_id: str,
    task_id: str,
    current_user: dict,
    payload: AugmisBusinessTaskCompleteRequest,
) -> dict[str, Any]:
    row = _require_task(db, tenant_id, task_id)
    row.task_status = "completed"
    row.completed_at = _now()
    row.completed_by = current_user["user_id"]
    row.completion_notes = _clean_text(payload.completion_notes)
    row.updated_at = row.completed_at
    db.commit()
    db.refresh(row)

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Completed task {row.title}",
        resource_type="bd_task",
        resource_id=row.id,
        metadata={"completed_by": row.completed_by},
    )

    return {"success": True, "data": serialize_task(row)}


def build_lead(
    db: Session,
    tenant_id: str,
    opportunity_id: str,
    current_user: dict,
    payload: AugmisBusinessBuildLeadRequest,
) -> dict[str, Any]:
    opportunity = _require_opportunity(db, tenant_id, opportunity_id)
    active_lead = (
        db.query(BusinessDevelopmentLead)
        .filter(
            BusinessDevelopmentLead.tenant_id == tenant_id,
            BusinessDevelopmentLead.opportunity_id == opportunity_id,
            BusinessDevelopmentLead.lead_stage.in_(ACTIVE_LEAD_STAGES),
            BusinessDevelopmentLead.lead_status == "active",
        )
        .first()
    )
    if active_lead:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This opportunity already has an active converted lead",
        )

    if opportunity.opportunity_status == "converted":
        historical_lead = (
            db.query(BusinessDevelopmentLead.id)
            .filter(
                BusinessDevelopmentLead.tenant_id == tenant_id,
                BusinessDevelopmentLead.opportunity_id == opportunity_id,
            )
            .first()
        )
        if historical_lead:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This opportunity has already been converted into a lead",
            )

    normalized_lead_stage = _normalize_lead_stage(payload.lead_stage)
    normalized_lead_priority = _normalize_priority(payload.lead_priority)
    normalized_task_priority = _normalize_priority(payload.first_task_priority)
    assigned_user_id = _validate_assigned_user_id(db, tenant_id, payload.assigned_user_id)
    prospect = _find_duplicate_prospect(
        db,
        tenant_id,
        opportunity.organization_name,
        opportunity.organization_domain,
        opportunity.country,
    )
    prospect_created = False
    contact_created = False

    if not prospect:
        prospect = BusinessDevelopmentProspect(
            id=f"BD-PRS-{str(uuid4())[:12].upper()}",
            tenant_id=tenant_id,
            organization_name=opportunity.organization_name,
            organization_domain=_clean_text(opportunity.organization_domain),
            website_url=_clean_text(opportunity.source_url),
            country=_clean_text(opportunity.country),
            region=_clean_text(opportunity.region),
            city=None,
            industry=_clean_text(opportunity.industry),
            organization_type=None,
            employee_range=None,
            general_email=None,
            general_phone=None,
            prospect_status="active",
            estimated_account_potential_min=None,
            estimated_account_potential_max=None,
            estimated_currency=None,
            notes=_clean_text(opportunity.requirement_summary),
            source_opportunity_id=opportunity.id,
            created_by=current_user["user_id"],
            updated_at=_now(),
        )
        db.add(prospect)
        db.flush()
        prospect_created = True

    if payload.contact_id:
        contact = _require_contact(db, tenant_id, payload.contact_id)
        if contact.prospect_id != prospect.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected contact must belong to the converted prospect",
            )
    else:
        _validate_contact_fields(
            payload.contact_name,
            payload.contact_email,
            payload.contact_job_title,
            payload.contact_phone,
        )
        existing_contact_query = db.query(BusinessDevelopmentContact).filter(
            BusinessDevelopmentContact.tenant_id == tenant_id,
            BusinessDevelopmentContact.prospect_id == prospect.id,
        )
        normalized_email = _clean_text(payload.contact_email)
        contact = None
        if normalized_email:
            contact = (
                existing_contact_query.filter(
                    func.lower(BusinessDevelopmentContact.email) == normalized_email.lower()
                )
                .first()
            )
        if not contact:
            contact = BusinessDevelopmentContact(
                id=f"BD-CON-{str(uuid4())[:12].upper()}",
                tenant_id=tenant_id,
                prospect_id=prospect.id,
                full_name=_clean_text(payload.contact_name),
                email=normalized_email,
                phone=_clean_text(payload.contact_phone),
                job_title=_clean_text(payload.contact_job_title),
                department=None,
                buyer_role=None,
                linkedin_url=None,
                company_profile_url=None,
                contact_source="manual_conversion",
                source_url=_clean_text(opportunity.source_url),
                evidence_text=_clean_text(opportunity.requirement_summary),
                verification_status="unverified",
                confidence_score=None,
                contact_status="active",
                is_primary=True,
                notes=f"Created during opportunity conversion from {opportunity.id}",
                created_by=current_user["user_id"],
                updated_at=_now(),
            )
            db.add(contact)
            db.flush()
            _enforce_primary_contact(db, tenant_id, prospect.id, contact.id)
            contact_created = True

    probability_pct = _resolve_probability_pct(normalized_lead_stage, payload.probability_pct)
    estimated_value = _estimate_opportunity_value(opportunity)
    weighted_value = (
        estimated_value * (probability_pct / 100.0) if estimated_value is not None else None
    )
    lead = BusinessDevelopmentLead(
        id=f"BD-LED-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        opportunity_id=opportunity.id,
        prospect_id=prospect.id,
        primary_contact_id=contact.id,
        title=_clean_text(payload.lead_title) or opportunity.title,
        lead_stage=normalized_lead_stage,
        lead_status="active" if normalized_lead_stage in ACTIVE_LEAD_STAGES else "won"
        if normalized_lead_stage == "closed_won"
        else "lost",
        priority=normalized_lead_priority,
        source_type=opportunity.source_type,
        source_name=opportunity.source_name,
        estimated_value=estimated_value,
        weighted_value=weighted_value,
        probability_pct=probability_pct,
        notes=_clean_text(payload.lead_notes) or _clean_text(opportunity.requirement_summary),
        converted_at=_now(),
        created_by=current_user["user_id"],
        updated_at=_now(),
    )
    db.add(lead)
    db.flush()

    for item in payload.selected_experience_matches:
        experience = (
            db.query(BusinessDevelopmentExperienceItem)
            .filter(
                BusinessDevelopmentExperienceItem.id == item.experience_item_id,
                BusinessDevelopmentExperienceItem.tenant_id == tenant_id,
            )
            .first()
        )
        if not experience:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experience item not found: {item.experience_item_id}",
            )
        db.add(
            BusinessDevelopmentLeadExperienceMatch(
                id=f"BD-LXM-{str(uuid4())[:12].upper()}",
                tenant_id=tenant_id,
                lead_id=lead.id,
                experience_item_id=experience.id,
                relevance_score=item.relevance_score,
                match_notes=_clean_text(item.match_notes),
                created_by=current_user["user_id"],
                updated_at=_now(),
            )
        )

    first_task = BusinessDevelopmentTask(
        id=f"BD-TSK-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        lead_id=lead.id,
        opportunity_id=opportunity.id,
        prospect_id=prospect.id,
        assigned_user_id=assigned_user_id,
        title=_clean_text(payload.first_task_title)
        or f"Initial follow-up for {prospect.organization_name}",
        description=_clean_text(payload.first_task_description)
        or "Review converted opportunity, confirm qualification, and plan the first outreach step.",
        task_type="qualification_follow_up",
        task_status="open",
        priority=normalized_task_priority,
        due_at=payload.first_task_due_at or calculate_working_day_due_at(_now(), normalized_task_priority),
        metadata_json={"source": "build_lead", "opportunity_id": opportunity.id},
        created_by=current_user["user_id"],
        updated_at=_now(),
    )
    db.add(first_task)

    activity_rows = []
    if prospect_created:
        activity_rows.append(
            _create_activity_row(
                tenant_id=tenant_id,
                current_user=current_user,
                activity_type="prospect_created",
                subject=f"Prospect created for {prospect.organization_name}",
                description="Prospect created during opportunity conversion.",
                opportunity_id=opportunity.id,
                prospect_id=prospect.id,
                metadata_json={"source": "build_lead"},
            )
        )
    if contact_created:
        activity_rows.append(
            _create_activity_row(
                tenant_id=tenant_id,
                current_user=current_user,
                activity_type="contact_created",
                subject=f"Contact created for {_contact_display_name(contact)}",
                description="Contact created during opportunity conversion.",
                opportunity_id=opportunity.id,
                prospect_id=prospect.id,
                contact_id=contact.id,
                metadata_json={"source": "build_lead"},
            )
        )
    activity_rows.extend(
        [
            _create_activity_row(
                tenant_id=tenant_id,
                current_user=current_user,
                activity_type="lead_created",
                subject=f"Lead created for {lead.title}",
                description="Manual sales workflow lead created from opportunity conversion.",
                lead_id=lead.id,
                opportunity_id=opportunity.id,
                prospect_id=prospect.id,
                contact_id=contact.id,
                metadata_json={"lead_stage": lead.lead_stage},
            ),
            _create_activity_row(
                tenant_id=tenant_id,
                current_user=current_user,
                activity_type="task_created",
                subject=f"Initial task created: {first_task.title}",
                description="First manual sales workflow task created during conversion.",
                lead_id=lead.id,
                opportunity_id=opportunity.id,
                prospect_id=prospect.id,
                contact_id=contact.id,
                metadata_json={"task_id": first_task.id},
            ),
            _create_activity_row(
                tenant_id=tenant_id,
                current_user=current_user,
                activity_type="opportunity_converted",
                subject=f"Opportunity converted: {opportunity.title}",
                description="Opportunity status changed to converted.",
                lead_id=lead.id,
                opportunity_id=opportunity.id,
                prospect_id=prospect.id,
                contact_id=contact.id,
                metadata_json={"lead_id": lead.id},
            ),
        ]
    )
    for row in activity_rows:
        db.add(row)

    opportunity.opportunity_status = "converted"
    opportunity.updated_at = _now()

    try:
        db.commit()
        db.refresh(lead)
        db.refresh(first_task)
        db.refresh(opportunity)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lead conversion conflicted with an existing tenant record",
        )
    except Exception:
        db.rollback()
        raise

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="CREATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Converted opportunity {opportunity.title} into lead {lead.title}",
        resource_type="bd_lead",
        resource_id=lead.id,
        metadata={"opportunity_id": opportunity.id, "task_id": first_task.id},
    )

    return {
        "success": True,
        "data": {
            "lead": _serialize_lead_with_related(db, tenant_id, lead),
            "first_task": serialize_task(first_task),
            "opportunity": serialize_opportunity(opportunity),
        },
    }


def get_dashboard(db: Session, tenant_id: str) -> dict[str, Any]:
    now = _now()
    today = now.date()
    closing_soon_cutoff = now + timedelta(days=14)

    open_opportunities = (
        db.query(func.count(BusinessDevelopmentOpportunity.id))
        .filter(
            BusinessDevelopmentOpportunity.tenant_id == tenant_id,
            BusinessDevelopmentOpportunity.opportunity_status.in_(ACTIVE_OPPORTUNITY_STATUSES),
        )
        .scalar()
        or 0
    )
    converted_opportunities = (
        db.query(func.count(BusinessDevelopmentOpportunity.id))
        .filter(
            BusinessDevelopmentOpportunity.tenant_id == tenant_id,
            BusinessDevelopmentOpportunity.opportunity_status == "converted",
        )
        .scalar()
        or 0
    )
    active_prospects = (
        db.query(func.count(BusinessDevelopmentProspect.id))
        .filter(
            BusinessDevelopmentProspect.tenant_id == tenant_id,
            BusinessDevelopmentProspect.prospect_status == "active",
        )
        .scalar()
        or 0
    )
    open_leads = (
        db.query(func.count(BusinessDevelopmentLead.id))
        .filter(
            BusinessDevelopmentLead.tenant_id == tenant_id,
            BusinessDevelopmentLead.lead_stage.in_(ACTIVE_LEAD_STAGES),
            BusinessDevelopmentLead.lead_status == "active",
        )
        .scalar()
        or 0
    )
    pipeline_value = (
        db.query(func.coalesce(func.sum(BusinessDevelopmentLead.estimated_value), 0.0))
        .filter(
            BusinessDevelopmentLead.tenant_id == tenant_id,
            BusinessDevelopmentLead.lead_stage.in_(ACTIVE_LEAD_STAGES),
            BusinessDevelopmentLead.lead_status == "active",
        )
        .scalar()
        or 0.0
    )
    weighted_pipeline_value = (
        db.query(func.coalesce(func.sum(BusinessDevelopmentLead.weighted_value), 0.0))
        .filter(
            BusinessDevelopmentLead.tenant_id == tenant_id,
            BusinessDevelopmentLead.lead_stage.in_(ACTIVE_LEAD_STAGES),
            BusinessDevelopmentLead.lead_status == "active",
        )
        .scalar()
        or 0.0
    )
    tasks_due_today = (
        db.query(func.count(BusinessDevelopmentTask.id))
        .filter(
            BusinessDevelopmentTask.tenant_id == tenant_id,
            BusinessDevelopmentTask.task_status.in_(OPEN_TASK_STATUSES),
            BusinessDevelopmentTask.due_at.is_not(None),
            func.date(BusinessDevelopmentTask.due_at) == today.isoformat(),
        )
        .scalar()
        or 0
    )
    overdue_tasks = (
        db.query(func.count(BusinessDevelopmentTask.id))
        .filter(
            BusinessDevelopmentTask.tenant_id == tenant_id,
            BusinessDevelopmentTask.task_status.in_(OPEN_TASK_STATUSES),
            BusinessDevelopmentTask.due_at.is_not(None),
            BusinessDevelopmentTask.due_at < now,
        )
        .scalar()
        or 0
    )

    leads_by_stage_rows = (
        db.query(
            BusinessDevelopmentLead.lead_stage,
            func.count(BusinessDevelopmentLead.id),
        )
        .filter(BusinessDevelopmentLead.tenant_id == tenant_id)
        .group_by(BusinessDevelopmentLead.lead_stage)
        .order_by(BusinessDevelopmentLead.lead_stage.asc())
        .all()
    )
    opportunities_by_source_rows = (
        db.query(
            BusinessDevelopmentOpportunity.source_type,
            func.count(BusinessDevelopmentOpportunity.id),
        )
        .filter(BusinessDevelopmentOpportunity.tenant_id == tenant_id)
        .group_by(BusinessDevelopmentOpportunity.source_type)
        .order_by(func.count(BusinessDevelopmentOpportunity.id).desc())
        .all()
    )
    market_label = func.coalesce(
        BusinessDevelopmentOpportunity.country,
        BusinessDevelopmentOpportunity.region,
        "Unknown",
    )
    opportunities_by_market_rows = (
        db.query(market_label, func.count(BusinessDevelopmentOpportunity.id))
        .filter(BusinessDevelopmentOpportunity.tenant_id == tenant_id)
        .group_by(market_label)
        .order_by(func.count(BusinessDevelopmentOpportunity.id).desc())
        .all()
    )

    closing_soon_rows = (
        db.query(BusinessDevelopmentOpportunity)
        .filter(
            BusinessDevelopmentOpportunity.tenant_id == tenant_id,
            BusinessDevelopmentOpportunity.opportunity_status.in_(ACTIVE_OPPORTUNITY_STATUSES),
            BusinessDevelopmentOpportunity.closing_at.is_not(None),
            BusinessDevelopmentOpportunity.closing_at >= now,
            BusinessDevelopmentOpportunity.closing_at <= closing_soon_cutoff,
        )
        .order_by(BusinessDevelopmentOpportunity.closing_at.asc())
        .limit(10)
        .all()
    )
    recent_activity_rows = (
        db.query(BusinessDevelopmentActivity)
        .filter(BusinessDevelopmentActivity.tenant_id == tenant_id)
        .order_by(BusinessDevelopmentActivity.activity_at.desc(), BusinessDevelopmentActivity.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "success": True,
        "data": {
            "open_opportunities": open_opportunities,
            "converted_opportunities": converted_opportunities,
            "active_prospects": active_prospects,
            "open_leads": open_leads,
            "pipeline_value": pipeline_value,
            "weighted_pipeline_value": weighted_pipeline_value,
            "tasks_due_today": tasks_due_today,
            "overdue_tasks": overdue_tasks,
            "opportunities_closing_soon": {
                "count": len(closing_soon_rows),
                "items": [serialize_opportunity(row) for row in closing_soon_rows],
            },
            "leads_by_stage": [
                {"lead_stage": stage_name, "count": count}
                for stage_name, count in leads_by_stage_rows
            ],
            "opportunities_by_source": [
                {"source_type": source_type, "count": count}
                for source_type, count in opportunities_by_source_rows
            ],
            "opportunities_by_market": [
                {"market": market, "count": count}
                for market, count in opportunities_by_market_rows
            ],
            "recent_activities": [serialize_activity(row) for row in recent_activity_rows],
        },
    }


def get_health_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    experience_count = (
        db.query(func.count(BusinessDevelopmentExperienceItem.id))
        .filter(BusinessDevelopmentExperienceItem.tenant_id == tenant_id)
        .scalar()
        or 0
    )
    opportunity_count = (
        db.query(func.count(BusinessDevelopmentOpportunity.id))
        .filter(BusinessDevelopmentOpportunity.tenant_id == tenant_id)
        .scalar()
        or 0
    )
    return {
        "success": True,
        "data": {
            "experience_item_count": experience_count,
            "opportunity_count": opportunity_count,
            "active_statuses": sorted(ACTIVE_OPPORTUNITY_STATUSES),
            "allowed_statuses": sorted(ALLOWED_OPPORTUNITY_STATUSES),
            "allowed_lead_stages": sorted(ALLOWED_LEAD_STAGES),
            "allowed_task_statuses": sorted(ALLOWED_TASK_STATUSES),
        },
    }
