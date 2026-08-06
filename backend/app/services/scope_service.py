import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.models.scope_models import (
    ItemCreateRequest,
    ItemUpdateRequest,
    MilestoneCreateRequest,
    MilestoneUpdateRequest,
    PhaseCreateRequest,
    PhaseUpdateRequest,
)


BASE_DIR = Path(__file__).resolve().parents[2]
STORAGE_FILE = BASE_DIR / "storage" / "scope_tracker.json"
MARKDOWN_FILE = BASE_DIR.parent / "Documentation" / "Infomentica_scope.md"

DEFAULT_TRACK = "augmis"


def _now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")


def _new_id(prefix: str):
    return f"{prefix}-{str(uuid4())[:8].upper()}"


def _default_augmis_phases():
    return [
        {
            "phase_id": _new_id("PHS"),
            "title": "Platform Foundation",
            "description": "Core retrieval, UI shell, dashboards, and operational intelligence modules.",
            "status": "completed",
            "milestones": [
                {
                    "milestone_id": _new_id("MLS"),
                    "title": "RAG and AI Core",
                    "description": "Streaming copilot, metadata-aware retrieval, and source-backed responses.",
                    "status": "completed",
                    "items": [
                        {
                            "item_id": _new_id("ITM"),
                            "title": "AI Copilot with SSE streaming",
                            "description": "",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Executive dashboard and document intelligence",
                            "description": "",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                    ],
                }
            ],
        },
        {
            "phase_id": _new_id("PHS"),
            "title": "Auth and SaaS Governance",
            "description": "JWT auth, RBAC, subscription plans, user management, and settings.",
            "status": "completed",
            "milestones": [
                {
                    "milestone_id": _new_id("MLS"),
                    "title": "Sprint 7A to 7G",
                    "description": "Authentication, access control, subscription, billing foundation, and admin user management.",
                    "status": "completed",
                    "items": [
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Frontend and backend auth flow",
                            "description": "",
                            "status": "completed",
                            "item_type": "milestone-item",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Subscription and settings pages",
                            "description": "",
                            "status": "completed",
                            "item_type": "milestone-item",
                            "owner": "",
                            "due_date": "",
                        },
                    ],
                }
            ],
        },
        {
            "phase_id": _new_id("PHS"),
            "title": "Repository Security and Access",
            "description": "Repository-aware access control for retrieval and ingestion.",
            "status": "partial",
            "milestones": [
                {
                    "milestone_id": _new_id("MLS"),
                    "title": "Sprint 7H and 7I",
                    "description": "Repository service, routes, secure retrieval filters, and frontend repository management.",
                    "status": "partial",
                    "items": [
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Repository-aware search and AI filtering",
                            "description": "",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Re-index all documents with repository metadata",
                            "description": "",
                            "status": "pending",
                            "item_type": "task",
                            "owner": "",
                            "due_date": "",
                        },
                    ],
                }
            ],
        },
    ]


