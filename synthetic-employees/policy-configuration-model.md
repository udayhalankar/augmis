# Symployee Document Controller Policy and Configuration Model

## Purpose

This document defines the formal policy and configuration model for the Symployee Document Controller MVP. The objective is to ensure that document control behavior is configuration-driven, tenant-scoped, auditable, and database-backed rather than hardcoded in application logic.

This model applies to:
- document intake and classification
- metadata extraction and validation
- naming and numbering
- revision handling
- workflow routing
- review SLA tracking
- transmittal generation
- register maintenance
- AI recommendation thresholds
- approval and override governance

## Design Principles

1. All business rules must be stored as tenant-scoped configuration records.
2. Every operational decision must resolve against an effective policy version.
3. Policies must support activation windows, versioning, and deprecation without deleting history.
4. Runtime execution must record both the selected policy record and the evaluated outcome.
5. Human approval rules must be separate from AI recommendation rules.
6. Connector writebacks must resolve through explicit policy checks before dispatch.

## Configuration Domains

The policy model is divided into the following configuration domains:

1. Document taxonomy
2. Metadata schemas
3. Naming and numbering rules
4. Revision rules
5. Reviewer matrix and routing
6. SLA rules
7. Transmittal sequencing and templates
8. Register definitions
9. AI confidence thresholds
10. Approval and override policies
11. Connector action policies
12. Retention and archive policies

## Common Control Fields

All configuration entities should support the following base fields:

- `id`
- `tenant_id`
- `code`
- `name`
- `description`
- `status`
- `version_no`
- `effective_from`
- `effective_to`
- `is_default`
- `priority`
- `created_by`
- `approved_by`
- `created_at`
- `updated_at`

Recommended statuses:
- `draft`
- `active`
- `inactive`
- `retired`

## 1. Document Taxonomy

Document taxonomy defines the controlled list of document types and related classification attributes.

### Entity: `document_type_definitions`

Key fields:
- `code`
- `name`
- `category`
- `description`
- `default_confidentiality`
- `default_review_workflow_code`
- `default_register_codes`
- `requires_revision_control`
- `requires_transmittal`
- `allowed_source_types`
- `allowed_file_extensions`
- `validation_profile_code`

Examples:
- drawing
- calculation
- procedure
- method_statement
- inspection_report
- specification
- contract
- letter
- invoice
- minutes
- permit
- risk_assessment
- moc
- hse_report
- engineering_query
- technical_bid
- commercial_bid
- vendor_data_book

### Supporting entity: `classification_attribute_definitions`

This table defines controlled vocabularies for:
- discipline
- department
- originator
- project
- priority
- confidentiality
- package
- work_breakdown_structure

## 2. Metadata Schemas

Metadata schemas define required and optional fields per document profile.

### Entity: `metadata_schema_definitions`

Key fields:
- `code`
- `name`
- `applies_to_document_type_codes`
- `applies_to_repository_types`
- `applies_to_project_types`
- `schema_json`
- `validation_mode`

### Child entity: `metadata_schema_fields`

Key fields:
- `schema_id`
- `field_code`
- `field_label`
- `data_type`
- `source_priority`
- `is_required`
- `is_unique_within_scope`
- `allow_manual_override`
- `default_value_expression`
- `regex_pattern`
- `lookup_source_code`
- `normalization_rule_code`
- `validation_rule_codes`
- `display_order`

Recommended data types:
- `text`
- `integer`
- `decimal`
- `date`
- `datetime`
- `boolean`
- `enum`
- `json`

Recommended source priority values:
- `connector`
- `filename`
- `document_content`
- `ai_extraction`
- `user_input`
- `system_generated`

Validation modes:
- `strict`
- `warn_only`
- `hybrid`

## 3. Naming and Numbering Rules

Naming rules generate file names, titles, and document numbers.

### Entity: `naming_rule_definitions`

Key fields:
- `code`
- `name`
- `applies_to_document_type_codes`
- `applies_to_repository_types`
- `filename_template`
- `document_number_template`
- `segment_separator`
- `revision_format`
- `extension_strategy`
- `normalization_rule_codes`
- `collision_strategy`

