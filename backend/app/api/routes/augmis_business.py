from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_saas_access
from app.models.augmis_business_models import (
    AugmisBusinessActivityCreateRequest,
    AugmisBusinessBuildLeadRequest,
    AugmisBusinessContactCreateRequest,
    AugmisBusinessContactUpdateRequest,
    AugmisBusinessConnectorCreateRequest,
    AugmisBusinessConnectorCredentialTestRequest,
    AugmisBusinessConnectorCredentialWriteRequest,
    AugmisBusinessConnectorScanRequest,
    AugmisBusinessConnectorUpdateRequest,
    AugmisBusinessDiscoveryUpdateRequest,
    AugmisBusinessLeadStageUpdateRequest,
    AugmisBusinessLeadUpdateRequest,
    AugmisBusinessMiniSolutionGenerateRequest,
    AugmisBusinessMiniSolutionUpdateRequest,
    AugmisBusinessOpportunityCreateRequest,
    AugmisBusinessOpportunityUpdateRequest,
    AugmisBusinessReplyCreateRequest,
    AugmisBusinessReplyResponseDraftUpdateRequest,
    AugmisBusinessReplyResponseGenerateRequest,
    AugmisBusinessReplyUpdateRequest,
    AugmisBusinessOutreachDraftUpdateRequest,
    AugmisBusinessOutreachGenerateRequest,
    AugmisBusinessProspectCreateRequest,
    AugmisBusinessProspectUpdateRequest,
    AugmisBusinessSearchProfileCreateRequest,
    AugmisBusinessSearchProfileUpdateRequest,
    AugmisBusinessStatusActionRequest,
    AugmisBusinessTaskCompleteRequest,
    AugmisBusinessTaskCreateRequest,
    AugmisBusinessTaskUpdateRequest,
)
from app.services.augmis_business_listener_service import (
    create_connector,
    create_search_profile,
    get_connector,
    get_discovery,
    import_discovery_as_opportunity,
    list_connector_runs,
    list_connectors,
    list_discoveries,
    list_discovery_duplicates,
    list_search_profiles,
    reject_discovery,
    run_connector_scan,
    shortlist_discovery,
    test_connector,
    update_connector,
    update_discovery,
    update_search_profile,
)
from app.services.augmis_business_connector_credential_service import (
    delete_connector_credential,
    get_connector_credential_status,
    list_connector_credential_statuses,
    save_connector_credential,
    test_connector_credential,
)
from app.services.augmis_business_ai_service import (
    assess_opportunity_ai,
    get_latest_opportunity_ai_assessment,
    list_latest_opportunity_experience_matches,
    list_opportunity_ai_assessment_history,
)
from app.services.augmis_business_generation_service import (
    approve_mini_solution,
    approve_outreach_draft,
    generate_mini_solution_for_lead,
    generate_mini_solution_for_opportunity,
    generate_outreach_for_lead,
    generate_outreach_for_opportunity,
    get_mini_solution,
    get_outreach_draft,
    list_mini_solutions_for_opportunity,
    list_outreach_for_opportunity,
    reject_mini_solution,
    reject_outreach_draft,
    update_mini_solution,
    update_outreach_draft,
)
from app.services.augmis_business_reply_service import (
    analyze_reply,
    approve_reply_response,
    create_reply,
    generate_reply_response,
    get_latest_reply_analysis,
    get_reply,
    get_reply_response,
    list_replies,
    list_reply_analyses,
    list_reply_responses,
    reject_reply_response,
    update_reply,
    update_reply_response,
)
from app.services.augmis_business_service import (
    build_lead,
    complete_task,
    create_contact,
    create_lead_activity,
    create_opportunity,
    create_prospect,
    create_task,
    delete_contact,
    delete_opportunity,
    get_dashboard,
    get_health_summary,
    get_lead,
    get_opportunity,
    get_prospect,
    list_experience_items,
    list_lead_activities,
    list_lead_tasks,
    list_leads,
    list_opportunities,
    list_prospect_activities,
    list_prospect_contacts,
    list_prospect_leads,
    list_prospect_opportunities,
    list_prospects,
    list_assignable_users,
    list_tasks,
    update_contact,
    update_lead,
    update_lead_stage,
    update_opportunity,
    update_prospect,
    update_task,
)