def _default_symployee_phases():
    return [
        {
            "phase_id": _new_id("PHS"),
            "title": "Framework and Governance",
            "description": "Define the Symployee operating model, policy structure, governance boundaries, and MVP delivery sequence.",
            "status": "in_progress",
            "milestones": [
                {
                    "milestone_id": _new_id("MLS"),
                    "title": "Sprint 1 - Platform foundation",
                    "description": "Document the product boundary, architecture shape, domain model, API contracts, state machines, and frontend information architecture.",
                    "status": "in_progress",
                    "items": [
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Formal policy and configuration model",
                            "description": "Document taxonomy, metadata schemas, naming rules, revision rules, reviewer matrix, SLA rules, transmittal sequences, register definitions, confidence thresholds, and approval policies.",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "MVP blueprint and domain contracts",
                            "description": "Document domain entities, state machines, API contracts, connector contracts, and frontend screen map for the first Symployee Document Controller.",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Track work as targeted action items",
                            "description": "Each pass should stay scoped to one active action item and its tasks until the item is marked completed, parked, or pending by the user.",
                            "status": "in_progress",
                            "item_type": "decision",
                            "owner": "",
                            "due_date": "",
                        },
                    ],
                }
            ],
        },
        {
            "phase_id": _new_id("PHS"),
            "title": "Connector and Intake Core",
            "description": "Bring shared-drive intake into the governed Symployee model with clean document identity, source object, version, and idempotency boundaries.",
            "status": "in_progress",
            "milestones": [
                {
                    "milestone_id": _new_id("MLS"),
                    "title": "Sprint 2 - Connector Agent",
                    "description": "Shared-drive-first connector contracts, secure synchronization, event receipt, and approved writeback seams. OTCS and SharePoint remain contract-first.",
                    "status": "partial",
                    "items": [
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Shared drive connector event contract",
                            "description": "Define supported read/write capabilities, event payload shape, idempotency rules, and result receipts for the customer-network connector agent.",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Adapter contracts for OTCS and SharePoint",
                            "description": "Keep deeper OTCS and SharePoint support parked at contract level for MVP while shared drive is the operational source.",
                            "status": "parked",
                            "item_type": "decision",
                            "owner": "",
                            "due_date": "",
                        },
                    ],
                },
                {
                    "milestone_id": _new_id("MLS"),
                    "title": "Sprint 3 - Document ingestion",
                    "description": "Register new shared-drive documents once, create logical document identity and versions, persist source references, and record append-only audit entries.",
                    "status": "in_progress",
                    "items": [
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Document identity, source object, and version registration",
                            "description": "Separate logical document, source system object, and version records so one document can move or exist across systems over time.",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Strict idempotency for connector events",
                            "description": "Prevent duplicate intake noise and preserve event history with connector event keys and idempotency records.",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Open actual document from Symployee surfaces",
                            "description": "Allow governed viewing of the real PDF or Office file from document detail and command-linked views through the backend host.",
                            "status": "completed",
                            "item_type": "task",
                            "owner": "",
                            "due_date": "",
                        },
                    ],
                },
            ],
        },
        {
            "phase_id": _new_id("PHS"),
            "title": "AI Recommendation and Policy Execution",
            "description": "Use policy-driven and model-driven recommendation generation while preserving human review, override, and provenance.",
            "status": "in_progress",
            "milestones": [
                {
                    "milestone_id": _new_id("MLS"),
                    "title": "Sprint 4 - AI classification",
                    "description": "Produce classification and metadata extraction recommendations with policy, model, prompt, confidence, and evidence linkage.",
                    "status": "in_progress",
                    "items": [
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Bootstrap active default policies",
                            "description": "Create the first working classification and metadata schema policy records required for Symployee intake.",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Policy-driven and model-driven recommendation generation",
                            "description": "Replace filename-only heuristics with active policy-backed classification and metadata extraction using parsed document text and governed prompt/model metadata.",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Prompt and recommendation governance",
                            "description": "Store prompt profile, prompt version, model, confidence, source evidence, and approval outcome separately for each AI recommendation.",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                    ],
                }
            ],
        },
        {
            "phase_id": _new_id("PHS"),
            "title": "Workflow, Review, and Commands",
            "description": "Separate AI recommendation review from connector action approval and expose the first governed operational consoles.",
            "status": "in_progress",
            "milestones": [
                {
                    "milestone_id": _new_id("MLS"),
                    "title": "Sprint 5 - Workflow engine",
                    "description": "Define review routing, SLA handling, reviewer matrix evaluation, and workflow boundaries without letting workflow tasks double as commands.",
                    "status": "completed",
                    "items": [
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Review workflow planning and routing",
                            "description": "Determine who should review by discipline, department, project, confidentiality, and policy while maintaining complete assignment and SLA history.",
                            "status": "completed",
                            "item_type": "task",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "SLA warnings, overdue tracking, and escalation",
                            "description": "Track pending review, approved, rejected, comments, days overdue, workload, reminders, and escalation events.",
                            "status": "completed",
                            "item_type": "task",
                            "owner": "",
                            "due_date": "",
                        },
                    ],
                },
                {
                    "milestone_id": _new_id("MLS"),
                    "title": "Sprint 6 - Review console",
                    "description": "Expose inbox, document detail, recommendation review, approvals, commands, and register views with operational audit visibility.",
                    "status": "in_progress",
                    "items": [
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Isolated Symployee frontend routes and shell",
                            "description": "Keep Symployee UI separate from the main Infomentica menu while backend contracts stabilize.",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Recommendation approval and override surfaces",
                            "description": "Allow human review and decisioning of classification and metadata recommendations separately from connector execution approval.",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Command review with approval history and actual file access",
                            "description": "Show connector commands, source recommendation summaries, status chips, approval history, and file links from document and command views.",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                    ],
                },
                {
                    "milestone_id": _new_id("MLS"),
                    "title": "Sprint 7 - OTCS/SharePoint actions",
                    "description": "Advance connector writeback and multi-system command lifecycle while still respecting the shared-drive-first MVP boundary.",
                    "status": "partial",
                    "items": [
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Create command drafts from approved recommendations",
                            "description": "Generate connector command drafts from approved classification or metadata recommendations without auto-dispatching them.",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Manual connector command drafting",
                            "description": "Allow document-level creation of manual command drafts for controlled operator action.",
                            "status": "completed",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Real writeback dispatch and connector acknowledgements",
                            "description": "Move beyond draft and approval into dispatched, acknowledged, failed, and rollback-capable command lifecycle.",
                            "status": "completed",
                            "item_type": "task",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "OTCS and SharePoint operational adapters",
                            "description": "Promote OTCS and SharePoint from contract-only to executable adapters only after shared-drive dispatch is stable.",
                            "status": "parked",
                            "item_type": "decision",
                            "owner": "",
                            "due_date": "",
                        },
                    ],
                },
            ],
        },
        {
            "phase_id": _new_id("PHS"),
            "title": "Registers, Compliance, and Analytics",
            "description": "Expand from intake and review into complete document-control governance, reporting, and hardening.",
            "status": "pending",
            "milestones": [
                {
                    "milestone_id": _new_id("MLS"),
                    "title": "Sprint 8 - Analytics",
                    "description": "Produce daily, weekly, and monthly reports with project, department, vendor, review time, bottleneck, and growth metrics.",
                    "status": "pending",
                    "items": [
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Master Document Register expansion",
                            "description": "Maintain the MDR automatically and prepare the structure for drawing, vendor, engineering, as-built, handover, submittal, MOC, and inspection registers.",
                            "status": "partial",
                            "item_type": "feature",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Operational dashboards and KPIs",
                            "description": "Expose pending review, overdue review, critical items, average review time, vendor KPI, and bottleneck analytics.",
                            "status": "pending",
                            "item_type": "task",
                            "owner": "",
                            "due_date": "",
                        },
                    ],
                },
                {
                    "milestone_id": _new_id("MLS"),
                    "title": "Sprint 9 - Hardening",
                    "description": "Close governance gaps around compliance monitoring, retention, revision evidence, and exception handling.",
                    "status": "pending",
                    "items": [
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Compliance monitoring rules",
                            "description": "Check ISO, project procedures, naming standards, revision standards, approval requirements, signatures, and retention policy violations.",
                            "status": "pending",
                            "item_type": "task",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Revision comparison artifacts",
                            "description": "Model structured diff evidence for changed pages, tables, drawings, dimensions, clauses, signatures, and approval pages.",
                            "status": "pending",
                            "item_type": "task",
                            "owner": "",
                            "due_date": "",
                        },
                    ],
                },
                {
                    "milestone_id": _new_id("MLS"),
                    "title": "Sprint 10 - Enterprise deployment",
                    "description": "Complete production readiness, deployment hardening, and operational rollout for customer-side connector execution.",
                    "status": "pending",
                    "items": [
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Production deployment and monitoring",
                            "description": "Prepare Docker, Nginx, AWS ECS or EC2, Prometheus, Grafana, Sentry, and connector operations for enterprise rollout.",
                            "status": "pending",
                            "item_type": "task",
                            "owner": "",
                            "due_date": "",
                        },
                        {
                            "item_id": _new_id("ITM"),
                            "title": "Archive and retention execution",
                            "description": "Archive completed documents according to retention policy without enabling destructive purge behavior in the MVP.",
                            "status": "pending",
                            "item_type": "task",
                            "owner": "",
                            "due_date": "",
                        },
                    ],
                },
            ],
        },
    ]


