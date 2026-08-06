# Symployee Document Controller Domain Entities

## Scope

This document defines the primary domain entities for the Symployee Document Controller MVP and the separation boundaries that must hold during implementation.

## Entity Groups

1. Governance and configuration
2. Identity and source tracking
3. Document content and versioning
4. AI recommendation and evidence
5. Workflow and approvals
6. Connector command execution
7. Registers and reporting
8. Audit and idempotency

## Governance and Configuration

### `synthetic_employee_definitions`

Represents the configured Symployee identity, role, instructions, permissions, and operating policies.

Minimum fields:
- `id`
- `tenant_id`
- `code`
- `name`
- `employee_type`
- `status`
- `instruction_profile_code`
- `permission_profile_json`
- `default_policy_set_code`

### `policy_sets`

Logical grouping of active policies resolved together for a tenant, project, or repository scope.

Minimum fields:
- `id`
- `tenant_id`
- `code`
- `name`
- `scope_type`
- `scope_ref`
- `status`
- `version_no`

## Identity and Source Tracking

### `document_identities`

Represents the logical document independent of storage location or revision.

Purpose:
- stable business identity
- register anchor record
- workflow anchor record

Minimum fields:
- `id`
- `tenant_id`
- `repository_id`
- `canonical_document_number`
- `title`
- `document_type_code`
- `discipline_code`
- `project_code`
- `originator_code`
- `status`
- `current_version_id`

### `document_source_objects`

Represents source-system objects or paths associated with a logical document.

Purpose:
- capture external object identifiers
- allow same document to move or exist in multiple source systems

Minimum fields:
- `id`
- `tenant_id`
- `document_identity_id`
- `repository_id`
- `source_system_type`
- `source_object_id`
- `source_path`
- `source_version_ref`
- `is_active`
- `first_seen_at`
- `last_seen_at`

### `connector_events`

Represents inbound file or object events from connector agents.

Purpose:
- persist raw intake requests
- enforce idempotency
- support replay and diagnostics

Minimum fields:
- `id`
- `tenant_id`
- `agent_id`
- `repository_id`
- `event_key`
- `event_type`
- `idempotency_key`
- `source_object_id`
- `source_path`
- `file_hash`
- `payload_json`
- `received_at`
- `processed_at`
- `processing_status`

## Document Content and Versioning

### `document_versions`

Represents a specific revision or content instance of a logical document.

Minimum fields:
- `id`
- `tenant_id`
- `document_identity_id`
- `revision_code`
- `version_label`
- `file_name`
- `file_extension`
- `mime_type`
- `file_hash`
- `page_count`
- `storage_object_key`
- `extracted_text_key`
- `status`
- `supersedes_version_id`
- `created_at`

### `document_metadata_values`

Represents normalized metadata for the current or historical version.

Minimum fields:
- `id`
- `tenant_id`
- `document_version_id`
- `schema_id`
- `field_code`
- `field_value_json`
- `value_source`
- `is_final`
- `is_overridden`

### `revision_comparisons`

Represents comparison runs between two versions.

Minimum fields:
- `id`
- `tenant_id`
- `document_identity_id`
- `base_version_id`
- `target_version_id`
- `compare_strategy_code`
- `status`
- `summary_json`
- `change_count`
- `confidence_score`
- `created_at`

### `revision_comparison_artifacts`

Represents structured diff evidence produced by revision analysis.

Minimum fields:
- `id`
- `tenant_id`
- `revision_comparison_id`
- `artifact_type`
- `page_ref`
- `section_ref`
- `before_value`
- `after_value`
- `evidence_json`
- `severity`

Artifact types:
- `added_page`
- `deleted_page`
- `text_change`
- `table_change`
- `drawing_change`
- `dimension_change`
- `signature_change`
- `approval_page_change`

## AI Recommendation and Evidence

### `ai_recommendations`

Represents AI-produced operational recommendations, never direct execution.

Minimum fields:
- `id`
- `tenant_id`
- `synthetic_employee_id`
- `document_identity_id`
- `document_version_id`
- `recommendation_type`
- `status`
- `recommendation_json`
- `confidence_score`
- `model_name`
- `model_provider`
- `prompt_profile_code`
- `prompt_version`
- `policy_code`
- `policy_version_no`
- `source_evidence_json`
- `created_at`

Recommendation types:
- `classification`
- `metadata_extraction`
- `duplicate_candidate`
- `revision_summary`
- `workflow_plan`
- `transmittal_draft`
- `register_update`
- `connector_action_plan`

### `ai_recommendation_evidence`

Represents structured evidence lines used by a recommendation.

Minimum fields:
- `id`
- `tenant_id`
- `recommendation_id`
- `evidence_type`
- `source_ref`
- `excerpt_text`
- `metadata_json`

