import json
from collections import Counter, defaultdict
import logging
import math
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from time import perf_counter

from openai import OpenAI
from sqlalchemy.orm import Session

from app.connectors.connector_factory import get_connector
from app.core.config import settings
from app.db_models import ConnectorFile, Document, DocumentChunk, Repository
from app.services.work_area_service import get_work_area_definition
from app.services.performance_cache_service import (
    get_cached_response,
    get_repository_cache_revision,
    get_repository_classification_cache,
    set_cached_response,
    update_repository_classification_cache,
)


AI_BATCH_SIZE = 12
AI_SNIPPET_CHARS = 900
AI_REPORT_MODEL = settings.OPENAI_MODEL
AI_CLIENT = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

TYPE_LABELS = {
    "sales_invoice": "Sales Invoice",
    "customer_correspondence": "Customer Correspondence",
    "purchase_order": "Purchase Order",
    "policy_procedure": "Policies & Procedures",
    "compliance_policy": "Compliance Policy",
    "proposal": "Proposal",
    "quote": "Quotation / RFQ",
    "contract": "Contract / Agreement",
    "sales_tracker": "Sales Tracker",
    "procurement_tracker": "Procurement Tracker",
    "vendor_document": "Vendor / Supplier Document",
    "invoice": "Invoice",
    "financial_report": "Financial Report",
    "correspondence": "Correspondence",
    "general_document": "General Document",
    "unknown": "Unknown",
}

STATUS_LABELS = {
    "aligned": "Aligned",
    "needs_review": "Needs Review",
    "unknown": "Unknown",
}
logger = logging.getLogger(__name__)


def _connector_payload(repo: Repository) -> dict:
    return {
        "repository_id": repo.repository_id,
        "tenant_id": repo.tenant_id,
        "repository_name": repo.repository_name,
        "source_type": repo.source_type,
        "source_path": repo.source_path,
        "connection_config": repo.connection_config or {},
    }


def _normalize_text(value: str | None) -> str:
    return str(value or "").strip().lower()


def _split_tokens(*values: str | None) -> str:
    return " ".join(_normalize_text(value) for value in values if value)


def _derive_expected_types(repo: Repository) -> set[str]:
    work_area = get_work_area_definition(repo.tenant_id, repo.business_area) or {}
    guidance = " ".join(
        [
            str(repo.business_area or ""),
            " ".join(work_area.get("tags_keywords") or []),
            " ".join(work_area.get("summary_focus") or []),
            " ".join(work_area.get("entities_to_extract") or []),
            " ".join(work_area.get("enabled_checks") or []),
        ]
    ).lower()

    expected_types = {"general_document"}
    if any(token in guidance for token in ["contract", "agreement", "renewal", "obligation"]):
        expected_types.add("contract")
    if any(token in guidance for token in ["invoice", "payment", "payable", "receivable"]):
        expected_types.add("invoice")
        expected_types.add("financial_report")
    if any(token in guidance for token in ["purchase order", "po", "procurement"]):
        expected_types.add("purchase_order")
        expected_types.add("procurement_tracker")
    if any(token in guidance for token in ["vendor", "supplier", "compliance"]):
        expected_types.add("vendor_document")
        expected_types.add("compliance_policy")
    if any(token in guidance for token in ["proposal", "quotation", "quote", "rfq", "tender"]):
        expected_types.add("proposal")
        expected_types.add("quote")
        expected_types.add("sales_tracker")
    if any(token in guidance for token in ["policy", "procedure", "hr", "leave", "employee"]):
        expected_types.add("policy_procedure")
        expected_types.add("correspondence")
    if any(token in guidance for token in ["email", "mail", "correspondence", "discussion", "follow-up"]):
        expected_types.add("correspondence")

    return expected_types


