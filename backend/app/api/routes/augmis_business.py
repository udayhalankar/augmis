from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Query
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
    AugmisBusinessConnectorProviderUpdateRequest,
    AugmisBusinessConnectorScanRequest,
    AugmisBusinessConnectorUpdateRequest,
    AugmisBusinessDiscoveryUpdateRequest,
    AugmisBusinessDiscoveryTranslationRequest,
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
    AugmisBusinessSearchProviderCreateRequest,
    AugmisBusinessSearchProviderUpdateRequest,
    AugmisBusinessStatusActionRequest,
    AugmisBusinessTaskCompleteRequest,
    AugmisBusinessTaskCreateRequest,
    AugmisBusinessTaskUpdateRequest,
    AugmisBusinessWebFetchTestRequest,
    AugmisBusinessWebDomainUpdateRequest,
    AugmisBusinessWebSeedCreateRequest,
    AugmisBusinessWebSeedUpdateRequest,
)
from app.services.augmis_business_discovery_translation_service import (
    get_discovery_translation,
    translate_discovery,
)
from app.services.augmis_business_listener_service import (
    create_connector,
    create_search_profile,
    execute_connector_scan_in_background,
    get_connector,
    get_connector_run,
    get_discovery,
    import_discovery_as_opportunity,
    list_connector_runs,
    list_connectors,
    list_discoveries,
    list_discovery_duplicates,
    list_search_profiles,
    recalculate_independent_discovery_validity,
    reject_discovery,
    reprocess_discovery_content,
    run_connector_scan,
    start_connector_scan,
    stop_connector_run,
    set_connector_provider,
    shortlist_discovery,
    test_connector,
    update_connector,
    update_discovery,
    update_search_profile,
)
from app.services.augmis_business_commercial_intelligence_service import (
    get_daily_deal_desk,
    get_discovery_commercial_intelligence,
    recalculate_discovery_priorities,
)
from app.services.augmis_business_discovery_intelligence_service import (
    deep_assess_discovery,
    get_latest_discovery_deep_assessment,
    list_discovery_deep_assessments,
)
from app.services.augmis_business_connector_credential_service import (
    delete_connector_credential,
    get_connector_credential_status,
    list_connector_credential_statuses,
    save_connector_credential,
    test_connector_credential,
)
from app.services.augmis_business_search_provider_service import (
    create_search_provider,
    delete_search_provider,
    get_search_provider,
    list_search_providers,
    test_search_provider,
    update_search_provider,
)
from app.services.augmis_business_independent_discovery_service import (
    create_web_seed,
    delete_web_seed,
    list_web_domains,
    list_web_pages,
    list_web_seeds,
    recrawl_web_domain,
    test_web_fetch_url,
    update_web_domain,
    update_web_seed,
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


@router.get("/connectors/{connector_id}/web-seeds")
def get_augmis_business_web_seeds(
    connector_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_web_seeds(db, current_user["tenant_id"], connector_id)


@router.post("/connectors/{connector_id}/web-seeds")
def create_augmis_business_web_seed(
    connector_id: str,
    payload: AugmisBusinessWebSeedCreateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return create_web_seed(db, current_user["tenant_id"], connector_id, current_user, payload)


@router.patch("/connectors/{connector_id}/web-seeds/{seed_id}")
def update_augmis_business_web_seed(
    connector_id: str,
    seed_id: str,
    payload: AugmisBusinessWebSeedUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return update_web_seed(db, current_user["tenant_id"], connector_id, seed_id, current_user, payload)


@router.delete("/connectors/{connector_id}/web-seeds/{seed_id}")
def delete_augmis_business_web_seed(
    connector_id: str,
    seed_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return delete_web_seed(db, current_user["tenant_id"], connector_id, seed_id, current_user)


@router.get("/connectors/{connector_id}/web-domains")
def get_augmis_business_web_domains(
    connector_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_web_domains(db, current_user["tenant_id"], connector_id)


@router.patch("/connectors/{connector_id}/web-domains/{domain_id}")
def update_augmis_business_web_domain(
    connector_id: str,
    domain_id: str,
    payload: AugmisBusinessWebDomainUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return update_web_domain(db, current_user["tenant_id"], connector_id, domain_id, current_user, payload)


@router.post("/connectors/{connector_id}/web-domains/{domain_id}/recrawl")
def recrawl_augmis_business_web_domain(
    connector_id: str,
    domain_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return recrawl_web_domain(db, current_user["tenant_id"], connector_id, domain_id, current_user)


@router.get("/connectors/{connector_id}/web-pages")
def get_augmis_business_web_pages(
    connector_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_web_pages(
        db,
        current_user["tenant_id"],
        connector_id,
        page=page,
        page_size=page_size,
        search=search,
    )


@router.post("/connectors/{connector_id}/web-fetch-test")
def test_augmis_business_web_fetch_url(
    connector_id: str,
    payload: AugmisBusinessWebFetchTestRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:scan")
    ),
    db: Session = Depends(get_db),
):
    return test_web_fetch_url(
        db,
        current_user["tenant_id"],
        connector_id,
        payload,
    )


@router.post("/connectors/{connector_id}/test")
def test_augmis_business_connector(
    connector_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return test_connector(db, current_user["tenant_id"], current_user, connector_id)


@router.patch("/connectors/{connector_id}/provider")
def update_augmis_business_connector_provider(
    connector_id: str,
    payload: AugmisBusinessConnectorProviderUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return set_connector_provider(
        db,
        current_user["tenant_id"],
        connector_id,
        current_user,
        payload.provider_code,
    )


@router.get("/search-providers")
def get_augmis_business_search_providers(
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_search_providers(db, current_user["tenant_id"])


@router.post("/search-providers")
def create_augmis_business_search_provider(
    payload: AugmisBusinessSearchProviderCreateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return create_search_provider(db, current_user["tenant_id"], current_user, payload)


@router.get("/search-providers/{provider_id}")
def get_augmis_business_search_provider(
    provider_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_search_provider(db, current_user["tenant_id"], provider_id)


@router.patch("/search-providers/{provider_id}")
def update_augmis_business_search_provider(
    provider_id: str,
    payload: AugmisBusinessSearchProviderUpdateRequest,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return update_search_provider(db, current_user["tenant_id"], provider_id, current_user, payload)


@router.delete("/search-providers/{provider_id}")
def delete_augmis_business_search_provider(
    provider_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return delete_search_provider(db, current_user["tenant_id"], provider_id, current_user)


@router.post("/search-providers/{provider_id}/test")
def test_augmis_business_search_provider_route(
    provider_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return test_search_provider(db, current_user["tenant_id"], provider_id, current_user)


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
        payload.model_dump(exclude_none=True),
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
        payload.model_dump(exclude_none=True),
    )


@router.post("/connectors/{connector_id}/scan")
def run_augmis_business_connector_scan(
    connector_id: str,
    payload: AugmisBusinessConnectorScanRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:scan")
    ),
    db: Session = Depends(get_db),
):
    result = start_connector_scan(db, current_user["tenant_id"], connector_id, current_user, payload)
    run = result["data"]["run"]
    connector = result["data"]["connector"]
    if connector.get("connector_type") == "independent_web_discovery" and run.get("status") == "queued":
        background_tasks.add_task(
            execute_connector_scan_in_background,
            current_user["tenant_id"],
            connector_id,
            current_user,
            payload,
            run["id"],
        )
    return result


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


@router.get("/connectors/{connector_id}/runs/{run_id}")
def get_augmis_business_connector_run(
    connector_id: str,
    run_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_connector_run(db, current_user["tenant_id"], connector_id, run_id)


@router.post("/connectors/{connector_id}/runs/{run_id}/stop")
def stop_augmis_business_connector_run(
    connector_id: str,
    run_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:scan")
    ),
    db: Session = Depends(get_db),
):
    return stop_connector_run(db, current_user["tenant_id"], connector_id, run_id, current_user)


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
    relevance_band: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str | None = Query(None),
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
        relevance_band=relevance_band,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/discoveries/deal-desk")
def get_augmis_business_deal_desk(
    limit: int = Query(10, ge=1, le=20),
    recommendation: str | None = Query(None),
    source_category: str | None = Query(None),
    priority_band: str | None = Query(None),
    opportunity_class: str | None = Query(None),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_daily_deal_desk(
        db,
        current_user["tenant_id"],
        limit=limit,
        recommendation=recommendation,
        source_category=source_category,
        priority_band=priority_band,
        opportunity_class=opportunity_class,
    )


@router.post("/discoveries/recalculate-priorities")
def recalculate_augmis_business_discovery_priorities(
    limit: int = Query(100, ge=1, le=250),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return recalculate_discovery_priorities(
        db,
        current_user["tenant_id"],
        current_user,
        limit=limit,
    )


@router.post("/discoveries/reprocess-content")
def reprocess_augmis_business_discovery_content(
    limit: int = Query(100, ge=1, le=250),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return reprocess_discovery_content(
        db,
        current_user["tenant_id"],
        current_user,
        limit=limit,
    )


@router.post("/discoveries/recalculate-validity")
def recalculate_augmis_business_discovery_validity(
    limit: int = Query(100, ge=1, le=250),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:admin")
    ),
    db: Session = Depends(get_db),
):
    return recalculate_independent_discovery_validity(
        db,
        current_user["tenant_id"],
        current_user,
        limit=limit,
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


@router.get("/discoveries/{discovery_id}/commercial-intelligence")
def get_augmis_business_discovery_commercial_intelligence(
    discovery_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_discovery_commercial_intelligence(db, current_user["tenant_id"], discovery_id)


@router.post("/discoveries/{discovery_id}/deep-assess")
def deep_assess_augmis_business_discovery(
    discovery_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:qualify")
    ),
    db: Session = Depends(get_db),
):
    return deep_assess_discovery(db, current_user["tenant_id"], discovery_id, current_user)


@router.get("/discoveries/{discovery_id}/deep-assessment")
def get_augmis_business_discovery_deep_assessment(
    discovery_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_latest_discovery_deep_assessment(db, current_user["tenant_id"], discovery_id)


@router.get("/discoveries/{discovery_id}/deep-assessments")
def get_augmis_business_discovery_deep_assessment_history(
    discovery_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return list_discovery_deep_assessments(db, current_user["tenant_id"], discovery_id)


@router.get("/discoveries/{discovery_id}/translation")
def get_augmis_business_discovery_translation(
    discovery_id: str,
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:read")
    ),
    db: Session = Depends(get_db),
):
    return get_discovery_translation(db, current_user["tenant_id"], discovery_id)


@router.post("/discoveries/{discovery_id}/translate")
def translate_augmis_business_discovery(
    discovery_id: str,
    payload: AugmisBusinessDiscoveryTranslationRequest | None = None,
    force: bool = Query(False),
    current_user: dict = Depends(
        require_saas_access("augmis_business", "business_development:update")
    ),
    db: Session = Depends(get_db),
):
    return translate_discovery(
        db,
        current_user["tenant_id"],
        discovery_id,
        current_user,
        force=bool(force or (payload.force if payload else False)),
    )


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
    sort_by: str | None = Query(None),
    sort_order: str | None = Query(None),
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
        sort_by=sort_by,
        sort_order=sort_order,
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
    sort_by: str | None = Query(None),
    sort_order: str | None = Query(None),
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
        sort_by=sort_by,
        sort_order=sort_order,
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
    assigned_user_id: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str | None = Query(None),
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
        assigned_user_id=assigned_user_id,
        sort_by=sort_by,
        sort_order=sort_order,
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
    sort_by: str | None = Query(None),
    sort_order: str | None = Query(None),
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
        sort_by=sort_by,
        sort_order=sort_order,
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
