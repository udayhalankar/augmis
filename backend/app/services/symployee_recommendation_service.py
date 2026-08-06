from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db_models import (
    SymployeeAIRecommendation,
    SymployeeApprovalRecord,
    SymployeeConnectorCommand,
    SymployeeDocumentIdentity,
    SymployeeDefinition,
    SymployeeOverrideRecord,
)
from app.services.audit_service import create_audit_log
from app.services.symployee_lifecycle_service import create_lifecycle_event
from app.services.symployee_records_service import (
    evaluate_record_declaration,
    evaluate_record_lifecycle_rule,
)
from app.services.symployee_workflow_service import sync_document_workflow


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{str(uuid4())[:12].upper()}"


def _build_recommendation_lifecycle_context(
    recommendation: SymployeeAIRecommendation,
    extra: dict | None = None,
) -> dict:
    return {
        **dict(recommendation.lifecycle_context_json or {}),
        "recommendation_id": recommendation.recommendation_id,
        "recommendation_type": recommendation.recommendation_type,
        "identity_id": recommendation.identity_id,
        "version_id": recommendation.version_id,
        "summary": _build_recommendation_summary(recommendation),
        "status": recommendation.status,
        "approval_outcome": recommendation.approval_outcome,
        **(extra or {}),
    }


def _set_recommendation_lifecycle_context(
    recommendation: SymployeeAIRecommendation,
    *,
    action_type: str,
    state_dimension: str,
    target_state: str,
    extra: dict | None = None,
) -> None:
    recommendation.lifecycle_action_type = action_type
    recommendation.lifecycle_state_dimension = state_dimension
    recommendation.lifecycle_target_state = target_state
    recommendation.lifecycle_context_json = _build_recommendation_lifecycle_context(
        recommendation,
        extra,
    )


def _append_lifecycle_event(
    db: Session,
    *,
    tenant_id: str,
    identity_id: str,
    version_id: str | None,
    event_type: str,
    state_dimension: str,
    previous_state: str | None,
    new_state: str,
    performed_by: str | None = None,
    reason: str | None = None,
    approval_id: str | None = None,
    metadata_json: dict | None = None,
) -> str:
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
        reason=reason or "",
        approval_id=approval_id,
        metadata_json=metadata_json,
    )
    return str(event["event_id"])


def _sync_recommendation_workflow(
    db: Session,
    tenant_id: str,
    recommendation: SymployeeAIRecommendation,
) -> None:
    symployee = (
        db.query(SymployeeDefinition)
        .filter(
            SymployeeDefinition.tenant_id == tenant_id,
            SymployeeDefinition.symployee_id == recommendation.symployee_id,
        )
        .first()
    )
    if symployee:
        sync_document_workflow(
            db=db,
            tenant_id=tenant_id,
            symployee_id=symployee.symployee_id,
            identity_id=recommendation.identity_id,
            version_id=recommendation.version_id,
        )


def _apply_effective_values_to_identity(
    db: Session,
    tenant_id: str,
    recommendation: SymployeeAIRecommendation,
    effective_values: dict | None,
) -> tuple[SymployeeDocumentIdentity | None, dict]:
    values = dict(effective_values or {})
    recommendation_data = dict(recommendation.recommendation_json or {})
    if recommendation.recommendation_type == "metadata_extraction":
        values = {
            **dict(recommendation_data.get("fields") or {}),
            **values,
        }
    if recommendation.recommendation_type == "classification":
        values = {
            **recommendation_data,
            **values,
        }

    identity = (
        db.query(SymployeeDocumentIdentity)
        .filter(
            SymployeeDocumentIdentity.tenant_id == tenant_id,
            SymployeeDocumentIdentity.identity_id == recommendation.identity_id,
        )
        .first()
    )
    if not identity:
        return None, {}

    applied: dict = {}
    field_map = {
        "document_number": "canonical_document_number",
        "canonical_document_number": "canonical_document_number",
        "document_type_code": "document_type_code",
        "discipline_code": "discipline_code",
        "project_code": "project_code",
        "originator_code": "originator_code",
        "title": "title",
    }
    for source_key, target_field in field_map.items():
        value = values.get(source_key)
        if value in (None, ""):
            continue
        if getattr(identity, target_field) != value:
            setattr(identity, target_field, value)
            applied[target_field] = value
    return identity, applied


