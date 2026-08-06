from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db_models import (
    SymployeeRecordArchivePolicy,
    SymployeeRecordAssignmentRule,
    SymployeeRecordCategory,
    SymployeeRecordDeclarationRule,
    SymployeeRecordDispositionPolicy,
    SymployeeRecordHoldPolicy,
    SymployeeRecordLifecycleRule,
    SymployeeRecordVitalPolicy,
    SymployeeRetentionSchedule,
)
from app.models.symployee_record_configuration_models import (
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


def _new_id(prefix: str) -> str:
    return f"{prefix}-{str(uuid4())[:12].upper()}"


def _model_dump(model, *, exclude_unset: bool = False) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=exclude_unset)
    return model.dict(exclude_unset=exclude_unset)


def _normalize_status(data: dict) -> None:
    status = data.get("status")
    if isinstance(status, str) and status.strip():
        data["status"] = status.strip().upper()


def _serialize(row) -> dict:
    payload: dict = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if isinstance(value, datetime):
            payload[column.name] = value.isoformat()
        else:
            payload[column.name] = value
    return payload


def _list_rows(
    db: Session,
    model,
    tenant_id: str,
    code_field: str,
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    current_only: bool = True,
) -> list[dict]:
    query = db.query(model).filter(model.tenant_id == tenant_id)
    if repository_id is not None:
        query = query.filter(model.repository_id == repository_id)
    if business_area is not None:
        query = query.filter(model.business_area == business_area)
    if project_code is not None and hasattr(model, "project_code"):
        query = query.filter(model.project_code == project_code)
    if document_type is not None:
        query = query.filter(model.document_type == document_type)
    if status is not None:
        query = query.filter(model.status == status.strip().upper())
    if current_only and hasattr(model, "is_current_version"):
        query = query.filter(model.is_current_version.is_(True))
    rows = query.order_by(
        model.rule_priority.asc(),
        getattr(model, code_field).asc(),
        model.version_no.desc(),
    ).all()
    return [_serialize(row) for row in rows]


def _get_row(db: Session, model, tenant_id: str, id_field: str, row_id: str):
    row = (
        db.query(model)
        .filter(model.tenant_id == tenant_id, getattr(model, id_field) == row_id)
        .first()
    )
    if not row:
        raise ValueError(f"{model.__tablename__} row not found")
    return row