Supported template variables should come from metadata and policy context only. Example variables:
- `{project_code}`
- `{discipline}`
- `{document_type_code}`
- `{originator_code}`
- `{sequence_no}`
- `{revision_code}`

Collision strategies:
- `reject`
- `increment_sequence`
- `hold_for_review`

### Supporting entity: `sequence_definitions`

Key fields:
- `code`
- `sequence_scope`
- `prefix`
- `padding_length`
- `next_value`
- `reset_rule`

## 4. Revision Rules

Revision rules define how new versions are identified and processed.

### Entity: `revision_rule_definitions`

Key fields:
- `code`
- `name`
- `revision_pattern`
- `revision_ordering_mode`
- `first_revision_value`
- `allow_skipped_revisions`
- `allow_parallel_revision_streams`
- `requires_change_summary`
- `compare_strategy_code`
- `supersede_previous_version`
- `major_minor_rule`

Revision ordering modes:
- `numeric`
- `alpha`
- `alphanumeric`
- `custom_sequence`

Comparison strategy codes:
- `hash_only`
- `text_diff`
- `layout_diff`
- `drawing_diff`
- `hybrid`

## 5. Reviewer Matrix and Routing

Reviewer matrix rules determine who reviews what and in which order.

### Entity: `review_matrix_definitions`

Key fields:
- `code`
- `name`
- `applies_to_document_type_codes`
- `applies_to_disciplines`
- `applies_to_projects`
- `applies_to_confidentiality_levels`
- `routing_mode`
- `fallback_behavior`

### Child entity: `review_matrix_steps`

Key fields:
- `matrix_id`
- `step_no`
- `step_code`
- `review_role_code`
- `assignment_strategy`
- `min_approvals_required`
- `is_mandatory`
- `can_run_in_parallel`
- `sla_rule_code`
- `escalation_rule_code`

Assignment strategies:
- `named_user`
- `role_pool_round_robin`
- `role_pool_least_loaded`
- `project_responsible`
- `department_head`

Routing modes:
- `sequential`
- `parallel`
- `hybrid`

Fallback behavior should default to `error` for MVP, not silent reassignment.

## 6. SLA Rules

SLA rules define response targets, warning thresholds, and escalation timing.

### Entity: `sla_rule_definitions`

Key fields:
- `code`
- `name`
- `applies_to_workflow_type`
- `applies_to_priority`
- `target_duration_hours`
- `warning_at_percent`
- `overdue_at_percent`
- `calendar_code`
- `pause_conditions`
- `escalation_rule_code`

### Supporting entity: `business_calendar_definitions`

Key fields:
- `code`
- `timezone`
- `working_days`
- `working_hours`
- `holiday_calendar_json`

## 7. Transmittal Sequencing and Templates

Transmittal rules define numbering, document packaging, and output composition.

### Entity: `transmittal_type_definitions`

Key fields:
- `code`
- `name`
- `direction`
- `default_subject_template`
- `default_body_template`
- `numbering_sequence_code`
- `pdf_template_code`
- `requires_acknowledgement`
- `default_distribution_rule_code`

Directions:
- `incoming`
- `outgoing`
- `vendor`
- `client`
- `internal`
- `revision_distribution`

### Supporting entity: `distribution_rule_definitions`

Key fields:
- `code`
- `name`
- `recipient_resolution_mode`
- `recipient_source_json`
- `cc_source_json`
- `ack_required`

## 8. Register Definitions

Register definitions control the structure and inclusion rules for generated registers.

### Entity: `register_definitions`

Key fields:
- `code`
- `name`
- `description`
- `register_type`
- `included_document_type_codes`
- `included_statuses`
- `column_config_json`
- `filter_config_json`
- `sort_config_json`
- `snapshot_mode`

Register types:
- `master_document_register`
- `drawing_register`
- `vendor_register`
- `engineering_register`
- `as_built_register`
- `handover_register`
- `submittal_register`
- `moc_register`
- `inspection_register`

Snapshot modes:
- `live`
- `scheduled_snapshot`
- `approval_snapshot`

