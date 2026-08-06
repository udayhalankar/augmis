from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_saas_access
from app.models.symployee_models import (
    SymployeeCommandApprovalRequest,
    SymployeeCommandCreateRequest,
    SymployeeCommandLifecycleRequest,
    SymployeePolicyCreateRequest,
    SymployeePolicyUpdateRequest,
    SymployeeRecommendationDecisionRequest,
    SymployeeRecommendationOverrideRequest,
    SymployeeRecommendationRejectRequest,
)
from app.models.symployee_lifecycle_models import (
    SymployeeLifecycleEventListRequest,
    SymployeeLifecycleTransitionRequest,
)
from app.models.symployee_records_models import (
    SymployeeArchiveTransferRequest,
    SymployeeArchiveTransferCompletionRequest,
    SymployeeRecordDeclarationEvaluationRequest,
    SymployeeRepositoryReprocessRequest,
    SymployeeDispositionCaseRequest,
    SymployeeDispositionApprovalRequest,
    SymployeeDispositionExecutionRequest,
    SymployeeLegalHoldRequest,
    SymployeeRecordDeclarationRequest,
    SymployeeRetentionAutomationRequest,
    SymployeeRecordTimeEvaluationRequest,
    SymployeeVitalStatusRequest,
)
from app.models.symployee_transmittal_models import (
    SymployeeAcknowledgementRequest,
    SymployeeTransmittalCreateRequest,
)
from app.services.symployee_document_service import (
    build_master_document_register,
    get_document_controller_overview,
    get_document_identity_detail,
    resolve_document_file,
    list_approvals,
    list_commands,
    list_document_identities,
    list_recommendations,
    list_symployees,
)
from app.services.symployee_lifecycle_service import (
    STATE_VOCABULARY,
    create_lifecycle_transition,
    list_lifecycle_events,
)
from app.services.symployee_policy_service import list_document_controller_policies
from app.services.symployee_policy_service import (
    bootstrap_document_controller_default_policies,
    create_document_controller_policy,
    get_document_controller_policy,
    update_document_controller_policy,
)
from app.services.symployee_records_service import (
    approve_disposition_case,
    complete_archive_transfer,
    create_disposition_case,
    declare_record,
    evaluate_record_declaration,
    execute_disposition_case,
    reprocess_repository_record_declarations,
    run_time_evaluation,
    run_retention_disposition_automation,
    initiate_archive_transfer,
    place_legal_hold,
    update_vital_status,
)
from app.services.symployee_recommendation_service import (
    acknowledge_connector_command,
    approve_connector_command,
    approve_recommendation,
    create_connector_command,
    dispatch_connector_command,
    fail_connector_command,
    override_recommendation,
    reject_connector_command,
    reject_recommendation,
    request_connector_command_rollback,
)
from app.services.symployee_transmittal_service import (
    acknowledge_transmittal,
    create_transmittal,
    list_transmittals,
)


router = APIRouter(prefix="/api/symployees", tags=["Symployees"])


def _serialize_result_rows(rows) -> list[dict]:
    serialized: list[dict] = []
    for row in rows:
        item: dict[str, object] = {}
        for key, value in row._mapping.items():
            item[key] = value.isoformat() if hasattr(value, "isoformat") and value is not None else value
        serialized.append(item)
    return serialized


@router.get("")
def get_symployees(
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": list_symployees(db, current_user["tenant_id"]),
    }


@router.get("/document-controller/overview")
def get_document_controller_summary(
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": get_document_controller_overview(db, current_user["tenant_id"]),
    }


@router.get("/document-controller/policies")
def get_document_controller_policies(
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": list_document_controller_policies(db, current_user["tenant_id"]),
    }


