from sqlalchemy.orm import Session

from app.connectors.connector_factory import get_connector
from app.db_models import Repository
from app.services.connector_sync_engine import run_incremental_connector_sync
from app.services.performance_cache_service import invalidate_repository_performance_caches
from app.services.sharepoint_delta_sync_engine import run_sharepoint_delta_sync


def run_repository_sync_by_type(
    db: Session,
    tenant_id,
    repository,
    connector,
    started_by=None,
    sync_mode: str = "manual",
):
    if repository.source_type == "sharepoint":
        return run_sharepoint_delta_sync(
            db=db,
            tenant_id=tenant_id,
            repository=repository,
            connector=connector,
            started_by=started_by,
            sync_mode=sync_mode,
        )

    return run_incremental_connector_sync(
        db=db,
        tenant_id=tenant_id,
        repository=repository,
        connector=connector,
        started_by=started_by,
        sync_mode=sync_mode,
    )


def sync_repository(repository_id: str, current_user: dict, db: Session):
    repo = (
        db.query(Repository)
        .filter(
            Repository.repository_id == repository_id,
            Repository.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not repo:
        return {
            "success": False,
            "message": "Repository not found",
        }

    repo_dict = {
        "repository_id": repo.repository_id,
        "tenant_id": repo.tenant_id,
        "repository_name": repo.repository_name,
        "source_type": repo.source_type,
        "business_area": repo.business_area,
        "source_path": repo.source_path,
        "connection_config": repo.connection_config or {},
    }
    connector = get_connector(repo_dict)

    sync_run = run_repository_sync_by_type(
        db=db,
        tenant_id=current_user["tenant_id"],
        repository=repo,
        connector=connector,
        started_by=current_user["user_id"],
        sync_mode="manual",
    )

    has_repository_changes = any(
        (
            sync_run.files_processed,
            sync_run.files_deleted,
            sync_run.files_failed,
            sync_run.chunks_created,
            sync_run.embeddings_created,
        )
    )

    if has_repository_changes:
        invalidate_repository_performance_caches(current_user["tenant_id"], repository_id)

        from app.services.dashboard_service import get_dashboard_data
        from app.services.escalation_service import get_escalation_dashboard
        # from app.services.procurement_dashboard_service import get_procurement_dashboard
        # from app.services.proposal_dashboard_service import get_proposal_dashboard
        from app.services.repository_content_report_service import build_repository_content_report
        # from app.services.vendor_dashboard_service import get_vendor_dashboard

        build_repository_content_report(
            db,
            current_user["tenant_id"],
            repository_id,
            force_refresh=True,
        )

        # get_proposal_dashboard(current_user["tenant_id"], force_refresh=True, db=db)
        # get_vendor_dashboard(current_user["tenant_id"], force_refresh=True, db=db)
        # get_procurement_dashboard(current_user["tenant_id"], force_refresh=True, db=db)

        get_escalation_dashboard(current_user["tenant_id"], force_refresh=True, db=db)
        get_dashboard_data(current_user, force_refresh=True, db=db)

    return {
        "success": True,
        "repository_id": repository_id,
        "sync_run_id": sync_run.id,
        "status": sync_run.sync_status,
        "files_found": sync_run.files_discovered,
        "indexed": sync_run.files_processed,
        "skipped": sync_run.files_skipped,
        "failed": sync_run.files_failed,
        "deleted": sync_run.files_deleted,
        "chunks_created": sync_run.chunks_created,
        "embeddings_created": sync_run.embeddings_created,
        "symployee_module": {
            "document_controller": True,
        },
    }
