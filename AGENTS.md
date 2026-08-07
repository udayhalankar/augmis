# AUGMIS Repository Instructions

## Project Architecture

This repository contains one AUGMIS platform with:

- frontend: Next.js 16, React 19, TypeScript, Material UI
- backend: FastAPI, SQLAlchemy, PostgreSQL
- existing authentication, JWT, RBAC, SaaS module access and tenant isolation
- existing enterprise shell and navigation
- existing connector scheduler
- existing AI services

Do not create parallel applications, authentication systems, database configurations or shells.

## Mandatory Working Method

For every task:

1. Read this file first.
2. Inspect all relevant existing files before editing.
3. Identify existing implementation patterns that should be reused.
4. Produce a short implementation plan.
5. List exact files to add and modify.
6. Implement only the requested scope.
7. Run the applicable validation commands.
8. Check every acceptance criterion individually.
9. Report incomplete criteria honestly.
10. Never claim a phase is complete when any requested action is missing.

## Scope Control

Do not:

- modify unrelated modules
- refactor working code unless explicitly requested
- fix unrelated lint errors
- introduce new frameworks without approval
- introduce SQLite
- introduce a second FastAPI app
- introduce a second root frontend layout
- replace authentication
- add Celery, Redis, Kafka, Kubernetes or microservices unless explicitly requested
- implement future phases early
- add placeholder buttons that do nothing
- add fake business data to production pages
- silently omit difficult requirements

When a requirement cannot be completed, stop and report:

- what is blocked
- why it is blocked
- which file or dependency causes it
- the safest resolution

## Tenant and Security Rules

- tenant_id must always come from authenticated JWT context
- never trust tenant_id supplied by the frontend
- every new database query must be tenant-scoped
- cross-tenant access must return 404 where appropriate
- backend authorization is authoritative
- frontend hiding is only UX
- never expose secrets or credentials
- never hard-code DATABASE_URL or API keys
- never invent contact details or unsupported business facts

## AUGMIS Business Module

The Business Development Agent lives under:

- frontend/app/augmis-business
- backend API namespace: /api/augmis-business

It is separate from Document Controller business logic but reuses the same platform shell, auth, DB, RBAC, scheduler and AI patterns.

Do not relocate the module unless explicitly instructed.

## Frontend Design Rules

Use:

- existing enterprise shell
- MUI icons
- colored icons with semantic meaning
- selective gradients on large KPI cards and card headers
- solid colors for buttons
- border radius between 5px and 10px
- compact enterprise tables
- meaningful loading, error and empty states
- reusable components rather than duplicated inline styling

Do not use:

- oversized rounded cards
- excessive gradients
- fake charts
- decorative Unicode icons
- placeholder actions
- excessive whitespace
- consumer-mobile styling

## Validation

For frontend changes, run as applicable:

- npm run build
- npx tsc --noEmit
- scoped lint on modified files where possible

Do not fix unrelated repository-wide lint errors.

For backend changes, run as applicable:

- Python compile/import validation
- relevant pytest tests
- Alembic migration validation
- application startup validation

## Completion Rule

Before reporting completion, create a checklist of every acceptance criterion and mark each as:

- PASS
- FAIL
- NOT TESTED
- BLOCKED

A task is complete only when all mandatory criteria are PASS.

If any mandatory item is FAIL, NOT TESTED or BLOCKED, state clearly that the task is not complete.