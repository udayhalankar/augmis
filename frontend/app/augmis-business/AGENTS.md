# AUGMIS Business Frontend Instructions

These instructions apply to the AUGMIS Business frontend module.

## Route Structure

Preserve:

- /augmis-business
- /augmis-business/opportunities
- /augmis-business/leads
- /augmis-business/prospects
- /augmis-business/pipeline
- /augmis-business/replies
- /augmis-business/tasks
- /augmis-business/connectors
- /augmis-business/control-centre

Do not relocate the module.

## Shell

Reuse the existing root layout, AppFrame, EnterpriseShell, auth providers and ModuleGuard.

Do not create another application frame, login page or root layout.

## Page Requirements

Every interactive page must include all actions stated in the task.

Do not consider a CRUD page complete unless the requested actions work end to end:

- list
- create
- view
- edit
- delete
- search
- filters
- loading
- error
- empty state
- permissions

If only some are requested, implement only those but verify every requested one.

## Visual Rules

- use colored Material UI icons
- gradient card headers
- selective gradients on large summary cards
- solid buttons
- radius 5px to 10px
- compact tables
- no fake data
- no non-functional buttons