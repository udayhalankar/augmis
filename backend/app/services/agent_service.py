from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path, PurePath

from sqlalchemy.orm import Session

from app.db_models import (
    MigrationAgent,
    MigrationAgentActivity,
    Repository,
    SymployeeConnectorCommand,
    SymployeeDocumentIdentity,
    SymployeeDocumentSourceObject,
)
from app.models.agent_models import (
    AgentCommandPollRequest,
    AgentCommandResultRequest,
    AgentHeartbeatRequest,
    AgentRegistrationRequest,
    AgentSyncRequest,
)
from app.services.audit_service import create_audit_log


def _utc_now() -> datetime:
    return datetime.now(UTC)


_WINDOWS_DRIVE_RE = re.compile(r"^(?P<drive>[A-Za-z]):[\\/](?P<path>.*)$")
_MNT_DRIVE_RE = re.compile(r"^/mnt/(?P<drive>[A-Za-z])(?:/(?P<path>.*))?$")


def _serialize_agent(agent: MigrationAgent) -> dict:
    return {
        "agent_id": agent.agent_id,
        "tenant_id": agent.tenant_id,
        "machine_name": agent.machine_name,
        "hostname": agent.hostname,
        "platform": agent.platform,
        "version": agent.version,
        "root_path": agent.root_path,
        "status": agent.status,
        "pending_change_count": agent.pending_change_count,
        "last_seen_at": agent.last_seen_at.isoformat() if agent.last_seen_at else None,
        "last_sync_at": agent.last_sync_at.isoformat() if agent.last_sync_at else None,
        "last_error": agent.last_error,
        "metadata": agent.metadata_json or {},
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "modified_at": agent.modified_at.isoformat() if agent.modified_at else None,
    }


def _serialize_activity(activity: MigrationAgentActivity) -> dict:
    return {
        "activity_id": activity.activity_id,
        "agent_id": activity.agent_id,
        "tenant_id": activity.tenant_id,
        "occurred_at": activity.occurred_at.isoformat() if activity.occurred_at else None,
        "event_type": activity.event_type,
        "root_path": activity.root_path,
        "file_path": activity.file_path,
        "file_name": activity.file_name,
        "kind": activity.kind,
        "change_type": activity.change_type,
        "item_count": activity.item_count,
        "metadata": activity.metadata_json or {},
    }


def _get_or_create_agent(db: Session, agent_id: str, version: str = "0.1.0", root_path: str = "") -> MigrationAgent:
    agent = db.query(MigrationAgent).filter(MigrationAgent.agent_id == agent_id).first()
    if agent:
        return agent
    agent = MigrationAgent(
        agent_id=agent_id,
        version=version,
        root_path=root_path,
        status="UNKNOWN",
        metadata_json={},
    )
    db.add(agent)
    db.flush()
    return agent


def register_agent(db: Session, payload: AgentRegistrationRequest) -> dict:
    agent = _get_or_create_agent(
        db,
        agent_id=payload.agent.agent_id,
        version=payload.agent.version,
        root_path=payload.root_path,
    )
    agent.tenant_id = payload.agent.tenant_id
    agent.machine_name = payload.agent.machine_name
    agent.hostname = payload.agent.hostname
    agent.platform = payload.agent.platform
    agent.version = payload.agent.version
    agent.root_path = payload.root_path
    agent.status = "REGISTERED"
    agent.metadata_json = {
        **(agent.metadata_json or {}),
        "capabilities": payload.capabilities,
        "registered_at": _utc_now().isoformat(),
    }
    db.add(
        MigrationAgentActivity(
            agent_id=agent.agent_id,
            tenant_id=agent.tenant_id,
            event_type="registered",
            root_path=payload.root_path,
            item_count=len(payload.capabilities or {}),
            metadata_json={"capabilities": payload.capabilities},
        )
    )
    db.commit()
    db.refresh(agent)
    return _serialize_agent(agent)


def record_heartbeat(db: Session, payload: AgentHeartbeatRequest) -> dict:
    agent = _get_or_create_agent(
        db,
        agent_id=payload.agent_id,
        root_path=payload.root_path,
    )
    agent.root_path = payload.root_path
    agent.status = payload.status
    agent.pending_change_count = payload.pending_change_count
    agent.last_seen_at = payload.seen_at
    db.add(
        MigrationAgentActivity(
            agent_id=agent.agent_id,
            tenant_id=agent.tenant_id,
            event_type="heartbeat",
            root_path=payload.root_path,
            item_count=payload.pending_change_count,
            metadata_json={"status": payload.status},
        )
    )
    db.commit()
    db.refresh(agent)
    return _serialize_agent(agent)


