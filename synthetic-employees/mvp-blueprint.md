# Symployee Document Controller MVP Blueprint

## Objective

Build the first production-capable Symployee Document Controller as a governed execution layer on top of existing enterprise repositories, with shared drive as the first operational source and OTCS/SharePoint represented initially as adapter contracts.

## Product Boundary

The MVP is not a replacement DMS.

Systems of record remain:
- OTCS
- SharePoint
- SAP DMS
- shared drives
- email systems

AUGMIS owns:
- intake orchestration
- AI recommendations
- workflow state
- approvals
- registers
- audit ledger
- connector command dispatch
- analytics

## MVP Source Scope

In scope:
- shared drive connector events
- shared drive read operations
- shared drive approved writeback for low-risk supported actions

Contract-only, not fully implemented:
- OTCS
- SharePoint
- email
- SAP DMS

## MVP Functional Slices

1. Connector registration and heartbeat
2. Shared drive file event intake
3. Document identity and version creation
4. Text extraction and OCR-ready pipeline
5. AI classification and metadata recommendation
6. Metadata validation against configured schema
7. Duplicate and revision candidate detection
8. Review workflow planning
9. Human approval and override
10. Connector command approval and dispatch
11. Master document register generation
12. Audit and operational traceability

## Core Design Rules

1. Configuration is DB-backed and policy-driven.
2. AI recommendation records are separate from action execution records.
3. Connector commands are separate from workflow tasks.
4. Audit records are append-only.
5. Writebacks require explicit approval policy evaluation.
6. Idempotency is mandatory for connector event intake.
7. One logical document can have multiple versions and multiple source references over time.

## Required Architecture Outcomes

The MVP must support:
- one tenant with clean tenant-scoped models that scale to many tenants
- one active Symployee type: document controller
- one fully operational source type: shared drive
- one core register: master document register
- one operational workflow family: document review and approval

## Design Deliverables in This Workspace

- `policy-configuration-model.md`
- `domain-entities.md`
- `state-machines.md`
- `api-contracts.md`
- `connector-contracts.md`
- `frontend/synthetic-employees/frontend-screen-map.md`

## Implementation Sequence Recommendation

1. establish policy/config entities first
2. implement document identity, source object, and version boundaries
3. implement connector event idempotency
4. implement AI recommendation ledger
5. implement workflow and approval logic
6. implement connector command lifecycle
7. implement register and dashboard views

## Non-Negotiable Audit Requirements

The platform must record:
- connector event received
- document registered
- AI recommendation generated
- policy/version used
- human decision recorded
- override recorded
- connector command created
- connector command dispatched
- connector command acknowledged or failed

## MVP Exit Criteria

The MVP is ready only when the system can:
- ingest a new shared drive document once without duplication
- identify logical document and current version correctly
- generate AI recommendations with stored model and prompt provenance
- validate metadata against policy-driven schemas
- route review tasks from configured reviewer matrix rules
- record approval or override decisions separately from recommendations
- create and dispatch approved shared-drive connector commands
- show complete audit history and master document register state
