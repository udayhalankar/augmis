from fastapi import HTTPException, status
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.db_models import Repository, RepositoryAccess
from app.db_models import ConnectorFile, ConnectorSyncFailure, ConnectorSyncRun, Document, DocumentChunk
from app.models.repository_models import (
    RepositoryAccessCreateRequest,
    RepositoryAccessUpdateRequest,
    RepositoryConnectionUpdateRequest,
    RepositoryCreateRequest,
    new_access_id,
    new_repository_id,
)
from app.services.sharedrive_setup_service import _normalize_sharedrive_path


REDACTED_VALUE = "__redacted__"
SENSITIVE_CONNECTION_FIELDS = {
    "sharepoint": {
        "client_secret",
        "client_secret_env",
        "certificate_private_key",
        "certificate_private_key_env",
        "certificate_private_key_path",
        "certificate_passphrase",
        "certificate_passphrase_env",
    }
}
PLAINTEXT_SHAREPOINT_SECRET_FIELDS = {
    "client_secret",
    "certificate_private_key",
    "certificate_passphrase",
}


def _derive_business_area_from_repository_name(repository_name: str | None) -> str:
    raw = str(repository_name or "").strip().lower()
    normalized = raw.replace("_", " ").replace("-", " ")
    normalized = " ".join(normalized.split())
    return normalized or "general"


def _is_tenant_admin(current_user: dict):
    return current_user.get("role") in ["SUPER_ADMIN", "TENANT_ADMIN"]


def _is_missing_repository_sync_columns(error: Exception) -> bool:
    message = str(error)
    return (
        "repositories.connection_config does not exist" in message
        or "repositories.sync_status does not exist" in message
        or "repositories.last_sync_at does not exist" in message
    )


def _redact_connection_config(source_type: str, config: dict | None) -> dict:
    redacted = dict(config or {})
    sensitive_fields = SENSITIVE_CONNECTION_FIELDS.get(source_type, set())

    for field in sensitive_fields:
        if redacted.get(field):
            redacted[field] = REDACTED_VALUE

    return redacted


def _merge_connection_config(source_type: str, existing: dict | None, incoming: dict | None) -> dict:
    merged = dict(existing or {})
    incoming = incoming or {}
    sensitive_fields = SENSITIVE_CONNECTION_FIELDS.get(source_type, set())

    for key, value in incoming.items():
        if key in sensitive_fields:
            if value == REDACTED_VALUE:
                continue

            if value in ("", None):
                merged.pop(key, None)
                continue

            merged[key] = value
            continue

        if value is None:
            merged.pop(key, None)
            continue

        merged[key] = value

    return merged


def _validate_sharepoint_secret_policy(config: dict | None):
    config = config or {}
    forbidden_fields = [
        field
        for field in PLAINTEXT_SHAREPOINT_SECRET_FIELDS
        if config.get(field) not in (None, "", REDACTED_VALUE)
    ]

    if forbidden_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "SharePoint config must use secret-manager or file/env references. "
                f"Do not persist raw values for: {', '.join(sorted(forbidden_fields))}."
            ),
        )


def _normalize_sharedrive_connection(
    source_path: str | None,
    connection_config: dict | None,
) -> tuple[str | None, dict]:
    normalized_config = dict(connection_config or {})
    normalized_root = str(normalized_config.get("root_path") or "").strip() or None
    normalized_source = (source_path or "").strip() or None

    root_path = None
    if normalized_root:
        root_path = _normalize_sharedrive_path(normalized_root, require_absolute=True)
        normalized_root = str(root_path)
        normalized_config["root_path"] = normalized_root

    resolved_path = None
    if normalized_source:
        source_path_obj = _normalize_sharedrive_path(normalized_source)
        if source_path_obj.is_absolute():
            resolved_path = source_path_obj
        elif root_path is not None:
            resolved_path = _normalize_sharedrive_path(normalized_source, root_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shared Drive source_path must be absolute or relative to a configured root_path",
            )
    elif root_path is not None:
        resolved_path = root_path

    if resolved_path is not None:
        normalized_config["root_path"] = normalized_root or str(resolved_path)

    return str(resolved_path) if resolved_path is not None else None, normalized_config


