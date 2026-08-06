from openai import OpenAI
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import case, or_
import re

from app.core.config import settings
from app.db_models import Document, DocumentChunk
from app.services.extracted_fact_service import get_extracted_facts_for_work_area
from app.services.repository_service import (
    get_allowed_business_areas,
    get_allowed_repository_ids,
)
from app.services.work_area_service import get_work_area_definition
from app.services.work_area_rule_engine_service import evaluate_work_area_rules


client = OpenAI(api_key=settings.OPENAI_API_KEY)
EMBEDDING_MODEL = settings.OPENAI_EMBEDDING_MODEL


def embed_query(query: str) -> list[float]:
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[query],
        )
        return response.data[0].embedding
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_type": "openai_embedding_error",
                "message": "Failed to generate a query embedding",
                "provider": "openai",
                "model": EMBEDDING_MODEL,
                "reason": str(exc),
            },
        )


def _serialize_rows(rows, search_mode: str) -> list[dict]:
    return [
        {
            "chunk_id": row.chunk_id,
            "document_id": row.document_id,
            "file_name": row.file_name,
            "business_area": row.business_area,
            "repository_id": row.repository_id,
            "chunk_text": row.chunk_text,
            "text": row.chunk_text,
            "metadata": row.metadata_json,
            "search_mode": search_mode,
        }
        for row in rows
    ]


def _build_status_payload(
    *,
    query: str,
    search_mode: str,
    results: list[dict],
    allowed_repo_ids: list[str],
    allowed_business_areas: list[str],
    message: str | None = None,
) -> dict:
    return {
        "query": query,
        "search_mode": search_mode,
        "result_count": len(results),
        "allowed_repository_count": len(allowed_repo_ids),
        "allowed_business_areas": allowed_business_areas,
        "message": message,
    }