def _default_scope():
    return {
        "title": "Scope Tracker",
        "last_updated": _now_iso(),
        "tracks": {
            "augmis": {
                "code": "augmis",
                "name": "AUGMIS",
                "description": "Platform-wide scope tracker for the broader AUGMIS product.",
                "phases": _default_augmis_phases(),
            },
            "symployee": {
                "code": "symployee",
                "name": "SYMPLOYEE",
                "description": "Detailed Symployee Document Controller scope grouped by targeted sprint action items.",
                "phases": _default_symployee_phases(),
            },
        },
    }


def _normalize_scope_data(data: dict) -> dict:
    if data.get("tracks"):
        data.setdefault("title", "Scope Tracker")
        data.setdefault("last_updated", _now_iso())
        data["tracks"].setdefault(
            "augmis",
            {
                "code": "augmis",
                "name": "AUGMIS",
                "description": "Platform-wide scope tracker for the broader AUGMIS product.",
                "phases": [],
            },
        )
        data["tracks"].setdefault(
            "symployee",
            {
                "code": "symployee",
                "name": "SYMPLOYEE",
                "description": "Detailed Symployee Document Controller scope grouped by targeted sprint action items.",
                "phases": _default_symployee_phases(),
            },
        )
        return data

    phases = data.get("phases", [])
    return {
        "title": data.get("title", "Scope Tracker"),
        "last_updated": data.get("last_updated", _now_iso()),
        "tracks": {
            "augmis": {
                "code": "augmis",
                "name": "AUGMIS",
                "description": "Platform-wide scope tracker for the broader AUGMIS product.",
                "phases": phases,
            },
            "symployee": {
                "code": "symployee",
                "name": "SYMPLOYEE",
                "description": "Detailed Symployee Document Controller scope grouped by targeted sprint action items.",
                "phases": _default_symployee_phases(),
            },
        },
    }