### `prompt_profiles`

Represents governed prompt configuration.

Minimum fields:
- `id`
- `tenant_id`
- `code`
- `name`
- `prompt_family`
- `version_no`
- `template_text`
- `response_schema_json`
- `status`

## Workflow and Approvals

### `workflow_instances`

Represents a workflow for intake, review, approval, transmittal, or archival.

Minimum fields:
- `id`
- `tenant_id`
- `document_identity_id`
- `workflow_type`
- `status`
- `policy_code`
- `policy_version_no`
- `started_at`
- `closed_at`

### `workflow_tasks`

Represents human or system workflow work items only.

Rule:
- workflow tasks must not act as connector commands
- workflow tasks must not be the system of record for AI actions

Minimum fields:
- `id`
- `tenant_id`
- `workflow_instance_id`
- `task_type`
- `title`
- `assigned_role_code`
- `assigned_user_id`
- `status`
- `due_at`
- `task_payload_json`

### `approval_records`

Represents approval decisions on recommendations, workflows, or commands.

Minimum fields:
- `id`
- `tenant_id`
- `approval_subject_type`
- `approval_subject_id`
- `decision`
- `approver_user_id`
- `comments`
- `policy_code`
- `policy_version_no`
- `created_at`

Approval subject types:
- `workflow_task`
- `ai_recommendation`
- `connector_command`
- `transmittal`
- `override`

### `override_records`

Represents explicit human override of AI or workflow outcome.

Minimum fields:
- `id`
- `tenant_id`
- `override_subject_type`
- `override_subject_id`
- `related_recommendation_id`
- `overridden_by_user_id`
- `reason_code`
- `reason_text`
- `before_state_json`
- `after_state_json`
- `requires_second_approval`
- `finalized_at`

## Connector Command Execution

### `connector_commands`

Represents approved writeback instructions sent to a connector agent.

This is a separate operational ledger from workflow tasks.

Minimum fields:
- `id`
- `tenant_id`
- `agent_id`
- `repository_id`
- `document_identity_id`
- `document_version_id`
- `command_type`
- `status`
- `approval_status`
- `payload_json`
- `policy_code`
- `policy_version_no`
- `approved_at`
- `dispatched_at`
- `acknowledged_at`
- `failed_at`
- `failure_reason`

Recommended statuses:
- `pending_approval`
- `approved`
- `dispatched`
- `acknowledged`
- `failed`
- `rolled_back`
- `cancelled`

### `connector_command_results`

Represents execution receipts from connector agents.

Minimum fields:
- `id`
- `tenant_id`
- `connector_command_id`
- `agent_id`
- `result_status`
- `result_payload_json`
- `received_at`

## Registers and Reporting

### `register_snapshots`

Represents generated register views and exports.

Minimum fields:
- `id`
- `tenant_id`
- `register_code`
- `snapshot_mode`
- `generated_at`
- `generated_by_type`
- `filter_context_json`
- `row_count`
- `storage_key`

### `transmittal_records`

Represents transmittals prepared or issued by the platform.

Minimum fields:
- `id`
- `tenant_id`
- `document_identity_id`
- `transmittal_type_code`
- `transmittal_number`
- `status`
- `draft_payload_json`
- `issued_at`

## Audit and Idempotency

### `audit_logs`

Represents append-only event history.

Rules:
- no update in normal operations
- no delete in normal operations
- corrections are new append entries, not mutation

Minimum fields:
- `id`
- `tenant_id`
- `actor_type`
- `actor_id`
- `action_code`
- `entity_type`
- `entity_id`
- `before_state_json`
- `after_state_json`
- `context_json`
- `created_at`

### `idempotency_records`

Represents dedupe protection for inbound and outbound commands.

Minimum fields:
- `id`
- `tenant_id`
- `scope_type`
- `scope_key`
- `idempotency_key`
- `first_seen_at`
- `last_seen_at`
- `resolution_status`

## Separation Rules

These boundaries must be preserved:

1. `document_identities` is not the same as `document_versions`.
2. `document_source_objects` is not the same as `document_identities`.
3. `ai_recommendations` is not the same as `approval_records`.
4. `workflow_tasks` is not the same as `connector_commands`.
5. `revision_comparisons` is not the same as `revision_comparison_artifacts`.
6. `audit_logs` is not a mutable operational table.

## MVP Must-Have Entities

If scope needs to be reduced, these are still mandatory:
- `document_identities`
- `document_source_objects`
- `document_versions`
- `connector_events`
- `ai_recommendations`
- `workflow_instances`
- `workflow_tasks`
- `approval_records`
- `override_records`
- `connector_commands`
- `audit_logs`
- `idempotency_records`
