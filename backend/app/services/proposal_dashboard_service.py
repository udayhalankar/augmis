from collections import Counter, defaultdict
from datetime import datetime
import logging
from pathlib import Path
from time import perf_counter

import pandas as pd

from app.core.database import SessionLocal
from app.services.performance_cache_service import (
    get_cached_response,
    get_tenant_cache_revision,
    set_cached_response,
)
from app.services.repository_source_service import resolve_repository_source_paths


SUPPORTED_PROPOSAL_FILES = {".csv", ".xlsx", ".xls"}
PENDING_KEYWORDS = ("pending", "awaiting approval", "clarification", "negotiation", "open")
PROPOSAL_SCHEMA_HINTS = {
    "proposal_id",
    "proposal_no",
    "customer",
    "country",
    "equipment",
    "proposal_date",
    "proposal_value_usd",
    "value_usd",
    "status",
    "sales_owner",
    "owner",
    "next_action",
    "due_date",
    "risk_level",
    "risk",
    "department",
    "title",
}
PROPOSAL_SCHEMA_STRONG_HINTS = {"proposal_id", "proposal_no", "equipment", "customer"}
logger = logging.getLogger(__name__)
PROPOSAL_DASHBOARD_CACHE_VERSION = "v3"


def _clean_value(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def _parse_date(value):
    if not value or pd.isna(value):
        return None

    try:
        return pd.to_datetime(value).to_pydatetime()
    except Exception:
        return None


def _parse_float(value) -> float:
    if value is None or value == "" or pd.isna(value):
        return 0.0

    try:
        return float(value)
    except Exception:
        text = str(value).replace(",", "").replace("$", "").strip()
        try:
            return float(text)
        except Exception:
            return 0.0


def _normalize_column_name(value) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _is_relevant_proposal_frame(df: pd.DataFrame) -> bool:
    columns = {_normalize_column_name(column) for column in df.columns}
    matches = len(columns & PROPOSAL_SCHEMA_HINTS)
    strong_matches = len(columns & PROPOSAL_SCHEMA_STRONG_HINTS)
    return strong_matches >= 1 and matches >= 3


def _normalize_risk(value: str) -> str:
    text = _clean_value(value).lower()

    if text in {"critical", "high", "medium", "low"}:
        return text.capitalize()

    return "Low"


def _pick_first(row: dict, *keys: str):
    for key in keys:
        value = row.get(key)
        if value is not None and not pd.isna(value) and str(value).strip() != "":
            return value
    return ""


def _normalize_status(status: str) -> str:
    text = _clean_value(status)
    return text or "Open"


def _build_title(row: dict) -> str:
    equipment = _clean_value(_pick_first(row, "title", "Equipment"))
    customer = _clean_value(_pick_first(row, "Customer", "vendor"))

    if equipment and customer:
        return f"{equipment} for {customer}"

    if equipment:
        return equipment

    if customer:
        return customer

    return _clean_value(_pick_first(row, "Proposal_No", "proposal_id")) or "Untitled Proposal"


def _normalize_proposal(row: dict, source_file: str, row_number: int) -> dict:
    proposal_id = _clean_value(_pick_first(row, "proposal_id", "Proposal_No"))
    status = _normalize_status(_pick_first(row, "status", "Status"))
    risk_level = _normalize_risk(_pick_first(row, "risk_level", "Risk_Level", "Risk"))
    created_at_dt = _parse_date(_pick_first(row, "created_at", "Proposal_Date"))
    due_date_dt = _parse_date(_pick_first(row, "due_date", "Due_Date"))

    explicit_aging = _pick_first(row, "aging_days")
    if explicit_aging not in {"", None}:
        try:
            aging_days = int(float(explicit_aging))
        except Exception:
            aging_days = 0
    elif due_date_dt is not None:
        aging_days = max((datetime.now() - due_date_dt).days, 0)
    elif created_at_dt is not None:
        aging_days = max((datetime.now() - created_at_dt).days, 0)
    else:
        aging_days = 0

    estimated_value = _parse_float(_pick_first(row, "estimated_value", "Proposal_Value_USD", "Value_USD"))

    approval_stage = _clean_value(_pick_first(row, "approval_stage", "Next_Action"))
    if not approval_stage:
        approval_stage = "Completed" if "approved" in status.lower() else "Open"

    return {
        "proposal_id": proposal_id or f"{source_file}:{row_number}",
        "title": _build_title(row),
        "department": _clean_value(_pick_first(row, "department", "Country")) or "General",
        "owner": _clean_value(_pick_first(row, "owner", "Sales_Owner", "Owner")) or "Unassigned",
        "status": status,
        "created_at": created_at_dt.date().isoformat() if created_at_dt else "",
        "due_date": due_date_dt.date().isoformat() if due_date_dt else "",
        "approval_stage": approval_stage,
        "risk_level": risk_level,
        "aging_days": aging_days,
        "estimated_value": estimated_value,
        "vendor": _clean_value(_pick_first(row, "vendor", "Customer")) or "Unknown",
        "priority": _clean_value(_pick_first(row, "priority")) or risk_level,
        "source_file": source_file,
    }


def _load_tabular_file(path: Path) -> list[dict]:
    rows: list[dict] = []

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path).fillna("")
        if not _is_relevant_proposal_frame(df):
            return []
        return df.to_dict(orient="records")

    workbook = pd.ExcelFile(path)
    for sheet_name in workbook.sheet_names:
        df = workbook.parse(sheet_name).fillna("")
        if not _is_relevant_proposal_frame(df):
            continue
        rows.extend(df.to_dict(orient="records"))

    return rows