def _build_recommendation_summary(recommendation: SymployeeAIRecommendation | None) -> str | None:
    if not recommendation:
        return None

    data = dict(recommendation.recommendation_json or {})
    if recommendation.recommendation_type == "classification":
        parts = [
            data.get("document_type_code"),
            data.get("discipline_code"),
            data.get("project_code"),
            data.get("originator_code"),
        ]
        summary = ", ".join(str(part) for part in parts if part)
        return summary or data.get("title")

    if recommendation.recommendation_type == "metadata_extraction":
        fields = dict(data.get("fields") or {})
        preferred_keys = [
            "document_number",
            "document_date",
            "project_code",
            "originator_code",
            "vendor_code",
            "revision_code",
        ]
        parts = [
            f"{key}={fields[key]}"
            for key in preferred_keys
            if fields.get(key) not in (None, "")
        ]
        if parts:
            return "; ".join(parts[:4])
        return f"{len(fields)} extracted fields" if fields else None

    return recommendation.recommendation_type


def _resolve_command_blueprint(
    recommendation: SymployeeAIRecommendation,
    identity: SymployeeDocumentIdentity | None,
) -> tuple[str, dict] | None:
    recommendation_data = dict(recommendation.recommendation_json or {})

    if recommendation.recommendation_type == "classification":
        payload = {
            "operation": "apply_classification",
            "identity_id": recommendation.identity_id,
            "version_id": recommendation.version_id,
            "document_title": (
                recommendation_data.get("title")
                or (identity.title if identity else None)
            ),
            "fields": {
                "document_type_code": recommendation_data.get("document_type_code"),
                "discipline_code": recommendation_data.get("discipline_code"),
                "project_code": recommendation_data.get("project_code"),
                "originator_code": recommendation_data.get("originator_code"),
            },
        }
        return "apply_classification_metadata", payload

    if recommendation.recommendation_type == "metadata_extraction":
        fields = dict(recommendation_data.get("fields") or {})
        validation = dict(recommendation_data.get("validation") or {})
        payload = {
            "operation": "apply_metadata",
            "identity_id": recommendation.identity_id,
            "version_id": recommendation.version_id,
            "document_title": identity.title if identity else None,
            "fields": fields,
            "validation": validation,
        }
        return "apply_extracted_metadata", payload

    return None


def _create_command_for_approved_recommendation(
    db: Session,
    tenant_id: str,
    user_id: str,
    recommendation: SymployeeAIRecommendation,
) -> dict | None:
    existing_command = (
        db.query(SymployeeConnectorCommand)
        .filter(
            SymployeeConnectorCommand.tenant_id == tenant_id,
            SymployeeConnectorCommand.source_recommendation_id == recommendation.recommendation_id,
        )
        .order_by(SymployeeConnectorCommand.created_at.desc())
        .first()
    )
    if existing_command:
        recommendation.lifecycle_context_json = _build_recommendation_lifecycle_context(
            recommendation,
            {
                "drafted_command_id": existing_command.command_id,
                "drafted_command_type": existing_command.command_type,
                "drafted_command_status": existing_command.status,
                "drafted_command_existing": True,
            },
        )
        db.commit()
        return {
            "command_id": existing_command.command_id,
            "status": existing_command.status,
            "approval_status": existing_command.approval_status,
            "lifecycle_event_id": existing_command.lifecycle_event_id,
            "existing": True,
        }

    identity = (
        db.query(SymployeeDocumentIdentity)
        .filter(
            SymployeeDocumentIdentity.tenant_id == tenant_id,
            SymployeeDocumentIdentity.identity_id == recommendation.identity_id,
        )
        .first()
    )
    if not identity:
        return None

    command_blueprint = _resolve_command_blueprint(recommendation, identity)
    if not command_blueprint:
        return None

    command_type, payload = command_blueprint
    event_id = _append_lifecycle_event(
        db,
        tenant_id=tenant_id,
        identity_id=recommendation.identity_id,
        version_id=recommendation.version_id,
        event_type="COMMAND_DRAFTED_FROM_RECOMMENDATION",
        state_dimension="command_status",
        previous_state=None,
        new_state="PENDING_APPROVAL",
        performed_by=user_id,
        metadata_json=_build_recommendation_lifecycle_context(
            recommendation,
            {
                "command_type": command_type,
                "command_source": "approved_recommendation",
            },
        ),
    )
    command = SymployeeConnectorCommand(
        command_id=_new_id("SCC"),
        tenant_id=tenant_id,
        agent_id=None,
        repository_id=identity.repository_id,
        identity_id=recommendation.identity_id,
        version_id=recommendation.version_id,
        command_type=command_type,
        status="PENDING_APPROVAL",
        approval_status="PENDING_APPROVAL",
        payload_json=payload,
        policy_code=recommendation.policy_code,
        policy_version_no=recommendation.policy_version_no,
        source_recommendation_id=recommendation.recommendation_id,
        lifecycle_event_id=event_id,
        idempotency_key=f"recommendation:{recommendation.recommendation_id}:{command_type}",
    )
    recommendation.lifecycle_context_json = _build_recommendation_lifecycle_context(
        recommendation,
        {
            "drafted_command_id": command.command_id,
            "drafted_command_type": command_type,
            "drafted_command_status": command.status,
            "drafted_command_existing": False,
            "drafted_command_lifecycle_event_id": event_id,
        },
    )
    db.add(command)
    db.commit()

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="SYMPLOYEE_COMMAND_DRAFTED_FROM_RECOMMENDATION",
        event_category="SYNTHETIC_EMPLOYEE",
        description=(
            f"Connector command drafted from recommendation {recommendation.recommendation_id}"
        ),
        resource_type="symployee_connector_command",
        resource_id=command.command_id,
        metadata={
            "recommendation_id": recommendation.recommendation_id,
            "command_type": command_type,
        },
    )

    return {
        "command_id": command.command_id,
        "status": command.status,
        "approval_status": command.approval_status,
        "lifecycle_event_id": event_id,
        "existing": False,
    }


