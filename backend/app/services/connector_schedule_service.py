from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db_models import Repository


def utc_now():
    return datetime.now(timezone.utc)


def is_repository_due_for_sync(repository: Repository) -> bool:
    if not repository.sync_enabled:
        return False

    if not repository.sync_interval_minutes:
        return False

    if not repository.last_sync_completed_at:
        return True

    next_due = repository.last_sync_completed_at + timedelta(
        minutes=repository.sync_interval_minutes
    )

    return utc_now() >= next_due


def get_due_repositories(db: Session, tenant_id=None):
    query = db.query(Repository).filter(
        Repository.sync_enabled == True,
        Repository.sync_interval_minutes.isnot(None),
    )

    if tenant_id:
        query = query.filter(Repository.tenant_id == tenant_id)

    repositories = query.all()

    return [repo for repo in repositories if is_repository_due_for_sync(repo)]
