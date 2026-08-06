from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SymployeeConfigScopeModel(BaseModel):
    repository_id: str | None = None
    business_area: str | None = None
    document_type: str | None = None
    status: str = "DRAFT"
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    version_no: int = 1
    is_current_version: bool = True
    rule_priority: int = 100
    config_payload_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeConfigScopeUpdateModel(BaseModel):
    repository_id: str | None = None
    business_area: str | None = None
    document_type: str | None = None
    status: str | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    version_no: int | None = None
    is_current_version: bool | None = None
    rule_priority: int | None = None
    config_payload_json: dict[str, Any] | None = None


class SymployeeConfigResponseModel(BaseModel):
    created_by: str | None = None
    created_at: datetime | None = None
    modified_by: str | None = None
    modified_at: datetime | None = None


class SymployeeConfigResolutionPreviewRequest(BaseModel):
    repository_id: str | None = None
    business_area: str | None = None
    project_code: str | None = None
    document_type: str | None = None
    as_of: datetime | None = None
    current_only: bool = True
    match_fields: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordCategoryCreate(SymployeeConfigScopeModel):
    category_code: str
    category_name: str
    category_description: str | None = None
    parent_category_code: str | None = None
    security_classification_default: str | None = None
    retention_schedule_code_default: str | None = None
    vital_policy_code_default: str | None = None
    hold_policy_code_default: str | None = None
    disposition_policy_code_default: str | None = None
    archive_policy_code_default: str | None = None


class SymployeeRecordCategoryUpdate(SymployeeConfigScopeUpdateModel):
    category_code: str | None = None
    category_name: str | None = None
    category_description: str | None = None
    parent_category_code: str | None = None
    security_classification_default: str | None = None
    retention_schedule_code_default: str | None = None
    vital_policy_code_default: str | None = None
    hold_policy_code_default: str | None = None
    disposition_policy_code_default: str | None = None
    archive_policy_code_default: str | None = None


class SymployeeRecordCategoryResponse(SymployeeConfigResponseModel):
    record_category_id: str
    tenant_id: str
    repository_id: str | None = None
    business_area: str | None = None
    document_type: str | None = None
    category_code: str
    category_name: str
    category_description: str | None = None
    parent_category_code: str | None = None
    security_classification_default: str | None = None
    retention_schedule_code_default: str | None = None
    vital_policy_code_default: str | None = None
    hold_policy_code_default: str | None = None
    disposition_policy_code_default: str | None = None
    archive_policy_code_default: str | None = None
    status: str
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    version_no: int
    is_current_version: bool
    rule_priority: int
    config_payload_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordDeclarationRuleCreate(SymployeeConfigScopeModel):
    rule_code: str
    rule_name: str
    rule_description: str | None = None
    record_category_code: str
    declaration_mode: str = "CANDIDATE_FIRST"
    approval_required: bool = False
    approval_role_code: str | None = None
    candidate_trigger_event: str
    declaration_trigger_event: str
    metadata_requirements_json: dict[str, Any] = Field(default_factory=dict)
    matching_criteria_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordDeclarationRuleUpdate(SymployeeConfigScopeUpdateModel):
    rule_code: str | None = None
    rule_name: str | None = None
    rule_description: str | None = None
    record_category_code: str | None = None
    declaration_mode: str | None = None
    approval_required: bool | None = None
    approval_role_code: str | None = None
    candidate_trigger_event: str | None = None
    declaration_trigger_event: str | None = None
    metadata_requirements_json: dict[str, Any] | None = None
    matching_criteria_json: dict[str, Any] | None = None