def approve_recommendation(
    db: Session,
    tenant_id: str,
    recommendation_id: str,
    approver_user_id: str,
    comments: str = "",
    effective_values: dict | None = None,
) -> dict:
    recommendation = (
        db.query(SymployeeAIRecommendation)
        .filter(
            SymployeeAIRecommendation.tenant_id == tenant_id,
            SymployeeAIRecommendation.recommendation_id == recommendation_id,
        )
        .first()
    )
    if not recommendation:
        raise ValueError("Recommendation not found")

    previous_status = recommendation.status
    recommendation.status = "APPROVED"
    recommendation.approval_outcome = "APPROVED"
    if effective_values:
        recommendation.recommendation_json = {
            **(recommendation.recommendation_json or {}),
            **effective_values,
        }
    _set_recommendation_lifecycle_context(
        recommendation,
        action_type="APPROVE_RECOMMENDATION",
        state_dimension="recommendation_status",
        target_state="APPROVED",
        extra={
            "comments": comments,
            "effective_values": effective_values or {},
        },
    )

    approval = SymployeeApprovalRecord(
        approval_id=_new_id("SAP"),
        tenant_id=tenant_id,
        approval_subject_type="ai_recommendation",
        approval_subject_id=recommendation_id,
        decision="APPROVED",
        approver_user_id=approver_user_id,
        comments=comments,
        policy_code=recommendation.policy_code,
        policy_version_no=recommendation.policy_version_no,
    )
    db.add(approval)
    db.flush()
    lifecycle_event_id = _append_lifecycle_event(
        db,
        tenant_id=tenant_id,
        identity_id=recommendation.identity_id,
        version_id=recommendation.version_id,
        event_type="RECOMMENDATION_APPROVED",
        state_dimension="recommendation_status",
        previous_state=previous_status,
        new_state="APPROVED",
        performed_by=approver_user_id,
        reason=comments or None,
        approval_id=approval.approval_id,
        metadata_json=_build_recommendation_lifecycle_context(
            recommendation,
            {
                "comments": comments,
                "effective_values": effective_values or {},
            },
        ),
    )
    identity, applied_identity_updates = _apply_effective_values_to_identity(
        db,
        tenant_id,
        recommendation,
        effective_values,
    )
    db.commit()

    command = _create_command_for_approved_recommendation(
        db=db,
        tenant_id=tenant_id,
        user_id=approver_user_id,
        recommendation=recommendation,
    )

    declaration_evaluation = None
    lifecycle_rule_evaluation = None
    if identity and applied_identity_updates:
        declaration_evaluation = evaluate_record_declaration(
            db,
            tenant_id,
            identity_id=recommendation.identity_id,
            version_id=recommendation.version_id,
            trigger_event="METADATA_UPDATE",
            dry_run=False,
            performed_by=approver_user_id,
            evaluation_reason="Approved metadata update declaration evaluation",
            metadata_json={
                "recommendation_id": recommendation.recommendation_id,
                "recommendation_type": recommendation.recommendation_type,
                "applied_identity_updates": applied_identity_updates,
            },
        )
        lifecycle_rule_evaluation = evaluate_record_lifecycle_rule(
            db,
            tenant_id,
            identity_id=recommendation.identity_id,
            version_id=recommendation.version_id,
            trigger_event="METADATA_UPDATE",
            performed_by=approver_user_id,
            evaluation_reason="Approved metadata update lifecycle evaluation",
            metadata_json={
                "recommendation_id": recommendation.recommendation_id,
                "recommendation_type": recommendation.recommendation_type,
                "applied_identity_updates": applied_identity_updates,
            },
        )

    _sync_recommendation_workflow(db, tenant_id, recommendation)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=approver_user_id,
        event_type="SYMPLOYEE_RECOMMENDATION_APPROVED",
        event_category="SYNTHETIC_EMPLOYEE",
        description=f"Recommendation approved: {recommendation_id}",
        resource_type="symployee_ai_recommendation",
        resource_id=recommendation_id,
        metadata={
            "comments": comments,
            "effective_values": effective_values or {},
            "applied_identity_updates": applied_identity_updates,
            "declaration_evaluation": declaration_evaluation,
            "lifecycle_rule_evaluation": lifecycle_rule_evaluation,
        },
    )

    return {
        "recommendation_id": recommendation_id,
        "status": recommendation.status,
        "approval_id": approval.approval_id,
        "lifecycle_event_id": lifecycle_event_id,
        "command": command,
        "applied_identity_updates": applied_identity_updates,
        "declaration_evaluation": declaration_evaluation,
        "lifecycle_rule_evaluation": lifecycle_rule_evaluation,
    }


