import json

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.extracted_fact_service import _FIELD_ALIASES, get_extracted_facts_for_work_area
from app.services.subscription_service import add_ai_token_usage, validate_usage_limit
from app.services.token_usage_service import estimate_ai_usage_tokens
from app.services.work_area_rule_engine_service import evaluate_all_work_area_rules, evaluate_work_area_rules
from app.services.work_area_service import get_work_areas


SUMMARY_CLIENT = OpenAI(api_key=settings.OPENAI_API_KEY)


def _canonical_specific(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split()).replace(" ", "_")


def _normalize_tokens(value: str) -> list[str]:
    tokens = []
    for token in _canonical_specific(value).split("_"):
        if not token:
            continue
        if len(token) > 3 and token.endswith("ies"):
            tokens.append(token[:-3] + "y")
        elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            tokens.append(token[:-1])
        else:
            tokens.append(token)
    return tokens


def _token_overlap_score(required_specific: str, candidate: str) -> float:
    required_tokens = set(_normalize_tokens(required_specific))
    candidate_tokens = set(_normalize_tokens(candidate))
    if not required_tokens or not candidate_tokens:
        return 0.0
    return len(required_tokens & candidate_tokens) / len(required_tokens)


def _build_available_fact_keys(extracted_facts: list[dict]) -> set[str]:
    keys = set()
    for fact in extracted_facts:
        keys.update((fact.get("facts_json") or {}).keys())
    return keys


def _clean_value(value):
    return None if value in (None, "", [], {}) else value


def _build_fact_highlights(extracted_facts: list[dict]) -> list[dict]:
    highlights = []
    seen = set()
    for fact in extracted_facts:
        facts = fact.get("facts_json") or {}
        highlight = {
            "record_id": facts.get("record_id") or fact.get("record_id"),
            "file_name": facts.get("file_name") or fact.get("file_name"),
            "status": _clean_value(facts.get("status")),
            "document_date": _clean_value(facts.get("document_date")),
            "expiry_date": _clean_value(facts.get("expiry_date")),
            "start_date": _clean_value(facts.get("start_date")),
            "aging_days": _clean_value(facts.get("aging_days")),
            "expiry_days": _clean_value(facts.get("expiry_days")),
            "contract_no": _clean_value(facts.get("contract_no")),
            "po_no": _clean_value(facts.get("po_no")),
            "invoice_no": _clean_value(facts.get("invoice_no")),
            "counterparty": _clean_value(facts.get("counterparty")),
            "vendor_name": _clean_value(facts.get("vendor_name")),
            "remaining_value": _clean_value(facts.get("remaining_value")),
            "contract_value": _clean_value(facts.get("contract_value")),
            "invoice_value": _clean_value(facts.get("invoice_value")),
            "po_value": _clean_value(facts.get("po_value")),
            "utilization_percent": _clean_value(facts.get("utilization_percent")),
            "quantity_mismatch": _clean_value(facts.get("quantity_mismatch")),
            "missing_grn_flag": _clean_value(facts.get("missing_grn_flag")),
            "renewal_pending_flag": _clean_value(facts.get("renewal_pending_flag")),
        }
        key = (
            highlight["record_id"],
            highlight["contract_no"],
            highlight["po_no"],
            highlight["invoice_no"],
            highlight["expiry_date"],
            highlight["document_date"],
        )
        if key in seen:
            continue
        seen.add(key)
        highlights.append({k: v for k, v in highlight.items() if v is not None})
        if len(highlights) >= 15:
            break
    return highlights


def _build_due_date_candidates(extracted_facts: list[dict]) -> list[dict]:
    candidates = []
    seen = set()
    for fact in extracted_facts:
        facts = fact.get("facts_json") or {}
        record_ref = facts.get("contract_no") or facts.get("po_no") or facts.get("invoice_no") or facts.get("record_id") or fact.get("record_id")
        for label, field_name in [
            ("expiry date", "expiry_date"),
            ("document date", "document_date"),
            ("start date", "start_date"),
        ]:
            value = _clean_value(facts.get(field_name))
            if not value:
                continue
            key = (record_ref, field_name, value)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "record_ref": record_ref,
                    "field": field_name,
                    "label": label,
                    "date": value,
                    "file_name": facts.get("file_name") or fact.get("file_name"),
                }
            )
            if len(candidates) >= 20:
                return candidates
    return candidates


