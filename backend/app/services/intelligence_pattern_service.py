from uuid import uuid4

from app.core.database import SessionLocal
from app.db_models import IntelligencePattern


DEFAULT_DASHBOARD_TYPE = "generic"
DASHBOARD_TYPES = {"generic", "proposal", "procurement", "vendor"}


def normalize_pattern_name(name: str | None) -> str:
    normalized = " ".join(str(name or "").strip().lower().split())
    if not normalized:
        raise ValueError("Pattern name is required.")
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


def normalize_intelligence_pattern(item: dict) -> dict:
    name = normalize_pattern_name(item.get("name", ""))
    dashboard_type = str(item.get("dashboard_type") or DEFAULT_DASHBOARD_TYPE).strip().lower()
    if dashboard_type not in DASHBOARD_TYPES:
        dashboard_type = DEFAULT_DASHBOARD_TYPE

    return {
        "name": name,
        "description": str(item.get("description", "") or "").strip(),
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


def _serialize_pattern(row: IntelligencePattern) -> dict:
    return {
        "name": row.name,
        "description": row.description or "",
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


def list_intelligence_patterns(tenant_id: str) -> dict:
    db = SessionLocal()
    try:
        rows = (
            db.query(IntelligencePattern)
            .filter(IntelligencePattern.tenant_id == tenant_id)
            .order_by(IntelligencePattern.name.asc())
            .all()
        )
        return {"success": True, "data": [_serialize_pattern(row) for row in rows]}
    finally:
        db.close()


def get_intelligence_pattern_definition(tenant_id: str, name: str) -> dict | None:
    normalized_name = normalize_pattern_name(name)
    db = SessionLocal()
    try:
        row = (
            db.query(IntelligencePattern)
            .filter(
                IntelligencePattern.tenant_id == tenant_id,
                IntelligencePattern.name == normalized_name,
            )
            .first()
        )
        return _serialize_pattern(row) if row else None
    finally:
        db.close()


def create_intelligence_pattern(tenant_id: str, **payload) -> dict:
    normalized_payload = normalize_intelligence_pattern(payload)
    db = SessionLocal()
    try:
        existing = (
            db.query(IntelligencePattern)
            .filter(
                IntelligencePattern.tenant_id == tenant_id,
                IntelligencePattern.name == normalized_payload["name"],
            )
            .first()
        )
        if existing:
            raise ValueError("An intelligence pattern with this name already exists.")

        row = IntelligencePattern(
            pattern_id=f"PAT-{str(uuid4())[:8].upper()}",
            tenant_id=tenant_id,
            **{key: value for key, value in normalized_payload.items() if key != "created_at"},
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"success": True, "data": _serialize_pattern(row)}
    finally:
        db.close()


def update_intelligence_pattern(tenant_id: str, existing_name: str, **payload) -> dict:
    normalized_existing_name = normalize_pattern_name(existing_name)
    normalized_payload = normalize_intelligence_pattern(payload)
    db = SessionLocal()
    try:
        row = (
            db.query(IntelligencePattern)
            .filter(
                IntelligencePattern.tenant_id == tenant_id,
                IntelligencePattern.name == normalized_existing_name,
            )
            .first()
        )
        if not row:
            raise ValueError("Intelligence pattern not found.")

        duplicate = (
            db.query(IntelligencePattern)
            .filter(
                IntelligencePattern.tenant_id == tenant_id,
                IntelligencePattern.name == normalized_payload["name"],
                IntelligencePattern.pattern_id != row.pattern_id,
            )
            .first()
        )
        if duplicate:
            raise ValueError("An intelligence pattern with this name already exists.")

        for key, value in normalized_payload.items():
            if key == "created_at":
                continue
            setattr(row, key, value)

        db.commit()
        db.refresh(row)
        return {"success": True, "data": _serialize_pattern(row)}
    finally:
        db.close()


def delete_intelligence_pattern(tenant_id: str, name: str) -> dict:
    normalized_name = normalize_pattern_name(name)
    db = SessionLocal()
    try:
        row = (
            db.query(IntelligencePattern)
            .filter(
                IntelligencePattern.tenant_id == tenant_id,
                IntelligencePattern.name == normalized_name,
            )
            .first()
        )
        if not row:
            raise ValueError("Intelligence pattern not found.")

        db.delete(row)
        db.commit()
        return {"success": True, "data": {"name": normalized_name}}
    finally:
        db.close()
