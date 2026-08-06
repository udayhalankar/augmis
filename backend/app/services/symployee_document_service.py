from __future__ import annotations

import os
from pathlib import Path
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db_models import (
    Document,
    Repository,
    SymployeeAIRecommendation,
    SymployeeApprovalRecord,
    SymployeeConnectorCommand,
    SymployeeConnectorEvent,
    SymployeeDefinition,
    SymployeeDocumentIdentity,
    SymployeeDocumentSourceObject,
    SymployeeDocumentVersion,
    SymployeeIdempotencyRecord,
    SymployeeWorkflowInstance,
    SymployeeWorkflowTask,
    User,
)
from app.services.audit_service import create_audit_log
from app.services.symployee_intelligence_service import generate_document_recommendations
from app.services.symployee_lifecycle_service import create_lifecycle_event
from app.services.symployee_workflow_service import (
    refresh_workflow_sla_states,
    sync_document_workflow,
)
from app.services.symployee_records_service import evaluate_record_declaration


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{str(uuid4())[:12].upper()}"


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
    metadata_json: dict | None = None,
) -> None:
    create_lifecycle_event(
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
        metadata_json=metadata_json,
    )


def _set_initial_identity_state(
    db: Session,
    *,
    tenant_id: str,
    identity: SymployeeDocumentIdentity,
    version_id: str | None,
    performed_by: str | None,
) -> None:
    state_defaults = {
        "document_lifecycle_stage": "REGISTERED",
        "review_status": "AWAITING_REVIEW",
        "record_status": "NON_RECORD",
        "security_status": "UNCLASSIFIED",
    }
    event_types = {
        "document_lifecycle_stage": "DOCUMENT_REGISTERED",
        "review_status": "REVIEW_STATUS_INITIALIZED",
        "record_status": "RECORD_STATUS_INITIALIZED",
        "security_status": "SECURITY_STATUS_INITIALIZED",
    }

    for field_name, default_value in state_defaults.items():
        previous_state = getattr(identity, field_name, None)
        if previous_state:
            continue

        setattr(identity, field_name, default_value)
        _append_lifecycle_event(
            db,
            tenant_id=tenant_id,
            identity_id=identity.identity_id,
            version_id=version_id,
            event_type=event_types[field_name],
            state_dimension=field_name,
            previous_state=previous_state,
            new_state=default_value,
            performed_by=performed_by,
        )


def _extract_metadata_candidate(source_file: dict, repository: Repository) -> dict:
    metadata = dict(source_file.get("metadata") or {})
    metadata.setdefault("repository_id", repository.repository_id)
    metadata.setdefault("repository_name", repository.repository_name)
    metadata.setdefault("source_type", repository.source_type)
    metadata.setdefault("source_path", source_file.get("file_path"))
    metadata.setdefault("external_file_id", source_file.get("external_file_id"))
    metadata.setdefault("file_name", source_file.get("file_name"))
    return metadata


def ensure_document_controller_symployee(
    db: Session,
    tenant_id: str,
) -> SymployeeDefinition:
    symployee = (
        db.query(SymployeeDefinition)
        .filter(
            SymployeeDefinition.tenant_id == tenant_id,
            SymployeeDefinition.code == "document_controller",
        )
        .first()
    )
    if symployee:
        return symployee

    symployee = SymployeeDefinition(
        symployee_id=_new_id("SYM"),
        tenant_id=tenant_id,
        code="document_controller",
        name="Symployee Document Controller",
        employee_type="document_controller",
        status="ACTIVE",
        instruction_profile_code="symployee.document_controller.default",
        permission_profile_json={
            "can_classify": True,
            "can_extract_metadata": True,
            "can_prepare_commands": True,
            "can_approve": False,
        },
        default_policy_set_code=None,
    )
    db.add(symployee)
    db.commit()
    db.refresh(symployee)
    return symployee


def _find_existing_identity_for_connector_file(
    db: Session,
    tenant_id: str,
    repository_id: str,
    connector_file,
    source_file: dict,
) -> SymployeeDocumentIdentity | None:
    previous_document_id = (connector_file.metadata_json or {}).get("previous_document_id")
    if previous_document_id:
        existing_version = (
            db.query(SymployeeDocumentVersion)
            .filter(
                SymployeeDocumentVersion.tenant_id == tenant_id,
                SymployeeDocumentVersion.document_id == previous_document_id,
            )
            .first()
        )
        if existing_version:
            return (
                db.query(SymployeeDocumentIdentity)
                .filter(
                    SymployeeDocumentIdentity.identity_id == existing_version.identity_id,
                    SymployeeDocumentIdentity.tenant_id == tenant_id,
                )
                .first()
            )

    external_object_id = source_file.get("external_file_id")
    if external_object_id:
        source_object = (
            db.query(SymployeeDocumentSourceObject)
            .filter(
                SymployeeDocumentSourceObject.tenant_id == tenant_id,
                SymployeeDocumentSourceObject.repository_id == repository_id,
                SymployeeDocumentSourceObject.source_system_type == "connector",
                SymployeeDocumentSourceObject.external_object_id == external_object_id,
            )
            .first()
        )
        if source_object:
            return (
                db.query(SymployeeDocumentIdentity)
                .filter(
                    SymployeeDocumentIdentity.identity_id == source_object.identity_id,
                    SymployeeDocumentIdentity.tenant_id == tenant_id,
                )
                .first()
            )

    return None


