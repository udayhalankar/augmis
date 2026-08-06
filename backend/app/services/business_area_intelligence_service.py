from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db_models import ConnectorFile, Document, DocumentChunk, Repository
from app.services.extracted_fact_service import get_extracted_facts_for_work_area
from app.services.repository_service import get_allowed_business_areas
from app.services.work_area_service import get_work_areas
from app.services.work_area_rule_engine_service import evaluate_work_area_rules

def _normalize_area_name(value: str | None) -> str:
    normalized = " ".join(
        str(value or "")
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )
    return normalized or "general"


def _title_case_area(value: str) -> str:
    return " ".join(part.capitalize() for part in value.split())


def _workspace_path_for_area(area_name: str) -> str:
    slug = "_".join(_normalize_area_name(area_name).split())
    return f"/business-areas/{slug}"


def _status_for_repositories(repositories: list[Repository]) -> tuple[str, str, int]:
    if not repositories:
        return "No repositories", "default", 0

    statuses = [str(repo.last_sync_status or repo.sync_status or "NOT_SYNCED").strip().lower() for repo in repositories]
    issues = sum(
        1
        for status in statuses
        if status in {"failed", "completed_with_errors", "not_synced"}
    )

    if any(status == "running" for status in statuses):
        return "Sync running", "info", issues
    if any(status == "failed" for status in statuses):
        return "Needs attention", "error", issues or 1
    if any(status == "completed_with_errors" for status in statuses):
        return "Indexed with warnings", "warning", issues or 1
    if all(status == "completed" for status in statuses):
        return "Indexed", "success", 0
    if any(status == "not_synced" for status in statuses):
        return "Awaiting first sync", "warning", issues or 1
    return "Ready", "default", issues


def _build_area_descriptions(tenant_id: str) -> dict[str, str]:
    work_area_payload = get_work_areas(tenant_id)
    items = work_area_payload.get("data") or []
    return {
        _normalize_area_name(item.get("name")): item
        for item in items
    }


def _repository_base_query(db: Session, current_user: dict):
    query = db.query(Repository).filter(
        Repository.tenant_id == current_user["tenant_id"],
        Repository.status == "ACTIVE",
    )
    if current_user.get("role") not in {"TENANT_ADMIN", "SUPER_ADMIN"}:
        allowed_areas = set(get_allowed_business_areas(current_user, "read"))
        if allowed_areas:
            query = query.filter(Repository.business_area.in_(sorted(allowed_areas)))
        else:
            query = query.filter(Repository.repository_id == "__no_access__")
    return query


