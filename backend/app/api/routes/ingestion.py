from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_saas_access
from app.models.ingestion_models import RepositoryRebuildRequest
from app.services.ingestion_service import rebuild_index
from app.services.audit_service import create_audit_log
from app.services.pgvector_indexing_service import index_document_pgvector
from app.services.repository_service import get_repository
from app.services.repository_ingestion_service import (
    get_repository_upload_dir,
    save_repository_upload,
)
from app.services.subscription_service import (
    add_storage_usage,
    refresh_tenant_usage_counts,
    validate_usage_limit,
)

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


class RebuildRequest(BaseModel):
    datasource: str | None = None
    repository_id: str | None = None


@router.post("/upload")
async def upload_repository_document(
    request: Request,
    repository_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(
        require_saas_access("documents", "documents:upload")
    ),
    db: Session = Depends(get_db),
):
    validate_usage_limit(current_user["tenant_id"], "documents", db)
    validate_usage_limit(current_user["tenant_id"], "storage", db)

    metadata = await save_repository_upload(
        repository_id=repository_id,
        file=file,
        current_user=current_user,
        db=db,
    )
    index_result = index_document_pgvector(metadata, db)

    add_storage_usage(
        current_user["tenant_id"],
        metadata.get("file_size_bytes", 0),
        db,
    )
    refresh_tenant_usage_counts(current_user["tenant_id"], db)

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="DOCUMENT_UPLOADED",
        event_category="DOCUMENT",
        description=f"Document uploaded and indexed: {metadata.get('original_file_name')}",
        resource_type="document",
        resource_id=metadata["document_id"],
        request=request,
        metadata={
            "repository_id": metadata["repository_id"],
            "business_area": metadata["business_area"],
            "file_name": metadata.get("original_file_name"),
            "chunks_indexed": index_result.get("chunks_indexed"),
            "file_size_mb": metadata.get("file_size_mb"),
        },
    )

    return {
        "success": True,
        "message": "File uploaded and indexed into PostgreSQL pgvector",
        "upload": metadata,
        "indexing": index_result,
    }


@router.post("/rebuild")
def rebuild_index_route(
    payload: RebuildRequest,
    current_user: dict = Depends(
        require_saas_access("documents", "documents:upload")
    ),
):
    try:
        return rebuild_index(
            datasource=payload.datasource,
            current_user=current_user,
            repository_id=payload.repository_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=410, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/rebuild/repository")
def rebuild_repository_index(
    payload: RepositoryRebuildRequest,
    current_user: dict = Depends(
        require_saas_access("documents", "documents:upload")
    ),
):
    repository = get_repository(payload.repository_id, current_user)["data"]

    if repository.get("source_type") == "sharedrive" and repository.get("source_path"):
        repository_dir = repository["source_path"]
    else:
        repository_dir = str(
            get_repository_upload_dir(
                current_user["tenant_id"],
                payload.repository_id,
            )
        )

    try:
        return rebuild_index(
            datasource=str(repository_dir),
            current_user=current_user,
            repository_id=payload.repository_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=410, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/upload/pgvector")
async def upload_repository_document_pgvector(
    repository_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(
        require_saas_access("documents", "documents:upload")
    ),
    db: Session = Depends(get_db),
):
    validate_usage_limit(current_user["tenant_id"], "documents", db)
    validate_usage_limit(current_user["tenant_id"], "storage", db)

    metadata = await save_repository_upload(
        repository_id=repository_id,
        file=file,
        current_user=current_user,
        db=db,
    )
    result = index_document_pgvector(metadata, db)

    add_storage_usage(
        current_user["tenant_id"],
        metadata.get("file_size_bytes", 0),
        db,
    )
    refresh_tenant_usage_counts(current_user["tenant_id"], db)

    return {
        "success": True,
        "message": "File uploaded and indexed into PostgreSQL pgvector",
        "upload": metadata,
        "indexing": result,
    }