router = APIRouter(prefix="/api/augmis-business", tags=["AUGMIS Business"])


@router.get("/health")
def get_augmis_business_health(
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_health_summary(db, current_user["tenant_id"])


@router.get("/search-profiles")
def get_augmis_business_search_profiles(
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_search_profiles(db, current_user["tenant_id"], current_user)


@router.post("/search-profiles")
def create_augmis_business_search_profile(
    payload: AugmisBusinessSearchProfileCreateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return create_search_profile(db, current_user["tenant_id"], current_user, payload)


@router.patch("/search-profiles/{profile_id}")
def update_augmis_business_search_profile(
    profile_id: str,
    payload: AugmisBusinessSearchProfileUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return update_search_profile(db, current_user["tenant_id"], profile_id, current_user, payload)


@router.get("/connectors")
def get_augmis_business_connectors(
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_connectors(db, current_user["tenant_id"], current_user)


@router.post("/connectors")
def create_augmis_business_connector(
    payload: AugmisBusinessConnectorCreateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return create_connector(db, current_user["tenant_id"], current_user, payload)


@router.get("/connectors/{connector_id}")
def get_augmis_business_connector(
    connector_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_connector(db, current_user["tenant_id"], connector_id)


@router.patch("/connectors/{connector_id}")
def update_augmis_business_connector(
    connector_id: str,
    payload: AugmisBusinessConnectorUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return update_connector(db, current_user["tenant_id"], connector_id, current_user, payload)


@router.post("/connectors/{connector_id}/test")
def test_augmis_business_connector(
    connector_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return test_connector(db, current_user["tenant_id"], current_user, connector_id)


@router.get("/connector-credentials")
def get_augmis_business_connector_credentials(
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_connector_credential_statuses(db, current_user["tenant_id"])


@router.get("/connector-credentials/{provider}")
def get_augmis_business_connector_credential(
    provider: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_connector_credential_status(db, current_user["tenant_id"], provider)


@router.post("/connector-credentials/{provider}")
def save_augmis_business_connector_credential(
    provider: str,
    payload: AugmisBusinessConnectorCredentialWriteRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return save_connector_credential(
        db,
        current_user["tenant_id"],
        provider,
        current_user,
        payload.api_key,
    )


@router.delete("/connector-credentials/{provider}")
def delete_augmis_business_connector_credential(
    provider: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return delete_connector_credential(db, current_user["tenant_id"], provider, current_user)


@router.post("/connector-credentials/{provider}/test")
def test_augmis_business_connector_credential_route(
    provider: str,
    payload: AugmisBusinessConnectorCredentialTestRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return test_connector_credential(
        db,
        current_user["tenant_id"],
        provider,
        current_user,
        payload.api_key,
    )


@router.post("/connectors/{connector_id}/scan")
def run_augmis_business_connector_scan(
    connector_id: str,
    payload: AugmisBusinessConnectorScanRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:scan")
    ),
    db: Session = Depends(get_db),
):
    return run_connector_scan(db, current_user["tenant_id"], connector_id, current_user, payload)


@router.get("/connectors/{connector_id}/runs")
def get_augmis_business_connector_runs(
    connector_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_connector_runs(db, current_user["tenant_id"], connector_id, page, page_size)


@router.get("/discoveries")
def get_augmis_business_discoveries(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    connector_id: str | None = Query(None),
    source_category: str | None = Query(None),
    country: str | None = Query(None),
    minimum_preliminary_score: float | None = Query(None, alias="minimum_score"),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_discoveries(
        db,
        current_user["tenant_id"],
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status_filter,
        connector_id=connector_id,
        source_category=source_category,
        country=country,
        minimum_preliminary_score=minimum_preliminary_score,
    )


@router.get("/discoveries/{discovery_id}")
def get_augmis_business_discovery(
    discovery_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_discovery(db, current_user["tenant_id"], discovery_id)


@router.patch("/discoveries/{discovery_id}")
def update_augmis_business_discovery(
    discovery_id: str,
    payload: AugmisBusinessDiscoveryUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:update")
    ),
    db: Session = Depends(get_db),
):
    return update_discovery(db, current_user["tenant_id"], discovery_id, current_user, payload)


@router.post("/discoveries/{discovery_id}/shortlist")
def shortlist_augmis_business_discovery(
    discovery_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:update")
    ),
    db: Session = Depends(get_db),
):
    return shortlist_discovery(db, current_user["tenant_id"], discovery_id, current_user)


@router.post("/discoveries/{discovery_id}/reject")
def reject_augmis_business_discovery(
    discovery_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:update")
    ),
    db: Session = Depends(get_db),
):
    return reject_discovery(db, current_user["tenant_id"], discovery_id, current_user)


@router.post("/discoveries/{discovery_id}/import")
def import_augmis_business_discovery(
    discovery_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:create")
    ),
    db: Session = Depends(get_db),
):
    return import_discovery_as_opportunity(db, current_user["tenant_id"], discovery_id, current_user)


@router.get("/discoveries/{discovery_id}/duplicates")
def get_augmis_business_discovery_duplicates(
    discovery_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_discovery_duplicates(db, current_user["tenant_id"], discovery_id)


@router.get("/dashboard")
def get_augmis_business_dashboard(
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_dashboard(db, current_user["tenant_id"])


@router.get("/experience-items")
def get_experience_items(
    category: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_experience_items(
        db=db,
        tenant_id=current_user["tenant_id"],
        category=category,
        status_filter=status_filter,
    )


@router.get("/opportunities")
def get_opportunities(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    source_type: str | None = Query(None),
    country: str | None = Query(None),
    region: str | None = Query(None),
    organization: str | None = Query(None),
    published_from: datetime | None = Query(None),
    published_to: datetime | None = Query(None),
    closing_from: datetime | None = Query(None),
    closing_to: datetime | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str | None = Query(None),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_opportunities(
        db=db,
        tenant_id=current_user["tenant_id"],
        page=page,
        page_size=page_size,
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
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("/opportunities")
def create_opportunity_record(
    payload: AugmisBusinessOpportunityCreateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:create")
    ),
    db: Session = Depends(get_db),
):
    return create_opportunity(
        db=db,
        tenant_id=current_user["tenant_id"],
        current_user=current_user,
        payload=payload,
    )


@router.get("/opportunities/{opportunity_id}")
def get_opportunity_record(
    opportunity_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_opportunity(db, current_user["tenant_id"], opportunity_id)


@router.patch("/opportunities/{opportunity_id}")
def update_opportunity_record(
    opportunity_id: str,
    payload: AugmisBusinessOpportunityUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:update")
    ),
    db: Session = Depends(get_db),
):
    return update_opportunity(
        db=db,
        tenant_id=current_user["tenant_id"],
        opportunity_id=opportunity_id,
        current_user=current_user,
        payload=payload,
    )


@router.delete("/opportunities/{opportunity_id}")
def delete_opportunity_record(
    opportunity_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:delete")
    ),
    db: Session = Depends(get_db),
):
    return delete_opportunity(
        db=db,
        tenant_id=current_user["tenant_id"],
        opportunity_id=opportunity_id,
        current_user=current_user,
    )


@router.post("/opportunities/{opportunity_id}/build-lead")
def build_lead_from_opportunity(
    opportunity_id: str,
    payload: AugmisBusinessBuildLeadRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:update")
    ),
    db: Session = Depends(get_db),
):
    return build_lead(
        db=db,
        tenant_id=current_user["tenant_id"],
        opportunity_id=opportunity_id,
        current_user=current_user,
        payload=payload,
    )


@router.post("/opportunities/{opportunity_id}/ai-assess")
def assess_opportunity_record(
    opportunity_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:qualify")
    ),
    db: Session = Depends(get_db),
):
    return assess_opportunity_ai(
        db=db,
        tenant_id=current_user["tenant_id"],
        opportunity_id=opportunity_id,
        current_user=current_user,
    )


@router.get("/opportunities/{opportunity_id}/ai-assessment")
def get_opportunity_ai_assessment_record(
    opportunity_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_latest_opportunity_ai_assessment(
        db=db,
        tenant_id=current_user["tenant_id"],
        opportunity_id=opportunity_id,
    )


@router.get("/opportunities/{opportunity_id}/ai-assessments")
def get_opportunity_ai_assessment_history_records(
    opportunity_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_opportunity_ai_assessment_history(
        db=db,
        tenant_id=current_user["tenant_id"],
        opportunity_id=opportunity_id,
    )


@router.get("/opportunities/{opportunity_id}/experience-matches")
def get_opportunity_experience_match_records(
    opportunity_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_latest_opportunity_experience_matches(
        db=db,
        tenant_id=current_user["tenant_id"],
        opportunity_id=opportunity_id,
    )


@router.post("/opportunities/{opportunity_id}/outreach/generate")
def generate_opportunity_outreach_record(
    opportunity_id: str,
    payload: AugmisBusinessOutreachGenerateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:outreach")
    ),
    db: Session = Depends(get_db),
):
    return generate_outreach_for_opportunity(
        db=db,
        tenant_id=current_user["tenant_id"],
        opportunity_id=opportunity_id,
        current_user=current_user,
        payload=payload,
    )


@router.get("/opportunities/{opportunity_id}/outreach")
def get_opportunity_outreach_records(
    opportunity_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_outreach_for_opportunity(db, current_user["tenant_id"], opportunity_id)


@router.get("/outreach/{outreach_id}")
def get_outreach_record(
    outreach_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_outreach_draft(db, current_user["tenant_id"], outreach_id)


@router.patch("/outreach/{outreach_id}")
def update_outreach_record(
    outreach_id: str,
    payload: AugmisBusinessOutreachDraftUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:outreach")
    ),
    db: Session = Depends(get_db),
):
    return update_outreach_draft(
        db=db,
        tenant_id=current_user["tenant_id"],
        outreach_id=outreach_id,
        current_user=current_user,
        payload=payload,
    )


@router.post("/outreach/{outreach_id}/approve")
def approve_outreach_record(
    outreach_id: str,
    payload: AugmisBusinessStatusActionRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:outreach")
    ),
    db: Session = Depends(get_db),
):
    return approve_outreach_draft(
        db=db,
        tenant_id=current_user["tenant_id"],
        outreach_id=outreach_id,
        current_user=current_user,
        payload=payload,
    )


@router.post("/outreach/{outreach_id}/reject")
def reject_outreach_record(
    outreach_id: str,
    payload: AugmisBusinessStatusActionRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:outreach")
    ),
    db: Session = Depends(get_db),
):
    return reject_outreach_draft(
        db=db,
        tenant_id=current_user["tenant_id"],
        outreach_id=outreach_id,
        current_user=current_user,
        payload=payload,
    )


@router.post("/opportunities/{opportunity_id}/mini-solution/generate")
def generate_opportunity_mini_solution_record(
    opportunity_id: str,
    payload: AugmisBusinessMiniSolutionGenerateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:outreach")
    ),
    db: Session = Depends(get_db),
):
    return generate_mini_solution_for_opportunity(
        db=db,
        tenant_id=current_user["tenant_id"],
        opportunity_id=opportunity_id,
        current_user=current_user,
        payload=payload,
    )


@router.get("/opportunities/{opportunity_id}/mini-solutions")
def get_opportunity_mini_solution_records(
    opportunity_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_mini_solutions_for_opportunity(db, current_user["tenant_id"], opportunity_id)


@router.get("/mini-solutions/{solution_id}")
def get_mini_solution_record(
    solution_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_mini_solution(db, current_user["tenant_id"], solution_id)


@router.patch("/mini-solutions/{solution_id}")
def update_mini_solution_record(
    solution_id: str,
    payload: AugmisBusinessMiniSolutionUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:outreach")
    ),
    db: Session = Depends(get_db),
):
    return update_mini_solution(
        db=db,
        tenant_id=current_user["tenant_id"],
        solution_id=solution_id,
        current_user=current_user,
        payload=payload,
    )


@router.post("/mini-solutions/{solution_id}/approve")
def approve_mini_solution_record(
    solution_id: str,
    payload: AugmisBusinessStatusActionRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:outreach")
    ),
    db: Session = Depends(get_db),
):
    return approve_mini_solution(
        db=db,
        tenant_id=current_user["tenant_id"],
        solution_id=solution_id,
        current_user=current_user,
        payload=payload,
    )


@router.post("/mini-solutions/{solution_id}/reject")
def reject_mini_solution_record(
    solution_id: str,
    payload: AugmisBusinessStatusActionRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:outreach")
    ),
    db: Session = Depends(get_db),
):
    return reject_mini_solution(
        db=db,
        tenant_id=current_user["tenant_id"],
        solution_id=solution_id,
        current_user=current_user,
        payload=payload,
    )


@router.get("/prospects")
def get_prospects(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_prospects(
        db=db,
        tenant_id=current_user["tenant_id"],
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status_filter,
    )


@router.post("/prospects")
def create_prospect_record(
    payload: AugmisBusinessProspectCreateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:create")
    ),
    db: Session = Depends(get_db),
):
    return create_prospect(
        db=db,
        tenant_id=current_user["tenant_id"],
        current_user=current_user,
        payload=payload,
    )


@router.get("/prospects/{prospect_id}")
def get_prospect_record(
    prospect_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_prospect(db, current_user["tenant_id"], prospect_id)


@router.get("/prospects/{prospect_id}/contacts")
def get_prospect_contacts(
    prospect_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_prospect_contacts(db, current_user["tenant_id"], prospect_id)


@router.get("/prospects/{prospect_id}/opportunities")
def get_prospect_opportunities(
    prospect_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_prospect_opportunities(db, current_user["tenant_id"], prospect_id)


@router.get("/prospects/{prospect_id}/leads")
def get_prospect_leads(
    prospect_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_prospect_leads(db, current_user["tenant_id"], prospect_id)


@router.get("/prospects/{prospect_id}/activities")
def get_prospect_activities(
    prospect_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_prospect_activities(db, current_user["tenant_id"], prospect_id)


@router.patch("/prospects/{prospect_id}")
def update_prospect_record(
    prospect_id: str,
    payload: AugmisBusinessProspectUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:update")
    ),
    db: Session = Depends(get_db),
):
    return update_prospect(
        db=db,
        tenant_id=current_user["tenant_id"],
        prospect_id=prospect_id,
        current_user=current_user,
        payload=payload,
    )


@router.post("/prospects/{prospect_id}/contacts")
def create_prospect_contact(
    prospect_id: str,
    payload: AugmisBusinessContactCreateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:create")
    ),
    db: Session = Depends(get_db),
):
    return create_contact(
        db=db,
        tenant_id=current_user["tenant_id"],
        prospect_id=prospect_id,
        current_user=current_user,
        payload=payload,
    )


@router.patch("/contacts/{contact_id}")
def update_contact_record(
    contact_id: str,
    payload: AugmisBusinessContactUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:update")
    ),
    db: Session = Depends(get_db),
):
    return update_contact(
        db=db,
        tenant_id=current_user["tenant_id"],
        contact_id=contact_id,
        current_user=current_user,
        payload=payload,
    )


@router.delete("/contacts/{contact_id}")
def delete_contact_record(
    contact_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:delete")
    ),
    db: Session = Depends(get_db),
):
    return delete_contact(
        db=db,
        tenant_id=current_user["tenant_id"],
        contact_id=contact_id,
        current_user=current_user,
    )


@router.get("/leads")
def get_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None),
    stage: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    prospect_id: str | None = Query(None),
    opportunity_id: str | None = Query(None),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_leads(
        db=db,
        tenant_id=current_user["tenant_id"],
        page=page,
        page_size=page_size,
        search=search,
        stage=stage,
        status_filter=status_filter,
        prospect_id=prospect_id,
        opportunity_id=opportunity_id,
    )


@router.get("/leads/{lead_id}")
def get_lead_record(
    lead_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_lead(db, current_user["tenant_id"], lead_id)


@router.post("/leads/{lead_id}/outreach/generate")
def generate_lead_outreach_record(
    lead_id: str,
    payload: AugmisBusinessOutreachGenerateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:outreach")
    ),
    db: Session = Depends(get_db),
):
    return generate_outreach_for_lead(
        db=db,
        tenant_id=current_user["tenant_id"],
        lead_id=lead_id,
        current_user=current_user,
        payload=payload,
    )


@router.post("/leads/{lead_id}/mini-solution/generate")
def generate_lead_mini_solution_record(
    lead_id: str,
    payload: AugmisBusinessMiniSolutionGenerateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:outreach")
    ),
    db: Session = Depends(get_db),
):
    return generate_mini_solution_for_lead(
        db=db,
        tenant_id=current_user["tenant_id"],
        lead_id=lead_id,
        current_user=current_user,
        payload=payload,
    )


@router.patch("/leads/{lead_id}")
def update_lead_record(
    lead_id: str,
    payload: AugmisBusinessLeadUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:update")
    ),
    db: Session = Depends(get_db),
):
    return update_lead(
        db=db,
        tenant_id=current_user["tenant_id"],
        lead_id=lead_id,
        current_user=current_user,
        payload=payload,
    )


@router.patch("/leads/{lead_id}/stage")
def update_lead_stage_record(
    lead_id: str,
    payload: AugmisBusinessLeadStageUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:update")
    ),
    db: Session = Depends(get_db),
):
    return update_lead_stage(
        db=db,
        tenant_id=current_user["tenant_id"],
        lead_id=lead_id,
        current_user=current_user,
        payload=payload,
    )


@router.get("/leads/{lead_id}/activities")
def get_lead_activity_records(
    lead_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_lead_activities(db, current_user["tenant_id"], lead_id)


@router.post("/leads/{lead_id}/activities")
def create_lead_activity_record(
    lead_id: str,
    payload: AugmisBusinessActivityCreateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:create")
    ),
    db: Session = Depends(get_db),
):
    return create_lead_activity(
        db=db,
        tenant_id=current_user["tenant_id"],
        lead_id=lead_id,
        current_user=current_user,
        payload=payload,
    )


@router.get("/leads/{lead_id}/tasks")
def get_lead_task_records(
    lead_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_lead_tasks(db, current_user["tenant_id"], lead_id)


@router.get("/tasks")
def get_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    lead_id: str | None = Query(None),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_tasks(
        db=db,
        tenant_id=current_user["tenant_id"],
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status_filter,
        priority=priority,
        lead_id=lead_id,
    )


@router.get("/users")
def get_augmis_business_users(
    search: str | None = Query(None),
    user_ids: list[str] | None = Query(None),
    include_inactive: bool = Query(False),
    limit: int = Query(25, ge=1, le=100),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_assignable_users(
        db=db,
        tenant_id=current_user["tenant_id"],
        search=search,
        user_ids=user_ids,
        include_inactive=include_inactive,
        limit=limit,
    )


@router.post("/tasks")
def create_task_record(
    payload: AugmisBusinessTaskCreateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:create")
    ),
    db: Session = Depends(get_db),
):
    return create_task(
        db=db,
        tenant_id=current_user["tenant_id"],
        current_user=current_user,
        payload=payload,
    )


@router.patch("/tasks/{task_id}")
def update_task_record(
    task_id: str,
    payload: AugmisBusinessTaskUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:update")
    ),
    db: Session = Depends(get_db),
):
    return update_task(
        db=db,
        tenant_id=current_user["tenant_id"],
        task_id=task_id,
        current_user=current_user,
        payload=payload,
    )


@router.post("/tasks/{task_id}/complete")
def complete_task_record(
    task_id: str,
    payload: AugmisBusinessTaskCompleteRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:update")
    ),
    db: Session = Depends(get_db),
):
    return complete_task(
        db=db,
        tenant_id=current_user["tenant_id"],
        task_id=task_id,
        current_user=current_user,
        payload=payload,
    )


@router.get("/replies")
def get_replies(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    intent: str | None = Query(None),
    lead_id: str | None = Query(None),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_replies(
        db=db,
        tenant_id=current_user["tenant_id"],
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status_filter,
        intent=intent,
        lead_id=lead_id,
    )


@router.post("/replies")
def create_reply_record(
    payload: AugmisBusinessReplyCreateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:create")
    ),
    db: Session = Depends(get_db),
):
    return create_reply(
        db=db,
        tenant_id=current_user["tenant_id"],
        current_user=current_user,
        payload=payload,
    )


@router.get("/replies/{reply_id}")
def get_reply_record(
    reply_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_reply(db, current_user["tenant_id"], reply_id)


@router.patch("/replies/{reply_id}")
def update_reply_record(
    reply_id: str,
    payload: AugmisBusinessReplyUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:update")
    ),
    db: Session = Depends(get_db),
):
    return update_reply(
        db=db,
        tenant_id=current_user["tenant_id"],
        reply_id=reply_id,
        current_user=current_user,
        payload=payload,
    )


@router.post("/replies/{reply_id}/analyze")
def analyze_reply_record(
    reply_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:outreach")
    ),
    db: Session = Depends(get_db),
):
    return analyze_reply(
        db=db,
        tenant_id=current_user["tenant_id"],
        reply_id=reply_id,
        current_user=current_user,
    )


@router.get("/replies/{reply_id}/analysis")
def get_reply_analysis_record(
    reply_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_latest_reply_analysis(db, current_user["tenant_id"], reply_id)


@router.get("/replies/{reply_id}/analyses")
def get_reply_analysis_history(
    reply_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_reply_analyses(db, current_user["tenant_id"], reply_id)


@router.post("/replies/{reply_id}/response/generate")
def generate_reply_response_record(
    reply_id: str,
    payload: AugmisBusinessReplyResponseGenerateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:outreach")
    ),
    db: Session = Depends(get_db),
):
    return generate_reply_response(
        db=db,
        tenant_id=current_user["tenant_id"],
        reply_id=reply_id,
        current_user=current_user,
        payload=payload,
    )


@router.get("/replies/{reply_id}/responses")
def get_reply_response_history(
    reply_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_reply_responses(db, current_user["tenant_id"], reply_id)


@router.get("/reply-responses/{response_id}")
def get_reply_response_record(
    response_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_reply_response(db, current_user["tenant_id"], response_id)


@router.patch("/reply-responses/{response_id}")
def update_reply_response_record(
    response_id: str,
    payload: AugmisBusinessReplyResponseDraftUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:update")
    ),
    db: Session = Depends(get_db),
):
    return update_reply_response(
        db=db,
        tenant_id=current_user["tenant_id"],
        response_id=response_id,
        current_user=current_user,
        payload=payload,
    )


@router.post("/reply-responses/{response_id}/approve")
def approve_reply_response_record(
    response_id: str,
    payload: AugmisBusinessStatusActionRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:outreach")
    ),
    db: Session = Depends(get_db),
):
    return approve_reply_response(
        db=db,
        tenant_id=current_user["tenant_id"],
        response_id=response_id,
        current_user=current_user,
        payload=payload,
    )


@router.post("/reply-responses/{response_id}/reject")
def reject_reply_response_record(
    response_id: str,
    payload: AugmisBusinessStatusActionRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:outreach")
    ),
    db: Session = Depends(get_db),
):
    return reject_reply_response(
        db=db,
        tenant_id=current_user["tenant_id"],
        response_id=response_id,
        current_user=current_user,
        payload=payload,
    )