def _heuristic_document_type(file_name: str, file_path: str | None, preview_text: str | None) -> str:
    combined = _split_tokens(file_name, file_path, preview_text[:1500] if preview_text else "")

    if any(keyword in combined for keyword in ("invoice", "tax invoice", "vat invoice", "order 403")):
        if any(keyword in combined for keyword in ("sales", "customer", "receivable")):
            return "sales_invoice"
        return "invoice"

    if any(keyword in combined for keyword in ("purchase order", "po no", "po_", "po-", "procurement")):
        return "purchase_order"

    if any(keyword in combined for keyword in ("policy", "procedure", "sop", "guideline", "manual")):
        return "policy_procedure"

    if any(keyword in combined for keyword in ("compliance", "audit", "certificate", "regulation")):
        return "compliance_policy"

    if any(keyword in combined for keyword in ("proposal_no", "proposal", "quotation", "quote", "rfq", "tender")):
        if "quote" in combined or "quotation" in combined or "rfq" in combined:
            return "quote"
        if "tracker" in combined:
            return "sales_tracker"
        return "proposal"

    if any(keyword in combined for keyword in ("tracker", "pipeline", "sales owner", "customer", "proposal_date")):
        return "sales_tracker"

    if any(keyword in combined for keyword in ("supplier", "vendor", "delivery_status", "risk_remarks")):
        return "vendor_document"

    if any(keyword in combined for keyword in ("pr_no", "item_name", "material", "request_date", "expected_date")):
        return "procurement_tracker"

    if any(keyword in combined for keyword in ("agreement", "contract", "msa", "nda", "terms and conditions")):
        return "contract"

    if any(keyword in combined for keyword in ("email", "mail", "correspondence", "discussion", "follow-up", "follow up")):
        if any(keyword in combined for keyword in ("customer", "client", "buyer")):
            return "customer_correspondence"
        return "correspondence"

    if any(keyword in combined for keyword in ("statement", "ledger", "balance", "profit", "loss", "revenue")):
        return "financial_report"

    if any(keyword in combined for keyword in ("checklist", "summary", "context", "note", "notes")):
        return "general_document"

    return "unknown"


def _repository_root_label(repo: Repository) -> str:
    root_path = (
        (repo.connection_config or {}).get("root_path")
        or repo.source_path
        or repo.repository_name
    )
    normalized = str(root_path or "").replace("\\", "/").rstrip("/")
    if not normalized:
        return f"{repo.repository_name} (Repository Root)"

    name = normalized.split("/")[-1] or repo.repository_name
    return f"{name} (Repository Root)"


def _normalize_folder_path(path_value: str | None, repo: Repository) -> str:
    raw = (path_value or "").strip()
    if not raw:
        return _repository_root_label(repo)

    normalized = raw.replace("\\", "/").rstrip("/")
    parent = normalized.rsplit("/", 1)[0] if "/" in normalized else ""
    if not parent:
        return _repository_root_label(repo)

    try:
        path_obj = PureWindowsPath(parent) if ":" in parent[:3] else PurePosixPath(parent)
        return str(path_obj).replace("\\", "/")
    except Exception:
        return str(PurePath(parent)).replace("\\", "/")


def _fallback_confidence(inferred_type: str) -> float:
    return 0.45 if inferred_type == "unknown" else 0.72


def _derive_status_and_severity(
    *,
    inferred_type: str,
    expected_types: set[str],
    ai_mismatch: bool | None,
    ai_severity: int | None,
) -> tuple[str, bool, int]:
    if inferred_type == "unknown":
        return "unknown", False, ai_severity if ai_severity is not None else 35

    is_mismatch = ai_mismatch if ai_mismatch is not None else inferred_type not in expected_types

    if is_mismatch:
        return "needs_review", True, ai_severity if ai_severity is not None else 78

    return "aligned", False, ai_severity if ai_severity is not None else 8


def _severity_label(score: int) -> str:
    if score >= 80:
        return "High"
    if score >= 50:
        return "Medium"
    if score > 0:
        return "Low"
    return "None"


