from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.connectors.connector_factory import get_connector
from app.db_models import (
    ConnectorFile,
    ConnectorSyncFailure,
    Document,
    DocumentChunk,
    Repository,
)
from app.utils.extraction import get_ocr_diagnostics


def _connector_payload(repo: Repository) -> dict:
    return {
        "repository_id": repo.repository_id,
        "tenant_id": repo.tenant_id,
        "repository_name": repo.repository_name,
        "source_type": repo.source_type,
        "source_path": repo.source_path,
        "connection_config": repo.connection_config or {},
    }


def _discover_live_source_files(repo: Repository) -> tuple[dict[str, dict], dict | None]:
    try:
        connector = get_connector(_connector_payload(repo))
        source_files = connector.list_files()
        return {
            str(item.get("external_file_id") or ""): item
            for item in source_files
            if str(item.get("external_file_id") or "").strip()
        }, None
    except Exception as exc:
        return {}, {
            "mode": "source_scan_unavailable",
            "error_id": f"repository_report_source_scan_{exc.__class__.__name__}",
            "error_message": str(exc),
        }


def _classify_index_quality(
    *,
    sync_status: str | None,
    chunk_count: int,
    extracted_characters: int | None,
    ocr_used: bool,
    failure_stage: str | None,
) -> str:
    if failure_stage:
        return "failed"

    if sync_status == "deleted":
        return "deleted"

    if chunk_count <= 0:
        return "empty"

    extracted_characters = extracted_characters or 0
    if ocr_used:
        return "ocr_indexed"
    if extracted_characters >= 1200 or chunk_count >= 3:
        return "good"
    if extracted_characters >= 250 or chunk_count >= 1:
        return "partial"
    return "low_text"


