# Symployee Document Controller API Contracts

## Purpose

This document defines the MVP API surface for the Symployee Document Controller domain. It is intended as a contract-first blueprint, not yet as framework-specific implementation code.

## API Principles

1. All APIs are tenant-scoped.
2. All mutating requests must create audit entries.
3. Idempotent intake endpoints must require an idempotency key.
4. AI recommendation approval and connector command approval are separate operations.
5. Error responses should be explicit. No silent fallback behavior.

## 1. Synthetic Employee

### `GET /api/v1/synthetic-employees`

Purpose:
- list available Symployees and current status

### `GET /api/v1/synthetic-employees/{id}`

Purpose:
- retrieve Symployee configuration summary and active policy set

## 2. Policy and Configuration

### `GET /api/v1/symployees/document-controller/policies`

Purpose:
- list active policy domains and versions

### `GET /api/v1/symployees/document-controller/policies/{policyDomain}/{code}`

Purpose:
- get a specific configuration record with effective version

## 3. Connector Agent Lifecycle

### `POST /api/v1/connector-agents/register`

Purpose:
- register or renew a connector agent

Request:
```json
{
  "tenant_key": "tenant-public-key",
  "agent_name": "AUGMIS-SharedDrive-Agent-01",
  "agent_type": "shared_drive",
  "capabilities": {
    "watch_folders": true,
    "writeback": true,
    "hashing": true
  },
  "host": {
    "machine_name": "SERVER-01",
    "os_family": "windows"
  }
}
```

### `POST /api/v1/connector-agents/heartbeat`

Purpose:
- update connectivity and runtime health

### `POST /api/v1/connector-agents/{agentId}/events`

Purpose:
- push connector intake events into the platform

Rules:
- requires `idempotency_key`
- duplicate event should return deterministic duplicate response, not create new records

Request:
```json
{
  "repository_id": "uuid",
  "event_type": "created",
  "event_key": "server01:shareA:pathHash:20260706120000",
  "idempotency_key": "shared-drive:repo1:sha256:abc123",
  "source_object_id": "pathhash-001",
  "source_path": "\\\\server\\projects\\P1000\\docs\\file.pdf",
  "file_name": "P1000-MEC-DRW-001-REV04.pdf",
  "file_hash": "sha256-value",
  "size_bytes": 2452342,
  "modified_at": "2026-07-06T12:00:00Z",
  "metadata": {
    "project_code": "P1000"
  }
}
```

Response:
```json
{
  "connector_event_id": "uuid",
  "processing_status": "accepted",
  "document_identity_id": "uuid",
  "document_version_id": "uuid"
}
```

## 4. Documents

### `GET /api/v1/document-identities`

Purpose:
- list logical documents with filters

Filters:
- repository
- document_type
- discipline
- project
- status
- review_state
- duplicate_flag

### `GET /api/v1/document-identities/{documentIdentityId}`

Purpose:
- get logical document overview, source objects, versions, latest recommendations, workflows, commands, and audit trail summary

### `GET /api/v1/document-identities/{documentIdentityId}/versions`

Purpose:
- list versions for a logical document

### `GET /api/v1/document-versions/{documentVersionId}`

Purpose:
- get version details, metadata, extraction outputs, and revision data

## 5. AI Recommendation APIs

### `GET /api/v1/ai-recommendations`

Purpose:
- list recommendations by status and type

### `GET /api/v1/ai-recommendations/{recommendationId}`

Purpose:
- retrieve recommendation payload, confidence, policy, prompt, and evidence

### `POST /api/v1/ai-recommendations/{recommendationId}/approve`

Purpose:
- approve a recommendation outcome without directly dispatching writeback

Request:
```json
{
  "comments": "Classification accepted",
  "effective_values": {
    "document_type_code": "drawing",
    "discipline_code": "mechanical"
  }
}
```

### `POST /api/v1/ai-recommendations/{recommendationId}/reject`

Purpose:
- reject a recommendation and record reason

### `POST /api/v1/ai-recommendations/{recommendationId}/override`

Purpose:
- create a human override record against a recommendation

