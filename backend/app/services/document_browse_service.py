from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db_models import ConnectorFile, ConnectorSyncFailure, Document, DocumentChunk
from app.services.extracted_fact_service import get_extracted_facts_for_work_area
from app.services.repository_service import (
    get_allowed_business_areas,
    get_allowed_repository_ids,
)
from app.services.work_area_service import get_work_area_definition
from app.services.work_area_rule_engine_service import evaluate_work_area_rules


def browse_indexed_documents(
    current_user: dict,
    db: Session,
    limit: int = 50,
    repository_id: str | None = None,
    file_name: str | None = None,
    business_area: str | None = None,
):
    selected_business_area = business_area
    allowed_repo_ids = get_allowed_repository_ids(current_user, "read")
    allowed_business_areas = get_allowed_business_areas(current_user, "read")

    if repository_id:
        allowed_repo_ids = [repo_id for repo_id in allowed_repo_ids if repo_id == repository_id]

    if selected_business_area and selected_business_area != "All":
        allowed_business_areas = [
            area for area in allowed_business_areas
            if str(area).strip().lower() == str(selected_business_area).strip().lower()
        ]

    if not allowed_repo_ids:
        return {
            "success": True,
            "data": [],
            "message": "No accessible repository files were found.",
            "status": {
                "browse_mode": True,
                "result_count": 0,
                "allowed_repository_count": 0,
                "allowed_business_areas": allowed_business_areas,
            },
        }

    connector_files_query = (
        db.query(ConnectorFile)
        .filter(
            ConnectorFile.tenant_id == current_user["tenant_id"],
            ConnectorFile.repository_id.in_(allowed_repo_ids),
            ConnectorFile.is_current_version == True,
        )
    )

    if file_name:
        connector_files_query = connector_files_query.filter(ConnectorFile.file_name == file_name)

    connector_files = (
        connector_files_query
        .order_by(ConnectorFile.file_name.asc())
        .limit(limit)
        .all()
    )

    doc_ids = [file.document_id for file in connector_files if file.document_id]
    docs = (
        db.query(Document)
        .filter(
            Document.tenant_id == current_user["tenant_id"],
            Document.document_id.in_(doc_ids) if doc_ids else False,
        )
        .all()
        if doc_ids
        else []
    )
    docs_by_id = {doc.document_id: doc for doc in docs}

    chunk_counts = {
        row.document_id: row.chunk_count
        for row in (
            db.query(
                DocumentChunk.document_id,
                func.count(DocumentChunk.chunk_id).label("chunk_count"),
            )
            .filter(
                DocumentChunk.tenant_id == current_user["tenant_id"],
                DocumentChunk.document_id.in_(doc_ids) if doc_ids else False,
                DocumentChunk.is_deleted == False,
            )
            .group_by(DocumentChunk.document_id)
            .all()
            if doc_ids
            else []
        )
    }

    first_chunks = {}
    if doc_ids:
        first_chunk_rows = (
            db.query(DocumentChunk)
            .filter(
                DocumentChunk.tenant_id == current_user["tenant_id"],
                DocumentChunk.document_id.in_(doc_ids),
                DocumentChunk.is_deleted == False,
            )
            .order_by(DocumentChunk.document_id.asc(), DocumentChunk.chunk_index.asc())
            .all()
        )
        for chunk in first_chunk_rows:
            if chunk.document_id not in first_chunks:
                first_chunks[chunk.document_id] = chunk

    failures = (
        db.query(ConnectorSyncFailure)
        .filter(
            ConnectorSyncFailure.tenant_id == current_user["tenant_id"],
            ConnectorSyncFailure.repository_id.in_(allowed_repo_ids),
            ConnectorSyncFailure.resolved == False,
        )
        .order_by(ConnectorSyncFailure.created_at.desc())
        .all()
    )
    failure_by_connector_file_id = {}
    for failure in failures:
        if failure.connector_file_id and failure.connector_file_id not in failure_by_connector_file_id:
            failure_by_connector_file_id[failure.connector_file_id] = failure

    results = []
    extracted_facts_by_area: dict[str, list[dict]] = {}
    status_rule_payload = (
        evaluate_work_area_rules(current_user["tenant_id"], selected_business_area, db=db).get("data", {})
        if selected_business_area and selected_business_area != "All"
        else {}
    )
    for file in connector_files:
        document = docs_by_id.get(file.document_id) if file.document_id else None
        metadata = (document.metadata_json if document else None) or file.metadata_json or {}
        document_business_area = document.business_area if document else None

        if (
            allowed_business_areas
            and document_business_area
            and document_business_area not in allowed_business_areas
        ):
            continue

        first_chunk = first_chunks.get(document.document_id) if document else None
        failure = failure_by_connector_file_id.get(str(file.id))
        text_preview = first_chunk.chunk_text if first_chunk else (
            "File is tracked in the repository but no indexed text chunks are available yet."
        )
        effective_status = "failed" if failure else file.sync_status
        work_area_definition = (
            get_work_area_definition(current_user["tenant_id"], document_business_area)
            if document_business_area
            else None
        )
        extracted_fact = None
        if document_business_area and document:
            normalized_area = str(document_business_area).strip().lower()
            if normalized_area not in extracted_facts_by_area:
                extracted_facts_by_area[normalized_area] = get_extracted_facts_for_work_area(
                    current_user["tenant_id"],
                    document_business_area,
                    db=db,
                )
            extracted_fact_rows = extracted_facts_by_area[normalized_area]
            extracted_fact = next(
                (
                    item for item in extracted_fact_rows
                    if item.get("document_id") == document.document_id
                ),
                None,
            )

        results.append(
            {
                "document_id": document.document_id if document else None,
                "repository_id": file.repository_id,
                "file_name": file.file_name,
                "business_area": document_business_area,
                "source_type": file.source_type,
                "page": 1,
                "score": None,
                "chunk_text": text_preview,
                "text": text_preview,
                "metadata": {
                    **metadata,
                    "chunk_count": chunk_counts.get(document.document_id, 0) if document else 0,
                    "browse_mode": True,
                    "sync_status": effective_status,
                    "failure_stage": failure.failure_stage if failure else None,
                    "last_error_message": failure.error_message if failure else file.last_error_message,
                    "file_hash": file.file_hash,
                    "tracked_only": document is None,
                    "intelligence_pattern": work_area_definition.get("intelligence_pattern") if work_area_definition else None,
                    "enabled_checks": work_area_definition.get("enabled_checks") if work_area_definition else [],
                    "required_specifics": work_area_definition.get("required_specifics") if work_area_definition else [],
                    "entities_to_extract": work_area_definition.get("entities_to_extract") if work_area_definition else [],
                    "compiled_checks": extracted_fact.get("compiled_checks") if extracted_fact else [],
                    "required_specifics_presence": extracted_fact.get("required_specifics_presence") if extracted_fact else {},
                    "extracted_facts": extracted_fact.get("facts_json") if extracted_fact else {},
                },
            }
        )

    return {
        "success": True,
        "data": results,
        "message": "Repository files loaded.",
        "status": {
                "browse_mode": True,
                "result_count": len(results),
                "allowed_repository_count": len(allowed_repo_ids),
                "allowed_business_areas": allowed_business_areas,
                "repository_id": repository_id,
                "file_name": file_name,
                "business_area": selected_business_area,
                "intelligence_pattern": status_rule_payload.get("intelligence_pattern"),
                "rule_finding_count": status_rule_payload.get("finding_count", 0),
            },
        }
