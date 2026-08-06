from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db_models import (
    Repository,
    AuditLog,
    SymployeeAIRecommendation,
    SymployeeDocumentIdentity,
    SymployeePolicyConfig,
    User,
    SymployeeWorkflowInstance,
    SymployeeWorkflowTask,
)
from app.services.symployee_lifecycle_service import create_lifecycle_event
from app.services.symployee_policy_service import resolve_policy
from app.services.symployee_records_service import (
    evaluate_record_declaration,
    evaluate_record_lifecycle_rule,
)


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
    workflow_instance_id: str | None,
    event_type: str,
    previous_state: str | None,
    new_state: str,
    metadata_json: dict | None = None,
) -> None:
    create_lifecycle_event(
        db,
        tenant_id,
        identity_id=identity_id,
        version_id=version_id,
        event_type=event_type,
        state_dimension="review_status",
        previous_state=previous_state,
        new_state=new_state,
        workflow_instance_id=workflow_instance_id,
        metadata_json=metadata_json,
    )


def _resolve_task_outcome_codes(
    recommendation: SymployeeAIRecommendation,
    task_status: str,
) -> tuple[str, str]:
    outcome = (recommendation.approval_outcome or "").upper()
    status = (recommendation.status or "").upper()

    if outcome == "APPROVED" or status == "APPROVED":
        return "APPROVED", "ACCEPTED"
    if outcome == "REJECTED" or status == "REJECTED":
        return "REJECTED", "REJECTED"
    if outcome == "OVERRIDDEN" or status == "SUPERSEDED":
        return "OVERRIDDEN", "SUPERSEDED"
    if task_status in {"COMPLETED", "REJECTED"}:
        return task_status, task_status
    return "PENDING", "AWAITING_REVIEW"


def _resolve_review_status(tasks: list[SymployeeWorkflowTask]) -> str:
    if not tasks:
        return "AWAITING_REVIEW"
    if any(task.status == "REJECTED" for task in tasks):
        return "REVIEW_REJECTED"
    if all(task.status == "COMPLETED" for task in tasks):
        return "REVIEW_COMPLETED"
    return "IN_REVIEW"


def _get_active_reviewer_policy(
    db: Session,
    tenant_id: str,
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
) -> dict | None:
    return resolve_policy(
        db=db,
        tenant_id=tenant_id,
        policy_domain="reviewer_assignment",
        repository_id=repository_id,
        business_area=business_area,
        project_code=project_code,
    )


def _get_active_sla_policy(
    db: Session,
    tenant_id: str,
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
) -> dict | None:
    return resolve_policy(
        db=db,
        tenant_id=tenant_id,
        policy_domain="sla_rules",
        repository_id=repository_id,
        business_area=business_area,
        project_code=project_code,
    )


def _append_task_event(
    payload: dict,
    *,
    event_code: str,
    occurred_at: datetime,
    details: dict | None = None,
) -> dict:
    updated = dict(payload or {})
    history = list(updated.get("workflow_events") or [])
    last = history[-1] if history else None
    candidate = {
        "event_code": event_code,
        "occurred_at": occurred_at.isoformat(),
        "details": details or {},
    }
    if last and last.get("event_code") == event_code and last.get("details") == candidate["details"]:
        updated["workflow_events"] = history
        return updated
    history.append(candidate)
    updated["workflow_events"] = history[-20:]
    return updated


def _queue_workflow_notification(
    db: Session,
    task: SymployeeWorkflowTask,
    *,
    event_type: str,
    description: str,
    occurred_at: datetime,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            audit_id=_new_id("AUD"),
            tenant_id=task.tenant_id,
            user_id=task.assigned_user_id,
            event_type=event_type,
            event_category="SYNTHETIC_EMPLOYEE_NOTIFICATION",
            description=description,
            resource_type="symployee_workflow_task",
            resource_id=task.workflow_task_id,
            metadata_json={
                "workflow_instance_id": task.workflow_instance_id,
                "identity_id": task.identity_id,
                "version_id": task.version_id,
                "task_code": task.task_code,
                "assigned_role_code": task.assigned_role_code,
                "assigned_user_id": task.assigned_user_id,
                "due_at": task.due_at.isoformat() if task.due_at else None,
                "occurred_at": occurred_at.isoformat(),
                **(metadata or {}),
            },
        )
    )


