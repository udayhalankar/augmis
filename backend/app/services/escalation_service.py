from collections import Counter, defaultdict
from datetime import datetime, timezone
import logging
from time import perf_counter

from app.core.database import SessionLocal
from app.db_models import ConnectorFile, Document, Repository
from app.services.performance_cache_service import (
    get_cached_response,
    get_tenant_cache_revision,
    set_cached_response,
)
from app.services.work_area_rule_engine_service import evaluate_all_work_area_rules

logger = logging.getLogger(__name__)
ESCALATION_DASHBOARD_CACHE_VERSION = "v3"


def _aging_days_from_timestamp(value) -> int:
    if not value:
        return 0
    try:
        if isinstance(value, datetime):
            reference = value
        else:
            reference = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        now = datetime.now(reference.tzinfo or timezone.utc)
        return max((now - reference).days, 0)
    except Exception:
        return 0


def _build_operational_escalations(tenant_id: str, *, db=None):
    should_close = db is None
    db = db or SessionLocal()
    escalations = []

    try:
        repositories = (
            db.query(Repository)
            .filter(
                Repository.tenant_id == tenant_id,
                Repository.status == "ACTIVE",
            )
            .all()
        )

        for repo in repositories:
            sync_status = str(repo.last_sync_status or repo.sync_status or "").strip().lower()
            sync_warning = repo.last_sync_error or (repo.sync_metadata or {}).get("discovery_warning", {}).get("message")
            if sync_status in {"failed", "completed_with_errors"}:
                severity = "Critical" if sync_status == "failed" else "High"
                escalations.append(
                    {
                        "escalation_id": f"OPS-SYNC-{repo.repository_id}",
                        "source_module": "Repository Operations",
                        "source_id": repo.repository_id,
                        "title": f"{repo.repository_name} sync requires attention",
                        "department": repo.business_area or "general",
                        "owner": "Repository Admin",
                        "status": "Escalated" if sync_status == "failed" else "In Review",
                        "severity": severity,
                        "sla_breached": "Yes" if _aging_days_from_timestamp(repo.last_sync_started_at or repo.last_sync_completed_at) > 1 else "No",
                        "aging_days": _aging_days_from_timestamp(repo.last_sync_started_at or repo.last_sync_completed_at),
                        "estimated_impact": 250000 if severity == "Critical" else 100000,
                        "escalation_type": "Sync Failure",
                        "description": sync_warning or "Repository sync completed with errors.",
                    }
                )

        documents = (
            db.query(Document, Repository)
            .join(
                Repository,
                Repository.repository_id == Document.repository_id,
            )
            .filter(
                Document.tenant_id == tenant_id,
                Document.is_current_version == True,
                Document.is_deleted == False,
                Repository.status == "ACTIVE",
            )
            .all()
        )

        for document, repo in documents:
            metadata = document.metadata_json or {}
            text_status = str(metadata.get("text_status") or "").strip().lower()
            ocr_available = bool(metadata.get("ocr_available"))
            ocr_error = str(metadata.get("ocr_error") or "").strip()
            extracted_characters = int(metadata.get("extracted_characters") or 0)

            if text_status in {"empty_text", "low_text"} and (not ocr_available or ocr_error):
                severity = "Critical" if text_status == "empty_text" else "High"
                escalations.append(
                    {
                        "escalation_id": f"OPS-OCR-{document.document_id}",
                        "source_module": "Document OCR",
                        "source_id": document.document_id,
                        "title": f"{document.file_name} has low searchable text coverage",
                        "department": repo.business_area or "general",
                        "owner": "Platform OCR",
                        "status": "Open",
                        "severity": severity,
                        "sla_breached": "Yes" if text_status == "empty_text" else "No",
                        "aging_days": _aging_days_from_timestamp(document.modified_at or document.created_at),
                        "estimated_impact": 150000 if severity == "Critical" else 60000,
                        "escalation_type": "OCR Coverage",
                        "description": ocr_error or f"Indexed text is too low ({extracted_characters} chars) and OCR was unavailable.",
                    }
                )

        failed_connector_files = (
            db.query(ConnectorFile, Repository)
            .join(
                Repository,
                Repository.repository_id == ConnectorFile.repository_id,
            )
            .filter(
                ConnectorFile.tenant_id == tenant_id,
                ConnectorFile.is_current_version == True,
                ConnectorFile.sync_status == "failed",
                Repository.status == "ACTIVE",
            )
            .all()
        )

        for connector_file, repo in failed_connector_files:
            error_message = str(connector_file.last_error_message or "Connector ingestion failed").strip()
            escalations.append(
                {
                    "escalation_id": f"OPS-INGEST-{connector_file.id}",
                    "source_module": "Document Indexing",
                    "source_id": connector_file.external_file_id or connector_file.id,
                    "title": f"{connector_file.file_name} failed indexing",
                    "department": repo.business_area or "general",
                    "owner": "Repository Admin",
                    "status": "Escalated",
                    "severity": "High",
                    "sla_breached": "Yes" if _aging_days_from_timestamp(connector_file.modified_at or connector_file.created_at) > 1 else "No",
                    "aging_days": _aging_days_from_timestamp(connector_file.modified_at or connector_file.created_at),
                    "estimated_impact": 75000,
                    "escalation_type": "Indexing Failure",
                    "description": error_message,
                }
            )
    finally:
        if should_close:
            db.close()

    return escalations