def serialize_repository(repo: Repository) -> dict:
    effective_sync_status = repo.last_sync_status or repo.sync_status
    effective_last_sync_at = repo.last_sync_completed_at or repo.last_sync_at

    return {
        "repository_id": repo.repository_id,
        "tenant_id": repo.tenant_id,
        "repository_name": repo.repository_name,
        "source_type": repo.source_type,
        "business_area": repo.business_area,
        "status": repo.status,
        "source_path": repo.source_path,
        "created_by": repo.created_by,
        "created_at": repo.created_at.isoformat() if repo.created_at else None,
        "connection_config": _redact_connection_config(
            repo.source_type,
            repo.connection_config,
        ),
        "sync_status": effective_sync_status,
        "last_sync_at": effective_last_sync_at.isoformat() if effective_last_sync_at else None,
        "last_sync_error": repo.last_sync_error,
        "sync_metadata": repo.sync_metadata or {},
        "legacy_sync_status": repo.sync_status,
        "last_sync_status": repo.last_sync_status,
    }


def _access_to_dict(access: RepositoryAccess) -> dict:
    return {
        "access_id": access.access_id,
        "tenant_id": access.tenant_id,
        "repository_id": access.repository_id,
        "user_id": access.user_id,
        "can_read": access.can_read,
        "can_ingest": access.can_ingest,
        "can_admin": access.can_admin,
        "business_area": access.business_area,
    }


def list_repositories(current_user: dict):
    db = SessionLocal()
    try:
        try:
            repositories = (
                db.query(Repository)
                .filter(Repository.tenant_id == current_user["tenant_id"])
                .all()
            )
        except ProgrammingError as exc:
            db.rollback()
            if not _is_missing_repository_sync_columns(exc):
                raise

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Repository schema upgrade pending. Run init_db.py and restart the backend.",
            )

        return {
            "success": True,
            "data": [serialize_repository(repo) for repo in repositories],
        }
    finally:
        db.close()


def create_repository(
    payload: RepositoryCreateRequest,
    current_user: dict,
    db: Session | None = None,
):
    should_close = db is None
    if db is None:
        db = SessionLocal()
    try:
        if not _is_tenant_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only tenant admins can create repositories",
            )

        if payload.source_type == "sharedrive" and not (payload.source_path or "").strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shared Drive repositories require a folder path",
            )

        if payload.source_type == "sharepoint":
            _validate_sharepoint_secret_policy(payload.connection_config)

        source_path = (payload.source_path or "").strip() or None
        connection_config = payload.connection_config or {}
        business_area = str(payload.business_area or "").strip().lower()
        if not business_area:
            business_area = _derive_business_area_from_repository_name(payload.repository_name)
        if payload.source_type == "sharedrive":
            source_path, connection_config = _normalize_sharedrive_connection(
                source_path,
                connection_config,
            )

        repo = Repository(
            repository_id=new_repository_id(),
            tenant_id=current_user["tenant_id"],
            repository_name=payload.repository_name,
            source_type=payload.source_type,
            business_area=business_area,
            status=payload.status,
            source_path=source_path,
            connection_config=connection_config,
            sync_status="NOT_SYNCED",
            last_sync_at=None,
            created_by=current_user["user_id"],
        )
        db.add(repo)

        access = RepositoryAccess(
            access_id=new_access_id(),
            tenant_id=current_user["tenant_id"],
            repository_id=repo.repository_id,
            user_id=current_user["user_id"],
            can_read=True,
            can_ingest=True,
            can_admin=True,
            business_area=business_area,
        )
        db.add(access)
        db.commit()
        db.refresh(repo)

        return {
            "success": True,
            "data": serialize_repository(repo),
        }
    finally:
        if should_close:
            db.close()


