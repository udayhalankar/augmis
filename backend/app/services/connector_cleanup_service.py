from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db_models import ConnectorSyncFailure, ConnectorSyncRun


def utc_now():
    return datetime.now(timezone.utc)


def cleanup_old_successful_sync_runs(
    db: Session,
    tenant_id,
    keep_days: int = 90,
):
    cutoff = utc_now() - timedelta(days=keep_days)

    old_runs = (
        db.query(ConnectorSyncRun)
        .filter(
            ConnectorSyncRun.tenant_id == tenant_id,
            ConnectorSyncRun.sync_status == "completed",
            ConnectorSyncRun.sync_started_at < cutoff,
        )
        .all()
    )

    count = len(old_runs)

    for run in old_runs:
        db.delete(run)

    db.commit()

    return count


def cleanup_resolved_failures(
    db: Session,
    tenant_id,
    keep_days: int = 30,
):
    cutoff = utc_now() - timedelta(days=keep_days)

    failures = (
        db.query(ConnectorSyncFailure)
        .filter(
            ConnectorSyncFailure.tenant_id == tenant_id,
            ConnectorSyncFailure.resolved == True,
            ConnectorSyncFailure.resolved_at < cutoff,
        )
        .all()
    )

    count = len(failures)

    for failure in failures:
        db.delete(failure)

    db.commit()

    return count
