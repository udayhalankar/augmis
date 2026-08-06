# Symployee Document Controller Connector Contracts

## Purpose

This document defines the connector-side contracts for the Symployee Document Controller MVP, with shared drive as the first operational implementation target.

## Connector Architecture Rule

The connector agent is a customer-network component. It performs local access and approved writeback. AUGMIS remains the orchestration and decision platform.

## Connector Contract Principles

1. Outbound connector communication is preferred.
2. Every connector event and command must carry an idempotency key.
3. The connector agent must never auto-approve business actions.
4. The connector agent may validate payload shape but not business policy.
5. Writeback commands are executed only after explicit platform approval.

## Standard Connector Capabilities

Each adapter should declare capabilities in a normalized shape:

```json
{
  "repository_type": "shared_drive",
  "supports_watch": true,
  "supports_poll": true,
  "supports_hashing": true,
  "supports_version_upload": false,
  "supports_metadata_writeback": true,
  "supports_move": true,
  "supports_email_send": false
}
```

## Shared Drive Connector Contract

### Read Operations

Supported for MVP:
- scan configured root path
- watch for created or modified files
- compute file hash
- read file bytes
- report file path and timestamps

### Write Operations

Supported for MVP only after approval:
- rename source file
- move source file
- copy source file to archive path
- write sidecar metadata file only if explicitly configured

Not supported in MVP:
- ACL changes
- destructive deletion
- implicit overwrite without version rule check

## Generic Connector Event Contract

Event types:
- `created`
- `modified`
- `deleted`
- `moved`

Minimum event payload:

```json
{
  "event_key": "connector-generated-unique-key",
  "idempotency_key": "stable-dedupe-key",
  "repository_id": "uuid",
  "event_type": "created",
  "source_object_id": "pathhash-001",
  "source_path": "\\\\server\\share\\project\\file.pdf",
  "file_name": "file.pdf",
  "file_hash": "sha256-value",
  "size_bytes": 2452342,
  "modified_at": "2026-07-06T12:00:00Z",
  "metadata": {}
}
```

Idempotency recommendation:
- shared drive idempotency key should include repository, normalized path, file hash, and modified timestamp bucket

## Generic Connector Command Contract

Command types:
- `update_metadata`
- `rename_source_file`
- `move_source_file`
- `archive_document`
- `create_transmittal_placeholder`
- `send_email`

Minimum command payload:

```json
{
  "command_id": "uuid",
  "idempotency_key": "stable-command-key",
  "command_type": "rename_source_file",
  "payload": {
    "source_path": "\\\\server\\share\\project\\draft.pdf",
    "target_path": "\\\\server\\share\\project\\P1000-MEC-DRW-001-REV04.pdf"
  }
}
```

## Generic Connector Result Contract

Result statuses:
- `acknowledged`
- `failed`
- `rolled_back`

Minimum result payload:

```json
{
  "command_id": "uuid",
  "result_status": "acknowledged",
  "result_payload": {
    "target_ref": "\\\\server\\share\\project\\P1000-MEC-DRW-001-REV04.pdf",
    "completed_at": "2026-07-06T12:30:00Z"
  }
}
```

## Adapter Interface Contract

Every connector adapter should implement these operations:

- `health_check()`
- `list_capabilities()`
- `fetch_changes(cursor)`
- `read_object(source_ref)`
- `resolve_metadata(source_ref)`
- `execute_command(command_payload)`
- `acknowledge_result(result_payload)`

## Reliability and Safety Rules

1. Connector events must be replayable.
2. Connector command execution must be idempotent.
3. Failed writebacks must return structured reason codes.
4. Connector must not translate a business rule failure into a generic transport failure.
5. Connector logs must not include secret tokens or sensitive file content.

## Shared Drive MVP Constraints

The shared drive adapter should assume:
- single configured root per repository for initial MVP
- Windows-friendly path normalization
- no destructive delete actions
- archive implemented as move or copy into policy-defined archive path

## OTCS and SharePoint Contract-Only Scope

For MVP design completeness, these adapters should expose the same abstract contract but can remain unimplemented:

### OTCS expected operations
- list nodes
- get metadata
- download file
- upload new version
- update category metadata

### SharePoint expected operations
- delta list items
- download file
- upload file
- update metadata
- move/copy item

## Security Contract

Connector authentication requirements:
- tenant-bound agent registration
- rotating agent secret or token
- explicit agent identity on every event and command result

Platform expectations:
- reject unknown agent id
- reject unsupported command type for adapter capability
- reject commands without satisfied approval policy
