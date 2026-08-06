from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_saas_access
from app.models.symployee_record_configuration_models import (
    SymployeeConfigResolutionPreviewRequest,
    SymployeeRecordArchivePolicyCreate,
    SymployeeRecordArchivePolicyUpdate,
    SymployeeRecordAssignmentRuleCreate,
    SymployeeRecordAssignmentRuleUpdate,
    SymployeeRecordCategoryCreate,
    SymployeeRecordCategoryUpdate,
    SymployeeRecordDeclarationRuleCreate,
    SymployeeRecordDeclarationRuleUpdate,
    SymployeeRecordDispositionPolicyCreate,
    SymployeeRecordDispositionPolicyUpdate,
    SymployeeRecordHoldPolicyCreate,
    SymployeeRecordHoldPolicyUpdate,
    SymployeeRecordLifecycleRuleCreate,
    SymployeeRecordLifecycleRuleUpdate,
    SymployeeRecordVitalPolicyCreate,
    SymployeeRecordVitalPolicyUpdate,
    SymployeeRetentionScheduleCreate,
    SymployeeRetentionScheduleUpdate,
)
from app.services import symployee_record_configuration_service as configuration_service


router = APIRouter(
    prefix="/api/symployees/document-controller/configuration/records",
    tags=["SymployeeRecordConfiguration"],
)


def _validate_model(model_class, payload: dict[str, Any]):
    if hasattr(model_class, "model_validate"):
        return model_class.model_validate(payload)
    return model_class.parse_obj(payload)


def _domain_registry() -> dict[str, dict[str, Any]]:
    return {
        "record-categories": {
            "model": configuration_service.SymployeeRecordCategory,
            "id_field": "record_category_id",
            "code_field": "category_code",
            "create_model": SymployeeRecordCategoryCreate,
            "update_model": SymployeeRecordCategoryUpdate,
            "list": configuration_service.list_record_categories,
            "get": configuration_service.get_record_category,
            "create": configuration_service.create_record_category,
            "update": configuration_service.update_record_category,
            "delete": configuration_service.delete_record_category,
        },
        "declaration-rules": {
            "model": configuration_service.SymployeeRecordDeclarationRule,
            "id_field": "declaration_rule_id",
            "code_field": "rule_code",
            "create_model": SymployeeRecordDeclarationRuleCreate,
            "update_model": SymployeeRecordDeclarationRuleUpdate,
            "list": configuration_service.list_record_declaration_rules,
            "get": configuration_service.get_record_declaration_rule,
            "create": configuration_service.create_record_declaration_rule,
            "update": configuration_service.update_record_declaration_rule,
            "delete": configuration_service.delete_record_declaration_rule,
        },
        "lifecycle-rules": {
            "model": configuration_service.SymployeeRecordLifecycleRule,
            "id_field": "lifecycle_rule_id",
            "code_field": "rule_code",
            "create_model": SymployeeRecordLifecycleRuleCreate,
            "update_model": SymployeeRecordLifecycleRuleUpdate,
            "list": configuration_service.list_record_lifecycle_rules,
            "get": configuration_service.get_record_lifecycle_rule,
            "create": configuration_service.create_record_lifecycle_rule,
            "update": configuration_service.update_record_lifecycle_rule,
            "delete": configuration_service.delete_record_lifecycle_rule,
        },
        "retention-schedules": {
            "model": configuration_service.SymployeeRetentionSchedule,
            "id_field": "retention_schedule_id",
            "code_field": "schedule_code",
            "create_model": SymployeeRetentionScheduleCreate,
            "update_model": SymployeeRetentionScheduleUpdate,
            "list": configuration_service.list_retention_schedules,
            "get": configuration_service.get_retention_schedule,
            "create": configuration_service.create_retention_schedule,
            "update": configuration_service.update_retention_schedule,
            "delete": configuration_service.delete_retention_schedule,
        },
        "vital-policies": {
            "model": configuration_service.SymployeeRecordVitalPolicy,
            "id_field": "vital_policy_id",
            "code_field": "policy_code",
            "create_model": SymployeeRecordVitalPolicyCreate,
            "update_model": SymployeeRecordVitalPolicyUpdate,
            "list": configuration_service.list_record_vital_policies,
            "get": configuration_service.get_record_vital_policy,
            "create": configuration_service.create_record_vital_policy,
            "update": configuration_service.update_record_vital_policy,
            "delete": configuration_service.delete_record_vital_policy,
        },
        "hold-policies": {
            "model": configuration_service.SymployeeRecordHoldPolicy,
            "id_field": "hold_policy_id",
            "code_field": "policy_code",
            "create_model": SymployeeRecordHoldPolicyCreate,
            "update_model": SymployeeRecordHoldPolicyUpdate,
            "list": configuration_service.list_record_hold_policies,
            "get": configuration_service.get_record_hold_policy,
            "create": configuration_service.create_record_hold_policy,
            "update": configuration_service.update_record_hold_policy,
            "delete": configuration_service.delete_record_hold_policy,
        },
        "disposition-policies": {
            "model": configuration_service.SymployeeRecordDispositionPolicy,
            "id_field": "disposition_policy_id",
            "code_field": "policy_code",
            "create_model": SymployeeRecordDispositionPolicyCreate,
            "update_model": SymployeeRecordDispositionPolicyUpdate,
            "list": configuration_service.list_record_disposition_policies,
            "get": configuration_service.get_record_disposition_policy,
            "create": configuration_service.create_record_disposition_policy,
            "update": configuration_service.update_record_disposition_policy,
            "delete": configuration_service.delete_record_disposition_policy,
        },
        "archive-policies": {
            "model": configuration_service.SymployeeRecordArchivePolicy,
            "id_field": "archive_policy_id",
            "code_field": "policy_code",
            "create_model": SymployeeRecordArchivePolicyCreate,
            "update_model": SymployeeRecordArchivePolicyUpdate,
            "list": configuration_service.list_record_archive_policies,
            "get": configuration_service.get_record_archive_policy,
            "create": configuration_service.create_record_archive_policy,
            "update": configuration_service.update_record_archive_policy,
            "delete": configuration_service.delete_record_archive_policy,
        },
        "assignment-rules": {
            "model": configuration_service.SymployeeRecordAssignmentRule,
            "id_field": "assignment_rule_id",
            "code_field": "rule_code",
            "create_model": SymployeeRecordAssignmentRuleCreate,
            "update_model": SymployeeRecordAssignmentRuleUpdate,
            "list": configuration_service.list_record_assignment_rules,
            "get": configuration_service.get_record_assignment_rule,
            "create": configuration_service.create_record_assignment_rule,
            "update": configuration_service.update_record_assignment_rule,
            "delete": configuration_service.delete_record_assignment_rule,
        },
    }


