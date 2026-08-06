from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import MetaData, Table
from sqlalchemy.orm import Session

from app.db_models import SymployeeDocumentIdentity, SymployeeDocumentVersion


IDENTITY_STATE_FIELDS = {
    "document_lifecycle_stage",
    "review_status",
    "issue_status",
    "record_status",
    "retention_status",
    "disposition_status",
    "security_status",
}
VERSION_STATE_FIELDS = {
    "revision_status",
    "issue_status",
}
STATE_VOCABULARY = {
    "document_lifecycle_stage": {
        "PLANNED",
        "DRAFT",
        "REGISTERED",
        "UNDER_REVIEW",
        "APPROVED",
        "ISSUED",
        "ACTIVE",
        "SUPERSEDED",
        "WITHDRAWN",
        "INACTIVE",
        "ARCHIVED",
        "DISPOSED",
    },
    "review_status": {
        "AWAITING_REVIEW",
        "IN_REVIEW",
        "REVIEW_COMPLETED",
        "REVIEW_REJECTED",
    },
    "issue_status": {
        "RECEIVED",
        "ISSUED",
        "AWAITING_ACKNOWLEDGEMENT",
        "ACKNOWLEDGED",
        "RESPONDED",
        "RESPONSE_OVERDUE",
    },
    "record_status": {
        "NON_RECORD",
        "RECORD_CANDIDATE",
        "DECLARED_RECORD",
        "UNDER_LEGAL_HOLD",
        "ARCHIVED",
        "DISPOSITION_PENDING",
        "DESTROYED",
        "PERMANENT",
    },
    "retention_status": {
        "NOT_CLASSIFIED",
        "SCHEDULED",
        "ELIGIBLE_FOR_DISPOSITION",
        "ON_HOLD",
        "COMPLETED",
    },
    "disposition_status": {
        "PENDING_REVIEW",
        "APPROVED",
        "EXECUTED",
        "ARCHIVE_TRANSFER_PENDING",
        "COMPLETED",
    },
    "security_status": {
        "UNCLASSIFIED",
        "INTERNAL",
        "CONFIDENTIAL",
        "RESTRICTED",
    },
    "revision_status": {
        "CURRENT",
        "SUPERSEDED",
        "WITHDRAWN",
    },
}


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{str(uuid4())[:12].upper()}"


def _lifecycle_events_table(db: Session) -> Table:
    return Table(
        "symployee_document_lifecycle_events",
        MetaData(),
        autoload_with=db.get_bind(),
    )


def _record_declarations_table(db: Session) -> Table:
    return Table(
        "symployee_record_declarations",
        MetaData(),
        autoload_with=db.get_bind(),
    )


def _workflow_instances_table(db: Session) -> Table:
    return Table(
        "symployee_workflow_instances",
        MetaData(),
        autoload_with=db.get_bind(),
    )


def _serialize_lifecycle_event(row) -> dict:
    return {
        "event_id": row.event_id,
        "tenant_id": row.tenant_id,
        "identity_id": row.identity_id,
        "version_id": row.version_id,
        "event_type": row.event_type,
        "state_dimension": row.state_dimension,
        "previous_state": row.previous_state,
        "new_state": row.new_state,
        "event_date": row.event_date.isoformat() if row.event_date else None,
        "performed_by": row.performed_by,
        "reason": row.reason,
        "workflow_instance_id": row.workflow_instance_id,
        "transmittal_id": row.transmittal_id,
        "approval_id": row.approval_id,
        "metadata_json": row.metadata_json or {},
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "modified_by": row.modified_by,
        "modified_at": row.modified_at.isoformat() if row.modified_at else None,
    }