def _ensure_file():
    STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not STORAGE_FILE.exists():
        data = _default_scope()
        STORAGE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        _write_markdown(data)


def _read_scope():
    _ensure_file()
    try:
        raw = json.loads(STORAGE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raw = _default_scope()
    data = _normalize_scope_data(raw)
    STORAGE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    _write_markdown(data)
    return data


def _write_scope(data: dict):
    normalized = _normalize_scope_data(data)
    normalized["last_updated"] = _now_iso()
    STORAGE_FILE.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    _write_markdown(normalized)


def _write_markdown(data: dict):
    MARKDOWN_FILE.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# {data.get('title', 'Scope Tracker')}",
        "",
        f"Last updated: {data.get('last_updated', _now_iso())}",
        "",
        "This markdown file is generated from the admin scope tracker page.",
        "",
    ]

    for track_code, track in data.get("tracks", {}).items():
        lines.extend(
            [
                f"# {track.get('name', track_code.upper())}",
                "",
            ]
        )
        if track.get("description"):
            lines.extend([track["description"], ""])

        for phase in track.get("phases", []):
            lines.extend(
                [
                    f"## Phase: {phase['title']} [{phase.get('status', 'pending')}]",
                    "",
                ]
            )
            if phase.get("description"):
                lines.extend([phase["description"], ""])

            for milestone in phase.get("milestones", []):
                lines.extend(
                    [
                        f"### Milestone: {milestone['title']} [{milestone.get('status', 'pending')}]",
                        "",
                    ]
                )
                if milestone.get("description"):
                    lines.extend([milestone["description"], ""])

                for item in milestone.get("items", []):
                    suffix_parts = []
                    if item.get("owner"):
                        suffix_parts.append(f"Owner: {item['owner']}")
                    if item.get("due_date"):
                        suffix_parts.append(f"Due: {item['due_date']}")
                    suffix = f" ({' | '.join(suffix_parts)})" if suffix_parts else ""

                    lines.append(
                        f"- [{item.get('status', 'pending')}] {item.get('item_type', 'task')}: {item['title']}{suffix}"
                    )
                    if item.get("description"):
                        lines.append(f"  - {item['description']}")
                lines.append("")

    MARKDOWN_FILE.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _get_track(data: dict, track: str) -> dict:
    normalized_track = (track or DEFAULT_TRACK).strip().lower()
    track_data = data.get("tracks", {}).get(normalized_track)
    if not track_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scope track not found",
        )
    return track_data


def _find_phase(data: dict, phase_id: str, track: str):
    track_data = _get_track(data, track)
    for phase in track_data.get("phases", []):
        if phase.get("phase_id") == phase_id:
            return phase
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Phase not found",
    )


def _find_milestone(phase: dict, milestone_id: str):
    for milestone in phase.get("milestones", []):
        if milestone.get("milestone_id") == milestone_id:
            return milestone
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Milestone not found",
    )


def _find_item(milestone: dict, item_id: str):
    for item in milestone.get("items", []):
        if item.get("item_id") == item_id:
            return item
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Item not found",
    )


def get_scope_tracker():
    return {
        "success": True,
        "data": _read_scope(),
    }


def create_phase(payload: PhaseCreateRequest, track: str = DEFAULT_TRACK):
    data = _read_scope()
    track_data = _get_track(data, track)
    phase = {
        "phase_id": _new_id("PHS"),
        "title": payload.title,
        "description": payload.description,
        "status": payload.status,
        "milestones": [],
    }
    track_data.setdefault("phases", []).append(phase)
    _write_scope(data)
    return {"success": True, "data": phase}


