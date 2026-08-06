from abc import ABC, abstractmethod


class BaseConnector(ABC):
    def __init__(self, repository: dict):
        self.repository = repository
        self.config = dict(repository.get("connection_config") or {})

        # For shared-drive repositories, source_path is the canonical mount.
        # Always mirror it into root_path so stale connector config cannot scan
        # the wrong directory while the UI still shows the right source path.
        if repository.get("source_type") == "sharedrive":
            source_path = str(repository.get("source_path") or "").strip()
            root_path = str(self.config.get("root_path") or "").strip()

            if source_path:
                self.config["root_path"] = source_path
            elif root_path:
                self.config["root_path"] = root_path

    @abstractmethod
    def list_files(self) -> list[dict]:
        pass

    @abstractmethod
    def get_file_content(self, source_file: dict) -> bytes:
        pass
