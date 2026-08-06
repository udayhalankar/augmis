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


SUPPORTED_VENDOR_FILES = {".csv", ".xlsx", ".xls"}
VENDOR_SCHEMA_HINTS = {
    "vendor",
    "vendor_name",
    "vendor_id",
    "supplier",
    "category",
    "material",
    "status",
    "delivery_status",
    "risk_level",
    "risk",
    "issue",
    "risk_remarks",
    "buyer",
    "department",
    "po_no",
    "po_date",
    "pending_value_usd",
    "total_value",
}
VENDOR_SCHEMA_STRONG_HINTS = {"vendor", "vendor_name", "vendor_id", "supplier"}
logger = logging.getLogger(__name__)
VENDOR_DASHBOARD_CACHE_VERSION = "v3"


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


def _is_relevant_vendor_frame(df: pd.DataFrame) -> bool:
    columns = {_normalize_column_name(column) for column in df.columns}
    matches = len(columns & VENDOR_SCHEMA_HINTS)
    strong_matches = len(columns & VENDOR_SCHEMA_STRONG_HINTS)
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


def _normalize_risk(value: str) -> str:
    text = _clean_value(value).lower()

    if text in {"critical", "high", "medium", "low"}:
        return text.capitalize()

    if "high" in text:
        return "High"

    if "medium" in text:
        return "Medium"

    return "Low"


def _normalize_compliance(row: dict) -> str:
    explicit = _clean_value(_pick_first(row, "compliance_status"))
    if explicit:
        return explicit

    issue_text = _clean_value(_pick_first(row, "Issue", "Risk_Remarks")).lower()
    risk = _normalize_risk(_pick_first(row, "risk_level", "Risk_Level"))

    if risk in {"High", "Critical"} or "pending" in issue_text or "expiring" in issue_text:
        return "Partially Compliant"

    return "Compliant"


def _normalize_contract_status(row: dict) -> str:
    explicit = _clean_value(_pick_first(row, "contract_status"))
    if explicit:
        return explicit

    status = _clean_value(_pick_first(row, "Status", "Delivery_Status")).lower()
    if "review" in status:
        return "Under Review"
    if "delay" in status or "pending" in status:
        return "Under Review"
    return "Active"


def _normalize_delivery_percent(row: dict) -> float:
    explicit = _pick_first(row, "on_time_delivery_percent")
    if explicit not in {"", None}:
        return _parse_float(explicit)

    status = _clean_value(_pick_first(row, "Status", "Delivery_Status")).lower()
    if "on track" in status or "dispatched" in status or "delivered" in status:
        return 95.0
    if "delayed" in status:
        return 55.0
    return 75.0


def _normalize_vendor(row: dict, source_file: str, row_number: int) -> dict:
    vendor_name = _clean_value(_pick_first(row, "vendor_name", "Vendor")) or "Unknown Vendor"
    vendor_id = _clean_value(_pick_first(row, "vendor_id", "PO_No")) or f"{source_file}:{row_number}"
    issue_text = _clean_value(_pick_first(row, "Issue", "Risk_Remarks"))
    delivery_percent = _normalize_delivery_percent(row)

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor_name,
        "category": _clean_value(_pick_first(row, "category", "Category", "Material")) or "General",
        "department": _clean_value(_pick_first(row, "department", "Buyer")) or "Procurement",
        "compliance_status": _normalize_compliance(row),
        "risk_level": _normalize_risk(_pick_first(row, "risk_level", "Risk_Level")),
        "delivery_performance": _clean_value(_pick_first(row, "delivery_performance", "Status", "Delivery_Status"))
        or ("Good" if delivery_percent >= 90 else "Average" if delivery_percent >= 70 else "Poor"),
        "on_time_delivery_percent": delivery_percent,
        "open_issues": 1 if issue_text else _parse_int(_pick_first(row, "open_issues")),
        "total_orders": _parse_int(_pick_first(row, "total_orders")) or 1,
        "total_value": _parse_float(_pick_first(row, "total_value", "Pending_Value_USD")),
        "last_audit_date": _clean_value(_pick_first(row, "last_audit_date", "PO_Date")),
        "contract_status": _normalize_contract_status(row),
        "criticality": _clean_value(_pick_first(row, "criticality")) or _normalize_risk(_pick_first(row, "risk_level", "Risk_Level")),
        "source_file": source_file,
        "issue_text": issue_text,
    }


