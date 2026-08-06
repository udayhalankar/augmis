from __future__ import annotations

import threading
import logging
import platform
import socket
import json
from pathlib import Path

from migration_agent.client import AgentClient
from migration_agent.config import load_config
from migration_agent.contracts import (
    AgentIdentity,
    CommandPollRequest,
    CommandResultRequest,
    HeartbeatRequest,
    RegistrationRequest,
    SyncRequest,
    now_utc,
    to_payload,
)
from migration_agent.state import append_recent_event, get_or_create_agent_id, update_state
from migration_agent.watcher import build_snapshot, diff_snapshots


class AgentRuntime:
    def __init__(self, root: Path, interval_seconds: int = 5) -> None:
        self.root = root
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self, stop_event: threading.Event | None = None) -> None:
        logger = logging.getLogger("migration_agent")
        config = load_config()
        if not config.root_path:
            config = config.__class__(
                backend_url=config.backend_url,
                tenant_id=config.tenant_id,
                token=config.token,
                root_path=str(self.root),
            )

        agent_id = get_or_create_agent_id()
        identity = AgentIdentity(
            agent_id=agent_id,
            tenant_id=config.tenant_id,
            machine_name=platform.node() or socket.gethostname(),
            hostname=socket.gethostname(),
            platform=platform.platform(),
            version="0.1.0",
        )
        client = AgentClient(config.backend_url or "http://127.0.0.1:8000", config.token)
        registration = RegistrationRequest(
            agent=identity,
            root_path=str(self.root),
            capabilities={"watching": True, "sync_mode": "polling"},
        )
        if config.backend_url:
            threading.Thread(
                target=self._best_effort_register,
                args=(client, registration, logger),
                daemon=True,
            ).start()
        update_state(
            agent_id=agent_id,
            tenant_id=config.tenant_id,
            root_path=str(self.root),
            backend_url=config.backend_url,
            status="starting",
        )
        previous = build_snapshot(self.root)
        first_cycle = True
        while True:
            if (stop_event or self._stop_event).wait(0 if first_cycle else self.interval_seconds):
                break
            current = build_snapshot(self.root)
            changes = [] if first_cycle else diff_snapshots(previous, current)
            previous = current
            first_cycle = False

            if not config.backend_url:
                continue

            heartbeat = HeartbeatRequest(
                agent_id=identity.agent_id or agent_id,
                seen_at=now_utc(),
                status="running",
                root_path=str(self.root),
                pending_change_count=len(changes),
            )
            threading.Thread(
                target=self._best_effort_heartbeat,
                args=(client, heartbeat, logger),
                daemon=True,
            ).start()

            if changes:
                payload = SyncRequest(
                    agent_id=identity.agent_id or agent_id,
                    root_path=str(self.root),
                    scanned_at=now_utc(),
                    changes=changes,
                    full_scan=False,
                )
                threading.Thread(
                    target=self._best_effort_sync,
                    args=(client, payload, logger),
                    daemon=True,
                ).start()

            threading.Thread(
                target=self._best_effort_process_commands,
                args=(client, identity.agent_id or agent_id, str(self.root), logger),
                daemon=True,
            ).start()

    @staticmethod
    def _best_effort_register(client: AgentClient, registration: RegistrationRequest, logger: logging.Logger) -> None:
        try:
            response = client.register(to_payload(registration))
            logger.info("Agent registration completed")
            update_state(
                status="registered",
                last_registration_at=now_utc(),
                registration=response,
            )
            append_recent_event({"event": "registered", "at": now_utc()})
        except Exception as exc:
            update_state(status="registration_failed", last_error=str(exc))
            logger.exception("Agent registration failed")

    @staticmethod
    def _best_effort_heartbeat(client: AgentClient, heartbeat: HeartbeatRequest, logger: logging.Logger) -> None:
        try:
            client.heartbeat(to_payload(heartbeat))
            logger.info("Heartbeat sent for %s", heartbeat.agent_id)
            update_state(
                status=heartbeat.status,
                last_seen_at=heartbeat.seen_at,
                pending_change_count=heartbeat.pending_change_count,
            )
            append_recent_event(
                {
                    "event": "heartbeat",
                    "at": heartbeat.seen_at,
                    "pending_change_count": heartbeat.pending_change_count,
                }
            )
        except Exception as exc:
            update_state(last_error=str(exc))
            logger.exception("Agent heartbeat failed")

    @staticmethod
    def _best_effort_sync(client: AgentClient, payload: SyncRequest, logger: logging.Logger) -> None:
        try:
            client.sync(to_payload(payload))
            logger.info("Sync sent with %s changes", len(payload.changes))
            update_state(
                status="running",
                last_sync_at=payload.scanned_at,
                last_sync_change_count=len(payload.changes),
            )
            append_recent_event(
                {
                    "event": "sync",
                    "at": payload.scanned_at,
                    "change_count": len(payload.changes),
                }
            )
        except Exception as exc:
            update_state(last_error=str(exc))
            logger.exception("Agent sync failed")

    @staticmethod
    def _best_effort_process_commands(
        client: AgentClient,
        agent_id: str,
        root_path: str,
        logger: logging.Logger,
    ) -> None:
        try:
            response = client.pull_commands(
                to_payload(CommandPollRequest(agent_id=agent_id, root_path=root_path))
            )
            items = ((response or {}).get("data") or {}).get("items") or []
            if not items:
                return
            for item in items:
                AgentRuntime._execute_command(client, agent_id, item, logger)
        except Exception as exc:
            update_state(last_error=str(exc))
            logger.exception("Agent command polling failed")

    @staticmethod
    def _execute_command(client: AgentClient, agent_id: str, item: dict, logger: logging.Logger) -> None:
        status = str(item.get("status") or "").upper()
        command_id = str(item.get("command_id") or "")
        target_file_path = str(item.get("target_file_path") or "")
        artifact_path = str(item.get("artifact_path") or "")
        payload = dict(item.get("payload") or {})

        try:
            if status == "DISPATCHED":
                artifact = Path(artifact_path)
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_text(
                    json.dumps(
                        {
                            "command_id": command_id,
                            "command_type": item.get("command_type"),
                            "document_title": item.get("document_title"),
                            "target_file_path": target_file_path,
                            "payload": payload,
                            "executed_at": now_utc(),
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                client.post_command_result(
                    to_payload(
                        CommandResultRequest(
                            agent_id=agent_id,
                            command_id=command_id,
                            result_status="ACKNOWLEDGED",
                            executed_at=now_utc(),
                            message="Shared-drive sidecar writeback created",
                            artifact_path=str(artifact),
                            metadata={"target_file_path": target_file_path},
                        )
                    )
                )
                append_recent_event(
                    {
                        "event": "command_acknowledged",
                        "command_id": command_id,
                        "at": now_utc(),
                        "artifact_path": str(artifact),
                    }
                )
                return

            if status == "ROLLBACK_PENDING":
                artifact = Path(artifact_path)
                if artifact.exists():
                    artifact.unlink()
                client.post_command_result(
                    to_payload(
                        CommandResultRequest(
                            agent_id=agent_id,
                            command_id=command_id,
                            result_status="ROLLED_BACK",
                            executed_at=now_utc(),
                            message="Shared-drive sidecar writeback rolled back",
                            artifact_path=str(artifact),
                            metadata={"target_file_path": target_file_path},
                        )
                    )
                )
                append_recent_event(
                    {
                        "event": "command_rolled_back",
                        "command_id": command_id,
                        "at": now_utc(),
                        "artifact_path": str(artifact),
                    }
                )
        except Exception as exc:
            logger.exception("Agent command execution failed for %s", command_id)
            client.try_post_json(
                "/api/agents/commands/result",
                to_payload(
                    CommandResultRequest(
                        agent_id=agent_id,
                        command_id=command_id,
                        result_status="FAILED",
                        executed_at=now_utc(),
                        message="Shared-drive command execution failed",
                        artifact_path=artifact_path or None,
                        failure_reason=str(exc),
                        metadata={"target_file_path": target_file_path},
                    )
                ),
            )


def main_service_loop(root: str, stop_event: threading.Event | None = None) -> None:
    AgentRuntime(Path(root)).run(stop_event)
