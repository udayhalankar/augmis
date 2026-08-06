from __future__ import annotations

import json
from urllib import error, request

from migration_agent.contracts import (
    COMMAND_PULL_ENDPOINT,
    COMMAND_RESULT_ENDPOINT,
    HEARTBEAT_ENDPOINT,
    REGISTER_ENDPOINT,
    SYNC_ENDPOINT,
)


class AgentClient:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def post_json(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8") or "{}")
        except error.HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code} calling {path}: {exc.read().decode('utf-8', 'ignore')}") from exc

    def register(self, payload: dict) -> dict:
        return self.post_json(REGISTER_ENDPOINT, payload)

    def heartbeat(self, payload: dict) -> dict:
        return self.post_json(HEARTBEAT_ENDPOINT, payload)

    def sync(self, payload: dict) -> dict:
        return self.post_json(SYNC_ENDPOINT, payload)

    def pull_commands(self, payload: dict) -> dict:
        return self.post_json(COMMAND_PULL_ENDPOINT, payload)

    def post_command_result(self, payload: dict) -> dict:
        return self.post_json(COMMAND_RESULT_ENDPOINT, payload)

    def try_post_json(self, path: str, payload: dict) -> dict | None:
        try:
            return self.post_json(path, payload)
        except Exception:
            return None
