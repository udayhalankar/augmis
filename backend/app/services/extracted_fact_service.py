import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db_models import Document, DocumentChunk, ExtractedFact
from app.services.work_area_service import get_work_area_definition, get_work_areas


_ID_PATTERNS = {
    "contract_no": r"\bCTR-\d{4}-\d{4,5}-\d{4,5}\b",
    "po_no": r"\bPO-\d{4}-\d{4,5}\b",
    "invoice_no": r"\bINV-\d{4}-\d{4,5}\b",
    "grn_no": r"\bGRN-\d{4}-\d{4,5}\b",
    "delivery_note_no": r"\bDN-\d{4}-\d{4,5}\b",
    "service_entry_no": r"\bSES-\d{4}-\d{4,5}\b",
    "vendor_id": r"\bVEN-\d{3,6}\b",
}

_FIELD_ALIASES = {
    "contract number": "contract_no",
    "contract id": "contract_no",
    "contract no": "contract_no",
    "po number": "po_no",
    "po no": "po_no",
    "purchase order": "po_no",
    "purchase order no": "po_no",
    "invoice number": "invoice_no",
    "invoice no": "invoice_no",
    "vendor name": "vendor_name",
    "counterparty name": "counterparty",
    "service entry number": "service_entry_no",
    "service entry no": "service_entry_no",
    "delivery note number": "delivery_note_no",
    "delivery note no": "delivery_note_no",
    "grn number": "grn_no",
    "grn no": "grn_no",
    "expiry date": "expiry_date",
    "end date": "expiry_date",
    "start date": "start_date",
    "document date": "document_date",
    "utilization": "utilization_percent",
    "utilization percent": "utilization_percent",
    "remaining value": "remaining_value",
    "available value": "remaining_value",
    "contract value": "contract_value",
    "invoice value": "invoice_value",
    "po value": "po_value",
    "status": "status",
}

_ENABLED_CHECK_RULES = {
    "expiring within 30 days": {
        "field": "expiry_days",
        "operator": "<=",
        "value": 30,
        "label": "expiring within 30 days",
        "severity": "High",
        "rule_type": "threshold",
    },
    "contract utilization above 80%": {
        "field": "utilization_percent",
        "operator": ">=",
        "value": 80,
        "label": "contract utilization above 80%",
        "severity": "High",
        "rule_type": "threshold",
    },
    "contract value exceeded": {
        "field": "remaining_value",
        "operator": "<=",
        "value": 0,
        "label": "contract value exceeded",
        "severity": "Critical",
        "rule_type": "risk",
    },
    "renewal pending": {
        "field": "status",
        "operator": "contains",
        "value": "renewal",
        "label": "renewal pending",
        "severity": "High",
        "rule_type": "risk",
    },
    "invoice greater than po": {
        "field": "invoice_value",
        "operator": ">",
        "compare_field": "po_value",
        "label": "invoice greater than po",
        "severity": "High",
        "rule_type": "risk",
    },
    "missing grn": {
        "field": "grn_no",
        "operator": "missing",
        "value": True,
        "label": "missing grn",
        "severity": "High",
        "rule_type": "risk",
    },
    "quantity mismatch": {
        "field": "quantity_mismatch",
        "operator": "==",
        "value": True,
        "label": "quantity mismatch",
        "severity": "Medium",
        "rule_type": "risk",
    },
    "overdue approval": {
        "field": "aging_days",
        "operator": ">=",
        "value": 20,
        "label": "overdue approval",
        "severity": "High",
        "rule_type": "threshold",
    },
    "supplier performance below threshold": {
        "field": "on_time_delivery_percent",
        "operator": "<",
        "value": 80,
        "label": "supplier performance below threshold",
        "severity": "High",
        "rule_type": "risk",
    },
    "repeated delays": {
        "field": "delay_count",
        "operator": ">=",
        "value": 2,
        "label": "repeated delays",
        "severity": "Medium",
        "rule_type": "risk",
    },
    "compliance lapse": {
        "field": "compliance_status",
        "operator": "contains",
        "value": "lapse",
        "label": "compliance lapse",
        "severity": "High",
        "rule_type": "risk",
    },
    "critical incident open": {
        "field": "severity",
        "operator": "in",
        "value": ["High", "Critical"],
        "label": "critical incident open",
        "severity": "Critical",
        "rule_type": "risk",
    },
    "sla breach": {
        "field": "status",
        "operator": "contains",
        "value": "sla breached",
        "label": "sla breach",
        "severity": "High",
        "rule_type": "risk",
    },
}


