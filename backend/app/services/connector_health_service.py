from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc)


def build_connector_health(repository):
    status = repository.last_sync_status or "never_synced"

    healthy = status in ["completed", "never_synced", None]

    if status in ["failed", "completed_with_errors"]:
        healthy = False

    return {
        "repository_id": str(repository.repository_id),
        "repository_name": repository.repository_name,
        "source_type": repository.source_type,
        "healthy": healthy,
        "last_sync_status": repository.last_sync_status,
        "last_sync_started_at": repository.last_sync_started_at,
        "last_sync_completed_at": repository.last_sync_completed_at,
        "last_sync_error": repository.last_sync_error,
        "sync_enabled": repository.sync_enabled,
        "checked_at": utc_now(),
    }
