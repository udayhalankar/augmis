from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.connector_sync_constants import ConnectorFileStatus
from app.core.connector_exceptions import (
    ConnectorChunkingError,
    ConnectorEmbeddingError,
    ConnectorParseError,
)
from app.db_models import ConnectorFile, Document, DocumentChunk
from app.services.chunking_service import chunk_text
from app.services.connector_temp_file_service import (
    safe_remove_temp_file,
    write_temp_connector_file,
)
from app.services.document_parser_service import parse_document_with_details
from app.services.connector_document_lifecycle_service import retire_old_document_version
from app.services.pgvector_indexing_service import embed_texts
from app.services.symployee_document_service import register_symployee_connector_ingestion


def utc_now():
    return datetime.now(timezone.utc)


def soft_delete_old_document_chunks(
    db: Session,
    tenant_id,
    document_id,
):
    chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.tenant_id == tenant_id,
            DocumentChunk.document_id == document_id,
        )
        .all()
    )

    for chunk in chunks:
        if hasattr(chunk, "is_deleted"):
            chunk.is_deleted = True
            if hasattr(chunk, "deleted_at"):
                chunk.deleted_at = utc_now()
        else:
            db.delete(chunk)

    db.commit()


def ingest_connector_file_to_pgvector(
    db: Session,
    tenant_id,
    repository,
    connector_file: ConnectorFile,
    source_file: dict,
    file_content: bytes,
    uploaded_by=None,
):
    temp_path = None

    try:
        file_name = source_file.get("file_name")
        temp_path = write_temp_connector_file(file_name, file_content)

        try:
            parse_result = parse_document_with_details(temp_path)
        except Exception as exc:
            raise ConnectorParseError(str(exc)) from exc

        parsed_text = parse_result.get("text", "")

        if not parsed_text or not parsed_text.strip():
            raise ConnectorParseError("Parsed document text is empty")

        try:
            chunks = chunk_text(parsed_text)
        except Exception as exc:
            raise ConnectorChunkingError(str(exc)) from exc

        if not chunks:
            raise ConnectorChunkingError("No chunks generated from parsed document")

        try:
            embeddings = embed_texts(chunks)
        except Exception as exc:
            raise ConnectorEmbeddingError(str(exc)) from exc
        document_id = f"DOC-CONN-{str(uuid4())[:12].upper()}"
        stored_path = source_file.get("metadata", {}).get("full_path") or source_file.get("file_path")
        previous_document_id = None

        if connector_file.metadata_json:
            previous_document_id = connector_file.metadata_json.get("previous_document_id")

        if previous_document_id:
            retire_old_document_version(
                db=db,
                tenant_id=tenant_id,
                old_document_id=previous_document_id,
            )

        document = Document(
            document_id=document_id,
            tenant_id=tenant_id,
            repository_id=repository.repository_id,
            file_name=connector_file.file_name,
            original_file_name=connector_file.file_name,
            source_type=repository.source_type,
            business_area=repository.business_area,
            stored_path=stored_path,
            uploaded_by=uploaded_by,
            uploaded_at=utc_now(),
            metadata_json={
                **(source_file.get("metadata") or {}),
                "parser": parse_result.get("parser"),
                "ocr_used": parse_result.get("ocr_used", False),
                "ocr_available": parse_result.get("ocr_available", False),
                "ocr_error": parse_result.get("ocr_error"),
                "page_count": parse_result.get("page_count"),
                "extracted_characters": parse_result.get("extracted_characters", 0),
                "text_status": parse_result.get("text_status"),
                "chunk_count": len(chunks),
            },
            external_file_id=connector_file.external_file_id,
            file_hash=connector_file.file_hash,
            version_number=connector_file.version_number,
            is_current_version=True,
            source_created_at=connector_file.source_created_at,
            source_modified_at=connector_file.source_modified_at,
            is_deleted=False,
            connector_file_id=connector_file.id,
            created_by=uploaded_by,
            modified_by=uploaded_by,
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        connector_file.document_id = document.document_id
        connector_file.metadata_json = {
            **(connector_file.metadata_json or {}),
            "parser": parse_result.get("parser"),
            "ocr_used": parse_result.get("ocr_used", False),
            "ocr_available": parse_result.get("ocr_available", False),
            "ocr_error": parse_result.get("ocr_error"),
            "page_count": parse_result.get("page_count"),
            "extracted_characters": parse_result.get("extracted_characters", 0),
            "text_status": parse_result.get("text_status"),
            "chunk_count": len(chunks),
        }

        for index, chunk_text_value in enumerate(chunks):
            chunk = DocumentChunk(
                chunk_id=f"CHUNK-{str(uuid4())[:12].upper()}",
                document_id=document.document_id,
                tenant_id=tenant_id,
                repository_id=repository.repository_id,
                business_area=repository.business_area,
                file_name=connector_file.file_name,
                chunk_index=index,
                chunk_text=chunk_text_value,
                embedding=embeddings[index],
                metadata_json={
                    "connector_file_id": str(connector_file.id),
                    "external_file_id": connector_file.external_file_id,
                    "file_hash": connector_file.file_hash,
                    "version_number": connector_file.version_number,
                    "source_modified_at": str(connector_file.source_modified_at),
                },
                created_by=uploaded_by,
                modified_by=uploaded_by,
            )
            db.add(chunk)

        connector_file.sync_status = ConnectorFileStatus.INDEXED
        connector_file.last_synced_at = utc_now()
        connector_file.last_error_message = None
        connector_file.modified_by = uploaded_by

        db.commit()
        db.refresh(connector_file)

        symployee_result = register_symployee_connector_ingestion(
            db=db,
            tenant_id=tenant_id,
            repository=repository,
            connector_file=connector_file,
            source_file=source_file,
            document=document,
            parse_result=parse_result,
            parsed_text=parsed_text,
            uploaded_by=uploaded_by,
        )

        return {
            "document_id": document.document_id,
            "chunks_created": len(chunks),
            "embeddings_created": len(chunks),
            "ocr_used": parse_result.get("ocr_used", False),
            "parser": parse_result.get("parser"),
            "extracted_characters": parse_result.get("extracted_characters", 0),
            "symployee_identity_id": symployee_result["identity_id"],
            "symployee_version_id": symployee_result["version_id"],
        }

    finally:
        safe_remove_temp_file(temp_path)