def _normalize_text(value) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "missing":
        return actual in (None, "", [], {})
    if operator == "exists":
        return actual not in (None, "", [], {})
    if operator == "contains":
        return _normalize_text(expected) in _normalize_text(actual)
    if operator == "in":
        if isinstance(expected, list):
            expected_values = {_normalize_text(item) for item in expected}
            return _normalize_text(actual) in expected_values
        return _normalize_text(actual) == _normalize_text(expected)

    try:
        left = float(actual)
        right = float(expected)
        numeric = True
    except Exception:
        numeric = False
        left = actual
        right = expected

    if not numeric:
        left = _normalize_text(actual)
        right = _normalize_text(expected)

    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    if operator == ">":
        return left > right
    if operator == ">=":
        return left >= right
    if operator == "<":
        return left < right
    if operator == "<=":
        return left <= right
    return False


def _canonical_field_name(value: str | None) -> str:
    normalized = _normalize_text(value).replace("-", " ").replace("_", " ")
    if normalized in _FIELD_ALIASES:
        return _FIELD_ALIASES[normalized]
    return normalized.replace(" ", "_")


def _safe_float(value):
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").replace("SAR", "").replace("USD", "").strip())
    except Exception:
        return None


def _extract_first(pattern: str, text: str, flags: int = re.IGNORECASE) -> str | None:
    match = re.search(pattern, text, flags)
    if not match:
        return None
    return str(match.group(1) if match.groups() else match.group(0)).strip()


def _extract_identifier(field: str, text: str, file_name: str) -> str | None:
    pattern = _ID_PATTERNS.get(field)
    if not pattern:
        return None
    return _extract_first(pattern, f"{file_name}\n{text}")


def _extract_labeled_number(text: str, labels: list[str], suffix: str = ""):
    for label in labels:
        escaped = re.escape(label)
        pattern = rf"{escaped}\s*[:\-]?\s*(?:SAR|USD|AED|INR)?\s*([0-9][0-9,]*\.?[0-9]*){suffix}"
        value = _extract_first(pattern, text)
        if value is not None:
            number = _safe_float(value)
            if number is not None:
                return number
    return None


def _extract_labeled_date(text: str, labels: list[str]) -> str | None:
    for label in labels:
        escaped = re.escape(label)
        pattern = rf"{escaped}\s*[:\-]?\s*([0-9]{{1,2}}\s+[A-Za-z]{{3,9}}\s+[0-9]{{4}}|[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})"
        value = _extract_first(pattern, text)
        if value:
            return value
    return None


def _parse_date(value: str | None):
    if not value:
        return None
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def _extract_status(text: str) -> str | None:
    status_value = _extract_first(r"Status\s*[:\-]?\s*([A-Za-z][A-Za-z0-9 %\-]+)", text)
    if status_value:
        return status_value.split("Contract Type")[0].strip()
    for phrase in [
        "renewal lapsed pending commercial revalidation",
        "renewal pending",
        "expiring soon",
        "expired",
        "pending approval",
        "escalated",
        "closed",
    ]:
        if phrase in text.lower():
            return phrase.title()
    return None


def _extract_party_from_filename(file_name: str) -> str | None:
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", file_name)
    if "_" not in stem:
        return None
    parts = stem.split("_")
    if len(parts) <= 1:
        return None
    candidate = " ".join(parts[1:]).replace("..", ".").strip(" ._")
    return candidate.replace("_", " ").strip() or None


def _extract_counterparty(text: str, file_name: str) -> str | None:
    patterns = [
        r"entered into between .*? and ([A-Za-z0-9&.,'()\- ]+?) for the provision",
        r"with ([A-Za-z0-9&.,'()\- ]+?)\s+Vendor ID",
        r"Authorized Signatory:\s*([A-Za-z0-9&.,'()\- ]+)",
    ]
    for pattern in patterns:
        value = _extract_first(pattern, text)
        if value:
            return value.strip()
    return _extract_party_from_filename(file_name)


def _extract_text_flags(text: str) -> dict:
    lowered = text.lower()
    return {
        "quantity_mismatch": "quantity discrepancy" in lowered or "quantity mismatch" in lowered,
        "missing_grn_flag": "missing grn" in lowered,
        "renewal_pending_flag": "renewal pending" in lowered or "renewal lapsed" in lowered,
        "compliance_status": "compliance lapse" if "compliance lapse" in lowered else None,
    }


