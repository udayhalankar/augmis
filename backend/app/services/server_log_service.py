from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Any
from uuid import uuid4
import csv

from sqlalchemy import Text, cast, or_
from sqlalchemy.exc import ProgrammingError

from app.core.database import SessionLocal
from app.core.request_context import clear_request_context, get_request_context, set_request_context
from app.db_models import ServerLog


SERVER_LOG_RETENTION_DAYS = 30
_LAST_PURGE_AT: datetime | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _is_missing_table(error: Exception) -> bool:
    return 'relation "server_logs" does not exist' in str(error)


def _serialize_log(row: ServerLog) -> dict[str, Any]:
    return {
        "log_id": row.log_id,
        "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
        "source": row.source,
        "level": row.level,
        "logger": row.logger,
        "category": row.category,
        "message": row.message,
        "exception": row.exception,
        "stack": row.stack,
        "route": row.route,
        "method": row.method,
        "status_code": row.status_code,
        "request_id": row.request_id,
        "tenant_id": row.tenant_id,
        "user_id": row.user_id,
        "user_email": row.user_email,
        "repository_id": row.repository_id,
        "business_area": row.business_area,
        "component": row.component,
        "is_critical": row.is_critical,
        "metadata": row.metadata_json or {},
    }


def purge_expired_server_logs(retention_days: int = SERVER_LOG_RETENTION_DAYS) -> None:
    global _LAST_PURGE_AT
    cutoff = _utc_now() - timedelta(days=max(1, retention_days))
    db = SessionLocal()
    try:
        db.query(ServerLog).filter(ServerLog.occurred_at < cutoff).delete()
        db.commit()
        _LAST_PURGE_AT = _utc_now()
    except ProgrammingError as exc:
        db.rollback()
        if _is_missing_table(exc):
            return
        raise
    finally:
        db.close()


def _maybe_purge_expired_server_logs() -> None:
    global _LAST_PURGE_AT
    now = _utc_now()
    if _LAST_PURGE_AT and (now - _LAST_PURGE_AT).total_seconds() < 1800:
        return
    purge_expired_server_logs()


