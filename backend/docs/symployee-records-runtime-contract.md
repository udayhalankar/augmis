# Symployee Records Runtime Contract

This note documents the current backend-owned contract for records configuration resolution and record-state transitions.

## Configuration Resolution

Runtime configuration selection is centralized in `backend/app/services/symployee_records_service.py` through `_resolve_config_row(...)`.

The resolver applies these rules in order:

1. Tenant match is mandatory.
2. Only rows with `status = ACTIVE` and `is_current_version = true` are eligible.
3. Any explicit extra filters for the domain must match first.
4. Scope fields are then matched exactly against the current identity:
   - `repository_id`
   - `business_area`
   - `project_code` when the table supports it
   - `document_type`
5. The winning row is chosen by this precedence:
   - Highest scope specificity wins.
   - For equal specificity, lower `rule_priority` wins.
   - For equal priority, higher `version_no` wins.
   - For equal version, later `effective_from` wins.
   - For equal effective date, later `created_at` wins.

Specificity is the count of populated scope fields among `repository_id`, `business_area`, `project_code`, and `document_type`.

This means a project-scoped rule can override a tenant-generic rule even if the generic row has a more preferred numeric priority, because specificity is evaluated before priority.

## Declaration Contract

`declare_record(...)` is the canonical runtime entry point for direct record declaration.

Current behavior:

1. Resolve declaration, lifecycle, retention, vital, and assignment config from backend tables.
2. Build evaluation context from identity/version metadata.
3. Resolve vital runtime state from policy, not from page logic.
4. Apply lifecycle transition `DECLARE_RECORD` with trigger event `DECLARED_RECORD`.
5. Persist the declaration row with:
   - linked config IDs
   - lifecycle transition payload
   - workflow routing payload
   - declaration activity fields (`record_stage`, `active_from`, `inactive_from`, `inactive_reason_code`)
6. Persist `source_event_id` from the first lifecycle event produced by the declaration transition.

The first lifecycle event is the declaration event itself (`RECORD_DECLARED`), not a later activity-stage event such as `RECORD_BECAME_ACTIVE`.

## Record State Vocabulary

The current record-status flow implemented in the lifecycle engine includes:

- `RECORD_CANDIDATE`
- `DECLARED_RECORD`
- `UNDER_LEGAL_HOLD`
- `DISPOSITION_PENDING`
- `ARCHIVED`

The current activity-stage flow includes:

- `ACTIVE`
- `INACTIVE`
- `ARCHIVED`

Vital runtime values currently emitted by the records service are:

- `NON_VITAL`
- `VITAL_CANDIDATE`
- `VITAL`
- `VITAL_UNDER_REVIEW`

Hold categories are backend validated and DB-backed:

- `LEGAL`
- `VALIDATION`
- `RECORDS`
- `OPERATIONAL`
- `OTHER`

## Lifecycle Transition Semantics

Record lifecycle transitions are centralized in `backend/app/services/symployee_lifecycle_service.py`.

Current implemented transition codes:

- `DECLARE_RECORD`
- `ACTIVATE_RECORD`
- `INACTIVATE_RECORD`
- `PLACE_HOLD`
- `RELEASE_HOLD`
- `MARK_DISPOSITION_PENDING`
- `MARK_ARCHIVE_PENDING`
- `MARK_ARCHIVED`
- `EVALUATE_RULE`

Important runtime rules:

- `DECLARE_RECORD` always writes `record_status = DECLARED_RECORD`.
- `DECLARE_RECORD` only writes `document_lifecycle_stage = ACTIVE` when the lifecycle rule `active_start_event` matches the actual trigger event.
- The declaration service now uses `trigger_event = DECLARED_RECORD`, which aligns declaration-time activation with lifecycle rules that start activity on declaration.
- `EVALUATE_RULE` can move a record to `INACTIVE` immediately on an eligibility event, or later on `TIME_EVALUATION` when the lifecycle clock basis and inactivity timeout are satisfied.

## Hardening Notes

- Page code should consume backend-owned fields and counts only. It should not infer configuration meaning from UI labels or route names.
- `hold_code` must not be treated as the UI classifier for legal versus non-legal holds; `hold_category` is the canonical field.
- Historical reprocessing/backfill should continue to use the dedicated scripts and metadata markers already introduced in Phase 14, rather than embedding backfill assumptions into runtime page logic.