def _create_row(
    db: Session,
    model,
    tenant_id: str,
    id_field: str,
    id_prefix: str,
    request_model,
    actor: str | None,
):
    payload = _model_dump(request_model)
    _normalize_status(payload)
    payload[id_field] = _new_id(id_prefix)
    payload["tenant_id"] = tenant_id
    payload["created_by"] = actor
    payload["modified_by"] = actor
    row = model(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize(row)


def _update_row(
    db: Session,
    model,
    tenant_id: str,
    id_field: str,
    row_id: str,
    request_model,
    actor: str | None,
):
    row = _get_row(db, model, tenant_id, id_field, row_id)
    payload = _model_dump(request_model, exclude_unset=True)
    _normalize_status(payload)
    for key, value in payload.items():
        setattr(row, key, value)
    row.modified_by = actor
    db.commit()
    db.refresh(row)
    return _serialize(row)


def _delete_row(db: Session, model, tenant_id: str, id_field: str, row_id: str) -> None:
    row = _get_row(db, model, tenant_id, id_field, row_id)
    db.delete(row)
    db.commit()


def set_row_status(
    db: Session,
    model,
    tenant_id: str,
    id_field: str,
    row_id: str,
    *,
    status: str,
    actor: str | None,
) -> dict:
    row = _get_row(db, model, tenant_id, id_field, row_id)
    row.status = status.strip().upper()
    row.modified_by = actor
    db.commit()
    db.refresh(row)
    return _serialize(row)


def preview_resolution(
    db: Session,
    model,
    tenant_id: str,
    code_field: str,
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
    document_type: str | None = None,
    as_of: datetime | None = None,
    current_only: bool = True,
    match_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_at = as_of or datetime.now(timezone.utc)
    query = db.query(model).filter(model.tenant_id == tenant_id)
    query = query.filter(model.status == "ACTIVE")
    query = query.filter(model.effective_from <= resolved_at)
    query = query.filter((model.effective_to.is_(None)) | (model.effective_to >= resolved_at))
    if current_only and hasattr(model, "is_current_version"):
        query = query.filter(model.is_current_version.is_(True))

    for field_name, field_value in (match_fields or {}).items():
        if field_value is None or not hasattr(model, field_name):
            continue
        query = query.filter(getattr(model, field_name) == field_value)

    candidates = []
    for row in query.all():
        if row.repository_id not in (None, repository_id):
            continue
        if row.business_area not in (None, business_area):
            continue
        if hasattr(row, "project_code") and row.project_code not in (None, project_code):
            continue
        if row.document_type not in (None, document_type):
            continue
        scope_rank = (
            int(row.repository_id is not None),
            int(row.business_area is not None),
            int(getattr(row, "project_code", None) is not None),
            int(row.document_type is not None),
        )
        candidates.append(
            {
                "row": row,
                "scope_rank": scope_rank,
                "rule_priority": row.rule_priority,
                "version_no": row.version_no,
                "code_value": getattr(row, code_field),
            }
        )

    candidates.sort(
        key=lambda item: (
            -sum(item["scope_rank"]),
            item["rule_priority"],
            -item["version_no"],
            item["code_value"],
        )
    )

    serialized_candidates = []
    for item in candidates:
        payload = _serialize(item["row"])
        payload["_scope_rank"] = {
            "repository_id": item["scope_rank"][0],
            "business_area": item["scope_rank"][1],
            "document_type": item["scope_rank"][2],
            "specificity": sum(item["scope_rank"]),
        }
        serialized_candidates.append(payload)

    return {
        "criteria": {
            "repository_id": repository_id,
            "business_area": business_area,
            "project_code": project_code,
            "document_type": document_type,
            "as_of": resolved_at.isoformat(),
            "current_only": current_only,
            "match_fields": match_fields or {},
        },
        "winner": serialized_candidates[0] if serialized_candidates else None,
        "candidates": serialized_candidates,
    }


def list_record_categories(
    db: Session,
    tenant_id: str,
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    current_only: bool = True,
) -> list[dict]:
    return _list_rows(
        db,
        SymployeeRecordCategory,
        tenant_id,
        "category_code",
        repository_id=repository_id,
        business_area=business_area,
        project_code=project_code,
        document_type=document_type,
        status=status,
        current_only=current_only,
    )


def get_record_category(db: Session, tenant_id: str, record_category_id: str) -> dict:
    return _serialize(_get_row(db, SymployeeRecordCategory, tenant_id, "record_category_id", record_category_id))


def create_record_category(
    db: Session,
    tenant_id: str,
    request: SymployeeRecordCategoryCreate,
    actor: str | None,
) -> dict:
    return _create_row(db, SymployeeRecordCategory, tenant_id, "record_category_id", "SRC", request, actor)


def update_record_category(
    db: Session,
    tenant_id: str,
    record_category_id: str,
    request: SymployeeRecordCategoryUpdate,
    actor: str | None,
) -> dict:
    return _update_row(db, SymployeeRecordCategory, tenant_id, "record_category_id", record_category_id, request, actor)


def delete_record_category(db: Session, tenant_id: str, record_category_id: str) -> None:
    _delete_row(db, SymployeeRecordCategory, tenant_id, "record_category_id", record_category_id)


def list_record_declaration_rules(
    db: Session,
    tenant_id: str,
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    current_only: bool = True,
) -> list[dict]:
    return _list_rows(
        db,
        SymployeeRecordDeclarationRule,
        tenant_id,
        "rule_code",
        repository_id=repository_id,
        business_area=business_area,
        project_code=project_code,
        document_type=document_type,
        status=status,
        current_only=current_only,
    )


def get_record_declaration_rule(db: Session, tenant_id: str, declaration_rule_id: str) -> dict:
    return _serialize(
        _get_row(db, SymployeeRecordDeclarationRule, tenant_id, "declaration_rule_id", declaration_rule_id)
    )


def create_record_declaration_rule(
    db: Session,
    tenant_id: str,
    request: SymployeeRecordDeclarationRuleCreate,
    actor: str | None,
) -> dict:
    return _create_row(
        db,
        SymployeeRecordDeclarationRule,
        tenant_id,
        "declaration_rule_id",
        "SRDR",
        request,
        actor,
    )


def update_record_declaration_rule(
    db: Session,
    tenant_id: str,
    declaration_rule_id: str,
    request: SymployeeRecordDeclarationRuleUpdate,
    actor: str | None,
) -> dict:
    return _update_row(
        db,
        SymployeeRecordDeclarationRule,
        tenant_id,
        "declaration_rule_id",
        declaration_rule_id,
        request,
        actor,
    )


def delete_record_declaration_rule(db: Session, tenant_id: str, declaration_rule_id: str) -> None:
    _delete_row(db, SymployeeRecordDeclarationRule, tenant_id, "declaration_rule_id", declaration_rule_id)


def list_record_lifecycle_rules(
    db: Session,
    tenant_id: str,
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    current_only: bool = True,
) -> list[dict]:
    return _list_rows(
        db,
        SymployeeRecordLifecycleRule,
        tenant_id,
        "rule_code",
        repository_id=repository_id,
        business_area=business_area,
        project_code=project_code,
        document_type=document_type,
        status=status,
        current_only=current_only,
    )


def get_record_lifecycle_rule(db: Session, tenant_id: str, lifecycle_rule_id: str) -> dict:
    return _serialize(_get_row(db, SymployeeRecordLifecycleRule, tenant_id, "lifecycle_rule_id", lifecycle_rule_id))


def create_record_lifecycle_rule(
    db: Session,
    tenant_id: str,
    request: SymployeeRecordLifecycleRuleCreate,
    actor: str | None,
) -> dict:
    return _create_row(
        db,
        SymployeeRecordLifecycleRule,
        tenant_id,
        "lifecycle_rule_id",
        "SRLR",
        request,
        actor,
    )


def update_record_lifecycle_rule(
    db: Session,
    tenant_id: str,
    lifecycle_rule_id: str,
    request: SymployeeRecordLifecycleRuleUpdate,
    actor: str | None,
) -> dict:
    return _update_row(
        db,
        SymployeeRecordLifecycleRule,
        tenant_id,
        "lifecycle_rule_id",
        lifecycle_rule_id,
        request,
        actor,
    )


def delete_record_lifecycle_rule(db: Session, tenant_id: str, lifecycle_rule_id: str) -> None:
    _delete_row(db, SymployeeRecordLifecycleRule, tenant_id, "lifecycle_rule_id", lifecycle_rule_id)


def list_retention_schedules(
    db: Session,
    tenant_id: str,
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    current_only: bool = True,
) -> list[dict]:
    return _list_rows(
        db,
        SymployeeRetentionSchedule,
        tenant_id,
        "schedule_code",
        repository_id=repository_id,
        business_area=business_area,
        project_code=project_code,
        document_type=document_type,
        status=status,
        current_only=current_only,
    )


def get_retention_schedule(db: Session, tenant_id: str, retention_schedule_id: str) -> dict:
    return _serialize(_get_row(db, SymployeeRetentionSchedule, tenant_id, "retention_schedule_id", retention_schedule_id))


def create_retention_schedule(
    db: Session,
    tenant_id: str,
    request: SymployeeRetentionScheduleCreate,
    actor: str | None,
) -> dict:
    return _create_row(
        db,
        SymployeeRetentionSchedule,
        tenant_id,
        "retention_schedule_id",
        "SRS",
        request,
        actor,
    )


def update_retention_schedule(
    db: Session,
    tenant_id: str,
    retention_schedule_id: str,
    request: SymployeeRetentionScheduleUpdate,
    actor: str | None,
) -> dict:
    return _update_row(
        db,
        SymployeeRetentionSchedule,
        tenant_id,
        "retention_schedule_id",
        retention_schedule_id,
        request,
        actor,
    )


def delete_retention_schedule(db: Session, tenant_id: str, retention_schedule_id: str) -> None:
    _delete_row(db, SymployeeRetentionSchedule, tenant_id, "retention_schedule_id", retention_schedule_id)


def list_record_vital_policies(
    db: Session,
    tenant_id: str,
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    current_only: bool = True,
) -> list[dict]:
    return _list_rows(
        db,
        SymployeeRecordVitalPolicy,
        tenant_id,
        "policy_code",
        repository_id=repository_id,
        business_area=business_area,
        project_code=project_code,
        document_type=document_type,
        status=status,
        current_only=current_only,
    )


def get_record_vital_policy(db: Session, tenant_id: str, vital_policy_id: str) -> dict:
    return _serialize(_get_row(db, SymployeeRecordVitalPolicy, tenant_id, "vital_policy_id", vital_policy_id))


def create_record_vital_policy(
    db: Session,
    tenant_id: str,
    request: SymployeeRecordVitalPolicyCreate,
    actor: str | None,
) -> dict:
    return _create_row(
        db,
        SymployeeRecordVitalPolicy,
        tenant_id,
        "vital_policy_id",
        "SRVP",
        request,
        actor,
    )


def update_record_vital_policy(
    db: Session,
    tenant_id: str,
    vital_policy_id: str,
    request: SymployeeRecordVitalPolicyUpdate,
    actor: str | None,
) -> dict:
    return _update_row(
        db,
        SymployeeRecordVitalPolicy,
        tenant_id,
        "vital_policy_id",
        vital_policy_id,
        request,
        actor,
    )


def delete_record_vital_policy(db: Session, tenant_id: str, vital_policy_id: str) -> None:
    _delete_row(db, SymployeeRecordVitalPolicy, tenant_id, "vital_policy_id", vital_policy_id)


def list_record_hold_policies(
    db: Session,
    tenant_id: str,
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    current_only: bool = True,
) -> list[dict]:
    return _list_rows(
        db,
        SymployeeRecordHoldPolicy,
        tenant_id,
        "policy_code",
        repository_id=repository_id,
        business_area=business_area,
        project_code=project_code,
        document_type=document_type,
        status=status,
        current_only=current_only,
    )


def get_record_hold_policy(db: Session, tenant_id: str, hold_policy_id: str) -> dict:
    return _serialize(_get_row(db, SymployeeRecordHoldPolicy, tenant_id, "hold_policy_id", hold_policy_id))


def create_record_hold_policy(
    db: Session,
    tenant_id: str,
    request: SymployeeRecordHoldPolicyCreate,
    actor: str | None,
) -> dict:
    return _create_row(
        db,
        SymployeeRecordHoldPolicy,
        tenant_id,
        "hold_policy_id",
        "SRHP",
        request,
        actor,
    )


def update_record_hold_policy(
    db: Session,
    tenant_id: str,
    hold_policy_id: str,
    request: SymployeeRecordHoldPolicyUpdate,
    actor: str | None,
) -> dict:
    return _update_row(
        db,
        SymployeeRecordHoldPolicy,
        tenant_id,
        "hold_policy_id",
        hold_policy_id,
        request,
        actor,
    )


def delete_record_hold_policy(db: Session, tenant_id: str, hold_policy_id: str) -> None:
    _delete_row(db, SymployeeRecordHoldPolicy, tenant_id, "hold_policy_id", hold_policy_id)


def list_record_disposition_policies(
    db: Session,
    tenant_id: str,
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    current_only: bool = True,
) -> list[dict]:
    return _list_rows(
        db,
        SymployeeRecordDispositionPolicy,
        tenant_id,
        "policy_code",
        repository_id=repository_id,
        business_area=business_area,
        project_code=project_code,
        document_type=document_type,
        status=status,
        current_only=current_only,
    )


def get_record_disposition_policy(db: Session, tenant_id: str, disposition_policy_id: str) -> dict:
    return _serialize(
        _get_row(db, SymployeeRecordDispositionPolicy, tenant_id, "disposition_policy_id", disposition_policy_id)
    )


def create_record_disposition_policy(
    db: Session,
    tenant_id: str,
    request: SymployeeRecordDispositionPolicyCreate,
    actor: str | None,
) -> dict:
    return _create_row(
        db,
        SymployeeRecordDispositionPolicy,
        tenant_id,
        "disposition_policy_id",
        "SRDP",
        request,
        actor,
    )


def update_record_disposition_policy(
    db: Session,
    tenant_id: str,
    disposition_policy_id: str,
    request: SymployeeRecordDispositionPolicyUpdate,
    actor: str | None,
) -> dict:
    return _update_row(
        db,
        SymployeeRecordDispositionPolicy,
        tenant_id,
        "disposition_policy_id",
        disposition_policy_id,
        request,
        actor,
    )


def delete_record_disposition_policy(db: Session, tenant_id: str, disposition_policy_id: str) -> None:
    _delete_row(db, SymployeeRecordDispositionPolicy, tenant_id, "disposition_policy_id", disposition_policy_id)


def list_record_archive_policies(
    db: Session,
    tenant_id: str,
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    current_only: bool = True,
) -> list[dict]:
    return _list_rows(
        db,
        SymployeeRecordArchivePolicy,
        tenant_id,
        "policy_code",
        repository_id=repository_id,
        business_area=business_area,
        project_code=project_code,
        document_type=document_type,
        status=status,
        current_only=current_only,
    )


def get_record_archive_policy(db: Session, tenant_id: str, archive_policy_id: str) -> dict:
    return _serialize(_get_row(db, SymployeeRecordArchivePolicy, tenant_id, "archive_policy_id", archive_policy_id))


def create_record_archive_policy(
    db: Session,
    tenant_id: str,
    request: SymployeeRecordArchivePolicyCreate,
    actor: str | None,
) -> dict:
    return _create_row(
        db,
        SymployeeRecordArchivePolicy,
        tenant_id,
        "archive_policy_id",
        "SRAP",
        request,
        actor,
    )


def update_record_archive_policy(
    db: Session,
    tenant_id: str,
    archive_policy_id: str,
    request: SymployeeRecordArchivePolicyUpdate,
    actor: str | None,
) -> dict:
    return _update_row(
        db,
        SymployeeRecordArchivePolicy,
        tenant_id,
        "archive_policy_id",
        archive_policy_id,
        request,
        actor,
    )


def delete_record_archive_policy(db: Session, tenant_id: str, archive_policy_id: str) -> None:
    _delete_row(db, SymployeeRecordArchivePolicy, tenant_id, "archive_policy_id", archive_policy_id)


def list_record_assignment_rules(
    db: Session,
    tenant_id: str,
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    current_only: bool = True,
) -> list[dict]:
    return _list_rows(
        db,
        SymployeeRecordAssignmentRule,
        tenant_id,
        "rule_code",
        repository_id=repository_id,
        business_area=business_area,
        project_code=project_code,
        document_type=document_type,
        status=status,
        current_only=current_only,
    )


def get_record_assignment_rule(db: Session, tenant_id: str, assignment_rule_id: str) -> dict:
    return _serialize(_get_row(db, SymployeeRecordAssignmentRule, tenant_id, "assignment_rule_id", assignment_rule_id))


def create_record_assignment_rule(
    db: Session,
    tenant_id: str,
    request: SymployeeRecordAssignmentRuleCreate,
    actor: str | None,
) -> dict:
    return _create_row(
        db,
        SymployeeRecordAssignmentRule,
        tenant_id,
        "assignment_rule_id",
        "SRAR",
        request,
        actor,
    )


def update_record_assignment_rule(
    db: Session,
    tenant_id: str,
    assignment_rule_id: str,
    request: SymployeeRecordAssignmentRuleUpdate,
    actor: str | None,
) -> dict:
    return _update_row(
        db,
        SymployeeRecordAssignmentRule,
        tenant_id,
        "assignment_rule_id",
        assignment_rule_id,
        request,
        actor,
    )


def delete_record_assignment_rule(db: Session, tenant_id: str, assignment_rule_id: str) -> None:
    _delete_row(db, SymployeeRecordAssignmentRule, tenant_id, "assignment_rule_id", assignment_rule_id)
