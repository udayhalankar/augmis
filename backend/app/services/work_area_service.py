import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.db_models import BusinessArea, Repository
from app.services.intelligence_pattern_service import (
    get_intelligence_pattern_definition,
    normalize_pattern_name,
)


LEGACY_RUNTIME_WORK_AREAS_PATH = (
    Path(__file__).resolve().parents[2] / "storage" / "runtime_work_areas.json"
)

DEFAULT_DASHBOARD_TYPE = "generic"
DASHBOARD_TYPES = {"generic", "proposal", "procurement", "vendor"}


def _normalize_work_area_name(name: str) -> str:
    normalized = " ".join(str(name or "").strip().lower().split())
    if not normalized:
        raise ValueError("Business Area Name is required.")
    return normalized


def _normalize_string_list(values) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized = []
    seen = set()
    for value in values:
        text = " ".join(str(value or "").strip().split())
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(text)
    return normalized


def _normalize_rule_list(values) -> list[dict]:
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, dict)]


def normalize_work_area_definition(item: dict) -> dict:
    name = _normalize_work_area_name(item.get("name", ""))
    intelligence_pattern = str(item.get("intelligence_pattern") or "").strip().lower()
    if intelligence_pattern:
        try:
            intelligence_pattern = normalize_pattern_name(intelligence_pattern)
        except ValueError:
            intelligence_pattern = ""
    dashboard_type = str(item.get("dashboard_type") or DEFAULT_DASHBOARD_TYPE).strip().lower()
    if dashboard_type not in DASHBOARD_TYPES:
        dashboard_type = DEFAULT_DASHBOARD_TYPE

    return {
        "name": name,
        "description": str(item.get("description", "") or "").strip(),
        "intelligence_pattern": intelligence_pattern,
        "dashboard_type": dashboard_type,
        "tags_keywords": _normalize_string_list(item.get("tags_keywords")),
        "summary_focus": _normalize_string_list(item.get("summary_focus")),
        "risk_rules": _normalize_rule_list(item.get("risk_rules")),
        "thresholds": _normalize_rule_list(item.get("thresholds")),
        "required_specifics": _normalize_string_list(item.get("required_specifics")),
        "entities_to_extract": _normalize_string_list(item.get("entities_to_extract")),
        "summary_template": str(item.get("summary_template", "") or "").strip(),
        "threshold_rules": _normalize_rule_list(item.get("threshold_rules")),
        "fact_extractors": _normalize_rule_list(item.get("fact_extractors")),
        "enabled_checks": _normalize_string_list(item.get("enabled_checks")),
        "created_at": item.get("created_at"),
    }