class SymployeeRecordDeclarationRuleResponse(SymployeeConfigResponseModel):
    declaration_rule_id: str
    tenant_id: str
    repository_id: str | None = None
    business_area: str | None = None
    document_type: str | None = None
    rule_code: str
    rule_name: str
    rule_description: str | None = None
    record_category_code: str
    declaration_mode: str
    approval_required: bool
    approval_role_code: str | None = None
    candidate_trigger_event: str
    declaration_trigger_event: str
    metadata_requirements_json: dict[str, Any] = Field(default_factory=dict)
    matching_criteria_json: dict[str, Any] = Field(default_factory=dict)
    status: str
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    version_no: int
    is_current_version: bool
    rule_priority: int
    config_payload_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordLifecycleRuleCreate(SymployeeConfigScopeModel):
    rule_code: str
    rule_name: str
    rule_description: str | None = None
    record_category_code: str | None = None
    active_start_event: str
    inactive_eligibility_event: str
    inactive_after_days: int | None = None
    inactive_override_required: bool = False
    reopen_to_active_allowed: bool = False
    reopen_trigger_events_json: list[str] = Field(default_factory=list)
    lifecycle_clock_basis: str | None = None


class SymployeeRecordLifecycleRuleUpdate(SymployeeConfigScopeUpdateModel):
    rule_code: str | None = None
    rule_name: str | None = None
    rule_description: str | None = None
    record_category_code: str | None = None
    active_start_event: str | None = None
    inactive_eligibility_event: str | None = None
    inactive_after_days: int | None = None
    inactive_override_required: bool | None = None
    reopen_to_active_allowed: bool | None = None
    reopen_trigger_events_json: list[str] | None = None
    lifecycle_clock_basis: str | None = None


class SymployeeRecordLifecycleRuleResponse(SymployeeConfigResponseModel):
    lifecycle_rule_id: str
    tenant_id: str
    repository_id: str | None = None
    business_area: str | None = None
    document_type: str | None = None
    rule_code: str
    rule_name: str
    rule_description: str | None = None
    record_category_code: str | None = None
    active_start_event: str
    inactive_eligibility_event: str
    inactive_after_days: int | None = None
    inactive_override_required: bool
    reopen_to_active_allowed: bool
    reopen_trigger_events_json: list[str] = Field(default_factory=list)
    lifecycle_clock_basis: str | None = None
    status: str
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    version_no: int
    is_current_version: bool
    rule_priority: int
    config_payload_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRetentionScheduleCreate(SymployeeConfigScopeModel):
    schedule_code: str
    schedule_name: str
    schedule_description: str | None = None
    record_category_code: str | None = None
    retention_start_event: str
    retention_period_value: int
    retention_period_unit: str
    review_required: bool = False
    review_offset_value: int | None = None
    review_offset_unit: str | None = None
    suspend_on_hold: bool = False
    final_disposition_policy_code: str


class SymployeeRetentionScheduleUpdate(SymployeeConfigScopeUpdateModel):
    schedule_code: str | None = None
    schedule_name: str | None = None
    schedule_description: str | None = None
    record_category_code: str | None = None
    retention_start_event: str | None = None
    retention_period_value: int | None = None
    retention_period_unit: str | None = None
    review_required: bool | None = None
    review_offset_value: int | None = None
    review_offset_unit: str | None = None
    suspend_on_hold: bool | None = None
    final_disposition_policy_code: str | None = None


class SymployeeRetentionScheduleResponse(SymployeeConfigResponseModel):
    retention_schedule_id: str
    tenant_id: str
    repository_id: str | None = None
    business_area: str | None = None
    document_type: str | None = None
    schedule_code: str
    schedule_name: str
    schedule_description: str | None = None
    record_category_code: str | None = None
    retention_start_event: str
    retention_period_value: int
    retention_period_unit: str
    review_required: bool
    review_offset_value: int | None = None
    review_offset_unit: str | None = None
    suspend_on_hold: bool
    final_disposition_policy_code: str
    status: str
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    version_no: int
    is_current_version: bool
    rule_priority: int
    config_payload_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordVitalPolicyCreate(SymployeeConfigScopeModel):
    policy_code: str
    policy_name: str
    policy_description: str | None = None
    record_category_code: str | None = None
    classification_mode: str = "RULE_DRIVEN"
    default_vital_flag: bool = False
    review_required: bool = False
    review_role_code: str | None = None
    review_interval_days: int | None = None
    criteria_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordVitalPolicyUpdate(SymployeeConfigScopeUpdateModel):
    policy_code: str | None = None
    policy_name: str | None = None
    policy_description: str | None = None
    record_category_code: str | None = None
    classification_mode: str | None = None
    default_vital_flag: bool | None = None
    review_required: bool | None = None
    review_role_code: str | None = None
    review_interval_days: int | None = None
    criteria_json: dict[str, Any] | None = None