def register_symployee_connector_ingestion(
    db: Session,
    tenant_id: str,
    repository: Repository,
    connector_file,
    source_file: dict,
    document: Document,
    parse_result: dict,
    parsed_text: str,
    uploaded_by: str | None = None,
) -> dict:
    symployee = ensure_document_controller_symployee(db, tenant_id)
    identity = _find_existing_identity_for_connector_file(
        db=db,
        tenant_id=tenant_id,
        repository_id=repository.repository_id,
        connector_file=connector_file,
        source_file=source_file,
    )

    file_name = source_file.get("file_name") or document.file_name
    title = os.path.splitext(file_name)[0]
    metadata_candidate = _extract_metadata_candidate(source_file, repository)
    intelligence_result = generate_document_recommendations(
        db=db,
        tenant_id=tenant_id,
        file_name=file_name,
        parsed_text=parsed_text,
        metadata_candidate=metadata_candidate,
        repository_id=repository.repository_id,
        business_area=repository.business_area,
        project_code=metadata_candidate.get("project_code"),
    )
    classification_result = intelligence_result["classification"]
    metadata_result = intelligence_result["metadata"]
    document_type_code = classification_result.get("document_type_code")
    confidence = classification_result.get("confidence_score")

    if identity is None:
        identity = SymployeeDocumentIdentity(
            identity_id=_new_id("SID"),
            tenant_id=tenant_id,
            repository_id=repository.repository_id,
            canonical_document_number=(metadata_result.get("fields") or {}).get("document_number") or metadata_candidate.get("document_number"),
            title=classification_result.get("title") or title,
            document_type_code=document_type_code,
            discipline_code=classification_result.get("discipline_code") or metadata_candidate.get("discipline"),
            project_code=classification_result.get("project_code") or metadata_candidate.get("project_code"),
            originator_code=classification_result.get("originator_code") or metadata_candidate.get("originator"),
            status="REGISTERED",
            document_lifecycle_stage="REGISTERED",
            review_status="AWAITING_REVIEW",
            record_status="NON_RECORD",
            security_status="UNCLASSIFIED",
            current_document_id=document.document_id,
        )
        db.add(identity)
        db.flush()

    source_object = (
        db.query(SymployeeDocumentSourceObject)
        .filter(
            SymployeeDocumentSourceObject.tenant_id == tenant_id,
            SymployeeDocumentSourceObject.repository_id == repository.repository_id,
            SymployeeDocumentSourceObject.source_system_type == "connector",
            SymployeeDocumentSourceObject.external_object_id == (source_file.get("external_file_id") or connector_file.external_file_id),
        )
        .first()
    )
    if not source_object:
        source_object = SymployeeDocumentSourceObject(
            source_object_id=_new_id("SSO"),
            tenant_id=tenant_id,
            identity_id=identity.identity_id,
            repository_id=repository.repository_id,
            source_system_type="connector",
            external_object_id=source_file.get("external_file_id") or connector_file.external_file_id,
            source_path=source_file.get("file_path"),
            source_version_ref=str(connector_file.version_number),
            is_active=True,
            last_seen_at=_now(),
        )
        db.add(source_object)
    else:
        source_object.identity_id = identity.identity_id
        source_object.source_path = source_file.get("file_path")
        source_object.source_version_ref = str(connector_file.version_number)
        source_object.last_seen_at = _now()

    existing_version = (
        db.query(SymployeeDocumentVersion)
        .filter(
            SymployeeDocumentVersion.tenant_id == tenant_id,
            SymployeeDocumentVersion.document_id == document.document_id,
        )
        .first()
    )
    version = existing_version
    previous_current_version = None
    if identity.current_version_id:
        previous_current_version = (
            db.query(SymployeeDocumentVersion)
            .filter(
                SymployeeDocumentVersion.tenant_id == tenant_id,
                SymployeeDocumentVersion.version_id == identity.current_version_id,
            )
            .first()
        )
    if version is None:
        version = SymployeeDocumentVersion(
            version_id=_new_id("SVR"),
            tenant_id=tenant_id,
            identity_id=identity.identity_id,
            connector_file_id=str(connector_file.id) if connector_file.id else None,
            document_id=document.document_id,
            revision_code=str(connector_file.version_number),
            version_label=f"REV-{connector_file.version_number}",
            file_name=file_name,
            file_extension=os.path.splitext(file_name)[1].lower() or None,
            mime_type=(source_file.get("metadata") or {}).get("mime_type"),
            file_hash=connector_file.file_hash,
            page_count=parse_result.get("page_count"),
            status="ACTIVE",
            revision_status="CURRENT",
            is_current_revision=True,
            supersedes_version_id=(
                previous_current_version.version_id
                if previous_current_version and previous_current_version.document_id != document.document_id
                else None
            ),
            metadata_json={
                "ocr_used": parse_result.get("ocr_used", False),
                "parser": parse_result.get("parser"),
                "source_modified_at": (
                    connector_file.source_modified_at.isoformat()
                    if connector_file.source_modified_at
                    else None
                ),
            },
        )
        db.add(version)
        db.flush()
        create_lifecycle_event(
            db,
            tenant_id,
            identity_id=identity.identity_id,
            version_id=version.version_id,
            event_type="REVISION_STATUS_INITIALIZED",
            state_dimension="revision_status",
            previous_state=None,
            new_state="CURRENT",
            performed_by=uploaded_by,
            metadata_json={
                "document_id": document.document_id,
                "revision_code": version.revision_code,
            },
        )
    else:
        if not version.revision_status:
            version.revision_status = "CURRENT"
            _append_lifecycle_event(
                db,
                tenant_id=tenant_id,
                identity_id=identity.identity_id,
                version_id=version.version_id,
                event_type="REVISION_STATUS_INITIALIZED",
                state_dimension="revision_status",
                previous_state=None,
                new_state="CURRENT",
                performed_by=uploaded_by,
                metadata_json={
                    "document_id": document.document_id,
                    "revision_code": version.revision_code,
                },
            )
        version.is_current_revision = True

    if (
        previous_current_version
        and previous_current_version.version_id != version.version_id
        and previous_current_version.is_current_revision
    ):
        prior_revision_status = previous_current_version.revision_status or "CURRENT"
        previous_current_version.is_current_revision = False
        previous_current_version.revision_status = "SUPERSEDED"
        _append_lifecycle_event(
            db,
            tenant_id=tenant_id,
            identity_id=identity.identity_id,
            version_id=previous_current_version.version_id,
            event_type="REVISION_SUPERSEDED",
            state_dimension="revision_status",
            previous_state=prior_revision_status,
            new_state="SUPERSEDED",
            performed_by=uploaded_by,
            metadata_json={
                "superseded_by_version_id": version.version_id,
            },
        )

    identity.current_version_id = version.version_id
    identity.current_document_id = document.document_id
    identity.title = classification_result.get("title") or identity.title
    identity.document_type_code = document_type_code or identity.document_type_code
    identity.discipline_code = classification_result.get("discipline_code") or identity.discipline_code
    identity.project_code = classification_result.get("project_code") or identity.project_code
    identity.originator_code = classification_result.get("originator_code") or identity.originator_code
    identity.canonical_document_number = (
        (metadata_result.get("fields") or {}).get("document_number")
        or identity.canonical_document_number
    )
    _set_initial_identity_state(
        db,
        tenant_id=tenant_id,
        identity=identity,
        version_id=version.version_id,
        performed_by=uploaded_by,
    )

    idempotency_key = (
        f"connector:{repository.repository_id}:{source_file.get('external_file_id') or connector_file.external_file_id}:"
        f"{connector_file.version_number}:{connector_file.file_hash or 'nofilehash'}"
    )
    idempotency_record = (
        db.query(SymployeeIdempotencyRecord)
        .filter(
            SymployeeIdempotencyRecord.tenant_id == tenant_id,
            SymployeeIdempotencyRecord.scope_type == "connector_event",
            SymployeeIdempotencyRecord.idempotency_key == idempotency_key,
        )
        .first()
    )
    if not idempotency_record:
        idempotency_record = SymployeeIdempotencyRecord(
            idempotency_record_id=_new_id("SIDEMP"),
            tenant_id=tenant_id,
            scope_type="connector_event",
            scope_key=repository.repository_id,
            idempotency_key=idempotency_key,
            resolution_status="accepted",
            last_seen_at=_now(),
        )
        db.add(idempotency_record)
    else:
        idempotency_record.last_seen_at = _now()

    connector_event = (
        db.query(SymployeeConnectorEvent)
        .filter(
            SymployeeConnectorEvent.tenant_id == tenant_id,
            SymployeeConnectorEvent.idempotency_key == idempotency_key,
        )
        .first()
    )
    if not connector_event:
        connector_event = SymployeeConnectorEvent(
            connector_event_id=_new_id("SCE"),
            tenant_id=tenant_id,
            repository_id=repository.repository_id,
            event_key=idempotency_key,
            idempotency_key=idempotency_key,
            event_type="created" if connector_file.version_number == 1 else "modified",
            external_object_id=source_file.get("external_file_id") or connector_file.external_file_id,
            source_path=source_file.get("file_path"),
            file_hash=connector_file.file_hash,
            payload_json={
                "file_name": file_name,
                "metadata": metadata_candidate,
            },
            processing_status="processed",
            processed_at=_now(),
            identity_id=identity.identity_id,
            version_id=version.version_id,
        )
        db.add(connector_event)
    else:
        connector_event.processing_status = "processed"
        connector_event.processed_at = _now()
        connector_event.identity_id = identity.identity_id
        connector_event.version_id = version.version_id

    existing_classification = (
        db.query(SymployeeAIRecommendation)
        .filter(
            SymployeeAIRecommendation.tenant_id == tenant_id,
            SymployeeAIRecommendation.identity_id == identity.identity_id,
            SymployeeAIRecommendation.version_id == version.version_id,
            SymployeeAIRecommendation.recommendation_type == "classification",
        )
        .first()
    )
    if not existing_classification:
        db.add(
            SymployeeAIRecommendation(
                recommendation_id=_new_id("SAR"),
                tenant_id=tenant_id,
                symployee_id=symployee.symployee_id,
                identity_id=identity.identity_id,
                version_id=version.version_id,
                recommendation_type="classification",
                status="NEEDS_REVIEW",
                recommendation_json={
                    "document_type_code": document_type_code,
                    "title": classification_result.get("title") or title,
                    "discipline_code": classification_result.get("discipline_code"),
                    "project_code": classification_result.get("project_code"),
                    "originator_code": classification_result.get("originator_code"),
                },
                confidence_score=confidence,
                model_name=classification_result.get("model_name"),
                model_provider=classification_result.get("model_provider"),
                prompt_profile_code=classification_result.get("prompt_profile_code"),
                prompt_version=classification_result.get("prompt_version"),
                policy_code=classification_result.get("policy_code"),
                policy_version_no=classification_result.get("policy_version_no"),
                source_evidence_json={
                    "file_name": file_name,
                    "external_file_id": source_file.get("external_file_id"),
                },
            )
        )
    else:
        existing_classification.status = "NEEDS_REVIEW"
        existing_classification.recommendation_json = {
            "document_type_code": document_type_code,
            "title": classification_result.get("title") or title,
            "discipline_code": classification_result.get("discipline_code"),
            "project_code": classification_result.get("project_code"),
            "originator_code": classification_result.get("originator_code"),
        }
        existing_classification.confidence_score = confidence
        existing_classification.model_name = classification_result.get("model_name")
        existing_classification.model_provider = classification_result.get("model_provider")
        existing_classification.prompt_profile_code = classification_result.get("prompt_profile_code")
        existing_classification.prompt_version = classification_result.get("prompt_version")
        existing_classification.policy_code = classification_result.get("policy_code")
        existing_classification.policy_version_no = classification_result.get("policy_version_no")
        existing_classification.source_evidence_json = {
            "file_name": file_name,
            "external_file_id": source_file.get("external_file_id"),
        }

    existing_metadata = (
        db.query(SymployeeAIRecommendation)
        .filter(
            SymployeeAIRecommendation.tenant_id == tenant_id,
            SymployeeAIRecommendation.identity_id == identity.identity_id,
            SymployeeAIRecommendation.version_id == version.version_id,
            SymployeeAIRecommendation.recommendation_type == "metadata_extraction",
        )
        .first()
    )
    if not existing_metadata:
        db.add(
            SymployeeAIRecommendation(
                recommendation_id=_new_id("SAR"),
                tenant_id=tenant_id,
                symployee_id=symployee.symployee_id,
                identity_id=identity.identity_id,
                version_id=version.version_id,
                recommendation_type="metadata_extraction",
                status="NEEDS_REVIEW",
                recommendation_json=metadata_result,
                confidence_score=metadata_result.get("confidence_score"),
                model_name=metadata_result.get("model_name"),
                model_provider=metadata_result.get("model_provider"),
                prompt_profile_code=metadata_result.get("prompt_profile_code"),
                prompt_version=metadata_result.get("prompt_version"),
                policy_code=metadata_result.get("policy_code"),
                policy_version_no=metadata_result.get("policy_version_no"),
                source_evidence_json={
                    "connector_metadata_keys": sorted(metadata_candidate.keys()),
                },
            )
        )
    else:
        existing_metadata.status = "NEEDS_REVIEW"
        existing_metadata.recommendation_json = metadata_result
        existing_metadata.confidence_score = metadata_result.get("confidence_score")
        existing_metadata.model_name = metadata_result.get("model_name")
        existing_metadata.model_provider = metadata_result.get("model_provider")
        existing_metadata.prompt_profile_code = metadata_result.get("prompt_profile_code")
        existing_metadata.prompt_version = metadata_result.get("prompt_version")
        existing_metadata.policy_code = metadata_result.get("policy_code")
        existing_metadata.policy_version_no = metadata_result.get("policy_version_no")
        existing_metadata.source_evidence_json = {
            "connector_metadata_keys": sorted(metadata_candidate.keys()),
        }

    db.commit()

    sync_document_workflow(
        db=db,
        tenant_id=tenant_id,
        symployee_id=symployee.symployee_id,
        identity_id=identity.identity_id,
        version_id=version.version_id,
    )

    declaration_evaluation = evaluate_record_declaration(
        db,
        tenant_id,
        identity_id=identity.identity_id,
        version_id=version.version_id,
        trigger_event="INGESTION",
        dry_run=False,
        performed_by=uploaded_by,
        evaluation_reason="Connector ingestion declaration evaluation",
        metadata_json={
            "trigger_source": "connector_ingestion",
            "connector_event_id": connector_event.connector_event_id,
            "repository_id": repository.repository_id,
            "document_id": document.document_id,
            "version_id": version.version_id,
        },
    )

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=uploaded_by,
        event_type="SYMPLOYEE_DOCUMENT_REGISTERED",
        event_category="SYNTHETIC_EMPLOYEE",
        description=f"Symployee registered document identity {identity.identity_id}",
        resource_type="symployee_document_identity",
        resource_id=identity.identity_id,
        metadata={
            "identity_id": identity.identity_id,
            "version_id": version.version_id,
            "document_id": document.document_id,
            "repository_id": repository.repository_id,
            "record_classification": declaration_evaluation.get("classification"),
            "record_status": declaration_evaluation.get("target_record_status"),
            "record_declaration_id": declaration_evaluation.get("record_declaration_id"),
        },
    )

    return {
        "identity_id": identity.identity_id,
        "version_id": version.version_id,
        "document_id": document.document_id,
        "declaration_evaluation": declaration_evaluation,
    }


