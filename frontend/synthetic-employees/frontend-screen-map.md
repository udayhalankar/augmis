# Symployee Document Controller Frontend Screen Map

## Purpose

This document defines the frontend information architecture for the Symployee Document Controller MVP.

## Route Strategy

Keep Symployee frontend work isolated under the synthetic employees area first, then integrate into the main navigation only after backend contracts are stable.

Recommended route family:
- `/synthetic-employees`
- `/synthetic-employees/document-controller`
- `/synthetic-employees/document-controller/inbox`
- `/synthetic-employees/document-controller/documents/[id]`
- `/synthetic-employees/document-controller/recommendations`
- `/synthetic-employees/document-controller/workflows`
- `/synthetic-employees/document-controller/approvals`
- `/synthetic-employees/document-controller/commands`
- `/synthetic-employees/document-controller/registers`
- `/synthetic-employees/document-controller/audit`
- `/synthetic-employees/document-controller/configuration`

## Screen Inventory

### 1. Symployee Landing

Route:
- `/synthetic-employees`

Purpose:
- show available Symployees
- show status, workload, and pending items

Core widgets:
- Symployee cards
- pending approvals
- overdue reviews
- command failures
- audit exceptions

### 2. Document Controller Overview

Route:
- `/synthetic-employees/document-controller`

Purpose:
- operational summary for the Document Controller Symployee

Core widgets:
- new documents registered
- pending metadata review
- pending workflow approvals
- overdue review tasks
- command queue status
- MDR growth trend

### 3. Intake Inbox

Route:
- `/synthetic-employees/document-controller/inbox`

Purpose:
- triage newly ingested documents before or during review

Table columns:
- intake timestamp
- repository
- file name
- detected document type
- confidence
- metadata completeness
- duplicate flag
- revision candidate flag
- current workflow state

Primary actions:
- open document
- review recommendation
- start workflow
- mark for manual handling

### 4. Document Detail

Route:
- `/synthetic-employees/document-controller/documents/[id]`

Purpose:
- single source of truth for logical document review

Tabs:
- overview
- versions
- metadata
- recommendations
- revision comparison
- workflows
- connector commands
- audit trail

Key panels:
- document identity summary
- source object references
- current version preview
- metadata validation issues
- latest AI recommendations with evidence
- approval history

### 5. Recommendations Queue

Route:
- `/synthetic-employees/document-controller/recommendations`

Purpose:
- review AI-produced recommendations before operational approval

Table columns:
- recommendation type
- document number
- confidence
- policy used
- model and prompt version
- status
- created at

Primary actions:
- approve recommendation
- reject recommendation
- override recommendation
- inspect evidence

### 6. Workflows Console

Route:
- `/synthetic-employees/document-controller/workflows`

Purpose:
- monitor workflow instances and task progression

Views:
- workflow list
- task list
- SLA heatmap
- overdue queue

### 7. Approvals Console

Route:
- `/synthetic-employees/document-controller/approvals`

Purpose:
- central place for human approval activity

Sections:
- task approvals
- recommendation approvals
- connector command approvals
- override approvals

This separation is important in the UI because the backend records are different.

### 8. Connector Commands Console

Route:
- `/synthetic-employees/document-controller/commands`

Purpose:
- monitor writeback command lifecycle

Table columns:
- command type
- target repository
- linked document
- approval status
- command status
- dispatched at
- agent result

Primary actions:
- approve command
- cancel command
- inspect payload
- inspect execution receipt

### 9. Registers

Route:
- `/synthetic-employees/document-controller/registers`

Purpose:
- present generated registers with filtering and export

MVP priority:
- Master Document Register

Future tabs:
- drawing register
- vendor register
- as-built register

### 10. Audit Console

Route:
- `/synthetic-employees/document-controller/audit`

Purpose:
- query append-only operational history

Filters:
- actor type
- action
- entity type
- entity id
- date range

### 11. Configuration Console

Route:
- `/synthetic-employees/document-controller/configuration`

Purpose:
- manage configuration-backed policy areas

MVP sections:
- document types
- metadata schemas
- naming rules
- revision rules
- review matrix
- SLA rules
- confidence thresholds
- approval policies
- shared drive connector action policies
- register definitions

## UI Principles

1. Recommendation approval must be visually separate from command approval.
2. Logical document identity must be visually separate from document version details.
3. Revision comparison evidence must be inspectable, not only summarized.
4. Audit trail must show policy version, model, prompt version, and actor.
5. Error states must be explicit and operationally useful.

## MVP Screen Build Order

1. overview
2. inbox
3. document detail
4. recommendations queue
5. approvals console
6. commands console
7. registers
8. audit
9. configuration