def record_sync(db: Session, payload: AgentSyncRequest) -> dict:
    agent = _get_or_create_agent(
        db,
        agent_id=payload.agent_id,
        root_path=payload.root_path,
    )
    agent.root_path = payload.root_path
    agent.last_sync_at = payload.scanned_at
    agent.last_seen_at = payload.scanned_at
    agent.status = "SYNCED" if payload.changes else "RUNNING"
    agent.pending_change_count = 0

    db.add(
        MigrationAgentActivity(
            agent_id=agent.agent_id,
            tenant_id=agent.tenant_id,
            event_type="sync",
            root_path=payload.root_path,
            item_count=len(payload.changes),
            metadata_json={
                "full_scan": payload.full_scan,
                "snapshot_entry_count": (payload.snapshot or {}).get("entry_count"),
            },
        )
    )

    for change in payload.changes[:200]:
        file_name = PurePath(change.path).name if change.path else None
        db.add(
            MigrationAgentActivity(
                agent_id=agent.agent_id,
                tenant_id=agent.tenant_id,
                event_type="file_change",
                root_path=payload.root_path,
                file_path=change.path,
                file_name=file_name,
                kind=change.kind,
                change_type=change.change_type,
                metadata_json={
                    "size": change.size,
                    "modified_at": change.modified_at,
                },
            )
        )

    db.commit()
    db.refresh(agent)
    return {
        "agent": _serialize_agent(agent),
        "activity_count": len(payload.changes),
    }


def list_agents(db: Session, limit: int = 100) -> dict:
    agents = (
        db.query(MigrationAgent)
        .order_by(MigrationAgent.last_seen_at.desc().nullslast(), MigrationAgent.modified_at.desc().nullslast())
        .limit(limit)
        .all()
    )
    activities = (
        db.query(MigrationAgentActivity)
        .order_by(MigrationAgentActivity.occurred_at.desc())
        .limit(limit * 5)
        .all()
    )
    return {
        "agents": [_serialize_agent(agent) for agent in agents],
        "activities": [_serialize_activity(activity) for activity in activities],
    }


def _normalize_path_value(path_value: str | None) -> Path | None:
    value = (path_value or "").strip()
    if not value:
        return None

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


def _normalize_source_type(source_type: str | None) -> str:
    return (source_type or "").strip().lower().replace("-", "").replace("_", "")


def _is_shared_drive_source_type(source_type: str | None) -> bool:
    return _normalize_source_type(source_type) == "sharedrive"


def _resolve_source_file_path(
    repository: Repository,
    source_object: SymployeeDocumentSourceObject,
) -> str | None:
    candidate_path = (
        source_object.source_path
        or source_object.external_object_id
        or source_object.source_version_ref
    )
    candidate = _normalize_path_value(candidate_path)
    if candidate is None:
        return None

    repository_root = _normalize_path_value(repository.source_path)
    if repository_root is not None and not candidate.is_absolute():
        candidate = repository_root / candidate

    return str(candidate)


def _path_within_root(path_value: str | None, root_path: str | None) -> bool:
    candidate = _normalize_path_value(path_value)
    root = _normalize_path_value(root_path)
    if candidate is None or root is None:
        return False
    try:
        candidate_resolved = candidate.resolve(strict=False)
        root_resolved = root.resolve(strict=False)
        candidate_resolved.relative_to(root_resolved)
        return True
    except Exception:
        return False


def _compute_artifact_path(source_path: str) -> str:
    source = _normalize_path_value(source_path) or Path(source_path)
    return str(source.parent / ".augmis" / f"{source.name}.augmis-command.json")


