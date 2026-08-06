from fastapi import HTTPException, status

from app.services.repository_service import (
    get_allowed_repository_ids,
    get_repository,
)


def build_ingestion_metadata(
    repository_id: str,
    current_user: dict,
    file_name: str,
    source_path: str | None = None,
):
    allowed_ingest_repos = get_allowed_repository_ids(
        current_user,
        permission_type="ingest",
    )

    if repository_id not in allowed_ingest_repos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have ingestion access to this repository",
        )

    repo = get_repository(repository_id, current_user)["data"]

    return {
        "tenant_id": current_user["tenant_id"],
        "repository_id": repo["repository_id"],
        "repository_name": repo["repository_name"],
        "source_type": repo["source_type"],
        "business_area": repo["business_area"],
        "file_name": file_name,
        "source_path": source_path or file_name,
        "uploaded_by": current_user["user_id"],
    }