def _match_rule(match_config: dict, context: dict) -> bool:
    if not match_config:
        return True

    direct_match = {
        key: value
        for key, value in match_config.items()
        if key not in {"all", "any"}
    }
    for key, expected in direct_match.items():
        actual = context.get(key)
        if actual is None:
            return False
        if str(actual).strip().lower() != str(expected).strip().lower():
            return False

    all_rules = list(match_config.get("all") or [])
    for rule in all_rules:
        if not _match_rule(dict(rule or {}), context):
            return False

    any_rules = list(match_config.get("any") or [])
    if any_rules and not any(_match_rule(dict(rule or {}), context) for rule in any_rules):
        return False
    return True


def _build_routing_context(
    db: Session,
    identity: SymployeeDocumentIdentity,
    recommendation: SymployeeAIRecommendation,
) -> dict:
    recommendation_data = dict(recommendation.recommendation_json or {})
    metadata_fields = dict(recommendation_data.get("fields") or {})
    repository = (
        db.query(Repository)
        .filter(Repository.repository_id == identity.repository_id)
        .first()
    )
    confidence_score = recommendation.confidence_score
    confidence_band = (
        "high" if (confidence_score or 0) >= 0.85 else "medium" if (confidence_score or 0) >= 0.6 else "low"
    )
    return {
        **metadata_fields,
        **recommendation_data,
        "document_type_code": identity.document_type_code,
        "project_code": identity.project_code,
        "discipline_code": identity.discipline_code,
        "originator_code": identity.originator_code,
        "canonical_document_number": identity.canonical_document_number,
        "title": identity.title,
        "repository_id": identity.repository_id,
        "business_area": repository.business_area if repository else None,
        "repository_name": repository.repository_name if repository else None,
        "source_type": repository.source_type if repository else None,
        "recommendation_type": recommendation.recommendation_type,
        "confidence_score": confidence_score,
        "confidence_band": confidence_band,
        "priority": metadata_fields.get("priority") or recommendation_data.get("priority"),
        "confidentiality": metadata_fields.get("confidentiality") or recommendation_data.get("confidentiality"),
        "package": metadata_fields.get("package") or recommendation_data.get("package"),
        "work_breakdown_structure": metadata_fields.get("work_breakdown_structure") or recommendation_data.get("work_breakdown_structure"),
        "department": metadata_fields.get("department") or recommendation_data.get("department"),
        "document_status": metadata_fields.get("document_status") or recommendation_data.get("document_status"),
    }


def _resolve_user_from_assignee(
    db: Session,
    tenant_id: str,
    assignee: dict,
) -> tuple[str | None, str | None, str | None]:
    role_code = assignee.get("role_code")
    user_id = assignee.get("user_id")
    user_email = assignee.get("user_email")
    strategy = assignee.get("strategy")

    user_query = db.query(User).filter(
        User.tenant_id == tenant_id,
        User.status == "ACTIVE",
    )
    user = None
    if user_id:
        user = user_query.filter(User.user_id == user_id).order_by(User.name.asc()).first()
    elif user_email:
        user = user_query.filter(User.email == user_email).order_by(User.name.asc()).first()
    elif role_code:
        candidates = user_query.filter(User.role == role_code).order_by(User.name.asc()).all()
        if strategy == "least_loaded_in_role" and candidates:
            def pending_load(candidate: User) -> int:
                return (
                    db.query(SymployeeWorkflowTask)
                    .filter(
                        SymployeeWorkflowTask.tenant_id == tenant_id,
                        SymployeeWorkflowTask.assigned_user_id == candidate.user_id,
                        SymployeeWorkflowTask.status == "PENDING",
                    )
                    .count()
                )
            user = min(candidates, key=pending_load)
        else:
            user = candidates[0] if candidates else None

    if user:
        return role_code or user.role, user.user_id, user.name
    return role_code, None, None