def _resolve_specific_fields(required_specific: str, available_fact_keys: set[str]) -> list[str]:
    if not available_fact_keys:
        return []

    scored_fields: dict[str, float] = {}
    normalized_specific = " ".join(str(required_specific or "").strip().lower().split())
    canonical_specific = _canonical_specific(required_specific)

    for field_name in available_fact_keys:
        score = 0.0
        if field_name == canonical_specific:
            score = 1.0
        else:
            score = max(score, _token_overlap_score(normalized_specific, field_name))
            for alias, aliased_field in _FIELD_ALIASES.items():
                if aliased_field != field_name:
                    continue
                score = max(score, _token_overlap_score(normalized_specific, alias))
        if score > 0:
            scored_fields[field_name] = score

    if not scored_fields:
        return []

    best_score = max(scored_fields.values())
    if best_score < 0.5:
        return []

    return sorted(field_name for field_name, score in scored_fields.items() if score == best_score)


def _collect_specific_values(
    extracted_facts: list[dict],
    required_specifics: list[str],
    available_fact_keys: set[str],
) -> tuple[dict[str, list], list[str]]:
    values = {}
    unresolved = []
    for item in required_specifics:
        candidate_fields = _resolve_specific_fields(item, available_fact_keys)
        if not candidate_fields:
            unresolved.append(item)
            values[item] = []
            continue
        collected = []
        seen = set()
        for fact in extracted_facts:
            fact_values = fact.get("facts_json") or {}
            for field_name in candidate_fields:
                field_value = fact_values.get(field_name)
                if field_value in (None, "", [], {}):
                    continue
                serialized = json.dumps(field_value, sort_keys=True, default=str)
                if serialized in seen:
                    continue
                seen.add(serialized)
                collected.append(field_value)
                break
            if len(collected) >= 5:
                break
        values[item] = collected
    return values, unresolved


def build_work_area_summary_payload(current_user: dict, db: Session) -> list[dict]:
    work_areas = get_work_areas(current_user["tenant_id"]).get("data") or []
    payload = []

    for item in work_areas:
        area_name = str(item.get("name") or "").strip()
        if not area_name:
            continue

        extracted_facts = get_extracted_facts_for_work_area(
            current_user["tenant_id"],
            area_name,
            db=db,
        )
        rule_payload = evaluate_work_area_rules(
            current_user["tenant_id"],
            area_name,
            db=db,
        ).get("data", {})
        required_specifics = item.get("required_specifics") or []
        rule_finding_count = rule_payload.get("finding_count") or 0
        available_fact_keys = _build_available_fact_keys(extracted_facts)
        specific_values, unresolved_required_specifics = _collect_specific_values(
            extracted_facts,
            required_specifics,
            available_fact_keys,
        )
        payload.append(
            {
                "work_area": area_name,
                "description": item.get("description") or "",
                "intelligence_pattern": item.get("intelligence_pattern") or "",
                "dashboard_type": item.get("dashboard_type") or "generic",
                "summary_focus": item.get("summary_focus") or [],
                "required_specifics": required_specifics,
                "entities_to_extract": item.get("entities_to_extract") or [],
                "enabled_checks": item.get("enabled_checks") or [],
                "threshold_rules": item.get("threshold_rules") or [],
                "risk_rules": item.get("risk_rules") or [],
                "summary_template": item.get("summary_template") or "",
                "facts_count": len(extracted_facts),
                "available_fact_keys": sorted(available_fact_keys),
                "specific_values": specific_values,
                "unresolved_required_specifics": unresolved_required_specifics,
                "fact_highlights": _build_fact_highlights(extracted_facts),
                "due_date_candidates": _build_due_date_candidates(extracted_facts),
                "fact_samples": [
                    {
                        "record_id": fact.get("record_id"),
                        "file_name": fact.get("file_name"),
                        "facts": fact.get("facts_json") or {},
                    }
                    for fact in extracted_facts[:12]
                ],
                "rule_finding_count": rule_finding_count,
                "rule_findings": [
                    {
                        "label": finding.get("label"),
                        "severity": finding.get("severity"),
                        "record_id": finding.get("record_id"),
                        "file_name": finding.get("file_name"),
                        "field": finding.get("field"),
                        "operator": finding.get("operator"),
                        "expected": finding.get("expected"),
                        "actual": finding.get("actual"),
                    }
                    for finding in (rule_payload.get("findings") or [])[:40]
                ],
            }
        )

    return payload


