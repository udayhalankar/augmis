from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.connector_sync_constants import ConnectorRetryStatus
from app.db_models import ConnectorFile, ConnectorSyncFailure


def utc_now():
    return datetime.now(timezone.utc)


def calculate_next_retry_at(retry_count: int):
    if retry_count <= 1:
        return utc_now() + timedelta(minutes=5)

    if retry_count == 2:
        return utc_now() + timedelta(minutes=15)

    return utc_now() + timedelta(minutes=60)


def can_retry_failure(failure: ConnectorSyncFailure):
    if failure.resolved:
        return False, ConnectorRetryStatus.WAITING

    if failure.retry_count >= failure.max_retries:
        return False, ConnectorRetryStatus.MAX_RETRIES_REACHED

    if failure.next_retry_at and failure.next_retry_at > utc_now():
        return False, ConnectorRetryStatus.WAITING

    return True, ConnectorRetryStatus.READY


def mark_failure_retry_attempted(
    db: Session,
    failure: ConnectorSyncFailure,
):
    failure.retry_count += 1
    failure.last_retry_at = utc_now()
    failure.next_retry_at = calculate_next_retry_at(failure.retry_count)

    if failure.connector_file_id:
        connector_file = (
            db.query(ConnectorFile)
            .filter(ConnectorFile.id == failure.connector_file_id)
            .first()
        )

        if connector_file:
            connector_file.retry_count = (connector_file.retry_count or 0) + 1
            connector_file.sync_status = "pending"

    db.commit()
    db.refresh(failure)

    return failure


def mark_failure_resolved(
    db: Session,
    failure: ConnectorSyncFailure,
):
    failure.resolved = True
    failure.resolved_at = utc_now()
    db.commit()
    db.refresh(failure)
    return failure


def get_ready_failures(
    db: Session,
    tenant_id=None,
    repository_id=None,
    limit: int = 50,
):
    query = db.query(ConnectorSyncFailure).filter(
        ConnectorSyncFailure.resolved == False,
        ConnectorSyncFailure.retry_count < ConnectorSyncFailure.max_retries,
    )

    if tenant_id:
        query = query.filter(ConnectorSyncFailure.tenant_id == tenant_id)

    if repository_id:
        query = query.filter(ConnectorSyncFailure.repository_id == repository_id)

    failures = query.order_by(ConnectorSyncFailure.created_at.asc()).limit(limit).all()

    ready = []

    for failure in failures:
        allowed, _ = can_retry_failure(failure)
        if allowed:
            ready.append(failure)

    return ready
