from __future__ import annotations

from collections import defaultdict
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db_models import SymployeePolicyConfig


def _new_id(prefix: str) -> str:
    return f"{prefix}-{str(uuid4())[:12].upper()}"


def _serialize_policy(row: SymployeePolicyConfig) -> dict:
    return {
        "policy_id": row.policy_id,
        "tenant_id": row.tenant_id,
        "symployee_code": row.symployee_code,
        "policy_domain": row.policy_domain,
        "policy_code": row.policy_code,
        "name": row.name,
        "version_no": row.version_no,
        "status": row.status,
        "is_default": row.is_default,
        "scope_type": row.scope_type or "tenant",
        "scope_ref": row.scope_ref,
        "config": row.config_json or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "modified_at": row.modified_at.isoformat() if row.modified_at else None,
    }


def _normalize_scope(scope_type: str | None, scope_ref: str | None) -> tuple[str, str | None]:
    normalized_type = (scope_type or "tenant").strip().lower()
    if normalized_type not in {"tenant", "business_area", "repository", "project"}:
        raise ValueError("Policy scope_type must be tenant, business_area, repository, or project")
    normalized_ref = (scope_ref or "").strip() or None
    if normalized_type == "tenant":
        return "tenant", None
    if not normalized_ref:
        raise ValueError("Policy scope_ref is required for non-tenant scoped policies")
    return normalized_type, normalized_ref


def _scope_filter(query, scope_type: str, scope_ref: str | None):
    query = query.filter(SymployeePolicyConfig.scope_type == scope_type)
    if scope_ref is None:
        return query.filter(SymployeePolicyConfig.scope_ref.is_(None))
    return query.filter(SymployeePolicyConfig.scope_ref == scope_ref)


def list_document_controller_policies(db: Session, tenant_id: str) -> dict:
    rows = (
        db.query(SymployeePolicyConfig)
        .filter(
            SymployeePolicyConfig.tenant_id == tenant_id,
            SymployeePolicyConfig.symployee_code == "document_controller",
        )
        .order_by(
            SymployeePolicyConfig.policy_domain.asc(),
            SymployeePolicyConfig.policy_code.asc(),
            SymployeePolicyConfig.version_no.desc(),
        )
        .all()
    )

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row.policy_domain].append(_serialize_policy(row))

    return {
        "domains": grouped,
        "total_policies": len(rows),
    }


