from uuid import uuid4

from fastapi import Request
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.request_context import get_request_context
from app.db_models import AuditLog


def _is_missing_audit_table(error: Exception) -> bool:
    return 'relation "audit_logs" does not exist' in str(error)


def create_audit_log(
    db: Session,
    tenant_id: str,
    event_type: str,
    event_category: str,
    description: str = "",
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    request: Request | None = None,
    metadata: dict | None = None,
):
    ip_address = None
    user_agent = None

    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
    request_context = get_request_context()

    audit = AuditLog(
        audit_id=f"AUD-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        user_id=user_id,
        event_type=event_type,
        event_category=event_category,
        description=description,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=(request.state.request_id if request and hasattr(request.state, "request_id") else None)
        or request_context.get("request_id"),
        metadata_json=metadata or {},
    )

    try:
        db.add(audit)
        db.commit()
        db.refresh(audit)
    except ProgrammingError as exc:
        db.rollback()
        if _is_missing_audit_table(exc):
            return None
        raise

    return audit


def serialize_audit_log(row: AuditLog):
    return {
        "audit_id": row.audit_id,
        "tenant_id": row.tenant_id,
        "user_id": row.user_id,
        "event_type": row.event_type,
        "event_category": row.event_category,
        "description": row.description,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "ip_address": row.ip_address,
        "user_agent": row.user_agent,
        "request_id": row.request_id,
        "metadata": row.metadata_json or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_audit_logs(
    db: Session,
    current_user: dict,
    event_category: str | None = None,
    event_type: str | None = None,
    request_id: str | None = None,
    limit: int = 100,
):
    try:
        query = db.query(AuditLog).filter(
            AuditLog.tenant_id == current_user["tenant_id"]
        )

        if event_category:
            query = query.filter(AuditLog.event_category == event_category)

        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if request_id:
            query = query.filter(AuditLog.request_id == request_id)

        rows = query.order_by(AuditLog.created_at.desc()).limit(limit).all()

        return {
            "success": True,
            "data": [serialize_audit_log(row) for row in rows],
        }
    except ProgrammingError as exc:
        db.rollback()
        if _is_missing_audit_table(exc):
            return {
                "success": True,
                "data": [],
                "message": "Audit table not initialized yet. Run init_db.py to enable audit history.",
            }
        raise
