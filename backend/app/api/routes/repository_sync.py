import mimetypes

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from urllib.parse import quote

from app.connectors.connector_factory import get_connector
from app.connectors.sharepoint_connector import SharePointGraphConnector
from app.core.database import get_db
from app.core.security import get_current_user, require_saas_access
from app.db_models import ConnectorFile, ConnectorSyncFailure, ConnectorSyncRun, Repository
from app.services.audit_service import create_audit_log
from app.services.connector_cleanup_service import (
    cleanup_old_successful_sync_runs,
    cleanup_resolved_failures,
)
from app.services.connector_health_service import build_connector_health
from app.services.repository_audit_service import build_repository_index_report
from app.services.repository_content_report_service import build_repository_content_report
from app.services.repository_content_report_service import paginate_repository_content_report
from app.services.connector_retry_service import (
    can_retry_failure,
    get_ready_failures,
    mark_failure_resolved,
    mark_failure_retry_attempted,
)
from app.services.connector_scheduler_service import (
    get_connector_scheduler_status,
    update_connector_scheduler_settings,
)
from app.core.config import settings
from app.services.runtime_chunking_settings_service import (
    get_chunking_settings as get_runtime_chunking_settings,
    update_chunking_settings as persist_chunking_settings,
)
from app.services.connector_scheduled_runner_service import (
    run_due_repository_syncs as run_due_repository_syncs_service,
)
from app.services.connector_sync_service import run_repository_sync_by_type
from app.services.symployee_document_service import list_document_identities
from app.services.sharedrive_setup_service import (
    discover_sharedrive_folders,
    discover_sharedrive_roots,
)
from app.services.sharepoint_setup_service import (
    discover_drive_folders,
    discover_drives,
    discover_sites,
)


router = APIRouter(prefix="/api/repositories", tags=["Repository Sync"])