def create_document_controller_policy(
    db: Session,
    tenant_id: str,
    name: str,
    policy_domain: str,
    policy_code: str,
    config_json: dict,
    created_by: str | None,
    scope_type: str = "tenant",
    scope_ref: str | None = None,
    is_default: bool = False,
    status: str = "DRAFT",
) -> dict:
    normalized_scope_type, normalized_scope_ref = _normalize_scope(scope_type, scope_ref)
    latest = (
        db.query(SymployeePolicyConfig)
        .filter(
            SymployeePolicyConfig.tenant_id == tenant_id,
            SymployeePolicyConfig.symployee_code == "document_controller",
            SymployeePolicyConfig.policy_domain == policy_domain,
            SymployeePolicyConfig.policy_code == policy_code,
            SymployeePolicyConfig.scope_type == normalized_scope_type,
        )
    )
    latest = _scope_filter(latest, normalized_scope_type, normalized_scope_ref).order_by(
        SymployeePolicyConfig.version_no.desc()
    ).first()
    version_no = (latest.version_no + 1) if latest else 1

    if is_default:
        default_query = db.query(SymployeePolicyConfig).filter(
            SymployeePolicyConfig.tenant_id == tenant_id,
            SymployeePolicyConfig.symployee_code == "document_controller",
            SymployeePolicyConfig.policy_domain == policy_domain,
            SymployeePolicyConfig.scope_type == normalized_scope_type,
        )
        default_query = _scope_filter(default_query, normalized_scope_type, normalized_scope_ref)
        default_query.update({"is_default": False}, synchronize_session=False)

    row = SymployeePolicyConfig(
        policy_id=_new_id("SPC"),
        tenant_id=tenant_id,
        symployee_code="document_controller",
        policy_domain=policy_domain,
        policy_code=policy_code,
        name=name,
        version_no=version_no,
        status=status.upper(),
        is_default=is_default,
        scope_type=normalized_scope_type,
        scope_ref=normalized_scope_ref,
        config_json=config_json or {},
        created_by=created_by,
        modified_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_policy(row)


def get_document_controller_policy(
    db: Session,
    tenant_id: str,
    policy_domain: str,
    policy_code: str,
) -> dict:
    rows = (
        db.query(SymployeePolicyConfig)
        .filter(
            SymployeePolicyConfig.tenant_id == tenant_id,
            SymployeePolicyConfig.symployee_code == "document_controller",
            SymployeePolicyConfig.policy_domain == policy_domain,
            SymployeePolicyConfig.policy_code == policy_code,
        )
        .order_by(SymployeePolicyConfig.version_no.desc())
        .all()
    )
    if not rows:
        raise ValueError("Policy not found")
    return {
        "policy_domain": policy_domain,
        "policy_code": policy_code,
        "versions": [_serialize_policy(row) for row in rows],
    }


def update_document_controller_policy(
    db: Session,
    tenant_id: str,
    policy_domain: str,
    policy_code: str,
    modified_by: str | None,
    *,
    name: str | None = None,
    scope_type: str | None = None,
    scope_ref: str | None = None,
    config_json: dict | None = None,
    is_default: bool | None = None,
    status: str | None = None,
) -> dict:
    current_query = db.query(SymployeePolicyConfig).filter(
        SymployeePolicyConfig.tenant_id == tenant_id,
        SymployeePolicyConfig.symployee_code == "document_controller",
        SymployeePolicyConfig.policy_domain == policy_domain,
        SymployeePolicyConfig.policy_code == policy_code,
    )
    if scope_type is not None:
        normalized_scope_type, normalized_scope_ref = _normalize_scope(scope_type, scope_ref)
        current_query = _scope_filter(current_query, normalized_scope_type, normalized_scope_ref)
    current = current_query.order_by(SymployeePolicyConfig.version_no.desc()).first()
    if not current:
        raise ValueError("Policy not found")

    return create_document_controller_policy(
        db=db,
        tenant_id=tenant_id,
        name=name or current.name,
        policy_domain=policy_domain,
        policy_code=policy_code,
        config_json=config_json if config_json is not None else (current.config_json or {}),
        created_by=modified_by,
        scope_type=(normalized_scope_type if scope_type is not None else (current.scope_type or "tenant")),
        scope_ref=(normalized_scope_ref if scope_type is not None else current.scope_ref),
        is_default=current.is_default if is_default is None else is_default,
        status=current.status if status is None else status,
    )


def resolve_policy(
    db: Session,
    tenant_id: str,
    policy_domain: str,
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
) -> dict | None:
    candidates = [
        ("repository", repository_id),
        ("business_area", business_area),
        ("project", project_code),
        ("tenant", None),
    ]
    for scope_type, scope_ref in candidates:
        if scope_type != "tenant" and not scope_ref:
            continue
        query = db.query(SymployeePolicyConfig).filter(
            SymployeePolicyConfig.tenant_id == tenant_id,
            SymployeePolicyConfig.symployee_code == "document_controller",
            SymployeePolicyConfig.policy_domain == policy_domain,
            SymployeePolicyConfig.status == "ACTIVE",
            SymployeePolicyConfig.scope_type == scope_type,
        )
        query = _scope_filter(query, scope_type, scope_ref)
        row = query.order_by(
            SymployeePolicyConfig.is_default.desc(),
            SymployeePolicyConfig.version_no.desc(),
        ).first()
        if row:
            serialized = _serialize_policy(row)
            serialized["resolved_scope_type"] = scope_type
            serialized["resolved_scope_ref"] = scope_ref
            return serialized
    return None


def resolve_required_policies(
    db: Session,
    tenant_id: str,
    policy_domains: list[str],
    *,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
) -> dict[str, dict]:
    resolved: dict[str, dict] = {}
    missing: list[str] = []

    for domain in policy_domains:
        row = resolve_policy(
            db=db,
            tenant_id=tenant_id,
            policy_domain=domain,
            repository_id=repository_id,
            business_area=business_area,
            project_code=project_code,
        )
        if not row:
            missing.append(domain)
            continue
        resolved[domain] = row

    if missing:
        missing_list = ", ".join(missing)
        raise ValueError(
            f"No active Symployee policy configured for required domain(s): {missing_list}"
        )

    return resolved


def bootstrap_document_controller_default_policies(
    db: Session,
    tenant_id: str,
    created_by: str | None,
) -> dict:
    defaults = [
        {
            "policy_domain": "classification",
            "policy_code": "default_document_classification",
            "name": "Default Document Classification",
            "status": "ACTIVE",
            "is_default": True,
            "config_json": {
                "document_types": [
                    "drawing",
                    "calculation",
                    "procedure",
                    "method_statement",
                    "inspection_report",
                    "specification",
                    "contract",
                    "letter",
                    "invoice",
                    "minutes",
                    "permit",
                    "risk_assessment",
                    "moc",
                    "hse_report",
                    "engineering_query",
                    "technical_bid",
                    "commercial_bid",
                    "vendor_data_book",
                ],
                "required_outputs": [
                    "document_type_code",
                    "title",
                    "discipline_code",
                    "project_code",
                    "originator_code",
                    "confidence_score",
                ],
                "confidence_thresholds": {
                    "auto_recommend_min_confidence": 0.85,
                    "manual_review_min_confidence": 0.6,
                    "hard_fail_below_confidence": 0.6,
                },
            },
        },
        {
            "policy_domain": "metadata_schema",
            "policy_code": "default_document_metadata_schema",
            "name": "Default Document Metadata Schema",
            "status": "ACTIVE",
            "is_default": True,
            "config_json": {
                "required_fields": [
                    "document_number",
                    "document_type_code",
                    "discipline_code",
                    "project_code",
                    "originator_code",
                    "revision_code",
                    "document_status",
                    "document_date",
                ],
                "optional_fields": [
                    "vendor_code",
                    "package",
                    "work_breakdown_structure",
                    "priority",
                    "confidentiality",
                ],
                "field_rules": {
                    "document_number": {
                        "type": "text",
                        "required": True,
                    },
                    "revision_code": {
                        "type": "text",
                        "required": True,
                    },
                    "document_date": {
                        "type": "date",
                        "required": False,
                    },
                },
            },
        },
        {
            "policy_domain": "reviewer_assignment",
            "policy_code": "default_document_reviewer_assignment",
            "name": "Default Document Reviewer Assignment",
            "status": "ACTIVE",
            "is_default": True,
            "config_json": {
                "default_assignment": {
                    "role_code": "tenant_admin",
                    "strategy": "least_loaded_in_role",
                },
                "task_assignments": {
                    "classification_review": {
                        "role_code": "tenant_admin",
                        "strategy": "least_loaded_in_role",
                    },
                    "metadata_review": {
                        "role_code": "tenant_admin",
                        "strategy": "least_loaded_in_role",
                    },
                },
                "routing_rules": [
                    {
                        "task_code": "classification_review",
                        "match": {
                            "all": [
                                {
                                    "document_type_code": "contract",
                                },
                                {
                                    "any": [
                                        {"business_area": "contracts"},
                                        {"confidentiality": "high"},
                                        {"priority": "critical"},
                                    ]
                                },
                            ]
                        },
                        "assignee": {
                            "role_code": "tenant_admin",
                            "strategy": "least_loaded_in_role",
                        },
                    },
                    {
                        "task_code": "metadata_review",
                        "match": {
                            "all": [
                                {
                                    "document_type_code": "contract",
                                },
                                {
                                    "any": [
                                        {"discipline_code": "legal"},
                                        {"project_code": "AKML"},
                                        {"confidentiality": "high"},
                                    ]
                                },
                            ]
                        },
                        "assignee": {
                            "role_code": "tenant_admin",
                            "strategy": "least_loaded_in_role",
                        },
                    },
                ],
            },
        },
        {
            "policy_domain": "sla_rules",
            "policy_code": "default_document_sla_rules",
            "name": "Default Document SLA Rules",
            "status": "ACTIVE",
            "is_default": True,
            "config_json": {
                "default_rule": {
                    "target_hours": 48,
                    "warning_before_hours": 12,
                    "escalate_after_hours": 24,
                },
                "task_rules": {
                    "classification_review": {
                        "target_hours": 24,
                        "warning_before_hours": 6,
                        "escalate_after_hours": 12,
                    },
                    "metadata_review": {
                        "target_hours": 48,
                        "warning_before_hours": 12,
                        "escalate_after_hours": 24,
                    },
                },
            },
        },
    ]

    created_or_existing: list[dict] = []
    for default in defaults:
        existing_active = (
            db.query(SymployeePolicyConfig)
            .filter(
                SymployeePolicyConfig.tenant_id == tenant_id,
                SymployeePolicyConfig.symployee_code == "document_controller",
                SymployeePolicyConfig.policy_domain == default["policy_domain"],
                SymployeePolicyConfig.policy_code == default["policy_code"],
                SymployeePolicyConfig.status == "ACTIVE",
                SymployeePolicyConfig.scope_type == "tenant",
                SymployeePolicyConfig.scope_ref.is_(None),
            )
            .order_by(SymployeePolicyConfig.version_no.desc())
            .first()
        )
        if existing_active:
            created_or_existing.append(_serialize_policy(existing_active))
            continue

        created_or_existing.append(
            create_document_controller_policy(
                db=db,
                tenant_id=tenant_id,
                name=default["name"],
                policy_domain=default["policy_domain"],
                policy_code=default["policy_code"],
                config_json=default["config_json"],
                created_by=created_by,
                scope_type="tenant",
                scope_ref=None,
                is_default=default["is_default"],
                status=default["status"],
            )
        )

    return {
        "items": created_or_existing,
        "count": len(created_or_existing),
    }