def _build_summary_prompt(work_area_payload: list[dict]) -> str:
    return f"""
Generate an executive DSS summary strictly from the supplied structured business-area payload.

Return JSON only with this schema:
{{
  "management_actions": ["..."],
  "work_areas": [
    {{
      "work_area": "name",
      "executive_summary": "short summary",
      "key_findings": ["..."],
      "risks": ["..."],
      "opportunities": ["..."],
      "due_dates": ["..."],
      "recommended_actions": ["..."],
      "priority_level": "None|Low|Medium|High|Critical",
      "specifics_covered": ["required specific name"],
      "specifics_missing": ["required specific name"],
      "template_applied": true
    }}
  ]
}}

Rules:
1. Use only the supplied structured data.
2. Prioritize rule_findings, fact_samples, specific_values, and available_fact_keys as evidence.
3. Prioritize fact_highlights and due_date_candidates when naming concrete records and dates.
4. If a work area has rule findings or facts, generate a concrete summary from the available evidence even when some required specifics are unresolved.
5. Every work area with evidence must mention concrete record references such as contract numbers, PO numbers, invoice numbers, or record IDs.
6. Every due_dates item must include both the record reference and what the date represents, for example 'CTR-2026-0101-1001 expiry date 2026-06-04'.
7. Use counts when possible. Avoid vague phrases like 'multiple' or 'several' unless followed by evidence-backed examples.
8. For procurement areas, explicitly mention missing GRN flags, approval delays, quantity mismatches, and aged items when those signals exist in the evidence.
9. Only say there are no concrete matches when both facts_count and rule_finding_count are zero.
10. Mention exact entities, dates, values, statuses, thresholds, and record IDs when they exist.
11. Treat required_specifics as guidance. Put evidenced items in specifics_covered and unresolved or unavailable items in specifics_missing.
12. Treat summary_template as guidance for narrative focus when it can be supported by the evidence.
13. Do not invent facts, project names, vendors, contracts, numbers, due dates, or actions.

Structured Work-Area Payload:
{json.dumps(work_area_payload, ensure_ascii=True, default=str)}
"""


def _validate_summary_contract(summary_payload: dict, work_area_payload: list[dict]) -> list[dict]:
    payload_by_name = {
        str(item.get("work_area") or "").strip().lower(): item
        for item in work_area_payload
    }
    validations = []

    for area_output in summary_payload.get("work_areas", []) or []:
        area_name = str(area_output.get("work_area") or "").strip().lower()
        source_definition = payload_by_name.get(area_name)
        if not source_definition:
            continue

        required_specifics = source_definition.get("required_specifics") or []
        available_specifics = {
            key: values
            for key, values in (source_definition.get("specific_values") or {}).items()
            if values
        }
        covered_specifics = {
            " ".join(str(item or "").strip().lower().split())
            for item in (area_output.get("specifics_covered") or [])
        }
        missing_specifics = [
            item
            for item in required_specifics
            if " ".join(str(item or "").strip().lower().split()) not in covered_specifics
            and item in available_specifics
        ]

        validations.append(
            {
                "work_area": area_name,
                "template_required": bool(source_definition.get("summary_template")),
                "template_applied": bool(area_output.get("template_applied")),
                "missing_required_specifics": missing_specifics,
                "available_specifics": available_specifics,
            }
        )

    return validations


