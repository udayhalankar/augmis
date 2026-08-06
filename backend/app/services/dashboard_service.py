from collections import Counter
from datetime import datetime, timedelta
import logging
from time import perf_counter

from sqlalchemy import func

from app.core.database import SessionLocal
from app.db_models import ConnectorFile, Document, DocumentChunk, Repository
from app.services.extracted_fact_service import build_ai_risk_signals_for_tenant
from app.services.performance_cache_service import (
    get_cached_response,
    get_tenant_cache_revision,
    set_cached_response,
)
from app.services.repository_service import get_allowed_business_areas, get_allowed_repository_ids
from app.services.work_area_rule_engine_service import evaluate_all_work_area_rules

logger = logging.getLogger(__name__)

EXECUTIVE_DASHBOARD_CACHE_VERSION = "v6"


def is_within_date_range(record_date, date_range: str) -> bool:
    if date_range == "All":
        return True

    if not record_date:
        return True

    if isinstance(record_date, str):
        try:
            item_date = datetime.fromisoformat(record_date.replace("Z", ""))
        except Exception:
            return True
    else:
        item_date = record_date

    today = datetime.now(item_date.tzinfo) if getattr(item_date, "tzinfo", None) else datetime.now()

    if date_range == "Last 7 Days":
        return item_date >= today - timedelta(days=7)

    if date_range == "Last 30 Days":
        return item_date >= today - timedelta(days=30)

    if date_range == "This Quarter":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        quarter_start = datetime(today.year, quarter_start_month, 1, tzinfo=getattr(item_date, "tzinfo", None))
        return item_date >= quarter_start

    if date_range == "This Year":
        year_start = datetime(today.year, 1, 1, tzinfo=getattr(item_date, "tzinfo", None))
        return item_date >= year_start

    return True


def passes_dashboard_filters(
    business_area_value: str | None,
    risk_level_value: str | None,
    record_date,
    business_area: str = "All",
    risk_level: str = "All",
    date_range: str = "All",
) -> bool:
    item_business_area = _normalize_business_area_name(business_area_value) or "unclassified"
    item_risk_level = risk_level_value or "Unclassified"
    requested_business_area = _normalize_business_area_filter(business_area)

    if requested_business_area != "All" and item_business_area != requested_business_area:
        return False

    if risk_level != "All" and item_risk_level != risk_level:
        return False

    if not is_within_date_range(record_date, date_range):
        return False

    return True


