from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.request_context import update_request_context
from app.core.security import get_current_user, require_saas_access
from app.models.repository_models import (
    IntelligencePatternCreateRequest,
    IntelligencePatternUpdateRequest,
    RepositoryAccessCreateRequest,
    RepositoryAccessUpdateRequest,
    RepositoryConnectionUpdateRequest,
    RepositoryCreateRequest,
    WorkAreaCreateRequest,
    WorkAreaUpdateRequest,
)
from app.services.audit_service import create_audit_log
from app.services.connector_sync_service import sync_repository
from app.services.intelligence_pattern_service import (
    create_intelligence_pattern,
    delete_intelligence_pattern,
    list_intelligence_patterns,
    update_intelligence_pattern,
)
from app.services.repository_service import (
    create_repository,
    delete_repository,
    delete_repository_access,
    disconnect_repository,
    get_repository,
    get_user_repository_access,
    grant_repository_access,
    list_repositories,
    list_repository_access,
    reset_repository_index_data,
    update_repository_connection,
    update_repository_access,
)
from app.services.business_area_intelligence_service import (
    get_business_area_detail,
    list_business_area_catalog,
)
from app.services.business_area_dashboard_service import get_business_area_dashboard
from app.services.work_area_service import (
    create_work_area,
    delete_work_area,
    get_work_areas,
    update_work_area,
)


router = APIRouter(prefix="/api/repositories", tags=["Repositories"])