def _render_summary_markdown(summary_payload: dict, validations: list[dict]) -> str:
    lines = []

    management_actions = summary_payload.get("management_actions") or []
    if management_actions:
        lines.append("Management Actions")
        for action in management_actions:
            lines.append(f"- {action}")
        lines.append("")

    validation_by_area = {
        str(item.get("work_area") or "").strip().lower(): item
        for item in validations
    }

    for area_output in summary_payload.get("work_areas", []) or []:
        area_name = str(area_output.get("work_area") or "").strip()
        if not area_name:
            continue
        lines.append(area_name.title())
        lines.append(f"Summary: {area_output.get('executive_summary') or 'No summary available.'}")

        for heading, key in [
            ("Key Findings", "key_findings"),
            ("Risks", "risks"),
            ("Opportunities", "opportunities"),
            ("Due Dates", "due_dates"),
            ("Recommended Actions", "recommended_actions"),
        ]:
            values = area_output.get(key) or []
            lines.append(f"{heading}:")
            if values:
                for value in values:
                    lines.append(f"- {value}")
            else:
                lines.append("- No concrete items identified.")

        lines.append(f"Priority Level: {area_output.get('priority_level') or 'None'}")

        validation = validation_by_area.get(area_name.lower())
        if validation:
            missing = validation.get("missing_required_specifics") or []
            if missing:
                lines.append(
                    "Validation Note: Missing required specifics in generated narrative for "
                    + ", ".join(missing)
                    + "."
                )
            elif validation.get("available_specifics") and not area_output.get("specifics_missing"):
                lines.append("Validation Note: Required specifics were covered from available structured facts.")
            if validation.get("template_required") and not validation.get("template_applied"):
                lines.append("Validation Note: Summary template was required but not fully applied.")
        lines.append("")

    return "\n".join(lines).strip()


def generate_executive_summary(current_user: dict, db: Session):
    validate_usage_limit(current_user["tenant_id"], "ai_tokens", db)

    work_area_payload = build_work_area_summary_payload(current_user, db)
    findings_payload = evaluate_all_work_area_rules(current_user["tenant_id"], db=db).get("data", {})
    if not any(item.get("facts_count") or item.get("rule_finding_count") for item in work_area_payload):
        return {
            "summary": (
                "No indexed business intelligence facts are available yet. Add repositories, "
                "run sync, and confirm documents are indexed so business-area patterns can extract facts and evaluate rules."
            ),
            "status": {
                "mode": "no_facts",
                "work_area_count": len(work_area_payload),
                "finding_count": findings_payload.get("finding_count", 0),
            },
            "structured_summary": {"work_areas": [], "management_actions": []},
            "validations": [],
        }

    prompt = _build_summary_prompt(work_area_payload)
    response = SUMMARY_CLIENT.chat.completions.create(
        model=settings.OPENAI_MODEL,
        response_format={"type": "json_object"},
        temperature=0.1,
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate executive summaries from structured business intelligence facts. "
                    "Return strict JSON only and do not invent information."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    content = response.choices[0].message.content or "{}"
    structured_summary = json.loads(content)
    validations = _validate_summary_contract(structured_summary, work_area_payload)
    summary_markdown = _render_summary_markdown(structured_summary, validations)
    actual_tokens = getattr(response.usage, "total_tokens", None)
    tokens_used = actual_tokens or estimate_ai_usage_tokens(
        question="executive summary",
        context=prompt,
        answer=summary_markdown,
    )
    add_ai_token_usage(current_user["tenant_id"], tokens_used, db)

    return {
        "summary": summary_markdown,
        "structured_summary": structured_summary,
        "validations": validations,
        "status": {
            "mode": "structured_fact_summary",
            "work_area_count": len(work_area_payload),
            "finding_count": findings_payload.get("finding_count", 0),
            "validation_warnings": sum(
                1
                for item in validations
                if item.get("missing_required_specifics")
                or (item.get("template_required") and not item.get("template_applied"))
            ),
        },
        "usage": {
            "tokens_used": tokens_used,
        },
    }