def _load_tabular_file(path: Path) -> list[dict]:
    rows: list[dict] = []

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path).fillna("")
        if not _is_relevant_vendor_frame(df):
            return []
        return df.to_dict(orient="records")

    workbook = pd.ExcelFile(path)
    for sheet_name in workbook.sheet_names:
        df = workbook.parse(sheet_name).fillna("")
        if not _is_relevant_vendor_frame(df):
            continue
        rows.extend(df.to_dict(orient="records"))

    return rows


def _load_vendors(source_roots: list[Path]):
    vendors = []

    for root in source_roots:
        if not root.exists():
            continue

        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_VENDOR_FILES:
                continue

            try:
                for row_number, row in enumerate(_load_tabular_file(path), start=1):
                    vendors.append(_normalize_vendor(row, path.name, row_number))
            except Exception:
                continue

    return vendors


def _build_vendor_dashboard_payload(
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
        vendors = _load_vendors(source_roots)
    finally:
        if should_close:
            db.close()

    total = len(vendors)

    high_risk = len([v for v in vendors if v["risk_level"] in ["High", "Critical"]])
    non_compliant = len([v for v in vendors if v["compliance_status"] == "Non-Compliant"])
    under_review = len([v for v in vendors if v["contract_status"] == "Under Review"])
    total_value = sum(v["total_value"] for v in vendors)
    total_issues = sum(v["open_issues"] for v in vendors)

    avg_delivery = (
        round(sum(v["on_time_delivery_percent"] for v in vendors) / total, 1)
        if total
        else 0
    )

    risk_distribution = Counter(v["risk_level"] for v in vendors)
    compliance_distribution = Counter(v["compliance_status"] for v in vendors)
    category_distribution = Counter(v["category"] for v in vendors)

    department_risk = defaultdict(lambda: {"Low": 0, "Medium": 0, "High": 0, "Critical": 0})
    for v in vendors:
        department_risk[v["department"]][v["risk_level"]] += 1

    issue_hotspots = sorted(
        [{"name": v["vendor_name"], "value": v["open_issues"]} for v in vendors],
        key=lambda x: x["value"],
        reverse=True,
    )[:6]

    delivery_performance = sorted(
        [{"name": v["vendor_name"], "value": v["on_time_delivery_percent"]} for v in vendors],
        key=lambda x: x["value"],
    )[:6]

    insights = [
        f"{high_risk} vendors are currently classified as High or Critical risk.",
        f"{non_compliant} vendors are marked as Non-Compliant and require immediate review.",
        f"Average on-time delivery performance is {avg_delivery}%.",
        f"Total open vendor issues across the supplier base is {total_issues}.",
    ]

    return {
        "success": True,
        "generated_at": datetime.utcnow().isoformat(),
        "data": {
            "source_directory": ", ".join(str(path) for path in source_roots),
            "kpis": {
                "total_vendors": total,
                "high_risk": high_risk,
                "non_compliant": non_compliant,
                "under_review": under_review,
                "avg_delivery": avg_delivery,
                "total_value": total_value,
                "open_issues": total_issues,
            },
            "risk_distribution": [
                {"name": k, "value": v} for k, v in risk_distribution.items()
            ],
            "compliance_distribution": [
                {"name": k, "value": v} for k, v in compliance_distribution.items()
            ],
            "category_distribution": [
                {"name": k, "value": v} for k, v in category_distribution.items()
            ],
            "department_risk": [
                {"department": dept, **values}
                for dept, values in department_risk.items()
            ],
            "issue_hotspots": issue_hotspots,
            "delivery_performance": delivery_performance,
            "insights": insights,
            "vendors": vendors if include_records else [],
            "records_included": include_records,
            "register_count": len(vendors),
        },
    }


def get_vendor_dashboard(
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

    cache_key = f"vendor_dashboard::{VENDOR_DASHBOARD_CACHE_VERSION}::{tenant_id}::{'full' if include_records else 'summary'}"
    if not force_refresh:
        cached_payload = get_cached_response(cache_key, revision=revision)
        if cached_payload is not None:
            logger.info(
                "vendor_dashboard cache_hit tenant=%s duration_ms=%.2f",
                tenant_id,
                (perf_counter() - started_at) * 1000,
            )
            return cached_payload

    payload = _build_vendor_dashboard_payload(
        tenant_id,
        include_records=include_records,
        db=db,
    )
    set_cached_response(
        cache_key,
        payload,
        revision=revision,
        metadata={"tenant_id": tenant_id, "entity": "vendor_dashboard"},
    )
    logger.info(
        "vendor_dashboard cache_miss tenant=%s vendors=%s duration_ms=%.2f",
        tenant_id,
        len(payload.get("data", {}).get("vendors", [])),
        (perf_counter() - started_at) * 1000,
    )
    return payload