def _resolve_reviewer_assignment(
    db: Session,
    tenant_id: str,
    identity: SymployeeDocumentIdentity,
    recommendation: SymployeeAIRecommendation,
    task_code: str,
    reviewer_policy: dict | None = None,
) -> dict:
    policy = reviewer_policy or _get_active_reviewer_policy(db, tenant_id)
    policy_config = dict(policy.get("config") or {}) if policy else {}
    task_assignments = dict(policy_config.get("task_assignments") or {})
    routing_rules = list(policy_config.get("routing_rules") or [])
    default_assignment = dict(policy_config.get("default_assignment") or {})
    context = _build_routing_context(db, identity, recommendation)

    selected_assignee = None
    selected_rule = None
    for rule in routing_rules:
        if rule.get("task_code") != task_code:
            continue
        if _match_rule(dict(rule.get("match") or {}), context):
            selected_assignee = dict(rule.get("assignee") or {})
            selected_rule = dict(rule)
            break

    if not selected_assignee:
        selected_assignee = dict(task_assignments.get(task_code) or {})
    if not selected_assignee:
        selected_assignee = default_assignment

    role_code, assigned_user_id, assigned_user_name = _resolve_user_from_assignee(
        db=db,
        tenant_id=tenant_id,
        assignee=selected_assignee,
    )

    return {
        "assigned_role_code": role_code or "document_controller",
        "assigned_user_id": assigned_user_id,
        "assigned_user_name": assigned_user_name,
        "policy_code": policy.get("policy_code") if policy else None,
        "policy_version_no": policy.get("version_no") if policy else None,
        "selected_rule": selected_rule,
        "routing_context": context,
    }


def _resolve_sla_rule(
    task_code: str,
    sla_policy: dict | None,
) -> dict:
    policy_config = dict(sla_policy.get("config") or {}) if sla_policy else {}
    default_rule = dict(policy_config.get("default_rule") or {})
    task_rules = dict(policy_config.get("task_rules") or {})
    resolved = {
        **default_rule,
        **dict(task_rules.get(task_code) or {}),
    }
    return {
        "target_hours": int(resolved.get("target_hours") or 48),
        "warning_before_hours": int(resolved.get("warning_before_hours") or 12),
        "escalate_after_hours": int(resolved.get("escalate_after_hours") or 24),
        "policy_code": sla_policy.get("policy_code") if sla_policy else None,
        "policy_version_no": sla_policy.get("version_no") if sla_policy else None,
    }


def _resolve_due_at(started_at: datetime, sla_rule: dict) -> datetime:
    return started_at + timedelta(hours=int(sla_rule.get("target_hours") or 48))


def _resolve_sla_status(
    task: SymployeeWorkflowTask,
    sla_rule: dict,
    now: datetime,
) -> tuple[str, str]:
    if task.status in {"COMPLETED", "REJECTED"}:
        return "COMPLETED", "NONE"

    if not task.due_at:
        return "ON_TRACK", "NONE"

    warning_before_hours = int(sla_rule.get("warning_before_hours") or 12)
    escalate_after_hours = int(sla_rule.get("escalate_after_hours") or 24)
    warning_at = task.due_at - timedelta(hours=warning_before_hours)
    escalate_at = task.due_at + timedelta(hours=escalate_after_hours)

    if now >= escalate_at:
        return "OVERDUE", "ESCALATED"
    if now >= task.due_at:
        return "OVERDUE", "NONE"
    if now >= warning_at:
        return "WARNING", "WARNING"
    return "ON_TRACK", "NONE"


def _compute_days_overdue(task: SymployeeWorkflowTask, now: datetime) -> int:
    if not task.due_at or task.status in {"COMPLETED", "REJECTED"} or now <= task.due_at:
        return 0
    return max(0, (now.date() - task.due_at.date()).days)


def _build_task_specs(recommendations: list[SymployeeAIRecommendation]) -> list[dict]:
    recommendation_map = {
        row.recommendation_type: row
        for row in recommendations
    }
    specs: list[dict] = []

    classification = recommendation_map.get("classification")
    if classification:
        specs.append(
            {
                "task_code": "classification_review",
                "task_name": "Review classification recommendation",
                "task_type": "recommendation_review",
                "sequence_no": 10,
                "assigned_role_code": "document_controller",
                "recommendation": classification,
            }
        )

    metadata = recommendation_map.get("metadata_extraction")
    if metadata:
        specs.append(
            {
                "task_code": "metadata_review",
                "task_name": "Review metadata extraction recommendation",
                "task_type": "recommendation_review",
                "sequence_no": 20,
                "assigned_role_code": "document_controller",
                "recommendation": metadata,
            }
        )

    return specs


