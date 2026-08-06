from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SymployeeTransmittalCreateRequest(BaseModel):
    direction: str
    purpose_code: str
    sender_org: str | None = None
    recipient_org: str | None = None
    response_required: bool = False
    response_due_at: datetime | None = None
    workflow_instance_id: str | None = None
    subject: str | None = None
    notes: str | None = None
    transmittal_number: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeTransmittalItemRequest(BaseModel):
    identity_id: str
    version_id: str | None = None
    sequence_no: int = 1
    purpose_code: str | None = None
    response_code: str | None = None
    issue_status: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeAcknowledgementRequest(BaseModel):
    transmittal_id: str
    transmittal_item_id: str | None = None
    recipient_ref: str
    recipient_name: str | None = None
    status: str
    response_status: str | None = None
    due_at: datetime | None = None
    comments: str = ""