def list_business_area_catalog(db: Session, current_user: dict) -> dict:
    repositories = _repository_base_query(db, current_user).all()
    definitions = _build_area_descriptions(current_user["tenant_id"])

    if not repositories:
        return {
            "success": True,
            "data": [],
        }

    repository_ids = [repo.repository_id for repo in repositories]
    repo_by_area: dict[str, list[Repository]] = defaultdict(list)
    for repo in repositories:
        repo_by_area[_normalize_area_name(repo.business_area)].append(repo)

    tracked_counts = {
        row.repository_id: int(row.file_count or 0)
        for row in (
            db.query(
                ConnectorFile.repository_id,
                func.count(ConnectorFile.id).label("file_count"),
            )
            .filter(
                ConnectorFile.tenant_id == current_user["tenant_id"],
                ConnectorFile.repository_id.in_(repository_ids),
                ConnectorFile.is_current_version == True,
                ConnectorFile.is_deleted == False,
            )
            .group_by(ConnectorFile.repository_id)
            .all()
        )
    }

    document_counts = {
        row.repository_id: int(row.document_count or 0)
        for row in (
            db.query(
                Document.repository_id,
                func.count(Document.document_id).label("document_count"),
            )
            .filter(
                Document.tenant_id == current_user["tenant_id"],
                Document.repository_id.in_(repository_ids),
                Document.is_current_version == True,
                Document.is_deleted == False,
            )
            .group_by(Document.repository_id)
            .all()
        )
    }

    chunk_counts = {
        row.repository_id: int(row.chunk_count or 0)
        for row in (
            db.query(
                DocumentChunk.repository_id,
                func.count(DocumentChunk.chunk_id).label("chunk_count"),
            )
            .filter(
                DocumentChunk.tenant_id == current_user["tenant_id"],
                DocumentChunk.repository_id.in_(repository_ids),
                DocumentChunk.is_deleted == False,
            )
            .group_by(DocumentChunk.repository_id)
            .all()
        )
    }

    cards = []
    for area_name in sorted(repo_by_area.keys()):
        area_repositories = repo_by_area[area_name]
        tracked_files = sum(tracked_counts.get(repo.repository_id, 0) for repo in area_repositories)
        documents_indexed = sum(document_counts.get(repo.repository_id, 0) for repo in area_repositories)
        chunks_indexed = sum(chunk_counts.get(repo.repository_id, 0) for repo in area_repositories)
        status_label, status_tone, issues = _status_for_repositories(area_repositories)
        source_counter = Counter((repo.source_type or "unknown") for repo in area_repositories)

        cards.append(
            {
                "slug": area_name,
                "name": area_name,
                "display_name": _title_case_area(area_name),
                "description": str((definitions.get(area_name) or {}).get("description") or f"Repository-backed intelligence for the {area_name} work area."),
                "path": _workspace_path_for_area(area_name),
                "dashboard_type": str((definitions.get(area_name) or {}).get("dashboard_type") or "generic"),
                "summary_focus": (definitions.get(area_name) or {}).get("summary_focus") or [],
                "required_specifics": (definitions.get(area_name) or {}).get("required_specifics") or [],
                "repository_count": len(area_repositories),
                "active_repository_count": len(area_repositories),
                "tracked_files": tracked_files,
                "documents_indexed": documents_indexed,
                "chunks_indexed": chunks_indexed,
                "status_label": status_label,
                "status_tone": status_tone,
                "needs_attention_count": issues,
                "has_indexed_data": documents_indexed > 0 or chunks_indexed > 0 or tracked_files > 0,
                "source_types": [
                    {"name": key, "value": value}
                    for key, value in sorted(source_counter.items(), key=lambda item: (-item[1], item[0]))
                ],
                "last_sync_at": max(
                    (
                        repo.last_sync_completed_at or repo.last_sync_at
                        for repo in area_repositories
                        if (repo.last_sync_completed_at or repo.last_sync_at)
                    ),
                    default=None,
                ).isoformat()
                if any((repo.last_sync_completed_at or repo.last_sync_at) for repo in area_repositories)
                else None,
            }
        )

    return {
        "success": True,
        "data": cards,
    }