def _resolve_task_status(recommendation: SymployeeAIRecommendation) -> tuple[str, str]:
    outcome = (recommendation.approval_outcome or "").upper()
    status = (recommendation.status or "").upper()

    if outcome == "APPROVED" or status == "APPROVED":
        return "COMPLETED", "ON_TRACK"
    if outcome == "REJECTED" or status == "REJECTED":
        return "REJECTED", "ON_TRACK"
    if outcome == "OVERRIDDEN" or status == "SUPERSEDED":
        return "COMPLETED", "ON_TRACK"
    return "PENDING", "ON_TRACK"


def sync_document_workflow(
    db: Session,
    tenant_id: str,
    symployee_id: str,
    identity_id: str,
    version_id: str | None,
) -> dict | None:
    identity = (
        db.query(SymployeeDocumentIdentity)
        .filter(
            SymployeeDocumentIdentity.tenant_id == tenant_id,
            SymployeeDocumentIdentity.identity_id == identity_id,
        )
        .first()
    )
    if not identity:
        return None

    recommendations = (
        db.query(SymployeeAIRecommendation)
        .filter(
            SymployeeAIRecommendation.tenant_id == tenant_id,
            SymployeeAIRecommendation.identity_id == identity_id,
            SymployeeAIRecommendation.version_id == version_id,
        )
        .order_by(SymployeeAIRecommendation.created_at.asc())
        .all()
    )
    if not recommendations:
        return None

    instance = (
        db.query(SymployeeWorkflowInstance)
        .filter(
            SymployeeWorkflowInstance.tenant_id == tenant_id,
            SymployeeWorkflowInstance.identity_id == identity_id,
            SymployeeWorkflowInstance.version_id == version_id,
            SymployeeWorkflowInstance.workflow_code == "document_intake_review",
        )
        .first()
    )
    if not instance:
        instance = SymployeeWorkflowInstance(
            workflow_instance_id=_new_id("SWI"),
            tenant_id=tenant_id,
            symployee_id=symployee_id,
            identity_id=identity_id,
            version_id=version_id,
            workflow_code="document_intake_review",
            workflow_status="ACTIVE",
            routing_status="PLANNED",
            current_step_code=None,
            policy_code="system_default_document_intake_review",
            policy_version_no=1,
            workflow_payload_json={
                "document_title": identity.title,
                "document_type_code": identity.document_type_code,
                "repository_id": identity.repository_id,
                "routing_basis": "default_recommendation_review_flow",
            },
            started_at=_now(),
            lifecycle_state_dimension="review_status",
            lifecycle_target_state="IN_REVIEW",
        )
        db.add(instance)
        db.flush()

    existing_tasks = {
        row.task_code: row
        for row in db.query(SymployeeWorkflowTask)
        .filter(
            SymployeeWorkflowTask.tenant_id == tenant_id,
            SymployeeWorkflowTask.workflow_instance_id == instance.workflow_instance_id,
        )
        .all()
    }

    desired_tasks = _build_task_specs(recommendations)
    current_step_code: str | None = None
    workflow_status = "COMPLETED"
    previous_workflow_status = instance.workflow_status
    repository = (
        db.query(Repository)
        .filter(Repository.repository_id == identity.repository_id)
        .first()
    )
    active_reviewer_policy = _get_active_reviewer_policy(
        db,
        tenant_id,
        repository_id=identity.repository_id,
        business_area=repository.business_area if repository else None,
        project_code=identity.project_code,
    )
    active_sla_policy = _get_active_sla_policy(
        db,
        tenant_id,
        repository_id=identity.repository_id,
        business_area=repository.business_area if repository else None,
        project_code=identity.project_code,
    )

    for spec in desired_tasks:
        recommendation = spec["recommendation"]
        task = existing_tasks.get(spec["task_code"])
        status, _ = _resolve_task_status(recommendation)
        assignment = _resolve_reviewer_assignment(
            db=db,
            tenant_id=tenant_id,
            identity=identity,
            recommendation=recommendation,
            task_code=spec["task_code"],
            reviewer_policy=active_reviewer_policy,
        )
        sla_rule = _resolve_sla_rule(
            task_code=spec["task_code"],
            sla_policy=active_sla_policy,
        )
        now = _now()
        outcome_code, response_code = _resolve_task_outcome_codes(recommendation, status)
        if task is None:
            started_at = now if status in {"PENDING", "IN_PROGRESS"} else None
            due_at = _resolve_due_at(started_at or now, sla_rule)
            sla_status, escalation_status = _resolve_sla_status(
                SymployeeWorkflowTask(
                    workflow_task_id="preview",
                    tenant_id=tenant_id,
                    workflow_instance_id=instance.workflow_instance_id,
                    identity_id=identity_id,
                    version_id=version_id,
                    task_code=spec["task_code"],
                    task_name=spec["task_name"],
                    task_type=spec["task_type"],
                    status=status,
                    sequence_no=spec["sequence_no"],
                    assigned_role_code=assignment["assigned_role_code"],
                    assigned_user_id=assignment["assigned_user_id"],
                    due_at=due_at,
                ),
                sla_rule,
                now,
            )
            task = SymployeeWorkflowTask(
                workflow_task_id=_new_id("SWT"),
                tenant_id=tenant_id,
                workflow_instance_id=instance.workflow_instance_id,
                identity_id=identity_id,
                version_id=version_id,
                task_code=spec["task_code"],
                task_name=spec["task_name"],
                task_type=spec["task_type"],
                sequence_no=spec["sequence_no"],
                assigned_role_code=assignment["assigned_role_code"],
                assigned_user_id=assignment["assigned_user_id"],
                due_at=due_at,
                started_at=started_at,
                completed_at=now if status in {"COMPLETED", "REJECTED"} else None,
                outcome_code=outcome_code,
                response_code=response_code,
                sla_status=sla_status,
                escalation_status=escalation_status,
                task_payload_json={
                    "recommendation_id": recommendation.recommendation_id,
                    "recommendation_type": recommendation.recommendation_type,
                    "recommendation_status": recommendation.status,
                    "confidence_score": recommendation.confidence_score,
                    "assigned_user_name": assignment["assigned_user_name"],
                    "reviewer_policy_code": assignment["policy_code"],
                    "reviewer_policy_version_no": assignment["policy_version_no"],
                    "sla_policy_code": sla_rule["policy_code"],
                    "sla_policy_version_no": sla_rule["policy_version_no"],
                    "sla_rule": sla_rule,
                    "selected_rule": assignment["selected_rule"],
                    "routing_context": assignment["routing_context"],
                },
                status=status,
            )
            task.task_payload_json = _append_task_event(
                task.task_payload_json or {},
                event_code="task_created",
                occurred_at=now,
                details={
                    "assigned_role_code": assignment["assigned_role_code"],
                    "assigned_user_id": assignment["assigned_user_id"],
                },
            )
            db.add(task)
        else:
            task.task_name = spec["task_name"]
            task.task_type = spec["task_type"]
            task.sequence_no = spec["sequence_no"]
            task.assigned_role_code = assignment["assigned_role_code"]
            task.assigned_user_id = assignment["assigned_user_id"]
            task.outcome_code = outcome_code
            task.response_code = response_code
            if not task.started_at and status in {"PENDING", "IN_PROGRESS"}:
                task.started_at = now
            if task.due_at is None:
                task.due_at = _resolve_due_at(task.started_at or now, sla_rule)
            task.sla_status, task.escalation_status = _resolve_sla_status(task, sla_rule, now)
            task.task_payload_json = {
                "recommendation_id": recommendation.recommendation_id,
                "recommendation_type": recommendation.recommendation_type,
                "recommendation_status": recommendation.status,
                "confidence_score": recommendation.confidence_score,
                "assigned_user_name": assignment["assigned_user_name"],
                "reviewer_policy_code": assignment["policy_code"],
                "reviewer_policy_version_no": assignment["policy_version_no"],
                "sla_policy_code": sla_rule["policy_code"],
                "sla_policy_version_no": sla_rule["policy_version_no"],
                "sla_rule": sla_rule,
                "selected_rule": assignment["selected_rule"],
                "routing_context": assignment["routing_context"],
                "workflow_events": list((task.task_payload_json or {}).get("workflow_events") or []),
            }
            if task.status != status:
                if status in {"COMPLETED", "REJECTED"}:
                    task.completed_at = now
                elif status == "PENDING":
                    task.completed_at = None
                task.status = status
                task.task_payload_json = _append_task_event(
                    task.task_payload_json or {},
                    event_code=f"task_status_{status.lower()}",
                    occurred_at=now,
                    details={"task_code": task.task_code},
                )
            task.sla_status, task.escalation_status = _resolve_sla_status(task, sla_rule, now)

        if task.status == "PENDING" and current_step_code is None:
            current_step_code = task.task_code
        if task.status not in {"COMPLETED", "REJECTED"}:
            workflow_status = "ACTIVE"

    instance.routing_status = "ROUTED"
    instance.current_step_code = current_step_code
    instance.workflow_status = workflow_status
    instance.completed_at = _now() if workflow_status == "COMPLETED" else None
    db.flush()
    tasks = (
        db.query(SymployeeWorkflowTask)
        .filter(
            SymployeeWorkflowTask.tenant_id == tenant_id,
            SymployeeWorkflowTask.workflow_instance_id == instance.workflow_instance_id,
        )
        .order_by(SymployeeWorkflowTask.sequence_no.asc(), SymployeeWorkflowTask.created_at.asc())
        .all()
    )
    previous_review_status = identity.review_status
    review_status = _resolve_review_status(tasks)
    identity.review_status = review_status
    instance.lifecycle_state_dimension = "review_status"
    instance.lifecycle_target_state = review_status
    instance.workflow_payload_json = {
        **(instance.workflow_payload_json or {}),
        "task_count": len(desired_tasks),
        "pending_task_count": len(
            [
                spec
                for spec in desired_tasks
                if (existing_tasks.get(spec["task_code"]) is None)
                or (existing_tasks.get(spec["task_code"]).status == "PENDING")
            ]
        ),
        "reviewer_assignment_policy_code": (
            active_reviewer_policy.get("policy_code") if active_reviewer_policy else None
        ),
        "sla_policy_code": active_sla_policy.get("policy_code") if active_sla_policy else None,
        "review_status": review_status,
    }
    if previous_review_status != review_status:
        _append_lifecycle_event(
            db,
            tenant_id=tenant_id,
            identity_id=identity.identity_id,
            version_id=version_id,
            workflow_instance_id=instance.workflow_instance_id,
            event_type="REVIEW_STATUS_CHANGED",
            previous_state=previous_review_status,
            new_state=review_status,
            metadata_json={
                "workflow_code": instance.workflow_code,
                "workflow_status": workflow_status,
                "current_step_code": current_step_code,
                "task_count": len(tasks),
                "pending_task_count": len([row for row in tasks if row.status == "PENDING"]),
            },
        )

    db.commit()
    db.refresh(instance)

    declaration_evaluation = None
    lifecycle_rule_evaluation = None
    if previous_workflow_status != "COMPLETED" and instance.workflow_status == "COMPLETED":
        declaration_evaluation = evaluate_record_declaration(
            db,
            tenant_id,
            identity_id=identity_id,
            version_id=version_id,
            trigger_event="WORKFLOW_COMPLETION",
            dry_run=False,
            performed_by=None,
            evaluation_reason="Workflow completion declaration evaluation",
            metadata_json={
                "workflow_instance_id": instance.workflow_instance_id,
                "workflow_code": instance.workflow_code,
                "workflow_status": instance.workflow_status,
            },
        )
        lifecycle_rule_evaluation = evaluate_record_lifecycle_rule(
            db,
            tenant_id,
            identity_id=identity_id,
            version_id=version_id,
            trigger_event="WORKFLOW_COMPLETION",
            performed_by=None,
            evaluation_reason="Workflow completion lifecycle evaluation",
            metadata_json={
                "workflow_instance_id": instance.workflow_instance_id,
                "workflow_code": instance.workflow_code,
                "workflow_status": instance.workflow_status,
            },
        )

    return {
        "workflow_instance_id": instance.workflow_instance_id,
        "workflow_code": instance.workflow_code,
        "workflow_status": instance.workflow_status,
        "routing_status": instance.routing_status,
        "current_step_code": instance.current_step_code,
        "task_count": len(tasks),
        "pending_task_count": len([row for row in tasks if row.status == "PENDING"]),
        "declaration_evaluation": declaration_evaluation,
        "lifecycle_rule_evaluation": lifecycle_rule_evaluation,
        "tasks": [
            {
                "workflow_task_id": row.workflow_task_id,
                "task_code": row.task_code,
                "task_name": row.task_name,
                "task_type": row.task_type,
                "status": row.status,
                "sequence_no": row.sequence_no,
                "assigned_role_code": row.assigned_role_code,
                "assigned_user_id": row.assigned_user_id,
                "due_at": row.due_at.isoformat() if row.due_at else None,
                "sla_status": row.sla_status,
                "escalation_status": row.escalation_status,
                "task_payload": row.task_payload_json or {},
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            }
            for row in tasks
        ],
    }


