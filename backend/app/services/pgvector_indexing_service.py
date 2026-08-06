from uuid import uuid4

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db_models import Document, DocumentChunk
from app.services.chunking_service import chunk_text
from app.services.document_parser_service import parse_document


client = OpenAI(api_key=settings.OPENAI_API_KEY)
EMBEDDING_MODEL = settings.OPENAI_EMBEDDING_MODEL
MAX_EMBEDDING_BATCH_ITEMS = 96
MAX_EMBEDDING_BATCH_CHARS = 120000


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    batches: list[list[str]] = []
    current_batch: list[str] = []
    current_batch_chars = 0

    for text in texts:
        chunk_text = str(text or "")
        chunk_chars = len(chunk_text)
        batch_full = len(current_batch) >= MAX_EMBEDDING_BATCH_ITEMS
        batch_too_large = current_batch and (current_batch_chars + chunk_chars) > MAX_EMBEDDING_BATCH_CHARS

        if batch_full or batch_too_large:
            batches.append(current_batch)
            current_batch = []
            current_batch_chars = 0

        current_batch.append(chunk_text)
        current_batch_chars += chunk_chars

    if current_batch:
        batches.append(current_batch)

    embeddings: list[list[float]] = []
    for batch in batches:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        embeddings.extend(item.embedding for item in response.data)

    return embeddings


def index_document_pgvector(upload_metadata: dict, db: Session):
    raw_text = parse_document(upload_metadata["stored_path"])
    chunks = chunk_text(raw_text)

    if not chunks:
        return {
            "success": False,
            "message": "No text extracted",
            "chunks_indexed": 0,
        }

    embeddings = embed_texts(chunks)

    document = Document(
        document_id=upload_metadata["document_id"],
        tenant_id=upload_metadata["tenant_id"],
        repository_id=upload_metadata["repository_id"],
        file_name=upload_metadata["file_name"],
        original_file_name=upload_metadata.get("original_file_name"),
        source_type=upload_metadata["source_type"],
        business_area=upload_metadata["business_area"],
        stored_path=upload_metadata["stored_path"],
        uploaded_by=upload_metadata["uploaded_by"],
        metadata_json=upload_metadata,
    )

    db.add(document)

    for index, chunk_text_value in enumerate(chunks):
        chunk = DocumentChunk(
            chunk_id=f"CHUNK-{str(uuid4())[:12].upper()}",
            document_id=upload_metadata["document_id"],
            tenant_id=upload_metadata["tenant_id"],
            repository_id=upload_metadata["repository_id"],
            business_area=upload_metadata["business_area"],
            file_name=upload_metadata["file_name"],
            chunk_index=index,
            chunk_text=chunk_text_value,
            embedding=embeddings[index],
            metadata_json={
                **upload_metadata,
                "chunk_index": index,
            },
        )
        db.add(chunk)

    db.commit()

    return {
        "success": True,
        "message": "Document indexed into PostgreSQL pgvector",
        "chunks_indexed": len(chunks),
        "document_id": upload_metadata["document_id"],
    }
