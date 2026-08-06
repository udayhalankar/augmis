from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.services.extracted_fact_service import (
    compile_enabled_checks,
    get_extracted_facts_for_work_area,
)
from app.services.work_area_service import get_work_area_definition, get_work_areas


def _normalize_text(value: Any) -> str:
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


def _normalize_rule(rule_type: str, rule: dict) -> dict:
    normalized = dict(rule)
    normalized["field"] = " ".join(str(rule.get("field") or "").strip().lower().split()).replace(" ", "_")
    normalized["compare_field"] = (
        " ".join(str(rule.get("compare_field") or "").strip().lower().split()).replace(" ", "_")
        if rule.get("compare_field")
        else None
    )
    normalized["label"] = str(rule.get("label") or rule.get("name") or normalized["field"] or "rule").strip()
    normalized["rule_type"] = rule_type
    return normalized


def evaluate_work_area_rules(
    tenant_id: str,
    work_area_name: str,
    *,
    db: Session | None = None,
    records_cache: dict[str, list[dict]] | None = None,
) -> dict:
    work_area = get_work_area_definition(tenant_id, work_area_name)
    if not work_area:
        return {"success": True, "data": {"work_area": work_area_name, "findings": [], "summary": {}}}

    dashboard_type = str(work_area.get("dashboard_type") or "generic").strip().lower()
    normalized_name = str(work_area.get("name") or work_area_name)
    if records_cache is not None and normalized_name in records_cache:
        extracted_records = records_cache[normalized_name]
    else:
        extracted_records = get_extracted_facts_for_work_area(
            tenant_id,
            normalized_name,
            db=db,
        )
        if records_cache is not None:
            records_cache[normalized_name] = extracted_records

    threshold_rules = [_normalize_rule("threshold", rule) for rule in (work_area.get("threshold_rules") or []) if isinstance(rule, dict)]
    risk_rules = [_normalize_rule("risk", rule) for rule in (work_area.get("risk_rules") or []) if isinstance(rule, dict)]
    compiled_enabled_checks = compile_enabled_checks(work_area)
    generated_threshold_rules = [
        _normalize_rule("threshold", rule)
        for rule in compiled_enabled_checks
        if isinstance(rule, dict) and rule.get("rule_type") == "threshold"
    ]
    generated_risk_rules = [
        _normalize_rule("risk", rule)
        for rule in compiled_enabled_checks
        if isinstance(rule, dict) and rule.get("rule_type") == "risk"
    ]
    threshold_rules.extend(generated_threshold_rules)
    risk_rules.extend(generated_risk_rules)
    findings = []

    for rule_type, rules in (("threshold", threshold_rules), ("risk", risk_rules)):
        for rule in rules:
            field = str(rule.get("field") or "").strip()
            operator = str(rule.get("operator") or "").strip()
            expected = rule.get("value")
            compare_field = str(rule.get("compare_field") or "").strip() or None
            label = str(rule.get("label") or rule.get("name") or field or "rule").strip()
            severity = str(rule.get("severity") or ("High" if rule_type == "risk" else "Medium")).strip()

            if not field or not operator:
                continue

            for extracted_record in extracted_records:
                record = extracted_record.get("facts_json") or {}
                actual = record.get(field)
                if operator not in {"missing", "exists"} and actual in (None, ""):
                    continue
                resolved_expected = record.get(compare_field) if compare_field else expected
                if compare_field and resolved_expected in (None, ""):
                    continue
                if not _compare(actual, operator, resolved_expected):
                    continue

                findings.append(
                    {
                        "work_area": work_area.get("name"),
                        "intelligence_pattern": work_area.get("intelligence_pattern"),
                        "dashboard_type": dashboard_type,
                        "rule_type": rule_type,
                        "label": label,
                        "field": field,
                        "operator": operator,
                        "expected": resolved_expected,
                        "actual": actual,
                        "severity": severity,
                        "record_id": extracted_record.get("record_id") or extracted_record.get("document_id") or "unknown",
                        "document_id": extracted_record.get("document_id"),
                        "file_name": extracted_record.get("file_name"),
                        "record": record,
                        "compiled_check": rule.get("generated_from_enabled_check") or label,
                    }
                )

    summary = defaultdict(int)
    for finding in findings:
        summary[finding["severity"]] += 1

    return {
        "success": True,
        "data": {
            "work_area": work_area.get("name"),
            "dashboard_type": dashboard_type,
            "intelligence_pattern": work_area.get("intelligence_pattern"),
            "finding_count": len(findings),
            "findings": findings,
            "summary": dict(summary),
        },
    }


def evaluate_all_work_area_rules(
    tenant_id: str,
    *,
    db: Session | None = None,
) -> dict:
    items = get_work_areas(tenant_id).get("data", [])
    results = []
    all_findings = []
    records_cache: dict[str, list[dict]] = {}
    for item in items:
        result = evaluate_work_area_rules(
            tenant_id,
            item.get("name", ""),
            db=db,
            records_cache=records_cache,
        )
        data = result.get("data", {})
        results.append(data)
        all_findings.extend(data.get("findings", []))

    return {
        "success": True,
        "data": {
            "work_areas": results,
            "findings": all_findings,
            "finding_count": len(all_findings),
        },
    }