def build_repository_index_report(
    db: Session,
    tenant_id: str,
    repository_id: str,
) -> dict:
    repo = (
        db.query(Repository)
        .filter(
            Repository.tenant_id == tenant_id,
            Repository.repository_id == repository_id,
        )
        .first()
    )
    if not repo:
        raise ValueError("Repository not found")

    connector_files = (
        db.query(ConnectorFile)
        .filter(
            ConnectorFile.tenant_id == tenant_id,
            ConnectorFile.repository_id == repository_id,
            ConnectorFile.is_current_version == True,
        )
        .order_by(ConnectorFile.file_name.asc())
        .all()
    )

    documents = (
        db.query(Document)
        .filter(
            Document.tenant_id == tenant_id,
            Document.repository_id == repository_id,
            Document.is_current_version == True,
        )
        .all()
    )
    docs_by_connector_file_id = {
        doc.connector_file_id: doc
        for doc in documents
        if doc.connector_file_id
    }

    chunk_counts = {
        row.document_id: row.chunk_count
        for row in (
            db.query(
                DocumentChunk.document_id,
                func.count(DocumentChunk.chunk_id).label("chunk_count"),
            )
            .filter(
                DocumentChunk.tenant_id == tenant_id,
                DocumentChunk.repository_id == repository_id,
                DocumentChunk.is_deleted == False,
            )
            .group_by(DocumentChunk.document_id)
            .all()
        )
    }

    unresolved_failures = (
        db.query(ConnectorSyncFailure)
        .filter(
            ConnectorSyncFailure.tenant_id == tenant_id,
            ConnectorSyncFailure.repository_id == repository_id,
            ConnectorSyncFailure.resolved == False,
        )
        .order_by(ConnectorSyncFailure.created_at.desc())
        .all()
    )

    failure_by_connector_file_id = {}
    failure_by_external_file_id = {}
    standalone_failures = []
    for failure in unresolved_failures:
        if failure.connector_file_id and failure.connector_file_id not in failure_by_connector_file_id:
            failure_by_connector_file_id[failure.connector_file_id] = failure
        if failure.external_file_id and failure.external_file_id not in failure_by_external_file_id:
            failure_by_external_file_id[failure.external_file_id] = failure
        if not failure.connector_file_id and not failure.external_file_id:
            standalone_failures.append(failure)

    items = []
    summary = defaultdict(int)
    duplicate_groups = defaultdict(list)

    for connector_file in connector_files:
        if connector_file.file_hash:
            duplicate_groups[connector_file.file_hash].append(connector_file.file_name)

    tracked_external_ids = {
        str(connector_file.external_file_id or "").strip()
        for connector_file in connector_files
        if str(connector_file.external_file_id or "").strip()
    }
    live_source_files, source_scan_diagnostics = _discover_live_source_files(repo)
    live_only_source_files = [
        source_file
        for external_id, source_file in live_source_files.items()
        if external_id not in tracked_external_ids
    ]

    for connector_file in connector_files:
        document = docs_by_connector_file_id.get(str(connector_file.id))
        failure = failure_by_connector_file_id.get(str(connector_file.id)) or failure_by_external_file_id.get(
            connector_file.external_file_id
        )
        document_meta = document.metadata_json or {} if document else {}
        connector_meta = connector_file.metadata_json or {}
        extracted_characters = document_meta.get("extracted_characters")
        if extracted_characters is None:
            extracted_characters = connector_meta.get("extracted_characters")
        ocr_used = bool(document_meta.get("ocr_used") or connector_meta.get("ocr_used"))
        parser = document_meta.get("parser") or connector_meta.get("parser")
        text_status = document_meta.get("text_status") or connector_meta.get("text_status")
        chunk_count = chunk_counts.get(document.document_id, 0) if document else 0
        failure_stage = failure.failure_stage if failure else None
        last_error_message = failure.error_message if failure else connector_file.last_error_message
        effective_status = connector_file.sync_status
        if failure_stage:
            effective_status = "failed"

        quality = _classify_index_quality(
            sync_status=effective_status,
            chunk_count=chunk_count,
            extracted_characters=extracted_characters,
            ocr_used=ocr_used,
            failure_stage=failure_stage,
        )

        if effective_status == "indexed":
            summary["indexed_files"] += 1
        if effective_status == "failed":
            summary["failed_files"] += 1
        if effective_status == "deleted" or connector_file.is_deleted:
            summary["deleted_files"] += 1
        if text_status == "empty_text":
            summary["empty_text_files"] += 1
        if ocr_used:
            summary["ocr_used_files"] += 1

        summary["total_files"] += 1
        summary["total_chunks"] += chunk_count
        duplicate_count = len(duplicate_groups.get(connector_file.file_hash or "", []))
        if duplicate_count > 1:
            summary["duplicate_files"] += 1

        items.append(
            {
                "file_name": connector_file.file_name,
                "file_path": connector_file.file_path,
                "external_file_id": connector_file.external_file_id,
                "file_hash": connector_file.file_hash,
                "sync_status": effective_status,
                "failure_stage": failure_stage,
                "last_error_message": last_error_message,
                "document_id": document.document_id if document else None,
                "chunk_count": chunk_count,
                "extracted_characters": extracted_characters,
                "parser": parser,
                "ocr_used": ocr_used,
                "ocr_available": connector_meta.get("ocr_available", False),
                "ocr_error": connector_meta.get("ocr_error"),
                "text_status": text_status,
                "index_quality": quality,
                "duplicate_count": duplicate_count,
                "duplicate_file_names": duplicate_groups.get(connector_file.file_hash or "", []),
                "source_modified_at": connector_file.source_modified_at.isoformat()
                if connector_file.source_modified_at
                else None,
            }
        )

    for failure in standalone_failures:
        summary["failed_files"] += 1
        summary["total_files"] += 1
        items.append(
            {
                "file_name": failure.file_name or "Unknown file",
                "file_path": failure.file_path,
                "external_file_id": failure.external_file_id,
                "sync_status": "failed",
                "failure_stage": failure.failure_stage,
                "last_error_message": failure.error_message,
                "document_id": None,
                "chunk_count": 0,
                "extracted_characters": None,
                "parser": None,
                "ocr_used": False,
                "ocr_available": False,
                "ocr_error": None,
                "text_status": "unknown",
                "index_quality": "failed",
                "source_modified_at": None,
            }
        )

    for source_file in live_only_source_files:
        summary["total_files"] += 1
        items.append(
            {
                "file_name": source_file.get("file_name") or source_file.get("external_file_id") or "Unknown file",
                "file_path": source_file.get("file_path"),
                "external_file_id": source_file.get("external_file_id"),
                "file_hash": source_file.get("file_hash"),
                "sync_status": "not_tracked",
                "failure_stage": None,
                "last_error_message": (
                    "File exists in the mounted source folder but has not been tracked by sync yet. "
                    "Run Sync or Reindex to ingest it."
                ),
                "document_id": None,
                "chunk_count": 0,
                "extracted_characters": None,
                "parser": None,
                "ocr_used": False,
                "ocr_available": False,
                "ocr_error": None,
                "text_status": "not_tracked",
                "index_quality": "not_tracked",
                "duplicate_count": 0,
                "duplicate_file_names": [],
                "source_modified_at": (
                    source_file.get("modified_at").isoformat()
                    if source_file.get("modified_at")
                    else None
                ),
                "tracking_state": "discovered_not_tracked",
            }
        )

    summary["documents_indexed"] = len(
        [doc for doc in documents if not doc.is_deleted and doc.is_current_version]
    )
    ocr_diagnostics = get_ocr_diagnostics()

    return {
        "repository_id": repo.repository_id,
        "repository_name": repo.repository_name,
        "source_type": repo.source_type,
        "business_area": repo.business_area,
        "ocr": ocr_diagnostics,
        "summary": {
            "total_files": summary["total_files"],
            "tracked_files": len(connector_files),
            "live_only_files": len(live_only_source_files),
            "detected_source_files": len(connector_files) + len(live_only_source_files),
            "documents_indexed": summary["documents_indexed"],
            "total_chunks": summary["total_chunks"],
            "indexed_files": summary["indexed_files"],
            "failed_files": summary["failed_files"],
            "deleted_files": summary["deleted_files"],
            "empty_text_files": summary["empty_text_files"],
            "ocr_used_files": summary["ocr_used_files"],
            "duplicate_files": summary["duplicate_files"],
        },
        "source_scan": source_scan_diagnostics
        or {
            "mode": "available",
            "detected_source_files": len(connector_files) + len(live_only_source_files),
            "live_only_files": len(live_only_source_files),
        },
        "items": items,
    }
