from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import sleep
from threading import Event

from migration_agent.contracts import FileChange


@dataclass(frozen=True)
class FileSnapshot:
    path: str
    kind: str
    size: int | None
    modified_ns: int


def _safe_file_stat(item: Path):
    try:
        return item.stat()
    except OSError:
        return None


def build_snapshot(root: Path) -> dict[str, FileSnapshot]:
    root = root.expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Root path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Root path is not a directory: {root}")

    snapshot: dict[str, FileSnapshot] = {}
    for item in sorted(root.rglob("*")):
        stat = _safe_file_stat(item)
        if stat is None:
            continue
        snapshot[str(item)] = FileSnapshot(
            path=str(item),
            kind="dir" if item.is_dir() else "file",
            size=None if item.is_dir() else stat.st_size,
            modified_ns=stat.st_mtime_ns,
        )
    return snapshot


def diff_snapshots(previous: dict[str, FileSnapshot], current: dict[str, FileSnapshot]) -> list[FileChange]:
    changes: list[FileChange] = []
    previous_keys = set(previous)
    current_keys = set(current)

    for removed in sorted(previous_keys - current_keys):
        old = previous[removed]
        changes.append(FileChange(path=old.path, kind=old.kind, change_type="deleted"))

    for added in sorted(current_keys - previous_keys):
        new = current[added]
        changes.append(
            FileChange(
                path=new.path,
                kind=new.kind,
                change_type="created",
                size=new.size,
            )
        )

    for common in sorted(previous_keys & current_keys):
        old = previous[common]
        new = current[common]
        if old.modified_ns != new.modified_ns or old.size != new.size:
            changes.append(
                FileChange(
                    path=new.path,
                    kind=new.kind,
                    change_type="modified",
                    size=new.size,
                )
            )

    return changes


def watch_folder(root: Path, interval_seconds: int = 5, stop_event: Event | None = None):
    previous = build_snapshot(root)
    yield []

    while True:
        if stop_event and stop_event.wait(interval_seconds):
            return
        if not stop_event:
            sleep(interval_seconds)
        current = build_snapshot(root)
        changes = diff_snapshots(previous, current)
        if changes:
            yield changes
            previous = current