def _build_target_fields(work_area: dict) -> list[str]:
    fields = {
        "document_id",
        "repository_id",
        "business_area",
        "file_name",
        "record_id",
        "status",
        "document_date",
        "start_date",
        "expiry_date",
        "expiry_days",
        "aging_days",
        "text_status",
        "ocr_used",
        "ocr_available",
        "page_count",
        "chunk_count",
        "extracted_characters",
        "summary_focus_text",
        "required_specifics_text",
    }
    for item in work_area.get("entities_to_extract") or []:
        fields.add(_canonical_field_name(str(item)))
    for rule in (work_area.get("threshold_rules") or []) + (work_area.get("risk_rules") or []):
        if rule.get("field"):
            fields.add(_canonical_field_name(rule.get("field")))
        if rule.get("compare_field"):
            fields.add(_canonical_field_name(rule.get("compare_field")))
    return sorted(fields)


def compile_enabled_checks(work_area: dict) -> list[dict]:
    compiled = []
    existing_rules = []
    for rule_type, rules in (("threshold", work_area.get("threshold_rules") or []), ("risk", work_area.get("risk_rules") or [])):
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            normalized_rule = dict(rule)
            normalized_rule["field"] = _canonical_field_name(rule.get("field"))
            normalized_rule["compare_field"] = _canonical_field_name(rule.get("compare_field")) if rule.get("compare_field") else None
            normalized_rule["label"] = str(rule.get("label") or rule.get("name") or normalized_rule["field"]).strip()
            normalized_rule["rule_type"] = rule_type
            normalized_rule["enabled_by_pattern"] = True
            existing_rules.append(normalized_rule)

    enabled_checks = [_normalize_text(item) for item in (work_area.get("enabled_checks") or []) if _normalize_text(item)]
    if not enabled_checks:
        return existing_rules

    for enabled_check in enabled_checks:
        matched = [
            rule for rule in existing_rules
            if enabled_check in _normalize_text(rule.get("label"))
            or _normalize_text(rule.get("label")) in enabled_check
            or enabled_check == _normalize_text(rule.get("field"))
        ]
        if matched:
            compiled.extend(matched)
            continue

        generated = _ENABLED_CHECK_RULES.get(enabled_check)
        if generated:
            generated_rule = dict(generated)
            generated_rule["enabled_by_pattern"] = True
            generated_rule["generated_from_enabled_check"] = enabled_check
            compiled.append(generated_rule)
        else:
            compiled.append(
                {
                    "label": enabled_check,
                    "rule_type": "informational",
                    "enabled_by_pattern": True,
                    "generated_from_enabled_check": enabled_check,
                    "unsupported": True,
                }
            )

    unique = []
    seen = set()
    for rule in compiled:
        key = (
            rule.get("rule_type"),
            rule.get("label"),
            rule.get("field"),
            rule.get("operator"),
            str(rule.get("value")),
            rule.get("compare_field"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(rule)
    return unique


def _normalize_rule(rule_type: str, rule: dict) -> dict:
    normalized = dict(rule)
    normalized["field"] = _canonical_field_name(rule.get("field"))
    normalized["compare_field"] = (
        _canonical_field_name(rule.get("compare_field"))
        if rule.get("compare_field")
        else None
    )
    normalized["label"] = str(
        rule.get("label") or rule.get("name") or normalized["field"] or "rule"
    ).strip()
    normalized["rule_type"] = rule_type
    return normalized


def build_executable_rules(work_area: dict) -> list[dict]:
    rules = []
    for rule_type, items in (
        ("threshold", work_area.get("threshold_rules") or []),
        ("risk", work_area.get("risk_rules") or []),
    ):
        for item in items:
            if isinstance(item, dict):
                rules.append(_normalize_rule(rule_type, item))

    for item in compile_enabled_checks(work_area):
        if not isinstance(item, dict):
            continue
        if item.get("rule_type") not in {"threshold", "risk"}:
            continue
        rules.append(_normalize_rule(item.get("rule_type"), item))

    unique = []
    seen = set()
    for rule in rules:
        key = (
            rule.get("rule_type"),
            rule.get("label"),
            rule.get("field"),
            rule.get("operator"),
            str(rule.get("value")),
            rule.get("compare_field"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(rule)
    return unique


def build_ai_risk_signals_for_work_area(
    tenant_id: str,
    work_area_name: str,
    *,
    db: Session,
) -> list[dict]:
    work_area = get_work_area_definition(tenant_id, work_area_name)
    if not work_area:
        return []

    extracted_facts = get_extracted_facts_for_work_area(
        tenant_id,
        work_area_name,
        db=db,
    )
    executable_rules = build_executable_rules(work_area)
    signals = []

    for fact_row in extracted_facts:
        facts = fact_row.get("facts_json") or {}
        for rule in executable_rules:
            field = str(rule.get("field") or "").strip()
            operator = str(rule.get("operator") or "").strip()
            expected = rule.get("value")
            compare_field = str(rule.get("compare_field") or "").strip() or None
            if not field or not operator:
                continue

            actual = facts.get(field)
            if operator not in {"missing", "exists"} and actual in (None, ""):
                continue

            resolved_expected = facts.get(compare_field) if compare_field else expected
            if compare_field and resolved_expected in (None, ""):
                continue

            if not _compare(actual, operator, resolved_expected):
                continue

            severity = str(
                rule.get("severity") or ("High" if rule.get("rule_type") == "risk" else "Medium")
            ).strip()
            signals.append(
                {
                    "source": "ai_extracted_fact",
                    "signal_origin": "enabled_check"
                    if rule.get("generated_from_enabled_check")
                    else "configured_rule",
                    "work_area": work_area.get("name"),
                    "intelligence_pattern": work_area.get("intelligence_pattern"),
                    "record_id": fact_row.get("record_id") or fact_row.get("document_id"),
                    "document_id": fact_row.get("document_id"),
                    "file_name": fact_row.get("file_name"),
                    "label": rule.get("label"),
                    "compiled_check": rule.get("generated_from_enabled_check") or rule.get("label"),
                    "severity": severity,
                    "field": field,
                    "operator": operator,
                    "expected": resolved_expected,
                    "actual": actual,
                    "record_date": facts.get("source_modified_at") or facts.get("document_date") or facts.get("expiry_date"),
                    "record": facts,
                }
            )

    return signals


def build_ai_risk_signals_for_tenant(
    tenant_id: str,
    *,
    db: Session,
) -> list[dict]:
    work_areas = get_work_areas(tenant_id).get("data") or []
    signals = []
    for work_area in work_areas:
        name = str(work_area.get("name") or "").strip()
        if not name:
            continue
        signals.extend(
            build_ai_risk_signals_for_work_area(
                tenant_id,
                name,
                db=db,
            )
        )
    return signals


def _extract_fact_value(field: str, text: str, file_name: str, metadata: dict):
    base_field = _canonical_field_name(field)
    if base_field in _ID_PATTERNS:
        return _extract_identifier(base_field, text, file_name)
    if base_field in {"counterparty", "vendor_name"}:
        return _extract_counterparty(text, file_name)
    if base_field in {"status", "renewal_status"}:
        return _extract_status(text)
    if base_field == "utilization_percent":
        return _extract_labeled_number(text, ["Utilization"], suffix=r"%?")
    if base_field in {"contract_value", "invoice_value", "po_value", "remaining_value"}:
        labels_map = {
            "contract_value": ["Contract Value"],
            "invoice_value": ["Invoice Value", "Invoice Amount"],
            "po_value": ["PO Value", "Purchase Order Value"],
            "remaining_value": ["Available Value", "Remaining Value"],
        }
        return _extract_labeled_number(text, labels_map[base_field])
    if base_field in {"start_date", "expiry_date", "document_date"}:
        labels_map = {
            "start_date": ["Start Date", "Created At"],
            "expiry_date": ["End Date", "Expiry Date", "Due Date"],
            "document_date": ["Document Date", "Created At", "Issue Date"],
        }
        return _extract_labeled_date(text, labels_map[base_field])
    if base_field == "linked_invoices":
        return _extract_labeled_number(text, ["Linked Invoices"])
    if base_field == "linked_pos":
        return _extract_labeled_number(text, ["Linked POs", "Linked Pos"])
    if base_field in {"ocr_used", "ocr_available", "page_count", "chunk_count", "extracted_characters", "text_status"}:
        return metadata.get(base_field)
    if base_field == "delay_count":
        return 2 if "repeated delay" in text.lower() or "repeated delays" in text.lower() else 0
    if base_field == "on_time_delivery_percent":
        return _extract_labeled_number(text, ["On Time Delivery", "On-Time Delivery"], suffix=r"%?")
    if base_field == "severity":
        return metadata.get("severity") or _extract_status(text)
    return None


def _build_required_specifics_presence(work_area: dict, facts: dict) -> dict:
    presence = {}
    for item in work_area.get("required_specifics") or []:
        canonical = _canonical_field_name(item)
        presence[item] = facts.get(canonical) not in (None, "", [], {})
    return presence


def _build_summary_payload(work_area: dict, facts: dict) -> dict:
    fields = []
    for item in work_area.get("required_specifics") or []:
        canonical = _canonical_field_name(item)
        if facts.get(canonical) not in (None, "", [], {}):
            fields.append({"field": canonical, "value": facts.get(canonical)})
    return {
        "summary_focus": work_area.get("summary_focus") or [],
        "required_specifics": work_area.get("required_specifics") or [],
        "entities_to_extract": work_area.get("entities_to_extract") or [],
        "summary_template": work_area.get("summary_template") or "",
        "specific_fact_values": fields,
    }


def _build_fact_record(work_area: dict, document: Document, chunk_rows: list[DocumentChunk]) -> dict:
    metadata = document.metadata_json or {}
    chunk_text = "\n\n".join(chunk.chunk_text for chunk in chunk_rows[:3] if chunk.chunk_text)
    file_name = document.file_name or ""
    target_fields = _build_target_fields(work_area)
    flags = _extract_text_flags(chunk_text)

    facts = {
        "document_id": document.document_id,
        "repository_id": document.repository_id,
        "business_area": document.business_area,
        "file_name": file_name,
        "record_id": file_name,
        "text_status": metadata.get("text_status"),
        "ocr_used": bool(metadata.get("ocr_used")),
        "ocr_available": bool(metadata.get("ocr_available")),
        "page_count": metadata.get("page_count"),
        "chunk_count": metadata.get("chunk_count") or len(chunk_rows),
        "extracted_characters": metadata.get("extracted_characters"),
        "document_date": document.created_at.isoformat() if document.created_at else None,
        "source_modified_at": document.source_modified_at.isoformat() if document.source_modified_at else None,
    }

    for field in target_fields:
        if field in facts and facts.get(field) not in (None, ""):
            continue
        value = _extract_fact_value(field, chunk_text, file_name, metadata)
        if value not in (None, ""):
            facts[field] = value

    facts.update({key: value for key, value in flags.items() if value not in (None, "")})

    if not facts.get("record_id"):
        for field in ["contract_no", "po_no", "invoice_no", "service_entry_no", "delivery_note_no", "grn_no"]:
            if facts.get(field):
                facts["record_id"] = facts[field]
                break
        else:
            facts["record_id"] = document.document_id

    for date_field in ["expiry_date", "start_date", "document_date"]:
        parsed = _parse_date(facts.get(date_field))
        if parsed:
            facts[date_field] = parsed.date().isoformat()

    expiry_dt = _parse_date(facts.get("expiry_date"))
    if expiry_dt:
        facts["expiry_days"] = (expiry_dt - datetime.now(timezone.utc)).days

    reference_dt = (
        document.source_modified_at
        or document.modified_at
        or document.created_at
    )
    if reference_dt:
        facts["aging_days"] = max((datetime.now(timezone.utc) - reference_dt).days, 0)

    if facts.get("invoice_value") is None and facts.get("contract_value") is not None and "invoice" in file_name.lower():
        facts["invoice_value"] = facts.get("contract_value")
    if facts.get("po_value") is None and "po-" in file_name.lower():
        facts["po_value"] = facts.get("contract_value")

    compiled_checks = compile_enabled_checks(work_area)
    matched_rule_labels = [rule.get("label") for rule in compiled_checks if rule.get("label")]

    return {
        "document_id": document.document_id,
        "repository_id": document.repository_id,
        "business_area": work_area.get("name") or document.business_area,
        "intelligence_pattern": work_area.get("intelligence_pattern"),
        "file_name": file_name,
        "record_id": facts.get("record_id") or document.document_id,
        "facts_json": facts,
        "extracted_entities": sorted(
            {
                _canonical_field_name(item)
                for item in (work_area.get("entities_to_extract") or [])
                if _canonical_field_name(item)
            }
        ),
        "required_specifics_presence": _build_required_specifics_presence(work_area, facts),
        "compiled_checks": compiled_checks,
        "matched_rule_labels": matched_rule_labels,
        "summary_payload": _build_summary_payload(work_area, facts),
        "source_modified_at": document.source_modified_at,
        "text_excerpt": chunk_text[:1200],
    }


def refresh_extracted_facts_for_work_area(
    tenant_id: str,
    work_area_name: str,
    *,
    db: Session,
) -> list[dict]:
    work_area = get_work_area_definition(tenant_id, work_area_name)
    if not work_area:
        return []

    normalized_area = _normalize_text(work_area.get("name"))
    documents = (
        db.query(Document)
        .filter(
            Document.tenant_id == tenant_id,
            Document.business_area == normalized_area,
            Document.is_current_version == True,
            Document.is_deleted == False,
        )
        .order_by(Document.file_name.asc())
        .all()
    )
    document_ids = [document.document_id for document in documents]
    chunk_rows = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.tenant_id == tenant_id,
            DocumentChunk.document_id.in_(document_ids) if document_ids else False,
            DocumentChunk.is_deleted == False,
        )
        .order_by(DocumentChunk.document_id.asc(), DocumentChunk.chunk_index.asc())
        .all()
        if document_ids
        else []
    )
    chunks_by_document: dict[str, list[DocumentChunk]] = {}
    for chunk in chunk_rows:
        chunks_by_document.setdefault(chunk.document_id, []).append(chunk)

    db.query(ExtractedFact).filter(
        ExtractedFact.tenant_id == tenant_id,
        ExtractedFact.business_area == normalized_area,
    ).delete(synchronize_session=False)

    records = []
    for document in documents:
        record = _build_fact_record(work_area, document, chunks_by_document.get(document.document_id, []))
        db.add(
            ExtractedFact(
                extracted_fact_id=f"FACT-{str(uuid4())[:8].upper()}",
                tenant_id=tenant_id,
                document_id=record["document_id"],
                repository_id=record["repository_id"],
                business_area=record["business_area"],
                intelligence_pattern=record["intelligence_pattern"],
                file_name=record["file_name"],
                record_id=record["record_id"],
                facts_json=record["facts_json"],
                extracted_entities=record["extracted_entities"],
                required_specifics_presence=record["required_specifics_presence"],
                compiled_checks=record["compiled_checks"],
                matched_rule_labels=record["matched_rule_labels"],
                summary_payload=record["summary_payload"],
                source_modified_at=record["source_modified_at"],
            )
        )
        records.append(record)

    db.commit()
    return records


def get_extracted_facts_for_work_area(
    tenant_id: str,
    work_area_name: str,
    *,
    db: Session,
    refresh: bool = False,
) -> list[dict]:
    work_area = get_work_area_definition(tenant_id, work_area_name)
    if not work_area:
        return []

    normalized_area = _normalize_text(work_area.get("name"))
    existing_rows = (
        db.query(ExtractedFact)
        .filter(
            ExtractedFact.tenant_id == tenant_id,
            ExtractedFact.business_area == normalized_area,
        )
        .order_by(ExtractedFact.file_name.asc())
        .all()
    )

    current_documents = (
        db.query(Document)
        .filter(
            Document.tenant_id == tenant_id,
            Document.business_area == normalized_area,
            Document.is_current_version == True,
            Document.is_deleted == False,
        )
        .all()
    )
    document_count = len(current_documents)
    current_signature = max(
        (
            (document.source_modified_at or document.modified_at or document.created_at)
            for document in current_documents
            if (document.source_modified_at or document.modified_at or document.created_at)
        ),
        default=None,
    )
    existing_signature = max(
        (row.source_modified_at for row in existing_rows if row.source_modified_at),
        default=None,
    )

    if refresh or len(existing_rows) != document_count or current_signature != existing_signature:
        return refresh_extracted_facts_for_work_area(tenant_id, normalized_area, db=db)

    return [
        {
            "document_id": row.document_id,
            "repository_id": row.repository_id,
            "business_area": row.business_area,
            "intelligence_pattern": row.intelligence_pattern,
            "file_name": row.file_name,
            "record_id": row.record_id,
            "facts_json": row.facts_json or {},
            "extracted_entities": row.extracted_entities or [],
            "required_specifics_presence": row.required_specifics_presence or {},
            "compiled_checks": row.compiled_checks or [],
            "matched_rule_labels": row.matched_rule_labels or [],
            "summary_payload": row.summary_payload or {},
        }
        for row in existing_rows
    ]