def _resolve_state_target(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    version_id: str | None,
    state_dimension: str,
) -> tuple[object, str]:
    if state_dimension in VERSION_STATE_FIELDS and version_id:
        version = (
            db.query(SymployeeDocumentVersion)
            .filter(
                SymployeeDocumentVersion.tenant_id == tenant_id,
                SymployeeDocumentVersion.version_id == version_id,
                SymployeeDocumentVersion.identity_id == identity_id,
            )
            .first()
        )
        if not version:
            raise ValueError("Document version not found for lifecycle transition")
        return version, "version"

    if state_dimension in VERSION_STATE_FIELDS and state_dimension not in IDENTITY_STATE_FIELDS:
        if not version_id:
            raise ValueError(f"version_id is required for state dimension '{state_dimension}'")
        raise ValueError("Document version not found for lifecycle transition")

    if state_dimension in IDENTITY_STATE_FIELDS:
        identity = (
            db.query(SymployeeDocumentIdentity)
            .filter(
                SymployeeDocumentIdentity.tenant_id == tenant_id,
                SymployeeDocumentIdentity.identity_id == identity_id,
            )
            .first()
        )
        if not identity:
            raise ValueError("Document identity not found for lifecycle transition")
        return identity, "identity"

    raise ValueError(f"Unsupported lifecycle state dimension '{state_dimension}'")


def _validate_state_value(state_dimension: str, new_state: str) -> None:
    allowed_states = STATE_VOCABULARY.get(state_dimension)
    if not allowed_states:
        return
    if new_state not in allowed_states:
        raise ValueError(
            f"Unsupported state '{new_state}' for lifecycle dimension '{state_dimension}'"
        )


def _normalize_event_code(value: str | None) -> str:
    return str(value or "").strip().upper().replace("-", "_").replace(" ", "_")


def _resolve_lifecycle_clock_anchor(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    version_id: str | None,
    lifecycle_rule: dict,
) -> datetime | None:
    basis = _normalize_event_code(lifecycle_rule.get("lifecycle_clock_basis"))
    if basis == "DECLARATION_DATE":
        declarations = _record_declarations_table(db)
        row = db.execute(
            declarations.select()
            .where(
                declarations.c.tenant_id == tenant_id,
                declarations.c.identity_id == identity_id,
            )
            .order_by(
                declarations.c.declared_at.desc(),
                declarations.c.created_at.desc(),
            )
            .limit(1)
        ).fetchone()
        return row.declared_at if row else None

    if basis == "WORKFLOW_COMPLETE_DATE":
        workflow_instances = _workflow_instances_table(db)
        query = (
            workflow_instances.select()
            .where(
                workflow_instances.c.tenant_id == tenant_id,
                workflow_instances.c.identity_id == identity_id,
                workflow_instances.c.completed_at.is_not(None),
            )
            .order_by(workflow_instances.c.completed_at.desc())
            .limit(1)
        )
        if version_id:
            query = query.where(workflow_instances.c.version_id == version_id)
        row = db.execute(query).fetchone()
        return row.completed_at if row else None

    if basis == "LAST_ACTIVITY_DATE":
        lifecycle_events = _lifecycle_events_table(db)
        query = (
            lifecycle_events.select()
            .where(
                lifecycle_events.c.tenant_id == tenant_id,
                lifecycle_events.c.identity_id == identity_id,
            )
            .order_by(
                lifecycle_events.c.event_date.desc(),
                lifecycle_events.c.created_at.desc(),
            )
            .limit(1)
        )
        if version_id:
            query = query.where(
                (lifecycle_events.c.version_id == version_id)
                | (lifecycle_events.c.version_id.is_(None))
            )
        row = db.execute(query).fetchone()
        return row.event_date if row else None

    return None


def _get_identity_snapshot(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
) -> dict[str, str | None]:
    identity = (
        db.query(SymployeeDocumentIdentity)
        .filter(
            SymployeeDocumentIdentity.tenant_id == tenant_id,
            SymployeeDocumentIdentity.identity_id == identity_id,
        )
        .first()
    )
    if not identity:
        raise ValueError("Document identity not found for lifecycle transition")
    return {
        "document_lifecycle_stage": identity.document_lifecycle_stage,
        "record_status": identity.record_status,
        "retention_status": identity.retention_status,
        "disposition_status": identity.disposition_status,
    }