## 9. AI Confidence Thresholds

Confidence thresholds define what happens after AI classification or extraction.

### Entity: `ai_policy_definitions`

Key fields:
- `code`
- `name`
- `policy_area`
- `model_profile_code`
- `prompt_profile_code`
- `auto_recommend_min_confidence`
- `manual_review_min_confidence`
- `hard_fail_below_confidence`
- `allow_auto_route`
- `allow_auto_create_task`
- `allow_auto_prepare_writeback`

Policy areas:
- `classification`
- `metadata_extraction`
- `duplicate_detection`
- `revision_comparison`
- `workflow_planning`
- `transmittal_drafting`

Recommended MVP defaults:
- `>= 0.85` create AI recommendation
- `0.60 - 0.84` create recommendation and force human review
- `< 0.60` no recommendation, route to manual processing

## 10. Approval and Override Policies

Approval policies govern who can approve, reject, return, or override.

### Entity: `approval_policy_definitions`

Key fields:
- `code`
- `name`
- `applies_to_action_types`
- `approval_mode`
- `min_approvers_required`
- `eligible_role_codes`
- `segregation_of_duties_rules`
- `requires_second_approval_for_override`
- `requires_writeback_reapproval`

Approval modes:
- `single`
- `dual`
- `multi_step`

### Supporting entity: `override_policy_definitions`

Key fields:
- `code`
- `name`
- `allowed_role_codes`
- `allowed_action_types`
- `mandatory_reason_codes`
- `requires_secondary_review`
- `audit_severity`

Human override rules for MVP:
- override must capture user, reason, timestamp, before/after values, and related recommendation id
- override of any connector writeback must require second approval unless policy explicitly states otherwise

## 11. Connector Action Policies

Connector action policies govern permitted writebacks by source system and action type.

### Entity: `connector_action_policy_definitions`

Key fields:
- `code`
- `name`
- `repository_type`
- `action_type`
- `is_enabled`
- `approval_policy_code`
- `payload_schema_json`
- `allowed_execution_window`
- `retry_policy_code`
- `rollback_policy_code`

Recommended action types:
- `update_metadata`
- `rename_source_file`
- `move_source_file`
- `upload_new_version`
- `create_transmittal_record`
- `send_email`
- `archive_document`

## 12. Retention and Archive Policies

Retention rules define when documents and workflow artifacts can move to archived state.

### Entity: `retention_policy_definitions`

Key fields:
- `code`
- `name`
- `applies_to_document_type_codes`
- `retention_trigger`
- `retention_period_days`
- `archive_location_rule`
- `purge_behavior`

Purge behavior should be disabled for MVP. Archive only.

## Policy Resolution Order

At runtime, the effective policy should be resolved in the following order:

1. tenant + project-specific rule
2. tenant + repository-type rule
3. tenant default rule
4. global platform default

If no active rule is found, the system must return an explicit error rather than silently applying a fallback.

## Required Runtime Linkage

The following operational records must store policy references:

- document classification result
- metadata validation result
- revision comparison result
- workflow creation
- workflow task creation
- AI recommendation
- approval decision
- connector command
- transmittal
- register snapshot

Each record should store:
- `policy_code`
- `policy_version_no`
- `policy_snapshot_json`

## Governance Requirements

1. Policy changes must be versioned and auditable.
2. Active policies must be promotable from draft only through approval.
3. Existing operational records must not be retroactively reinterpreted after policy changes.
4. All AI recommendations must store the exact model profile and prompt profile used.
5. Every connector command must store the approval policy and connector action policy used at dispatch time.

## MVP Scope Decision

The MVP should implement these policy domains first:

1. document taxonomy
2. metadata schemas
3. naming rules
4. revision rules
5. review matrix
6. SLA rules
7. AI confidence thresholds
8. approval policies
9. connector action policies for shared drive only
10. master document register definition

The following can remain defined in the model but delayed in implementation:
- advanced retention policies
- OTCS writeback policies
- SharePoint writeback policies
- complex distribution rules
- multi-calendar SLA logic
