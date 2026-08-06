from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db_models import (
    ConnectorSyncRun,
    ConnectorFile,
    ConnectorSyncFailure,
)
from app.core.connector_sync_constants import (
    ConnectorSyncStatus,
    ConnectorFileStatus,
)


def utc_now():
    return datetime.now(timezone.utc)


def start_sync_run(
    db: Session,
    tenant_id,
    repository_id,
    source_type: str,
    started_by=None,
    sync_mode: str = "manual",
) -> ConnectorSyncRun:
    sync_run = ConnectorSyncRun(
        tenant_id=tenant_id,
        repository_id=repository_id,
        source_type=source_type,
        sync_status=ConnectorSyncStatus.RUNNING,
        sync_mode=sync_mode,
        started_by=started_by,
    )

    db.add(sync_run)
    db.commit()
    db.refresh(sync_run)

    return sync_run


def complete_sync_run(
    db: Session,
    sync_run: ConnectorSyncRun,
    status: str = ConnectorSyncStatus.COMPLETED,
    error_message: str | None = None,
):
    sync_run.sync_status = status
    sync_run.sync_completed_at = utc_now()
    sync_run.error_message = error_message

    db.commit()
    db.refresh(sync_run)

    return sync_run


def register_connector_file(
    db: Session,
    tenant_id,
    repository_id,
    source_type: str,
    external_file_id: str,
    file_name: str,
    file_path: str | None = None,
    file_hash: str | None = None,
    file_size: int | None = None,
    source_created_at=None,
    source_modified_at=None,
    sync_run_id=None,
    metadata: dict | None = None,
) -> ConnectorFile:
    existing = (
        db.query(ConnectorFile)
        .filter(
            ConnectorFile.tenant_id == tenant_id,
            ConnectorFile.repository_id == repository_id,
            ConnectorFile.external_file_id == external_file_id,
            ConnectorFile.is_current_version == True,
        )
        .first()
    )

    if existing:
        existing.file_name = file_name
        existing.file_path = file_path
        existing.file_hash = file_hash
        existing.file_size = file_size
        existing.source_created_at = source_created_at
        existing.source_modified_at = source_modified_at
        existing.last_synced_at = utc_now()
        existing.last_sync_run_id = sync_run_id
        existing.sync_status = ConnectorFileStatus.UNCHANGED
        existing.metadata_json = metadata or {}

        db.commit()
        db.refresh(existing)
        return existing

    connector_file = ConnectorFile(
        tenant_id=tenant_id,
        repository_id=repository_id,
        source_type=source_type,
        external_file_id=external_file_id,
        file_name=file_name,
        file_path=file_path,
        file_hash=file_hash,
        file_size=file_size,
        source_created_at=source_created_at,
        source_modified_at=source_modified_at,
        last_synced_at=utc_now(),
        last_sync_run_id=sync_run_id,
        sync_status=ConnectorFileStatus.NEW,
        metadata_json=metadata or {},
    )

    db.add(connector_file)
    db.commit()
    db.refresh(connector_file)

    return connector_file


def mark_connector_file_failed(
    db: Session,
    connector_file: ConnectorFile | None,
    tenant_id,
    repository_id,
    failure_stage: str,
    error_message: str,
    sync_run_id=None,
    external_file_id: str | None = None,
    file_name: str | None = None,
    file_path: str | None = None,
):
    failure = ConnectorSyncFailure(
        tenant_id=tenant_id,
        repository_id=repository_id,
        sync_run_id=sync_run_id,
        connector_file_id=connector_file.id if connector_file else None,
        external_file_id=external_file_id,
        file_name=file_name,
        file_path=file_path,
        failure_stage=failure_stage,
        error_message=error_message,
    )

    db.add(failure)

    if connector_file:
        connector_file.sync_status = ConnectorFileStatus.FAILED
        connector_file.retry_count = (connector_file.retry_count or 0) + 1
        connector_file.last_error_message = error_message

    db.commit()
    db.refresh(failure)

    return failure