@router.get("")
def repositories(
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    return list_repositories(current_user)


@router.get("/work-areas")
def list_work_areas(
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
):
    return get_work_areas(current_user["tenant_id"])


@router.get("/intelligence-patterns")
def get_patterns(
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
):
    return list_intelligence_patterns(current_user["tenant_id"])


@router.post("/intelligence-patterns")
def add_pattern(
    payload: IntelligencePatternCreateRequest,
    request: Request,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    try:
        result = create_intelligence_pattern(
            tenant_id=current_user["tenant_id"],
            name=payload.name,
            description=payload.description,
            dashboard_type=payload.dashboard_type,
            tags_keywords=payload.tags_keywords,
            summary_focus=payload.summary_focus,
            risk_rules=payload.risk_rules,
            thresholds=payload.thresholds,
            required_specifics=payload.required_specifics,
            entities_to_extract=payload.entities_to_extract,
            summary_template=payload.summary_template,
            threshold_rules=payload.threshold_rules,
            fact_extractors=payload.fact_extractors,
            enabled_checks=payload.enabled_checks,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="INTELLIGENCE_PATTERN_CREATED",
        event_category="SETTINGS",
        description=f"Intelligence pattern created: {result['data']['name']}",
        resource_type="intelligence_pattern",
        resource_id=result["data"]["name"],
        request=request,
        metadata=result["data"],
    )
    return result


@router.patch("/intelligence-patterns/{pattern_name}")
def edit_pattern(
    pattern_name: str,
    payload: IntelligencePatternUpdateRequest,
    request: Request,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    try:
        result = update_intelligence_pattern(
            tenant_id=current_user["tenant_id"],
            existing_name=pattern_name,
            name=payload.name,
            description=payload.description,
            dashboard_type=payload.dashboard_type,
            tags_keywords=payload.tags_keywords,
            summary_focus=payload.summary_focus,
            risk_rules=payload.risk_rules,
            thresholds=payload.thresholds,
            required_specifics=payload.required_specifics,
            entities_to_extract=payload.entities_to_extract,
            summary_template=payload.summary_template,
            threshold_rules=payload.threshold_rules,
            fact_extractors=payload.fact_extractors,
            enabled_checks=payload.enabled_checks,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="INTELLIGENCE_PATTERN_UPDATED",
        event_category="SETTINGS",
        description=f"Intelligence pattern updated: {result['data']['name']}",
        resource_type="intelligence_pattern",
        resource_id=result["data"]["name"],
        request=request,
        metadata=result["data"],
    )
    return result


@router.delete("/intelligence-patterns/{pattern_name}")
def remove_pattern(
    pattern_name: str,
    request: Request,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    try:
        result = delete_intelligence_pattern(
            tenant_id=current_user["tenant_id"],
            name=pattern_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="INTELLIGENCE_PATTERN_DELETED",
        event_category="SETTINGS",
        description=f"Intelligence pattern deleted: {result['data']['name']}",
        resource_type="intelligence_pattern",
        resource_id=result["data"]["name"],
        request=request,
        metadata=result["data"],
    )
    return result


@router.post("/work-areas")
def add_work_area(
    payload: WorkAreaCreateRequest,
    request: Request,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    try:
        result = create_work_area(
            tenant_id=current_user["tenant_id"],
            name=payload.name,
            description=payload.description,
            intelligence_pattern=payload.intelligence_pattern,
            tags_keywords=payload.tags_keywords,
            summary_focus=payload.summary_focus,
            risk_rules=payload.risk_rules,
            thresholds=payload.thresholds,
            required_specifics=payload.required_specifics,
            entities_to_extract=payload.entities_to_extract,
            summary_template=payload.summary_template,
            threshold_rules=payload.threshold_rules,
            fact_extractors=payload.fact_extractors,
            dashboard_type=payload.dashboard_type,
            enabled_checks=payload.enabled_checks,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="WORK_AREA_CREATED",
        event_category="SETTINGS",
        description=f"Work area created: {result['data']['name']}",
        resource_type="work_area",
        resource_id=result["data"]["name"],
        request=request,
        metadata=result["data"],
    )

    return result


@router.patch("/work-areas/{work_area_name}")
def edit_work_area(
    work_area_name: str,
    payload: WorkAreaUpdateRequest,
    request: Request,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    try:
        result = update_work_area(
            tenant_id=current_user["tenant_id"],
            existing_name=work_area_name,
            name=payload.name,
            description=payload.description,
            intelligence_pattern=payload.intelligence_pattern,
            tags_keywords=payload.tags_keywords,
            summary_focus=payload.summary_focus,
            risk_rules=payload.risk_rules,
            thresholds=payload.thresholds,
            required_specifics=payload.required_specifics,
            entities_to_extract=payload.entities_to_extract,
            summary_template=payload.summary_template,
            threshold_rules=payload.threshold_rules,
            fact_extractors=payload.fact_extractors,
            dashboard_type=payload.dashboard_type,
            enabled_checks=payload.enabled_checks,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="WORK_AREA_UPDATED",
        event_category="SETTINGS",
        description=f"Work area updated: {result['data']['name']}",
        resource_type="work_area",
        resource_id=result["data"]["name"],
        request=request,
        metadata=result["data"],
    )

    return result


@router.delete("/work-areas/{work_area_name}")
def remove_work_area(
    work_area_name: str,
    request: Request,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    try:
        result = delete_work_area(
            tenant_id=current_user["tenant_id"],
            name=work_area_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="WORK_AREA_DELETED",
        event_category="SETTINGS",
        description=f"Work area deleted: {result['data']['name']}",
        resource_type="work_area",
        resource_id=result["data"]["name"],
        request=request,
        metadata=result["data"],
    )

    return result


@router.get("/business-areas")
def business_area_catalog(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    return list_business_area_catalog(db, current_user)


@router.get("/business-areas/{business_area}")
def business_area_detail(
    business_area: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    try:
        return get_business_area_detail(db, current_user, business_area)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/business-areas/{business_area}/dashboard")
def business_area_dashboard(
    business_area: str,
    include_records: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    return get_business_area_dashboard(
        business_area,
        current_user["tenant_id"],
        include_records=include_records,
        db=db,
    )


@router.post("")
def add_repository(
    payload: RepositoryCreateRequest,
    request: Request,
    current_user: dict = Depends(
        require_saas_access("documents", "documents:upload")
    ),
    db: Session = Depends(get_db),
):
    result = create_repository(payload, current_user, db)
    repo = result["data"]

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="REPOSITORY_CREATED",
        event_category="REPOSITORY",
        description=f"Repository created: {repo['repository_name']}",
        resource_type="repository",
        resource_id=repo["repository_id"],
        request=request,
        metadata=repo,
    )

    return result


@router.get("/my-access")
def my_repository_access(
    current_user: dict = Depends(get_current_user),
):
    return get_user_repository_access(current_user)


@router.get("/{repository_id}")
def repository_detail(
    repository_id: str,
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    return get_repository(repository_id, current_user)


@router.patch("/{repository_id}/connection")
def update_connection(
    repository_id: str,
    payload: RepositoryConnectionUpdateRequest,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    return update_repository_connection(repository_id, payload, current_user, db)


@router.post("/{repository_id}/sync")
def sync_repo(
    repository_id: str,
    request: Request,
    current_user: dict = Depends(
        require_saas_access("documents", "documents:upload")
    ),
    db: Session = Depends(get_db),
):
    update_request_context(
        route=request.url.path,
        method=request.method,
        repository_id=repository_id,
        component="repository_sync",
    )
    result = sync_repository(repository_id, current_user, db)

    if result.get("success"):
        create_audit_log(
            db=db,
            tenant_id=current_user["tenant_id"],
            user_id=current_user["user_id"],
            event_type="REPOSITORY_SYNC_TRIGGERED",
            event_category="REPOSITORY_SYNC",
            description=f"Manual sync triggered for repository {repository_id}",
            resource_type="repository",
            resource_id=repository_id,
            request=request,
            metadata=result,
        )

    return result


@router.post("/{repository_id}/reindex")
def reindex_repo(
    repository_id: str,
    request: Request,
    current_user: dict = Depends(
        require_saas_access("documents", "documents:upload")
    ),
    db: Session = Depends(get_db),
):
    update_request_context(
        route=request.url.path,
        method=request.method,
        repository_id=repository_id,
        component="repository_reindex",
    )
    reset_result = reset_repository_index_data(repository_id, current_user, db)
    sync_result = sync_repository(repository_id, current_user, db)

    result = {
        "success": bool(sync_result.get("success")),
        "repository_id": repository_id,
        "reset": reset_result,
        "sync": sync_result,
    }

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="REPOSITORY_REINDEX_TRIGGERED",
        event_category="REPOSITORY_SYNC",
        description=f"Repository reindex triggered for {repository_id}",
        resource_type="repository",
        resource_id=repository_id,
        request=request,
        metadata=result,
    )

    return result


@router.post("/{repository_id}/disconnect")
def disconnect_repo(
    repository_id: str,
    request: Request,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    result = disconnect_repository(repository_id, current_user, db)

    if result.get("success"):
        create_audit_log(
            db=db,
            tenant_id=current_user["tenant_id"],
            user_id=current_user["user_id"],
            event_type="REPOSITORY_DISCONNECTED",
            event_category="REPOSITORY",
            description=f"Repository disconnected: {repository_id}",
            resource_type="repository",
            resource_id=repository_id,
            request=request,
            metadata=result,
        )

    return result


@router.delete("/{repository_id}")
def remove_repository(
    repository_id: str,
    request: Request,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    result = delete_repository(repository_id, current_user, db)

    if result.get("deleted"):
        create_audit_log(
            db=db,
            tenant_id=current_user["tenant_id"],
            user_id=current_user["user_id"],
            event_type="REPOSITORY_REMOVED",
            event_category="REPOSITORY",
            description=f"Repository removed: {repository_id}",
            resource_type="repository",
            resource_id=repository_id,
            request=request,
            metadata=result,
        )

    return result


@router.get("/{repository_id}/access")
def repository_access(
    repository_id: str,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
):
    return list_repository_access(repository_id, current_user)


@router.post("/access")
def grant_access(
    payload: RepositoryAccessCreateRequest,
    request: Request,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    result = grant_repository_access(payload, current_user, db)
    access = result["data"]

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="REPOSITORY_ACCESS_GRANTED",
        event_category="REPOSITORY",
        description=f"Repository access granted to user {access['user_id']}",
        resource_type="repository_access",
        resource_id=access["access_id"],
        request=request,
        metadata=access,
    )

    return result


@router.patch("/access/{access_id}")
def update_access(
    access_id: str,
    payload: RepositoryAccessUpdateRequest,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
):
    return update_repository_access(access_id, payload, current_user)


@router.delete("/access/{access_id}")
def remove_access(
    access_id: str,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
):
    return delete_repository_access(access_id, current_user)
