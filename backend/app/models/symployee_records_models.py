from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


HoldCategory = Literal["LEGAL", "VALIDATION", "RECORDS", "OPERATIONAL", "OTHER"]
VitalStatus = Literal["NON_VITAL", "VITAL_CANDIDATE", "VITAL", "VITAL_UNDER_REVIEW"]


class SymployeeRecordDeclarationRequest(BaseModel):
    identity_id: str
    version_id: str | None = None
    record_category: str
    owner_user_id: str | None = None
    declaration_reason: str = ""
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordDeclarationEvaluationRequest(BaseModel):
    identity_id: str
    version_id: str | None = None
    trigger_event: str
    dry_run: bool = True
    evaluation_reason: str = ""
    context_overrides_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRepositoryReprocessRequest(BaseModel):
    repository_id: str | None = None
    identity_ids: list[str] = Field(default_factory=list)
    limit: int = 100
    trigger_event: str = "INGESTION"
    dry_run: bool = False
    evaluation_reason: str = ""
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordTimeEvaluationRequest(BaseModel):
    identity_id: str | None = None
    version_id: str | None = None
    limit: int = 100
    evaluation_reason: str = ""
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRetentionAutomationRequest(BaseModel):
    identity_id: str | None = None
    version_id: str | None = None
    limit: int = 100
    evaluation_reason: str = ""
    auto_initiate_disposition: bool = True
    auto_initiate_archive: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeVitalStatusRequest(BaseModel):
    identity_id: str
    vital_status: VitalStatus
    reason: str = ""
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeLegalHoldRequest(BaseModel):
    identity_id: str
    hold_category: HoldCategory | None = None
    hold_code: str
    authority: str
    matter_reference: str | None = None
    reason: str = ""
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeDispositionCaseRequest(BaseModel):
    identity_id: str
    disposition_type: str
    reason: str = ""
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeDispositionApprovalRequest(BaseModel):
    approval_role: Literal["RECORDS", "LEGAL", "BUSINESS_OWNER"]
    comments: str = ""
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeDispositionExecutionRequest(BaseModel):
    execution_outcome: Literal["DESTROY", "ARCHIVE"]
    reason: str = ""
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeArchiveTransferRequest(BaseModel):
    identity_id: str
    archive_destination: str
    disposition_case_id: str | None = None
    preservation_format: str | None = None
    checksum_value: str | None = None
    checksum_algorithm: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeArchiveTransferCompletionRequest(BaseModel):
    receipt_reference: str | None = None
    integrity_verified: bool | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