def _parse_record_date(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except Exception:
        return None


def _normalize_business_area_name(value: str | None) -> str:
    normalized = " ".join(str(value or "").strip().lower().split())
    return normalized


def _normalize_business_area_filter(value: str | None) -> str:
    normalized = _normalize_business_area_name(value)
    return "All" if normalized in {"", "all"} else normalized


def _display_business_area_name(value: str) -> str:
    if not value:
        return "Unclassified"
    return " ".join(part.capitalize() for part in value.split())


def _normalize_risk_bucket(value: str | None) -> str:
    normalized = " ".join(str(value or "").strip().lower().split())
    if normalized == "critical":
        return "High"
    if normalized == "high":
        return "High"
    if normalized == "medium":
        return "Medium"
    if normalized == "low":
        return "Low"
    return "Unclassified"


def _extract_record_date_from_finding(record: dict | None):
    if not isinstance(record, dict):
        return None

    for field in [
        "record_date",
        "created_at",
        "due_date",
        "expiry_date",
        "last_audit_date",
        "source_modified_at",
        "modified",
        "indexed_at",
    ]:
        parsed = _parse_record_date(record.get(field))
        if parsed:
            return parsed

    return None


def _build_rule_finding_records(tenant_id: str, *, db=None) -> list[dict]:
    findings_payload = evaluate_all_work_area_rules(tenant_id, db=db).get("data", {})
    findings = findings_payload.get("findings") or []
    records = []

    for finding in findings:
        record = finding.get("record") or {}
        severity = str(finding.get("severity") or "").strip()
        records.append(
            {
                "source": "rule_engine",
                "label": finding.get("label"),
                "compiled_check": finding.get("compiled_check"),
                "business_area": finding.get("work_area") or record.get("business_area"),
                "risk_level": _normalize_risk_bucket(severity),
                "record_date": _extract_record_date_from_finding(record),
                "record_id": finding.get("record_id"),
                "document_id": finding.get("document_id"),
                "repository_id": record.get("repository_id"),
                "file_name": finding.get("file_name"),
                "field": finding.get("field"),
                "operator": finding.get("operator"),
                "expected": finding.get("expected"),
                "actual": finding.get("actual"),
            }
        )

    return records


def _build_ai_risk_signal_records(tenant_id: str, *, db=None) -> list[dict]:
    signals = build_ai_risk_signals_for_tenant(tenant_id, db=db)
    records = []

    for signal in signals:
        records.append(
            {
                "source": signal.get("source") or "ai_extracted_fact",
                "signal_origin": signal.get("signal_origin"),
                "label": signal.get("label"),
                "compiled_check": signal.get("compiled_check"),
                "business_area": signal.get("work_area") or (signal.get("record") or {}).get("business_area"),
                "risk_level": _normalize_risk_bucket(signal.get("severity")),
                "record_date": _extract_record_date_from_finding(signal.get("record") or {}),
                "record_id": signal.get("record_id"),
                "document_id": signal.get("document_id"),
                "repository_id": (signal.get("record") or {}).get("repository_id"),
                "file_name": signal.get("file_name"),
                "field": signal.get("field"),
                "operator": signal.get("operator"),
                "expected": signal.get("expected"),
                "actual": signal.get("actual"),
            }
        )

    return records


def _merge_risk_records(*record_sets: list[dict]) -> list[dict]:
    merged = []
    seen = set()

    for record_set in record_sets:
        for record in record_set:
            key = (
                record.get("business_area"),
                record.get("record_id"),
                record.get("document_id"),
                record.get("label"),
                record.get("compiled_check"),
                record.get("risk_level"),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(record)

    return merged


def _risk_sort_key(record: dict) -> tuple:
    priority = {
        "High": 0,
        "Medium": 1,
        "Low": 2,
        "Unclassified": 3,
    }
    record_date = record.get("record_date")
    sortable_date = record_date.isoformat() if isinstance(record_date, datetime) else str(record_date or "")
    return (
        priority.get(record.get("risk_level"), 9),
        record.get("business_area") or "",
        record.get("record_id") or "",
        sortable_date,
    )


def _load_repository_scope(
    session,
    current_user: dict,
    business_area: str = "All",
):
    normalized_filter = _normalize_business_area_filter(business_area)
    query = session.query(Repository).filter(
        Repository.tenant_id == current_user["tenant_id"],
        Repository.status == "ACTIVE",
    )

    if current_user.get("role") not in {"TENANT_ADMIN", "SUPER_ADMIN"}:
        allowed_repository_ids = get_allowed_repository_ids(current_user, "read")
        allowed_business_areas = get_allowed_business_areas(current_user, "read")

        if not allowed_repository_ids:
            return []

        query = query.filter(Repository.repository_id.in_(allowed_repository_ids))
        if allowed_business_areas:
            query = query.filter(Repository.business_area.in_(sorted(allowed_business_areas)))

    repositories = query.all()

    if normalized_filter == "All":
        return repositories

    return [
        repo
        for repo in repositories
        if _normalize_business_area_name(repo.business_area) == normalized_filter
    ]


def _build_dashboard_data(
    current_user: dict,
    business_area: str = "All",
    risk_level: str = "All",
    date_range: str = "All",
    *,
    db=None,
):
    should_close = db is None
    session = db or SessionLocal()

    try:
        tenant_id = current_user["tenant_id"]
        repositories = _load_repository_scope(
            session,
            current_user,
            business_area=business_area,
        )
        repository_ids = [repo.repository_id for repo in repositories]

        tracked_file_counts: dict[str, int] = {}
        document_counts: dict[str, int] = {}
        chunk_counts: dict[str, int] = {}

        if repository_ids:
            tracked_file_counts = {
                row.repository_id: int(row.file_count or 0)
                for row in (
                    session.query(
                        ConnectorFile.repository_id,
                        func.count(ConnectorFile.id).label("file_count"),
                    )
                    .filter(
                        ConnectorFile.tenant_id == tenant_id,
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
                    session.query(
                        Document.repository_id,
                        func.count(Document.document_id).label("document_count"),
                    )
                    .filter(
                        Document.tenant_id == tenant_id,
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
                    session.query(
                        DocumentChunk.repository_id,
                        func.count(DocumentChunk.chunk_id).label("chunk_count"),
                    )
                    .filter(
                        DocumentChunk.tenant_id == tenant_id,
                        DocumentChunk.repository_id.in_(repository_ids),
                        DocumentChunk.is_deleted == False,
                    )
                    .group_by(DocumentChunk.repository_id)
                    .all()
                )
            }

        total_tracked_files = sum(tracked_file_counts.values())
        total_indexed_documents = sum(document_counts.values())
        total_chunks = sum(chunk_counts.values())

        repository_items_by_area = Counter()
        repository_counts_by_area = Counter()
        active_repository_counts_by_area = Counter()

        for repo in repositories:
            normalized_area = _normalize_business_area_name(repo.business_area) or "general"
            area_label = _display_business_area_name(normalized_area)
            repository_counts_by_area[area_label] += 1
            active_repository_counts_by_area[area_label] += 1
            repository_items_by_area[area_label] += tracked_file_counts.get(
                repo.repository_id,
                document_counts.get(repo.repository_id, 0),
            )

        rule_records = _build_rule_finding_records(tenant_id, db=session)
        ai_risk_records = _build_ai_risk_signal_records(tenant_id, db=session)
        records = _merge_risk_records(rule_records, ai_risk_records)

        filtered_records = [
            record
            for record in records
            if passes_dashboard_filters(
                business_area_value=record["business_area"],
                risk_level_value=record["risk_level"],
                record_date=record["record_date"],
                business_area=business_area,
                risk_level=risk_level,
                date_range=date_range,
            )
        ]

        risk_counter = Counter()

        for record in filtered_records:
            risk_counter[record["risk_level"] or "Unclassified"] += 1

        high_risk_count = risk_counter.get("High", 0)
        critical_risk_count = risk_counter.get("Critical", 0)
        medium_risk_count = risk_counter.get("Medium", 0)
        low_risk_count = risk_counter.get("Low", 0)
        ai_identified_risk_count = sum(
            1 for record in filtered_records if record.get("source") == "ai_extracted_fact"
        )
        configured_rule_risk_count = sum(
            1 for record in filtered_records if record.get("source") == "rule_engine"
        )
        risk_signal_rows = [
            {
                "source": record.get("source"),
                "signal_origin": record.get("signal_origin"),
                "business_area": record.get("business_area"),
                "risk_level": record.get("risk_level"),
                "label": record.get("label"),
                "compiled_check": record.get("compiled_check"),
                "record_id": record.get("record_id"),
                "document_id": record.get("document_id"),
                "repository_id": record.get("repository_id"),
                "file_name": record.get("file_name"),
                "field": record.get("field"),
                "operator": record.get("operator"),
                "expected": record.get("expected"),
                "actual": record.get("actual"),
                "record_date": (
                    record.get("record_date").isoformat()
                    if isinstance(record.get("record_date"), datetime)
                    else record.get("record_date")
                ),
            }
            for record in sorted(filtered_records, key=_risk_sort_key)
        ]

        return {
            "filters": {
                "business_area": _normalize_business_area_filter(business_area),
                "risk_level": risk_level,
                "date_range": date_range,
            },
            "total_documents": total_tracked_files,
            "total_repository_items": total_tracked_files,
            "indexed_documents": total_indexed_documents,
            "total_chunks": total_chunks,
            "repository_count": len(repositories),
            "active_repository_count": len(repositories),
            "business_area_count": len(repository_counts_by_area),
            "high_risk_count": high_risk_count + critical_risk_count,
            "critical_risk_count": critical_risk_count,
            "medium_risk_count": medium_risk_count,
            "low_risk_count": low_risk_count,
            "risk_distribution": dict(risk_counter),
            "ai_identified_risk_count": ai_identified_risk_count,
            "configured_rule_risk_count": configured_rule_risk_count,
            "risk_signal_rows": risk_signal_rows,
            "business_areas": dict(repository_items_by_area),
            "documents": total_tracked_files,
            "chunks": total_chunks,
            "business_area_counts": dict(repository_items_by_area),
            "business_area_repository_counts": dict(repository_counts_by_area),
            "business_area_active_repository_counts": dict(active_repository_counts_by_area),
            "risk_counts": dict(risk_counter),
        }
    finally:
        if should_close:
            session.close()


def get_dashboard_data(
    current_user: dict,
    business_area: str = "All",
    risk_level: str = "All",
    date_range: str = "All",
    *,
    force_refresh: bool = False,
    db=None,
):
    started_at = perf_counter()
    should_close = db is None
    db = db or SessionLocal()

    try:
        revision = get_tenant_cache_revision(db, current_user["tenant_id"])
    finally:
        if should_close:
            db.close()

    cache_key = (
        f"executive_dashboard::{EXECUTIVE_DASHBOARD_CACHE_VERSION}::{current_user['tenant_id']}::{business_area}::{risk_level}::{date_range}"
    )
    if not force_refresh:
        cached_payload = get_cached_response(cache_key, revision=revision)
        if cached_payload is not None:
            logger.info(
                "executive_dashboard cache_hit tenant=%s filters=%s/%s/%s duration_ms=%.2f",
                current_user["tenant_id"],
                business_area,
                risk_level,
                date_range,
                (perf_counter() - started_at) * 1000,
            )
            return cached_payload

    payload = _build_dashboard_data(
        current_user,
        business_area=business_area,
        risk_level=risk_level,
        date_range=date_range,
        db=db,
    )
    set_cached_response(
        cache_key,
        payload,
        revision=revision,
        metadata={
            "tenant_id": current_user["tenant_id"],
            "entity": "executive_dashboard",
            "filters": {
                "business_area": business_area,
                "risk_level": risk_level,
                "date_range": date_range,
            },
        },
    )
    logger.info(
        "executive_dashboard cache_miss tenant=%s documents=%s chunks=%s filters=%s/%s/%s duration_ms=%.2f",
        current_user["tenant_id"],
        payload.get("documents", 0),
        payload.get("chunks", 0),
        business_area,
        risk_level,
        date_range,
        (perf_counter() - started_at) * 1000,
    )
    return payload
