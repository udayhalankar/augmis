#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


REPO_ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = Path("/mnt/d/Backups/Infomentica_Backup")
BACKUP_PREFIX = "code_backup_"
BACKUP_SUFFIX = ".zip"

EXCLUDED_DIR_NAMES = {
    ".backups",
    ".codex",
    ".git",
    ".next",
    ".venv",
    "__pycache__",
    "index_store",
    "node_modules",
}

EXCLUDED_TOP_LEVEL_DIRS = {
    "datasource",
}

EXCLUDED_FILE_SUFFIXES = {
    ".log",
    ".pyc",
    ".pyo",
    ".zip",
}

EXCLUDED_FILE_NAMES = {
    ".DS_Store",
    ".env",
    ".env.local",
}

RETAIN_LATEST_COUNT = 10


def should_skip_parts(parts: tuple[str, ...]) -> bool:
    if not parts:
        return False

    if parts[0] in EXCLUDED_TOP_LEVEL_DIRS:
        return True

    return any(part in EXCLUDED_DIR_NAMES for part in parts)


def should_skip_file(file_path: Path) -> bool:
    relative = file_path.relative_to(REPO_ROOT)

    if relative.name in EXCLUDED_FILE_NAMES:
        return True

    if relative.name.startswith(".env."):
        return True

    if file_path.suffix.lower() in EXCLUDED_FILE_SUFFIXES:
        return True

    return should_skip_parts(relative.parts[:-1])


def collect_files() -> list[Path]:
    files: list[Path] = []

    for root, dirs, filenames in os.walk(REPO_ROOT):
        root_path = Path(root)
        relative_root = root_path.relative_to(REPO_ROOT)

        if relative_root.parts and should_skip_parts(relative_root.parts):
            dirs[:] = []
            continue

        dirs[:] = [
            directory
            for directory in dirs
            if directory not in EXCLUDED_DIR_NAMES
            and not (
                root_path == REPO_ROOT and directory in EXCLUDED_TOP_LEVEL_DIRS
            )
        ]

        for filename in filenames:
            file_path = root_path / filename
            if should_skip_file(file_path):
                continue
            files.append(file_path)

    files.sort()
    return files


def build_backup_name(timestamp: datetime) -> str:
    return f"{BACKUP_PREFIX}{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}{BACKUP_SUFFIX}"


def create_backup(files: list[Path]) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / build_backup_name(datetime.now())

    with ZipFile(backup_path, "w", compression=ZIP_DEFLATED) as archive:
        for file_path in files:
            archive.write(file_path, arcname=file_path.relative_to(REPO_ROOT))

    return backup_path


def parse_backup_timestamp(backup_path: Path) -> datetime:
    timestamp_text = backup_path.stem.removeprefix(BACKUP_PREFIX)
    return datetime.strptime(timestamp_text, "%Y-%m-%d_%H-%M-%S")


def prune_backups() -> tuple[list[Path], list[Path]]:
    backups = sorted(
        BACKUP_DIR.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"),
        key=parse_backup_timestamp,
    )

    if len(backups) <= RETAIN_LATEST_COUNT:
        return backups, []

    keep: set[Path] = set(backups[-RETAIN_LATEST_COUNT:])
    first_backup_by_day: dict[str, Path] = {}

    for backup in backups:
        day_key = parse_backup_timestamp(backup).strftime("%Y-%m-%d")
        first_backup_by_day.setdefault(day_key, backup)

    keep.update(first_backup_by_day.values())

    deleted: list[Path] = []
    for backup in backups:
        if backup in keep:
            continue
        backup.unlink(missing_ok=True)
        deleted.append(backup)

    kept = sorted(keep, key=parse_backup_timestamp)
    return kept, deleted


def main() -> int:
    files = collect_files()
    backup_path = create_backup(files)
    kept, deleted = prune_backups()

    print(f"Created backup: {backup_path}")
    print(f"Included files: {len(files)}")
    print(f"Backups retained: {len(kept)}")
    print(f"Backups deleted: {len(deleted)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