def reject_recommendation(
    db: Session,
    tenant_id: str,
    recommendation_id: str,
    approver_user_id: str,
    comments: str = "",
    reason_code: str | None = None,
) -> dict:
    recommendation = (
        db.query(SymployeeAIRecommendation)
        .filter(
            SymployeeAIRecommendation.tenant_id == tenant_id,
            SymployeeAIRecommendation.recommendation_id == recommendation_id,
        )
        .first()
    )
    if not recommendation:
        raise ValueError("Recommendation not found")

    previous_status = recommendation.status
    recommendation.status = "REJECTED"
    recommendation.approval_outcome = "REJECTED"
    _set_recommendation_lifecycle_context(
        recommendation,
        action_type="REJECT_RECOMMENDATION",
        state_dimension="recommendation_status",
        target_state="REJECTED",
        extra={
            "comments": comments,
            "reason_code": reason_code,
        },
    )

    approval = SymployeeApprovalRecord(
        approval_id=_new_id("SAP"),
        tenant_id=tenant_id,
        approval_subject_type="ai_recommendation",
        approval_subject_id=recommendation_id,
        decision="REJECTED",
        approver_user_id=approver_user_id,
        comments=comments,
        policy_code=recommendation.policy_code,
        policy_version_no=recommendation.policy_version_no,
    )
    db.add(approval)
    db.flush()
    lifecycle_event_id = _append_lifecycle_event(
        db,
        tenant_id=tenant_id,
        identity_id=recommendation.identity_id,
        version_id=recommendation.version_id,
        event_type="RECOMMENDATION_REJECTED",
        state_dimension="recommendation_status",
        previous_state=previous_status,
        new_state="REJECTED",
        performed_by=approver_user_id,
        reason=comments or reason_code,
        approval_id=approval.approval_id,
        metadata_json=_build_recommendation_lifecycle_context(
            recommendation,
            {
                "comments": comments,
                "reason_code": reason_code,
            },
        ),
    )
    db.commit()

    _sync_recommendation_workflow(db, tenant_id, recommendation)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=approver_user_id,
        event_type="SYMPLOYEE_RECOMMENDATION_REJECTED",
        event_category="SYNTHETIC_EMPLOYEE",
        description=f"Recommendation rejected: {recommendation_id}",
        resource_type="symployee_ai_recommendation",
        resource_id=recommendation_id,
        metadata={"comments": comments, "reason_code": reason_code},
    )

    return {
        "recommendation_id": recommendation_id,
        "status": recommendation.status,
        "approval_id": approval.approval_id,
        "lifecycle_event_id": lifecycle_event_id,
    }


