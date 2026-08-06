import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.db_models import Repository


PERFORMANCE_CACHE_FILE = (
    Path(__file__).resolve().parents[2] / "storage" / "runtime_performance_cache.json"
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> dict:
    return {
        "responses": {},
        "classification": {},
    }


def _load_state() -> dict:
    if not PERFORMANCE_CACHE_FILE.exists():
        return _default_state()

    try:
        payload = json.loads(PERFORMANCE_CACHE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _default_state()

    state = _default_state()
    for key, value in payload.items():
        if isinstance(value, dict):
            state[key] = value
    return state


def _save_state(state: dict) -> None:
    PERFORMANCE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PERFORMANCE_CACHE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def get_cached_response(cache_key: str, revision: str | None = None):
    state = _load_state()
    record = state.get("responses", {}).get(cache_key)
    if not record:
        return None
    if revision is not None and record.get("revision") != revision:
        return None
    return deepcopy(record.get("payload"))


def set_cached_response(
    cache_key: str,
    payload: dict,
    *,
    revision: str | None = None,
    metadata: dict | None = None,
) -> None:
    state = _load_state()
    state.setdefault("responses", {})[cache_key] = {
        "revision": revision,
        "metadata": metadata or {},
        "updated_at": _utcnow_iso(),
        "payload": payload,
    }
    _save_state(state)


def clear_cached_response(cache_key: str) -> None:
    state = _load_state()
    if cache_key in state.get("responses", {}):
        del state["responses"][cache_key]
        _save_state(state)


def clear_cached_responses_by_prefix(prefix: str) -> None:
    state = _load_state()
    keys = [
        key for key in state.get("responses", {})
        if key.startswith(prefix)
    ]
    if not keys:
        return
    for key in keys:
        del state["responses"][key]
    _save_state(state)


def get_repository_classification_cache(repository_id: str) -> dict[str, dict]:
    state = _load_state()
    repo_cache = state.get("classification", {}).get(repository_id, {})
    return deepcopy(repo_cache.get("files", {}))


def update_repository_classification_cache(
    repository_id: str,
    entries: dict[str, dict],
    *,
    valid_keys: set[str] | None = None,
) -> None:
    state = _load_state()
    repo_cache = state.setdefault("classification", {}).setdefault(
        repository_id,
        {"updated_at": _utcnow_iso(), "files": {}},
    )
    existing_files = repo_cache.setdefault("files", {})
    existing_files.update(entries)

    if valid_keys is not None:
        stale_keys = [key for key in existing_files if key not in valid_keys]
        for key in stale_keys:
            del existing_files[key]

    repo_cache["updated_at"] = _utcnow_iso()
    _save_state(state)


def get_repository_cache_revision(
    db: Session,
    tenant_id: str,
    repository_id: str,
) -> str:
    repo = (
        db.query(Repository)
        .filter(
            Repository.tenant_id == tenant_id,
            Repository.repository_id == repository_id,
        )
        .first()
    )
    if not repo:
        return f"{tenant_id}:{repository_id}:missing"

    return "|".join(
        [
            repo.repository_id,
            repo.status or "",
            repo.last_sync_status or repo.sync_status or "",
            repo.last_sync_run_id or "",
            repo.last_sync_completed_at.isoformat() if repo.last_sync_completed_at else "",
            repo.modified_at.isoformat() if repo.modified_at else "",
        ]
    )


def get_tenant_cache_revision(
    db: Session,
    tenant_id: str,
    *,
    business_areas: set[str] | None = None,
    repository_ids: set[str] | None = None,
) -> str:
    query = db.query(Repository).filter(Repository.tenant_id == tenant_id)

    if business_areas:
        query = query.filter(Repository.business_area.in_(sorted(business_areas)))

    if repository_ids:
        query = query.filter(Repository.repository_id.in_(sorted(repository_ids)))

    repos = query.order_by(Repository.repository_id.asc()).all()
    if not repos:
        return f"{tenant_id}:no_repositories"

    return "||".join(
        "|".join(
            [
                repo.repository_id,
                repo.status or "",
                repo.last_sync_status or repo.sync_status or "",
                repo.last_sync_run_id or "",
                repo.last_sync_completed_at.isoformat() if repo.last_sync_completed_at else "",
                repo.modified_at.isoformat() if repo.modified_at else "",
            ]
        )
        for repo in repos
    )


def invalidate_repository_performance_caches(
    tenant_id: str,
    repository_id: str,
) -> None:
    clear_cached_response(f"repository_content_report::{tenant_id}::{repository_id}")
    clear_cached_responses_by_prefix(f"executive_dashboard::{tenant_id}::")
    clear_cached_responses_by_prefix(f"executive_dashboard::v2::{tenant_id}::")
    clear_cached_responses_by_prefix(f"proposal_dashboard::{tenant_id}")
    clear_cached_responses_by_prefix(f"proposal_dashboard::v2::{tenant_id}")
    clear_cached_responses_by_prefix(f"vendor_dashboard::{tenant_id}")
    clear_cached_responses_by_prefix(f"vendor_dashboard::v2::{tenant_id}")
    clear_cached_responses_by_prefix(f"procurement_dashboard::{tenant_id}")
    clear_cached_responses_by_prefix(f"procurement_dashboard::v2::{tenant_id}")
    clear_cached_responses_by_prefix(f"escalation_dashboard::{tenant_id}")
    clear_cached_responses_by_prefix(f"escalation_dashboard::v2::{tenant_id}")
