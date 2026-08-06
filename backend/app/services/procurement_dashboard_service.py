from collections import Counter, defaultdict
from datetime import datetime
import logging
from pathlib import Path
from time import perf_counter

import pandas as pd

from app.core.database import SessionLocal
from app.services.repository_source_service import resolve_repository_source_paths
from app.services.performance_cache_service import (
    get_cached_response,
    get_tenant_cache_revision,
    set_cached_response,
)
SUPPORTED_PROCUREMENT_FILES = {".csv", ".xlsx", ".xls"}
PROCUREMENT_SCHEMA_HINTS = {
    "procurement_id",
    "pr_no",
    "po_no",
    "request_date",
    "po_date",
    "expected_date",
    "due_date",
    "status",
    "risk_level",
    "risk",
    "buyer",
    "requestor",
    "vendor",
    "supplier",
    "item",
    "item_name",
    "material",
    "value_usd",
    "pending_value_usd",
    "department",
    "next_action",
}
PROCUREMENT_SCHEMA_STRONG_HINTS = {"procurement_id", "pr_no", "po_no", "item", "item_name", "material"}
logger = logging.getLogger(__name__)
PROCUREMENT_DASHBOARD_CACHE_VERSION = "v3"


def _clean_value(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def _pick_first(row: dict, *keys: str):
    for key in keys:
        value = row.get(key)
        if value is not None and not pd.isna(value) and str(value).strip() != "":
            return value
    return ""


def _normalize_column_name(value) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _is_relevant_procurement_frame(df: pd.DataFrame) -> bool:
    columns = {_normalize_column_name(column) for column in df.columns}
    matches = len(columns & PROCUREMENT_SCHEMA_HINTS)
    strong_matches = len(columns & PROCUREMENT_SCHEMA_STRONG_HINTS)
    return strong_matches >= 1 and matches >= 3


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


def _parse_int(value) -> int:
    if value is None or value == "" or pd.isna(value):
        return 0

    try:
        return int(float(value))
    except Exception:
        return 0


def _parse_date(value):
    if value is None or value == "" or pd.isna(value):
        return None

    try:
        return pd.to_datetime(value).to_pydatetime()
    except Exception:
        return None


def _normalize_risk(value: str) -> str:
    text = _clean_value(value).lower()

    if text in {"critical", "high", "medium", "low"}:
        return text.capitalize()

    if "high" in text:
        return "High"

    if "medium" in text:
        return "Medium"

    return "Low"


def _normalize_status(value: str) -> str:
    text = _clean_value(value)
    return text or "Draft"


def _normalize_procurement(row: dict, source_file: str, row_number: int) -> dict:
    procurement_id = _clean_value(_pick_first(row, "procurement_id", "PR_No", "PO_No"))
    status = _normalize_status(_pick_first(row, "status", "Status"))
    risk_level = _normalize_risk(_pick_first(row, "risk_level", "Risk_Level", "Risk"))

    created_at_dt = _parse_date(_pick_first(row, "created_at", "Request_Date", "PO_Date"))
    due_date_dt = _parse_date(_pick_first(row, "due_date", "Due_Date", "Expected_Date"))

    explicit_aging = _pick_first(row, "aging_days")
    if explicit_aging not in {"", None}:
        aging_days = _parse_int(explicit_aging)
    elif due_date_dt is not None:
        aging_days = max((datetime.now() - due_date_dt).days, 0)
    elif created_at_dt is not None:
        aging_days = max((datetime.now() - created_at_dt).days, 0)
    else:
        aging_days = 0

    explicit_cycle = _pick_first(row, "cycle_time_days")
    if explicit_cycle not in {"", None}:
        cycle_time_days = _parse_int(explicit_cycle)
    else:
        cycle_time_days = aging_days

    item_name = _clean_value(_pick_first(row, "item_name", "Item", "Material"))
    vendor_name = _clean_value(_pick_first(row, "vendor", "Vendor", "Supplier"))

    return {
        "procurement_id": procurement_id or f"{source_file}:{row_number}",
        "item_name": item_name or "Unspecified Item",
        "department": _clean_value(_pick_first(row, "department", "Buyer")) or "Procurement",
        "requestor": _clean_value(_pick_first(row, "requestor", "Requestor", "Buyer")) or "Unassigned",
        "procurement_type": _clean_value(_pick_first(row, "procurement_type", "Type")) or "Purchase Request",
        "status": status,
        "created_at": created_at_dt.date().isoformat() if created_at_dt else "",
        "due_date": due_date_dt.date().isoformat() if due_date_dt else "",
        "approval_stage": _clean_value(_pick_first(row, "approval_stage", "Next_Action")) or (
            "Completed" if "approved" in status.lower() else "Open"
        ),
        "aging_days": aging_days,
        "cycle_time_days": cycle_time_days,
        "estimated_value": _parse_float(_pick_first(row, "estimated_value", "Value_USD", "Pending_Value_USD")),
        "vendor": vendor_name or "Unknown Vendor",
        "priority": _clean_value(_pick_first(row, "priority")) or risk_level,
        "risk_level": risk_level,
        "source_file": source_file,
    }


def _load_tabular_file(path: Path) -> list[dict]:
    rows: list[dict] = []

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path).fillna("")
        if not _is_relevant_procurement_frame(df):
            return []
        return df.to_dict(orient="records")

    workbook = pd.ExcelFile(path)
    for sheet_name in workbook.sheet_names:
        df = workbook.parse(sheet_name).fillna("")
        if not _is_relevant_procurement_frame(df):
            continue
        rows.extend(df.to_dict(orient="records"))

    return rows


