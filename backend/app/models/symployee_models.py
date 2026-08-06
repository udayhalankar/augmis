from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SymployeeRecommendationDecisionRequest(BaseModel):
    comments: str = ""
    effective_values: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecommendationRejectRequest(BaseModel):
    comments: str = ""
    reason_code: str | None = None


class SymployeeRecommendationOverrideRequest(BaseModel):
    reason_code: str
    reason_text: str = ""
    after_state: dict[str, Any] = Field(default_factory=dict)


class SymployeeCommandCreateRequest(BaseModel):
    repository_id: str
    agent_id: str | None = None
    identity_id: str
    version_id: str | None = None
    command_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    source_recommendation_id: str | None = None


class SymployeeCommandApprovalRequest(BaseModel):
    comments: str = ""


class SymployeeCommandLifecycleRequest(BaseModel):
    comments: str = ""
    failure_reason: str = ""


class SymployeePolicyCreateRequest(BaseModel):
    policy_domain: str
    policy_code: str
    name: str
    scope_type: str = "tenant"
    scope_ref: str | None = None
    config_json: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    status: str = "DRAFT"


class SymployeePolicyUpdateRequest(BaseModel):
    name: str | None = None
    scope_type: str | None = None
    scope_ref: str | None = None
    config_json: dict[str, Any] | None = None
    is_default: bool | None = None
    status: str | None = None
