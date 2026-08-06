# Scope Tracker

Last updated: 2026-07-18T12:38:12

This markdown file is generated from the admin scope tracker page.

# AUGMIS

Platform-wide scope tracker for the broader AUGMIS product.

## Phase: Platform Foundation [completed]

Core retrieval, UI shell, dashboards, and operational intelligence modules.

### Milestone: RAG and AI Core [completed]

Streaming copilot, metadata-aware retrieval, and source-backed responses.

- [completed] feature: AI Copilot with SSE streaming
- [completed] feature: Executive dashboard and document intelligence

## Phase: Auth and SaaS Governance [completed]

JWT auth, RBAC, subscription plans, user management, and settings.

### Milestone: Sprint 7A to 7G [completed]

Authentication, access control, subscription, billing foundation, and admin user management.

- [completed] milestone-item: Frontend and backend auth flow
- [completed] milestone-item: Subscription and settings pages

## Phase: Repository Security and Access [partial]

Repository-aware access control for retrieval and ingestion.

### Milestone: Sprint 7H and 7I [partial]

Repository service, routes, secure retrieval filters, and frontend repository management.

- [completed] feature: Repository-aware search and AI filtering
- [pending] task: Re-index all documents with repository metadata

# SYMPLOYEE

Detailed Symployee Document Controller scope grouped by targeted sprint action items.

## Phase: Framework and Governance [in_progress]

Define the Symployee operating model, policy structure, governance boundaries, and MVP delivery sequence.

### Milestone: Sprint 1 - Platform foundation [in_progress]

Document the product boundary, architecture shape, domain model, API contracts, state machines, and frontend information architecture.

- [completed] feature: Formal policy and configuration model
  - Document taxonomy, metadata schemas, naming rules, revision rules, reviewer matrix, SLA rules, transmittal sequences, register definitions, confidence thresholds, and approval policies.
- [completed] feature: MVP blueprint and domain contracts
  - Document domain entities, state machines, API contracts, connector contracts, and frontend screen map for the first Symployee Document Controller.
- [in_progress] decision: Track work as targeted action items
  - Each pass should stay scoped to one active action item and its tasks until the item is marked completed, parked, or pending by the user.

## Phase: Connector and Intake Core [in_progress]

Bring shared-drive intake into the governed Symployee model with clean document identity, source object, version, and idempotency boundaries.

### Milestone: Sprint 2 - Connector Agent [partial]

Shared-drive-first connector contracts, secure synchronization, event receipt, and approved writeback seams. OTCS and SharePoint remain contract-first.

- [completed] feature: Shared drive connector event contract
  - Define supported read/write capabilities, event payload shape, idempotency rules, and result receipts for the customer-network connector agent.
- [parked] decision: Adapter contracts for OTCS and SharePoint
  - Keep deeper OTCS and SharePoint support parked at contract level for MVP while shared drive is the operational source.

### Milestone: Sprint 3 - Document ingestion [in_progress]

Register new shared-drive documents once, create logical document identity and versions, persist source references, and record append-only audit entries.

- [completed] feature: Document identity, source object, and version registration
  - Separate logical document, source system object, and version records so one document can move or exist across systems over time.
- [completed] feature: Strict idempotency for connector events
  - Prevent duplicate intake noise and preserve event history with connector event keys and idempotency records.
- [completed] task: Open actual document from Symployee surfaces
  - Allow governed viewing of the real PDF or Office file from document detail and command-linked views through the backend host.

## Phase: AI Recommendation and Policy Execution [in_progress]

Use policy-driven and model-driven recommendation generation while preserving human review, override, and provenance.

### Milestone: Sprint 4 - AI classification [in_progress]

Produce classification and metadata extraction recommendations with policy, model, prompt, confidence, and evidence linkage.

- [completed] feature: Bootstrap active default policies
  - Create the first working classification and metadata schema policy records required for Symployee intake.
- [completed] feature: Policy-driven and model-driven recommendation generation
  - Replace filename-only heuristics with active policy-backed classification and metadata extraction using parsed document text and governed prompt/model metadata.