def _parse_confidence_value(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)

    normalized = _normalize_text(str(value or ""))
    confidence_map = {
        "low": 0.35,
        "medium": 0.65,
        "med": 0.65,
        "high": 0.9,
    }
    if normalized in confidence_map:
        return confidence_map[normalized]

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_severity_value(value) -> int:
    if isinstance(value, (int, float)):
        return int(float(value))

    normalized = _normalize_text(str(value or ""))
    severity_map = {
        "none": 0,
        "low": 35,
        "medium": 60,
        "med": 60,
        "high": 85,
        "critical": 95,
    }
    if normalized in severity_map:
        return severity_map[normalized]

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _tracked_classification_cache_key(connector_file: ConnectorFile) -> str:
    return "|".join(
        [
            "tracked",
            str(connector_file.id),
            connector_file.file_hash or "",
            str(connector_file.version_number or ""),
            connector_file.source_modified_at.isoformat()
            if connector_file.source_modified_at
            else "",
        ]
    )


def _live_classification_cache_key(source_file: dict) -> str:
    return "|".join(
        [
            "live",
            str(source_file.get("external_file_id") or "").strip(),
            str(source_file.get("file_hash") or "").strip(),
            str(source_file.get("source_modified_at") or "").strip(),
        ]
    )


def _build_ai_batch_payload(items: list[dict]) -> list[dict]:
    payload = []
    for item in items:
        payload.append(
            {
                "id": item["connector_file_id"],
                "file_name": item["file_name"],
                "folder_path": item["folder_path"],
                "preview_text": (item["preview_text"] or "")[:AI_SNIPPET_CHARS],
                "heuristic_type": item["heuristic_type"],
            }
        )
    return payload


def _classify_with_ai(
    repo: Repository,
    items: list[dict],
    expected_types: set[str],
) -> tuple[dict[str, dict], dict]:
    if not items:
        return {}, {
            "mode": "heuristic",
            "display_label": "Rule-based fallback",
            "fallback_reason": "No files were available for AI classification.",
            "error_id": "content_report_no_items",
            "error_message": None,
            "batches_attempted": 0,
            "batches_failed": 0,
        }

    if not AI_CLIENT:
        return {}, {
            "mode": "heuristic",
            "display_label": "Rule-based fallback",
            "fallback_reason": "AI classification is unavailable because the OpenAI client is not configured for the backend.",
            "error_id": "content_report_ai_client_unavailable",
            "error_message": "OPENAI_API_KEY is missing or the AI client could not be initialized.",
            "batches_attempted": 0,
            "batches_failed": 0,
        }

    allowed_types = sorted(TYPE_LABELS.keys())
    results: dict[str, dict] = {}
    diagnostics = {
        "mode": "ai",
        "display_label": "AI-assisted",
        "fallback_reason": None,
        "error_id": None,
        "error_message": None,
        "batches_attempted": 0,
        "batches_failed": 0,
    }

    for start in range(0, len(items), AI_BATCH_SIZE):
        batch = items[start : start + AI_BATCH_SIZE]
        batch_payload = _build_ai_batch_payload(batch)
        batch_number = start // AI_BATCH_SIZE + 1
        diagnostics["batches_attempted"] += 1

        prompt = {
            "repository_name": repo.repository_name,
            "repository_business_area": repo.business_area,
            "expected_types": sorted(expected_types),
            "allowed_types": allowed_types,
            "documents": batch_payload,
            "instructions": {
                "goal": "Classify each document for an enterprise repository content report.",
                "mismatch_rule": "If the document type looks unrelated to the repository business area, set mismatch=true and assign a severity score from 0 to 100.",
                "unknown_rule": "If evidence is insufficient, set inferred_type to unknown, confidence low, mismatch false, and severity around 20-40.",
                "output": "Return JSON only with key documents. Each item must include id, inferred_type, confidence, mismatch, mismatch_severity, rationale.",
            },
        }

        try:
            response = AI_CLIENT.chat.completions.create(
                model=AI_REPORT_MODEL,
                response_format={"type": "json_object"},
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You classify enterprise repository files into a fixed taxonomy. "
                            "Return strict JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(prompt, ensure_ascii=True),
                    },
                ],
            )
            content = response.choices[0].message.content or "{}"
            payload = json.loads(content)
            for row in payload.get("documents", []):
                doc_id = str(row.get("id") or "").strip()
                inferred_type = str(row.get("inferred_type") or "unknown").strip()
                if not doc_id or inferred_type not in TYPE_LABELS:
                    continue
                results[doc_id] = {
                    "inferred_type": inferred_type,
                    "confidence": _parse_confidence_value(row.get("confidence")),
                    "mismatch": bool(row.get("mismatch", False)),
                    "mismatch_severity": _parse_severity_value(row.get("mismatch_severity")),
                    "rationale": str(row.get("rationale") or "").strip(),
                    "classification_mode": "ai",
                }
        except Exception as exc:
            diagnostics["batches_failed"] += 1
            if diagnostics["error_id"] is None:
                diagnostics["error_id"] = f"content_report_ai_batch_{batch_number}_{exc.__class__.__name__}"
                diagnostics["error_message"] = str(exc)
                diagnostics["fallback_reason"] = (
                    "AI classification could not complete for one or more batches, "
                    "so the report fell back to rule-based classification."
                )
            continue

    if results and diagnostics["batches_failed"] > 0:
        diagnostics["mode"] = "ai_with_fallback"
        diagnostics["display_label"] = "AI-assisted with fallback"
    elif not results:
        diagnostics["mode"] = "heuristic"
        diagnostics["display_label"] = "Rule-based fallback"
        if diagnostics["fallback_reason"] is None:
            diagnostics["fallback_reason"] = (
                "AI classification returned no usable classifications, so the report used rule-based inference instead."
            )
            diagnostics["error_id"] = "content_report_ai_no_results"

    return results, diagnostics


