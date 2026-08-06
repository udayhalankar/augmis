import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.services.secure_ingestion_context import build_ingestion_metadata


UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploaded_files"


def get_repository_upload_dir(tenant_id: str, repository_id: str) -> Path:
    return UPLOAD_ROOT / tenant_id / repository_id


async def save_repository_upload(
    repository_id: str,
    file: UploadFile,
    current_user: dict,
    db: Session | None = None,
):
    metadata = build_ingestion_metadata(
        repository_id=repository_id,
        current_user=current_user,
        file_name=file.filename,
        source_path=file.filename,
    )

    tenant_dir = get_repository_upload_dir(current_user["tenant_id"], repository_id)
    tenant_dir.mkdir(parents=True, exist_ok=True)

    safe_file_name = (file.filename or "uploaded_file").replace("/", "_").replace("\\", "_")
    stored_file_name = f"{uuid4()}_{safe_file_name}"
    stored_path = tenant_dir / stored_file_name

    with stored_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size_bytes = stored_path.stat().st_size

    metadata.update(
        {
            "document_id": f"DOC-{str(uuid4())[:8].upper()}",
            "stored_path": str(stored_path),
            "original_file_name": file.filename,
            "uploaded_at": datetime.utcnow().isoformat(),
            "file_size_bytes": file_size_bytes,
            "file_size_mb": round(file_size_bytes / (1024 * 1024), 4),
        }
    )

    return metadata


def attach_repository_metadata_to_chunks(
    chunks: list[str],
    base_metadata: dict,
):
    enriched = []

    for index, chunk in enumerate(chunks):
        chunk_id = f"CHUNK-{str(uuid4())[:12].upper()}"
        enriched.append(
            {
                "id": chunk_id,
                "text": chunk,
                "metadata": {
                    **base_metadata,
                    "chunk_index": index,
                    "chunk_id": chunk_id,
                },
            }
        )

    return enriched