def get_repository(repository_id: str, current_user: dict):
    db = SessionLocal()
    try:
        repo = (
            db.query(Repository)
            .filter(
                Repository.repository_id == repository_id,
                Repository.tenant_id == current_user["tenant_id"],
            )
            .first()
        )

        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found",
            )

        return {
            "success": True,
            "data": serialize_repository(repo),
        }
    finally:
        db.close()


def list_repository_access(repository_id: str, current_user: dict):
    db = SessionLocal()
    try:
        repo = (
            db.query(Repository)
            .filter(
                Repository.repository_id == repository_id,
                Repository.tenant_id == current_user["tenant_id"],
            )
            .first()
        )
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found",
            )

        if not _is_tenant_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only tenant admins can view repository access",
            )

        rows = (
            db.query(RepositoryAccess)
            .filter(
                RepositoryAccess.tenant_id == current_user["tenant_id"],
                RepositoryAccess.repository_id == repo.repository_id,
            )
            .all()
        )

        return {
            "success": True,
            "data": [_access_to_dict(row) for row in rows],
        }
    finally:
        db.close()


def grant_repository_access(
    payload: RepositoryAccessCreateRequest,
    current_user: dict,
    db: Session | None = None,
):
    should_close = db is None
    if db is None:
        db = SessionLocal()
    try:
        if not _is_tenant_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only tenant admins can grant repository access",
            )

        repo = (
            db.query(Repository)
            .filter(
                Repository.repository_id == payload.repository_id,
                Repository.tenant_id == current_user["tenant_id"],
            )
            .first()
        )
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found",
            )

        existing = (
            db.query(RepositoryAccess)
            .filter(
                RepositoryAccess.tenant_id == current_user["tenant_id"],
                RepositoryAccess.repository_id == payload.repository_id,
                RepositoryAccess.user_id == payload.user_id,
            )
            .first()
        )
        if existing:
            db.delete(existing)
            db.flush()

        access = RepositoryAccess(
            access_id=new_access_id(),
            tenant_id=current_user["tenant_id"],
            repository_id=payload.repository_id,
            user_id=payload.user_id,
            can_read=payload.can_read,
            can_ingest=payload.can_ingest,
            can_admin=payload.can_admin,
            business_area=payload.business_area or repo.business_area,
        )
        db.add(access)
        db.commit()
        db.refresh(access)

        return {
            "success": True,
            "data": _access_to_dict(access),
        }
    finally:
        if should_close:
            db.close()


def update_repository_access(
    access_id: str,
    payload: RepositoryAccessUpdateRequest,
    current_user: dict,
):
    db = SessionLocal()
    try:
        if not _is_tenant_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only tenant admins can update repository access",
            )

        access = (
            db.query(RepositoryAccess)
            .filter(
                RepositoryAccess.access_id == access_id,
                RepositoryAccess.tenant_id == current_user["tenant_id"],
            )
            .first()
        )
        if not access:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository access record not found",
            )

        access.can_read = payload.can_read
        access.can_ingest = payload.can_ingest
        access.can_admin = payload.can_admin
        access.business_area = payload.business_area or access.business_area
        db.commit()
        db.refresh(access)

        return {
            "success": True,
            "data": _access_to_dict(access),
        }
    finally:
        db.close()


def update_repository_connection(
    repository_id: str,
    payload: RepositoryConnectionUpdateRequest,
    current_user: dict,
    db: Session,
):
    if not _is_tenant_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenant admins can update repository connections",
        )

    repo = (
        db.query(Repository)
        .filter(
            Repository.repository_id == repository_id,
            Repository.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    if repo.source_type == "sharepoint":
        _validate_sharepoint_secret_policy(payload.connection_config)

    requested_business_area = (
        str(payload.business_area or "").strip().lower()
        if payload.business_area is not None
        else ""
    )
    if payload.business_area is not None and not requested_business_area:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business area is required",
        )

    merged_connection_config = _merge_connection_config(
        repo.source_type,
        repo.connection_config,
        payload.connection_config,
    )
    if repo.source_type == "sharedrive":
        requested_source_path = (
            (payload.source_path or "").strip()
            if payload.source_path is not None
            else repo.source_path
        )
        normalized_source_path, merged_connection_config = _normalize_sharedrive_connection(
            requested_source_path,
            merged_connection_config,
        )
        if not normalized_source_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shared Drive repositories require a folder path",
            )
        repo.source_path = normalized_source_path

    if requested_business_area:
        repo.business_area = requested_business_area
        (
            db.query(RepositoryAccess)
            .filter(
                RepositoryAccess.tenant_id == current_user["tenant_id"],
                RepositoryAccess.repository_id == repository_id,
            )
            .update({"business_area": requested_business_area}, synchronize_session=False)
        )

    repo.connection_config = merged_connection_config
    repo.sync_status = "NOT_SYNCED"
    repo.last_sync_at = None

    db.commit()
    db.refresh(repo)

    return {
        "success": True,
        "data": serialize_repository(repo),
    }