def create_lifecycle_event(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    version_id: str | None,
    event_type: str,
    state_dimension: str,
    previous_state: str | None,
    new_state: str,
    performed_by: str | None = None,
    reason: str = "",
    workflow_instance_id: str | None = None,
    transmittal_id: str | None = None,
    approval_id: str | None = None,
    metadata_json: dict | None = None,
    created_by: str | None = None,
) -> dict:
    _validate_state_value(state_dimension, new_state)
    event_id = _new_id("SLE")
    now = _now()
    db.execute(
        _lifecycle_events_table(db).insert().values(
            event_id=event_id,
            tenant_id=tenant_id,
            identity_id=identity_id,
            version_id=version_id,
            event_type=event_type,
            state_dimension=state_dimension,
            previous_state=previous_state,
            new_state=new_state,
            event_date=now,
            performed_by=performed_by,
            reason=reason or None,
            workflow_instance_id=workflow_instance_id,
            transmittal_id=transmittal_id,
            approval_id=approval_id,
            metadata_json=metadata_json or {},
            created_by=created_by or performed_by,
            created_at=now,
            modified_by=created_by or performed_by,
            modified_at=now,
        )
    )
    return {
        "event_id": event_id,
        "tenant_id": tenant_id,
        "identity_id": identity_id,
        "version_id": version_id,
        "event_type": event_type,
        "state_dimension": state_dimension,
        "previous_state": previous_state,
        "new_state": new_state,
        "performed_by": performed_by,
        "reason": reason,
        "workflow_instance_id": workflow_instance_id,
        "transmittal_id": transmittal_id,
        "approval_id": approval_id,
        "metadata_json": metadata_json or {},
        "created_at": now.isoformat(),
    }


def apply_state_transition(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    version_id: str | None,
    state_dimension: str,
    new_state: str,
    event_type: str,
    performed_by: str | None = None,
    reason: str = "",
    workflow_instance_id: str | None = None,
    transmittal_id: str | None = None,
    approval_id: str | None = None,
    metadata_json: dict | None = None,
    expected_previous_state: str | None = None,
    commit: bool = False,
) -> dict:
    _validate_state_value(state_dimension, new_state)
    target, target_scope = _resolve_state_target(
        db,
        tenant_id,
        identity_id=identity_id,
        version_id=version_id,
        state_dimension=state_dimension,
    )
    previous_state = getattr(target, state_dimension, None)
    if expected_previous_state is not None and previous_state != expected_previous_state:
        raise ValueError(
            f"Lifecycle transition conflict for {state_dimension}: "
            f"expected '{expected_previous_state}' but found '{previous_state}'"
        )

    changed = previous_state != new_state
    if changed:
        setattr(target, state_dimension, new_state)

    event = create_lifecycle_event(
        db,
        tenant_id,
        identity_id=identity_id,
        version_id=version_id,
        event_type=event_type,
        state_dimension=state_dimension,
        previous_state=previous_state,
        new_state=new_state,
        performed_by=performed_by,
        reason=reason,
        workflow_instance_id=workflow_instance_id,
        transmittal_id=transmittal_id,
        approval_id=approval_id,
        metadata_json={
            "target_scope": target_scope,
            "changed": changed,
            **(metadata_json or {}),
        },
        created_by=performed_by,
    )
    if commit:
        db.commit()

    return {
        **event,
        "target_scope": target_scope,
        "changed": changed,
    }


def list_lifecycle_events(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str | None = None,
    version_id: str | None = None,
    state_dimension: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
) -> dict:
    events_table = _lifecycle_events_table(db)
    query = (
        events_table.select()
        .where(events_table.c.tenant_id == tenant_id)
        .order_by(events_table.c.event_date.desc(), events_table.c.created_at.desc())
        .limit(max(1, min(limit, 500)))
    )
    if identity_id:
        query = query.where(events_table.c.identity_id == identity_id)
    if version_id:
        query = query.where(events_table.c.version_id == version_id)
    if state_dimension:
        query = query.where(events_table.c.state_dimension == state_dimension)
    if event_type:
        query = query.where(events_table.c.event_type == event_type)

    rows = db.execute(query).fetchall()
    return {
        "items": [_serialize_lifecycle_event(row) for row in rows],
        "filters": {
            "tenant_id": tenant_id,
            "identity_id": identity_id,
            "version_id": version_id,
            "state_dimension": state_dimension,
            "event_type": event_type,
            "limit": max(1, min(limit, 500)),
        },
    }


