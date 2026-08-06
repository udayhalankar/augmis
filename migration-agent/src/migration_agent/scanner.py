from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class ScanEntry:
    path: str
    name: str
    kind: str
    size: int | None
    modified_at: str | None


def _safe_file_stat(item: Path):
    try:
        return item.stat()
    except OSError:
        return None


def scan_root(root: Path) -> dict:
    root = root.expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Root path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Root path is not a directory: {root}")

    entries: list[ScanEntry] = []
    for item in sorted(root.rglob("*")):
        stat = _safe_file_stat(item)
        if stat is None:
            continue
        entries.append(
            ScanEntry(
                path=str(item),
                name=item.name,
                kind="dir" if item.is_dir() else "file",
                size=None if item.is_dir() else stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            )
        )

    return {
        "root_path": str(root),
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "entry_count": len(entries),
        "entries": [asdict(entry) for entry in entries],
    }