def create_server_log(
    *,
    source: str,
    level: str,
    message: str,
    logger: str | None = None,
    category: str | None = None,
    exception: str | None = None,
    stack: str | None = None,
    route: str | None = None,
    method: str | None = None,
    status_code: int | None = None,
    request_id: str | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
    user_email: str | None = None,
    repository_id: str | None = None,
    business_area: str | None = None,
    component: str | None = None,
    is_critical: bool = False,
    metadata: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> dict[str, Any] | None:
    _maybe_purge_expired_server_logs()
    db = SessionLocal()
    try:
        entry = ServerLog(
            log_id=f"LOG-{str(uuid4())[:12].upper()}",
            occurred_at=occurred_at or _utc_now(),
            source=str(source or "backend").strip().lower(),
            level=str(level or "INFO").strip().upper(),
            logger=logger,
            category=category,
            message=message[:12000],
            exception=exception[:24000] if exception else None,
            stack=stack[:24000] if stack else None,
            route=route,
            method=method,
            status_code=status_code,
            request_id=request_id,
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            repository_id=repository_id,
            business_area=business_area,
            component=component,
            is_critical=bool(is_critical),
            metadata_json=metadata or {},
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return _serialize_log(entry)
    except ProgrammingError as exc:
        db.rollback()
        if _is_missing_table(exc):
            return None
        raise
    finally:
        db.close()


def list_server_logs(
    *,
    source: str | None = None,
    level: str | None = None,
    q: str | None = None,
    route: str | None = None,
    user: str | None = None,
    repository_id: str | None = None,
    business_area: str | None = None,
    request_id: str | None = None,
    category: str | None = None,
    critical_only: bool = False,
    start_at: str | None = None,
    end_at: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    db = SessionLocal()
    try:
        query = db.query(ServerLog)

        if source:
            query = query.filter(ServerLog.source == source.strip().lower())
        if level:
            query = query.filter(ServerLog.level == level.strip().upper())
        if route:
            query = query.filter(ServerLog.route.ilike(f"%{route.strip()}%"))
        if user:
            value = user.strip()
            query = query.filter(
                or_(
                    ServerLog.user_email.ilike(f"%{value}%"),
                    ServerLog.user_id.ilike(f"%{value}%"),
                )
            )
        if repository_id:
            query = query.filter(ServerLog.repository_id == repository_id.strip())
        if business_area:
            query = query.filter(ServerLog.business_area.ilike(f"%{business_area.strip()}%"))
        if request_id:
            query = query.filter(ServerLog.request_id == request_id.strip())
        if category:
            query = query.filter(ServerLog.category == category.strip())
        if critical_only:
            query = query.filter(ServerLog.is_critical.is_(True))

        started = _normalize_datetime(start_at)
        ended = _normalize_datetime(end_at)
        if started:
            query = query.filter(ServerLog.occurred_at >= started)
        if ended:
            query = query.filter(ServerLog.occurred_at <= ended)

        if q:
            text = q.strip()
            query = query.filter(
                or_(
                    ServerLog.message.ilike(f"%{text}%"),
                    ServerLog.exception.ilike(f"%{text}%"),
                    ServerLog.stack.ilike(f"%{text}%"),
                    ServerLog.logger.ilike(f"%{text}%"),
                    cast(ServerLog.metadata_json, Text).ilike(f"%{text}%"),
                )
            )

        rows = query.order_by(ServerLog.occurred_at.desc()).limit(max(1, min(limit, 1000))).all()
        return [_serialize_log(row) for row in rows]
    except ProgrammingError as exc:
        db.rollback()
        if _is_missing_table(exc):
            return []
        raise
    finally:
        db.close()


def export_server_logs_csv(logs: list[dict[str, Any]]) -> str:
    if not logs:
        return ""

    output = StringIO()
    fieldnames = [
        "log_id",
        "occurred_at",
        "source",
        "level",
        "logger",
        "category",
        "message",
        "route",
        "method",
        "status_code",
        "request_id",
        "user_email",
        "repository_id",
        "business_area",
        "component",
        "is_critical",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in logs:
        writer.writerow({key: row.get(key) for key in fieldnames})
    return output.getvalue()


def mark_server_log_critical(log_id: str, is_critical: bool) -> dict[str, Any] | None:
    db = SessionLocal()
    try:
        entry = db.query(ServerLog).filter(ServerLog.log_id == log_id).first()
        if not entry:
            return None
        entry.is_critical = bool(is_critical)
        db.commit()
        db.refresh(entry)
        return _serialize_log(entry)
    finally:
        db.close()


def append_frontend_log(entry: dict[str, Any]) -> dict[str, Any] | None:
    return create_server_log(
        source="frontend",
        level=str(entry.get("level") or "ERROR").upper(),
        logger="frontend",
        message=str(entry.get("message") or "Frontend error"),
        category=entry.get("category") or "client_error",
        stack=entry.get("stack"),
        route=entry.get("route"),
        method=entry.get("method"),
        status_code=entry.get("status_code"),
        request_id=entry.get("request_id"),
        tenant_id=entry.get("tenant_id"),
        user_id=entry.get("user_id"),
        user_email=entry.get("user_email"),
        repository_id=entry.get("repository_id"),
        business_area=entry.get("business_area"),
        component=entry.get("component"),
        is_critical=bool(entry.get("is_critical")),
        metadata={
            "user_agent": entry.get("user_agent"),
            **(entry.get("metadata") or {}),
        },
    )


def get_log_context_from_request_context() -> dict[str, Any]:
    return get_request_context()


@contextmanager
def background_log_context(**values: Any):
    token = set_request_context(**values)
    try:
        yield
    finally:
        clear_request_context(token)
