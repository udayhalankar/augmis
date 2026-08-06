from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import MetaData, Table
from sqlalchemy.orm import Session

from app.db_models import Repository, SymployeeDocumentIdentity, SymployeeDocumentVersion
from app.services.symployee_lifecycle_service import (
    apply_record_lifecycle_transition,
    apply_state_transition,
    create_lifecycle_event,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{str(uuid4())[:12].upper()}"


def _table(db: Session, table_name: str) -> Table:
    return Table(
        table_name,
        MetaData(),
        autoload_with=db.get_bind(),
    )


def _require_identity(db: Session, tenant_id: str, identity_id: str) -> SymployeeDocumentIdentity:
    identity = (
        db.query(SymployeeDocumentIdentity)
        .filter(
            SymployeeDocumentIdentity.tenant_id == tenant_id,
            SymployeeDocumentIdentity.identity_id == identity_id,
        )
        .first()
    )
    if not identity:
        raise ValueError("Document identity not found")
    return identity


def _require_version(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    version_id: str | None,
) -> SymployeeDocumentVersion | None:
    if not version_id:
        return None
    version = (
        db.query(SymployeeDocumentVersion)
        .filter(
            SymployeeDocumentVersion.tenant_id == tenant_id,
            SymployeeDocumentVersion.identity_id == identity_id,
            SymployeeDocumentVersion.version_id == version_id,
        )
        .first()
    )
    if not version:
        raise ValueError("Document version not found")
    return version


def _resolve_current_version(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
) -> SymployeeDocumentVersion | None:
    return (
        db.query(SymployeeDocumentVersion)
        .filter(
            SymployeeDocumentVersion.tenant_id == tenant_id,
            SymployeeDocumentVersion.identity_id == identity_id,
        )
        .order_by(
            SymployeeDocumentVersion.is_current_revision.desc(),
            SymployeeDocumentVersion.created_at.desc(),
        )
        .first()
    )


def _active_record_declaration(db: Session, tenant_id: str, identity_id: str):
    declarations = _table(db, "symployee_record_declarations")
    return db.execute(
        declarations.select()
        .where(
            declarations.c.tenant_id == tenant_id,
            declarations.c.identity_id == identity_id,
            declarations.c.record_status.in_(["DECLARED_RECORD", "UNDER_LEGAL_HOLD", "ARCHIVED", "PERMANENT"]),
        )
        .order_by(declarations.c.declared_at.desc(), declarations.c.created_at.desc())
        .limit(1)
    ).fetchone()


def _latest_record_declaration(db: Session, tenant_id: str, identity_id: str):
    declarations = _table(db, "symployee_record_declarations")
    return db.execute(
        declarations.select()
        .where(
            declarations.c.tenant_id == tenant_id,
            declarations.c.identity_id == identity_id,
        )
        .order_by(declarations.c.declared_at.desc(), declarations.c.created_at.desc())
        .limit(1)
    ).fetchone()


def _governed_record_statuses() -> set[str]:
    return {"DECLARED_RECORD", "UNDER_LEGAL_HOLD", "ARCHIVED", "PERMANENT"}


def _find_active_legal_hold(db: Session, tenant_id: str, identity_id: str, hold_code: str | None = None):
    holds = _table(db, "symployee_record_legal_holds")
    query = holds.select().where(
        holds.c.tenant_id == tenant_id,
        holds.c.identity_id == identity_id,
        holds.c.hold_status == "ACTIVE",
    )
    if hold_code:
        query = query.where(holds.c.hold_code == hold_code)
    return db.execute(
        query.order_by(holds.c.placed_at.desc(), holds.c.created_at.desc()).limit(1)
    ).fetchone()


def _resolve_scope_candidates(identity: SymployeeDocumentIdentity) -> list[tuple[str, str | None]]:
    return [
        ("repository", identity.repository_id),
        ("project", identity.project_code),
        ("document_type", identity.document_type_code),
        ("tenant", None),
    ]


def _resolve_repository_business_area(
    db: Session,
    tenant_id: str,
    repository_id: str | None,
) -> str | None:
    if not repository_id:
        return None
    repository = (
        db.query(Repository)
        .filter(
            Repository.tenant_id == tenant_id,
            Repository.repository_id == repository_id,
        )
        .first()
    )
    return repository.business_area if repository else None


def _resolve_config_row(
    db: Session,
    tenant_id: str,
    *,
    identity: SymployeeDocumentIdentity,
    table_name: str,
    extra_filters: dict[str, object] | None = None,
) -> dict | None:
    table = _table(db, table_name)
    query = table.select().where(
        table.c.tenant_id == tenant_id,
        table.c.status == "ACTIVE",
        table.c.is_current_version.is_(True),
    )
    for key, value in (extra_filters or {}).items():
        column = getattr(table.c, key)
        if isinstance(value, (list, tuple, set)):
            values = [item for item in value if item is not None]
            if not values:
                continue
            query = query.where(column.in_(values))
        else:
            query = query.where(column == value)

    rows = db.execute(query).fetchall()
    if not rows:
        return None

    business_area = _resolve_repository_business_area(db, tenant_id, identity.repository_id)
    matches: list[tuple[int, int, int, datetime, datetime, object]] = []
    for row in rows:
        if row.repository_id and row.repository_id != identity.repository_id:
            continue
        if row.business_area and row.business_area != business_area:
            continue
        if hasattr(row, "project_code") and row.project_code and row.project_code != identity.project_code:
            continue
        if row.document_type and row.document_type != identity.document_type_code:
            continue
        specificity = sum(
            1
            for value in (
                row.repository_id,
                row.business_area,
                getattr(row, "project_code", None),
                row.document_type,
            )
            if value
        )
        rule_priority = int(row.rule_priority or 100)
        version_no = int(row.version_no or 1)
        effective_from = row.effective_from or datetime(1970, 1, 1, tzinfo=UTC)
        created_at = row.created_at or datetime(1970, 1, 1, tzinfo=UTC)
        matches.append((specificity, -rule_priority, version_no, effective_from, created_at, row))

    if not matches:
        return None

    selected = sorted(
        matches,
        key=lambda item: (
            item[0],
            item[1],
            item[2],
            item[3],
            item[4],
        ),
        reverse=True,
    )[0][5]
    return _serialize_row(selected)


def _add_retention_period(started_at: datetime, value: int, unit: str) -> datetime:
    normalized_unit = (unit or "YEARS").upper()
    if normalized_unit == "DAYS":
        return started_at + timedelta(days=value)
    if normalized_unit == "MONTHS":
        return started_at + timedelta(days=value * 30)
    return started_at + timedelta(days=value * 365)


def _serialize_row(row) -> dict:
    return {
        key: (
            value.isoformat()
            if isinstance(value, datetime)
            else value
        )
        for key, value in row._mapping.items()
    }


def _normalize_hold_category(hold_category: str | None) -> str:
    normalized = (hold_category or "OTHER").strip().upper()
    if normalized in {"LEGAL", "VALIDATION", "RECORDS", "OPERATIONAL", "OTHER"}:
        return normalized
    raise ValueError("Unsupported hold category")


def _resolve_record_declaration_rule(
    db: Session,
    tenant_id: str,
    *,
    identity: SymployeeDocumentIdentity,
    record_category: str,
) -> dict | None:
    return _resolve_config_row(
        db,
        tenant_id,
        identity=identity,
        table_name="symployee_record_declaration_rules",
        extra_filters={"record_category_code": record_category},
    )


def _resolve_record_lifecycle_rule(
    db: Session,
    tenant_id: str,
    *,
    identity: SymployeeDocumentIdentity,
    record_category: str,
) -> dict | None:
    return _resolve_config_row(
        db,
        tenant_id,
        identity=identity,
        table_name="symployee_record_lifecycle_rules",
        extra_filters={"record_category_code": [record_category, None]},
    )


def _resolve_retention_schedule_config(
    db: Session,
    tenant_id: str,
    *,
    identity: SymployeeDocumentIdentity,
    record_category: str,
) -> dict | None:
    return _resolve_config_row(
        db,
        tenant_id,
        identity=identity,
        table_name="symployee_retention_schedules",
        extra_filters={"record_category_code": [record_category, None]},
    )


def _resolve_vital_policy(
    db: Session,
    tenant_id: str,
    *,
    identity: SymployeeDocumentIdentity,
    record_category: str,
) -> dict | None:
    return _resolve_config_row(
        db,
        tenant_id,
        identity=identity,
        table_name="symployee_record_vital_policies",
        extra_filters={"record_category_code": [record_category, None]},
    )


def _criteria_match(
    evaluation_context: dict[str, Any],
    criteria: dict[str, Any] | None,
) -> bool:
    if not criteria:
        return False
    return all(
        _match_rule_criterion(evaluation_context.get(field_name), expected)
        for field_name, expected in dict(criteria).items()
    )


def _resolve_vital_runtime(
    *,
    vital_policy: dict[str, Any] | None,
    evaluation_context: dict[str, Any],
    declared_at: datetime | None = None,
) -> tuple[str, dict[str, Any]]:
    if not vital_policy:
        return "NON_VITAL", {}

    classification_mode = str(vital_policy.get("classification_mode") or "RULE_DRIVEN").strip().upper()
    review_required = bool(vital_policy.get("review_required"))
    criteria_matched = _criteria_match(evaluation_context, vital_policy.get("criteria_json") or {})
    candidate_flag = bool(vital_policy.get("default_vital_flag")) or criteria_matched

    if not candidate_flag:
        vital_status = "NON_VITAL"
    elif classification_mode == "MANUAL_APPROVAL":
        vital_status = "VITAL_CANDIDATE"
    elif review_required:
        vital_status = "VITAL_UNDER_REVIEW"
    else:
        vital_status = "VITAL"

    review_interval_days = vital_policy.get("review_interval_days")
    review_due_at = None
    if review_interval_days and declared_at and vital_status in {"VITAL", "VITAL_UNDER_REVIEW"}:
        review_due_at = declared_at + timedelta(days=int(review_interval_days))

    config_payload = dict(vital_policy.get("config_payload_json") or {})
    profile = {
        "vital_policy_id": vital_policy.get("vital_policy_id"),
        "policy_code": vital_policy.get("policy_code"),
        "classification_mode": classification_mode,
        "criteria_matched": criteria_matched,
        "default_vital_flag": bool(vital_policy.get("default_vital_flag")),
        "review_required": review_required,
        "review_role_code": vital_policy.get("review_role_code"),
        "review_interval_days": review_interval_days,
        "review_due_at": review_due_at.isoformat() if review_due_at else None,
        "recovery_metadata": dict(config_payload.get("recovery_metadata") or {}),
        "protection_metadata": dict(config_payload.get("protection_metadata") or {}),
    }
    return vital_status, profile


def _resolve_assignment_rule(
    db: Session,
    tenant_id: str,
    *,
    identity: SymployeeDocumentIdentity,
    record_category: str,
    assignment_context: str = "DECLARATION",
) -> dict | None:
    filters: dict[str, object] = {
        "assignment_context": [assignment_context],
    }
    if record_category:
        filters["record_category_code"] = [record_category, None]
    return _resolve_config_row(
        db,
        tenant_id,
        identity=identity,
        table_name="symployee_record_assignment_rules",
        extra_filters=filters,
    )


def _build_assignment_routing(
    assignment_rule: dict[str, Any] | None,
) -> dict[str, Any]:
    if not assignment_rule:
        return {}
    logic = dict(assignment_rule.get("assignment_logic_json") or {})
    owner_role_code = assignment_rule.get("owner_role_code")
    performer_role_code = assignment_rule.get("performer_role_code")
    approver_role_code = assignment_rule.get("approver_role_code")
    routing = {
        "assignment_rule_id": assignment_rule.get("assignment_rule_id"),
        "assignment_context": assignment_rule.get("assignment_context"),
        "rule_code": assignment_rule.get("rule_code"),
        "rule_name": assignment_rule.get("rule_name"),
        "repository_id": assignment_rule.get("repository_id"),
        "business_area": assignment_rule.get("business_area"),
        "project_code": assignment_rule.get("project_code"),
        "document_type": assignment_rule.get("document_type"),
        "record_category_code": assignment_rule.get("record_category_code"),
        "owner_role_code": owner_role_code,
        "performer_role_code": performer_role_code,
        "approver_role_code": approver_role_code,
        "escalation_role_code": assignment_rule.get("escalation_role_code"),
        "fallback_role_code": assignment_rule.get("fallback_role_code"),
        "declaration_owner_role_code": logic.get("declaration_owner_role_code") or owner_role_code,
        "records_officer_role_code": logic.get("records_officer_role_code") or performer_role_code or owner_role_code,
        "legal_approver_role_code": logic.get("legal_approver_role_code"),
        "business_approver_role_code": logic.get("business_approver_role_code"),
        "archive_approver_role_code": logic.get("archive_approver_role_code") or approver_role_code,
        "disposition_executor_role_code": logic.get("disposition_executor_role_code") or performer_role_code,
        "assignment_logic_json": logic,
    }
    return routing


def _resolve_hold_policy(
    db: Session,
    tenant_id: str,
    *,
    identity: SymployeeDocumentIdentity,
    record_category: str | None,
    hold_category: str,
) -> dict | None:
    filters: dict[str, object] = {"hold_category": hold_category}
    if record_category:
        filters["record_category_code"] = [record_category, None]
    return _resolve_config_row(
        db,
        tenant_id,
        identity=identity,
        table_name="symployee_record_hold_policies",
        extra_filters=filters,
    )


def _resolve_disposition_policy(
    db: Session,
    tenant_id: str,
    *,
    identity: SymployeeDocumentIdentity,
    record_category: str,
    disposition_type: str,
) -> dict | None:
    return _resolve_config_row(
        db,
        tenant_id,
        identity=identity,
        table_name="symployee_record_disposition_policies",
        extra_filters={
            "record_category_code": [record_category, None],
            "allowed_outcome": [disposition_type, "MIXED"],
        },
    )


def _resolve_archive_policy(
    db: Session,
    tenant_id: str,
    *,
    identity: SymployeeDocumentIdentity,
    record_category: str,
) -> dict | None:
    return _resolve_config_row(
        db,
        tenant_id,
        identity=identity,
        table_name="symployee_record_archive_policies",
        extra_filters={"record_category_code": [record_category, None]},
    )    


def _resolve_retention_schedule_by_id(
    db: Session,
    tenant_id: str,
    *,
    retention_schedule_id: str | None,
) -> dict | None:
    if not retention_schedule_id:
        return None
    schedules = _table(db, "symployee_retention_schedules")
    row = db.execute(
        schedules.select().where(
            schedules.c.tenant_id == tenant_id,
            schedules.c.retention_schedule_id == retention_schedule_id,
        )
    ).fetchone()
    return _serialize_row(row) if row else None


def _resolve_disposition_policy_by_code(
    db: Session,
    tenant_id: str,
    *,
    identity: SymployeeDocumentIdentity,
    record_category: str,
    policy_code: str | None,
) -> dict | None:
    if not policy_code:
        return None
    return _resolve_config_row(
        db,
        tenant_id,
        identity=identity,
        table_name="symployee_record_disposition_policies",
        extra_filters={
            "record_category_code": [record_category, None],
            "policy_code": policy_code,
        },
    )


def _resolve_archive_policy_by_id(
    db: Session,
    tenant_id: str,
    *,
    archive_policy_id: str | None,
) -> dict | None:
    if not archive_policy_id:
        return None
    policies = _table(db, "symployee_record_archive_policies")
    row = db.execute(
        policies.select().where(
            policies.c.tenant_id == tenant_id,
            policies.c.archive_policy_id == archive_policy_id,
        )
    ).fetchone()
    return _serialize_row(row) if row else None


def _resolve_disposition_type_from_policy(
    *,
    disposition_policy: dict[str, Any] | None,
    archive_policy: dict[str, Any] | None,
) -> str:
    allowed_outcome = str((disposition_policy or {}).get("allowed_outcome") or "MIXED").upper()
    if allowed_outcome in {"ARCHIVE", "DESTROY", "REVIEW_EXTEND"}:
        return allowed_outcome
    if archive_policy and bool(archive_policy.get("transfer_required")):
        return "ARCHIVE"
    return "DESTROY"


def _resolve_retention_anchor_at(
    declaration,
    *,
    retention_schedule: dict[str, Any] | None,
) -> datetime | None:
    start_event = str((retention_schedule or {}).get("retention_start_event") or "DECLARED").upper()
    if start_event in {"DECLARED", "DECLARATION", "DECLARED_RECORD"}:
        return declaration.declared_at
    if start_event in {"DECLARED_INACTIVE", "INACTIVE", "INACTIVE_FROM"}:
        return getattr(declaration, "inactive_from", None)
    if start_event in {"ACTIVE", "ACTIVE_FROM"}:
        return getattr(declaration, "active_from", None) or declaration.declared_at
    if start_event == "LAST_ACTIVITY_DATE":
        return (
            getattr(declaration, "modified_at", None)
            or getattr(declaration, "inactive_from", None)
            or getattr(declaration, "active_from", None)
            or declaration.declared_at
        )
    return declaration.declared_at


def _resolve_review_due_at(
    *,
    retention_schedule: dict[str, Any] | None,
    eligibility_at: datetime | None,
) -> datetime | None:
    if not retention_schedule or not bool(retention_schedule.get("review_required")):
        return None
    if not eligibility_at:
        return None
    offset_value = retention_schedule.get("review_offset_value")
    offset_unit = retention_schedule.get("review_offset_unit")
    if offset_value in (None, "", 0, "0") or not offset_unit:
        return eligibility_at
    return _add_retention_period(eligibility_at, -int(offset_value), str(offset_unit))


def _find_active_hold_rows(db: Session, tenant_id: str, identity_id: str) -> list[Any]:
    holds = _table(db, "symployee_record_legal_holds")
    rows = db.execute(
        holds.select().where(
            holds.c.tenant_id == tenant_id,
            holds.c.identity_id == identity_id,
            holds.c.hold_status == "ACTIVE",
        )
    ).fetchall()
    return list(rows)


def _find_open_disposition_case(db: Session, tenant_id: str, identity_id: str):
    cases = _table(db, "symployee_disposition_cases")
    return db.execute(
        cases.select()
        .where(
            cases.c.tenant_id == tenant_id,
            cases.c.identity_id == identity_id,
            cases.c.case_status.not_in(["COMPLETED", "CANCELLED"]),
        )
        .order_by(cases.c.requested_at.desc(), cases.c.created_at.desc())
        .limit(1)
    ).fetchone()


def _find_disposition_case(db: Session, tenant_id: str, disposition_case_id: str):
    cases = _table(db, "symployee_disposition_cases")
    return db.execute(
        cases.select().where(
            cases.c.tenant_id == tenant_id,
            cases.c.disposition_case_id == disposition_case_id,
        )
    ).fetchone()


def _find_open_archive_transfer(db: Session, tenant_id: str, identity_id: str):
    transfers = _table(db, "symployee_archive_transfers")
    return db.execute(
        transfers.select()
        .where(
            transfers.c.tenant_id == tenant_id,
            transfers.c.identity_id == identity_id,
            transfers.c.transfer_status.not_in(["COMPLETED", "CANCELLED"]),
        )
        .order_by(transfers.c.requested_at.desc(), transfers.c.created_at.desc())
        .limit(1)
    ).fetchone()


def _find_archive_transfer(db: Session, tenant_id: str, archive_transfer_id: str):
    transfers = _table(db, "symployee_archive_transfers")
    return db.execute(
        transfers.select().where(
            transfers.c.tenant_id == tenant_id,
            transfers.c.archive_transfer_id == archive_transfer_id,
        )
    ).fetchone()


def _resolve_hold_effects(
    db: Session,
    tenant_id: str,
    *,
    active_holds: list[Any],
) -> dict[str, Any]:
    policies = _table(db, "symployee_record_hold_policies")
    blocks_disposition = False
    blocks_archive_transfer = False
    hold_ids: list[str] = []
    categories: list[str] = []
    for hold in active_holds:
        hold_ids.append(hold.legal_hold_id)
        category = str(getattr(hold, "hold_category", None) or "OTHER").upper()
        categories.append(category)
        policy = None
        if getattr(hold, "hold_policy_id", None):
            policy = db.execute(
                policies.select().where(
                    policies.c.tenant_id == tenant_id,
                    policies.c.hold_policy_id == hold.hold_policy_id,
                )
            ).fetchone()
        if policy:
            blocks_disposition = blocks_disposition or bool(policy.blocks_disposition)
            blocks_archive_transfer = blocks_archive_transfer or bool(policy.blocks_archive_transfer)
        elif category == "LEGAL":
            blocks_disposition = True
            blocks_archive_transfer = True
    return {
        "active_hold_ids": hold_ids,
        "active_hold_categories": categories,
        "blocks_disposition": blocks_disposition,
        "blocks_archive_transfer": blocks_archive_transfer,
    }


def _resolve_initial_activity_stage(
    lifecycle_transition: dict | None,
) -> str | None:
    ending_state = dict((lifecycle_transition or {}).get("ending_state") or {})
    return ending_state.get("document_lifecycle_stage")


def _activity_fields_from_transition(
    lifecycle_transition: dict | None,
    *,
    previous_active_from: datetime | None = None,
) -> dict[str, Any]:
    if not lifecycle_transition:
        return {}
    ending_state = dict(lifecycle_transition.get("ending_state") or {})
    stage = ending_state.get("document_lifecycle_stage")
    events = list(lifecycle_transition.get("events") or [])
    transition_event = next(
        (
            event
            for event in reversed(events)
            if event.get("state_dimension") == "document_lifecycle_stage"
        ),
        None,
    )
    event_at = None
    if transition_event and transition_event.get("created_at"):
        event_at = datetime.fromisoformat(str(transition_event["created_at"]))
    metadata = dict((transition_event or {}).get("metadata_json") or {})

    if stage == "ACTIVE":
        return {
            "record_stage": "ACTIVE",
            "active_from": previous_active_from or event_at or _now(),
            "inactive_from": None,
            "inactive_reason_code": None,
            "inactive_reason": None,
        }
    if stage == "INACTIVE":
        return {
            "record_stage": "INACTIVE",
            "active_from": previous_active_from,
            "inactive_from": event_at or _now(),
            "inactive_reason_code": metadata.get("inactive_reason_code"),
            "inactive_reason": metadata.get("inactive_reason_code"),
        }
    if stage == "ARCHIVED":
        return {
            "record_stage": "ARCHIVED",
            "active_from": previous_active_from,
            "inactive_from": event_at or _now(),
            "inactive_reason_code": metadata.get("inactive_reason_code") or "ARCHIVED",
            "inactive_reason": metadata.get("inactive_reason_code") or "ARCHIVED",
        }
    return {}


def _sync_declaration_activity_fields(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    lifecycle_transition: dict | None,
) -> dict[str, Any]:
    if not lifecycle_transition:
        return {}
    declarations = _table(db, "symployee_record_declarations")
    existing = _latest_record_declaration(db, tenant_id, identity_id)
    if not existing:
        return {}
    updates = _activity_fields_from_transition(
        lifecycle_transition,
        previous_active_from=getattr(existing, "active_from", None),
    )
    if not updates:
        return {}
    db.execute(
        declarations.update()
        .where(
            declarations.c.tenant_id == tenant_id,
            declarations.c.record_declaration_id == existing.record_declaration_id,
        )
        .values(
            **updates,
            modified_at=_now(),
        )
    )
    return updates


def _candidate_record_statuses() -> set[str]:
    return {
        "RECORD_CANDIDATE",
        "DECLARED_RECORD",
        "UNDER_LEGAL_HOLD",
        "ARCHIVED",
        "PERMANENT",
    }


def _build_declaration_context(
    db: Session,
    tenant_id: str,
    *,
    identity: SymployeeDocumentIdentity,
    version: SymployeeDocumentVersion | None,
    context_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "identity_id": identity.identity_id,
        "repository_id": identity.repository_id,
        "canonical_document_number": identity.canonical_document_number,
        "title": identity.title,
        "document_type_code": identity.document_type_code,
        "discipline_code": identity.discipline_code,
        "project_code": identity.project_code,
        "originator_code": identity.originator_code,
        "document_lifecycle_stage": identity.document_lifecycle_stage,
        "review_status": identity.review_status,
        "issue_status": identity.issue_status,
        "record_status": identity.record_status,
        "retention_status": identity.retention_status,
        "disposition_status": identity.disposition_status,
        "security_status": identity.security_status,
        "business_area": _resolve_repository_business_area(db, tenant_id, identity.repository_id),
    }
    if version:
        context.update(
            {
                "version_id": version.version_id,
                "revision_code": version.revision_code,
                "revision_status": version.revision_status,
                "issue_status": version.issue_status or context.get("issue_status"),
                "version_label": version.version_label,
                "file_name": version.file_name,
                "file_extension": version.file_extension,
                "mime_type": version.mime_type,
                "file_hash": version.file_hash,
                "page_count": version.page_count,
                "version_status": version.status,
            }
        )
        for key, value in dict(version.metadata_json or {}).items():
            context[f"metadata.{key}"] = value
            context.setdefault(key, value)
    for key, value in dict(context_overrides or {}).items():
        context[key] = value
    return context


def _match_rule_criterion(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        if "exists" in expected:
            return (actual is not None) is bool(expected["exists"])
        if "eq" in expected:
            return actual == expected["eq"]
        if "in" in expected:
            return actual in list(expected["in"] or [])
        if "contains" in expected:
            if isinstance(actual, str):
                return str(expected["contains"]) in actual
            if isinstance(actual, (list, tuple, set)):
                return expected["contains"] in actual
            if isinstance(actual, dict):
                return expected["contains"] in actual.keys()
            return False
        return False
    if isinstance(expected, (list, tuple, set)):
        return actual in expected
    return actual == expected


def _resolve_rule_target_status(rule: dict[str, Any], trigger_event: str) -> str | None:
    trigger = (trigger_event or "").strip().upper()
    candidate_trigger = str(rule.get("candidate_trigger_event") or "").strip().upper()
    declaration_trigger = str(rule.get("declaration_trigger_event") or "").strip().upper()
    declaration_mode = str(rule.get("declaration_mode") or "CANDIDATE_FIRST").strip().upper()

    if trigger and trigger == declaration_trigger:
        return "DECLARED_RECORD"
    if trigger and trigger == candidate_trigger:
        if declaration_mode in {"DIRECT_DECLARE", "DIRECT_DECLARATION", "DIRECT", "AUTO_DECLARE", "DECLARE_IMMEDIATELY"}:
            return "DECLARED_RECORD"
        return "RECORD_CANDIDATE"
    return None


def _list_matching_declaration_rules(
    db: Session,
    tenant_id: str,
    *,
    identity: SymployeeDocumentIdentity,
    evaluation_context: dict[str, Any],
    trigger_event: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    table = _table(db, "symployee_record_declaration_rules")
    now = _now()
    rows = db.execute(
        table.select().where(
            table.c.tenant_id == tenant_id,
            table.c.status == "ACTIVE",
            table.c.is_current_version.is_(True),
            table.c.effective_from <= now,
            (table.c.effective_to.is_(None) | (table.c.effective_to >= now)),
        )
    ).fetchall()

    business_area = _resolve_repository_business_area(db, tenant_id, identity.repository_id)
    traces: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None

    for row in rows:
        if row.repository_id and row.repository_id != identity.repository_id:
            continue
        if row.business_area and row.business_area != business_area:
            continue
        if row.document_type and row.document_type != identity.document_type_code:
            continue

        rule = _serialize_row(row)
        target_status = _resolve_rule_target_status(rule, trigger_event)
        criteria = dict(rule.get("matching_criteria_json") or {})
        criteria_results = []
        matches_criteria = True
        for field_name, expected in criteria.items():
            actual = evaluation_context.get(field_name)
            passed = _match_rule_criterion(actual, expected)
            criteria_results.append(
                {
                    "field": field_name,
                    "expected": expected,
                    "actual": actual,
                    "matched": passed,
                }
            )
            if not passed:
                matches_criteria = False

        specificity = sum(1 for value in (row.repository_id, row.business_area, row.document_type) if value)
        trace = {
            "declaration_rule_id": row.declaration_rule_id,
            "rule_code": row.rule_code,
            "rule_name": row.rule_name,
            "record_category_code": row.record_category_code,
            "declaration_mode": row.declaration_mode,
            "trigger_matched": target_status is not None,
            "candidate_trigger_event": row.candidate_trigger_event,
            "declaration_trigger_event": row.declaration_trigger_event,
            "target_record_status": target_status,
            "matches_criteria": matches_criteria,
            "criteria_results": criteria_results,
            "specificity": specificity,
            "rule_priority": row.rule_priority,
        }
        traces.append(trace)
        if target_status is None or not matches_criteria:
            continue

        candidate = {
            "rule": rule,
            "trace": trace,
            "sort_key": (
                specificity,
                -(int(row.rule_priority or 100)),
                int(row.version_no or 1),
                row.effective_from or datetime(1970, 1, 1, tzinfo=UTC),
                row.created_at or datetime(1970, 1, 1, tzinfo=UTC),
            ),
        }
        if selected is None or candidate["sort_key"] > selected["sort_key"]:
            selected = candidate

    return traces, selected


def _merge_declaration_metadata(
    *,
    existing_metadata: dict[str, Any] | None,
    execution_log: dict[str, Any],
    declaration_rule: dict[str, Any] | None,
    lifecycle_rule: dict[str, Any] | None,
    retention_schedule: dict[str, Any] | None,
    vital_policy: dict[str, Any] | None,
    vital_profile: dict[str, Any] | None,
    assignment_rule: dict[str, Any] | None,
    metadata_json: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        **dict(existing_metadata or {}),
        "config_linkage": {
            "declaration_rule_id": declaration_rule["declaration_rule_id"] if declaration_rule else None,
            "lifecycle_rule_id": lifecycle_rule["lifecycle_rule_id"] if lifecycle_rule else None,
            "retention_schedule_id": retention_schedule["retention_schedule_id"] if retention_schedule else None,
            "vital_policy_id": vital_policy["vital_policy_id"] if vital_policy else None,
            "assignment_rule_id": assignment_rule["assignment_rule_id"] if assignment_rule else None,
            },
            "declaration_engine": execution_log,
            "vital_profile": dict(vital_profile or {}),
            **(metadata_json or {}),
        }


def _persist_record_declaration(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    version_id: str | None,
    record_category: str,
    record_status: str,
    vital_status: str | None,
    owner_user_id: str | None,
    declaration_reason: str,
    source_event_id: str,
    declaration_rule: dict[str, Any] | None,
    lifecycle_rule: dict[str, Any] | None,
    retention_schedule: dict[str, Any] | None,
    metadata_json: dict[str, Any],
    actor: str | None,
    record_stage: str | None = None,
    active_from: datetime | None = None,
    inactive_from: datetime | None = None,
    inactive_reason_code: str | None = None,
    inactive_reason: str | None = None,
) -> str:
    declarations = _table(db, "symployee_record_declarations")
    existing = _latest_record_declaration(db, tenant_id, identity_id)
    now = _now()
    if existing and existing.record_status in _candidate_record_statuses():
        db.execute(
            declarations.update()
            .where(
                declarations.c.tenant_id == tenant_id,
                declarations.c.record_declaration_id == existing.record_declaration_id,
            )
            .values(
                version_id=version_id,
                record_category=record_category,
                record_status=record_status,
                record_stage=record_stage,
                active_from=active_from,
                inactive_from=inactive_from,
                inactive_reason_code=inactive_reason_code,
                vital_status=vital_status,
                inactive_reason=inactive_reason,
                owner_user_id=owner_user_id or existing.owner_user_id,
                declared_at=now,
                declared_by=actor,
                declaration_reason=declaration_reason or None,
                source_event_id=source_event_id,
                declaration_rule_id=(declaration_rule["declaration_rule_id"] if declaration_rule else None),
                lifecycle_rule_id=(lifecycle_rule["lifecycle_rule_id"] if lifecycle_rule else None),
                retention_schedule_id=(retention_schedule["retention_schedule_id"] if retention_schedule else None),
                metadata_json=metadata_json,
                modified_by=actor,
                modified_at=now,
            )
        )
        return existing.record_declaration_id

    record_declaration_id = _new_id("SRD")
    db.execute(
        declarations.insert().values(
            record_declaration_id=record_declaration_id,
            tenant_id=tenant_id,
            identity_id=identity_id,
            version_id=version_id,
            record_category=record_category,
            record_status=record_status,
            record_stage=record_stage,
            active_from=active_from,
            inactive_from=inactive_from,
            inactive_reason_code=inactive_reason_code,
            vital_status=vital_status,
            inactive_reason=inactive_reason,
            owner_user_id=owner_user_id,
            declared_at=now,
            declared_by=actor,
            declaration_reason=declaration_reason or None,
            source_event_id=source_event_id,
            declaration_rule_id=(declaration_rule["declaration_rule_id"] if declaration_rule else None),
            lifecycle_rule_id=(lifecycle_rule["lifecycle_rule_id"] if lifecycle_rule else None),
            retention_schedule_id=(retention_schedule["retention_schedule_id"] if retention_schedule else None),
            metadata_json=metadata_json,
            created_by=actor,
            created_at=now,
            modified_by=actor,
            modified_at=now,
        )
    )
    return record_declaration_id


def evaluate_record_declaration(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    version_id: str | None,
    trigger_event: str,
    dry_run: bool = True,
    performed_by: str | None = None,
    evaluation_reason: str = "",
    context_overrides_json: dict[str, Any] | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    identity = _require_identity(db, tenant_id, identity_id)
    version = _require_version(db, tenant_id, identity_id=identity_id, version_id=version_id)
    evaluation_context = _build_declaration_context(
        db,
        tenant_id,
        identity=identity,
        version=version,
        context_overrides=context_overrides_json,
    )
    rule_traces, selected = _list_matching_declaration_rules(
        db,
        tenant_id,
        identity=identity,
        evaluation_context=evaluation_context,
        trigger_event=trigger_event,
    )

    selected_rule = selected["rule"] if selected else None
    selected_trace = selected["trace"] if selected else None
    target_record_status = selected_trace["target_record_status"] if selected_trace else "NON_RECORD"
    classification = target_record_status
    record_category = selected_rule["record_category_code"] if selected_rule else None
    lifecycle_rule = (
        _resolve_record_lifecycle_rule(db, tenant_id, identity=identity, record_category=record_category)
        if record_category
        else None
    )
    retention_schedule = (
        _resolve_retention_schedule_config(db, tenant_id, identity=identity, record_category=record_category)
        if record_category
        else None
    )
    vital_policy = (
        _resolve_vital_policy(db, tenant_id, identity=identity, record_category=record_category)
        if record_category
        else None
    )
    assignment_rule = (
        _resolve_assignment_rule(db, tenant_id, identity=identity, record_category=record_category)
        if record_category
        else None
    )
    workflow_routing = _build_assignment_routing(assignment_rule)
    vital_status = None
    vital_profile: dict[str, Any] = {}
    if record_category:
        vital_status, vital_profile = _resolve_vital_runtime(
            vital_policy=vital_policy,
            evaluation_context=evaluation_context,
        )

    latest_declaration = _latest_record_declaration(db, tenant_id, identity_id)
    if latest_declaration and latest_declaration.record_status in {"DECLARED_RECORD", "UNDER_LEGAL_HOLD", "ARCHIVED", "PERMANENT"} and target_record_status == "RECORD_CANDIDATE":
        target_record_status = latest_declaration.record_status
        classification = target_record_status

    execution_log = {
        "evaluated_at": _now().isoformat(),
        "trigger_event": trigger_event,
        "dry_run": dry_run,
        "evaluation_reason": evaluation_reason,
        "selected_rule": selected_trace,
        "resolved_links": {
            "declaration_rule_id": selected_rule["declaration_rule_id"] if selected_rule else None,
            "lifecycle_rule_id": lifecycle_rule["lifecycle_rule_id"] if lifecycle_rule else None,
            "retention_schedule_id": retention_schedule["retention_schedule_id"] if retention_schedule else None,
            "vital_policy_id": vital_policy["vital_policy_id"] if vital_policy else None,
            "assignment_rule_id": assignment_rule["assignment_rule_id"] if assignment_rule else None,
        },
        "owner_role_code": assignment_rule["owner_role_code"] if assignment_rule else None,
        "workflow_routing": workflow_routing,
        "rule_trace": rule_traces,
    }

    result: dict[str, Any] = {
        "identity_id": identity.identity_id,
        "version_id": version.version_id if version else None,
        "trigger_event": trigger_event,
        "dry_run": dry_run,
        "classification": classification,
        "target_record_status": target_record_status,
        "record_category": record_category,
        "owner_user_id": performed_by if record_category else None,
        "owner_role_code": assignment_rule["owner_role_code"] if assignment_rule else None,
        "workflow_routing": workflow_routing,
        "vital_status": vital_status,
        "vital_profile": vital_profile,
        "declaration_rule_id": selected_rule["declaration_rule_id"] if selected_rule else None,
        "lifecycle_rule_id": lifecycle_rule["lifecycle_rule_id"] if lifecycle_rule else None,
        "retention_schedule_id": retention_schedule["retention_schedule_id"] if retention_schedule else None,
        "vital_policy_id": vital_policy["vital_policy_id"] if vital_policy else None,
        "assignment_rule_id": assignment_rule["assignment_rule_id"] if assignment_rule else None,
        "matched_rule_count": sum(1 for item in rule_traces if item["trigger_matched"] and item["matches_criteria"]),
        "rule_trace": rule_traces,
        "execution_log": execution_log,
    }
    if dry_run:
        return result

    if target_record_status == "NON_RECORD":
        lifecycle = apply_state_transition(
            db,
            tenant_id,
            identity_id=identity.identity_id,
            version_id=version.version_id if version else None,
            state_dimension="record_status",
            new_state="NON_RECORD",
            event_type="RECORD_CLASSIFIED_NON_RECORD",
            performed_by=performed_by,
            reason=evaluation_reason,
            metadata_json={
                "declaration_engine": execution_log,
                **(metadata_json or {}),
            },
        )
        db.commit()
        return {
            **result,
            "source_event_id": lifecycle["event_id"],
            "record_declaration_id": None,
            "executed": True,
        }

    lifecycle_event_type = (
        "RECORD_DECLARED_BY_RULE"
        if target_record_status == "DECLARED_RECORD"
        else "RECORD_CANDIDATE_IDENTIFIED"
    )
    lifecycle = apply_state_transition(
        db,
        tenant_id,
        identity_id=identity.identity_id,
        version_id=version.version_id if version else None,
        state_dimension="record_status",
        new_state=target_record_status,
        event_type=lifecycle_event_type,
        performed_by=performed_by,
        reason=evaluation_reason,
        metadata_json={
            "declaration_engine": execution_log,
            **(metadata_json or {}),
        },
    )
    merged_metadata = _merge_declaration_metadata(
        existing_metadata=(dict(latest_declaration.metadata_json or {}) if latest_declaration else None),
        execution_log=execution_log,
        declaration_rule=selected_rule,
        lifecycle_rule=lifecycle_rule,
        retention_schedule=retention_schedule,
        vital_policy=vital_policy,
        vital_profile=vital_profile,
        assignment_rule=assignment_rule,
        metadata_json=metadata_json,
    )
    record_declaration_id = _persist_record_declaration(
        db,
        tenant_id,
        identity_id=identity.identity_id,
        version_id=version.version_id if version else None,
        record_category=record_category,
        record_status=target_record_status,
        vital_status=vital_status,
        owner_user_id=performed_by,
        declaration_reason=evaluation_reason,
        source_event_id=lifecycle["event_id"],
        declaration_rule=selected_rule,
        lifecycle_rule=lifecycle_rule,
        retention_schedule=retention_schedule,
        metadata_json=merged_metadata,
        actor=performed_by,
    )
    lifecycle_rule_evaluation = evaluate_record_lifecycle_rule(
        db,
        tenant_id,
        identity_id=identity.identity_id,
        version_id=version.version_id if version else None,
        trigger_event=trigger_event,
        performed_by=performed_by,
        evaluation_reason=evaluation_reason,
        metadata_json=metadata_json,
        commit=False,
    )
    activity_updates = _sync_declaration_activity_fields(
        db,
        tenant_id,
        identity_id=identity.identity_id,
        lifecycle_transition=lifecycle_rule_evaluation.get("transition"),
    )
    db.commit()
    return {
        **result,
        "source_event_id": lifecycle["event_id"],
        "record_declaration_id": record_declaration_id,
        "lifecycle_rule_evaluation": lifecycle_rule_evaluation,
        "activity_updates": activity_updates,
        "executed": True,
    }


def evaluate_record_lifecycle_rule(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    version_id: str | None,
    trigger_event: str,
    performed_by: str | None = None,
    evaluation_reason: str = "",
    metadata_json: dict[str, Any] | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    identity = _require_identity(db, tenant_id, identity_id)
    latest_declaration = _latest_record_declaration(db, tenant_id, identity_id)
    if not latest_declaration:
        return {
            "identity_id": identity_id,
            "version_id": version_id,
            "trigger_event": trigger_event,
            "matched": False,
            "reason": "No record declaration found",
            "lifecycle_rule_id": None,
            "record_category": None,
            "transition": None,
        }

    record_category = latest_declaration.record_category
    lifecycle_rule = _resolve_record_lifecycle_rule(
        db,
        tenant_id,
        identity=identity,
        record_category=record_category,
    ) if record_category else None
    if not lifecycle_rule:
        return {
            "identity_id": identity_id,
            "version_id": version_id,
            "trigger_event": trigger_event,
            "matched": False,
            "reason": "No lifecycle rule resolved",
            "lifecycle_rule_id": None,
            "record_category": record_category,
            "transition": None,
        }

    transition = apply_record_lifecycle_transition(
        db,
        tenant_id,
        identity_id=identity_id,
        version_id=version_id,
        transition_code="EVALUATE_RULE",
        trigger_event=trigger_event,
        lifecycle_rule=lifecycle_rule,
        performed_by=performed_by,
        reason=evaluation_reason,
        metadata_json={
            "record_category": record_category,
            **(metadata_json or {}),
        },
        commit=commit,
    )
    activity_updates = {}
    if commit:
        activity_updates = _sync_declaration_activity_fields(
            db,
            tenant_id,
            identity_id=identity_id,
            lifecycle_transition=transition,
        )
        db.commit()
    return {
        "identity_id": identity_id,
        "version_id": version_id,
        "trigger_event": trigger_event,
        "matched": bool(transition.get("events")),
        "reason": evaluation_reason,
        "lifecycle_rule_id": lifecycle_rule.get("lifecycle_rule_id"),
        "record_category": record_category,
        "transition": transition,
        "activity_updates": activity_updates,
    }


def run_time_evaluation(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str | None = None,
    version_id: str | None = None,
    limit: int = 100,
    performed_by: str | None = None,
    evaluation_reason: str = "",
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    declarations = _table(db, "symployee_record_declarations")
    query = (
        declarations.select()
        .where(declarations.c.tenant_id == tenant_id)
        .order_by(
            declarations.c.identity_id.asc(),
            declarations.c.declared_at.desc(),
            declarations.c.created_at.desc(),
        )
    )
    if identity_id:
        query = query.where(declarations.c.identity_id == identity_id)
    if version_id:
        query = query.where(declarations.c.version_id == version_id)

    rows = db.execute(query).fetchall()
    latest_by_identity: dict[str, Any] = {}
    for row in rows:
        if row.identity_id not in latest_by_identity:
            latest_by_identity[row.identity_id] = row
        if len(latest_by_identity) >= max(1, min(limit, 500)):
            break

    items: list[dict[str, Any]] = []
    processed = 0
    matched = 0
    changed = 0
    for row in latest_by_identity.values():
        result = evaluate_record_lifecycle_rule(
            db,
            tenant_id,
            identity_id=row.identity_id,
            version_id=row.version_id,
            trigger_event="TIME_EVALUATION",
            performed_by=performed_by,
            evaluation_reason=evaluation_reason or "Controlled time evaluation",
            metadata_json=metadata_json,
            commit=True,
        )
        processed += 1
        if result.get("matched"):
            matched += 1
        transition = dict(result.get("transition") or {})
        if transition.get("changed"):
            changed += 1
        items.append(result)

    return {
        "processed": processed,
        "matched": matched,
        "changed": changed,
        "filters": {
            "tenant_id": tenant_id,
            "identity_id": identity_id,
            "version_id": version_id,
            "limit": max(1, min(limit, 500)),
        },
        "items": items,
    }


def reprocess_repository_record_declarations(
    db: Session,
    tenant_id: str,
    *,
    repository_id: str | None = None,
    identity_ids: list[str] | None = None,
    limit: int = 100,
    trigger_event: str = "INGESTION",
    dry_run: bool = False,
    performed_by: str | None = None,
    evaluation_reason: str = "",
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    identity_query = (
        db.query(SymployeeDocumentIdentity)
        .filter(SymployeeDocumentIdentity.tenant_id == tenant_id)
        .order_by(SymployeeDocumentIdentity.created_at.desc())
    )
    if repository_id:
        identity_query = identity_query.filter(SymployeeDocumentIdentity.repository_id == repository_id)
    if identity_ids:
        identity_query = identity_query.filter(SymployeeDocumentIdentity.identity_id.in_(identity_ids))

    max_limit = max(1, min(limit, 500))
    identities = identity_query.limit(max_limit).all()

    items: list[dict[str, Any]] = []
    processed = 0
    executed = 0
    skipped = 0
    errors = 0
    for identity in identities:
        processed += 1
        version = _resolve_current_version(db, tenant_id, identity_id=identity.identity_id)
        version_id = version.version_id if version else None
        try:
            preview = evaluate_record_declaration(
                db,
                tenant_id,
                identity_id=identity.identity_id,
                version_id=version_id,
                trigger_event=trigger_event,
                dry_run=True,
                performed_by=performed_by,
                evaluation_reason=evaluation_reason or "Repository content reprocessing declaration evaluation",
                metadata_json={
                    "trigger_source": "repository_reprocess",
                    "repository_id": identity.repository_id,
                    **(metadata_json or {}),
                },
            )
            latest_declaration = _latest_record_declaration(db, tenant_id, identity.identity_id)
            preserved_existing_governed_status = (
                latest_declaration.record_status
                if latest_declaration
                and latest_declaration.record_status in _governed_record_statuses()
                and preview["target_record_status"] == "NON_RECORD"
                else None
            )
            already_aligned = (
                not dry_run
                and (
                    (
                        preview["target_record_status"] == "NON_RECORD"
                        and identity.record_status == "NON_RECORD"
                    )
                    or (
                        latest_declaration is not None
                        and latest_declaration.record_status == preview["target_record_status"]
                        and latest_declaration.record_category == preview["record_category"]
                        and latest_declaration.vital_status == preview["vital_status"]
                        and latest_declaration.declaration_rule_id == preview["declaration_rule_id"]
                        and latest_declaration.lifecycle_rule_id == preview["lifecycle_rule_id"]
                        and latest_declaration.retention_schedule_id == preview["retention_schedule_id"]
                    )
                )
            )
            if dry_run or already_aligned or preserved_existing_governed_status:
                items.append(
                    {
                        "identity_id": identity.identity_id,
                        "repository_id": identity.repository_id,
                        "version_id": version_id,
                        "executed": False,
                        "skipped": already_aligned,
                        "preserved_existing_governed_status": preserved_existing_governed_status,
                        "result": preview,
                    }
                )
                skipped += 1 if already_aligned else 0
                continue

            result = evaluate_record_declaration(
                db,
                tenant_id,
                identity_id=identity.identity_id,
                version_id=version_id,
                trigger_event=trigger_event,
                dry_run=False,
                performed_by=performed_by,
                evaluation_reason=evaluation_reason or "Repository content reprocessing declaration evaluation",
                metadata_json={
                    "trigger_source": "repository_reprocess",
                    "repository_id": identity.repository_id,
                    **(metadata_json or {}),
                },
            )
            items.append(
                {
                    "identity_id": identity.identity_id,
                    "repository_id": identity.repository_id,
                    "version_id": version_id,
                    "executed": True,
                    "skipped": False,
                    "result": result,
                }
            )
            executed += 1
        except ValueError as exc:
            errors += 1
            items.append(
                {
                    "identity_id": identity.identity_id,
                    "repository_id": identity.repository_id,
                    "version_id": version_id,
                    "executed": False,
                    "skipped": False,
                    "error": str(exc),
                }
            )

    return {
        "processed": processed,
        "executed": executed,
        "skipped": skipped,
        "errors": errors,
        "filters": {
            "repository_id": repository_id,
            "identity_ids": identity_ids or [],
            "limit": max_limit,
            "trigger_event": trigger_event,
            "dry_run": dry_run,
        },
        "items": items,
    }


def run_retention_disposition_automation(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str | None = None,
    version_id: str | None = None,
    limit: int = 100,
    performed_by: str | None = None,
    evaluation_reason: str = "",
    auto_initiate_disposition: bool = True,
    auto_initiate_archive: bool = True,
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    declarations = _table(db, "symployee_record_declarations")
    query = (
        declarations.select()
        .where(declarations.c.tenant_id == tenant_id)
        .order_by(
            declarations.c.identity_id.asc(),
            declarations.c.declared_at.desc(),
            declarations.c.created_at.desc(),
        )
    )
    if identity_id:
        query = query.where(declarations.c.identity_id == identity_id)
    if version_id:
        query = query.where(declarations.c.version_id == version_id)

    rows = db.execute(query).fetchall()
    latest_by_identity: dict[str, Any] = {}
    for row in rows:
        if row.identity_id not in latest_by_identity:
            latest_by_identity[row.identity_id] = row
        if len(latest_by_identity) >= max(1, min(limit, 500)):
            break

    processed = 0
    changed = 0
    disposition_initiated = 0
    archive_initiated = 0
    items: list[dict[str, Any]] = []

    for declaration in latest_by_identity.values():
        processed += 1
        identity = _require_identity(db, tenant_id, declaration.identity_id)
        assignment_rule = _resolve_assignment_rule(
            db,
            tenant_id,
            identity=identity,
            record_category=getattr(declaration, "record_category", None),
            assignment_context="RETENTION_REVIEW",
        )
        workflow_routing = _build_assignment_routing(assignment_rule)
        retention_schedule = (
            _resolve_retention_schedule_by_id(
                db,
                tenant_id,
                retention_schedule_id=getattr(declaration, "retention_schedule_id", None),
            )
            or _resolve_retention_schedule_config(
                db,
                tenant_id,
                identity=identity,
                record_category=declaration.record_category,
            )
        )
        active_holds = _find_active_hold_rows(db, tenant_id, declaration.identity_id)
        hold_effects = _resolve_hold_effects(
            db,
            tenant_id,
            active_holds=active_holds,
        )
        open_disposition = _find_open_disposition_case(db, tenant_id, declaration.identity_id)
        open_archive_transfer = _find_open_archive_transfer(db, tenant_id, declaration.identity_id)

        target_retention_status = "NOT_CLASSIFIED"
        retention_anchor_at = None
        review_due_at = None
        eligibility_at = None
        disposition_policy = None
        archive_policy = None
        automation_created_case = None
        automation_created_transfer = None

        if retention_schedule:
            retention_anchor_at = _resolve_retention_anchor_at(
                declaration,
                retention_schedule=retention_schedule,
            )
            if retention_anchor_at:
                eligibility_at = _add_retention_period(
                    retention_anchor_at,
                    int(retention_schedule["retention_period_value"]),
                    str(retention_schedule["retention_period_unit"]),
                )
                review_due_at = _resolve_review_due_at(
                    retention_schedule=retention_schedule,
                    eligibility_at=eligibility_at,
                )

            disposition_policy = _resolve_disposition_policy_by_code(
                db,
                tenant_id,
                identity=identity,
                record_category=declaration.record_category,
                policy_code=retention_schedule.get("final_disposition_policy_code"),
            )
            archive_policy = _resolve_archive_policy(
                db,
                tenant_id,
                identity=identity,
                record_category=declaration.record_category,
            )

            if normalize := str(getattr(identity, "record_status", None) or "").upper():
                if normalize in {"ARCHIVED", "DESTROYED", "PERMANENT"}:
                    target_retention_status = "COMPLETED"
                elif active_holds and bool(retention_schedule.get("suspend_on_hold")):
                    target_retention_status = "ON_HOLD"
                elif eligibility_at and _now() >= eligibility_at:
                    target_retention_status = "ELIGIBLE_FOR_DISPOSITION"
                else:
                    target_retention_status = "SCHEDULED"

        current_retention_status = str(getattr(identity, "retention_status", None) or "NOT_CLASSIFIED").upper()
        retention_transition = None
        if target_retention_status != current_retention_status:
            retention_transition = apply_state_transition(
                db,
                tenant_id,
                identity_id=declaration.identity_id,
                version_id=declaration.version_id,
                state_dimension="retention_status",
                new_state=target_retention_status,
                event_type=f"RETENTION_{target_retention_status}",
                performed_by=performed_by,
                reason=evaluation_reason or "Retention and disposition automation",
                metadata_json={
                    "record_declaration_id": declaration.record_declaration_id,
                    "retention_schedule_id": retention_schedule["retention_schedule_id"] if retention_schedule else None,
                    "active_hold_ids": hold_effects["active_hold_ids"],
                    "workflow_routing": workflow_routing,
                    **(metadata_json or {}),
                },
                commit=False,
            )

        existing_metadata = dict(getattr(declaration, "metadata_json", None) or {})
        automation_payload = {
            "evaluated_at": _now().isoformat(),
            "assignment_rule_id": assignment_rule.get("assignment_rule_id") if assignment_rule else None,
            "workflow_routing": workflow_routing,
            "retention_schedule_id": retention_schedule["retention_schedule_id"] if retention_schedule else None,
            "retention_schedule_code": retention_schedule.get("schedule_code") if retention_schedule else None,
            "retention_start_event": retention_schedule.get("retention_start_event") if retention_schedule else None,
            "retention_anchor_at": retention_anchor_at.isoformat() if retention_anchor_at else None,
            "review_due_at": review_due_at.isoformat() if review_due_at else None,
            "eligibility_at": eligibility_at.isoformat() if eligibility_at else None,
            "hold_blocked": bool(active_holds),
            "blocks_disposition": hold_effects["blocks_disposition"],
            "blocks_archive_transfer": hold_effects["blocks_archive_transfer"],
            "active_hold_ids": hold_effects["active_hold_ids"],
            "active_hold_categories": hold_effects["active_hold_categories"],
            "disposition_policy_id": disposition_policy.get("disposition_policy_id") if disposition_policy else None,
            "final_disposition_policy_code": retention_schedule.get("final_disposition_policy_code") if retention_schedule else None,
            "archive_policy_id": archive_policy.get("archive_policy_id") if archive_policy else None,
            "review_required": bool(retention_schedule.get("review_required")) if retention_schedule else False,
        }
        db.execute(
            declarations.update()
            .where(
                declarations.c.tenant_id == tenant_id,
                declarations.c.record_declaration_id == declaration.record_declaration_id,
            )
            .values(
                metadata_json={
                    **existing_metadata,
                    "retention_automation": automation_payload,
                    **(metadata_json or {}),
                },
                modified_by=performed_by,
                modified_at=_now(),
            )
        )

        if (
            retention_schedule
            and target_retention_status == "ELIGIBLE_FOR_DISPOSITION"
            and auto_initiate_disposition
            and not open_disposition
            and not hold_effects["blocks_disposition"]
        ):
            disposition_type = _resolve_disposition_type_from_policy(
                disposition_policy=disposition_policy,
                archive_policy=archive_policy,
            )
            automation_created_case = create_disposition_case(
                db,
                tenant_id,
                identity_id=declaration.identity_id,
                disposition_type=disposition_type,
                requested_by=performed_by,
                reason=evaluation_reason or "Automated disposition initiation",
                metadata_json={
                    "automation": True,
                    "retention_schedule_id": retention_schedule["retention_schedule_id"],
                    **(metadata_json or {}),
                },
            )
            open_disposition = _find_open_disposition_case(db, tenant_id, declaration.identity_id)
            disposition_initiated += 1

        if (
            auto_initiate_archive
            and open_disposition
            and str(open_disposition.case_status or "").upper() == "APPROVED"
            and str(open_disposition.disposition_type or "").upper() == "ARCHIVE"
            and not open_archive_transfer
            and not hold_effects["blocks_archive_transfer"]
        ):
            archive_policy = archive_policy or _resolve_archive_policy(
                db,
                tenant_id,
                identity=identity,
                record_category=declaration.record_category,
            )
            automation_created_transfer = initiate_archive_transfer(
                db,
                tenant_id,
                identity_id=declaration.identity_id,
                archive_destination=(
                    (archive_policy or {}).get("destination_code")
                    or "CORP_ARCHIVE"
                ),
                requested_by=performed_by,
                disposition_case_id=open_disposition.disposition_case_id,
                preservation_format=(archive_policy or {}).get("package_format_code"),
                metadata_json={
                    "automation": True,
                    "archive_policy_id": (archive_policy or {}).get("archive_policy_id"),
                    **(metadata_json or {}),
                },
            )
            archive_initiated += 1

        if retention_transition and retention_transition.get("changed"):
            changed += 1

        items.append(
            {
                "record_declaration_id": declaration.record_declaration_id,
                "identity_id": declaration.identity_id,
                "retention_status": target_retention_status,
                "current_retention_status": current_retention_status,
                "retention_schedule_id": retention_schedule["retention_schedule_id"] if retention_schedule else None,
                "review_due_at": review_due_at.isoformat() if review_due_at else None,
                "eligibility_at": eligibility_at.isoformat() if eligibility_at else None,
                "hold_effects": hold_effects,
                "open_disposition_case_id": open_disposition.disposition_case_id if open_disposition else None,
                "open_archive_transfer_id": open_archive_transfer.archive_transfer_id if open_archive_transfer else None,
                "assignment_rule_id": assignment_rule.get("assignment_rule_id") if assignment_rule else None,
                "workflow_routing": workflow_routing,
                "automation_created_case": automation_created_case,
                "automation_created_transfer": automation_created_transfer,
            }
        )

    db.commit()
    return {
        "processed": processed,
        "changed": changed,
        "disposition_initiated": disposition_initiated,
        "archive_initiated": archive_initiated,
        "filters": {
            "tenant_id": tenant_id,
            "identity_id": identity_id,
            "version_id": version_id,
            "limit": max(1, min(limit, 500)),
            "auto_initiate_disposition": auto_initiate_disposition,
            "auto_initiate_archive": auto_initiate_archive,
        },
        "items": items,
    }


def approve_disposition_case(
    db: Session,
    tenant_id: str,
    *,
    disposition_case_id: str,
    approval_role: str,
    approver_user_id: str | None,
    comments: str = "",
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case = _find_disposition_case(db, tenant_id, disposition_case_id)
    if not case:
        raise ValueError("Disposition case not found")
    if str(case.case_status or "").upper() in {"COMPLETED", "CANCELLED"}:
        return {
            "disposition_case_id": case.disposition_case_id,
            "case_status": case.case_status,
            "existing": True,
        }

    declaration = _latest_record_declaration(db, tenant_id, case.identity_id)
    identity = _require_identity(db, tenant_id, case.identity_id)
    assignment_rule = _resolve_assignment_rule(
        db,
        tenant_id,
        identity=identity,
        record_category=(declaration.record_category if declaration else None),
        assignment_context="DISPOSITION_APPROVAL",
    ) if declaration else None
    workflow_routing = _build_assignment_routing(assignment_rule)
    disposition_policy = (
        _resolve_disposition_policy_by_code(
            db,
            tenant_id,
            identity=identity,
            record_category=declaration.record_category if declaration else "",
            policy_code=(dict(case.metadata_json or {}).get("final_disposition_policy_code")),
        )
        if not getattr(case, "disposition_policy_id", None)
        else None
    )
    if getattr(case, "disposition_policy_id", None):
        policies = _table(db, "symployee_record_disposition_policies")
        policy_row = db.execute(
            policies.select().where(
                policies.c.tenant_id == tenant_id,
                policies.c.disposition_policy_id == case.disposition_policy_id,
            )
        ).fetchone()
        disposition_policy = _serialize_row(policy_row) if policy_row else disposition_policy

    required_roles: list[str] = []
    if disposition_policy:
        if bool(disposition_policy.get("records_approval_required")):
            required_roles.append("RECORDS")
        if bool(disposition_policy.get("legal_approval_required")):
            required_roles.append("LEGAL")
        if bool(disposition_policy.get("business_owner_approval_required")):
            required_roles.append("BUSINESS_OWNER")
        if not required_roles and bool(disposition_policy.get("approval_required")):
            required_roles.append("RECORDS")
    if not required_roles:
        if workflow_routing.get("records_officer_role_code") or workflow_routing.get("approver_role_code"):
            required_roles.append("RECORDS")
        if workflow_routing.get("legal_approver_role_code"):
            required_roles.append("LEGAL")
        if workflow_routing.get("business_approver_role_code"):
            required_roles.append("BUSINESS_OWNER")

    existing_metadata = dict(case.metadata_json or {})
    approvals = dict(existing_metadata.get("approvals") or {})
    approvals[approval_role] = {
        "approved_by": approver_user_id,
        "approved_at": _now().isoformat(),
        "comments": comments or None,
    }
    approval_complete = all(role in approvals for role in required_roles) if required_roles else True
    new_case_status = "APPROVED" if approval_complete else "PENDING_APPROVALS"

    cases = _table(db, "symployee_disposition_cases")
    db.execute(
        cases.update()
        .where(
            cases.c.tenant_id == tenant_id,
            cases.c.disposition_case_id == disposition_case_id,
        )
        .values(
            case_status=new_case_status,
            metadata_json={
                **existing_metadata,
                "approvals": approvals,
                "required_approval_roles": required_roles,
                "workflow_routing": workflow_routing,
                **(metadata_json or {}),
            },
            modified_by=approver_user_id,
            modified_at=_now(),
        )
    )
    event = create_lifecycle_event(
        db,
        tenant_id,
        identity_id=case.identity_id,
        version_id=getattr(case, "version_id", None),
        event_type="DISPOSITION_APPROVAL_RECORDED",
        state_dimension="disposition_status",
        previous_state=case.case_status,
        new_state=new_case_status,
        performed_by=approver_user_id,
        reason=comments,
        metadata_json={
            "disposition_case_id": disposition_case_id,
            "approval_role": approval_role,
            "approval_complete": approval_complete,
            "workflow_routing": workflow_routing,
            **(metadata_json or {}),
        },
        created_by=approver_user_id,
    )

    archive_transfer = None
    if approval_complete:
        apply_state_transition(
            db,
            tenant_id,
            identity_id=case.identity_id,
            version_id=None,
            state_dimension="disposition_status",
            new_state="APPROVED",
            event_type="DISPOSITION_APPROVED",
            performed_by=approver_user_id,
            reason=comments,
            metadata_json={
                "disposition_case_id": disposition_case_id,
                **(metadata_json or {}),
            },
            commit=False,
        )
        if str(case.disposition_type or "").upper() == "ARCHIVE" and not _find_open_archive_transfer(db, tenant_id, case.identity_id):
            archive_policy = _resolve_archive_policy(
                db,
                tenant_id,
                identity=identity,
                record_category=declaration.record_category if declaration else "",
            ) if declaration else None
            archive_transfer = initiate_archive_transfer(
                db,
                tenant_id,
                identity_id=case.identity_id,
                archive_destination=((archive_policy or {}).get("destination_code") or "CORP_ARCHIVE"),
                requested_by=approver_user_id,
                disposition_case_id=disposition_case_id,
                preservation_format=(archive_policy or {}).get("package_format_code"),
                metadata_json={
                    "automation": True,
                    "trigger": "DISPOSITION_APPROVAL",
                    **(metadata_json or {}),
                },
            )

    db.commit()
    return {
        "disposition_case_id": disposition_case_id,
        "case_status": new_case_status,
        "approval_role": approval_role,
        "required_approval_roles": required_roles,
        "approvals": approvals,
        "assignment_rule_id": assignment_rule.get("assignment_rule_id") if assignment_rule else None,
        "workflow_routing": workflow_routing,
        "source_event_id": event["event_id"],
        "archive_transfer": archive_transfer,
    }


def execute_disposition_case(
    db: Session,
    tenant_id: str,
    *,
    disposition_case_id: str,
    execution_outcome: str,
    executed_by: str | None,
    reason: str = "",
    evidence_json: dict[str, Any] | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case = _find_disposition_case(db, tenant_id, disposition_case_id)
    if not case:
        raise ValueError("Disposition case not found")
    if str(execution_outcome or "").upper() != "DESTROY":
        raise ValueError("Archive executions should be completed through archive transfer completion")
    identity = _require_identity(db, tenant_id, case.identity_id)
    declaration = _latest_record_declaration(db, tenant_id, case.identity_id)
    assignment_rule = _resolve_assignment_rule(
        db,
        tenant_id,
        identity=identity,
        record_category=(declaration.record_category if declaration else None),
        assignment_context="DISPOSITION_EXECUTION",
    ) if declaration else None
    workflow_routing = _build_assignment_routing(assignment_rule)

    existing_metadata = dict(case.metadata_json or {})
    cases = _table(db, "symployee_disposition_cases")
    db.execute(
        cases.update()
        .where(
            cases.c.tenant_id == tenant_id,
            cases.c.disposition_case_id == disposition_case_id,
        )
        .values(
            case_status="COMPLETED",
            metadata_json={
                **existing_metadata,
                "execution": {
                    "execution_outcome": "DESTROY",
                    "executed_at": _now().isoformat(),
                    "executed_by": executed_by,
                    "reason": reason or None,
                    "evidence_json": evidence_json or {},
                },
                "workflow_routing": workflow_routing,
                **(metadata_json or {}),
            },
            modified_by=executed_by,
            modified_at=_now(),
        )
    )
    disposition_event = apply_state_transition(
        db,
        tenant_id,
        identity_id=case.identity_id,
        version_id=None,
        state_dimension="disposition_status",
        new_state="COMPLETED",
        event_type="DISPOSITION_EXECUTED",
        performed_by=executed_by,
        reason=reason,
        metadata_json={
            "disposition_case_id": disposition_case_id,
            "execution_outcome": "DESTROY",
            "evidence_json": evidence_json or {},
            **(metadata_json or {}),
        },
        commit=False,
    )
    retention_event = apply_state_transition(
        db,
        tenant_id,
        identity_id=case.identity_id,
        version_id=None,
        state_dimension="retention_status",
        new_state="COMPLETED",
        event_type="RETENTION_COMPLETED",
        performed_by=executed_by,
        reason=reason,
        metadata_json={
            "disposition_case_id": disposition_case_id,
            **(metadata_json or {}),
        },
        commit=False,
    )
    record_event = apply_state_transition(
        db,
        tenant_id,
        identity_id=case.identity_id,
        version_id=None,
        state_dimension="record_status",
        new_state="DESTROYED",
        event_type="DESTRUCTION_EXECUTED",
        performed_by=executed_by,
        reason=reason,
        metadata_json={
            "disposition_case_id": disposition_case_id,
            **(metadata_json or {}),
        },
        commit=False,
    )
    lifecycle_event = apply_state_transition(
        db,
        tenant_id,
        identity_id=case.identity_id,
        version_id=None,
        state_dimension="document_lifecycle_stage",
        new_state="DISPOSED",
        event_type="RECORD_DISPOSED",
        performed_by=executed_by,
        reason=reason,
        metadata_json={
            "disposition_case_id": disposition_case_id,
            **(metadata_json or {}),
        },
        commit=False,
    )
    db.commit()
    return {
        "disposition_case_id": disposition_case_id,
        "case_status": "COMPLETED",
        "execution_outcome": "DESTROY",
        "assignment_rule_id": assignment_rule.get("assignment_rule_id") if assignment_rule else None,
        "workflow_routing": workflow_routing,
        "source_event_ids": [
            disposition_event["event_id"],
            retention_event["event_id"],
            record_event["event_id"],
            lifecycle_event["event_id"],
        ],
    }


def complete_archive_transfer(
    db: Session,
    tenant_id: str,
    *,
    archive_transfer_id: str,
    completed_by: str | None,
    receipt_reference: str | None = None,
    integrity_verified: bool | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    transfer = _find_archive_transfer(db, tenant_id, archive_transfer_id)
    if not transfer:
        raise ValueError("Archive transfer not found")
    if str(transfer.transfer_status or "").upper() == "COMPLETED":
        return {
            "archive_transfer_id": transfer.archive_transfer_id,
            "transfer_status": transfer.transfer_status,
            "existing": True,
        }

    archive_policy = _resolve_archive_policy_by_id(
        db,
        tenant_id,
        archive_policy_id=getattr(transfer, "archive_policy_id", None),
    )
    identity = _require_identity(db, tenant_id, transfer.identity_id)
    declaration = _latest_record_declaration(db, tenant_id, transfer.identity_id)
    assignment_rule = _resolve_assignment_rule(
        db,
        tenant_id,
        identity=identity,
        record_category=(declaration.record_category if declaration else None),
        assignment_context="ARCHIVE_TRANSFER",
    ) if declaration else None
    workflow_routing = _build_assignment_routing(assignment_rule)
    if archive_policy and bool(archive_policy.get("receipt_confirmation_required")) and not receipt_reference:
        raise ValueError("Receipt reference is required by the archive policy")
    if archive_policy and bool(archive_policy.get("checksum_required")) and integrity_verified is False:
        raise ValueError("Integrity verification cannot be false when checksum validation is required")

    transfers = _table(db, "symployee_archive_transfers")
    existing_metadata = dict(transfer.metadata_json or {})
    db.execute(
        transfers.update()
        .where(
            transfers.c.tenant_id == tenant_id,
            transfers.c.archive_transfer_id == archive_transfer_id,
        )
        .values(
            transfer_status="COMPLETED",
            metadata_json={
                **existing_metadata,
                "completion": {
                    "completed_at": _now().isoformat(),
                    "completed_by": completed_by,
                    "receipt_reference": receipt_reference,
                    "integrity_verified": integrity_verified,
                },
                "workflow_routing": workflow_routing,
                **(metadata_json or {}),
            },
            modified_by=completed_by,
            modified_at=_now(),
        )
    )
    if getattr(transfer, "disposition_case_id", None):
        cases = _table(db, "symployee_disposition_cases")
        case = _find_disposition_case(db, tenant_id, transfer.disposition_case_id)
        if case:
            db.execute(
                cases.update()
                .where(
                    cases.c.tenant_id == tenant_id,
                    cases.c.disposition_case_id == transfer.disposition_case_id,
                )
                .values(
                    case_status="COMPLETED",
                    metadata_json={
                        **dict(case.metadata_json or {}),
                        "archive_completion": {
                            "archive_transfer_id": archive_transfer_id,
                            "completed_at": _now().isoformat(),
                        },
                    },
                    modified_by=completed_by,
                    modified_at=_now(),
                )
            )

    lifecycle = apply_record_lifecycle_transition(
        db,
        tenant_id,
        identity_id=transfer.identity_id,
        version_id=None,
        transition_code="MARK_ARCHIVED",
        trigger_event="ARCHIVE_TRANSFER_COMPLETED",
        lifecycle_rule=None,
        performed_by=completed_by,
        reason="Archive transfer completed",
        metadata_json={
            "archive_transfer_id": archive_transfer_id,
            "receipt_reference": receipt_reference,
            "integrity_verified": integrity_verified,
            "workflow_routing": workflow_routing,
            **(metadata_json or {}),
        },
        commit=False,
    )
    disposition_event = apply_state_transition(
        db,
        tenant_id,
        identity_id=transfer.identity_id,
        version_id=None,
        state_dimension="disposition_status",
        new_state="COMPLETED",
        event_type="ARCHIVE_TRANSFER_COMPLETED",
        performed_by=completed_by,
        reason="Archive transfer completed",
        metadata_json={
            "archive_transfer_id": archive_transfer_id,
            "workflow_routing": workflow_routing,
            **(metadata_json or {}),
        },
        commit=False,
    )
    retention_event = apply_state_transition(
        db,
        tenant_id,
        identity_id=transfer.identity_id,
        version_id=None,
        state_dimension="retention_status",
        new_state="COMPLETED",
        event_type="RETENTION_COMPLETED",
        performed_by=completed_by,
        reason="Archive transfer completed",
        metadata_json={
            "archive_transfer_id": archive_transfer_id,
            "workflow_routing": workflow_routing,
            **(metadata_json or {}),
        },
        commit=False,
    )
    db.commit()
    return {
        "archive_transfer_id": archive_transfer_id,
        "transfer_status": "COMPLETED",
        "assignment_rule_id": assignment_rule.get("assignment_rule_id") if assignment_rule else None,
        "workflow_routing": workflow_routing,
        "source_event_ids": [
            *(event["event_id"] for event in lifecycle.get("events", []) if event.get("event_id")),
            disposition_event["event_id"],
            retention_event["event_id"],
        ],
        "lifecycle_transition": lifecycle,
    }


def update_vital_status(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    vital_status: str,
    modified_by: str | None = None,
    reason: str = "",
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if vital_status not in {"NON_VITAL", "VITAL_CANDIDATE", "VITAL", "VITAL_UNDER_REVIEW"}:
        raise ValueError("Unsupported vital status")

    identity = _require_identity(db, tenant_id, identity_id)
    declaration = _latest_record_declaration(db, tenant_id, identity_id)
    if not declaration:
        raise ValueError("Record declaration not found")
    assignment_rule = _resolve_assignment_rule(
        db,
        tenant_id,
        identity=identity,
        record_category=getattr(declaration, "record_category", None),
        assignment_context="VITAL_REVIEW",
    )
    workflow_routing = _build_assignment_routing(assignment_rule)

    declarations = _table(db, "symployee_record_declarations")
    previous_status = getattr(declaration, "vital_status", None)
    existing_metadata = dict(getattr(declaration, "metadata_json", None) or {})
    vital_profile = dict(existing_metadata.get("vital_profile") or {})
    vital_profile.update(
        {
            "last_reviewed_at": _now().isoformat(),
            "manual_override": True,
            "override_reason": reason or None,
        }
    )
    if vital_status in {"VITAL", "VITAL_UNDER_REVIEW"} and vital_profile.get("review_interval_days"):
        vital_profile["review_due_at"] = (
            _now() + timedelta(days=int(vital_profile["review_interval_days"]))
        ).isoformat()
    elif vital_status == "NON_VITAL":
        vital_profile["review_due_at"] = None

    event = create_lifecycle_event(
        db,
        tenant_id,
        identity_id=identity.identity_id,
        version_id=declaration.version_id,
        event_type="VITAL_STATUS_UPDATED",
        state_dimension="vital_status",
        previous_state=previous_status,
        new_state=vital_status,
        performed_by=modified_by,
        reason=reason,
        metadata_json={
            "record_declaration_id": declaration.record_declaration_id,
            "workflow_routing": workflow_routing,
            **(metadata_json or {}),
        },
        created_by=modified_by,
    )
    db.execute(
        declarations.update()
        .where(
            declarations.c.tenant_id == tenant_id,
            declarations.c.record_declaration_id == declaration.record_declaration_id,
        )
        .values(
            vital_status=vital_status,
            metadata_json={
                **existing_metadata,
                "vital_profile": vital_profile,
                "workflow_routing": workflow_routing,
                **(metadata_json or {}),
            },
            modified_by=modified_by,
            modified_at=_now(),
        )
    )
    db.commit()
    return {
        "record_declaration_id": declaration.record_declaration_id,
        "identity_id": identity_id,
        "vital_status": vital_status,
        "previous_vital_status": previous_status,
        "vital_profile": vital_profile,
        "assignment_rule_id": assignment_rule.get("assignment_rule_id") if assignment_rule else None,
        "workflow_routing": workflow_routing,
        "source_event_id": event["event_id"],
    }


def resolve_retention_rule(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    record_category: str,
    trigger_event: str = "DECLARED",
) -> dict | None:
    identity = _require_identity(db, tenant_id, identity_id)
    rules = _table(db, "symployee_retention_rules")
    base_rows = db.execute(
        rules.select()
        .where(
            rules.c.tenant_id == tenant_id,
            rules.c.record_category == record_category,
            rules.c.trigger_event == trigger_event,
            rules.c.status == "ACTIVE",
        )
    ).fetchall()
    if not base_rows:
        return None

    for scope_type, scope_ref in _resolve_scope_candidates(identity):
        for row in base_rows:
            if row.scope_type != scope_type:
                continue
            if scope_ref is None:
                if row.scope_ref is None or row.is_default:
                    return _serialize_row(row)
            elif row.scope_ref == scope_ref:
                return _serialize_row(row)

    default_rows = [
        row for row in base_rows
        if row.scope_type == "tenant" and (row.scope_ref is None or row.is_default)
    ]
    if default_rows:
        prioritized = sorted(default_rows, key=lambda row: (not bool(row.is_default), row.created_at or _now()))
        return _serialize_row(prioritized[0])
    return _serialize_row(base_rows[0])


def declare_record(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    version_id: str | None,
    record_category: str,
    owner_user_id: str | None = None,
    declared_by: str | None = None,
    declaration_reason: str = "",
    metadata_json: dict | None = None,
) -> dict:
    identity = _require_identity(db, tenant_id, identity_id)
    version = _require_version(db, tenant_id, identity_id=identity_id, version_id=version_id)
    existing = _active_record_declaration(db, tenant_id, identity_id)
    if existing and existing.record_category == record_category:
        return {
            "record_declaration_id": existing.record_declaration_id,
            "record_status": existing.record_status,
            "vital_status": getattr(existing, "vital_status", None),
            "inactive_reason": getattr(existing, "inactive_reason", None),
            "declaration_rule_id": existing.declaration_rule_id,
            "lifecycle_rule_id": existing.lifecycle_rule_id,
            "retention_schedule_id": existing.retention_schedule_id,
            "existing": True,
            "retention_rule": resolve_retention_rule(
                db,
                tenant_id,
                identity_id=identity_id,
                record_category=record_category,
            ),
        }

    declaration_rule = _resolve_record_declaration_rule(
        db,
        tenant_id,
        identity=identity,
        record_category=record_category,
    )
    lifecycle_rule = _resolve_record_lifecycle_rule(
        db,
        tenant_id,
        identity=identity,
        record_category=record_category,
    )
    retention_schedule = _resolve_retention_schedule_config(
        db,
        tenant_id,
        identity=identity,
        record_category=record_category,
    )
    vital_policy = _resolve_vital_policy(
        db,
        tenant_id,
        identity=identity,
        record_category=record_category,
    )
    assignment_rule = _resolve_assignment_rule(
        db,
        tenant_id,
        identity=identity,
        record_category=record_category,
        assignment_context="DECLARATION",
    )
    workflow_routing = _build_assignment_routing(assignment_rule)
    evaluation_context = _build_declaration_context(
        db,
        tenant_id,
        identity=identity,
        version=version,
    )
    vital_status, vital_profile = _resolve_vital_runtime(
        vital_policy=vital_policy,
        evaluation_context=evaluation_context,
        declared_at=_now(),
    )
    lifecycle = apply_record_lifecycle_transition(
        db,
        tenant_id,
        identity_id=identity.identity_id,
        version_id=version.version_id if version else None,
        transition_code="DECLARE_RECORD",
        trigger_event="DECLARED_RECORD",
        lifecycle_rule=lifecycle_rule,
        performed_by=declared_by,
        reason=declaration_reason,
        metadata_json={
            "record_category": record_category,
            **(metadata_json or {}),
        },
    )
    activity_fields = _activity_fields_from_transition(lifecycle)
    retention_rule = resolve_retention_rule(
        db,
        tenant_id,
        identity_id=identity_id,
        record_category=record_category,
    )
    source_event_id = lifecycle["events"][0]["event_id"] if lifecycle.get("events") else None
    declarations = _table(db, "symployee_record_declarations")
    record_declaration_id = _new_id("SRD")
    db.execute(
        declarations.insert().values(
            record_declaration_id=record_declaration_id,
            tenant_id=tenant_id,
            identity_id=identity.identity_id,
            version_id=version.version_id if version else None,
            record_category=record_category,
            record_status="DECLARED_RECORD",
            record_stage=activity_fields.get("record_stage"),
            active_from=activity_fields.get("active_from"),
            inactive_from=activity_fields.get("inactive_from"),
            inactive_reason_code=activity_fields.get("inactive_reason_code"),
            vital_status=vital_status,
            inactive_reason=activity_fields.get("inactive_reason"),
            owner_user_id=owner_user_id,
            declared_at=_now(),
            declared_by=declared_by,
            declaration_reason=declaration_reason or None,
            source_event_id=source_event_id,
            declaration_rule_id=(
                declaration_rule["declaration_rule_id"] if declaration_rule else None
            ),
            lifecycle_rule_id=(
                lifecycle_rule["lifecycle_rule_id"] if lifecycle_rule else None
            ),
            retention_schedule_id=(
                retention_schedule["retention_schedule_id"] if retention_schedule else None
            ),
            metadata_json={
                "config_linkage": {
                    "declaration_rule_id": declaration_rule["declaration_rule_id"] if declaration_rule else None,
                "lifecycle_rule_id": lifecycle_rule["lifecycle_rule_id"] if lifecycle_rule else None,
                "retention_schedule_id": retention_schedule["retention_schedule_id"] if retention_schedule else None,
                "vital_policy_id": vital_policy["vital_policy_id"] if vital_policy else None,
                "assignment_rule_id": assignment_rule["assignment_rule_id"] if assignment_rule else None,
                },
                "lifecycle_transition": lifecycle,
                "retention_rule": retention_rule,
                "vital_profile": vital_profile,
                "workflow_routing": workflow_routing,
                **(metadata_json or {}),
            },
            created_by=declared_by,
            created_at=_now(),
            modified_by=declared_by,
            modified_at=_now(),
        )
    )
    db.commit()
    return {
        "record_declaration_id": record_declaration_id,
        "identity_id": identity.identity_id,
        "version_id": version.version_id if version else None,
        "record_status": "DECLARED_RECORD",
        "record_category": record_category,
        "vital_status": vital_status,
        "vital_profile": vital_profile,
        "inactive_reason": None,
        "declaration_rule_id": declaration_rule["declaration_rule_id"] if declaration_rule else None,
        "lifecycle_rule_id": lifecycle_rule["lifecycle_rule_id"] if lifecycle_rule else None,
        "retention_schedule_id": retention_schedule["retention_schedule_id"] if retention_schedule else None,
        "vital_policy_id": vital_policy["vital_policy_id"] if vital_policy else None,
        "assignment_rule_id": assignment_rule["assignment_rule_id"] if assignment_rule else None,
        "workflow_routing": workflow_routing,
        "source_event_id": source_event_id,
        "activity_stage": _resolve_initial_activity_stage(lifecycle),
        "record_stage": activity_fields.get("record_stage"),
        "active_from": activity_fields.get("active_from").isoformat() if activity_fields.get("active_from") else None,
        "inactive_from": activity_fields.get("inactive_from").isoformat() if activity_fields.get("inactive_from") else None,
        "inactive_reason_code": activity_fields.get("inactive_reason_code"),
        "lifecycle_transition": lifecycle,
        "retention_rule": retention_rule,
        "existing": False,
    }


def place_legal_hold(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    hold_category: str | None,
    hold_code: str,
    authority: str,
    placed_by: str | None = None,
    reason: str = "",
    matter_reference: str | None = None,
    metadata_json: dict | None = None,
) -> dict:
    resolved_hold_category = _normalize_hold_category(hold_category)
    identity = _require_identity(db, tenant_id, identity_id)
    existing_hold = _find_active_legal_hold(db, tenant_id, identity_id, hold_code)
    if existing_hold:
        return {
            "legal_hold_id": existing_hold.legal_hold_id,
            "hold_status": existing_hold.hold_status,
            "existing": True,
        }

    declaration = _active_record_declaration(db, tenant_id, identity_id)
    hold_policy = _resolve_hold_policy(
        db,
        tenant_id,
        identity=identity,
        record_category=declaration.record_category if declaration else None,
        hold_category=resolved_hold_category,
    )
    assignment_rule = _resolve_assignment_rule(
        db,
        tenant_id,
        identity=identity,
        record_category=declaration.record_category if declaration else None,
        assignment_context="HOLD_PLACEMENT",
    ) if declaration else None
    workflow_routing = _build_assignment_routing(assignment_rule)
    lifecycle = apply_record_lifecycle_transition(
        db,
        tenant_id,
        identity_id=identity.identity_id,
        version_id=identity.current_version_id,
        transition_code="PLACE_HOLD",
        trigger_event="HOLD_PLACEMENT",
        lifecycle_rule=None,
        performed_by=placed_by,
        reason=reason,
        metadata_json={
            "hold_category": resolved_hold_category,
            "hold_code": hold_code,
            "authority": authority,
            "matter_reference": matter_reference,
            **(metadata_json or {}),
        },
    )
    holds = _table(db, "symployee_record_legal_holds")
    legal_hold_id = _new_id("SLH")
    db.execute(
        holds.insert().values(
            legal_hold_id=legal_hold_id,
            tenant_id=tenant_id,
            identity_id=identity.identity_id,
            record_declaration_id=declaration.record_declaration_id if declaration else None,
            hold_policy_id=hold_policy["hold_policy_id"] if hold_policy else None,
            hold_category=resolved_hold_category,
            hold_code=hold_code,
            hold_status="ACTIVE",
            authority=authority,
            matter_reference=matter_reference,
            reason=reason or None,
            placed_at=_now(),
            placed_by=placed_by,
            metadata_json={
                "source_event_id": lifecycle["events"][0]["event_id"] if lifecycle.get("events") else None,
                "prior_record_status": lifecycle.get("starting_state", {}).get("record_status"),
                "prior_document_lifecycle_stage": lifecycle.get("starting_state", {}).get("document_lifecycle_stage"),
                "lifecycle_transition": lifecycle,
                "config_linkage": {
                    "hold_policy_id": hold_policy["hold_policy_id"] if hold_policy else None,
                },
                "workflow_routing": workflow_routing,
                **(metadata_json or {}),
            },
            created_by=placed_by,
            created_at=_now(),
            modified_by=placed_by,
            modified_at=_now(),
        )
    )
    db.commit()
    return {
        "legal_hold_id": legal_hold_id,
        "identity_id": identity.identity_id,
        "record_declaration_id": declaration.record_declaration_id if declaration else None,
        "hold_policy_id": hold_policy["hold_policy_id"] if hold_policy else None,
        "hold_category": resolved_hold_category,
        "hold_status": "ACTIVE",
        "assignment_rule_id": assignment_rule.get("assignment_rule_id") if assignment_rule else None,
        "workflow_routing": workflow_routing,
        "source_event_id": lifecycle["events"][0]["event_id"] if lifecycle.get("events") else None,
        "lifecycle_transition": lifecycle,
        "existing": False,
    }


def release_legal_hold(
    db: Session,
    tenant_id: str,
    *,
    legal_hold_id: str,
    released_by: str | None = None,
    release_reason: str = "",
    metadata_json: dict | None = None,
) -> dict:
    holds = _table(db, "symployee_record_legal_holds")
    hold = db.execute(
        holds.select().where(
            holds.c.tenant_id == tenant_id,
            holds.c.legal_hold_id == legal_hold_id,
        )
    ).fetchone()
    if not hold:
        raise ValueError("Legal hold not found")
    if hold.hold_status != "ACTIVE":
        return {
            "legal_hold_id": hold.legal_hold_id,
            "hold_status": hold.hold_status,
            "existing": True,
            "hold_policy_id": getattr(hold, "hold_policy_id", None),
        }

    remaining_active_hold = db.execute(
        holds.select().where(
            holds.c.tenant_id == tenant_id,
            holds.c.identity_id == hold.identity_id,
            holds.c.hold_status == "ACTIVE",
            holds.c.legal_hold_id != legal_hold_id,
        ).limit(1)
    ).fetchone()
    target_record_status = (
        "UNDER_LEGAL_HOLD"
        if remaining_active_hold
        else (
            dict(hold.metadata_json or {}).get("prior_record_status")
            or "DECLARED_RECORD"
        )
    )
    lifecycle = apply_record_lifecycle_transition(
        db,
        tenant_id,
        identity_id=hold.identity_id,
        version_id=None,
        transition_code="RELEASE_HOLD",
        trigger_event="HOLD_RELEASE",
        lifecycle_rule=None,
        performed_by=released_by,
        reason=release_reason,
        hold_restore_record_status=target_record_status,
        metadata_json={
            "legal_hold_id": legal_hold_id,
            **(metadata_json or {}),
        },
    )
    db.execute(
        holds.update()
        .where(
            holds.c.tenant_id == tenant_id,
            holds.c.legal_hold_id == legal_hold_id,
        )
        .values(
            hold_status="RELEASED",
            released_at=_now(),
            released_by=released_by,
            release_reason=release_reason or None,
            metadata_json={
                **dict(hold.metadata_json or {}),
                "release_event_id": lifecycle["events"][0]["event_id"] if lifecycle.get("events") else None,
                "lifecycle_transition": lifecycle,
                **(metadata_json or {}),
            },
            modified_by=released_by,
            modified_at=_now(),
        )
    )
    activity_updates = _sync_declaration_activity_fields(
        db,
        tenant_id,
        identity_id=hold.identity_id,
        lifecycle_transition=lifecycle,
    )
    db.commit()
    return {
        "legal_hold_id": legal_hold_id,
        "hold_status": "RELEASED",
        "hold_policy_id": getattr(hold, "hold_policy_id", None),
        "source_event_id": lifecycle["events"][0]["event_id"] if lifecycle.get("events") else None,
        "record_status": target_record_status,
        "activity_updates": activity_updates,
        "lifecycle_transition": lifecycle,
    }


def create_disposition_case(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    disposition_type: str,
    requested_by: str | None = None,
    reason: str = "",
    metadata_json: dict | None = None,
) -> dict:
    identity = _require_identity(db, tenant_id, identity_id)
    declaration = _active_record_declaration(db, tenant_id, identity_id)
    if not declaration:
        raise ValueError("Record declaration is required before creating a disposition case")

    retention_rule = resolve_retention_rule(
        db,
        tenant_id,
        identity_id=identity_id,
        record_category=declaration.record_category,
    )
    disposition_policy = _resolve_disposition_policy(
        db,
        tenant_id,
        identity=identity,
        record_category=declaration.record_category,
        disposition_type=disposition_type,
    )
    assignment_rule = _resolve_assignment_rule(
        db,
        tenant_id,
        identity=identity,
        record_category=declaration.record_category,
        assignment_context="DISPOSITION_APPROVAL",
    )
    workflow_routing = _build_assignment_routing(assignment_rule)
    eligibility_date = None
    if retention_rule:
        retention_anchor = declaration.declared_at or _now()
        eligibility_date = _add_retention_period(
            retention_anchor,
            int(retention_rule["retention_period_value"]),
            str(retention_rule["retention_period_unit"]),
        )

    lifecycle = apply_record_lifecycle_transition(
        db,
        tenant_id,
        identity_id=identity.identity_id,
        version_id=identity.current_version_id,
        transition_code="MARK_DISPOSITION_PENDING",
        trigger_event="DISPOSITION_REQUESTED",
        lifecycle_rule=None,
        performed_by=requested_by,
        reason=reason,
        metadata_json={
            "disposition_type": disposition_type,
            "eligibility_date": eligibility_date.isoformat() if eligibility_date else None,
            **(metadata_json or {}),
        },
    )
    cases = _table(db, "symployee_disposition_cases")
    disposition_case_id = _new_id("SDC")
    db.execute(
        cases.insert().values(
            disposition_case_id=disposition_case_id,
            tenant_id=tenant_id,
            identity_id=identity.identity_id,
            record_declaration_id=declaration.record_declaration_id,
            retention_rule_id=retention_rule["retention_rule_id"] if retention_rule else None,
            disposition_policy_id=(
                disposition_policy["disposition_policy_id"] if disposition_policy else None
            ),
            disposition_type=disposition_type,
            case_status="PENDING_REVIEW",
            eligibility_date=eligibility_date,
            requested_at=_now(),
            requested_by=requested_by,
            reason=reason or None,
            metadata_json={
                "source_event_id": lifecycle["events"][0]["event_id"] if lifecycle.get("events") else None,
                "lifecycle_transition": lifecycle,
                "config_linkage": {
                    "disposition_policy_id": disposition_policy["disposition_policy_id"] if disposition_policy else None,
                    "retention_schedule_id": getattr(declaration, "retention_schedule_id", None),
                },
                "workflow_routing": workflow_routing,
                **(metadata_json or {}),
            },
            created_by=requested_by,
            created_at=_now(),
            modified_by=requested_by,
            modified_at=_now(),
        )
    )
    activity_updates = _sync_declaration_activity_fields(
        db,
        tenant_id,
        identity_id=identity.identity_id,
        lifecycle_transition=lifecycle,
    )
    db.commit()
    return {
        "disposition_case_id": disposition_case_id,
        "identity_id": identity.identity_id,
        "record_declaration_id": declaration.record_declaration_id,
        "retention_rule_id": retention_rule["retention_rule_id"] if retention_rule else None,
        "retention_schedule_id": getattr(declaration, "retention_schedule_id", None),
        "disposition_policy_id": disposition_policy["disposition_policy_id"] if disposition_policy else None,
        "assignment_rule_id": assignment_rule.get("assignment_rule_id") if assignment_rule else None,
        "workflow_routing": workflow_routing,
        "case_status": "PENDING_REVIEW",
        "eligibility_date": eligibility_date.isoformat() if eligibility_date else None,
        "source_event_id": lifecycle["events"][0]["event_id"] if lifecycle.get("events") else None,
        "activity_updates": activity_updates,
        "lifecycle_transition": lifecycle,
    }


def initiate_archive_transfer(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    archive_destination: str,
    requested_by: str | None = None,
    disposition_case_id: str | None = None,
    preservation_format: str | None = None,
    checksum_value: str | None = None,
    checksum_algorithm: str | None = None,
    metadata_json: dict | None = None,
) -> dict:
    identity = _require_identity(db, tenant_id, identity_id)
    declaration = _active_record_declaration(db, tenant_id, identity_id)
    if not declaration:
        raise ValueError("Record declaration is required before initiating archive transfer")

    archive_policy = _resolve_archive_policy(
        db,
        tenant_id,
        identity=identity,
        record_category=declaration.record_category,
    )
    assignment_rule = _resolve_assignment_rule(
        db,
        tenant_id,
        identity=identity,
        record_category=declaration.record_category,
        assignment_context="ARCHIVE_TRANSFER",
    )
    workflow_routing = _build_assignment_routing(assignment_rule)
    lifecycle = apply_record_lifecycle_transition(
        db,
        tenant_id,
        identity_id=identity.identity_id,
        version_id=identity.current_version_id,
        transition_code="MARK_ARCHIVE_PENDING",
        trigger_event="ARCHIVE_TRANSFER_REQUESTED",
        lifecycle_rule=None,
        performed_by=requested_by,
        reason="Archive transfer initiated",
        metadata_json={
            "archive_destination": archive_destination,
            "disposition_case_id": disposition_case_id,
            **(metadata_json or {}),
        },
    )
    transfers = _table(db, "symployee_archive_transfers")
    archive_transfer_id = _new_id("SAT")
    db.execute(
        transfers.insert().values(
            archive_transfer_id=archive_transfer_id,
            tenant_id=tenant_id,
            identity_id=identity.identity_id,
            record_declaration_id=declaration.record_declaration_id,
            disposition_case_id=disposition_case_id,
            archive_policy_id=archive_policy["archive_policy_id"] if archive_policy else None,
            transfer_status="PENDING",
            archive_destination=archive_destination,
            preservation_format=preservation_format,
            checksum_value=checksum_value,
            checksum_algorithm=checksum_algorithm,
            requested_at=_now(),
            requested_by=requested_by,
            metadata_json={
                "source_event_id": lifecycle["events"][0]["event_id"] if lifecycle.get("events") else None,
                "lifecycle_transition": lifecycle,
                "config_linkage": {
                    "archive_policy_id": archive_policy["archive_policy_id"] if archive_policy else None,
                },
                "workflow_routing": workflow_routing,
                **(metadata_json or {}),
            },
            created_by=requested_by,
            created_at=_now(),
            modified_by=requested_by,
            modified_at=_now(),
        )
    )
    activity_updates = _sync_declaration_activity_fields(
        db,
        tenant_id,
        identity_id=identity.identity_id,
        lifecycle_transition=lifecycle,
    )
    db.commit()
    return {
        "archive_transfer_id": archive_transfer_id,
        "identity_id": identity.identity_id,
        "record_declaration_id": declaration.record_declaration_id,
        "disposition_case_id": disposition_case_id,
        "archive_policy_id": archive_policy["archive_policy_id"] if archive_policy else None,
        "assignment_rule_id": assignment_rule.get("assignment_rule_id") if assignment_rule else None,
        "workflow_routing": workflow_routing,
        "transfer_status": "PENDING",
        "archive_destination": archive_destination,
        "source_event_id": lifecycle["events"][0]["event_id"] if lifecycle.get("events") else None,
        "activity_updates": activity_updates,
        "lifecycle_transition": lifecycle,
    }
