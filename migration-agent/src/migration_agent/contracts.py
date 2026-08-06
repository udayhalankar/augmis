from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone


API_BASE_PATH = "/api/agents"

REGISTER_ENDPOINT = f"{API_BASE_PATH}/register"
HEARTBEAT_ENDPOINT = f"{API_BASE_PATH}/heartbeat"
SYNC_ENDPOINT = f"{API_BASE_PATH}/sync"
CHANGES_ENDPOINT = f"{API_BASE_PATH}/changes"
COMMAND_PULL_ENDPOINT = f"{API_BASE_PATH}/commands/pull"
COMMAND_RESULT_ENDPOINT = f"{API_BASE_PATH}/commands/result"


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str | None
    tenant_id: str | None
    machine_name: str | None
    hostname: str | None
    platform: str | None
    version: str


@dataclass(frozen=True)
class RegistrationRequest:
    agent: AgentIdentity
    root_path: str
    capabilities: dict


@dataclass(frozen=True)
class HeartbeatRequest:
    agent_id: str
    seen_at: str
    status: str
    root_path: str
    pending_change_count: int = 0


@dataclass(frozen=True)
class FileChange:
    path: str
    kind: str
    change_type: str
    size: int | None = None
    modified_at: str | None = None


@dataclass(frozen=True)
class SyncRequest:
    agent_id: str
    root_path: str
    scanned_at: str
    changes: list[FileChange]
    full_scan: bool = False


@dataclass(frozen=True)
class CommandPollRequest:
    agent_id: str
    root_path: str


@dataclass(frozen=True)
class CommandResultRequest:
    agent_id: str
    command_id: str
    result_status: str
    executed_at: str
    message: str = ""
    artifact_path: str | None = None
    failure_reason: str | None = None
    rollback_supported: bool = True
    metadata: dict | None = None


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_payload(instance) -> dict:
    return asdict(instance)