def repo_or_404(db: Session, repository_id: str, current_user: dict) -> Repository:
    repo = (
        db.query(Repository)
        .filter(
            Repository.repository_id == repository_id,
            Repository.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    return repo


def _connector_file_or_404(
    db: Session,
    tenant_id: str,
    repository_id: str,
    connector_file_id: str,
) -> ConnectorFile:
    connector_file = (
        db.query(ConnectorFile)
        .filter(
            ConnectorFile.id == connector_file_id,
            ConnectorFile.tenant_id == tenant_id,
            ConnectorFile.repository_id == repository_id,
            ConnectorFile.is_current_version == True,
        )
        .first()
    )
    if not connector_file:
        raise HTTPException(status_code=404, detail="Repository file not found")
    return connector_file


@router.get("/connector-capabilities")
def get_connector_capabilities(
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
):
    return {
        "sharedrive": {
            "label": "Shared Drive",
            "status": "operational",
            "settings_enabled": True,
            "required_fields": [
                {
                    "key": "root_path",
                    "label": "Root Path",
                    "type": "text",
                    "placeholder": "/mnt/shared/company/sales",
                    "required": True,
                }
            ],
            "message": "Shared Drive connector is operational.",
        },
        "sharepoint": {
            "label": "SharePoint",
            "status": "operational",
            "settings_enabled": True,
            "required_fields": [
                {
                    "key": "tenant_id",
                    "label": "Azure Tenant ID",
                    "type": "text",
                    "required": True,
                },
                {
                    "key": "client_id",
                    "label": "Azure App Client ID",
                    "type": "text",
                    "required": True,
                },
                {
                    "key": "client_secret",
                    "label": "Azure App Client Secret",
                    "type": "password",
                    "required": True,
                },
                {
                    "key": "site_id",
                    "label": "SharePoint Site ID",
                    "type": "text",
                    "required": True,
                },
                {
                    "key": "drive_id",
                    "label": "Document Library Drive ID",
                    "type": "text",
                    "required": True,
                },
                {
                    "key": "folder_path",
                    "label": "Folder Path",
                    "type": "text",
                    "placeholder": "/Sales",
                    "required": False,
                },
            ],
            "message": "SharePoint Graph connector is operational.",
        },
        "otcs": {
            "label": "OTCS",
            "status": "scaffolded",
            "settings_enabled": False,
            "required_fields": [
                {
                    "key": "base_url",
                    "label": "OTCS Base URL",
                    "type": "text",
                    "required": True,
                },
                {
                    "key": "folder_id",
                    "label": "Folder ID",
                    "type": "text",
                    "required": True,
                },
                {
                    "key": "auth_type",
                    "label": "Auth Type",
                    "type": "select",
                    "options": ["token", "basic"],
                    "required": True,
                },
            ],
            "message": "OTCS settings will become active in Sprint 8J.",
        },
    }


@router.patch("/{repository_id}/sync/schedule")
def update_repository_sync_schedule(
    repository_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
):
    repo = repo_or_404(db, repository_id, current_user)

    repo.sync_enabled = bool(payload.get("sync_enabled", True))
    repo.sync_interval_minutes = payload.get("sync_interval_minutes")

    db.commit()
    db.refresh(repo)

    return {
        "repository_id": repo.repository_id,
        "sync_enabled": repo.sync_enabled,
        "sync_interval_minutes": repo.sync_interval_minutes,
    }


@router.post("/sync/run-due")
def run_due_repository_syncs(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
):
    return run_due_repository_syncs_service(
        db=db,
        tenant_id=current_user["tenant_id"],
        started_by=current_user["user_id"],
    )


@router.get("/sync/scheduler/settings")
def get_scheduler_settings(
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
):
    return get_connector_scheduler_status()


@router.patch("/sync/scheduler/settings")
def update_scheduler_settings(
    payload: dict,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
):
    mode = (payload.get("mode") or "embedded").strip().lower()
    interval_minutes = int(payload.get("interval_minutes", 5))
    timezone_name = (payload.get("timezone") or "UTC").strip() or "UTC"

    if mode not in {"embedded", "external", "disabled"}:
        raise HTTPException(
            status_code=400,
            detail="Scheduler mode must be one of: embedded, external, disabled",
        )

    if interval_minutes < 1:
        raise HTTPException(
            status_code=400,
            detail="Scheduler interval_minutes must be at least 1",
        )

    return update_connector_scheduler_settings(
        mode=mode,
        interval_minutes=interval_minutes,
        timezone_name=timezone_name,
    )


@router.get("/chunking/settings")
def get_chunking_settings(
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
):
    data = get_runtime_chunking_settings()
    data["recommended_range"] = {
        "max_chars": {"min": 800, "max": 1500},
        "overlap_chars": {"min": 80, "max": 220},
    }
    return data


@router.patch("/chunking/settings")
def update_chunking_settings(
    payload: dict,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
):
    max_chars = int(payload.get("max_chars", settings.CHUNK_MAX_CHARS))
    overlap_chars = int(payload.get("overlap_chars", settings.CHUNK_OVERLAP_CHARS))

    if max_chars < 200:
        raise HTTPException(
            status_code=400,
            detail="Chunk max_chars must be at least 200",
        )

    if overlap_chars < 0:
        raise HTTPException(
            status_code=400,
            detail="Chunk overlap_chars cannot be negative",
        )

    if overlap_chars >= max_chars:
        raise HTTPException(
            status_code=400,
            detail="Chunk overlap_chars must be smaller than max_chars",
        )

    data = persist_chunking_settings(max_chars=max_chars, overlap_chars=overlap_chars)
    data["message"] = "Chunking settings saved and will persist across backend restart."
    return data


@router.post("/{repository_id}/connector/test")
def test_repository_connector(
    repository_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    repo = repo_or_404(db, repository_id, current_user)

    connector = get_connector(
        {
            "repository_id": repo.repository_id,
            "tenant_id": repo.tenant_id,
            "repository_name": repo.repository_name,
            "source_type": repo.source_type,
            "business_area": repo.business_area,
            "source_path": repo.source_path,
            "connection_config": repo.connection_config or {},
        }
    )

    if not hasattr(connector, "test_connection"):
        return {
            "ok": False,
            "message": "Connector does not support test_connection",
        }

    result = connector.test_connection()

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="CONNECTOR_TESTED",
        event_category="REPOSITORY_SYNC",
        description=f"Connector test executed for repository {repo.repository_name}",
        resource_type="repository",
        resource_id=repo.repository_id,
        request=request,
        metadata={"source_type": repo.source_type, "result": result},
    )

    return result


@router.post("/sharepoint/discover-sites")
def api_discover_sharepoint_sites(
    payload: dict,
    search: str = "",
    current_user: dict = Depends(get_current_user),
):
    _ = current_user
    return discover_sites(payload, search)


@router.post("/sharepoint/discover-drives")
def api_discover_sharepoint_drives(
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    _ = current_user
    return discover_drives(payload)


@router.post("/sharepoint/discover-folders")
def api_discover_sharepoint_folders(
    payload: dict,
    folder_path: str = "/",
    current_user: dict = Depends(get_current_user),
):
    _ = current_user
    return discover_drive_folders(payload, folder_path)


@router.post("/sharepoint/resolve-site")
def resolve_sharepoint_site(
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    _ = current_user

    hostname = (payload.get("hostname") or "").strip()
    site_path = (payload.get("site_path") or "").strip().strip("/")

    if not hostname or not site_path:
        raise HTTPException(
            status_code=400,
            detail="hostname and site_path are required to resolve a SharePoint site",
        )

    connector = SharePointGraphConnector({"connection_config": payload})
    encoded_path = quote(site_path, safe="/")
    url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{encoded_path}"
    data = connector._graph_get_json(url)

    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "display_name": data.get("displayName"),
        "web_url": data.get("webUrl"),
        "site_collection": data.get("siteCollection"),
    }


@router.post("/sharepoint/validate-config")
def api_validate_sharepoint_config(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    connector = SharePointGraphConnector({"connection_config": payload})
    result = connector.test_connection()

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="SHAREPOINT_CONFIG_VALIDATED",
        event_category="REPOSITORY_SYNC",
        description="SharePoint configuration validated",
        resource_type="sharepoint_connector",
        resource_id=payload.get("site_id") or payload.get("drive_id"),
        request=request,
        metadata={
            "site_id": payload.get("site_id"),
            "drive_id": payload.get("drive_id"),
            "auth_method": payload.get("auth_method") or "client_secret",
            "result": result,
        },
    )

    return {
        "ok": True,
        "message": "SharePoint configuration is valid",
        "drive": result,
    }


@router.get("/sharedrive/discover-roots")
def api_discover_sharedrive_roots(
    base_path: str | None = None,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
):
    _ = current_user
    try:
        return discover_sharedrive_roots(base_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/sharedrive/discover-folders")
def api_discover_sharedrive_folders(
    root_path: str,
    folder_path: str | None = None,
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
):
    _ = current_user
    try:
        return discover_sharedrive_folders(root_path, folder_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{repository_id}/sharepoint/reset-delta")
def reset_sharepoint_delta_cursor(
    repository_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    repo = repo_or_404(db, repository_id, current_user)

    if repo.source_type != "sharepoint":
        raise HTTPException(
            status_code=400,
            detail="Delta reset is only available for SharePoint repositories",
        )

    metadata = repo.sync_metadata or {}
    metadata.pop("sharepoint_delta_link", None)
    metadata["sharepoint_delta_initialized"] = False

    config = repo.connection_config or {}
    config.pop("delta_link", None)

    repo.sync_metadata = metadata
    repo.connection_config = config
    db.commit()

    return {
        "message": "SharePoint delta cursor reset. Next sync will perform initial delta crawl.",
        "repository_id": str(repo.repository_id),
    }


@router.get("/{repository_id}/sync/status")
def get_repository_sync_status(
    repository_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    repo = repo_or_404(db, repository_id, current_user)

    return {
        "repository_id": repo.repository_id,
        "repository_name": repo.repository_name,
        "source_type": repo.source_type,
        "last_sync_run_id": repo.last_sync_run_id,
        "last_sync_status": repo.last_sync_status,
        "last_sync_started_at": repo.last_sync_started_at,
        "last_sync_completed_at": repo.last_sync_completed_at,
        "last_sync_error": repo.last_sync_error,
        "sync_enabled": repo.sync_enabled,
        "sync_interval_minutes": repo.sync_interval_minutes,
        "sync_metadata": repo.sync_metadata or {},
    }


@router.get("/{repository_id}/index-report")
def get_repository_index_report(
    repository_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
):
    repo = repo_or_404(db, repository_id, current_user)
    _ = repo

    try:
        return build_repository_index_report(
            db=db,
            tenant_id=current_user["tenant_id"],
            repository_id=repository_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{repository_id}/content-report")
def get_repository_content_report(
    repository_id: str,
    status: str = "all",
    page: int = 1,
    page_size: int = 4,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    repo_or_404(db, repository_id, current_user)
    try:
        report = build_repository_content_report(
            db=db,
            tenant_id=current_user["tenant_id"],
            repository_id=repository_id,
        )
        return paginate_repository_content_report(
            report,
            status_filter=status,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{repository_id}/files/{connector_file_id}/content")
def open_repository_file(
    repository_id: str,
    connector_file_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    repo = repo_or_404(db, repository_id, current_user)
    connector_file = _connector_file_or_404(
        db,
        current_user["tenant_id"],
        repository_id,
        connector_file_id,
    )

    connector = get_connector(
        {
            "repository_id": repo.repository_id,
            "tenant_id": repo.tenant_id,
            "repository_name": repo.repository_name,
            "source_type": repo.source_type,
            "business_area": repo.business_area,
            "connection_config": repo.connection_config or {},
            "source_path": repo.source_path,
        }
    )

    source_file = {
        "external_file_id": connector_file.external_file_id,
        "file_name": connector_file.file_name,
        "file_path": connector_file.file_path,
        "is_deleted": connector_file.is_deleted,
        "metadata": connector_file.metadata_json or {},
    }

    try:
        content = connector.get_file_content(source_file)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    media_type = (
        (connector_file.metadata_json or {}).get("mime_type")
        or mimetypes.guess_type(connector_file.file_name)[0]
        or "application/octet-stream"
    )
    filename = quote(connector_file.file_name)

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{filename}",
        },
    )


@router.get("/{repository_id}/sync/health")
def get_repository_sync_health(
    repository_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    repo = repo_or_404(db, repository_id, current_user)
    return build_connector_health(repo)


@router.get("/{repository_id}/symployee-summary")
def get_repository_symployee_summary(
    repository_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    repo = repo_or_404(db, repository_id, current_user)
    data = list_document_identities(db, current_user["tenant_id"], limit=500)
    repo_items = [
        item
        for item in data["items"]
        if item.get("repository_id") == repo.repository_id
    ]
    return {
        "repository_id": repo.repository_id,
        "repository_name": repo.repository_name,
        "symployee_documents": len(repo_items),
        "items": repo_items,
    }


@router.post("/sync/cleanup")
def cleanup_connector_sync_records(
    keep_successful_runs_days: int = 90,
    keep_resolved_failures_days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("settings", "admin:users")),
):
    deleted_runs = cleanup_old_successful_sync_runs(
        db=db,
        tenant_id=current_user["tenant_id"],
        keep_days=keep_successful_runs_days,
    )

    deleted_failures = cleanup_resolved_failures(
        db=db,
        tenant_id=current_user["tenant_id"],
        keep_days=keep_resolved_failures_days,
    )

    return {
        "message": "Connector sync cleanup completed",
        "deleted_successful_sync_runs": deleted_runs,
        "deleted_resolved_failures": deleted_failures,
    }


@router.get("/{repository_id}/sync/history")
def get_repository_sync_history(
    repository_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    repo = repo_or_404(db, repository_id, current_user)

    runs = (
        db.query(ConnectorSyncRun)
        .filter(
            ConnectorSyncRun.tenant_id == current_user["tenant_id"],
            ConnectorSyncRun.repository_id == repo.repository_id,
        )
        .order_by(ConnectorSyncRun.sync_started_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": run.id,
            "source_type": run.source_type,
            "sync_status": run.sync_status,
            "sync_mode": run.sync_mode,
            "sync_started_at": run.sync_started_at,
            "sync_completed_at": run.sync_completed_at,
            "files_discovered": run.files_discovered,
            "files_processed": run.files_processed,
            "files_skipped": run.files_skipped,
            "files_failed": run.files_failed,
            "files_deleted": run.files_deleted,
            "chunks_created": run.chunks_created,
            "embeddings_created": run.embeddings_created,
            "error_message": run.error_message,
        }
        for run in runs
    ]


@router.get("/{repository_id}/sync/runs/{sync_run_id}")
def get_sync_run_detail(
    repository_id: str,
    sync_run_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    repo = repo_or_404(db, repository_id, current_user)

    run = (
        db.query(ConnectorSyncRun)
        .filter(
            ConnectorSyncRun.id == sync_run_id,
            ConnectorSyncRun.tenant_id == current_user["tenant_id"],
            ConnectorSyncRun.repository_id == repo.repository_id,
        )
        .first()
    )

    if not run:
        raise HTTPException(status_code=404, detail="Sync run not found")

    failures = (
        db.query(ConnectorSyncFailure)
        .filter(
            ConnectorSyncFailure.sync_run_id == run.id,
            ConnectorSyncFailure.tenant_id == current_user["tenant_id"],
        )
        .order_by(ConnectorSyncFailure.created_at.desc())
        .all()
    )

    return {
        "id": run.id,
        "status": run.sync_status,
        "started_at": run.sync_started_at,
        "completed_at": run.sync_completed_at,
        "files_discovered": run.files_discovered,
        "files_processed": run.files_processed,
        "files_skipped": run.files_skipped,
        "files_failed": run.files_failed,
        "files_deleted": run.files_deleted,
        "chunks_created": run.chunks_created,
        "embeddings_created": run.embeddings_created,
        "error_message": run.error_message,
        "failures": [
            {
                "id": failure.id,
                "file_name": failure.file_name,
                "file_path": failure.file_path,
                "failure_stage": failure.failure_stage,
                "error_message": failure.error_message,
                "retry_count": failure.retry_count,
                "resolved": failure.resolved,
                "created_at": failure.created_at,
            }
            for failure in failures
        ],
    }


@router.get("/{repository_id}/sync/failures")
def get_repository_sync_failures(
    repository_id: str,
    resolved: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    repo = repo_or_404(db, repository_id, current_user)

    failures = (
        db.query(ConnectorSyncFailure)
        .filter(
            ConnectorSyncFailure.tenant_id == current_user["tenant_id"],
            ConnectorSyncFailure.repository_id == repo.repository_id,
            ConnectorSyncFailure.resolved == resolved,
        )
        .order_by(ConnectorSyncFailure.created_at.desc())
        .all()
    )

    return [
        {
            "id": failure.id,
            "sync_run_id": failure.sync_run_id,
            "connector_file_id": failure.connector_file_id,
            "external_file_id": failure.external_file_id,
            "file_name": failure.file_name,
            "file_path": failure.file_path,
            "failure_stage": failure.failure_stage,
            "error_message": failure.error_message,
            "retry_count": failure.retry_count,
            "max_retries": failure.max_retries,
            "last_retry_at": failure.last_retry_at,
            "next_retry_at": failure.next_retry_at,
            "resolved": failure.resolved,
            "created_at": failure.created_at,
        }
        for failure in failures
    ]


@router.get("/{repository_id}/sync/logs")
def get_repository_sync_logs(
    repository_id: str,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    repo = repo_or_404(db, repository_id, current_user)

    files = (
        db.query(ConnectorFile)
        .filter(
            ConnectorFile.tenant_id == current_user["tenant_id"],
            ConnectorFile.repository_id == repo.repository_id,
        )
        .order_by(ConnectorFile.last_synced_at.desc().nullslast())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": file.id,
            "external_file_id": file.external_file_id,
            "file_name": file.file_name,
            "file_path": file.file_path,
            "sync_status": file.sync_status,
            "version_number": file.version_number,
            "is_current_version": file.is_current_version,
            "is_deleted": file.is_deleted,
            "file_size": file.file_size,
            "source_modified_at": file.source_modified_at,
            "last_synced_at": file.last_synced_at,
            "retry_count": file.retry_count,
            "last_error_message": file.last_error_message,
            "document_id": file.document_id,
        }
        for file in files
    ]


@router.post("/{repository_id}/sync/retry-ready")
def retry_ready_failures_for_repository(
    repository_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
):
    repo = repo_or_404(db, repository_id, current_user)

    failures = get_ready_failures(
        db=db,
        tenant_id=current_user["tenant_id"],
        repository_id=repo.repository_id,
    )

    if not failures:
        return {
            "message": "No retry-ready failures found",
            "retried": 0,
        }

    connector = get_connector(
        {
            "repository_id": repo.repository_id,
            "tenant_id": repo.tenant_id,
            "repository_name": repo.repository_name,
            "source_type": repo.source_type,
            "business_area": repo.business_area,
            "source_path": repo.source_path,
            "connection_config": repo.connection_config or {},
        }
    )

    for failure in failures:
        allowed, _reason = can_retry_failure(failure)

        if not allowed:
            continue

        mark_failure_retry_attempted(db, failure)

    sync_run = run_repository_sync_by_type(
        db=db,
        tenant_id=current_user["tenant_id"],
        repository=repo,
        connector=connector,
        started_by=current_user["user_id"],
        sync_mode="retry",
    )

    for failure in failures:
        mark_failure_resolved(db, failure)

    return {
        "message": "Retry-ready failures processed",
        "retried": len(failures),
        "sync_run_id": sync_run.id,
        "status": sync_run.sync_status,
    }


@router.get("/{repository_id}/files/{external_file_id}/versions")
def get_file_versions(
    repository_id: str,
    external_file_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
):
    repo = repo_or_404(db, repository_id, current_user)

    versions = (
        db.query(ConnectorFile)
        .filter(
            ConnectorFile.tenant_id == current_user["tenant_id"],
            ConnectorFile.repository_id == repo.repository_id,
            ConnectorFile.external_file_id == external_file_id,
        )
        .order_by(ConnectorFile.version_number.desc())
        .all()
    )

    return [
        {
            "id": version.id,
            "external_file_id": version.external_file_id,
            "file_name": version.file_name,
            "file_path": version.file_path,
            "file_hash": version.file_hash,
            "version_number": version.version_number,
            "is_current_version": version.is_current_version,
            "is_deleted": version.is_deleted,
            "source_modified_at": version.source_modified_at,
            "last_synced_at": version.last_synced_at,
            "document_id": version.document_id,
            "sync_status": version.sync_status,
        }
        for version in versions
    ]


@router.post("/{repository_id}/sync/failures/{failure_id}/retry")
def retry_failed_file(
    repository_id: str,
    failure_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
):
    repo = repo_or_404(db, repository_id, current_user)

    failure = (
        db.query(ConnectorSyncFailure)
        .filter(
            ConnectorSyncFailure.id == failure_id,
            ConnectorSyncFailure.tenant_id == current_user["tenant_id"],
            ConnectorSyncFailure.repository_id == repo.repository_id,
            ConnectorSyncFailure.resolved == False,
        )
        .first()
    )

    if not failure:
        raise HTTPException(status_code=404, detail="Failure not found")

    allowed, reason = can_retry_failure(failure)

    if not allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Failure is not ready for retry: {reason}",
        )

    connector_file = None
    if failure.connector_file_id:
        connector_file = (
            db.query(ConnectorFile)
            .filter(
                ConnectorFile.id == failure.connector_file_id,
                ConnectorFile.tenant_id == current_user["tenant_id"],
            )
            .first()
        )

    mark_failure_retry_attempted(db, failure)

    connector = get_connector(
        {
            "repository_id": repo.repository_id,
            "tenant_id": repo.tenant_id,
            "repository_name": repo.repository_name,
            "source_type": repo.source_type,
            "business_area": repo.business_area,
            "source_path": repo.source_path,
            "connection_config": repo.connection_config or {},
        }
    )

    sync_run = run_repository_sync_by_type(
        db=db,
        tenant_id=current_user["tenant_id"],
        repository=repo,
        connector=connector,
        started_by=current_user["user_id"],
        sync_mode="retry",
    )

    mark_failure_resolved(db, failure)

    return {
        "message": "Retry sync triggered",
        "sync_run_id": sync_run.id,
        "status": sync_run.sync_status,
    }