def _discover_live_source_files(repo: Repository) -> tuple[dict[str, dict], dict | None]:
    try:
        connector = get_connector(_connector_payload(repo))
        source_files = connector.list_files()
        return {
            str(item.get("external_file_id") or ""): item
            for item in source_files
            if str(item.get("external_file_id") or "").strip()
        }, None
    except Exception as exc:
        return {}, {
            "mode": "connector_scan_unavailable",
            "error_id": f"content_report_source_scan_{exc.__class__.__name__}",
            "error_message": str(exc),
        }


def _build_repository_content_report_payload(
    db: Session,
    tenant_id: str,
    repository_id: str,
) -> dict:
    repo = (
        db.query(Repository)
        .filter(
            Repository.tenant_id == tenant_id,
            Repository.repository_id == repository_id,
        )
        .first()
    )
    if not repo:
        raise ValueError("Repository not found")

    connector_files = (
        db.query(ConnectorFile)
        .filter(
            ConnectorFile.tenant_id == tenant_id,
            ConnectorFile.repository_id == repository_id,
            ConnectorFile.is_current_version == True,
        )
        .order_by(ConnectorFile.file_path.asc().nullslast(), ConnectorFile.file_name.asc())
        .all()
    )

    doc_ids = [file.document_id for file in connector_files if file.document_id]
    documents = (
        db.query(Document)
        .filter(
            Document.tenant_id == tenant_id,
            Document.document_id.in_(doc_ids) if doc_ids else False,
        )
        .all()
        if doc_ids
        else []
    )
    documents_by_id = {document.document_id: document for document in documents}

    first_chunks: dict[str, DocumentChunk] = {}
    if doc_ids:
        chunk_rows = (
            db.query(DocumentChunk)
            .filter(
                DocumentChunk.tenant_id == tenant_id,
                DocumentChunk.document_id.in_(doc_ids),
                DocumentChunk.is_deleted == False,
            )
            .order_by(DocumentChunk.document_id.asc(), DocumentChunk.chunk_index.asc())
            .all()
        )
        for chunk in chunk_rows:
            if chunk.document_id not in first_chunks:
                first_chunks[chunk.document_id] = chunk

    expected_types = _derive_expected_types(repo)

    tracked_external_ids = {
        str(connector_file.external_file_id or "").strip()
        for connector_file in connector_files
        if str(connector_file.external_file_id or "").strip()
    }

    live_source_files, source_scan_error = _discover_live_source_files(repo)

    classification_cache = get_repository_classification_cache(repository_id)
    classification_updates: dict[str, dict] = {}
    valid_classification_keys: set[str] = set()
    ai_candidates: list[dict] = []
    tracked_file_cache_keys: dict[str, str] = {}
    for connector_file in connector_files:
        document = documents_by_id.get(connector_file.document_id) if connector_file.document_id else None
        first_chunk = first_chunks.get(document.document_id) if document else None
        preview_text = first_chunk.chunk_text if first_chunk else ""
        folder_path = _normalize_folder_path(connector_file.file_path, repo)
        cache_key = _tracked_classification_cache_key(connector_file)
        valid_classification_keys.add(cache_key)
        tracked_file_cache_keys[str(connector_file.id)] = cache_key
        cached_classification = classification_cache.get(cache_key)
        if cached_classification:
            continue

        ai_candidates.append(
            {
                "connector_file_id": str(connector_file.id),
                "file_name": connector_file.file_name,
                "folder_path": folder_path,
                "preview_text": preview_text,
                "heuristic_type": _heuristic_document_type(
                    connector_file.file_name,
                    connector_file.file_path,
                    preview_text,
                ),
            }
        )

    live_only_source_files = [
        source_file
        for external_id, source_file in live_source_files.items()
        if external_id not in tracked_external_ids
    ]

    live_file_cache_keys: dict[str, str] = {}
    for source_file in live_only_source_files:
        folder_path = _normalize_folder_path(source_file.get("file_path"), repo)
        cache_key = _live_classification_cache_key(source_file)
        live_identifier = f"live::{source_file['external_file_id']}"
        valid_classification_keys.add(cache_key)
        live_file_cache_keys[live_identifier] = cache_key
        cached_classification = classification_cache.get(cache_key)
        if cached_classification:
            continue

        ai_candidates.append(
            {
                "connector_file_id": live_identifier,
                "file_name": source_file.get("file_name") or source_file["external_file_id"],
                "folder_path": folder_path,
                "preview_text": "",
                "heuristic_type": _heuristic_document_type(
                    source_file.get("file_name"),
                    source_file.get("file_path"),
                    "",
                ),
            }
        )

    ai_results, classification_details = _classify_with_ai(repo, ai_candidates, expected_types)
    merged_ai_results: dict[str, dict] = {}

    ai_candidates_by_id = {
        candidate["connector_file_id"]: candidate for candidate in ai_candidates
    }

    for candidate_id, candidate in ai_candidates_by_id.items():
        if candidate_id in ai_results:
            continue
        ai_results[candidate_id] = {
            "inferred_type": candidate["heuristic_type"],
            "confidence": _fallback_confidence(candidate["heuristic_type"]),
            "mismatch": None,
            "mismatch_severity": None,
            "rationale": "",
            "classification_mode": "heuristic",
        }

    for connector_file in connector_files:
        file_id = str(connector_file.id)
        cache_key = tracked_file_cache_keys[file_id]
        cached_classification = classification_cache.get(cache_key)
        if cached_classification:
            merged_ai_results[file_id] = cached_classification
        elif file_id in ai_results:
            merged_ai_results[file_id] = ai_results[file_id]
            classification_updates[cache_key] = ai_results[file_id]

    for source_file in live_only_source_files:
        live_identifier = f"live::{source_file['external_file_id']}"
        cache_key = live_file_cache_keys[live_identifier]
        cached_classification = classification_cache.get(cache_key)
        if cached_classification:
            merged_ai_results[live_identifier] = cached_classification
        elif live_identifier in ai_results:
            merged_ai_results[live_identifier] = ai_results[live_identifier]
            classification_updates[cache_key] = ai_results[live_identifier]

    if classification_updates or valid_classification_keys:
        update_repository_classification_cache(
            repository_id,
            classification_updates,
            valid_keys=valid_classification_keys,
        )

    folder_groups: dict[str, list[dict]] = defaultdict(list)
    summary_type_counter = Counter()
    summary_status_counter = Counter()
    mismatch_count = 0

    for connector_file in connector_files:
        document = documents_by_id.get(connector_file.document_id) if connector_file.document_id else None
        first_chunk = first_chunks.get(document.document_id) if document else None
        preview_text = first_chunk.chunk_text if first_chunk else ""
        folder_path = _normalize_folder_path(connector_file.file_path, repo)
        metadata = (document.metadata_json if document else None) or connector_file.metadata_json or {}

        ai_result = merged_ai_results.get(str(connector_file.id), {})
        inferred_type = ai_result.get(
            "inferred_type",
            _heuristic_document_type(connector_file.file_name, connector_file.file_path, preview_text),
        )
        confidence = float(ai_result.get("confidence") or _fallback_confidence(inferred_type))

        status, is_mismatch, severity_score = _derive_status_and_severity(
            inferred_type=inferred_type,
            expected_types=expected_types,
            ai_mismatch=ai_result.get("mismatch"),
            ai_severity=ai_result.get("mismatch_severity"),
        )
        if is_mismatch:
            mismatch_count += 1

        reason = ai_result.get("rationale")
        if not reason and status == "needs_review":
            reason = (
                f"AI classification suggests {TYPE_LABELS.get(inferred_type, TYPE_LABELS['unknown'])} "
                f"does not fit the {repo.business_area} repository."
            )
        elif not reason and status == "unknown":
            reason = "AI could not determine a confident document type from the available evidence."

        item = {
            "connector_file_id": str(connector_file.id),
            "file_name": connector_file.file_name,
            "file_path": connector_file.file_path,
            "folder_path": folder_path,
            "document_id": document.document_id if document else None,
            "repository_id": connector_file.repository_id,
            "sync_status": connector_file.sync_status,
            "tracking_state": "tracked",
            "tracked_only": document is None,
            "inferred_type": inferred_type,
            "inferred_type_label": TYPE_LABELS.get(inferred_type, TYPE_LABELS["unknown"]),
            "status": status,
            "status_label": STATUS_LABELS[status],
            "is_mismatch": is_mismatch,
            "severity_score": severity_score,
            "severity_label": _severity_label(severity_score),
            "confidence": round(confidence, 2),
            "reason": reason,
            "classification_mode": ai_result.get("classification_mode", "heuristic"),
            "open_target": {
                "repository_id": connector_file.repository_id,
                "connector_file_id": str(connector_file.id),
            },
            "metadata": {
                "file_hash": connector_file.file_hash,
                "parser": metadata.get("parser"),
                "ocr_used": metadata.get("ocr_used", False),
                "text_status": metadata.get("text_status"),
                "chunk_count": metadata.get("chunk_count", 0),
            },
        }

        folder_groups[folder_path].append(item)
        summary_type_counter[inferred_type] += 1
        summary_status_counter[status] += 1

    for source_file in live_only_source_files:
        external_file_id = str(source_file.get("external_file_id") or "").strip()
        folder_path = _normalize_folder_path(source_file.get("file_path"), repo)
        ai_result = merged_ai_results.get(f"live::{external_file_id}", {})
        inferred_type = ai_result.get(
            "inferred_type",
            _heuristic_document_type(
                source_file.get("file_name"),
                source_file.get("file_path"),
                "",
            ),
        )
        confidence = float(ai_result.get("confidence") or _fallback_confidence(inferred_type))

        status, is_mismatch, severity_score = _derive_status_and_severity(
            inferred_type=inferred_type,
            expected_types=expected_types,
            ai_mismatch=ai_result.get("mismatch"),
            ai_severity=ai_result.get("mismatch_severity"),
        )
        if is_mismatch:
            mismatch_count += 1

        reason = ai_result.get("rationale")
        if not reason:
            reason = (
                "This file exists in the mounted source folder but has not been tracked by repository sync yet. "
                "Run Sync or Reindex to ingest and index it."
            )

        item = {
            "connector_file_id": f"live::{external_file_id}",
            "file_name": source_file.get("file_name") or external_file_id,
            "file_path": source_file.get("file_path"),
            "folder_path": folder_path,
            "document_id": None,
            "repository_id": repo.repository_id,
            "sync_status": "not_tracked",
            "tracking_state": "discovered_not_tracked",
            "tracked_only": False,
            "inferred_type": inferred_type,
            "inferred_type_label": TYPE_LABELS.get(inferred_type, TYPE_LABELS["unknown"]),
            "status": status,
            "status_label": STATUS_LABELS[status],
            "is_mismatch": is_mismatch,
            "severity_score": severity_score,
            "severity_label": _severity_label(severity_score),
            "confidence": round(confidence, 2),
            "reason": reason,
            "classification_mode": ai_result.get("classification_mode", "heuristic"),
            "open_target": None,
            "metadata": {
                "file_hash": source_file.get("file_hash"),
                "parser": None,
                "ocr_used": False,
                "text_status": "not_tracked",
                "chunk_count": 0,
                "file_size": source_file.get("file_size"),
            },
        }

        folder_groups[folder_path].append(item)
        summary_type_counter[inferred_type] += 1
        summary_status_counter[status] += 1

    folder_summaries = []
    for folder_path, items in sorted(folder_groups.items(), key=lambda entry: entry[0].lower()):
        type_counter = Counter(item["inferred_type"] for item in items)
        mismatch_items = [item for item in items if item["status"] == "needs_review"]
        dominant_type, dominant_count = (
            type_counter.most_common(1)[0] if type_counter else ("unknown", 0)
        )

        folder_summaries.append(
            {
                "folder_path": folder_path,
                "folder_name": Path(folder_path.replace("\\", "/")).name or folder_path,
                "file_count": len(items),
                "dominant_type": dominant_type,
                "dominant_type_label": TYPE_LABELS.get(dominant_type, TYPE_LABELS["unknown"]),
                "dominant_type_count": dominant_count,
                "mismatch_count": len(mismatch_items),
                "alignment_status": "mixed" if mismatch_items else "aligned",
                "types_found": [
                    {
                        "type": type_name,
                        "label": TYPE_LABELS.get(type_name, TYPE_LABELS["unknown"]),
                        "count": count,
                    }
                    for type_name, count in type_counter.most_common()
                ],
                "items": sorted(
                    items,
                    key=lambda item: (
                        item["status"] != "needs_review",
                        item["status"] != "unknown",
                        item["file_name"].lower(),
                    ),
                ),
            }
        )

    return {
        "repository_id": repo.repository_id,
        "repository_name": repo.repository_name,
        "business_area": repo.business_area,
        "source_type": repo.source_type,
        "root_folder_label": _repository_root_label(repo),
        "expected_types": [
            {"type": item, "label": TYPE_LABELS.get(item, TYPE_LABELS["unknown"])}
            for item in sorted(expected_types)
        ],
        "status_options": [
            {"value": "all", "label": "All"},
            {"value": "needs_review", "label": STATUS_LABELS["needs_review"]},
            {"value": "aligned", "label": STATUS_LABELS["aligned"]},
            {"value": "unknown", "label": STATUS_LABELS["unknown"]},
        ],
        "summary": {
            "total_files": len(connector_files) + len(live_only_source_files),
            "tracked_files": len(connector_files),
            "live_untracked_files": len(live_only_source_files),
            "folder_count": len(folder_summaries),
            "mismatch_files": mismatch_count,
            "aligned_files": summary_status_counter["aligned"],
            "unknown_files": summary_status_counter["unknown"],
            "type_distribution": [
                {
                    "type": type_name,
                    "label": TYPE_LABELS.get(type_name, TYPE_LABELS["unknown"]),
                    "count": count,
                }
                for type_name, count in summary_type_counter.most_common()
            ],
            "status_distribution": [
                {
                    "status": status_name,
                    "label": STATUS_LABELS[status_name],
                    "count": count,
                }
                for status_name, count in summary_status_counter.items()
            ],
            "classification_mode": (
                "ai"
                if classification_details.get("mode") in {"ai", "ai_with_fallback"}
                else "heuristic"
            ),
            "classification_details": classification_details,
            "source_scan": {
                "discovered_files": len(live_source_files),
                "tracked_files": len(connector_files),
                "live_untracked_files": len(live_only_source_files),
                "error": source_scan_error,
            },
        },
        "folders": folder_summaries,
    }