class SymployeeRecordVitalPolicyResponse(SymployeeConfigResponseModel):
    vital_policy_id: str
    tenant_id: str
    repository_id: str | None = None
    business_area: str | None = None
    document_type: str | None = None
    policy_code: str
    policy_name: str
    policy_description: str | None = None
    record_category_code: str | None = None
    classification_mode: str
    default_vital_flag: bool
    review_required: bool
    review_role_code: str | None = None
    review_interval_days: int | None = None
    criteria_json: dict[str, Any] = Field(default_factory=dict)
    status: str
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    version_no: int
    is_current_version: bool
    rule_priority: int
    config_payload_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordHoldPolicyCreate(SymployeeConfigScopeModel):
    policy_code: str
    policy_name: str
    policy_description: str | None = None
    record_category_code: str | None = None
    hold_category: str
    placement_role_code: str
    release_role_code: str | None = None
    matter_reference_required: bool = False
    reason_required: bool = False
    blocks_disposition: bool = False
    blocks_archive_transfer: bool = False
    default_expiry_mode: str | None = None
    criteria_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordHoldPolicyUpdate(SymployeeConfigScopeUpdateModel):
    policy_code: str | None = None
    policy_name: str | None = None
    policy_description: str | None = None
    record_category_code: str | None = None
    hold_category: str | None = None
    placement_role_code: str | None = None
    release_role_code: str | None = None
    matter_reference_required: bool | None = None
    reason_required: bool | None = None
    blocks_disposition: bool | None = None
    blocks_archive_transfer: bool | None = None
    default_expiry_mode: str | None = None
    criteria_json: dict[str, Any] | None = None


class SymployeeRecordHoldPolicyResponse(SymployeeConfigResponseModel):
    hold_policy_id: str
    tenant_id: str
    repository_id: str | None = None
    business_area: str | None = None
    document_type: str | None = None
    policy_code: str
    policy_name: str
    policy_description: str | None = None
    record_category_code: str | None = None
    hold_category: str
    placement_role_code: str
    release_role_code: str | None = None
    matter_reference_required: bool
    reason_required: bool
    blocks_disposition: bool
    blocks_archive_transfer: bool
    default_expiry_mode: str | None = None
    criteria_json: dict[str, Any] = Field(default_factory=dict)
    status: str
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    version_no: int
    is_current_version: bool
    rule_priority: int
    config_payload_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordDispositionPolicyCreate(SymployeeConfigScopeModel):
    policy_code: str
    policy_name: str
    policy_description: str | None = None
    record_category_code: str | None = None
    allowed_outcome: str = "MIXED"
    approval_required: bool = False
    records_approval_required: bool = False
    legal_approval_required: bool = False
    business_owner_approval_required: bool = False
    evidence_requirements_json: dict[str, Any] = Field(default_factory=dict)
    blocked_by_active_hold: bool = False
    disposition_execution_role_code: str


class SymployeeRecordDispositionPolicyUpdate(SymployeeConfigScopeUpdateModel):
    policy_code: str | None = None
    policy_name: str | None = None
    policy_description: str | None = None
    record_category_code: str | None = None
    allowed_outcome: str | None = None
    approval_required: bool | None = None
    records_approval_required: bool | None = None
    legal_approval_required: bool | None = None
    business_owner_approval_required: bool | None = None
    evidence_requirements_json: dict[str, Any] | None = None
    blocked_by_active_hold: bool | None = None
    disposition_execution_role_code: str | None = None