def _resolve_domain(domain: str) -> dict[str, Any]:
    entry = _domain_registry().get(domain)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Unknown records configuration domain: {domain}")
    return entry


@router.get("")
def get_records_configuration_domains(
    repository_id: str | None = Query(None),
    business_area: str | None = Query(None),
    project_code: str | None = Query(None),
    document_type: str | None = Query(None),
    status: str | None = Query(None),
    current_only: bool = Query(True),
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    tenant_id = current_user["tenant_id"]
    data: dict[str, Any] = {}
    for domain, entry in _domain_registry().items():
        data[domain] = entry["list"](
            db,
            tenant_id,
            repository_id=repository_id,
            business_area=business_area,
            project_code=project_code,
            document_type=document_type,
            status=status,
            current_only=current_only,
        )
    return {"success": True, "data": data}


@router.get("/{domain}")
def list_records_configuration_domain_rows(
    domain: str,
    repository_id: str | None = Query(None),
    business_area: str | None = Query(None),
    project_code: str | None = Query(None),
    document_type: str | None = Query(None),
    status: str | None = Query(None),
    current_only: bool = Query(True),
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    entry = _resolve_domain(domain)
    data = entry["list"](
        db,
        current_user["tenant_id"],
        repository_id=repository_id,
        business_area=business_area,
        project_code=project_code,
        document_type=document_type,
        status=status,
        current_only=current_only,
    )
    return {"success": True, "data": data}


@router.post("/{domain}")
def create_records_configuration_domain_row(
    domain: str,
    payload: dict[str, Any],
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    entry = _resolve_domain(domain)
    try:
        request = _validate_model(entry["create_model"], payload)
        data = entry["create"](db, current_user["tenant_id"], request, current_user["user_id"])
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.get("/{domain}/{row_id}")
def get_records_configuration_domain_row(
    domain: str,
    row_id: str,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    entry = _resolve_domain(domain)
    try:
        data = entry["get"](db, current_user["tenant_id"], row_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.patch("/{domain}/{row_id}")
def update_records_configuration_domain_row(
    domain: str,
    row_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    entry = _resolve_domain(domain)
    try:
        request = _validate_model(entry["update_model"], payload)
        data = entry["update"](db, current_user["tenant_id"], row_id, request, current_user["user_id"])
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.delete("/{domain}/{row_id}")
def delete_records_configuration_domain_row(
    domain: str,
    row_id: str,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    entry = _resolve_domain(domain)
    try:
        entry["delete"](db, current_user["tenant_id"], row_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True}


@router.post("/{domain}/{row_id}/activate")
def activate_records_configuration_domain_row(
    domain: str,
    row_id: str,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    entry = _resolve_domain(domain)
    try:
        data = configuration_service.set_row_status(
            db,
            entry["model"],
            current_user["tenant_id"],
            entry["id_field"],
            row_id,
            status="ACTIVE",
            actor=current_user["user_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/{domain}/{row_id}/deactivate")
def deactivate_records_configuration_domain_row(
    domain: str,
    row_id: str,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    entry = _resolve_domain(domain)
    try:
        data = configuration_service.set_row_status(
            db,
            entry["model"],
            current_user["tenant_id"],
            entry["id_field"],
            row_id,
            status="INACTIVE",
            actor=current_user["user_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/{domain}/preview-resolution")
def preview_records_configuration_resolution(
    domain: str,
    payload: SymployeeConfigResolutionPreviewRequest,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
    db: Session = Depends(get_db),
):
    entry = _resolve_domain(domain)
    data = configuration_service.preview_resolution(
        db,
        entry["model"],
        current_user["tenant_id"],
        entry["code_field"],
        repository_id=payload.repository_id,
        business_area=payload.business_area,
        project_code=payload.project_code,
        document_type=payload.document_type,
        as_of=payload.as_of,
        current_only=payload.current_only,
        match_fields=payload.match_fields,
    )
    return {"success": True, "data": data}