def get_business_area_detail(db: Session, current_user: dict, business_area: str) -> dict:
    area_name = _normalize_area_name(business_area)
    repositories = (
        _repository_base_query(db, current_user)
        .filter(Repository.business_area == area_name)
        .order_by(Repository.repository_name.asc())
        .all()
    )

    if not repositories:
        raise ValueError("Business area not found")

    definitions = _build_area_descriptions(current_user["tenant_id"])
    repository_ids = [repo.repository_id for repo in repositories]

    tracked_counts = {
        row.repository_id: int(row.file_count or 0)
        for row in (
            db.query(
                ConnectorFile.repository_id,
                func.count(ConnectorFile.id).label("file_count"),
            )
            .filter(
                ConnectorFile.tenant_id == current_user["tenant_id"],
                ConnectorFile.repository_id.in_(repository_ids),
                ConnectorFile.is_current_version == True,
                ConnectorFile.is_deleted == False,
            )
            .group_by(ConnectorFile.repository_id)
            .all()
        )
    }
    document_counts = {
        row.repository_id: int(row.document_count or 0)
        for row in (
            db.query(
                Document.repository_id,
                func.count(Document.document_id).label("document_count"),
            )
            .filter(
                Document.tenant_id == current_user["tenant_id"],
                Document.repository_id.in_(repository_ids),
                Document.is_current_version == True,
                Document.is_deleted == False,
            )
            .group_by(Document.repository_id)
            .all()
        )
    }
    chunk_counts = {
        row.repository_id: int(row.chunk_count or 0)
        for row in (
            db.query(
                DocumentChunk.repository_id,
                func.count(DocumentChunk.chunk_id).label("chunk_count"),
            )
            .filter(
                DocumentChunk.tenant_id == current_user["tenant_id"],
                DocumentChunk.repository_id.in_(repository_ids),
                DocumentChunk.is_deleted == False,
            )
            .group_by(DocumentChunk.repository_id)
            .all()
        )
    }

    status_label, status_tone, issues = _status_for_repositories(repositories)
    extracted_facts = get_extracted_facts_for_work_area(
        current_user["tenant_id"],
        area_name,
        db=db,
    )
    rule_payload = evaluate_work_area_rules(current_user["tenant_id"], area_name, db=db).get("data", {})
    sync_status_distribution = Counter(
        (repo.last_sync_status or repo.sync_status or "NOT_SYNCED").replace("_", " ").title()
        for repo in repositories
    )
    source_distribution = Counter((repo.source_type or "unknown").title() for repo in repositories)
    repository_cards = []
    for repo in repositories:
        tracked_files = tracked_counts.get(repo.repository_id, 0)
        documents_indexed = document_counts.get(repo.repository_id, 0)
        chunks_indexed = chunk_counts.get(repo.repository_id, 0)
        sync_status = str(repo.last_sync_status or repo.sync_status or "NOT_SYNCED").replace("_", " ").title()
        repository_cards.append(
            {
                "repository_id": repo.repository_id,
                "repository_name": repo.repository_name,
                "source_type": (repo.source_type or "unknown").title(),
                "sync_status": sync_status,
                "tracked_files": tracked_files,
                "documents_indexed": documents_indexed,
                "chunks_indexed": chunks_indexed,
                "last_sync_at": (
                    repo.last_sync_completed_at or repo.last_sync_at
                ).isoformat()
                if (repo.last_sync_completed_at or repo.last_sync_at)
                else None,
                "last_sync_error": repo.last_sync_error,
            }
        )

    repository_cards.sort(
        key=lambda item: (
            0 if item["sync_status"] == "Completed" else 1,
            item["repository_name"].lower(),
        )
    )

    insights = [
        f"{len(repositories)} active repository{'ies' if len(repositories) != 1 else ''} are mapped to this work area.",
        f"{sum(tracked_counts.values())} tracked source files and {sum(chunk_counts.values())} searchable chunks are currently associated with this area.",
    ]
    if issues:
        insights.append(f"{issues} repository sync status item(s) need attention before intelligence is fully reliable.")
    else:
        insights.append("All repositories in this work area are currently synchronized without reported warnings.")
    if rule_payload.get("finding_count"):
        insights.append(
            f"{rule_payload.get('finding_count')} configured rule finding(s) were detected for this work area."
        )
    if extracted_facts:
        insights.append(
            f"{len(extracted_facts)} extracted fact record(s) are available for pattern-driven intelligence in this work area."
        )

    return {
        "success": True,
        "data": {
            "slug": area_name,
            "name": area_name,
            "display_name": _title_case_area(area_name),
            "description": str((definitions.get(area_name) or {}).get("description") or f"Repository-backed intelligence for the {area_name} work area."),
            "path": _workspace_path_for_area(area_name),
            "dashboard_type": str((definitions.get(area_name) or {}).get("dashboard_type") or "generic"),
            "summary_focus": (definitions.get(area_name) or {}).get("summary_focus") or [],
            "required_specifics": (definitions.get(area_name) or {}).get("required_specifics") or [],
            "entities_to_extract": (definitions.get(area_name) or {}).get("entities_to_extract") or [],
            "threshold_rules": (definitions.get(area_name) or {}).get("threshold_rules") or [],
            "enabled_checks": (definitions.get(area_name) or {}).get("enabled_checks") or [],
            "extracted_fact_count": len(extracted_facts),
            "extracted_fact_samples": [
                {
                    "record_id": fact.get("record_id"),
                    "file_name": fact.get("file_name"),
                    "facts": fact.get("facts_json") or {},
                    "compiled_checks": fact.get("compiled_checks") or [],
                }
                for fact in extracted_facts[:10]
            ],
            "rule_summary": rule_payload.get("summary") or {},
            "rule_finding_count": rule_payload.get("finding_count") or 0,
            "rule_findings": rule_payload.get("findings") or [],
            "status_label": status_label,
            "status_tone": status_tone,
            "metrics": {
                "repository_count": len(repositories),
                "tracked_files": sum(tracked_counts.values()),
                "documents_indexed": sum(document_counts.values()),
                "chunks_indexed": sum(chunk_counts.values()),
                "needs_attention_count": issues,
                "active_sources": len({repo.source_type for repo in repositories}),
            },
            "charts": {
                "sync_status_distribution": [
                    {"name": key, "value": value}
                    for key, value in sorted(sync_status_distribution.items(), key=lambda item: (-item[1], item[0]))
                ],
                "source_distribution": [
                    {"name": key, "value": value}
                    for key, value in sorted(source_distribution.items(), key=lambda item: (-item[1], item[0]))
                ],
                "repository_chunk_distribution": [
                    {"name": item["repository_name"], "value": item["chunks_indexed"]}
                    for item in repository_cards
                ],
            },
            "insights": insights,
            "repositories": repository_cards,
            "generated_at": datetime.utcnow().isoformat(),
        },
    }