def build_repository_content_report(
    db: Session,
    tenant_id: str,
    repository_id: str,
    *,
    force_refresh: bool = False,
) -> dict:
    started_at = perf_counter()
    revision = get_repository_cache_revision(db, tenant_id, repository_id)
    cache_key = f"repository_content_report::{tenant_id}::{repository_id}"

    if not force_refresh:
        cached_payload = get_cached_response(cache_key, revision=revision)
        if cached_payload is not None:
            logger.info(
                "repository_content_report cache_hit tenant=%s repository=%s duration_ms=%.2f",
                tenant_id,
                repository_id,
                (perf_counter() - started_at) * 1000,
            )
            return cached_payload

    payload = _build_repository_content_report_payload(db, tenant_id, repository_id)
    set_cached_response(
        cache_key,
        payload,
        revision=revision,
        metadata={
            "tenant_id": tenant_id,
            "repository_id": repository_id,
            "entity": "repository_content_report",
        },
    )
    logger.info(
        "repository_content_report cache_miss tenant=%s repository=%s files=%s folders=%s duration_ms=%.2f",
        tenant_id,
        repository_id,
        payload.get("summary", {}).get("total_files", 0),
        payload.get("summary", {}).get("folder_count", 0),
        (perf_counter() - started_at) * 1000,
    )
    return payload