@router.post("/document-controller/policies")
def create_document_controller_policy_record(
    payload: SymployeePolicyCreateRequest,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": create_document_controller_policy(
            db=db,
            tenant_id=current_user["tenant_id"],
            name=payload.name,
            policy_domain=payload.policy_domain,
            policy_code=payload.policy_code,
            config_json=payload.config_json,
            created_by=current_user["user_id"],
            scope_type=payload.scope_type,
            scope_ref=payload.scope_ref,
            is_default=payload.is_default,
            status=payload.status,
        ),
    }


@router.post("/document-controller/policies/bootstrap-defaults")
def bootstrap_document_controller_default_policy_records(
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": bootstrap_document_controller_default_policies(
            db=db,
            tenant_id=current_user["tenant_id"],
            created_by=current_user["user_id"],
        ),
    }


@router.get("/document-controller/policies/{policy_domain}/{policy_code}")
def get_document_controller_policy_record(
    policy_domain: str,
    policy_code: str,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    try:
        data = get_document_controller_policy(
            db=db,
            tenant_id=current_user["tenant_id"],
            policy_domain=policy_domain,
            policy_code=policy_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.patch("/document-controller/policies/{policy_domain}/{policy_code}")
def update_document_controller_policy_record(
    policy_domain: str,
    policy_code: str,
    payload: SymployeePolicyUpdateRequest,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    try:
        data = update_document_controller_policy(
            db=db,
            tenant_id=current_user["tenant_id"],
            policy_domain=policy_domain,
            policy_code=policy_code,
            modified_by=current_user["user_id"],
            name=payload.name,
            scope_type=payload.scope_type,
            scope_ref=payload.scope_ref,
            config_json=payload.config_json,
            is_default=payload.is_default,
            status=payload.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.get("/document-controller/documents")
def get_document_controller_documents(
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": list_document_identities(db, current_user["tenant_id"], limit=limit),
    }


@router.get("/document-controller/documents/{identity_id}")
def get_document_controller_document_detail(
    identity_id: str,
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    try:
        data = get_document_identity_detail(db, current_user["tenant_id"], identity_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "success": True,
        "data": data,
    }


@router.get("/document-controller/documents/{identity_id}/file")
def open_document_controller_document_file(
    identity_id: str,
    version_id: str | None = Query(None),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    try:
        file_ref = resolve_document_file(
            db=db,
            tenant_id=current_user["tenant_id"],
            identity_id=identity_id,
            version_id=version_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FileResponse(
        path=file_ref["path"],
        filename=file_ref["file_name"],
        media_type=file_ref.get("mime_type") or "application/octet-stream",
    )


@router.get("/document-controller/recommendations")
def get_document_controller_recommendations(
    limit: int = Query(200, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": list_recommendations(db, current_user["tenant_id"], limit=limit),
    }


@router.post("/document-controller/recommendations/{recommendation_id}/approve")
def approve_document_controller_recommendation(
    recommendation_id: str,
    payload: SymployeeRecommendationDecisionRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = approve_recommendation(
            db=db,
            tenant_id=current_user["tenant_id"],
            recommendation_id=recommendation_id,
            approver_user_id=current_user["user_id"],
            comments=payload.comments,
            effective_values=payload.effective_values,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/recommendations/{recommendation_id}/reject")
def reject_document_controller_recommendation(
    recommendation_id: str,
    payload: SymployeeRecommendationRejectRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = reject_recommendation(
            db=db,
            tenant_id=current_user["tenant_id"],
            recommendation_id=recommendation_id,
            approver_user_id=current_user["user_id"],
            comments=payload.comments,
            reason_code=payload.reason_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/recommendations/{recommendation_id}/override")
def override_document_controller_recommendation(
    recommendation_id: str,
    payload: SymployeeRecommendationOverrideRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = override_recommendation(
            db=db,
            tenant_id=current_user["tenant_id"],
            recommendation_id=recommendation_id,
            approver_user_id=current_user["user_id"],
            reason_code=payload.reason_code,
            reason_text=payload.reason_text,
            after_state=payload.after_state,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.get("/document-controller/approvals")
def get_document_controller_approvals(
    limit: int = Query(200, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": list_approvals(db, current_user["tenant_id"], limit=limit),
    }


@router.get("/document-controller/commands")
def get_document_controller_commands(
    limit: int = Query(200, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": list_commands(db, current_user["tenant_id"], limit=limit),
    }


@router.post("/document-controller/commands")
def create_document_controller_command(
    payload: SymployeeCommandCreateRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    data = create_connector_command(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        repository_id=payload.repository_id,
        identity_id=payload.identity_id,
        version_id=payload.version_id,
        command_type=payload.command_type,
        payload=payload.payload,
        source_recommendation_id=payload.source_recommendation_id,
        agent_id=payload.agent_id,
    )
    return {"success": True, "data": data}


@router.post("/document-controller/commands/{command_id}/approve")
def approve_document_controller_command(
    command_id: str,
    payload: SymployeeCommandApprovalRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = approve_connector_command(
            db=db,
            tenant_id=current_user["tenant_id"],
            command_id=command_id,
            approver_user_id=current_user["user_id"],
            comments=payload.comments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/commands/{command_id}/reject")
def reject_document_controller_command(
    command_id: str,
    payload: SymployeeCommandApprovalRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = reject_connector_command(
            db=db,
            tenant_id=current_user["tenant_id"],
            command_id=command_id,
            approver_user_id=current_user["user_id"],
            comments=payload.comments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/commands/{command_id}/dispatch")
def dispatch_document_controller_command(
    command_id: str,
    payload: SymployeeCommandLifecycleRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = dispatch_connector_command(
            db=db,
            tenant_id=current_user["tenant_id"],
            command_id=command_id,
            user_id=current_user["user_id"],
            comments=payload.comments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/commands/{command_id}/acknowledge")
def acknowledge_document_controller_command(
    command_id: str,
    payload: SymployeeCommandLifecycleRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = acknowledge_connector_command(
            db=db,
            tenant_id=current_user["tenant_id"],
            command_id=command_id,
            user_id=current_user["user_id"],
            comments=payload.comments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/commands/{command_id}/fail")
def fail_document_controller_command(
    command_id: str,
    payload: SymployeeCommandLifecycleRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = fail_connector_command(
            db=db,
            tenant_id=current_user["tenant_id"],
            command_id=command_id,
            user_id=current_user["user_id"],
            comments=payload.comments,
            failure_reason=payload.failure_reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/commands/{command_id}/rollback")
def rollback_document_controller_command(
    command_id: str,
    payload: SymployeeCommandLifecycleRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = request_connector_command_rollback(
            db=db,
            tenant_id=current_user["tenant_id"],
            command_id=command_id,
            user_id=current_user["user_id"],
            comments=payload.comments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.get("/document-controller/registers/master-document-register")
def get_document_controller_master_register(
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": build_master_document_register(db, current_user["tenant_id"]),
    }


@router.get("/document-controller/lifecycle-events")
def get_document_controller_lifecycle_events(
    identity_id: str | None = Query(None),
    version_id: str | None = Query(None),
    state_dimension: str | None = Query(None),
    event_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    request = SymployeeLifecycleEventListRequest(
        identity_id=identity_id,
        version_id=version_id,
        state_dimension=state_dimension,
        event_type=event_type,
        limit=limit,
    )
    return {
        "success": True,
        "data": list_lifecycle_events(
            db,
            current_user["tenant_id"],
            identity_id=request.identity_id,
            version_id=request.version_id,
            state_dimension=request.state_dimension,
            event_type=request.event_type,
            limit=request.limit,
        ),
    }


@router.get("/document-controller/lifecycle/{identity_id}")
def get_document_controller_lifecycle_history(
    identity_id: str,
    limit: int = Query(200, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": list_lifecycle_events(
            db,
            current_user["tenant_id"],
            identity_id=identity_id,
            limit=limit,
        ),
    }


@router.post("/document-controller/lifecycle/transitions")
def create_document_controller_lifecycle_transition(
    payload: SymployeeLifecycleTransitionRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = create_lifecycle_transition(
            db,
            current_user["tenant_id"],
            identity_id=payload.identity_id,
            version_id=payload.version_id,
            state_dimension=payload.state_dimension,
            new_state=payload.new_state,
            performed_by=current_user["user_id"],
            reason=payload.reason,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/records/declarations")
def declare_document_controller_record(
    payload: SymployeeRecordDeclarationRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = declare_record(
            db,
            current_user["tenant_id"],
            identity_id=payload.identity_id,
            version_id=payload.version_id,
            record_category=payload.record_category,
            owner_user_id=payload.owner_user_id,
            declared_by=current_user["user_id"],
            declaration_reason=payload.declaration_reason,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/records/declaration-evaluation")
def evaluate_document_controller_record_declaration(
    payload: SymployeeRecordDeclarationEvaluationRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = evaluate_record_declaration(
            db,
            current_user["tenant_id"],
            identity_id=payload.identity_id,
            version_id=payload.version_id,
            trigger_event=payload.trigger_event,
            dry_run=payload.dry_run,
            performed_by=current_user["user_id"],
            evaluation_reason=payload.evaluation_reason,
            context_overrides_json=payload.context_overrides_json,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/records/reprocess")
def reprocess_document_controller_repository_content(
    payload: SymployeeRepositoryReprocessRequest,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    try:
        data = reprocess_repository_record_declarations(
            db,
            current_user["tenant_id"],
            repository_id=payload.repository_id,
            identity_ids=payload.identity_ids,
            limit=payload.limit,
            trigger_event=payload.trigger_event,
            dry_run=payload.dry_run,
            performed_by=current_user["user_id"],
            evaluation_reason=payload.evaluation_reason,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/records/time-evaluation")
def run_document_controller_record_time_evaluation(
    payload: SymployeeRecordTimeEvaluationRequest,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    try:
        data = run_time_evaluation(
            db,
            current_user["tenant_id"],
            identity_id=payload.identity_id,
            version_id=payload.version_id,
            limit=payload.limit,
            performed_by=current_user["user_id"],
            evaluation_reason=payload.evaluation_reason,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/records/retention-automation")
def run_document_controller_retention_automation(
    payload: SymployeeRetentionAutomationRequest,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    try:
        data = run_retention_disposition_automation(
            db,
            current_user["tenant_id"],
            identity_id=payload.identity_id,
            version_id=payload.version_id,
            limit=payload.limit,
            performed_by=current_user["user_id"],
            evaluation_reason=payload.evaluation_reason,
            auto_initiate_disposition=payload.auto_initiate_disposition,
            auto_initiate_archive=payload.auto_initiate_archive,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.get("/document-controller/records/declarations")
def get_document_controller_record_declarations(
    identity_id: str | None = Query(None),
    record_stage: str | None = Query(None),
    record_status: str | None = Query(None),
    vital_status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    sql = """
        select *
        from symployee_record_declarations
        where tenant_id = :tenant_id
          and (:identity_id is null or identity_id = :identity_id)
          and (:record_stage is null or upper(coalesce(record_stage, '')) = upper(:record_stage))
          and (:record_status is null or upper(coalesce(record_status, '')) = upper(:record_status))
          and (:vital_status is null or upper(coalesce(vital_status, '')) = upper(:vital_status))
        order by declared_at desc nulls last, created_at desc
        limit :limit
    """
    rows = db.execute(
        text(sql),
        {
            "tenant_id": current_user["tenant_id"],
            "identity_id": identity_id,
            "record_stage": record_stage,
            "record_status": record_status,
            "vital_status": vital_status,
            "limit": limit,
        },
    ).fetchall()
    return {
        "success": True,
        "data": {
            "items": _serialize_result_rows(rows),
            "filters": {
                "tenant_id": current_user["tenant_id"],
                "identity_id": identity_id,
                "record_stage": record_stage,
                "record_status": record_status,
                "vital_status": vital_status,
                "limit": limit,
            },
        },
    }


@router.get("/document-controller/records/vocabulary")
def get_document_controller_record_vocabulary(
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    return {
        "success": True,
        "data": {
            "hold_categories": ["LEGAL", "VALIDATION", "RECORDS", "OPERATIONAL", "OTHER"],
            "hold_statuses": ["ACTIVE", "RELEASED"],
            "record_stages": ["ACTIVE", "INACTIVE"],
            "record_statuses": sorted(STATE_VOCABULARY["record_status"]),
            "retention_statuses": sorted(STATE_VOCABULARY["retention_status"]),
            "disposition_statuses": ["PENDING_REVIEW", "PENDING_APPROVALS", "APPROVED", "COMPLETED", "CANCELLED"],
            "archive_transfer_statuses": ["PENDING", "COMPLETED", "CANCELLED"],
        },
    }


@router.post("/document-controller/records/vital-status")
def update_document_controller_record_vital_status(
    payload: SymployeeVitalStatusRequest,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    try:
        data = update_vital_status(
            db,
            current_user["tenant_id"],
            identity_id=payload.identity_id,
            vital_status=payload.vital_status,
            modified_by=current_user["user_id"],
            reason=payload.reason,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/records/legal-holds")
def place_document_controller_legal_hold(
    payload: SymployeeLegalHoldRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = place_legal_hold(
            db,
            current_user["tenant_id"],
            identity_id=payload.identity_id,
            hold_category=payload.hold_category,
            hold_code=payload.hold_code,
            authority=payload.authority,
            placed_by=current_user["user_id"],
            reason=payload.reason,
            matter_reference=payload.matter_reference,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.get("/document-controller/records/legal-holds")
def get_document_controller_legal_holds(
    identity_id: str | None = Query(None),
    hold_category: str | None = Query(None),
    hold_status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    sql = """
        select
            legal_hold_id,
            tenant_id,
            identity_id,
            record_declaration_id,
            hold_category,
            hold_code,
            hold_status,
            hold_policy_id,
            authority,
            matter_reference,
            reason,
            placed_at,
            placed_by,
            released_at,
            released_by,
            release_reason,
            metadata_json,
            created_by,
            created_at,
            modified_by,
            modified_at
        from symployee_record_legal_holds
        where tenant_id = :tenant_id
          and (:identity_id is null or identity_id = :identity_id)
          and (:hold_category is null or upper(coalesce(hold_category, '')) = upper(:hold_category))
          and (:hold_status is null or upper(coalesce(hold_status, '')) = upper(:hold_status))
        order by placed_at desc nulls last, created_at desc
        limit :limit
    """
    rows = db.execute(
        text(sql),
        {
            "tenant_id": current_user["tenant_id"],
            "identity_id": identity_id,
            "hold_category": hold_category,
            "hold_status": hold_status,
            "limit": limit,
        },
    ).fetchall()
    return {
        "success": True,
        "data": {
            "items": _serialize_result_rows(rows),
            "filters": {
                "tenant_id": current_user["tenant_id"],
                "identity_id": identity_id,
                "hold_category": hold_category,
                "hold_status": hold_status,
                "limit": limit,
            },
        },
    }


@router.post("/document-controller/records/disposition")
def create_document_controller_disposition_case(
    payload: SymployeeDispositionCaseRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = create_disposition_case(
            db,
            current_user["tenant_id"],
            identity_id=payload.identity_id,
            disposition_type=payload.disposition_type,
            requested_by=current_user["user_id"],
            reason=payload.reason,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.get("/document-controller/records/disposition")
def get_document_controller_disposition_cases(
    identity_id: str | None = Query(None),
    case_status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    sql = """
        select *
        from symployee_disposition_cases
        where tenant_id = :tenant_id
          and (:identity_id is null or identity_id = :identity_id)
          and (:case_status is null or upper(coalesce(case_status, '')) = upper(:case_status))
        order by created_at desc
        limit :limit
    """
    rows = db.execute(
        text(sql),
        {
            "tenant_id": current_user["tenant_id"],
            "identity_id": identity_id,
            "case_status": case_status,
            "limit": limit,
        },
    ).fetchall()
    return {
        "success": True,
        "data": {
            "items": _serialize_result_rows(rows),
            "filters": {
                "tenant_id": current_user["tenant_id"],
                "identity_id": identity_id,
                "case_status": case_status,
                "limit": limit,
            },
        },
    }


@router.post("/document-controller/records/disposition/{disposition_case_id}/approve")
def approve_document_controller_disposition_case(
    disposition_case_id: str,
    payload: SymployeeDispositionApprovalRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = approve_disposition_case(
            db,
            current_user["tenant_id"],
            disposition_case_id=disposition_case_id,
            approval_role=payload.approval_role,
            approver_user_id=current_user["user_id"],
            comments=payload.comments,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/records/disposition/{disposition_case_id}/execute")
def execute_document_controller_disposition_case(
    disposition_case_id: str,
    payload: SymployeeDispositionExecutionRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = execute_disposition_case(
            db,
            current_user["tenant_id"],
            disposition_case_id=disposition_case_id,
            execution_outcome=payload.execution_outcome,
            executed_by=current_user["user_id"],
            reason=payload.reason,
            evidence_json=payload.evidence_json,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/document-controller/records/archive-transfers")
def create_document_controller_archive_transfer(
    payload: SymployeeArchiveTransferRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = initiate_archive_transfer(
            db,
            current_user["tenant_id"],
            identity_id=payload.identity_id,
            archive_destination=payload.archive_destination,
            requested_by=current_user["user_id"],
            disposition_case_id=payload.disposition_case_id,
            preservation_format=payload.preservation_format,
            checksum_value=payload.checksum_value,
            checksum_algorithm=payload.checksum_algorithm,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.get("/document-controller/records/archive-transfers")
def get_document_controller_archive_transfers(
    identity_id: str | None = Query(None),
    disposition_case_id: str | None = Query(None),
    transfer_status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    sql = """
        select *
        from symployee_archive_transfers
        where tenant_id = :tenant_id
          and (:identity_id is null or identity_id = :identity_id)
          and (:disposition_case_id is null or disposition_case_id = :disposition_case_id)
          and (:transfer_status is null or upper(coalesce(transfer_status, '')) = upper(:transfer_status))
        order by requested_at desc nulls last, created_at desc
        limit :limit
    """
    rows = db.execute(
        text(sql),
        {
            "tenant_id": current_user["tenant_id"],
            "identity_id": identity_id,
            "disposition_case_id": disposition_case_id,
            "transfer_status": transfer_status,
            "limit": limit,
        },
    ).fetchall()
    return {
        "success": True,
        "data": {
            "items": _serialize_result_rows(rows),
            "filters": {
                "tenant_id": current_user["tenant_id"],
                "identity_id": identity_id,
                "disposition_case_id": disposition_case_id,
                "transfer_status": transfer_status,
                "limit": limit,
            },
        },
    }


@router.post("/document-controller/records/archive-transfers/{archive_transfer_id}/complete")
def complete_document_controller_archive_transfer(
    archive_transfer_id: str,
    payload: SymployeeArchiveTransferCompletionRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = complete_archive_transfer(
            db,
            current_user["tenant_id"],
            archive_transfer_id=archive_transfer_id,
            completed_by=current_user["user_id"],
            receipt_reference=payload.receipt_reference,
            integrity_verified=payload.integrity_verified,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.get("/document-controller/transmittals")
def get_document_controller_transmittals(
    direction: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": list_transmittals(
            db,
            current_user["tenant_id"],
            direction=direction,
            limit=limit,
        ),
    }


@router.get("/document-controller/transmittals/acknowledgements")
def get_document_controller_transmittal_acknowledgements(
    transmittal_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    sql = """
        select *
        from symployee_distribution_acknowledgements
        where tenant_id = :tenant_id
          and (:transmittal_id is null or transmittal_id = :transmittal_id)
        order by created_at desc
        limit :limit
    """
    rows = db.execute(
        text(sql),
        {
            "tenant_id": current_user["tenant_id"],
            "transmittal_id": transmittal_id,
            "limit": limit,
        },
    ).fetchall()
    return {
        "success": True,
        "data": {
            "items": _serialize_result_rows(rows),
            "filters": {
                "tenant_id": current_user["tenant_id"],
                "transmittal_id": transmittal_id,
                "limit": limit,
            },
        },
    }


@router.get("/document-controller/correspondence")
def get_document_controller_correspondence(
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    sql = """
        select
            di.identity_id as correspondence_id,
            di.canonical_document_number as reference_number,
            di.title as subject,
            di.document_type_code as correspondence_type,
            di.status,
            di.document_lifecycle_stage,
            di.review_status,
            di.issue_status,
            di.record_status,
            di.security_status,
            di.project_code,
            di.originator_code,
            di.created_at,
            di.modified_at,
            repo.repository_name,
            dv.file_name as current_file_name,
            case
                when lower(coalesce(di.document_type_code, '')) like '%incoming%' then 'INCOMING'
                when lower(coalesce(di.document_type_code, '')) like '%outgoing%' then 'OUTGOING'
                else 'UNSPECIFIED'
            end as direction
        from symployee_document_identities di
        left join repositories repo
            on repo.repository_id = di.repository_id
        left join symployee_document_versions dv
            on dv.version_id = di.current_version_id
           and dv.tenant_id = di.tenant_id
        where di.tenant_id = :tenant_id
          and (
            lower(coalesce(di.document_type_code, '')) in ('correspondence', 'customer_correspondence', 'letter')
            or lower(coalesce(di.document_type_code, '')) like '%correspondence%'
            or lower(coalesce(di.title, '')) like '%correspondence%'
            or lower(coalesce(di.title, '')) like '%letter%'
          )
        order by coalesce(di.modified_at, di.created_at) desc, di.identity_id desc
        limit :limit
    """
    rows = db.execute(
        text(sql),
        {
            "tenant_id": current_user["tenant_id"],
            "limit": limit,
        },
    ).fetchall()
    return {
        "success": True,
        "data": {
            "items": _serialize_result_rows(rows),
            "filters": {
                "tenant_id": current_user["tenant_id"],
                "limit": limit,
            },
        },
    }


@router.post("/document-controller/transmittals")
def create_document_controller_transmittal(
    payload: SymployeeTransmittalCreateRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    data = create_transmittal(
        db,
        current_user["tenant_id"],
        direction=payload.direction,
        purpose_code=payload.purpose_code,
        sender_org=payload.sender_org,
        recipient_org=payload.recipient_org,
        response_required=payload.response_required,
        response_due_at=payload.response_due_at,
        prepared_by=current_user["user_id"],
        workflow_instance_id=payload.workflow_instance_id,
        subject=payload.subject,
        notes=payload.notes,
        transmittal_number=payload.transmittal_number,
        metadata_json=payload.metadata_json,
    )
    return {"success": True, "data": data}


@router.post("/document-controller/transmittals/acknowledgements")
def acknowledge_document_controller_transmittal(
    payload: SymployeeAcknowledgementRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = acknowledge_transmittal(
            db,
            current_user["tenant_id"],
            transmittal_id=payload.transmittal_id,
            transmittal_item_id=payload.transmittal_item_id,
            recipient_ref=payload.recipient_ref,
            recipient_name=payload.recipient_name,
            status=payload.status,
            response_status=payload.response_status,
            due_at=payload.due_at,
            comments=payload.comments,
            modified_by=current_user["user_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}