def pull_symployee_commands(db: Session, payload: AgentCommandPollRequest) -> dict:
    agent = _get_or_create_agent(
        db,
        agent_id=payload.agent_id,
        root_path=payload.root_path,
    )
    root_path = payload.root_path or agent.root_path

    commands = (
        db.query(SymployeeConnectorCommand)
        .order_by(SymployeeConnectorCommand.created_at.asc())
        .all()
    )

    items: list[dict] = []
    for command in commands:
        if command.status not in {"DISPATCHED", "ROLLBACK_PENDING"}:
            continue
        if command.agent_id and command.agent_id != payload.agent_id:
            continue

        repository = (
            db.query(Repository)
            .filter(Repository.repository_id == command.repository_id)
            .first()
        )
        if not repository or not _is_shared_drive_source_type(repository.source_type):
            continue

        source_object = (
            db.query(SymployeeDocumentSourceObject)
            .filter(
                SymployeeDocumentSourceObject.tenant_id == command.tenant_id,
                SymployeeDocumentSourceObject.identity_id == command.identity_id,
                SymployeeDocumentSourceObject.repository_id == command.repository_id,
                SymployeeDocumentSourceObject.is_active.is_(True),
            )
            .order_by(SymployeeDocumentSourceObject.last_seen_at.desc().nullslast())
            .first()
        )
        resolved_source_path = (
            _resolve_source_file_path(repository, source_object) if source_object else None
        )
        if not source_object or not _path_within_root(resolved_source_path, root_path):
            continue

        identity = (
            db.query(SymployeeDocumentIdentity)
            .filter(
                SymployeeDocumentIdentity.tenant_id == command.tenant_id,
                SymployeeDocumentIdentity.identity_id == command.identity_id,
            )
            .first()
        )
        artifact_path = _compute_artifact_path(resolved_source_path)
        payload_json = dict(command.payload_json or {})
        payload_json["agent_execution"] = {
            "target_file_path": resolved_source_path,
            "artifact_path": artifact_path,
            "repository_name": repository.repository_name,
            "repository_source_type": repository.source_type,
            "document_title": identity.title if identity else None,
            "source_object_path": source_object.source_path,
            "repository_root_path": repository.source_path,
        }
        command.payload_json = payload_json
        if not command.agent_id:
            command.agent_id = payload.agent_id

        items.append(
            {
                "command_id": command.command_id,
                "tenant_id": command.tenant_id,
                "status": command.status,
                "command_type": command.command_type,
                "payload": payload_json,
                "target_file_path": resolved_source_path,
                "artifact_path": artifact_path,
                "identity_id": command.identity_id,
                "repository_id": command.repository_id,
                "document_title": identity.title if identity else None,
            }
        )

    db.commit()
    return {"items": items, "count": len(items)}


def record_symployee_command_result(db: Session, payload: AgentCommandResultRequest) -> dict:
    command = (
        db.query(SymployeeConnectorCommand)
        .filter(SymployeeConnectorCommand.command_id == payload.command_id)
        .first()
    )
    if not command:
        raise ValueError("Connector command not found")

    command.agent_id = payload.agent_id
    payload_json = dict(command.payload_json or {})
    history = list(payload_json.get("execution_history") or [])
    history.append(
        {
            "status": payload.result_status.upper(),
            "executed_at": payload.executed_at.isoformat(),
            "message": payload.message,
            "artifact_path": payload.artifact_path,
            "failure_reason": payload.failure_reason,
            "rollback_supported": payload.rollback_supported,
            "metadata": payload.metadata or {},
            "agent_id": payload.agent_id,
        }
    )
    payload_json["execution_history"] = history[-20:]
    payload_json["latest_execution"] = history[-1]
    command.payload_json = payload_json

    result_status = payload.result_status.upper()
    if result_status == "ACKNOWLEDGED":
        command.status = "ACKNOWLEDGED"
        command.acknowledged_at = payload.executed_at
    elif result_status == "FAILED":
        command.status = "FAILED"
        command.failed_at = payload.executed_at
        command.failure_reason = payload.failure_reason or payload.message
    elif result_status == "ROLLED_BACK":
        command.status = "ROLLED_BACK"
        if payload.failure_reason:
            command.failure_reason = payload.failure_reason
    else:
        raise ValueError("Unsupported command result status")

    db.add(
        MigrationAgentActivity(
            agent_id=payload.agent_id,
            tenant_id=command.tenant_id,
            event_type="symployee_command_result",
            root_path=None,
            file_path=payload.artifact_path,
            file_name=PurePath(payload.artifact_path).name if payload.artifact_path else None,
            item_count=1,
            metadata_json={
                "command_id": payload.command_id,
                "result_status": result_status,
                "message": payload.message,
                "failure_reason": payload.failure_reason,
            },
        )
    )
    db.commit()

    create_audit_log(
        db=db,
        tenant_id=command.tenant_id,
        user_id=None,
        event_type=f"SYMPLOYEE_COMMAND_{result_status}",
        event_category="SYNTHETIC_EMPLOYEE",
        description=f"Agent reported {result_status.lower()} for connector command {command.command_id}",
        resource_type="symployee_connector_command",
        resource_id=command.command_id,
        metadata={
            "agent_id": payload.agent_id,
            "artifact_path": payload.artifact_path,
            "message": payload.message,
            "failure_reason": payload.failure_reason,
            "metadata": payload.metadata or {},
        },
    )

    return {
        "command_id": command.command_id,
        "status": command.status,
        "agent_id": command.agent_id,
        "artifact_path": payload.artifact_path,
    }
