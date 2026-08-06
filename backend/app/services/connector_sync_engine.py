from sqlalchemy.orm import Session

from app.core.connector_exceptions import (
    ConnectorChunkingError,
    ConnectorConfigurationError,
    ConnectorDiscoveryError,
    ConnectorDownloadError,
    ConnectorEmbeddingError,
    ConnectorIngestionError,
    ConnectorParseError,
)
from app.core.connector_sync_constants import (
    ConnectorFailureStage,
    ConnectorSyncStatus,
)
from app.services.connector_validation_service import (
    validate_repository_connector_config,
    validate_source_file_contract,
)
from app.services.connector_sync_db_service import (
    complete_sync_run,
    mark_connector_file_failed,
    start_sync_run,
)
from app.services.connector_incremental_service import (
    IncrementalDecision,
    create_new_connector_file,
    create_updated_file_version,
    decide_incremental_action,
    mark_file_unchanged,
    mark_file_duplicate_skipped,
)
from app.services.connector_document_lifecycle_service import soft_delete_missing_files
from app.services.connector_ingestion_pipeline import ingest_connector_file_to_pgvector


def run_incremental_connector_sync(
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

        try:
            source_files = connector.list_files()
        except Exception as exc:
            raise ConnectorDiscoveryError(str(exc)) from exc

        source_external_ids = set()
        discovery_warning_message = None
        discovery_warning_metadata = None

        sync_run.files_discovered = len(source_files)

        if repository.source_type == "sharedrive" and len(source_files) == 0:
            try:
                connection_details = connector.test_connection()
                discovery_warning_metadata = {
                    "warning_code": "sharedrive_zero_discovered",
                    "root_path": connection_details.get("root_path"),
                    "directory_count": connection_details.get("directory_count", 0),
                    "file_count": connection_details.get("file_count", 0),
                }
                discovery_warning_message = (
                    "Shared Drive folder is reachable but no supported files were discovered. "
                    "Check whether the mounted path is correct and whether the folder contains "
                    "supported file types: PDF, DOCX, XLSX, XLS, CSV, TXT, or MD."
                )
            except Exception:
                discovery_warning_metadata = {
                    "warning_code": "sharedrive_zero_discovered",
                }
                discovery_warning_message = (
                    "No files were discovered in the Shared Drive repository."
                )

        db.commit()

        for source_file in source_files:
            connector_file = None

            try:
                validate_source_file_contract(source_file)

                external_file_id = source_file["external_file_id"]

                source_external_ids.add(external_file_id)

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

        deleted_files = soft_delete_missing_files(
            db=db,
            tenant_id=tenant_id,
            repository_id=repository_id,
            source_external_file_ids=source_external_ids,
            sync_run_id=sync_run.id,
        )

        sync_run.files_deleted = len(deleted_files)

        final_status = (
            ConnectorSyncStatus.COMPLETED_WITH_ERRORS
            if sync_run.files_failed > 0 or discovery_warning_message
            else ConnectorSyncStatus.COMPLETED
        )

        complete_sync_run(
            db=db,
            sync_run=sync_run,
            status=final_status,
            error_message=discovery_warning_message,
        )

        repository.last_sync_run_id = sync_run.id
        repository.sync_status = final_status
        repository.last_sync_status = final_status
        repository.last_sync_started_at = sync_run.sync_started_at
        repository.last_sync_completed_at = sync_run.sync_completed_at
        repository.last_sync_at = sync_run.sync_completed_at
        repository.last_sync_error = discovery_warning_message

        sync_metadata = dict(repository.sync_metadata or {})
        if discovery_warning_message:
            sync_metadata["discovery_warning"] = {
                "message": discovery_warning_message,
                **(discovery_warning_metadata or {}),
            }
        else:
            sync_metadata.pop("discovery_warning", None)
        repository.sync_metadata = sync_metadata

        db.commit()

        return sync_run

    except ConnectorConfigurationError as sync_error:
        complete_sync_run(
            db=db,
            sync_run=sync_run,
            status=ConnectorSyncStatus.FAILED,
            error_message=str(sync_error),
        )

        repository.last_sync_run_id = sync_run.id
        repository.sync_status = ConnectorSyncStatus.FAILED
        repository.last_sync_status = ConnectorSyncStatus.FAILED
        repository.last_sync_completed_at = sync_run.sync_completed_at
        repository.last_sync_at = sync_run.sync_completed_at
        repository.last_sync_error = str(sync_error)

        db.commit()

        raise

    except ConnectorDiscoveryError as sync_error:
        complete_sync_run(
            db=db,
            sync_run=sync_run,
            status=ConnectorSyncStatus.FAILED,
            error_message=str(sync_error),
        )

        repository.last_sync_run_id = sync_run.id
        repository.sync_status = ConnectorSyncStatus.FAILED
        repository.last_sync_status = ConnectorSyncStatus.FAILED
        repository.last_sync_completed_at = sync_run.sync_completed_at
        repository.last_sync_at = sync_run.sync_completed_at
        repository.last_sync_error = str(sync_error)

        db.commit()

        raise

    except Exception as sync_error:
        complete_sync_run(
            db=db,
            sync_run=sync_run,
            status=ConnectorSyncStatus.FAILED,
            error_message=str(sync_error),
        )

        repository.last_sync_run_id = sync_run.id
        repository.sync_status = ConnectorSyncStatus.FAILED
        repository.last_sync_status = ConnectorSyncStatus.FAILED
        repository.last_sync_completed_at = sync_run.sync_completed_at
        repository.last_sync_at = sync_run.sync_completed_at
        repository.last_sync_error = str(sync_error)

        db.commit()

        raise