def override_recommendation(
    db: Session,
    tenant_id: str,
    recommendation_id: str,
    approver_user_id: str,
    reason_code: str,
    reason_text: str,
    after_state: dict,
) -> dict:
    recommendation = (
        db.query(SymployeeAIRecommendation)
        .filter(
            SymployeeAIRecommendation.tenant_id == tenant_id,
            SymployeeAIRecommendation.recommendation_id == recommendation_id,
        )
        .first()
    )
    if not recommendation:
        raise ValueError("Recommendation not found")

    previous_status = recommendation.status
    override = SymployeeOverrideRecord(
        override_id=_new_id("SOR"),
        tenant_id=tenant_id,
        override_subject_type="ai_recommendation",
        override_subject_id=recommendation_id,
        related_recommendation_id=recommendation_id,
        overridden_by_user_id=approver_user_id,
        reason_code=reason_code,
        reason_text=reason_text,
        before_state_json=recommendation.recommendation_json or {},
        after_state_json=after_state or {},
        requires_second_approval=False,
        finalized_at=_now(),
        status="EFFECTIVE",
    )
    recommendation.status = "SUPERSEDED"
    recommendation.approval_outcome = "OVERRIDDEN"
    _set_recommendation_lifecycle_context(
        recommendation,
        action_type="OVERRIDE_RECOMMENDATION",
        state_dimension="recommendation_status",
        target_state="SUPERSEDED",
        extra={
            "reason_code": reason_code,
            "reason_text": reason_text,
            "after_state": after_state or {},
        },
    )
    db.add(override)
    db.flush()
    lifecycle_event_id = _append_lifecycle_event(
        db,
        tenant_id=tenant_id,
        identity_id=recommendation.identity_id,
        version_id=recommendation.version_id,
        event_type="RECOMMENDATION_OVERRIDDEN",
        state_dimension="recommendation_status",
        previous_state=previous_status,
        new_state="SUPERSEDED",
        performed_by=approver_user_id,
        reason=reason_text or reason_code,
        metadata_json=_build_recommendation_lifecycle_context(
            recommendation,
            {
                "reason_code": reason_code,
                "reason_text": reason_text,
                "after_state": after_state or {},
                "override_id": override.override_id,
            },
        ),
    )
    db.commit()

    _sync_recommendation_workflow(db, tenant_id, recommendation)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=approver_user_id,
        event_type="SYMPLOYEE_RECOMMENDATION_OVERRIDDEN",
        event_category="SYNTHETIC_EMPLOYEE",
        description=f"Recommendation overridden: {recommendation_id}",
        resource_type="symployee_override_record",
        resource_id=override.override_id,
        metadata={"reason_code": reason_code, "reason_text": reason_text},
    )

    return {
        "recommendation_id": recommendation_id,
        "override_id": override.override_id,
        "status": override.status,
        "lifecycle_event_id": lifecycle_event_id,
    }


