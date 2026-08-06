import logging

from sqlalchemy.orm import Session

from app.connectors.connector_factory import get_connector
from app.db_models import Repository
from app.services.connector_schedule_service import get_due_repositories
from app.services.connector_sync_service import run_repository_sync_by_type


logger = logging.getLogger(__name__)


def run_due_repository_syncs(
    db: Session,
    tenant_id=None,
    started_by=None,
):
    due_repos = get_due_repositories(
        db=db,
        tenant_id=tenant_id,
    )

    results = []

    for repo in due_repos:
        try:
            connector = get_connector(_repository_to_connector_payload(repo))

            sync_run = run_repository_sync_by_type(
                db=db,
                tenant_id=repo.tenant_id,
                repository=repo,
                connector=connector,
                started_by=started_by,
                sync_mode="scheduled",
            )

            results.append(
                {
                    "repository_id": repo.repository_id,
                    "repository_name": repo.repository_name,
                    "sync_run_id": sync_run.id,
                    "status": sync_run.sync_status,
                }
            )
        except Exception as exc:
            logger.exception(
                "Scheduled sync failed for repository %s",
                repo.repository_id,
                extra={
                    "category": "scheduled_sync_failure",
                    "is_critical": True,
                    "context": {
                        "repository_id": repo.repository_id,
                        "business_area": repo.business_area,
                    },
                },
            )
            results.append(
                {
                    "repository_id": repo.repository_id,
                    "repository_name": repo.repository_name,
                    "status": "failed",
                    "error": str(exc),
                }
            )

    return {
        "due_count": len(due_repos),
        "results": results,
    }


def _repository_to_connector_payload(repo: Repository):
    return {
        "repository_id": repo.repository_id,
        "tenant_id": repo.tenant_id,
        "repository_name": repo.repository_name,
        "source_type": repo.source_type,
        "business_area": repo.business_area,
        "source_path": repo.source_path,
        "connection_config": repo.connection_config or {},
    }
