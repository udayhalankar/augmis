from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db_models import ConnectorFile
from app.core.connector_sync_constants import ConnectorFileStatus


def utc_now():
    return datetime.now(timezone.utc)


class IncrementalDecision:
    NEW = "new"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    DUPLICATE = "duplicate"
    DELETED = "deleted"


def get_current_connector_file(
    db: Session,
    tenant_id,
    repository_id,
    external_file_id: str,
):
    return (
        db.query(ConnectorFile)
        .filter(
            ConnectorFile.tenant_id == tenant_id,
            ConnectorFile.repository_id == repository_id,
            ConnectorFile.external_file_id == external_file_id,
            ConnectorFile.is_current_version == True,
            ConnectorFile.is_deleted == False,
        )
        .first()
    )


def find_duplicate_by_hash(
    db: Session,
    tenant_id,
    repository_id,
    file_hash: str | None,
):
    if not file_hash:
        return None

    return (
        db.query(ConnectorFile)
        .filter(
            ConnectorFile.tenant_id == tenant_id,
            ConnectorFile.repository_id == repository_id,
            ConnectorFile.file_hash == file_hash,
            ConnectorFile.is_deleted == False,
        )
        .first()
    )


def decide_incremental_action(
    db: Session,
    tenant_id,
    repository_id,
    source_file: dict,
):
    """
    source_file required keys:
    - external_file_id
    - file_hash
    - modified_at
    """

    external_file_id = source_file.get("external_file_id")
    file_hash = source_file.get("file_hash")
    source_modified_at = source_file.get("modified_at")

    existing = get_current_connector_file(
        db=db,
        tenant_id=tenant_id,
        repository_id=repository_id,
        external_file_id=external_file_id,
    )

    if not existing:
        duplicate = find_duplicate_by_hash(
            db=db,
            tenant_id=tenant_id,
            repository_id=repository_id,
            file_hash=file_hash,
        )

        if duplicate:
            return {
                "decision": IncrementalDecision.DUPLICATE,
                "existing": duplicate,
                "reason": "Same file hash already indexed",
            }

        return {
            "decision": IncrementalDecision.NEW,
            "existing": None,
            "reason": "File not found in connector registry",
        }

    if existing.file_hash and file_hash and existing.file_hash == file_hash:
        return {
            "decision": IncrementalDecision.UNCHANGED,
            "existing": existing,
            "reason": "File hash unchanged",
        }

    if source_modified_at and existing.source_modified_at:
        if source_modified_at <= existing.source_modified_at:
            return {
                "decision": IncrementalDecision.UNCHANGED,
                "existing": existing,
                "reason": "Source modified date not newer",
            }

    return {
        "decision": IncrementalDecision.UPDATED,
        "existing": existing,
        "reason": "File changed",
    }


def mark_file_unchanged(
    db: Session,
    connector_file: ConnectorFile,
    sync_run_id=None,
):
    connector_file.sync_status = ConnectorFileStatus.UNCHANGED
    connector_file.last_synced_at = utc_now()
    connector_file.last_sync_run_id = sync_run_id

    db.commit()
    db.refresh(connector_file)

    return connector_file


def mark_file_duplicate_skipped(
    db: Session,
    tenant_id,
    repository_id,
    source_type: str,
    source_file: dict,
    duplicate_file: ConnectorFile,
    sync_run_id=None,
):
    skipped = ConnectorFile(
        tenant_id=tenant_id,
        repository_id=repository_id,
        source_type=source_type,
        external_file_id=source_file.get("external_file_id"),
        file_name=source_file.get("file_name"),
        file_path=source_file.get("file_path"),
        file_hash=source_file.get("file_hash"),
        file_size=source_file.get("file_size"),
        source_created_at=source_file.get("created_at"),
        source_modified_at=source_file.get("modified_at"),
        last_synced_at=utc_now(),
        last_sync_run_id=sync_run_id,
        sync_status=ConnectorFileStatus.SKIPPED_DUPLICATE,
        document_id=duplicate_file.document_id,
        version_number=1,
        is_current_version=True,
        metadata_json={
            "duplicate_of_connector_file_id": str(duplicate_file.id),
            "duplicate_reason": "same_sha256_hash",
        },
    )

    db.add(skipped)
    db.commit()
    db.refresh(skipped)

    return skipped


def create_new_connector_file(
    db: Session,
    tenant_id,
    repository_id,
    source_type: str,
    source_file: dict,
    sync_run_id=None,
):
    connector_file = ConnectorFile(
        tenant_id=tenant_id,
        repository_id=repository_id,
        source_type=source_type,
        external_file_id=source_file.get("external_file_id"),
        file_name=source_file.get("file_name"),
        file_path=source_file.get("file_path"),
        file_hash=source_file.get("file_hash"),
        file_size=source_file.get("file_size"),
        source_created_at=source_file.get("created_at"),
        source_modified_at=source_file.get("modified_at"),
        last_synced_at=utc_now(),
        last_sync_run_id=sync_run_id,
        sync_status=ConnectorFileStatus.NEW,
        version_number=1,
        is_current_version=True,
        metadata_json=source_file.get("metadata") or {},
    )

    db.add(connector_file)
    db.commit()
    db.refresh(connector_file)

    return connector_file


def create_updated_file_version(
    db: Session,
    existing_file: ConnectorFile,
    source_file: dict,
    sync_run_id=None,
):
    existing_file.is_current_version = False
    existing_file.sync_status = ConnectorFileStatus.UPDATED

    new_version = ConnectorFile(
        tenant_id=existing_file.tenant_id,
        repository_id=existing_file.repository_id,
        source_type=existing_file.source_type,
        external_file_id=existing_file.external_file_id,
        file_name=source_file.get("file_name"),
        file_path=source_file.get("file_path"),
        file_hash=source_file.get("file_hash"),
        file_size=source_file.get("file_size"),
        source_created_at=source_file.get("created_at"),
        source_modified_at=source_file.get("modified_at"),
        last_synced_at=utc_now(),
        last_sync_run_id=sync_run_id,
        sync_status=ConnectorFileStatus.UPDATED,
        version_number=(existing_file.version_number or 1) + 1,
        is_current_version=True,
        document_id=None,
        metadata_json={
            **(source_file.get("metadata") or {}),
            "previous_connector_file_id": str(existing_file.id),
            "previous_document_id": (
                str(existing_file.document_id) if existing_file.document_id else None
            ),
        },
    )

    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    return new_version


def mark_missing_files_deleted(
    db: Session,
    tenant_id,
    repository_id,
    source_external_file_ids: set[str],
    sync_run_id=None,
):
    existing_files = (
        db.query(ConnectorFile)
        .filter(
            ConnectorFile.tenant_id == tenant_id,
            ConnectorFile.repository_id == repository_id,
            ConnectorFile.is_current_version == True,
            ConnectorFile.is_deleted == False,
        )
        .all()
    )

    deleted = []

    for file in existing_files:
        if file.external_file_id not in source_external_file_ids:
            file.is_deleted = True
            file.deleted_at = utc_now()
            file.sync_status = ConnectorFileStatus.DELETED
            file.last_sync_run_id = sync_run_id
            deleted.append(file)

    db.commit()

    return deleted