def _generate_escalations(tenant_id: str, *, db=None):
    escalations = []
    rule_findings = evaluate_all_work_area_rules(tenant_id, db=db).get("data", {}).get("findings", [])
    for finding in rule_findings:
        severity = str(finding.get("severity") or "Medium")
        if severity not in {"Medium", "High", "Critical"}:
            continue
        work_area_name = str(finding.get("work_area") or "Business Area").strip()
        escalation_reason = (
            f"{finding.get('label')} because {finding.get('field')} "
            f"{finding.get('operator')} {finding.get('expected')} "
            f"(actual: {finding.get('actual')})"
        )
        escalations.append(
            {
                "escalation_id": f"RULE-{str(finding.get('work_area') or 'GEN').upper()}-{finding.get('record_id')}",
                "source_module": work_area_name,
                "source_id": finding.get("record_id"),
                "title": f"{finding.get('label')} triggered",
                "department": work_area_name,
                "owner": "Business Area Intelligence",
                "status": "Open",
                "severity": severity,
                "sla_breached": "No",
                "aging_days": 0,
                "estimated_impact": 150000 if severity == "Critical" else 60000,
                "escalation_type": "Rule Breach",
                "escalation_reason": escalation_reason,
                "description": escalation_reason,
            }
        )

    escalations.sort(
        key=lambda e: (
            {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}.get(e.get("severity"), 0),
            e.get("aging_days", 0),
        ),
        reverse=True,
    )

    return escalations


