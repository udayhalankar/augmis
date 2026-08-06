from __future__ import annotations

import argparse
import json
from pathlib import Path

from migration_agent.client import AgentClient
from migration_agent.config import load_config
from migration_agent.contracts import (
    AgentIdentity,
    HeartbeatRequest,
    RegistrationRequest,
    SyncRequest,
    now_utc,
    to_payload,
)
from migration_agent.scanner import scan_root
from migration_agent.service import main_service_loop
from migration_agent.state import get_or_create_agent_id
from migration_agent.watcher import watch_folder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="migration-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan a root folder and print JSON")
    scan_parser.add_argument("--root", required=True, help="Folder to scan")

    heartbeat_parser = subparsers.add_parser("heartbeat", help="Send a heartbeat to the backend")
    heartbeat_parser.add_argument("--root", help="Folder to scan before heartbeat")

    sync_parser = subparsers.add_parser("sync", help="Scan and post inventory to the backend")
    sync_parser.add_argument("--root", required=True, help="Folder to scan")
    sync_parser.add_argument("--endpoint", default="/api/agents/sync", help="Backend sync endpoint")

    watch_parser = subparsers.add_parser("watch", help="Watch a folder and sync changes")
    watch_parser.add_argument("--root", required=True, help="Folder to watch")
    watch_parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds")

    service_parser = subparsers.add_parser("service", help="Run the runtime loop used by a Windows service")
    service_parser.add_argument("--root", required=True, help="Folder to watch")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config()
    agent_id = get_or_create_agent_id()

    if args.command == "scan":
        print(json.dumps(scan_root(Path(args.root)), indent=2))
        return

    if args.command == "heartbeat":
        payload = to_payload(
            HeartbeatRequest(
                agent_id=agent_id,
                seen_at=now_utc(),
                status="ok",
                root_path=args.root or config.root_path or "",
            )
        )
        if not config.backend_url:
            print(json.dumps(payload, indent=2))
            return
        client = AgentClient(config.backend_url, config.token)
        print(json.dumps(client.heartbeat(payload), indent=2))
        return

    if args.command == "sync":
        scan_result = scan_root(Path(args.root))
        payload = to_payload(
            SyncRequest(
                agent_id=agent_id,
                root_path=scan_result["root_path"],
                scanned_at=scan_result["scanned_at"],
                changes=[],
                full_scan=True,
            )
        )
        payload["snapshot"] = scan_result
        if not config.backend_url:
            print(json.dumps(payload, indent=2))
            return
        client = AgentClient(config.backend_url, config.token)
        print(json.dumps(client.post_json(args.endpoint, payload), indent=2))
        return

    if args.command == "watch":
        root = Path(args.root)
        first = True
        for changes in watch_folder(root, args.interval):
            if first:
                print(json.dumps({"event": "watch_started", "root": str(root)}, indent=2))
                first = False
                continue
            print(json.dumps({"event": "changes_detected", "count": len(changes)}, indent=2))
            if config.backend_url:
                client = AgentClient(config.backend_url, config.token)
                payload = to_payload(
                    SyncRequest(
                        agent_id=agent_id,
                        root_path=str(root),
                        scanned_at=now_utc(),
                        changes=changes,
                        full_scan=False,
                    )
                )
                print(json.dumps(client.sync(payload), indent=2))
        return

    if args.command == "service":
        main_service_loop(args.root)
        return


if __name__ == "__main__":
    main()
