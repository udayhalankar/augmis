# Symployee Document Controller State Machines

## Purpose

This document defines the required lifecycle states for the main operational entities in the Symployee Document Controller MVP.

## 1. Connector Event State Machine

Entity: `connector_events`

States:
- `received`
- `validated`
- `deduplicated`
- `accepted`
- `rejected`
- `processed`
- `failed`

Transitions:
- `received -> validated`
- `validated -> deduplicated`
- `deduplicated -> accepted`
- `deduplicated -> rejected`
- `accepted -> processed`
- `accepted -> failed`

Notes:
- duplicate events must move to `rejected` with reason `duplicate_event`
- raw event payload must be preserved even for rejected events

## 2. Document Identity State Machine

Entity: `document_identities`

States:
- `registered`
- `under_review`
- `approved`
- `rejected`
- `issued`
- `superseded`
- `archived`

Transitions:
- `registered -> under_review`
- `under_review -> approved`
- `under_review -> rejected`
- `approved -> issued`
- `approved -> superseded`
- `issued -> superseded`
- `superseded -> archived`
- `approved -> archived`

Notes:
- state applies to current business status of the logical document, not file processing state

## 3. Document Version State Machine

Entity: `document_versions`

States:
- `registered`
- `stored`
- `text_extracted`
- `classified`
- `metadata_validated`
- `workflow_planned`
- `active`
- `superseded`
- `processing_failed`

Transitions:
- `registered -> stored`
- `stored -> text_extracted`
- `text_extracted -> classified`
- `classified -> metadata_validated`
- `metadata_validated -> workflow_planned`
- `workflow_planned -> active`
- `active -> superseded`
- `stored -> processing_failed`
- `text_extracted -> processing_failed`
- `classified -> processing_failed`
- `metadata_validated -> processing_failed`

Notes:
- `processing_failed` means operational pipeline failed, not that the business document is rejected

## 4. AI Recommendation State Machine

Entity: `ai_recommendations`

States:
- `drafted`
- `published`
- `needs_review`
- `approved`
- `rejected`
- `superseded`
- `expired`

Transitions:
- `drafted -> published`
- `published -> needs_review`
- `published -> approved`
- `published -> rejected`
- `needs_review -> approved`
- `needs_review -> rejected`
- `approved -> superseded`
- `published -> expired`

Notes:
- a recommendation can be approved without immediate command dispatch
- recommendation approval does not equal writeback execution

## 5. Workflow Instance State Machine

Entity: `workflow_instances`

States:
- `open`
- `in_progress`
- `waiting_approval`
- `completed`
- `returned`
- `cancelled`
- `failed`

Transitions:
- `open -> in_progress`
- `in_progress -> waiting_approval`
- `waiting_approval -> completed`
- `waiting_approval -> returned`
- `open -> cancelled`
- `in_progress -> failed`

## 6. Workflow Task State Machine

Entity: `workflow_tasks`

States:
- `pending`
- `assigned`
- `in_progress`
- `completed`
- `returned`
- `cancelled`
- `overdue`

Transitions:
- `pending -> assigned`
- `assigned -> in_progress`
- `in_progress -> completed`
- `in_progress -> returned`
- `assigned -> overdue`
- `in_progress -> overdue`
- `pending -> cancelled`

Notes:
- overdue is a live operational state driven by SLA clock

## 7. Approval Record State Machine

Entity: `approval_records`

States:
- `submitted`
- `approved`
- `rejected`
- `returned`
- `voided`

Transitions:
- `submitted -> approved`
- `submitted -> rejected`
- `submitted -> returned`
- `submitted -> voided`

## 8. Override Record State Machine

Entity: `override_records`

States:
- `requested`
- `pending_second_approval`
- `effective`
- `rejected`
- `withdrawn`

Transitions:
- `requested -> pending_second_approval`
- `requested -> effective`
- `pending_second_approval -> effective`
- `pending_second_approval -> rejected`
- `requested -> withdrawn`

Notes:
- if policy requires second approval, override must not become effective directly

## 9. Connector Command State Machine

Entity: `connector_commands`

States:
- `pending_approval`
- `approved`
- `dispatched`
- `acknowledged`
- `failed`
- `rolled_back`
- `cancelled`

Transitions:
- `pending_approval -> approved`
- `approved -> dispatched`
- `dispatched -> acknowledged`
- `dispatched -> failed`
- `failed -> rolled_back`
- `pending_approval -> cancelled`
- `approved -> cancelled`

Notes:
- connector commands are operational writeback units
- command creation can originate from approved recommendation or approved manual action
- commands must carry idempotency keys

## 10. Revision Comparison State Machine

Entity: `revision_comparisons`

States:
- `queued`
- `running`
- `completed`
- `needs_review`
- `failed`

Transitions:
- `queued -> running`
- `running -> completed`
- `running -> needs_review`
- `running -> failed`

## 11. Transmittal State Machine

Entity: `transmittal_records`

States:
- `draft`
- `pending_approval`
- `approved`
- `issued`
- `acknowledged`
- `rejected`
- `cancelled`

Transitions:
- `draft -> pending_approval`
- `pending_approval -> approved`
- `approved -> issued`
- `issued -> acknowledged`
- `pending_approval -> rejected`
- `draft -> cancelled`

## 12. Register Snapshot State Machine

Entity: `register_snapshots`

States:
- `queued`
- `generating`
- `ready`
- `failed`

Transitions:
- `queued -> generating`
- `generating -> ready`
- `generating -> failed`

## State Integrity Rules

1. A `connector_command` cannot reach `dispatched` unless approval policy has already been satisfied.
2. An `override_record` cannot become `effective` without second approval when policy requires it.
3. A `workflow_task` reaching `completed` does not automatically approve a connector command.
4. A `document_identity` can remain `approved` while a new `document_version` is still in processing.
5. A failed `revision_comparison` must not block manual review; it should create a reviewable exception path.