def _load_proposals(source_roots: list[Path]):
    proposals = []

    for root in source_roots:
        if not root.exists():
            continue

        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_PROPOSAL_FILES:
                continue

            try:
                for row_number, row in enumerate(_load_tabular_file(path), start=1):
                    proposals.append(_normalize_proposal(row, path.name, row_number))
            except Exception:
                continue

    return proposals


def _build_proposal_dashboard_payload(
    tenant_id: str,
    *,
    include_records: bool = True,
    db=None,
):
    should_close = db is None
    db = db or SessionLocal()
    source_roots: list[Path] = []

    try:
        source_roots = resolve_repository_source_paths(
            db,
            tenant_id,
        )
        proposals = _load_proposals(source_roots)
    finally:
        if should_close:
            db.close()

    total = len(proposals)
    pending = len(
        [p for p in proposals if any(keyword in p["status"].lower() for keyword in PENDING_KEYWORDS)]
    )
    overdue = len(
        [
            p
            for p in proposals
            if p["aging_days"] > 20
            or (p["due_date"] and _parse_date(p["due_date"]) and _parse_date(p["due_date"]) < datetime.now())
        ]
    )
    high_risk = len([p for p in proposals if p["risk_level"] in ["High", "Critical"]])
    total_value = sum(p["estimated_value"] for p in proposals)
    avg_aging = round(sum(p["aging_days"] for p in proposals) / total, 1) if total else 0

    status_distribution = Counter(p["status"] for p in proposals)
    risk_distribution = Counter(p["risk_level"] for p in proposals)

    aging_buckets = {
        "0-7 days": 0,
        "8-14 days": 0,
        "15-30 days": 0,
        "30+ days": 0,
    }

    for p in proposals:
        aging = p["aging_days"]
        if aging <= 7:
            aging_buckets["0-7 days"] += 1
        elif aging <= 14:
            aging_buckets["8-14 days"] += 1
        elif aging <= 30:
            aging_buckets["15-30 days"] += 1
        else:
            aging_buckets["30+ days"] += 1

    department_risk = defaultdict(lambda: {"Low": 0, "Medium": 0, "High": 0, "Critical": 0})
    for p in proposals:
        department_risk[p["department"]][p["risk_level"]] += 1

    bottlenecks = Counter(
        p["approval_stage"]
        for p in proposals
        if any(keyword in p["status"].lower() for keyword in PENDING_KEYWORDS) or "escalated" in p["status"].lower()
    )

    insights = [
        f"{high_risk} proposals are currently classified as High or Critical risk.",
        f"{overdue} proposals have crossed the 20-day aging threshold.",
        f"The highest bottleneck stage is {bottlenecks.most_common(1)[0][0] if bottlenecks else 'N/A'}.",
        f"Average proposal aging is {avg_aging} days across all active proposals.",
    ]

    return {
        "success": True,
        "generated_at": datetime.utcnow().isoformat(),
        "data": {
            "source_directory": ", ".join(str(path) for path in source_roots),
            "kpis": {
                "total_proposals": total,
                "pending_approvals": pending,
                "high_risk": high_risk,
                "overdue": overdue,
                "avg_aging_days": avg_aging,
                "total_value": total_value,
            },
            "status_distribution": [
                {"name": k, "value": v} for k, v in status_distribution.items()
            ],
            "risk_distribution": [
                {"name": k, "value": v} for k, v in risk_distribution.items()
            ],
            "aging_analysis": [
                {"name": k, "value": v} for k, v in aging_buckets.items()
            ],
            "department_risk": [
                {"department": dept, **values}
                for dept, values in department_risk.items()
            ],
            "bottlenecks": [
                {"name": k, "value": v} for k, v in bottlenecks.items()
            ],
            "insights": insights,
            "proposals": proposals if include_records else [],
            "records_included": include_records,
            "register_count": len(proposals),
        },
    }


def get_proposal_dashboard(
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

    cache_key = f"proposal_dashboard::{PROPOSAL_DASHBOARD_CACHE_VERSION}::{tenant_id}::{'full' if include_records else 'summary'}"
    if not force_refresh:
        cached_payload = get_cached_response(cache_key, revision=revision)
        if cached_payload is not None:
            logger.info(
                "proposal_dashboard cache_hit tenant=%s duration_ms=%.2f",
                tenant_id,
                (perf_counter() - started_at) * 1000,
            )
            return cached_payload

    payload = _build_proposal_dashboard_payload(
        tenant_id,
        include_records=include_records,
        db=db,
    )
    set_cached_response(
        cache_key,
        payload,
        revision=revision,
        metadata={"tenant_id": tenant_id, "entity": "proposal_dashboard"},
    )
    logger.info(
        "proposal_dashboard cache_miss tenant=%s proposals=%s duration_ms=%.2f",
        tenant_id,
        len(payload.get("data", {}).get("proposals", [])),
        (perf_counter() - started_at) * 1000,
    )
    return payload