def create_lifecycle_transition(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    version_id: str | None,
    state_dimension: str,
    new_state: str,
    performed_by: str | None,
    reason: str = "",
    metadata_json: dict | None = None,
) -> dict:
    return apply_state_transition(
        db,
        tenant_id,
        identity_id=identity_id,
        version_id=version_id,
        state_dimension=state_dimension,
        new_state=new_state,
        event_type="STATE_TRANSITION",
        performed_by=performed_by,
        reason=reason,
        metadata_json=metadata_json,
        commit=False,
    )


def apply_record_lifecycle_transition(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    version_id: str | None,
    transition_code: str,
    trigger_event: str,
    lifecycle_rule: dict | None = None,
    performed_by: str | None = None,
    reason: str = "",
    metadata_json: dict | None = None,
    hold_restore_record_status: str | None = None,
    commit: bool = False,
) -> dict:
    normalized_transition = _normalize_event_code(transition_code)
    normalized_trigger = _normalize_event_code(trigger_event)
    rule = dict(lifecycle_rule or {})
    active_start_event = _normalize_event_code(rule.get("active_start_event"))
    inactive_eligibility_event = _normalize_event_code(rule.get("inactive_eligibility_event"))
    inactive_after_days = rule.get("inactive_after_days")
    reopen_events = {
        _normalize_event_code(value)
        for value in list(rule.get("reopen_trigger_events_json") or [])
        if value
    }
    starting_state = _get_identity_snapshot(
        db,
        tenant_id,
        identity_id=identity_id,
    )
    transition_events: list[dict] = []

    def _append_transition(
        *,
        state_dimension: str,
        new_state: str,
        event_type: str,
        extra_metadata: dict | None = None,
    ) -> None:
        transition_events.append(
            apply_state_transition(
                db,
                tenant_id,
                identity_id=identity_id,
                version_id=version_id,
                state_dimension=state_dimension,
                new_state=new_state,
                event_type=event_type,
                performed_by=performed_by,
                reason=reason,
                metadata_json={
                    "transition_code": normalized_transition,
                    "trigger_event": normalized_trigger,
                    "lifecycle_rule_id": rule.get("lifecycle_rule_id"),
                    **dict(metadata_json or {}),
                    **dict(extra_metadata or {}),
                },
                commit=False,
            )
        )

    if normalized_transition == "DECLARE_RECORD":
        _append_transition(
            state_dimension="record_status",
            new_state="DECLARED_RECORD",
            event_type="RECORD_DECLARED",
        )
        if active_start_event and normalized_trigger == active_start_event:
            _append_transition(
                state_dimension="document_lifecycle_stage",
                new_state="ACTIVE",
                event_type="RECORD_BECAME_ACTIVE",
            )
    elif normalized_transition == "ACTIVATE_RECORD":
        _append_transition(
            state_dimension="document_lifecycle_stage",
            new_state="ACTIVE",
            event_type="RECORD_BECAME_ACTIVE",
        )
    elif normalized_transition == "INACTIVATE_RECORD":
        _append_transition(
            state_dimension="document_lifecycle_stage",
            new_state="INACTIVE",
            event_type="RECORD_BECAME_INACTIVE",
        )
    elif normalized_transition == "PLACE_HOLD":
        _append_transition(
            state_dimension="record_status",
            new_state="UNDER_LEGAL_HOLD",
            event_type="LEGAL_HOLD_PLACED",
            extra_metadata={
                "prior_record_status": starting_state.get("record_status"),
                "prior_document_lifecycle_stage": starting_state.get("document_lifecycle_stage"),
            },
        )
    elif normalized_transition == "RELEASE_HOLD":
        _append_transition(
            state_dimension="record_status",
            new_state=hold_restore_record_status or "DECLARED_RECORD",
            event_type="LEGAL_HOLD_RELEASED",
        )
    elif normalized_transition == "MARK_DISPOSITION_PENDING":
        _append_transition(
            state_dimension="record_status",
            new_state="DISPOSITION_PENDING",
            event_type="RECORD_MARKED_FOR_DISPOSITION",
        )
        _append_transition(
            state_dimension="disposition_status",
            new_state="PENDING_REVIEW",
            event_type="DISPOSITION_CASE_CREATED",
        )
    elif normalized_transition == "MARK_ARCHIVE_PENDING":
        _append_transition(
            state_dimension="disposition_status",
            new_state="ARCHIVE_TRANSFER_PENDING",
            event_type="ARCHIVE_TRANSFER_INITIATED",
        )
    elif normalized_transition == "MARK_ARCHIVED":
        _append_transition(
            state_dimension="document_lifecycle_stage",
            new_state="ARCHIVED",
            event_type="RECORD_ARCHIVED",
        )
        _append_transition(
            state_dimension="record_status",
            new_state="ARCHIVED",
            event_type="RECORD_ARCHIVED",
        )
    elif normalized_transition == "EVALUATE_RULE":
        if active_start_event and normalized_trigger == active_start_event:
            _append_transition(
                state_dimension="document_lifecycle_stage",
                new_state="ACTIVE",
                event_type="RECORD_BECAME_ACTIVE",
            )
        elif inactive_eligibility_event and normalized_trigger == inactive_eligibility_event:
            if inactive_after_days in (None, 0, "0"):
                _append_transition(
                    state_dimension="document_lifecycle_stage",
                    new_state="INACTIVE",
                    event_type="RECORD_BECAME_INACTIVE",
                    extra_metadata={
                        "inactive_reason_code": "RULE_EVENT_ELIGIBLE",
                    },
                )
        elif normalized_trigger == "TIME_EVALUATION" and inactive_eligibility_event:
            anchor_at = _resolve_lifecycle_clock_anchor(
                db,
                tenant_id,
                identity_id=identity_id,
                version_id=version_id,
                lifecycle_rule=rule,
            )
            if (
                anchor_at
                and inactive_after_days not in (None, "", 0, "0")
                and starting_state.get("document_lifecycle_stage") != "INACTIVE"
            ):
                due_at = anchor_at + timedelta(days=int(inactive_after_days))
                if _now() >= due_at:
                    _append_transition(
                        state_dimension="document_lifecycle_stage",
                        new_state="INACTIVE",
                        event_type="RECORD_BECAME_INACTIVE",
                        extra_metadata={
                            "inactive_reason_code": "RULE_INACTIVITY_TIMEOUT",
                            "lifecycle_clock_basis": rule.get("lifecycle_clock_basis"),
                            "anchor_at": anchor_at.isoformat(),
                            "due_at": due_at.isoformat(),
                        },
                    )
                else:
                    transition_events.append(
                        {
                            "changed": False,
                            "event_type": "RECORD_INACTIVITY_NOT_DUE",
                            "anchor_at": anchor_at.isoformat(),
                            "due_at": due_at.isoformat(),
                        }
                    )
            else:
                transition_events.append(
                    {
                        "changed": False,
                        "event_type": "RECORD_INACTIVITY_NOT_ELIGIBLE",
                        "lifecycle_clock_basis": rule.get("lifecycle_clock_basis"),
                        "anchor_at": anchor_at.isoformat() if anchor_at else None,
                    }
                )
        elif (
            rule.get("reopen_to_active_allowed")
            and normalized_trigger in reopen_events
        ):
            _append_transition(
                state_dimension="document_lifecycle_stage",
                new_state="ACTIVE",
                event_type="RECORD_REOPENED_TO_ACTIVE",
            )
    else:
        raise ValueError(f"Unsupported record lifecycle transition '{transition_code}'")

    if commit:
        db.commit()

    ending_state = _get_identity_snapshot(
        db,
        tenant_id,
        identity_id=identity_id,
    )
    return {
        "transition_code": normalized_transition,
        "trigger_event": normalized_trigger,
        "lifecycle_rule_id": rule.get("lifecycle_rule_id"),
        "starting_state": starting_state,
        "ending_state": ending_state,
        "events": transition_events,
        "changed": any(event.get("changed") for event in transition_events),
    }
