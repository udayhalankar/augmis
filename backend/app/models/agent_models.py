from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AgentIdentityModel(BaseModel):
    agent_id: str
    tenant_id: str | None = None
    machine_name: str | None = None
    hostname: str | None = None
    platform: str | None = None
    version: str


class AgentRegistrationRequest(BaseModel):
    agent: AgentIdentityModel
    root_path: str
    capabilities: dict = Field(default_factory=dict)


class AgentHeartbeatRequest(BaseModel):
    agent_id: str
    seen_at: datetime
    status: str
    root_path: str
    pending_change_count: int = 0


class AgentFileChangeRequest(BaseModel):
    path: str
    kind: str
    change_type: str
    size: int | None = None
    modified_at: str | None = None


class AgentSyncRequest(BaseModel):
    agent_id: str
    root_path: str
    scanned_at: datetime
    changes: list[AgentFileChangeRequest] = Field(default_factory=list)
    full_scan: bool = False
    snapshot: dict | None = None


class AgentCommandPollRequest(BaseModel):
    agent_id: str
    root_path: str


class AgentCommandResultRequest(BaseModel):
    agent_id: str
    command_id: str
    result_status: str
    executed_at: datetime
    message: str = ""
    artifact_path: str | None = None
    failure_reason: str | None = None
    rollback_supported: bool = True
    metadata: dict = Field(default_factory=dict)
