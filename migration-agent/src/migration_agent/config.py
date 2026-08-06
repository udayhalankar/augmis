from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentConfig:
    backend_url: str | None
    tenant_id: str | None
    token: str | None
    root_path: str | None


def load_config() -> AgentConfig:
    file_values = _load_dotenv_values()
    return AgentConfig(
        backend_url=os.getenv("MIGRATION_AGENT_BACKEND_URL") or file_values.get("MIGRATION_AGENT_BACKEND_URL"),
        tenant_id=os.getenv("MIGRATION_AGENT_TENANT_ID") or file_values.get("MIGRATION_AGENT_TENANT_ID"),
        token=os.getenv("MIGRATION_AGENT_TOKEN") or file_values.get("MIGRATION_AGENT_TOKEN"),
        root_path=os.getenv("MIGRATION_AGENT_ROOT_PATH") or file_values.get("MIGRATION_AGENT_ROOT_PATH"),
    )


def _load_dotenv_values() -> dict[str, str]:
    candidates = []
    config_file = os.getenv("MIGRATION_AGENT_CONFIG_FILE")
    if config_file:
        candidates.append(Path(config_file))
    candidates.append(Path.cwd() / ".env")
    candidates.append(Path(__file__).resolve().parents[2] / ".env")

    values: dict[str, str] = {}
    for candidate in candidates:
        if not candidate.exists():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in values:
                values[key] = value
    return values