def refresh_workflow_sla_states(
    db: Session,
    tenant_id: str,
    identity_id: str | None = None,
) -> None:
    identity = None
    if identity_id:
        identity = (
            db.query(SymployeeDocumentIdentity)
            .filter(
                SymployeeDocumentIdentity.tenant_id == tenant_id,
                SymployeeDocumentIdentity.identity_id == identity_id,
            )
            .first()
        )
    repository = None
    if identity:
        repository = (
            db.query(Repository)
            .filter(Repository.repository_id == identity.repository_id)
            .first()
        )
    active_sla_policy = _get_active_sla_policy(
        db,
        tenant_id,
        repository_id=identity.repository_id if identity else None,
        business_area=repository.business_area if repository else None,
        project_code=identity.project_code if identity else None,
    )
    query = db.query(SymployeeWorkflowTask).filter(
        SymployeeWorkflowTask.tenant_id == tenant_id,
    )
    if identity_id:
        query = query.filter(SymployeeWorkflowTask.identity_id == identity_id)

    tasks = query.all()
    now = _now()
    changed = False
    for task in tasks:
        sla_rule = _resolve_sla_rule(task.task_code, active_sla_policy)
        previous_sla_status = task.sla_status
        previous_escalation_status = task.escalation_status
        sla_status, escalation_status = _resolve_sla_status(task, sla_rule, now)
        if task.sla_status != sla_status:
            task.sla_status = sla_status
            changed = True
        if task.escalation_status != escalation_status:
            task.escalation_status = escalation_status
            changed = True
        payload = dict(task.task_payload_json or {})
        payload["sla_policy_code"] = sla_rule["policy_code"]
        payload["sla_policy_version_no"] = sla_rule["policy_version_no"]
        payload["sla_rule"] = sla_rule
        if previous_sla_status != sla_status:
            event_code = (
                "reminder_generated"
                if sla_status == "WARNING"
                else "task_overdue"
                if sla_status == "OVERDUE"
                else "sla_reset"
            )
            payload = _append_task_event(
                payload,
                event_code=event_code,
                occurred_at=now,
                details={"previous_sla_status": previous_sla_status, "sla_status": sla_status},
            )
            if event_code == "reminder_generated":
                _queue_workflow_notification(
                    db,
                    task,
                    event_type="SYMPLOYEE_WORKFLOW_REMINDER",
                    description=f"Workflow task needs attention before SLA due date: {task.task_name}",
                    occurred_at=now,
                    metadata={
                        "previous_sla_status": previous_sla_status,
                        "sla_status": sla_status,
                    },
                )
            changed = True
        if previous_escalation_status != escalation_status and escalation_status == "ESCALATED":
            payload = _append_task_event(
                payload,
                event_code="task_escalated",
                occurred_at=now,
                details={"previous_escalation_status": previous_escalation_status},
            )
            _queue_workflow_notification(
                db,
                task,
                event_type="SYMPLOYEE_WORKFLOW_ESCALATED",
                description=f"Workflow task escalated after SLA breach: {task.task_name}",
                occurred_at=now,
                metadata={"previous_escalation_status": previous_escalation_status},
            )
            changed = True
        task.task_payload_json = payload

    if changed:
        db.commit()