- [completed] feature: Prompt and recommendation governance
  - Store prompt profile, prompt version, model, confidence, source evidence, and approval outcome separately for each AI recommendation.

## Phase: Workflow, Review, and Commands [completed]

Separate AI recommendation review from connector action approval and expose the first governed operational consoles.

### Milestone: Sprint 5 - Workflow engine [completed]

Define review routing, SLA handling, reviewer matrix evaluation, and workflow boundaries without letting workflow tasks double as commands.

- [completed] task: Review workflow planning and routing
  - Determine who should review by discipline, department, project, confidentiality, and policy while maintaining complete assignment and SLA history.
- [completed] task: SLA warnings, overdue tracking, and escalation
  - Track pending review, approved, rejected, comments, days overdue, workload, reminders, and escalation events.

### Milestone: Sprint 6 - Review console [in_progress]

Expose inbox, document detail, recommendation review, approvals, commands, and register views with operational audit visibility.

- [completed] feature: Isolated Symployee frontend routes and shell
  - Keep Symployee UI separate from the main Infomentica menu while backend contracts stabilize.
- [completed] feature: Recommendation approval and override surfaces
  - Allow human review and decisioning of classification and metadata recommendations separately from connector execution approval.
- [completed] feature: Command review with approval history and actual file access
  - Show connector commands, source recommendation summaries, status chips, approval history, and file links from document and command views.

### Milestone: Sprint 7 - OTCS/SharePoint actions [partial]

Advance connector writeback and multi-system command lifecycle while still respecting the shared-drive-first MVP boundary.

- [completed] feature: Create command drafts from approved recommendations
  - Generate connector command drafts from approved classification or metadata recommendations without auto-dispatching them.
- [completed] feature: Manual connector command drafting
  - Allow document-level creation of manual command drafts for controlled operator action.
- [completed] task: Real writeback dispatch and connector acknowledgements
  - Move beyond draft and approval into dispatched, acknowledged, failed, and rollback-capable command lifecycle.
- [parked] decision: OTCS and SharePoint operational adapters
  - Promote OTCS and SharePoint from contract-only to executable adapters only after shared-drive dispatch is stable.

## Phase: Registers, Compliance, and Analytics [pending]

Expand from intake and review into complete document-control governance, reporting, and hardening.

### Milestone: Sprint 8 - Analytics [pending]

Produce daily, weekly, and monthly reports with project, department, vendor, review time, bottleneck, and growth metrics.

- [partial] feature: Master Document Register expansion
  - Maintain the MDR automatically and prepare the structure for drawing, vendor, engineering, as-built, handover, submittal, MOC, and inspection registers.
- [pending] task: Operational dashboards and KPIs
  - Expose pending review, overdue review, critical items, average review time, vendor KPI, and bottleneck analytics.

### Milestone: Sprint 9 - Hardening [pending]

Close governance gaps around compliance monitoring, retention, revision evidence, and exception handling.

- [pending] task: Compliance monitoring rules
  - Check ISO, project procedures, naming standards, revision standards, approval requirements, signatures, and retention policy violations.
- [pending] task: Revision comparison artifacts
  - Model structured diff evidence for changed pages, tables, drawings, dimensions, clauses, signatures, and approval pages.

### Milestone: Sprint 10 - Enterprise deployment [pending]

Complete production readiness, deployment hardening, and operational rollout for customer-side connector execution.

- [pending] task: Production deployment and monitoring
  - Prepare Docker, Nginx, AWS ECS or EC2, Prometheus, Grafana, Sentry, and connector operations for enterprise rollout.
- [pending] task: Archive and retention execution
  - Archive completed documents according to retention policy without enabling destructive purge behavior in the MVP.

## Phase: Stabilization pass  [pending]

Reduce errors by fixing pre-existing compile issues

### Milestone: Reduce the existing frontend TypeScript error [pending]

Reduce the existing frontend TypeScript error baseline by fixing pre-existing compile issues, starting with shared MUI prop typing and high-noise component errors, so npx tsc --noEmit -p tsconfig.json becomes a reliable validation gate for future Symployee and platform changes.