Request:
```json
{
  "reason_code": "incorrect_classification",
  "reason_text": "This is a method statement, not a drawing",
  "after_state": {
    "document_type_code": "method_statement"
  }
}
```

## 6. Workflow APIs

### `POST /api/v1/document-identities/{documentIdentityId}/workflows`

Purpose:
- create a workflow instance for review, approval, transmittal, or archive

### `GET /api/v1/workflows`

Purpose:
- list workflow instances by status, due date, assignee, and workflow type

### `GET /api/v1/workflows/{workflowId}`

Purpose:
- get workflow detail and task chain

### `POST /api/v1/workflow-tasks/{taskId}/decision`

Purpose:
- record approve, reject, or return against a workflow task

Request:
```json
{
  "decision": "approved",
  "comments": "Reviewed and accepted"
}
```

## 7. Connector Command APIs

### `POST /api/v1/connector-commands`

Purpose:
- create a connector command draft from approved recommendation or manual operation

Request:
```json
{
  "repository_id": "uuid",
  "agent_id": "uuid",
  "document_identity_id": "uuid",
  "document_version_id": "uuid",
  "command_type": "update_metadata",
  "payload": {
    "target_path": "\\\\server\\projects\\P1000\\docs\\file.pdf",
    "metadata_updates": {
      "document_number": "P1000-MEC-DRW-001"
    }
  },
  "source_recommendation_id": "uuid"
}
```

### `GET /api/v1/connector-commands`

Purpose:
- list commands by status, repository, agent, or document

### `GET /api/v1/connector-commands/{commandId}`

Purpose:
- get command payload, approval history, and execution receipts

### `POST /api/v1/connector-commands/{commandId}/approve`

Purpose:
- approve a connector writeback command

### `POST /api/v1/connector-commands/{commandId}/cancel`

Purpose:
- cancel a command before dispatch

### `POST /api/v1/connector-agents/{agentId}/command-results`

Purpose:
- connector agent acknowledges or fails command execution

Request:
```json
{
  "command_id": "uuid",
  "result_status": "acknowledged",
  "result_payload": {
    "target_ref": "\\\\server\\projects\\P1000\\docs\\file.pdf",
    "completed_at": "2026-07-06T12:30:00Z"
  }
}
```

## 8. Revision Comparison APIs

### `GET /api/v1/revision-comparisons`

Purpose:
- list revision comparisons by status or document

### `GET /api/v1/revision-comparisons/{comparisonId}`

Purpose:
- retrieve comparison summary and structured artifacts

## 9. Transmittal APIs

### `POST /api/v1/transmittals`

Purpose:
- create transmittal draft

### `GET /api/v1/transmittals`

Purpose:
- list transmittals with status and acknowledgement state

### `POST /api/v1/transmittals/{transmittalId}/approve`

Purpose:
- approve transmittal before issue

### `POST /api/v1/transmittals/{transmittalId}/issue`

Purpose:
- mark transmittal issued after approval

## 10. Register APIs

### `GET /api/v1/registers/master-document-register`

Purpose:
- retrieve live MDR rows by filter

### `POST /api/v1/registers/master-document-register/snapshots`

Purpose:
- generate exportable register snapshot

## 11. Audit APIs

### `GET /api/v1/audit-logs`

Purpose:
- search append-only event history

Filters:
- actor_type
- action_code
- entity_type
- entity_id
- from_date
- to_date

## Error Contract

Recommended error payload:

```json
{
  "error": {
    "code": "POLICY_NOT_FOUND",
    "message": "No active metadata schema policy found for repository shared_drive and document type drawing.",
    "details": {
      "tenant_id": "uuid",
      "repository_type": "shared_drive",
      "document_type_code": "drawing"
    }
  }
}
```

## API Separation Rules

1. Recommendation approval endpoints must not dispatch connector commands implicitly.
2. Workflow task decisions must not be treated as connector command approvals unless explicitly linked through approval policy.
3. Connector agent result endpoints must not mutate workflow decisions directly.
4. Document identity endpoints must not collapse logical document and version state into one ambiguous status field.
