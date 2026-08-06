from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4


def get_agent_data_dir() -> Path:
    candidates = []
    program_data = os.getenv("PROGRAMDATA")
    if program_data:
        candidates.append(Path(program_data) / "MigrationAgent")
    candidates.append(Path(__file__).resolve().parents[2] / ".runtime")
    candidates.append(Path(tempfile.gettempdir()) / "MigrationAgent")

    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return path
        except OSError:
            continue
    raise OSError("Unable to resolve a writable migration-agent runtime directory.")


def get_state_path() -> Path:
    return get_agent_data_dir() / "agent-state.json"


def load_state() -> dict[str, Any]:
    state_path = get_state_path()
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict[str, Any]) -> None:
    state_path = get_state_path()
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def update_state(**updates: Any) -> dict[str, Any]:
    state = load_state()
    state.update(updates)
    save_state(state)
    return state


def append_recent_event(event: dict[str, Any], max_items: int = 50) -> dict[str, Any]:
    state = load_state()
    recent_events = list(state.get("recent_events") or [])
    recent_events.insert(0, event)
    state["recent_events"] = recent_events[:max_items]
    save_state(state)
    return state


def get_or_create_agent_id() -> str:
    state = load_state()
    agent_id = state.get("agent_id")
    if agent_id:
        return str(agent_id)
    agent_id = f"agent-{uuid4()}"
    state["agent_id"] = agent_id
    save_state(state)
    return agent_id
