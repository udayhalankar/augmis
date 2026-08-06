import os
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.db_models import Repository
from app.services.repository_ingestion_service import get_repository_upload_dir


_WINDOWS_DRIVE_RE = re.compile(r"^(?P<drive>[A-Za-z]):[\\/](?P<path>.*)$")
_MNT_DRIVE_RE = re.compile(r"^/mnt/(?P<drive>[A-Za-z])(?:/(?P<path>.*))?$")


def _normalize_path(raw_path: str) -> Path:
    value = (raw_path or "").strip()
    if not value:
        return Path()

    match = _WINDOWS_DRIVE_RE.match(value)
    if match:
        drive = match.group("drive").upper()
        remainder = match.group("path").replace("/", "\\").lstrip("\\/")
        if os.name == "nt":
            return Path(f"{drive}:\\{remainder}") if remainder else Path(f"{drive}:\\")
        return Path("/mnt") / drive.lower() / Path(remainder.replace("\\", "/"))

    mnt_match = _MNT_DRIVE_RE.match(value.replace("\\", "/"))
    if mnt_match:
        drive = mnt_match.group("drive").upper()
        remainder = str(mnt_match.group("path") or "").replace("/", "\\").lstrip("\\/")
        if os.name == "nt":
            return Path(f"{drive}:\\{remainder}") if remainder else Path(f"{drive}:\\")
        return Path(value.replace("\\", "/"))

    return Path(value.replace("\\", "/"))


def _pick_sharedrive_source_path(repo: Repository) -> Path | None:
    source_path_value = (repo.source_path or "").strip()
    root_path_value = (repo.connection_config or {}).get("root_path")

    source_path = _normalize_path(source_path_value) if source_path_value else None
    root_path = _normalize_path(root_path_value) if root_path_value else None

    if source_path and root_path and not source_path.is_absolute() and root_path.is_absolute():
        source_path = root_path / source_path

    if source_path and root_path:
        try:
            source_resolved = source_path.resolve() if source_path.exists() else source_path
            root_resolved = root_path.resolve() if root_path.exists() else root_path

            if source_resolved == root_resolved:
                return source_path

            if source_resolved in root_resolved.parents:
                return root_path

            if root_resolved in source_resolved.parents:
                return source_path
        except Exception:
            pass

        # If both are configured but unrelated, prefer the explicit repository source path.
        return source_path

    return source_path or root_path


def resolve_repository_source_paths(
    db: Session,
    tenant_id: str,
    *,
    business_areas: set[str] | None = None,
    repository_ids: set[str] | None = None,
    source_types: set[str] | None = None,
    include_upload_dirs: bool = True,
) -> list[Path]:
    query = db.query(Repository).filter(
        Repository.tenant_id == tenant_id,
        Repository.status == "ACTIVE",
    )

    if business_areas:
        query = query.filter(Repository.business_area.in_(sorted(business_areas)))

    if repository_ids:
        query = query.filter(Repository.repository_id.in_(sorted(repository_ids)))

    if source_types:
        query = query.filter(Repository.source_type.in_(sorted(source_types)))

    roots: list[Path] = []
    seen: set[str] = set()

    for repo in query.all():
        resolved_source = None

        if repo.source_type == "sharedrive":
            resolved_source = _pick_sharedrive_source_path(repo)
        else:
            source_path = (repo.source_path or "").strip()
            if source_path:
                resolved_source = _normalize_path(source_path)

        if resolved_source is not None:
            resolved_key = str(resolved_source.resolve()) if resolved_source.exists() else str(resolved_source)
            if resolved_key not in seen:
                roots.append(resolved_source)
                seen.add(resolved_key)

        if include_upload_dirs:
            upload_dir = get_repository_upload_dir(tenant_id, repo.repository_id)
            upload_key = str(upload_dir.resolve())
            if upload_key not in seen:
                roots.append(upload_dir)
                seen.add(upload_key)

    return roots