def disconnect_repository(
    repository_id: str,
    current_user: dict,
    db: Session,
):
    if not _is_tenant_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenant admins can disconnect repositories",
        )

    repo = (
        db.query(Repository)
        .filter(
            Repository.repository_id == repository_id,
            Repository.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    repo.connection_config = {}
    repo.sync_enabled = False
    repo.sync_status = "DISCONNECTED"
    repo.last_sync_at = None
    repo.last_sync_run_id = None
    repo.last_sync_status = None
    repo.last_sync_started_at = None
    repo.last_sync_completed_at = None
    repo.last_sync_error = None
    repo.sync_cursor = None
    repo.sync_metadata = {}

    db.commit()
    db.refresh(repo)

    return {
        "success": True,
        "data": serialize_repository(repo),
    }


def delete_repository(
    repository_id: str,
    current_user: dict,
    db: Session,
):
    if not _is_tenant_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenant admins can remove repositories",
        )

    repo = (
        db.query(Repository)
        .filter(
            Repository.repository_id == repository_id,
            Repository.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    db.query(ConnectorSyncFailure).filter(
        ConnectorSyncFailure.tenant_id == current_user["tenant_id"],
        ConnectorSyncFailure.repository_id == repository_id,
    ).delete(synchronize_session=False)

    db.query(ConnectorFile).filter(
        ConnectorFile.tenant_id == current_user["tenant_id"],
        ConnectorFile.repository_id == repository_id,
    ).delete(synchronize_session=False)

    db.query(ConnectorSyncRun).filter(
        ConnectorSyncRun.tenant_id == current_user["tenant_id"],
        ConnectorSyncRun.repository_id == repository_id,
    ).delete(synchronize_session=False)

    db.query(DocumentChunk).filter(
        DocumentChunk.tenant_id == current_user["tenant_id"],
        DocumentChunk.repository_id == repository_id,
    ).delete(synchronize_session=False)

    db.query(Document).filter(
        Document.tenant_id == current_user["tenant_id"],
        Document.repository_id == repository_id,
    ).delete(synchronize_session=False)

    db.query(RepositoryAccess).filter(
        RepositoryAccess.tenant_id == current_user["tenant_id"],
        RepositoryAccess.repository_id == repository_id,
    ).delete(synchronize_session=False)

    db.delete(repo)
    db.commit()

    return {
        "success": True,
        "deleted": 1,
        "repository_id": repository_id,
    }


def reset_repository_index_data(
    repository_id: str,
    current_user: dict,
    db: Session,
):
    if not _is_tenant_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenant admins can reindex repositories",
        )

    repo = (
        db.query(Repository)
        .filter(
            Repository.repository_id == repository_id,
            Repository.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    deleted_failures = (
        db.query(ConnectorSyncFailure)
        .filter(
            ConnectorSyncFailure.tenant_id == current_user["tenant_id"],
            ConnectorSyncFailure.repository_id == repository_id,
        )
        .delete(synchronize_session=False)
    )

    deleted_files = (
        db.query(ConnectorFile)
        .filter(
            ConnectorFile.tenant_id == current_user["tenant_id"],
            ConnectorFile.repository_id == repository_id,
        )
        .delete(synchronize_session=False)
    )

    deleted_runs = (
        db.query(ConnectorSyncRun)
        .filter(
            ConnectorSyncRun.tenant_id == current_user["tenant_id"],
            ConnectorSyncRun.repository_id == repository_id,
        )
        .delete(synchronize_session=False)
    )

    deleted_chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.tenant_id == current_user["tenant_id"],
            DocumentChunk.repository_id == repository_id,
        )
        .delete(synchronize_session=False)
    )

    deleted_documents = (
        db.query(Document)
        .filter(
            Document.tenant_id == current_user["tenant_id"],
            Document.repository_id == repository_id,
        )
        .delete(synchronize_session=False)
    )

    repo.sync_status = "NOT_SYNCED"
    repo.last_sync_at = None
    repo.last_sync_run_id = None
    repo.last_sync_status = None
    repo.last_sync_started_at = None
    repo.last_sync_completed_at = None
    repo.last_sync_error = None
    repo.sync_cursor = None
    repo.sync_metadata = {}

    db.commit()
    db.refresh(repo)

    return {
        "success": True,
        "repository_id": repository_id,
        "deleted_connector_files": deleted_files,
        "deleted_documents": deleted_documents,
        "deleted_chunks": deleted_chunks,
        "deleted_sync_runs": deleted_runs,
        "deleted_failures": deleted_failures,
        "repository": serialize_repository(repo),
    }


def delete_repository_access(access_id: str, current_user: dict):
    db = SessionLocal()
    try:
        if not _is_tenant_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only tenant admins can delete repository access",
            )

        access = (
            db.query(RepositoryAccess)
            .filter(
                RepositoryAccess.access_id == access_id,
                RepositoryAccess.tenant_id == current_user["tenant_id"],
            )
            .first()
        )
        if not access:
            return {
                "success": True,
                "deleted": 0,
            }

        db.delete(access)
        db.commit()

        return {
            "success": True,
            "deleted": 1,
        }
    finally:
        db.close()


def get_user_repository_access(current_user: dict):
    db = SessionLocal()
    try:
        tenant_repos = {
            repo.repository_id: repo
            for repo in db.query(Repository)
            .filter(
                Repository.tenant_id == current_user["tenant_id"],
                Repository.status == "ACTIVE",
            )
            .all()
        }

        rows = (
            db.query(RepositoryAccess)
            .filter(
                RepositoryAccess.tenant_id == current_user["tenant_id"],
                RepositoryAccess.user_id == current_user["user_id"],
            )
            .all()
        )

        return {
            "success": True,
            "data": [
                {
                    **_access_to_dict(row),
                    "repository": serialize_repository(tenant_repos[row.repository_id])
                    if row.repository_id in tenant_repos
                    else None,
                }
                for row in rows
                if row.repository_id in tenant_repos
            ],
        }
    finally:
        db.close()


def get_allowed_repository_ids(current_user: dict, permission_type: str = "read"):
    access_rows = get_user_repository_access(current_user)["data"]

    flag_map = {
        "read": "can_read",
        "ingest": "can_ingest",
        "admin": "can_admin",
    }
    flag = flag_map.get(permission_type, "can_read")

    return [
        row["repository_id"]
        for row in access_rows
        if row.get(flag) is True
    ]


def get_tenant_repository_ids(current_user: dict):
    db = SessionLocal()
    try:
        repos = (
            db.query(Repository.repository_id)
            .filter(
                Repository.tenant_id == current_user["tenant_id"],
                Repository.status == "ACTIVE",
            )
            .all()
        )
        return [row.repository_id for row in repos]
    finally:
        db.close()


def get_allowed_business_areas(current_user: dict, permission_type: str = "read"):
    access_rows = get_user_repository_access(current_user)["data"]

    flag_map = {
        "read": "can_read",
        "ingest": "can_ingest",
        "admin": "can_admin",
    }
    flag = flag_map.get(permission_type, "can_read")

    areas = [
        row.get("business_area")
        for row in access_rows
        if row.get(flag) is True and row.get("business_area")
    ]

    return sorted(list(set(areas)))