def update_phase(phase_id: str, payload: PhaseUpdateRequest, track: str = DEFAULT_TRACK):
    data = _read_scope()
    phase = _find_phase(data, phase_id, track)

    if payload.title is not None:
        phase["title"] = payload.title
    if payload.description is not None:
        phase["description"] = payload.description
    if payload.status is not None:
        phase["status"] = payload.status

    _write_scope(data)
    return {"success": True, "data": phase}


def delete_phase(phase_id: str, track: str = DEFAULT_TRACK):
    data = _read_scope()
    track_data = _get_track(data, track)
    before = len(track_data.get("phases", []))
    track_data["phases"] = [
        phase for phase in track_data.get("phases", []) if phase.get("phase_id") != phase_id
    ]
    if len(track_data["phases"]) == before:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phase not found",
        )
    _write_scope(data)
    return {"success": True}


def create_milestone(
    phase_id: str,
    payload: MilestoneCreateRequest,
    track: str = DEFAULT_TRACK,
):
    data = _read_scope()
    phase = _find_phase(data, phase_id, track)
    milestone = {
        "milestone_id": _new_id("MLS"),
        "title": payload.title,
        "description": payload.description,
        "status": payload.status,
        "items": [],
    }
    phase.setdefault("milestones", []).append(milestone)
    _write_scope(data)
    return {"success": True, "data": milestone}


def update_milestone(
    phase_id: str,
    milestone_id: str,
    payload: MilestoneUpdateRequest,
    track: str = DEFAULT_TRACK,
):
    data = _read_scope()
    phase = _find_phase(data, phase_id, track)
    milestone = _find_milestone(phase, milestone_id)

    if payload.title is not None:
        milestone["title"] = payload.title
    if payload.description is not None:
        milestone["description"] = payload.description
    if payload.status is not None:
        milestone["status"] = payload.status

    _write_scope(data)
    return {"success": True, "data": milestone}


def delete_milestone(phase_id: str, milestone_id: str, track: str = DEFAULT_TRACK):
    data = _read_scope()
    phase = _find_phase(data, phase_id, track)
    before = len(phase.get("milestones", []))
    phase["milestones"] = [
        milestone
        for milestone in phase.get("milestones", [])
        if milestone.get("milestone_id") != milestone_id
    ]
    if len(phase["milestones"]) == before:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone not found",
        )
    _write_scope(data)
    return {"success": True}


def create_item(
    phase_id: str,
    milestone_id: str,
    payload: ItemCreateRequest,
    track: str = DEFAULT_TRACK,
):
    data = _read_scope()
    phase = _find_phase(data, phase_id, track)
    milestone = _find_milestone(phase, milestone_id)
    item = {
        "item_id": _new_id("ITM"),
        "title": payload.title,
        "description": payload.description,
        "status": payload.status,
        "item_type": payload.item_type,
        "owner": payload.owner,
        "due_date": payload.due_date,
    }
    milestone.setdefault("items", []).append(item)
    _write_scope(data)
    return {"success": True, "data": item}


def update_item(
    phase_id: str,
    milestone_id: str,
    item_id: str,
    payload: ItemUpdateRequest,
    track: str = DEFAULT_TRACK,
):
    data = _read_scope()
    phase = _find_phase(data, phase_id, track)
    milestone = _find_milestone(phase, milestone_id)
    item = _find_item(milestone, item_id)

    if payload.title is not None:
        item["title"] = payload.title
    if payload.description is not None:
        item["description"] = payload.description
    if payload.status is not None:
        item["status"] = payload.status
    if payload.item_type is not None:
        item["item_type"] = payload.item_type
    if payload.owner is not None:
        item["owner"] = payload.owner
    if payload.due_date is not None:
        item["due_date"] = payload.due_date

    _write_scope(data)
    return {"success": True, "data": item}


def delete_item(
    phase_id: str,
    milestone_id: str,
    item_id: str,
    track: str = DEFAULT_TRACK,
):
    data = _read_scope()
    phase = _find_phase(data, phase_id, track)
    milestone = _find_milestone(phase, milestone_id)
    before = len(milestone.get("items", []))
    milestone["items"] = [
        item for item in milestone.get("items", []) if item.get("item_id") != item_id
    ]
    if len(milestone["items"]) == before:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    _write_scope(data)
    return {"success": True}