def _load_procurement(source_roots: list[Path]):
    items = []

    for root in source_roots:
        if not root.exists():
            continue

        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_PROCUREMENT_FILES:
                continue

            try:
                for row_number, row in enumerate(_load_tabular_file(path), start=1):
                    items.append(_normalize_procurement(row, path.name, row_number))
            except Exception:
                continue

    return items


def _build_procurement_dashboard_payload(
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
        items = _load_procurement(source_roots)
    finally:
        if should_close:
            db.close()

    total = len(items)

    pending = len([i for i in items if i["status"] == "Pending Approval"])
    escalated = len([i for i in items if i["status"] == "Escalated"])
    overdue = len([i for i in items if i["aging_days"] > 20])
    high_risk = len([i for i in items if i["risk_level"] in ["High", "Critical"]])
    total_value = sum(i["estimated_value"] for i in items)

    avg_cycle_time = (
        round(sum(i["cycle_time_days"] for i in items) / total, 1)
        if total
        else 0
    )

    status_distribution = Counter(i["status"] for i in items)
    type_distribution = Counter(i["procurement_type"] for i in items)
    risk_distribution = Counter(i["risk_level"] for i in items)

    aging_buckets = {
        "0-7 days": 0,
        "8-14 days": 0,
        "15-30 days": 0,
        "30+ days": 0,
    }

    for i in items:
        aging = i["aging_days"]
        if aging <= 7:
            aging_buckets["0-7 days"] += 1
        elif aging <= 14:
            aging_buckets["8-14 days"] += 1
        elif aging <= 30:
            aging_buckets["15-30 days"] += 1
        else:
            aging_buckets["30+ days"] += 1

    department_delay = defaultdict(lambda: {"count": 0, "total_aging": 0})
    for i in items:
        department_delay[i["department"]]["count"] += 1
        department_delay[i["department"]]["total_aging"] += i["aging_days"]

    department_delay_chart = [
        {
            "name": dept,
            "value": round(values["total_aging"] / values["count"], 1),
        }
        for dept, values in department_delay.items()
    ]

    bottlenecks = Counter(
        i["approval_stage"]
        for i in items
        if i["status"] in ["Pending Approval", "Escalated"]
    )

    value_by_department = defaultdict(float)
    for i in items:
        value_by_department[i["department"]] += i["estimated_value"]

    insights = [
        f"{pending} procurement items are pending approval.",
        f"{escalated} procurement items have been escalated for management attention.",
        f"{overdue} procurement items have crossed the 20-day aging threshold.",
        f"Average procurement cycle time is {avg_cycle_time} days.",
        f"Total procurement value exposure is ₹{round(total_value):,}.",
    ]

    return {
        "success": True,
        "generated_at": datetime.utcnow().isoformat(),
        "data": {
            "source_directory": ", ".join(str(path) for path in source_roots),
            "kpis": {
                "total_items": total,
                "pending_approvals": pending,
                "escalated": escalated,
                "overdue": overdue,
                "high_risk": high_risk,
                "avg_cycle_time": avg_cycle_time,
                "total_value": total_value,
            },
            "status_distribution": [
                {"name": k, "value": v} for k, v in status_distribution.items()
            ],
            "type_distribution": [
                {"name": k, "value": v} for k, v in type_distribution.items()
            ],
            "risk_distribution": [
                {"name": k, "value": v} for k, v in risk_distribution.items()
            ],
            "aging_analysis": [
                {"name": k, "value": v} for k, v in aging_buckets.items()
            ],
            "department_delay": department_delay_chart,
            "bottlenecks": [
                {"name": k, "value": v} for k, v in bottlenecks.items()
            ],
            "value_by_department": [
                {"name": k, "value": v} for k, v in value_by_department.items()
            ],
            "insights": insights,
            "procurement": items if include_records else [],
            "records_included": include_records,
            "register_count": len(items),
        },
    }


def get_procurement_dashboard(
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

    cache_key = f"procurement_dashboard::{PROCUREMENT_DASHBOARD_CACHE_VERSION}::{tenant_id}::{'full' if include_records else 'summary'}"
    if not force_refresh:
        cached_payload = get_cached_response(cache_key, revision=revision)
        if cached_payload is not None:
            logger.info(
                "procurement_dashboard cache_hit tenant=%s duration_ms=%.2f",
                tenant_id,
                (perf_counter() - started_at) * 1000,
            )
            return cached_payload

    payload = _build_procurement_dashboard_payload(
        tenant_id,
        include_records=include_records,
        db=db,
    )
    set_cached_response(
        cache_key,
        payload,
        revision=revision,
        metadata={"tenant_id": tenant_id, "entity": "procurement_dashboard"},
    )
    logger.info(
        "procurement_dashboard cache_miss tenant=%s items=%s duration_ms=%.2f",
        tenant_id,
        len(payload.get("data", {}).get("procurement", [])),
        (perf_counter() - started_at) * 1000,
    )
    return payload
