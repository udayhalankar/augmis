import os
import re
from pathlib import Path

_WINDOWS_DRIVE_RE = re.compile(r"^(?P<drive>[A-Za-z]):[\\/](?P<path>.*)$")
_MNT_DRIVE_RE = re.compile(r"^/mnt/(?P<drive>[A-Za-z])(?:/(?P<path>.*))?$")


def _is_absolute_sharedrive_path(raw_path: str, normalized: Path) -> bool:
    return bool(
        _WINDOWS_DRIVE_RE.match(raw_path)
        or raw_path.startswith(("/", "\\"))
        or normalized.is_absolute()
    )


def _normalize_sharedrive_path(
    raw_path: str | None,
    base_path: Path | None = None,
    *,
    require_absolute: bool = False,
) -> Path:
    value = (raw_path or "").strip()
    if not value:
        return base_path if base_path is not None else Path()

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

    normalized = Path(value.replace("\\", "/"))

    if base_path is not None and not normalized.is_absolute():
        normalized = base_path / normalized

    if require_absolute and not _is_absolute_sharedrive_path(value, normalized):
        raise ValueError(f"Path must be absolute: {normalized}")

    return normalized


def _safe_dir(path: Path, base_path: Path) -> Path:
    resolved = path.resolve()
    base_resolved = base_path.resolve()

    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise ValueError("Path must remain within the configured datasource root")

    return resolved


def discover_sharedrive_roots(base_path: str | None = None):
    value = (base_path or "").strip()
    if not value:
        raise ValueError("A root path is required to browse shared drive contents")

    root = _normalize_sharedrive_path(value, require_absolute=True)

    if not root.exists() or not root.is_dir():
        raise ValueError(f"Root path does not exist or is not mounted: {root}")

    return [
        {
            "name": item.name,
            "path": str(item.resolve()),
            "is_dir": item.is_dir(),
        }
        for item in sorted(root.iterdir(), key=lambda item: item.name.lower())
        if item.is_dir()
    ]


def discover_sharedrive_folders(root_path: str, folder_path: str | None = None):
    root_value = (root_path or "").strip()
    if not root_value:
        raise ValueError("A root path is required to browse shared drive folders")

    root = _normalize_sharedrive_path(root_value, require_absolute=True)

    if not root.exists() or not root.is_dir():
        raise ValueError(f"Root path does not exist or is not mounted: {root}")

    target = root
    if folder_path and folder_path not in ["/", ""]:
        target = _normalize_sharedrive_path(folder_path, root)
        target = _safe_dir(target, root)

    if not target.exists() or not target.is_dir():
        raise ValueError(f"Folder path does not exist or is not mounted: {target}")

    return [
        {
            "name": item.name,
            "path": str(item.resolve()),
            "is_dir": item.is_dir(),
        }
        for item in sorted(target.iterdir(), key=lambda item: item.name.lower())
        if item.is_dir()
    ]