def create_connector_command(
    db: Session,
    tenant_id: str,
    user_id: str,
    repository_id: str,
    identity_id: str,
    version_id: str | None,
    command_type: str,
    payload: dict,
    source_recommendation_id: str | None = None,
    agent_id: str | None = None,
) -> dict:
    recommendation = None
    if source_recommendation_id:
        recommendation = (
            db.query(SymployeeAIRecommendation)
            .filter(
                SymployeeAIRecommendation.tenant_id == tenant_id,
                SymployeeAIRecommendation.recommendation_id == source_recommendation_id,
            )
            .first()
        )
        if recommendation:
            _set_recommendation_lifecycle_context(
                recommendation,
                action_type="DRAFT_COMMAND",
                state_dimension="command_status",
                target_state="PENDING_APPROVAL",
                extra={
                    "command_type": command_type,
                    "command_source": "manual_draft",
                },
            )
    lifecycle_event_id = _append_lifecycle_event(
        db,
        tenant_id=tenant_id,
        identity_id=identity_id,
        version_id=version_id,
        event_type="COMMAND_DRAFTED",
        state_dimension="command_status",
        previous_state=None,
        new_state="PENDING_APPROVAL",
        performed_by=user_id,
        metadata_json=(
            _build_recommendation_lifecycle_context(
                recommendation,
                {
                    "command_type": command_type,
                    "command_source": "manual_draft",
                },
            )
            if recommendation
            else {
                "identity_id": identity_id,
                "version_id": version_id,
                "command_type": command_type,
                "command_source": "manual_draft",
            }
        ),
    )
    command = SymployeeConnectorCommand(
        command_id=_new_id("SCC"),
        tenant_id=tenant_id,
        agent_id=agent_id,
        repository_id=repository_id,
        identity_id=identity_id,
        version_id=version_id,
        command_type=command_type,
        status="PENDING_APPROVAL",
        approval_status="PENDING_APPROVAL",
        payload_json=payload or {},
        policy_code=None,
        policy_version_no=None,
        source_recommendation_id=source_recommendation_id,
        lifecycle_event_id=lifecycle_event_id,
        idempotency_key=f"{repository_id}:{identity_id}:{command_type}:{str(uuid4())[:8]}",
    )
    if recommendation:
        recommendation.lifecycle_context_json = _build_recommendation_lifecycle_context(
            recommendation,
            {
                "drafted_command_id": command.command_id,
                "drafted_command_type": command_type,
                "drafted_command_status": command.status,
                "drafted_command_existing": False,
                "drafted_command_lifecycle_event_id": lifecycle_event_id,
            },
        )
    db.add(command)
    db.commit()

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="SYMPLOYEE_COMMAND_CREATED",
        event_category="SYNTHETIC_EMPLOYEE",
        description=f"Connector command created: {command.command_id}",
        resource_type="symployee_connector_command",
        resource_id=command.command_id,
        metadata={"command_type": command_type},
    )

    return {
        "command_id": command.command_id,
        "status": command.status,
        "approval_status": command.approval_status,
        "lifecycle_event_id": lifecycle_event_id,
    }


def approve_connector_command(
    db: Session,
    tenant_id: str,
    command_id: str,
    approver_user_id: str,
    comments: str = "",
) -> dict:
    command = (
        db.query(SymployeeConnectorCommand)
        .filter(
            SymployeeConnectorCommand.tenant_id == tenant_id,
            SymployeeConnectorCommand.command_id == command_id,
        )
        .first()
    )
    if not command:
        raise ValueError("Connector command not found")

    command.status = "APPROVED"
    command.approval_status = "APPROVED"
    command.approved_at = _now()

    approval = SymployeeApprovalRecord(
        approval_id=_new_id("SAP"),
        tenant_id=tenant_id,
        approval_subject_type="connector_command",
        approval_subject_id=command.command_id,
        decision="APPROVED",
        approver_user_id=approver_user_id,
        comments=comments,
        policy_code=command.policy_code,
        policy_version_no=command.policy_version_no,
    )
    db.add(approval)
    db.commit()

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=approver_user_id,
        event_type="SYMPLOYEE_COMMAND_APPROVED",
        event_category="SYNTHETIC_EMPLOYEE",
        description=f"Connector command approved: {command.command_id}",
        resource_type="symployee_connector_command",
        resource_id=command.command_id,
        metadata={"comments": comments},
    )

    return {
        "command_id": command.command_id,
        "status": command.status,
        "approval_status": command.approval_status,
        "approval_id": approval.approval_id,
    }


def reject_connector_command(
    db: Session,
    tenant_id: str,
    command_id: str,
    approver_user_id: str,
    comments: str = "",
) -> dict:
    command = (
        db.query(SymployeeConnectorCommand)
        .filter(
            SymployeeConnectorCommand.tenant_id == tenant_id,
            SymployeeConnectorCommand.command_id == command_id,
        )
        .first()
    )
    if not command:
        raise ValueError("Connector command not found")

    command.status = "REJECTED"
    command.approval_status = "REJECTED"

    approval = SymployeeApprovalRecord(
        approval_id=_new_id("SAP"),
        tenant_id=tenant_id,
        approval_subject_type="connector_command",
        approval_subject_id=command.command_id,
        decision="REJECTED",
        approver_user_id=approver_user_id,
        comments=comments,
        policy_code=command.policy_code,
        policy_version_no=command.policy_version_no,
    )
    db.add(approval)
    db.commit()

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=approver_user_id,
        event_type="SYMPLOYEE_COMMAND_REJECTED",
        event_category="SYNTHETIC_EMPLOYEE",
        description=f"Connector command rejected: {command.command_id}",
        resource_type="symployee_connector_command",
        resource_id=command.command_id,
        metadata={"comments": comments},
    )

    return {
        "command_id": command.command_id,
        "status": command.status,
        "approval_status": command.approval_status,
        "approval_id": approval.approval_id,
    }


