from datetime import datetime, timezone

from app.connectors.base_connector import BaseConnector
from app.services.connector_hash_service import sha256_file
from app.services.sharedrive_setup_service import _normalize_sharedrive_path


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".xls",
    ".csv",
    ".txt",
    ".md",
}


class SharedDriveConnector(BaseConnector):
    def test_connection(self):
        root_path = (self.config.get("root_path") or "").strip()

        if not root_path:
            raise ValueError("Shared Drive root_path is required")

        root = _normalize_sharedrive_path(root_path, require_absolute=True)

        if not root.exists():
            raise ValueError(f"Shared Drive root path does not exist: {root}")

        if not root.is_dir():
            raise ValueError(f"Shared Drive root path is not a directory: {root}")

        readable_dirs = 0
        readable_files = 0
        for path in root.iterdir():
          if path.is_dir():
              readable_dirs += 1
          elif path.is_file():
              readable_files += 1

        return {
            "ok": True,
            "root_path": str(root.resolve()),
            "directory_count": readable_dirs,
            "file_count": readable_files,
        }

    def list_files(self) -> list[dict]:
        root_path = (self.config.get("root_path") or "").strip()

        if not root_path:
            raise ValueError("Shared Drive root_path is required")

        root = _normalize_sharedrive_path(root_path, require_absolute=True)

        if not root.exists():
            raise ValueError(f"Shared Drive root path does not exist: {root}")

        if not root.is_dir():
            raise ValueError(f"Shared Drive root path is not a directory: {root}")

        files = []

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            stat = path.stat()
            relative_path = path.relative_to(root).as_posix()

            files.append(
                {
                    "external_file_id": relative_path,
                    "file_name": path.name,
                    "file_path": relative_path,
                    "file_hash": sha256_file(str(path)),
                    "file_size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime, timezone.utc),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                    "metadata": {
                        "full_path": str(path),
                        "source": "shared_drive",
                    },
                }
            )

        return files

    def get_file_content(self, source_file: dict) -> bytes:
        full_path = source_file.get("metadata", {}).get("full_path")

        if not full_path:
            file_path = source_file.get("file_path")
            if not file_path:
                raise ValueError("Shared drive source file missing file_path")
            root = _normalize_sharedrive_path(self.config.get("root_path", ""), require_absolute=True)
            full_path = str(root / file_path)

        with open(full_path, "rb") as file_obj:
            return file_obj.read()
