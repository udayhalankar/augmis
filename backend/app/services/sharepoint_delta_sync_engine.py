from sqlalchemy.orm import Session

from app.core.connector_exceptions import (
    ConnectorChunkingError,
    ConnectorDownloadError,
    ConnectorEmbeddingError,
    ConnectorIngestionError,
    ConnectorParseError,
)
from app.core.connector_sync_constants import (
    ConnectorFailureStage,
    ConnectorFileStatus,
    ConnectorSyncStatus,
)
from app.db_models import ConnectorFile
from app.services.connector_document_lifecycle_service import (
    soft_delete_connector_document,
)
from app.services.connector_incremental_service import (
    IncrementalDecision,
    create_new_connector_file,
    create_updated_file_version,
    decide_incremental_action,
    mark_file_duplicate_skipped,
    mark_file_unchanged,
)
from app.services.connector_ingestion_pipeline import ingest_connector_file_to_pgvector
from app.services.connector_sync_db_service import (
    complete_sync_run,
    mark_connector_file_failed,
    start_sync_run,
)
from app.services.connector_validation_service import (
    validate_repository_connector_config,
    validate_source_file_contract,
)


def _get_existing_connector_file(
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


def _soft_delete_delta_item(
    db: Session,
    tenant_id,
    repository_id,
    source_file: dict,
    sync_run_id=None,
):
    existing = _get_existing_connector_file(
        db=db,
        tenant_id=tenant_id,
        repository_id=repository_id,
        external_file_id=source_file.get("external_file_id"),
    )

    if not existing:
        return None

    existing.last_sync_run_id = sync_run_id
    existing.sync_status = ConnectorFileStatus.DELETED

    return soft_delete_connector_document(
        db=db,
        tenant_id=tenant_id,
        connector_file=existing,
    )


def run_sharepoint_delta_sync(
    db: Session,
    tenant_id,
    repository,
    connector,
    started_by=None,
    sync_mode: str = "manual",
):
    repository_id = repository.repository_id

    sync_run = start_sync_run(
        db=db,
        tenant_id=tenant_id,
        repository_id=repository_id,
        source_type=repository.source_type,
        started_by=started_by,
        sync_mode=sync_mode,
    )

    repository.last_sync_run_id = sync_run.id
    repository.sync_status = ConnectorSyncStatus.RUNNING
    repository.last_sync_status = ConnectorSyncStatus.RUNNING
    repository.last_sync_started_at = sync_run.sync_started_at
    repository.last_sync_error = None
    db.commit()

    try:
        validate_repository_connector_config(repository)

        previous_delta_link = None
        if repository.sync_metadata:
            previous_delta_link = repository.sync_metadata.get("sharepoint_delta_link")

        delta_result = connector.list_files_delta(delta_link=previous_delta_link)
        changed_files = delta_result["files"]
        new_delta_link = delta_result.get("delta_link")

        sync_run.files_discovered = len(changed_files)
        db.commit()

        for source_file in changed_files:
            connector_file = None

            try:
                validate_source_file_contract(source_file)

                if source_file.get("is_deleted"):
                    deleted = _soft_delete_delta_item(
                        db=db,
                        tenant_id=tenant_id,
                        repository_id=repository_id,
                        source_file=source_file,
                        sync_run_id=sync_run.id,
                    )

                    if deleted:
                        sync_run.files_deleted += 1
                    else:
                        sync_run.files_skipped += 1

                    db.commit()
                    continue

                decision = decide_incremental_action(
                    db=db,
                    tenant_id=tenant_id,
                    repository_id=repository_id,
                    source_file=source_file,
                )

                if decision["decision"] == IncrementalDecision.UNCHANGED:
                    mark_file_unchanged(
                        db=db,
                        connector_file=decision["existing"],
                        sync_run_id=sync_run.id,
                    )
                    sync_run.files_skipped += 1
                    db.commit()
                    continue

                if decision["decision"] == IncrementalDecision.DUPLICATE:
                    mark_file_duplicate_skipped(
                        db=db,
                        tenant_id=tenant_id,
                        repository_id=repository_id,
                        source_type=repository.source_type,
                        source_file=source_file,
                        duplicate_file=decision["existing"],
                        sync_run_id=sync_run.id,
                    )
                    sync_run.files_skipped += 1
                    db.commit()
                    continue

                if decision["decision"] == IncrementalDecision.NEW:
                    connector_file = create_new_connector_file(
                        db=db,
                        tenant_id=tenant_id,
                        repository_id=repository_id,
                        source_type=repository.source_type,
                        source_file=source_file,
                        sync_run_id=sync_run.id,
                    )
                elif decision["decision"] == IncrementalDecision.UPDATED:
                    connector_file = create_updated_file_version(
                        db=db,
                        existing_file=decision["existing"],
                        source_file=source_file,
                        sync_run_id=sync_run.id,
                    )

                try:
                    file_content = connector.get_file_content(source_file)
                except Exception as exc:
                    raise ConnectorDownloadError(str(exc)) from exc

                try:
                    result = ingest_connector_file_to_pgvector(
                        db=db,
                        tenant_id=tenant_id,
                        repository=repository,
                        connector_file=connector_file,
                        source_file=source_file,
                        file_content=file_content,
                        uploaded_by=started_by,
                    )
                except Exception as exc:
                    raise ConnectorIngestionError(str(exc)) from exc

                sync_run.files_processed += 1
                sync_run.chunks_created += result["chunks_created"]
                sync_run.embeddings_created += result["embeddings_created"]
                db.commit()

            except ConnectorDownloadError as file_error:
                sync_run.files_failed += 1
                mark_connector_file_failed(
                    db=db,
                    connector_file=connector_file,
                    tenant_id=tenant_id,
                    repository_id=repository_id,
                    sync_run_id=sync_run.id,
                    failure_stage=ConnectorFailureStage.DOWNLOAD,
                    error_message=str(file_error),
                    external_file_id=source_file.get("external_file_id"),
                    file_name=source_file.get("file_name"),
                    file_path=source_file.get("file_path"),
                )
                db.commit()

            except ConnectorIngestionError as file_error:
                sync_run.files_failed += 1

                root_error = file_error.__cause__ if isinstance(file_error.__cause__, Exception) else file_error

                if isinstance(root_error, ConnectorParseError):
                    failure_stage = ConnectorFailureStage.PARSE
                elif isinstance(root_error, ConnectorChunkingError):
                    failure_stage = ConnectorFailureStage.CHUNK
                elif isinstance(root_error, ConnectorEmbeddingError):
                    failure_stage = ConnectorFailureStage.EMBED
                else:
                    failure_stage = ConnectorFailureStage.DB_WRITE

                mark_connector_file_failed(
                    db=db,
                    connector_file=connector_file,
                    tenant_id=tenant_id,
                    repository_id=repository_id,
                    sync_run_id=sync_run.id,
                    failure_stage=failure_stage,
                    error_message=str(root_error),
                    external_file_id=source_file.get("external_file_id"),
                    file_name=source_file.get("file_name"),
                    file_path=source_file.get("file_path"),
                )
                db.commit()

            except Exception as file_error:
                sync_run.files_failed += 1
                mark_connector_file_failed(
                    db=db,
                    connector_file=connector_file,
                    tenant_id=tenant_id,
                    repository_id=repository_id,
                    sync_run_id=sync_run.id,
                    failure_stage=ConnectorFailureStage.DISCOVERY,
                    error_message=str(file_error),
                    external_file_id=source_file.get("external_file_id"),
                    file_name=source_file.get("file_name"),
                    file_path=source_file.get("file_path"),
                )
                db.commit()

        if new_delta_link:
            current_metadata = repository.sync_metadata or {}
            current_metadata["sharepoint_delta_link"] = new_delta_link
            current_metadata["sharepoint_delta_initialized"] = True
            repository.sync_metadata = current_metadata

            current_config = repository.connection_config or {}
            current_config["delta_link"] = new_delta_link
            repository.connection_config = current_config

        final_status = (
            ConnectorSyncStatus.COMPLETED_WITH_ERRORS
            if sync_run.files_failed > 0
            else ConnectorSyncStatus.COMPLETED
        )

        complete_sync_run(db=db, sync_run=sync_run, status=final_status)

        repository.sync_status = final_status
        repository.last_sync_status = final_status
        repository.last_sync_completed_at = sync_run.sync_completed_at
        repository.last_sync_at = sync_run.sync_completed_at
        repository.last_sync_error = None
        db.commit()

        return sync_run

    except Exception as sync_error:
        complete_sync_run(
            db=db,
            sync_run=sync_run,
            status=ConnectorSyncStatus.FAILED,
            error_message=str(sync_error),
        )

        repository.sync_status = ConnectorSyncStatus.FAILED
        repository.last_sync_status = ConnectorSyncStatus.FAILED
        repository.last_sync_completed_at = sync_run.sync_completed_at
        repository.last_sync_at = sync_run.sync_completed_at
        repository.last_sync_error = str(sync_error)
        db.commit()
        raise