class SymployeeRecordDispositionPolicyResponse(SymployeeConfigResponseModel):
    disposition_policy_id: str
    tenant_id: str
    repository_id: str | None = None
    business_area: str | None = None
    document_type: str | None = None
    policy_code: str
    policy_name: str
    policy_description: str | None = None
    record_category_code: str | None = None
    allowed_outcome: str
    approval_required: bool
    records_approval_required: bool
    legal_approval_required: bool
    business_owner_approval_required: bool
    evidence_requirements_json: dict[str, Any] = Field(default_factory=dict)
    blocked_by_active_hold: bool
    disposition_execution_role_code: str
    status: str
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    version_no: int
    is_current_version: bool
    rule_priority: int
    config_payload_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordArchivePolicyCreate(SymployeeConfigScopeModel):
    policy_code: str
    policy_name: str
    policy_description: str | None = None
    record_category_code: str | None = None
    transfer_required: bool = False
    destination_code: str
    package_format_code: str
    checksum_required: bool = False
    metadata_profile_code: str
    preservation_review_interval_days: int | None = None
    receipt_confirmation_required: bool = False
    criteria_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordArchivePolicyUpdate(SymployeeConfigScopeUpdateModel):
    policy_code: str | None = None
    policy_name: str | None = None
    policy_description: str | None = None
    record_category_code: str | None = None
    transfer_required: bool | None = None
    destination_code: str | None = None
    package_format_code: str | None = None
    checksum_required: bool | None = None
    metadata_profile_code: str | None = None
    preservation_review_interval_days: int | None = None
    receipt_confirmation_required: bool | None = None
    criteria_json: dict[str, Any] | None = None


class SymployeeRecordArchivePolicyResponse(SymployeeConfigResponseModel):
    archive_policy_id: str
    tenant_id: str
    repository_id: str | None = None
    business_area: str | None = None
    document_type: str | None = None
    policy_code: str
    policy_name: str
    policy_description: str | None = None
    record_category_code: str | None = None
    transfer_required: bool
    destination_code: str
    package_format_code: str
    checksum_required: bool
    metadata_profile_code: str
    preservation_review_interval_days: int | None = None
    receipt_confirmation_required: bool
    criteria_json: dict[str, Any] = Field(default_factory=dict)
    status: str
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    version_no: int
    is_current_version: bool
    rule_priority: int
    config_payload_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordAssignmentRuleCreate(SymployeeConfigScopeModel):
    rule_code: str
    rule_name: str
    rule_description: str | None = None
    project_code: str | None = None
    record_category_code: str | None = None
    assignment_context: str
    owner_role_code: str | None = None
    performer_role_code: str | None = None
    approver_role_code: str | None = None
    escalation_role_code: str | None = None
    fallback_role_code: str | None = None
    assignment_logic_json: dict[str, Any] = Field(default_factory=dict)


class SymployeeRecordAssignmentRuleUpdate(SymployeeConfigScopeUpdateModel):
    rule_code: str | None = None
    rule_name: str | None = None
    rule_description: str | None = None
    project_code: str | None = None
    record_category_code: str | None = None
    assignment_context: str | None = None
    owner_role_code: str | None = None
    performer_role_code: str | None = None
    approver_role_code: str | None = None
    escalation_role_code: str | None = None
    fallback_role_code: str | None = None
    assignment_logic_json: dict[str, Any] | None = None


class SymployeeRecordAssignmentRuleResponse(SymployeeConfigResponseModel):
    assignment_rule_id: str
    tenant_id: str
    repository_id: str | None = None
    business_area: str | None = None
    project_code: str | None = None
    document_type: str | None = None
    rule_code: str
    rule_name: str
    rule_description: str | None = None
    record_category_code: str | None = None
    assignment_context: str
    owner_role_code: str | None = None
    performer_role_code: str | None = None
    approver_role_code: str | None = None
    escalation_role_code: str | None = None
    fallback_role_code: str | None = None
    assignment_logic_json: dict[str, Any] = Field(default_factory=dict)
    status: str
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    version_no: int
    is_current_version: bool
    rule_priority: int
    config_payload_json: dict[str, Any] = Field(default_factory=dict)
