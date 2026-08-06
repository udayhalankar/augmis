from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SymployeeLifecycleEventListRequest(BaseModel):
    identity_id: str | None = None
    version_id: str | None = None
    state_dimension: str | None = None
    event_type: str | None = None
    limit: int = 100


class SymployeeLifecycleTransitionRequest(BaseModel):
    identity_id: str
    version_id: str | None = None
    state_dimension: str
    new_state: str
    reason: str = ""
    metadata_json: dict[str, Any] = Field(default_factory=dict)