def dispatch_connector_command(
    db: Session,
    tenant_id: str,
    command_id: str,
    user_id: str,
    comments: str = "",
) -> dict:
    command = (
        db.query(SymployeeConnectorCommand)
        .filter(
            SymployeeConnectorCommand.tenant_id == tenant_id,
            SymployeeConnectorCommand.command_id == command_id,
        )
        .first()
    )
    if not command:
        raise ValueError("Connector command not found")
    if command.approval_status != "APPROVED":
        raise ValueError("Connector command must be approved before dispatch")

    command.status = "DISPATCHED"
    command.dispatched_at = _now()
    db.commit()

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="SYMPLOYEE_COMMAND_DISPATCHED",
        event_category="SYNTHETIC_EMPLOYEE",
        description=f"Connector command dispatched: {command.command_id}",
        resource_type="symployee_connector_command",
        resource_id=command.command_id,
        metadata={"comments": comments},
    )

    return {
        "command_id": command.command_id,
        "status": command.status,
        "approval_status": command.approval_status,
    }


def acknowledge_connector_command(
    db: Session,
    tenant_id: str,
    command_id: str,
    user_id: str,
    comments: str = "",
) -> dict:
    command = (
        db.query(SymployeeConnectorCommand)
        .filter(
            SymployeeConnectorCommand.tenant_id == tenant_id,
            SymployeeConnectorCommand.command_id == command_id,
        )
        .first()
    )
    if not command:
        raise ValueError("Connector command not found")

    command.status = "ACKNOWLEDGED"
    command.acknowledged_at = _now()
    db.commit()

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="SYMPLOYEE_COMMAND_ACKNOWLEDGED",
        event_category="SYNTHETIC_EMPLOYEE",
        description=f"Connector command acknowledged: {command.command_id}",
        resource_type="symployee_connector_command",
        resource_id=command.command_id,
        metadata={"comments": comments},
    )

    return {
        "command_id": command.command_id,
        "status": command.status,
        "approval_status": command.approval_status,
    }


def fail_connector_command(
    db: Session,
    tenant_id: str,
    command_id: str,
    user_id: str,
    comments: str = "",
    failure_reason: str = "",
) -> dict:
    command = (
        db.query(SymployeeConnectorCommand)
        .filter(
            SymployeeConnectorCommand.tenant_id == tenant_id,
            SymployeeConnectorCommand.command_id == command_id,
        )
        .first()
    )
    if not command:
        raise ValueError("Connector command not found")

    command.status = "FAILED"
    command.failed_at = _now()
    command.failure_reason = failure_reason or comments or "Command execution failed"
    db.commit()

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="SYMPLOYEE_COMMAND_FAILED",
        event_category="SYNTHETIC_EMPLOYEE",
        description=f"Connector command failed: {command.command_id}",
        resource_type="symployee_connector_command",
        resource_id=command.command_id,
        metadata={"comments": comments, "failure_reason": command.failure_reason},
    )

    return {
        "command_id": command.command_id,
        "status": command.status,
        "approval_status": command.approval_status,
        "failure_reason": command.failure_reason,
    }


def request_connector_command_rollback(
    db: Session,
    tenant_id: str,
    command_id: str,
    user_id: str,
    comments: str = "",
) -> dict:
    command = (
        db.query(SymployeeConnectorCommand)
        .filter(
            SymployeeConnectorCommand.tenant_id == tenant_id,
            SymployeeConnectorCommand.command_id == command_id,
        )
        .first()
    )
    if not command:
        raise ValueError("Connector command not found")
    if command.status not in {"ACKNOWLEDGED", "FAILED"}:
        raise ValueError("Rollback can only be requested for acknowledged or failed commands")

    command.status = "ROLLBACK_PENDING"
    payload_json = dict(command.payload_json or {})
    payload_json["rollback_requested_at"] = _now().isoformat()
    payload_json["rollback_requested_by"] = user_id
    command.payload_json = payload_json
    db.commit()

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="SYMPLOYEE_COMMAND_ROLLBACK_REQUESTED",
        event_category="SYNTHETIC_EMPLOYEE",
        description=f"Rollback requested for connector command {command.command_id}",
        resource_type="symployee_connector_command",
        resource_id=command.command_id,
        metadata={"comments": comments},
    )

    return {
        "command_id": command.command_id,
        "status": command.status,
        "approval_status": command.approval_status,
    }