def paginate_repository_content_report(
    report: dict,
    *,
    status_filter: str = "all",
    page: int = 1,
    page_size: int = 4,
) -> dict:
    status_filter = (status_filter or "all").strip().lower()
    page = max(page, 1)
    page_size = max(page_size, 1)

    folders = report.get("folders", [])

    if status_filter == "all":
        filtered_folders = folders
    else:
        filtered_folders = []
        for folder in folders:
            filtered_items = [
                item for item in folder.get("items", [])
                if item.get("status") == status_filter
            ]
            if not filtered_items:
                continue
            filtered_folder = dict(folder)
            filtered_folder["items"] = filtered_items
            filtered_folder["file_count"] = len(filtered_items)
            filtered_folder["mismatch_count"] = len(
                [item for item in filtered_items if item.get("status") == "needs_review"]
            )
            filtered_folders.append(filtered_folder)

    total_folders = len(filtered_folders)
    total_pages = max(math.ceil(total_folders / page_size), 1)
    page = min(page, total_pages)
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    paged_folders = filtered_folders[start_index:end_index]

    filtered_items = [
        item
        for folder in filtered_folders
        for item in folder.get("items", [])
    ]

    report_payload = dict(report)
    report_payload["folders"] = paged_folders
    report_payload["pagination"] = {
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "total_folders": total_folders,
        "has_previous": page > 1,
        "has_next": page < total_pages,
    }
    report_payload["applied_filters"] = {
        "status": status_filter,
    }
    report_payload["filtered_summary"] = {
        "total_files": len(filtered_items),
        "folder_count": total_folders,
        "mismatch_files": len(
            [item for item in filtered_items if item.get("status") == "needs_review"]
        ),
        "aligned_files": len(
            [item for item in filtered_items if item.get("status") == "aligned"]
        ),
        "unknown_files": len(
            [item for item in filtered_items if item.get("status") == "unknown"]
        ),
    }
    return report_payload