def _serialize_business_area(row: BusinessArea) -> dict:
    return {
        "name": row.name,
        "description": row.description or "",
        "intelligence_pattern": row.intelligence_pattern or "",
        "dashboard_type": row.dashboard_type or DEFAULT_DASHBOARD_TYPE,
        "tags_keywords": row.tags_keywords or [],
        "summary_focus": row.summary_focus or [],
        "risk_rules": row.risk_rules or [],
        "thresholds": row.thresholds or [],
        "required_specifics": row.required_specifics or [],
        "entities_to_extract": row.entities_to_extract or [],
        "summary_template": row.summary_template or "",
        "threshold_rules": row.threshold_rules or [],
        "fact_extractors": row.fact_extractors or [],
        "enabled_checks": row.enabled_checks or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _read_legacy_runtime_file() -> dict:
    if not LEGACY_RUNTIME_WORK_AREAS_PATH.exists():
        return {}
    try:
        data = json.loads(LEGACY_RUNTIME_WORK_AREAS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _import_legacy_business_areas_if_needed(tenant_id: str, db: Session) -> None:
    existing = (
        db.query(BusinessArea)
        .filter(BusinessArea.tenant_id == tenant_id)
        .count()
    )
    if existing:
        return

    runtime_data = _read_legacy_runtime_file()
    tenant_items = runtime_data.get(tenant_id)
    if not isinstance(tenant_items, list) or not tenant_items:
        tenant_items = [
            {
                "name": repository.business_area,
                "description": "",
                "intelligence_pattern": "",
                "dashboard_type": "",
            }
            for repository in (
                db.query(Repository)
                .filter(Repository.tenant_id == tenant_id)
                .order_by(Repository.business_area.asc())
                .all()
            )
            if str(repository.business_area or "").strip()
        ]
        if not tenant_items:
            return

    seen = set()
    for item in tenant_items:
        normalized_item = normalize_work_area_definition(item)
        name = normalized_item["name"]
        if name in seen:
            continue
        seen.add(name)
        db.add(
            BusinessArea(
                business_area_id=f"BA-{str(uuid4())[:8].upper()}",
                tenant_id=tenant_id,
                name=name,
                description=normalized_item["description"],
                intelligence_pattern=normalized_item["intelligence_pattern"],
                dashboard_type=normalized_item["dashboard_type"],
                tags_keywords=normalized_item["tags_keywords"],
                summary_focus=normalized_item["summary_focus"],
                risk_rules=normalized_item["risk_rules"],
                thresholds=normalized_item["thresholds"],
                required_specifics=normalized_item["required_specifics"],
                entities_to_extract=normalized_item["entities_to_extract"],
                summary_template=normalized_item["summary_template"],
                threshold_rules=normalized_item["threshold_rules"],
                fact_extractors=normalized_item["fact_extractors"],
                enabled_checks=normalized_item["enabled_checks"],
            )
        )
    db.commit()


def _merge_pattern_defaults(
    tenant_id: str,
    business_area_definition: dict,
) -> dict:
    intelligence_pattern = str(business_area_definition.get("intelligence_pattern") or "").strip().lower()
    if not intelligence_pattern:
        return business_area_definition

    pattern_definition = get_intelligence_pattern_definition(tenant_id, intelligence_pattern)
    if pattern_definition is None:
        return business_area_definition

    merged = dict(pattern_definition)
    merged.update(business_area_definition)

    for field in [
        "tags_keywords",
        "summary_focus",
        "risk_rules",
        "thresholds",
        "required_specifics",
        "entities_to_extract",
        "threshold_rules",
        "fact_extractors",
        "enabled_checks",
    ]:
        if not merged.get(field):
            merged[field] = pattern_definition.get(field) or []

    if not merged.get("summary_template"):
        merged["summary_template"] = pattern_definition.get("summary_template") or ""

    if not merged.get("dashboard_type"):
        merged["dashboard_type"] = pattern_definition.get("dashboard_type") or DEFAULT_DASHBOARD_TYPE

    merged["intelligence_pattern"] = intelligence_pattern
    merged["intelligence_pattern_definition"] = pattern_definition
    return merged


def get_work_areas(tenant_id: str) -> dict:
    db = SessionLocal()
    try:
        _import_legacy_business_areas_if_needed(tenant_id, db)
        rows = (
            db.query(BusinessArea)
            .filter(BusinessArea.tenant_id == tenant_id)
            .order_by(BusinessArea.name.asc())
            .all()
        )
        data = [_merge_pattern_defaults(tenant_id, _serialize_business_area(row)) for row in rows]
        return {"success": True, "data": data}
    finally:
        db.close()


def get_work_area_definition(tenant_id: str, name: str) -> dict | None:
    normalized_name = _normalize_work_area_name(name)
    db = SessionLocal()
    try:
        _import_legacy_business_areas_if_needed(tenant_id, db)
        row = (
            db.query(BusinessArea)
            .filter(
                BusinessArea.tenant_id == tenant_id,
                BusinessArea.name == normalized_name,
            )
            .first()
        )
        return _merge_pattern_defaults(tenant_id, _serialize_business_area(row)) if row else None
    finally:
        db.close()


def create_work_area(
    tenant_id: str,
    name: str,
    description: str,
    *,
    tags_keywords=None,
    summary_focus=None,
    risk_rules=None,
    thresholds=None,
    required_specifics=None,
    entities_to_extract=None,
    summary_template: str = "",
    threshold_rules=None,
    fact_extractors=None,
    dashboard_type: str = DEFAULT_DASHBOARD_TYPE,
    enabled_checks=None,
    intelligence_pattern: str = "",
) -> dict:
    normalized_item = normalize_work_area_definition(
        {
            "name": name,
            "description": description,
            "intelligence_pattern": intelligence_pattern,
            "tags_keywords": tags_keywords,
            "summary_focus": summary_focus,
            "risk_rules": risk_rules,
            "thresholds": thresholds,
            "required_specifics": required_specifics,
            "entities_to_extract": entities_to_extract,
            "summary_template": summary_template,
            "threshold_rules": threshold_rules,
            "fact_extractors": fact_extractors,
            "dashboard_type": dashboard_type,
            "enabled_checks": enabled_checks,
        }
    )
    db = SessionLocal()
    try:
        _import_legacy_business_areas_if_needed(tenant_id, db)
        existing = (
            db.query(BusinessArea)
            .filter(
                BusinessArea.tenant_id == tenant_id,
                BusinessArea.name == normalized_item["name"],
            )
            .first()
        )
        if existing:
            raise ValueError("A business area with this name already exists.")

        row = BusinessArea(
            business_area_id=f"BA-{str(uuid4())[:8].upper()}",
            tenant_id=tenant_id,
            **{key: value for key, value in normalized_item.items() if key != "created_at"},
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"success": True, "data": _merge_pattern_defaults(tenant_id, _serialize_business_area(row))}
    finally:
        db.close()


def update_work_area(
    tenant_id: str,
    existing_name: str,
    name: str,
    description: str,
    *,
    tags_keywords=None,
    summary_focus=None,
    risk_rules=None,
    thresholds=None,
    required_specifics=None,
    entities_to_extract=None,
    summary_template: str = "",
    threshold_rules=None,
    fact_extractors=None,
    dashboard_type: str = DEFAULT_DASHBOARD_TYPE,
    enabled_checks=None,
    intelligence_pattern: str = "",
) -> dict:
    normalized_existing_name = _normalize_work_area_name(existing_name)
    normalized_item = normalize_work_area_definition(
        {
            "name": name,
            "description": description,
            "intelligence_pattern": intelligence_pattern,
            "tags_keywords": tags_keywords,
            "summary_focus": summary_focus,
            "risk_rules": risk_rules,
            "thresholds": thresholds,
            "required_specifics": required_specifics,
            "entities_to_extract": entities_to_extract,
            "summary_template": summary_template,
            "threshold_rules": threshold_rules,
            "fact_extractors": fact_extractors,
            "dashboard_type": dashboard_type,
            "enabled_checks": enabled_checks,
        }
    )
    db = SessionLocal()
    try:
        _import_legacy_business_areas_if_needed(tenant_id, db)
        row = (
            db.query(BusinessArea)
            .filter(
                BusinessArea.tenant_id == tenant_id,
                BusinessArea.name == normalized_existing_name,
            )
            .first()
        )
        if not row:
            raise ValueError("Business area not found.")

        duplicate = (
            db.query(BusinessArea)
            .filter(
                BusinessArea.tenant_id == tenant_id,
                BusinessArea.name == normalized_item["name"],
                BusinessArea.business_area_id != row.business_area_id,
            )
            .first()
        )
        if duplicate:
            raise ValueError("A business area with this name already exists.")

        for key, value in normalized_item.items():
            if key == "created_at":
                continue
            setattr(row, key, value)

        db.commit()
        db.refresh(row)
        return {
            "success": True,
            "data": {
                **_merge_pattern_defaults(tenant_id, _serialize_business_area(row)),
                "previous_name": normalized_existing_name,
            },
        }
    finally:
        db.close()


def delete_work_area(tenant_id: str, name: str) -> dict:
    normalized_name = _normalize_work_area_name(name)
    db = SessionLocal()
    try:
        _import_legacy_business_areas_if_needed(tenant_id, db)
        row = (
            db.query(BusinessArea)
            .filter(
                BusinessArea.tenant_id == tenant_id,
                BusinessArea.name == normalized_name,
            )
            .first()
        )
        if not row:
            raise ValueError("Business area not found.")

        db.delete(row)
        db.commit()
        return {"success": True, "data": {"name": normalized_name}}
    finally:
        db.close()