def _serialize_identity(identity: SymployeeDocumentIdentity) -> dict:
    return {
        "identity_id": identity.identity_id,
        "repository_id": identity.repository_id,
        "canonical_document_number": identity.canonical_document_number,
        "title": identity.title,
        "document_type_code": identity.document_type_code,
        "discipline_code": identity.discipline_code,
        "project_code": identity.project_code,
        "originator_code": identity.originator_code,
        "status": identity.status,
        "current_version_id": identity.current_version_id,
        "current_document_id": identity.current_document_id,
        "created_at": identity.created_at.isoformat() if identity.created_at else None,
        "modified_at": identity.modified_at.isoformat() if identity.modified_at else None,
    }


def _serialize_version(version: SymployeeDocumentVersion) -> dict:
    return {
        "version_id": version.version_id,
        "document_id": version.document_id,
        "connector_file_id": version.connector_file_id,
        "revision_code": version.revision_code,
        "version_label": version.version_label,
        "file_name": version.file_name,
        "file_extension": version.file_extension,
        "mime_type": version.mime_type,
        "file_hash": version.file_hash,
        "page_count": version.page_count,
        "status": version.status,
        "metadata": version.metadata_json or {},
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


def _serialize_workflow_task(task: SymployeeWorkflowTask) -> dict:
    now = _now()
    days_overdue = 0
    if task.due_at and task.status not in {"COMPLETED", "REJECTED"} and now > task.due_at:
        days_overdue = max(0, (now.date() - task.due_at.date()).days)
    return {
        "workflow_task_id": task.workflow_task_id,
        "workflow_instance_id": task.workflow_instance_id,
        "task_code": task.task_code,
        "task_name": task.task_name,
        "task_type": task.task_type,
        "status": task.status,
        "sequence_no": task.sequence_no,
        "assigned_role_code": task.assigned_role_code,
        "assigned_user_id": task.assigned_user_id,
        "assigned_user_name": (task.task_payload_json or {}).get("assigned_user_name"),
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "sla_status": task.sla_status,
        "escalation_status": task.escalation_status,
        "days_overdue": days_overdue,
        "task_payload": task.task_payload_json or {},
        "workflow_events": (task.task_payload_json or {}).get("workflow_events") or [],
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


def _serialize_workflow_instance(
    instance: SymployeeWorkflowInstance,
    tasks: list[SymployeeWorkflowTask],
) -> dict:
    return {
        "workflow_instance_id": instance.workflow_instance_id,
        "workflow_code": instance.workflow_code,
        "workflow_status": instance.workflow_status,
        "routing_status": instance.routing_status,
        "current_step_code": instance.current_step_code,
        "policy_code": instance.policy_code,
        "policy_version_no": instance.policy_version_no,
        "workflow_payload": instance.workflow_payload_json or {},
        "started_at": instance.started_at.isoformat() if instance.started_at else None,
        "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
        "tasks": [_serialize_workflow_task(task) for task in tasks],
    }


def resolve_document_file(
    db: Session,
    tenant_id: str,
    identity_id: str,
    version_id: str | None = None,
) -> dict:
    identity = (
        db.query(SymployeeDocumentIdentity)
        .filter(
            SymployeeDocumentIdentity.tenant_id == tenant_id,
            SymployeeDocumentIdentity.identity_id == identity_id,
        )
        .first()
    )
    if not identity:
        raise ValueError("Symployee document identity not found")

    version_query = db.query(SymployeeDocumentVersion).filter(
        SymployeeDocumentVersion.tenant_id == tenant_id,
        SymployeeDocumentVersion.identity_id == identity_id,
    )
    if version_id:
        version = version_query.filter(
            SymployeeDocumentVersion.version_id == version_id
        ).first()
    else:
        version = version_query.order_by(SymployeeDocumentVersion.created_at.desc()).first()
    if not version:
        raise ValueError("Symployee document version not found")

    document = (
        db.query(Document)
        .filter(
            Document.tenant_id == tenant_id,
            Document.document_id == version.document_id,
        )
        .first()
    )

    source_object = (
        db.query(SymployeeDocumentSourceObject)
        .filter(
            SymployeeDocumentSourceObject.tenant_id == tenant_id,
            SymployeeDocumentSourceObject.identity_id == identity_id,
            SymployeeDocumentSourceObject.is_active.is_(True),
        )
        .order_by(SymployeeDocumentSourceObject.last_seen_at.desc())
        .first()
    )

    candidate_paths = [
        (document.stored_path if document else None),
        (source_object.source_path if source_object else None),
    ]
    for candidate in candidate_paths:
        normalized = (candidate or "").strip()
        if normalized and Path(normalized).exists():
            return {
                "path": normalized,
                "file_name": version.file_name,
                "mime_type": version.mime_type,
                "version_id": version.version_id,
            }

    raise ValueError("Actual document file is not available on the backend host")


def _serialize_recommendation(row: SymployeeAIRecommendation) -> dict:
    return {
        "recommendation_id": row.recommendation_id,
        "identity_id": row.identity_id,
        "version_id": row.version_id,
        "recommendation_type": row.recommendation_type,
        "status": row.status,
        "recommendation": row.recommendation_json or {},
        "confidence_score": row.confidence_score,
        "model_name": row.model_name,
        "model_provider": row.model_provider,
        "prompt_profile_code": row.prompt_profile_code,
        "prompt_version": row.prompt_version,
        "policy_code": row.policy_code,
        "policy_version_no": row.policy_version_no,
        "approval_outcome": row.approval_outcome,
        "source_evidence": row.source_evidence_json or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _build_recommendation_summary(row: SymployeeAIRecommendation | None) -> str | None:
    if not row:
        return None

    data = dict(row.recommendation_json or {})
    if row.recommendation_type == "classification":
        parts = [
            data.get("document_type_code"),
            data.get("discipline_code"),
            data.get("project_code"),
            data.get("originator_code"),
        ]
        summary = ", ".join(str(part) for part in parts if part)
        return summary or data.get("title")

    if row.recommendation_type == "metadata_extraction":
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

    return row.recommendation_type


def _serialize_command(
    row: SymployeeConnectorCommand,
    document_title: str | None = None,
    source_recommendation: SymployeeAIRecommendation | None = None,
) -> dict:
    return {
        "command_id": row.command_id,
        "repository_id": row.repository_id,
        "identity_id": row.identity_id,
        "version_id": row.version_id,
        "command_type": row.command_type,
        "status": row.status,
        "approval_status": row.approval_status,
        "payload": row.payload_json or {},
        "execution_history": (row.payload_json or {}).get("execution_history") or [],
        "latest_execution": (row.payload_json or {}).get("latest_execution") or {},
        "policy_code": row.policy_code,
        "policy_version_no": row.policy_version_no,
        "source_recommendation_id": row.source_recommendation_id,
        "source_recommendation_type": (
            source_recommendation.recommendation_type if source_recommendation else None
        ),
        "source_recommendation_status": (
            source_recommendation.status if source_recommendation else None
        ),
        "source_recommendation_summary": _build_recommendation_summary(source_recommendation),
        "document_title": document_title,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
        "dispatched_at": row.dispatched_at.isoformat() if row.dispatched_at else None,
        "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
        "failed_at": row.failed_at.isoformat() if row.failed_at else None,
        "failure_reason": row.failure_reason,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_symployees(db: Session, tenant_id: str) -> dict:
    symployees = (
        db.query(SymployeeDefinition)
        .filter(SymployeeDefinition.tenant_id == tenant_id)
        .order_by(SymployeeDefinition.name.asc())
        .all()
    )
    return {
        "items": [
            {
                "symployee_id": row.symployee_id,
                "code": row.code,
                "name": row.name,
                "employee_type": row.employee_type,
                "status": row.status,
                "instruction_profile_code": row.instruction_profile_code,
            }
            for row in symployees
        ]
    }


def _calculate_metadata_missing_fields(identity: SymployeeDocumentIdentity) -> list[str]:
    checks = [
        ("document_number", identity.canonical_document_number),
        ("document_type_code", identity.document_type_code),
        ("discipline_code", identity.discipline_code),
        ("project_code", identity.project_code),
        ("originator_code", identity.originator_code),
    ]
    return [field for field, value in checks if value in (None, "")]


def _build_count_breakdown(values: list[str | None], *, unknown_label: str = "Unspecified") -> list[dict]:
    counts: dict[str, int] = {}
    for raw_value in values:
        value = (raw_value or "").strip() or unknown_label
        counts[value] = counts.get(value, 0) + 1
    return [
        {"label": label, "count": count}
        for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _round_metric(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 1)


def get_document_controller_overview(db: Session, tenant_id: str) -> dict:
    refresh_workflow_sla_states(db, tenant_id)

    identity_rows = (
        db.query(SymployeeDocumentIdentity)
        .filter(SymployeeDocumentIdentity.tenant_id == tenant_id)
        .all()
    )
    recommendation_rows = (
        db.query(SymployeeAIRecommendation)
        .filter(SymployeeAIRecommendation.tenant_id == tenant_id)
        .all()
    )
    command_rows = (
        db.query(SymployeeConnectorCommand)
        .filter(SymployeeConnectorCommand.tenant_id == tenant_id)
        .all()
    )
    workflow_rows = (
        db.query(SymployeeWorkflowInstance)
        .filter(SymployeeWorkflowInstance.tenant_id == tenant_id)
        .all()
    )
    workload_rows = (
        db.query(SymployeeWorkflowTask)
        .filter(
            SymployeeWorkflowTask.tenant_id == tenant_id,
        )
        .all()
    )
    source_object_rows = (
        db.query(SymployeeDocumentSourceObject)
        .filter(
            SymployeeDocumentSourceObject.tenant_id == tenant_id,
            SymployeeDocumentSourceObject.is_active.is_(True),
        )
        .all()
    )
    approval_rows = (
        db.query(SymployeeApprovalRecord)
        .filter(SymployeeApprovalRecord.tenant_id == tenant_id)
        .all()
    )
    repository_rows = (
        db.query(Repository)
        .filter(Repository.tenant_id == tenant_id)
        .all()
    )

    total_documents = len(identity_rows)
    pending_recommendations = len(
        [row for row in recommendation_rows if row.status == "NEEDS_REVIEW"]
    )
    pending_commands = len(
        [row for row in command_rows if row.status == "PENDING_APPROVAL"]
    )
    approved_items = len([row for row in approval_rows if row.decision == "APPROVED"])
    active_workflows = len(
        [row for row in workflow_rows if row.workflow_status == "ACTIVE"]
    )
    warning_tasks = len([row for row in workload_rows if row.sla_status == "WARNING"])
    overdue_tasks = len([row for row in workload_rows if row.sla_status == "OVERDUE"])
    escalated_tasks = len(
        [row for row in workload_rows if row.escalation_status == "ESCALATED"]
    )

    recommendation_map: dict[str, list[SymployeeAIRecommendation]] = {}
    for row in recommendation_rows:
        recommendation_map.setdefault(row.identity_id, []).append(row)

    command_map: dict[str, list[SymployeeConnectorCommand]] = {}
    for row in command_rows:
        command_map.setdefault(row.identity_id, []).append(row)

    task_map: dict[str, list[SymployeeWorkflowTask]] = {}
    for row in workload_rows:
        task_map.setdefault(row.identity_id, []).append(row)

    source_map: dict[str, list[SymployeeDocumentSourceObject]] = {}
    for row in source_object_rows:
        source_map.setdefault(row.identity_id, []).append(row)

    workload_map: dict[str, dict] = {}
    for row in workload_rows:
        if row.status != "PENDING":
            continue
        key = row.assigned_user_id or row.assigned_role_code or "unassigned"
        payload = dict(row.task_payload_json or {})
        entry = workload_map.setdefault(
            key,
            {
                "assigned_user_id": row.assigned_user_id,
                "assigned_user_name": payload.get("assigned_user_name"),
                "assigned_role_code": row.assigned_role_code,
                "pending_tasks": 0,
                "warning_tasks": 0,
                "overdue_tasks": 0,
            },
        )
        entry["pending_tasks"] += 1
        if row.sla_status == "WARNING":
            entry["warning_tasks"] += 1
        if row.sla_status == "OVERDUE":
            entry["overdue_tasks"] += 1

    metadata_gap_count = 0
    attention_required_count = 0
    current_time = _now()
    review_age_days: list[float] = []
    completion_days: list[float] = []
    for row in recommendation_rows:
        if row.status == "NEEDS_REVIEW" and row.created_at:
            review_age_days.append((current_time - row.created_at).total_seconds() / 86400)
    for row in workload_rows:
        if row.completed_at and row.created_at:
            completion_days.append((row.completed_at - row.created_at).total_seconds() / 86400)
    for identity in identity_rows:
        missing_fields = _calculate_metadata_missing_fields(identity)
        tasks = task_map.get(identity.identity_id, [])
        commands = command_map.get(identity.identity_id, [])
        recommendations = recommendation_map.get(identity.identity_id, [])
        if missing_fields:
            metadata_gap_count += 1
        if (
            missing_fields
            or any(task.sla_status == "OVERDUE" for task in tasks)
            or any(command.status == "FAILED" for command in commands)
            or any(rec.status == "NEEDS_REVIEW" for rec in recommendations)
        ):
            attention_required_count += 1

    recent_activity = []
    repository_name_map = {
        row.repository_id: row.repository_name for row in repository_rows
    }
    for identity in sorted(
        identity_rows,
        key=lambda row: row.modified_at or row.created_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )[:10]:
        latest_source = sorted(
            source_map.get(identity.identity_id, []),
            key=lambda row: row.last_seen_at or row.first_seen_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        recent_activity.append(
            {
                "identity_id": identity.identity_id,
                "title": identity.title,
                "repository_name": repository_name_map.get(identity.repository_id, identity.repository_id),
                "status": identity.status,
                "last_seen_at": (
                    latest_source[0].last_seen_at.isoformat()
                    if latest_source and latest_source[0].last_seen_at
                    else None
                ),
                "modified_at": identity.modified_at.isoformat() if identity.modified_at else None,
            }
        )

    return {
        "total_documents": total_documents,
        "pending_recommendations": pending_recommendations,
        "pending_commands": pending_commands,
        "approved_items": approved_items,
        "active_workflows": active_workflows,
        "warning_tasks": warning_tasks,
        "overdue_tasks": overdue_tasks,
        "escalated_tasks": escalated_tasks,
        "reviewer_workload": sorted(
            workload_map.values(),
            key=lambda item: (-item["overdue_tasks"], -item["pending_tasks"], item["assigned_role_code"] or ""),
        )[:10],
        "analytics": {
            "register": {
                "repository_count": len({row.repository_id for row in identity_rows}),
                "project_count": len({row.project_code for row in identity_rows if row.project_code}),
                "document_type_count": len(
                    {row.document_type_code for row in identity_rows if row.document_type_code}
                ),
                "documents_missing_metadata": metadata_gap_count,
                "documents_requiring_attention": attention_required_count,
            },
            "review": {
                "pending_tasks": len([row for row in workload_rows if row.status == "PENDING"]),
                "completed_tasks": len([row for row in workload_rows if row.status == "COMPLETED"]),
                "average_open_review_age_days": _round_metric(
                    sum(review_age_days) / len(review_age_days) if review_age_days else None
                ),
                "average_review_completion_days": _round_metric(
                    sum(completion_days) / len(completion_days) if completion_days else None
                ),
            },
            "commands": {
                "failed_commands": len([row for row in command_rows if row.status == "FAILED"]),
                "approved_commands": len([row for row in command_rows if row.status == "APPROVED"]),
                "dispatched_commands": len([row for row in command_rows if row.status == "DISPATCHED"]),
                "acknowledged_commands": len(
                    [row for row in command_rows if row.status == "ACKNOWLEDGED"]
                ),
            },
            "compliance": {
                "documents_missing_document_number": len(
                    [row for row in identity_rows if not row.canonical_document_number]
                ),
                "documents_missing_project_code": len(
                    [row for row in identity_rows if not row.project_code]
                ),
                "documents_missing_originator_code": len(
                    [row for row in identity_rows if not row.originator_code]
                ),
                "documents_without_current_version": len(
                    [row for row in identity_rows if not row.current_version_id]
                ),
                "overdue_tasks": overdue_tasks,
                "escalated_tasks": escalated_tasks,
            },
            "breakdowns": {
                "by_repository": _build_count_breakdown(
                    [repository_name_map.get(row.repository_id, row.repository_id) for row in identity_rows]
                )[:10],
                "by_document_type": _build_count_breakdown(
                    [row.document_type_code for row in identity_rows]
                )[:10],
                "by_project": _build_count_breakdown([row.project_code for row in identity_rows])[:10],
                "recommendation_status": _build_count_breakdown(
                    [row.status for row in recommendation_rows]
                )[:10],
                "command_status": _build_count_breakdown([row.status for row in command_rows])[:10],
            },
            "recent_activity": recent_activity,
        },
    }


def list_document_identities(db: Session, tenant_id: str, limit: int = 100) -> dict:
    rows = (
        db.query(SymployeeDocumentIdentity)
        .filter(SymployeeDocumentIdentity.tenant_id == tenant_id)
        .order_by(SymployeeDocumentIdentity.created_at.desc())
        .limit(limit)
        .all()
    )
    items = []
    for row in rows:
        recommendation_count = (
            db.query(func.count(SymployeeAIRecommendation.recommendation_id))
            .filter(
                SymployeeAIRecommendation.tenant_id == tenant_id,
                SymployeeAIRecommendation.identity_id == row.identity_id,
            )
            .scalar()
            or 0
        )
        command_count = (
            db.query(func.count(SymployeeConnectorCommand.command_id))
            .filter(
                SymployeeConnectorCommand.tenant_id == tenant_id,
                SymployeeConnectorCommand.identity_id == row.identity_id,
            )
            .scalar()
            or 0
        )
        items.append(
            {
                **_serialize_identity(row),
                "recommendation_count": recommendation_count,
                "command_count": command_count,
            }
        )
    return {"items": items}


def get_document_identity_detail(db: Session, tenant_id: str, identity_id: str) -> dict:
    identity = (
        db.query(SymployeeDocumentIdentity)
        .filter(
            SymployeeDocumentIdentity.tenant_id == tenant_id,
            SymployeeDocumentIdentity.identity_id == identity_id,
        )
        .first()
    )
    if not identity:
        raise ValueError("Symployee document identity not found")

    versions = (
        db.query(SymployeeDocumentVersion)
        .filter(
            SymployeeDocumentVersion.tenant_id == tenant_id,
            SymployeeDocumentVersion.identity_id == identity_id,
        )
        .order_by(SymployeeDocumentVersion.created_at.desc())
        .all()
    )
    source_objects = (
        db.query(SymployeeDocumentSourceObject)
        .filter(
            SymployeeDocumentSourceObject.tenant_id == tenant_id,
            SymployeeDocumentSourceObject.identity_id == identity_id,
        )
        .all()
    )
    recommendations = (
        db.query(SymployeeAIRecommendation)
        .filter(
            SymployeeAIRecommendation.tenant_id == tenant_id,
            SymployeeAIRecommendation.identity_id == identity_id,
        )
        .order_by(SymployeeAIRecommendation.created_at.desc())
        .all()
    )
    refresh_workflow_sla_states(db, tenant_id, identity_id)
    if recommendations:
        symployee = ensure_document_controller_symployee(db, tenant_id)
        sync_document_workflow(
            db=db,
            tenant_id=tenant_id,
            symployee_id=symployee.symployee_id,
            identity_id=identity_id,
            version_id=identity.current_version_id,
        )
    workflow_instances = (
        db.query(SymployeeWorkflowInstance)
        .filter(
            SymployeeWorkflowInstance.tenant_id == tenant_id,
            SymployeeWorkflowInstance.identity_id == identity_id,
        )
        .order_by(SymployeeWorkflowInstance.created_at.desc())
        .all()
    )
    workflow_instance_ids = [row.workflow_instance_id for row in workflow_instances]
    workflow_tasks = (
        db.query(SymployeeWorkflowTask)
        .filter(
            SymployeeWorkflowTask.tenant_id == tenant_id,
            SymployeeWorkflowTask.workflow_instance_id.in_(workflow_instance_ids or ["__none__"]),
        )
        .order_by(
            SymployeeWorkflowTask.sequence_no.asc(),
            SymployeeWorkflowTask.created_at.asc(),
        )
        .all()
    )
    tasks_by_instance: dict[str, list[SymployeeWorkflowTask]] = {}
    for row in workflow_tasks:
        tasks_by_instance.setdefault(row.workflow_instance_id, []).append(row)
    commands = (
        db.query(SymployeeConnectorCommand)
        .filter(
            SymployeeConnectorCommand.tenant_id == tenant_id,
            SymployeeConnectorCommand.identity_id == identity_id,
        )
        .order_by(SymployeeConnectorCommand.created_at.desc())
        .all()
    )
    command_ids = [row.command_id for row in commands]
    command_approvals = (
        db.query(SymployeeApprovalRecord)
        .filter(
            SymployeeApprovalRecord.tenant_id == tenant_id,
            SymployeeApprovalRecord.approval_subject_type == "connector_command",
            SymployeeApprovalRecord.approval_subject_id.in_(command_ids or ["__none__"]),
        )
        .order_by(SymployeeApprovalRecord.created_at.desc())
        .all()
    )
    approvers = {
        row.user_id: row.name
        for row in db.query(User).filter(User.tenant_id == tenant_id).all()
    }
    approvals_by_command: dict[str, list[dict]] = {}
    for row in command_approvals:
        approvals_by_command.setdefault(row.approval_subject_id, []).append(
            {
                "approval_id": row.approval_id,
                "decision": row.decision,
                "approver_user_id": row.approver_user_id,
                "approver_name": approvers.get(row.approver_user_id),
                "comments": row.comments,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    try:
        resolve_document_file(db, tenant_id, identity_id, identity.current_version_id)
        actual_document_available = True
    except ValueError:
        actual_document_available = False

    return {
        "identity": _serialize_identity(identity),
        "versions": [_serialize_version(row) for row in versions],
        "source_objects": [
            {
                "source_object_id": row.source_object_id,
                "source_system_type": row.source_system_type,
                "external_object_id": row.external_object_id,
                "source_path": row.source_path,
                "source_version_ref": row.source_version_ref,
                "is_active": row.is_active,
                "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
                "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
            }
            for row in source_objects
        ],
        "recommendations": [_serialize_recommendation(row) for row in recommendations],
        "workflows": [
            _serialize_workflow_instance(
                row,
                tasks_by_instance.get(row.workflow_instance_id, []),
            )
            for row in workflow_instances
        ],
        "commands": [
            {
                **_serialize_command(
                    row,
                    document_title=identity.title,
                    source_recommendation=next(
                        (
                            recommendation
                            for recommendation in recommendations
                            if recommendation.recommendation_id == row.source_recommendation_id
                        ),
                        None,
                    ),
                ),
                "approval_history": approvals_by_command.get(row.command_id, []),
            }
            for row in commands
        ],
        "actual_document_available": actual_document_available,
    }


def list_recommendations(db: Session, tenant_id: str, limit: int = 200) -> dict:
    rows = (
        db.query(SymployeeAIRecommendation)
        .filter(SymployeeAIRecommendation.tenant_id == tenant_id)
        .order_by(SymployeeAIRecommendation.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"items": [_serialize_recommendation(row) for row in rows]}


def list_approvals(db: Session, tenant_id: str, limit: int = 200) -> dict:
    rows = (
        db.query(SymployeeApprovalRecord)
        .filter(SymployeeApprovalRecord.tenant_id == tenant_id)
        .order_by(SymployeeApprovalRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    approvers = {
        row.user_id: row.name
        for row in db.query(User)
        .filter(User.tenant_id == tenant_id)
        .all()
    }
    return {
        "items": [
            {
                "approval_id": row.approval_id,
                "approval_subject_type": row.approval_subject_type,
                "approval_subject_id": row.approval_subject_id,
                "decision": row.decision,
                "approver_user_id": row.approver_user_id,
                "approver_name": approvers.get(row.approver_user_id),
                "comments": row.comments,
                "policy_code": row.policy_code,
                "policy_version_no": row.policy_version_no,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }


def list_commands(db: Session, tenant_id: str, limit: int = 200) -> dict:
    rows = (
        db.query(SymployeeConnectorCommand)
        .filter(SymployeeConnectorCommand.tenant_id == tenant_id)
        .order_by(SymployeeConnectorCommand.created_at.desc())
        .limit(limit)
        .all()
    )
    identity_ids = {row.identity_id for row in rows if row.identity_id}
    recommendation_ids = {
        row.source_recommendation_id for row in rows if row.source_recommendation_id
    }
    identities = {
        row.identity_id: row
        for row in db.query(SymployeeDocumentIdentity)
        .filter(
            SymployeeDocumentIdentity.tenant_id == tenant_id,
            SymployeeDocumentIdentity.identity_id.in_(identity_ids or {"__none__"}),
        )
        .all()
    }
    recommendations = {
        row.recommendation_id: row
        for row in db.query(SymployeeAIRecommendation)
        .filter(
            SymployeeAIRecommendation.tenant_id == tenant_id,
            SymployeeAIRecommendation.recommendation_id.in_(recommendation_ids or {"__none__"}),
        )
        .all()
    }
    return {
        "items": [
            _serialize_command(
                row,
                document_title=(
                    identities[row.identity_id].title if identities.get(row.identity_id) else None
                ),
                source_recommendation=recommendations.get(row.source_recommendation_id),
            )
            for row in rows
        ]
    }


def build_master_document_register(db: Session, tenant_id: str) -> dict:
    refresh_workflow_sla_states(db, tenant_id)

    rows = (
        db.query(SymployeeDocumentIdentity, Repository)
        .join(Repository, Repository.repository_id == SymployeeDocumentIdentity.repository_id)
        .filter(SymployeeDocumentIdentity.tenant_id == tenant_id)
        .order_by(SymployeeDocumentIdentity.created_at.desc())
        .all()
    )
    identity_ids = [identity.identity_id for identity, _repo in rows]
    version_ids = [identity.current_version_id for identity, _repo in rows if identity.current_version_id]
    version_rows = (
        db.query(SymployeeDocumentVersion)
        .filter(
            SymployeeDocumentVersion.tenant_id == tenant_id,
            SymployeeDocumentVersion.version_id.in_(version_ids or ["__none__"]),
        )
        .all()
    )
    recommendation_rows = (
        db.query(SymployeeAIRecommendation)
        .filter(
            SymployeeAIRecommendation.tenant_id == tenant_id,
            SymployeeAIRecommendation.identity_id.in_(identity_ids or ["__none__"]),
        )
        .all()
    )
    command_rows = (
        db.query(SymployeeConnectorCommand)
        .filter(
            SymployeeConnectorCommand.tenant_id == tenant_id,
            SymployeeConnectorCommand.identity_id.in_(identity_ids or ["__none__"]),
        )
        .all()
    )
    task_rows = (
        db.query(SymployeeWorkflowTask)
        .filter(
            SymployeeWorkflowTask.tenant_id == tenant_id,
            SymployeeWorkflowTask.identity_id.in_(identity_ids or ["__none__"]),
        )
        .all()
    )
    source_rows = (
        db.query(SymployeeDocumentSourceObject)
        .filter(
            SymployeeDocumentSourceObject.tenant_id == tenant_id,
            SymployeeDocumentSourceObject.identity_id.in_(identity_ids or ["__none__"]),
            SymployeeDocumentSourceObject.is_active.is_(True),
        )
        .all()
    )
    version_map = {row.version_id: row for row in version_rows}
    recommendation_map: dict[str, list[SymployeeAIRecommendation]] = {}
    for row in recommendation_rows:
        recommendation_map.setdefault(row.identity_id, []).append(row)
    command_map: dict[str, list[SymployeeConnectorCommand]] = {}
    for row in command_rows:
        command_map.setdefault(row.identity_id, []).append(row)
    task_map: dict[str, list[SymployeeWorkflowTask]] = {}
    for row in task_rows:
        task_map.setdefault(row.identity_id, []).append(row)
    source_map: dict[str, list[SymployeeDocumentSourceObject]] = {}
    for row in source_rows:
        source_map.setdefault(row.identity_id, []).append(row)

    items = []
    for identity, repo in rows:
        current_version = version_map.get(identity.current_version_id)
        recommendations = recommendation_map.get(identity.identity_id, [])
        commands = command_map.get(identity.identity_id, [])
        tasks = task_map.get(identity.identity_id, [])
        sources = source_map.get(identity.identity_id, [])
        missing_fields = _calculate_metadata_missing_fields(identity)
        latest_source = max(
            sources,
            key=lambda row: row.last_seen_at or row.first_seen_at or datetime.min.replace(tzinfo=UTC),
            default=None,
        )
        latest_task = max(
            tasks,
            key=lambda row: row.created_at or datetime.min.replace(tzinfo=UTC),
            default=None,
        )
        latest_command = max(
            commands,
            key=lambda row: row.created_at or datetime.min.replace(tzinfo=UTC),
            default=None,
        )
        items.append(
            {
                "identity_id": identity.identity_id,
                "repository_name": repo.repository_name,
                "repository_id": repo.repository_id,
                "canonical_document_number": identity.canonical_document_number,
                "title": identity.title,
                "document_type_code": identity.document_type_code,
                "discipline_code": identity.discipline_code,
                "project_code": identity.project_code,
                "originator_code": identity.originator_code,
                "status": identity.status,
                "current_version_id": identity.current_version_id,
                "current_revision_code": current_version.revision_code if current_version else None,
                "current_version_label": current_version.version_label if current_version else None,
                "current_file_name": current_version.file_name if current_version else None,
                "file_extension": current_version.file_extension if current_version else None,
                "page_count": current_version.page_count if current_version else None,
                "source_path": latest_source.source_path if latest_source else None,
                "source_version_ref": latest_source.source_version_ref if latest_source else None,
                "last_seen_at": (
                    latest_source.last_seen_at.isoformat()
                    if latest_source and latest_source.last_seen_at
                    else None
                ),
                "recommendation_count": len(recommendations),
                "pending_recommendation_count": len(
                    [row for row in recommendations if row.status == "NEEDS_REVIEW"]
                ),
                "command_count": len(commands),
                "pending_command_count": len(
                    [row for row in commands if row.status == "PENDING_APPROVAL"]
                ),
                "failed_command_count": len(
                    [row for row in commands if row.status == "FAILED"]
                ),
                "latest_command_status": latest_command.status if latest_command else None,
                "open_workflow_task_count": len(
                    [row for row in tasks if row.status == "PENDING"]
                ),
                "overdue_workflow_task_count": len(
                    [row for row in tasks if row.sla_status == "OVERDUE"]
                ),
                "latest_sla_status": latest_task.sla_status if latest_task else None,
                "latest_escalation_status": (
                    latest_task.escalation_status if latest_task else None
                ),
                "assigned_user_name": (
                    (latest_task.task_payload_json or {}).get("assigned_user_name")
                    if latest_task
                    else None
                ),
                "assigned_role_code": latest_task.assigned_role_code if latest_task else None,
                "metadata_missing_fields": missing_fields,
                "metadata_completeness_pct": round(((5 - len(missing_fields)) / 5) * 100, 1),
                "attention_flags": [
                    *(["metadata_incomplete"] if missing_fields else []),
                    *(
                        ["review_pending"]
                        if any(row.status == "NEEDS_REVIEW" for row in recommendations)
                        else []
                    ),
                    *(
                        ["workflow_overdue"]
                        if any(row.sla_status == "OVERDUE" for row in tasks)
                        else []
                    ),
                    *(
                        ["command_failed"]
                        if any(row.status == "FAILED" for row in commands)
                        else []
                    ),
                ],
                "created_at": identity.created_at.isoformat() if identity.created_at else None,
            }
        )

    return {
        "items": items,
        "summary": {
            "total_documents": len(items),
            "repository_count": len({identity.repository_id for identity, _repo in rows}),
            "project_count": len({identity.project_code for identity, _repo in rows if identity.project_code}),
            "documents_missing_metadata": len(
                [row for row in items if row["metadata_missing_fields"]]
            ),
            "documents_pending_review": len(
                [row for row in items if row["pending_recommendation_count"] > 0]
            ),
            "documents_with_overdue_tasks": len(
                [row for row in items if row["overdue_workflow_task_count"] > 0]
            ),
        },
    }