def _build_escalation_dashboard_payload(
    tenant_id: str,
    *,
    include_records: bool = True,
    db=None,
):
    escalations = _generate_escalations(tenant_id, db=db)
    total = len(escalations)

    active_escalations = len(
        [e for e in escalations if e["status"] in ["Open", "In Review", "Escalated"]]
    )

    critical = len([e for e in escalations if e["severity"] == "Critical"])
    sla_breached = len([e for e in escalations if e["sla_breached"] == "Yes"])
    overdue = len([e for e in escalations if int(e["aging_days"] or 0) > 20])
    total_impact = sum(float(e["estimated_impact"] or 0) for e in escalations)

    avg_aging = (
        round(sum(int(e["aging_days"] or 0) for e in escalations) / total, 1)
        if total
        else 0
    )

    status_distribution = Counter(e["status"] for e in escalations)
    severity_distribution = Counter(e["severity"] for e in escalations)
    type_distribution = Counter(e["escalation_type"] for e in escalations)
    source_distribution = Counter(e["source_module"] for e in escalations)

    aging_buckets = {
        "0-7 days": 0,
        "8-14 days": 0,
        "15-30 days": 0,
        "30+ days": 0,
    }

    for e in escalations:
        aging = int(e["aging_days"] or 0)

        if aging <= 7:
            aging_buckets["0-7 days"] += 1
        elif aging <= 14:
            aging_buckets["8-14 days"] += 1
        elif aging <= 30:
            aging_buckets["15-30 days"] += 1
        else:
            aging_buckets["30+ days"] += 1

    department_hotspots = Counter(e["department"] for e in escalations)

    owner_load = Counter(
        e["owner"]
        for e in escalations
        if e["status"] in ["Open", "In Review", "Escalated"]
    )

    impact_by_department = defaultdict(float)
    for e in escalations:
        impact_by_department[e["department"]] += float(e["estimated_impact"] or 0)

    sla_by_department = defaultdict(lambda: {"breached": 0, "total": 0})

    for e in escalations:
        department = e["department"]
        sla_by_department[department]["total"] += 1

        if e["sla_breached"] == "Yes":
            sla_by_department[department]["breached"] += 1

    sla_breach_chart = [
        {
            "name": dept,
            "value": round((values["breached"] / values["total"]) * 100, 1),
        }
        for dept, values in sla_by_department.items()
    ]

    insights = [
        f"{active_escalations} active business escalations were generated from configured business-area rules.",
        f"{critical} escalations are classified as Critical severity.",
        f"{sla_breached} escalations have breached SLA rules.",
        f"Average escalation aging is {avg_aging} days.",
        f"Estimated business impact exposure is ₹{round(total_impact):,}.",
    ]

    return {
        "success": True,
        "generated_at": datetime.utcnow().isoformat(),
        "data": {
            "kpis": {
                "total_escalations": total,
                "active_escalations": active_escalations,
                "critical": critical,
                "sla_breached": sla_breached,
                "overdue": overdue,
                "avg_aging": avg_aging,
                "total_impact": total_impact,
            },
            "status_distribution": [
                {"name": k, "value": v} for k, v in status_distribution.items()
            ],
            "severity_distribution": [
                {"name": k, "value": v} for k, v in severity_distribution.items()
            ],
            "type_distribution": [
                {"name": k, "value": v} for k, v in type_distribution.items()
            ],
            "source_distribution": [
                {"name": k, "value": v} for k, v in source_distribution.items()
            ],
            "aging_analysis": [
                {"name": k, "value": v} for k, v in aging_buckets.items()
            ],
            "department_hotspots": [
                {"name": k, "value": v} for k, v in department_hotspots.items()
            ],
            "owner_load": [
                {"name": k, "value": v} for k, v in owner_load.items()
            ],
            "impact_by_department": [
                {"name": k, "value": v} for k, v in impact_by_department.items()
            ],
            "sla_breach_by_department": sla_breach_chart,
            "insights": insights,
            "escalations": escalations if include_records else [],
            "records_included": include_records,
            "register_count": len(escalations),
        },
    }


def get_escalation_dashboard(
    tenant_id: str,
    *,
    force_refresh: bool = False,
    include_records: bool = True,
    db=None,
):
    started_at = perf_counter()
    should_close = db is None
    db = db or SessionLocal()

    try:
        revision = get_tenant_cache_revision(db, tenant_id)
    finally:
        if should_close:
            db.close()

    cache_key = f"escalation_dashboard::{ESCALATION_DASHBOARD_CACHE_VERSION}::{tenant_id}::{'full' if include_records else 'summary'}"
    if not force_refresh:
        cached_payload = get_cached_response(cache_key, revision=revision)
        if cached_payload is not None:
            logger.info(
                "escalation_dashboard cache_hit tenant=%s duration_ms=%.2f",
                tenant_id,
                (perf_counter() - started_at) * 1000,
            )
            return cached_payload

    payload = _build_escalation_dashboard_payload(
        tenant_id,
        include_records=include_records,
        db=db,
    )
    set_cached_response(
        cache_key,
        payload,
        revision=revision,
        metadata={"tenant_id": tenant_id, "entity": "escalation_dashboard"},
    )
    logger.info(
        "escalation_dashboard cache_miss tenant=%s escalations=%s duration_ms=%.2f",
        tenant_id,
        len(payload.get("data", {}).get("escalations", [])),
        (perf_counter() - started_at) * 1000,
    )
    return payload