def _tokenize_query(query: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", query.lower()) if len(token) >= 3]


def _augment_query_for_work_area(query: str, current_user: dict, business_area: str) -> tuple[str, dict | None]:
    if not business_area or business_area == "All":
        return query, None

    work_area = get_work_area_definition(current_user["tenant_id"], business_area)
    if not work_area:
        return query, None

    additions = []
    additions.extend((work_area.get("tags_keywords") or [])[:4])
    additions.extend((work_area.get("summary_focus") or [])[:2])
    additions.extend((work_area.get("required_specifics") or [])[:3])
    additions.extend((work_area.get("enabled_checks") or [])[:3])
    additions = [str(item).strip() for item in additions if str(item).strip()]

    if not additions:
        return query, work_area

    return f"{query} {' '.join(additions)}".strip(), work_area


def _lexical_relevance_boost(row: DocumentChunk, query: str) -> float:
    query_text = query.strip().lower()
    tokens = _tokenize_query(query)
    chunk_text = (row.chunk_text or "").lower()
    file_name = (row.file_name or "").lower()

    score = 0.0

    if query_text and query_text in chunk_text:
        score += 6.0
    if query_text and query_text in file_name:
        score += 4.0

    for token in tokens:
        if token in file_name:
            score += 1.5
        if token in chunk_text:
            score += 0.75

    return score


def _fetch_lexical_candidates(
    db: Session,
    current_user: dict,
    allowed_repo_ids: list[str],
    allowed_business_areas: list[str],
    query: str,
    top_k: int,
) -> list[DocumentChunk]:
    normalized_query = query.strip()
    tokens = _tokenize_query(query)[:8]
    lexical_conditions = []
    exact_match_case = None
    file_name_match_case = None
    chunk_text_match_case = None

    if normalized_query:
        like_query = f"%{normalized_query}%"
        lexical_conditions.extend(
            [
                DocumentChunk.chunk_text.ilike(like_query),
                DocumentChunk.file_name.ilike(like_query),
            ]
        )
        exact_match_case = case(
            (DocumentChunk.file_name.ilike(like_query), 0),
            (DocumentChunk.chunk_text.ilike(like_query), 1),
            else_=2,
        )

    for token in tokens:
        token_like = f"%{token}%"
        lexical_conditions.extend(
            [
                DocumentChunk.chunk_text.ilike(token_like),
                DocumentChunk.file_name.ilike(token_like),
            ]
        )

    if not lexical_conditions:
        return []

    if tokens:
        file_name_match_case = case(
            *[(DocumentChunk.file_name.ilike(f"%{token}%"), 0) for token in tokens],
            else_=1,
        )
        chunk_text_match_case = case(
            *[(DocumentChunk.chunk_text.ilike(f"%{token}%"), 0) for token in tokens],
            else_=1,
        )

    order_by_clauses = []
    if exact_match_case is not None:
        order_by_clauses.append(exact_match_case.asc())
    if file_name_match_case is not None:
        order_by_clauses.append(file_name_match_case.asc())
    if chunk_text_match_case is not None:
        order_by_clauses.append(chunk_text_match_case.asc())
    order_by_clauses.extend(
        [
            DocumentChunk.file_name.asc(),
            DocumentChunk.chunk_index.asc(),
        ]
    )

    return (
        _build_base_query(
            db=db,
            current_user=current_user,
            allowed_repo_ids=allowed_repo_ids,
            allowed_business_areas=allowed_business_areas,
        )
        .filter(or_(*lexical_conditions))
        .order_by(*order_by_clauses)
        .limit(max(top_k * 10, 50))
        .all()
    )


def _hybrid_rank_rows(
    semantic_rows: list[DocumentChunk],
    lexical_rows: list[DocumentChunk],
    query: str,
    top_k: int,
) -> list[DocumentChunk]:
    semantic_rank = {
        row.chunk_id: index for index, row in enumerate(semantic_rows)
    }
    lexical_rank = {
        row.chunk_id: index for index, row in enumerate(lexical_rows)
    }

    combined: dict[str, DocumentChunk] = {}
    for row in semantic_rows + lexical_rows:
        if row.chunk_id not in combined:
            combined[row.chunk_id] = row

    semantic_window = max(len(semantic_rows), 1)
    lexical_window = max(len(lexical_rows), 1)
    scored_rows = []
    for row in combined.values():
        semantic_index = semantic_rank.get(row.chunk_id)
        lexical_index = lexical_rank.get(row.chunk_id)

        semantic_score = 0.0
        if semantic_index is not None:
            semantic_score = (semantic_window - semantic_index) * 0.45

        lexical_rank_score = 0.0
        if lexical_index is not None:
            lexical_rank_score = (lexical_window - lexical_index) * 0.6

        lexical_boost = _lexical_relevance_boost(row, query)
        total_score = semantic_score + lexical_rank_score + lexical_boost
        stable_rank = min(
            semantic_index if semantic_index is not None else 10_000,
            lexical_index if lexical_index is not None else 10_000,
        )
        scored_rows.append((total_score, stable_rank, row))

    scored_rows.sort(key=lambda item: (-item[0], item[1]))
    return [row for _, _, row in scored_rows[:top_k]]


def _build_base_query(db: Session, current_user: dict, allowed_repo_ids: list[str], allowed_business_areas: list[str]):
    q = (
        db.query(DocumentChunk)
        .join(Document, Document.document_id == DocumentChunk.document_id)
        .filter(DocumentChunk.tenant_id == current_user["tenant_id"])
        .filter(DocumentChunk.repository_id.in_(allowed_repo_ids))
        .filter(DocumentChunk.is_deleted == False)
        .filter(Document.is_deleted == False)
        .filter(Document.is_current_version == True)
    )

    if allowed_business_areas:
        q = q.filter(DocumentChunk.business_area.in_(allowed_business_areas))

    return q


def _search_lexical(
    db: Session,
    current_user: dict,
    allowed_repo_ids: list[str],
    allowed_business_areas: list[str],
    query: str,
    top_k: int,
    fallback_reason: str | None = None,
):
    rows = _fetch_lexical_candidates(
        db=db,
        current_user=current_user,
        allowed_repo_ids=allowed_repo_ids,
        allowed_business_areas=allowed_business_areas,
        query=query,
        top_k=top_k,
    )
    data = _serialize_rows(rows, "lexical")
    message_text = fallback_reason or (
        "Lexical search completed."
        if data
        else "Lexical search completed. No matching indexed chunks were found."
    )

    return {
        "success": True,
        "data": data,
        "message": message_text,
        "status": _build_status_payload(
            query=query,
            search_mode="lexical",
            results=data,
            allowed_repo_ids=allowed_repo_ids,
            allowed_business_areas=allowed_business_areas,
            message=message_text,
        ),
    }


def search_pgvector(
    query: str,
    current_user: dict,
    db: Session,
    top_k: int = 8,
    business_area: str = "All",
):
    allowed_repo_ids = get_allowed_repository_ids(current_user, "read")
    allowed_business_areas = get_allowed_business_areas(current_user, "read")
    effective_business_areas = allowed_business_areas

    if business_area and business_area != "All":
        normalized_business_area = business_area.strip().lower()
        effective_business_areas = [
            area for area in allowed_business_areas if str(area).strip().lower() == normalized_business_area
        ]

    if not allowed_repo_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_type": "access_filtering",
                "message": "No accessible repositories were found for this user",
                "allowed_repository_ids": [],
                "allowed_business_areas": effective_business_areas,
            },
        )

    if business_area and business_area != "All" and not effective_business_areas:
        return {
            "success": True,
            "data": [],
            "message": f"No accessible indexed content was found for business area '{business_area}'.",
            "status": _build_status_payload(
                query=query,
                search_mode="none",
                results=[],
                allowed_repo_ids=allowed_repo_ids,
                allowed_business_areas=effective_business_areas,
                message=f"No accessible indexed content was found for business area '{business_area}'.",
            ),
        }

    effective_query, work_area_definition = _augment_query_for_work_area(
        query=query,
        current_user=current_user,
        business_area=business_area,
    )

    try:
        query_embedding = embed_query(effective_query)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        reason = detail.get("message") or "Embedding generation failed"
        return _search_lexical(
            db=db,
            current_user=current_user,
            allowed_repo_ids=allowed_repo_ids,
            allowed_business_areas=effective_business_areas,
            query=query,
            top_k=top_k,
            fallback_reason=f"Semantic search is unavailable right now. Showing lexical matches instead. Reason: {reason}.",
        )

    q = _build_base_query(
        db=db,
        current_user=current_user,
        allowed_repo_ids=allowed_repo_ids,
        allowed_business_areas=effective_business_areas,
    )

    try:
        results = (
            q.order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(max(top_k * 4, top_k))
            .all()
        )
    except SQLAlchemyError:
        return _search_lexical(
            db=db,
            current_user=current_user,
            allowed_repo_ids=allowed_repo_ids,
            allowed_business_areas=effective_business_areas,
            query=query,
            top_k=top_k,
            fallback_reason=(
                "Semantic search is unavailable right now. Showing lexical matches instead. "
                "Reason: Failed to execute the vector search query."
            ),
        )
    except Exception:
        return _search_lexical(
            db=db,
            current_user=current_user,
            allowed_repo_ids=allowed_repo_ids,
            allowed_business_areas=effective_business_areas,
            query=query,
            top_k=top_k,
            fallback_reason=(
                "Semantic search is unavailable right now. Showing lexical matches instead. "
                "Reason: Unexpected failure during vector search."
            ),
        )

    lexical_candidates = _fetch_lexical_candidates(
        db=db,
        current_user=current_user,
        allowed_repo_ids=allowed_repo_ids,
        allowed_business_areas=effective_business_areas,
        query=effective_query,
        top_k=max(top_k * 2, top_k),
    )
    ranked_rows = _hybrid_rank_rows(results, lexical_candidates, effective_query, top_k)
    data = _serialize_rows(ranked_rows, "semantic_hybrid")
    rule_payload = None
    fact_rows = []
    if work_area_definition:
        rule_payload = evaluate_work_area_rules(
            current_user["tenant_id"],
            business_area,
            db=db,
        ).get("data", {})
        fact_rows = get_extracted_facts_for_work_area(
            current_user["tenant_id"],
            business_area,
            db=db,
        )
        facts_by_document = {
            item.get("document_id"): item
            for item in fact_rows
            if item.get("document_id")
        }
        for item in data:
            item.setdefault("metadata", {})
            item["metadata"]["intelligence_pattern"] = work_area_definition.get("intelligence_pattern")
            item["metadata"]["enabled_checks"] = work_area_definition.get("enabled_checks") or []
            item["metadata"]["required_specifics"] = work_area_definition.get("required_specifics") or []
            item["metadata"]["rule_finding_count"] = rule_payload.get("finding_count") or 0
            extracted_fact = facts_by_document.get(item.get("document_id"))
            if extracted_fact:
                item["metadata"]["entities_to_extract"] = work_area_definition.get("entities_to_extract") or []
                item["metadata"]["compiled_checks"] = extracted_fact.get("compiled_checks") or []
                item["metadata"]["required_specifics_presence"] = extracted_fact.get("required_specifics_presence") or {}
                item["metadata"]["extracted_facts"] = extracted_fact.get("facts_json") or {}
    message_text = (
        "Hybrid semantic search completed."
        if data
        else "Hybrid semantic search completed. No matching indexed chunks were found."
    )

    return {
        "success": True,
        "data": data,
        "message": message_text,
        "status": {
            **_build_status_payload(
            query=query,
            search_mode="semantic_hybrid",
            results=data,
            allowed_repo_ids=allowed_repo_ids,
            allowed_business_areas=effective_business_areas,
            message=message_text,
            ),
            "intelligence_pattern": work_area_definition.get("intelligence_pattern") if work_area_definition else None,
            "rule_finding_count": rule_payload.get("finding_count") if rule_payload else 0,
            "extracted_fact_count": len(fact_rows),
        },
    }
