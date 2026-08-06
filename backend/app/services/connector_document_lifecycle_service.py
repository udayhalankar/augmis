from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.connector_sync_constants import ConnectorFileStatus
from app.db_models import ConnectorFile, Document, DocumentChunk


def utc_now():
    return datetime.now(timezone.utc)


def retire_old_document_version(
    db: Session,
    tenant_id,
    old_document_id,
):
    if not old_document_id:
        return None

    old_doc = (
        db.query(Document)
        .filter(
            Document.document_id == old_document_id,
            Document.tenant_id == tenant_id,
        )
        .first()
    )

    if not old_doc:
        return None

    old_doc.is_current_version = False

    old_chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == old_doc.document_id,
            DocumentChunk.tenant_id == tenant_id,
        )
        .all()
    )

    for chunk in old_chunks:
        chunk.is_deleted = True
        chunk.deleted_at = utc_now()

    db.commit()
    return old_doc


def soft_delete_connector_document(
    db: Session,
    tenant_id,
    connector_file: ConnectorFile,
):
    connector_file.is_deleted = True
    connector_file.deleted_at = utc_now()
    connector_file.sync_status = ConnectorFileStatus.DELETED
    connector_file.is_current_version = False

    if connector_file.document_id:
        document = (
            db.query(Document)
            .filter(
                Document.document_id == connector_file.document_id,
                Document.tenant_id == tenant_id,
            )
            .first()
        )

        if document:
            document.is_deleted = True
            document.deleted_at = utc_now()
            document.is_current_version = False

            chunks = (
                db.query(DocumentChunk)
                .filter(
                    DocumentChunk.document_id == document.document_id,
                    DocumentChunk.tenant_id == tenant_id,
                )
                .all()
            )

            for chunk in chunks:
                chunk.is_deleted = True
                chunk.deleted_at = utc_now()

    db.commit()
    return connector_file


def soft_delete_missing_files(
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

    deleted_files = []

    for file in existing_files:
        if file.external_file_id not in source_external_file_ids:
            file.last_sync_run_id = sync_run_id
            soft_delete_connector_document(
                db=db,
                tenant_id=tenant_id,
                connector_file=file,
            )
            deleted_files.append(file)

    return deleted_files
