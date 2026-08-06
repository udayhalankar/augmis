import json
import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db_models import Document, DocumentChunk
from app.services.extracted_fact_service import get_extracted_facts_for_work_area
from app.services.repository_service import (
    get_allowed_business_areas,
    get_allowed_repository_ids,
)
from app.services.pgvector_search_service import search_pgvector


def _serialize_chunk(chunk: DocumentChunk) -> dict:
    return {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "file_name": chunk.file_name,
        "business_area": chunk.business_area,
        "repository_id": chunk.repository_id,
        "chunk_text": chunk.chunk_text,
        "text": chunk.chunk_text,
        "metadata": chunk.metadata_json,
        "search_mode": "copilot_exact_document",
    }


def _extract_document_identifier(query: str) -> str | None:
    normalized = " ".join(str(query or "").strip().split())
    if not normalized:
        return None

    match = re.search(r"\b([A-Z]{2,5}-\d{4}-\d{3,5}(?:-\d{3,5})?)\b", normalized, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def _retrieve_exact_document_chunks(
    query: str,
    current_user: dict,
    db: Session,
    business_area: str = "All",
) -> list[dict]:
    document_identifier = _extract_document_identifier(query)
    if not document_identifier:
        return []

    allowed_repo_ids = get_allowed_repository_ids(current_user, "read")
    allowed_business_areas = get_allowed_business_areas(current_user, "read")
    effective_business_areas = allowed_business_areas

    if not allowed_repo_ids:
        return []

    if business_area and business_area != "All":
        normalized_business_area = business_area.strip().lower()
        effective_business_areas = [
            area for area in allowed_business_areas if str(area).strip().lower() == normalized_business_area
        ]
        if not effective_business_areas:
            return []

    like_query = f"%{document_identifier}%"
    rows = (
        db.query(DocumentChunk)
        .join(Document, Document.document_id == DocumentChunk.document_id)
        .filter(DocumentChunk.tenant_id == current_user["tenant_id"])
        .filter(DocumentChunk.repository_id.in_(allowed_repo_ids))
        .filter(DocumentChunk.is_deleted == False)
        .filter(Document.is_deleted == False)
        .filter(Document.is_current_version == True)
        .filter(
            or_(
                DocumentChunk.file_name.ilike(like_query),
                Document.file_name.ilike(like_query),
                Document.original_file_name.ilike(like_query),
            )
        )
        .order_by(DocumentChunk.file_name.asc(), DocumentChunk.chunk_index.asc())
        .all()
    )

    if effective_business_areas:
        allowed_area_set = {str(area).strip().lower() for area in effective_business_areas}
        rows = [
            row for row in rows
            if str(row.business_area or "").strip().lower() in allowed_area_set
        ]

    return [_serialize_chunk(row) for row in rows]


def retrieve_context(
    query: str,
    current_user: dict,
    db: Session,
    top_k: int = 8,
    business_area: str = "All",
):
    exact_chunks = _retrieve_exact_document_chunks(
        query=query,
        current_user=current_user,
        db=db,
        business_area=business_area,
    )

    if exact_chunks:
        chunks = exact_chunks[:top_k]
    else:
        result = search_pgvector(
            query=query,
            current_user=current_user,
            db=db,
            top_k=top_k,
            business_area=business_area,
        )
        chunks = result.get("data", [])

    facts_by_document = {}
    business_area_name = business_area if business_area and business_area != "All" else None
    if business_area_name:
        fact_rows = get_extracted_facts_for_work_area(
            current_user["tenant_id"],
            business_area_name,
            db=db,
        )
        facts_by_document = {
            item.get("document_id"): item.get("facts_json") or {}
            for item in fact_rows
            if item.get("document_id")
        }

    context_text = "\n\n".join(
        [
            f"Source: {chunk.get('file_name')} | "
            f"Repository: {chunk.get('repository_id')} | "
            f"Business Area: {chunk.get('business_area')} | "
            f"Extracted Facts: {json.dumps(facts_by_document.get(chunk.get('document_id'), {}), ensure_ascii=True, default=str)}\n"
            f"{chunk.get('chunk_text')}"
            for chunk in chunks
        ]
    )

    sources = [
        {
            "chunk_id": chunk.get("chunk_id"),
            "document_id": chunk.get("document_id"),
            "file_name": chunk.get("file_name"),
            "repository_id": chunk.get("repository_id"),
            "business_area": chunk.get("business_area"),
            "metadata": chunk.get("metadata", {}),
            "preview": chunk.get("chunk_text", "")[:500],
        }
        for chunk in chunks
    ]

    return {
        "context": context_text,
        "sources": sources,
        "chunks": chunks,
    }
