from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.services.symployee_records_service import (
    _normalize_hold_category,
    evaluate_record_lifecycle_rule,
    reprocess_repository_record_declarations,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _run_id() -> str:
    return f"PHASE14-{str(uuid4())[:8].upper()}"


def _chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[idx : idx + size] for idx in range(0, len(values), size)]


def _scope_join(repository_id: str | None) -> str:
    if not repository_id:
        return ""
    return """
        join symployee_document_identities i
          on i.tenant_id = d.tenant_id
         and i.identity_id = d.identity_id
         and i.repository_id = :repository_id
    """


def _holds_scope_join(repository_id: str | None) -> str:
    if not repository_id:
        return ""
    return """
        join symployee_document_identities i
          on i.tenant_id = h.tenant_id
         and i.identity_id = h.identity_id
         and i.repository_id = :repository_id
    """


def _collect_counts(db, tenant_id: str, repository_id: str | None) -> dict[str, Any]:
    params = {"tenant_id": tenant_id, "repository_id": repository_id}
    identity_total = db.execute(
        text(
            """
            select count(*)
            from symployee_document_identities
            where tenant_id = :tenant_id
              and (:repository_id is null or repository_id = :repository_id)
            """
        ),
        params,
    ).scalar_one()

    latest_declaration = db.execute(
        text(
            f"""
            with latest as (
              select distinct on (d.identity_id)
                     d.identity_id,
                     d.record_status,
                     d.record_stage
              from symployee_record_declarations d
              {_scope_join(repository_id)}
              where d.tenant_id = :tenant_id
              order by d.identity_id, d.declared_at desc nulls last, d.created_at desc
            )
            select
              count(*) as declaration_identity_count,
              count(*) filter (where record_status = 'RECORD_CANDIDATE') as candidate_count,
              count(*) filter (where record_status in ('DECLARED_RECORD','UNDER_LEGAL_HOLD','ARCHIVED','PERMANENT')) as governed_count,
              count(*) filter (where record_stage = 'ACTIVE') as active_stage_count,
              count(*) filter (where record_stage = 'INACTIVE') as inactive_stage_count,
              count(*) filter (where record_stage = 'ARCHIVED') as archived_stage_count,
              count(*) filter (where record_stage is null) as missing_stage_count
            from latest
            """
        ),
        params,
    ).mappings().one()

    hold_counts = db.execute(
        text(
            f"""
            select
              count(*) as hold_total,
              count(*) filter (where h.hold_category is null or trim(h.hold_category) = '') as hold_missing_category_count,
              count(*) filter (where h.hold_status = 'ACTIVE' and coalesce(h.hold_category, 'OTHER') = 'LEGAL') as active_legal_hold_count,
              count(*) filter (where h.hold_status = 'ACTIVE' and coalesce(h.hold_category, 'OTHER') <> 'LEGAL') as active_other_hold_count
            from symployee_record_legal_holds h
            {_holds_scope_join(repository_id)}
            where h.tenant_id = :tenant_id
            """
        ),
        params,
    ).mappings().one()

    return {
        "identity_total": int(identity_total or 0),
        **{key: int(value or 0) for key, value in dict(latest_declaration).items()},
        **{key: int(value or 0) for key, value in dict(hold_counts).items()},
    }


def _select_identity_ids(db, tenant_id: str, repository_id: str | None, limit: int | None) -> list[str]:
    rows = db.execute(
        text(
            """
            select identity_id
            from symployee_document_identities
            where tenant_id = :tenant_id
              and (:repository_id is null or repository_id = :repository_id)
            order by created_at desc
            """
            + (" limit :limit" if limit else "")
        ),
        {"tenant_id": tenant_id, "repository_id": repository_id, "limit": limit},
    ).fetchall()
    return [str(row[0]) for row in rows]


def _select_latest_declaration_rows(
    db,
    tenant_id: str,
    repository_id: str | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            f"""
            with latest as (
              select distinct on (d.identity_id)
                     d.identity_id,
                     d.version_id
              from symployee_record_declarations d
              {_scope_join(repository_id)}
              where d.tenant_id = :tenant_id
              order by d.identity_id, d.declared_at desc nulls last, d.created_at desc
            )
            select identity_id, version_id
            from latest
            order by identity_id
            """
            + (" limit :limit" if limit else "")
        ),
        {"tenant_id": tenant_id, "repository_id": repository_id, "limit": limit},
    ).mappings().all()
    return [dict(row) for row in rows]


def _resolve_hold_policy_categories(db, tenant_id: str) -> dict[str, str]:
    rows = db.execute(
        text(
            """
            select hold_policy_id, hold_category
            from symployee_record_hold_policies
            where tenant_id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id},
    ).fetchall()
    return {str(row[0]): str(row[1]).upper() for row in rows if row[0] and row[1]}


def _infer_hold_category(hold_code: str | None, policy_category: str | None) -> str:
    if policy_category:
        return _normalize_hold_category(policy_category)
    code = str(hold_code or "").upper()
    if "VALIDATION" in code:
        return "VALIDATION"
    if "LEGAL" in code:
        return "LEGAL"
    if "RECORD" in code:
        return "RECORDS"
    if "OPERATION" in code:
        return "OPERATIONAL"
    return "OTHER"


def _backfill_hold_categories(
    db,
    *,
    tenant_id: str,
    repository_id: str | None,
    dry_run: bool,
    performed_by: str | None,
    metadata_json: dict[str, Any],
) -> dict[str, Any]:
    params = {"tenant_id": tenant_id, "repository_id": repository_id}
    rows = db.execute(
        text(
            f"""
            select
              h.legal_hold_id,
              h.identity_id,
              h.hold_code,
              h.hold_category,
              h.hold_policy_id
            from symployee_record_legal_holds h
            {_holds_scope_join(repository_id)}
            where h.tenant_id = :tenant_id
              and (h.hold_category is null or trim(h.hold_category) = '')
            order by h.created_at asc
            """
        ),
        params,
    ).mappings().all()
    policy_categories = _resolve_hold_policy_categories(db, tenant_id)
    updates: list[dict[str, Any]] = []
    for row in rows:
        resolved = _infer_hold_category(
            row.get("hold_code"),
            policy_categories.get(str(row.get("hold_policy_id"))) if row.get("hold_policy_id") else None,
        )
        updates.append(
            {
                "legal_hold_id": row["legal_hold_id"],
                "identity_id": row["identity_id"],
                "hold_code": row["hold_code"],
                "resolved_hold_category": resolved,
            }
        )

    if not dry_run and updates:
        for item in updates:
            db.execute(
                text(
                    """
                    update symployee_record_legal_holds
                    set hold_category = :hold_category,
                        metadata_json = coalesce(metadata_json, '{}'::jsonb) || :metadata_json::jsonb,
                        modified_by = :modified_by,
                        modified_at = now()
                    where tenant_id = :tenant_id
                      and legal_hold_id = :legal_hold_id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "legal_hold_id": item["legal_hold_id"],
                    "hold_category": item["resolved_hold_category"],
                    "metadata_json": json.dumps(
                        {
                            "phase14_backfill": {
                                "updated_at": _now_iso(),
                                **metadata_json,
                            }
                        }
                    ),
                    "modified_by": performed_by,
                },
            )
        db.commit()

    return {
        "processed": len(rows),
        "updated": 0 if dry_run else len(updates),
        "items": updates,
    }


def _reprocess_identities(
    db,
    *,
    tenant_id: str,
    repository_id: str | None,
    identity_ids: list[str],
    batch_size: int,
    trigger_event: str,
    dry_run: bool,
    performed_by: str | None,
    metadata_json: dict[str, Any],
) -> dict[str, Any]:
    summary = {"processed": 0, "executed": 0, "skipped": 0, "errors": 0, "preserved_existing_governed": 0}
    batches: list[dict[str, Any]] = []
    for batch in _chunked(identity_ids, batch_size):
        result = reprocess_repository_record_declarations(
            db,
            tenant_id,
            repository_id=repository_id,
            identity_ids=batch,
            limit=len(batch),
            trigger_event=trigger_event,
            dry_run=dry_run,
            performed_by=performed_by,
            evaluation_reason="Phase 14 historical repository declaration backfill",
            metadata_json=metadata_json,
        )
        summary["processed"] += int(result["processed"])
        summary["executed"] += int(result["executed"])
        summary["skipped"] += int(result["skipped"])
        summary["errors"] += int(result["errors"])
        summary["preserved_existing_governed"] += sum(
            1 for item in result["items"] if item.get("preserved_existing_governed_status")
        )
        batches.append(
            {
                "identity_ids": batch,
                "processed": result["processed"],
                "executed": result["executed"],
                "skipped": result["skipped"],
                "errors": result["errors"],
                "preserved_existing_governed": sum(
                    1 for item in result["items"] if item.get("preserved_existing_governed_status")
                ),
            }
        )
    return {"summary": summary, "batches": batches}


def _evaluate_activity_states(
    db,
    *,
    tenant_id: str,
    declaration_rows: list[dict[str, Any]],
    batch_size: int,
    dry_run: bool,
    performed_by: str | None,
    metadata_json: dict[str, Any],
) -> dict[str, Any]:
    summary = {"processed": 0, "matched": 0, "changed": 0, "errors": 0}
    batches: list[dict[str, Any]] = []
    for batch in _chunked([json.dumps(row) for row in declaration_rows], batch_size):
        processed = matched = changed = errors = 0
        for payload in batch:
            row = json.loads(payload)
            try:
                result = evaluate_record_lifecycle_rule(
                    db,
                    tenant_id,
                    identity_id=row["identity_id"],
                    version_id=row.get("version_id"),
                    trigger_event="TIME_EVALUATION",
                    performed_by=performed_by,
                    evaluation_reason="Phase 14 declaration activity-state backfill",
                    metadata_json=metadata_json,
                    commit=not dry_run,
                )
                processed += 1
                if result.get("matched"):
                    matched += 1
                if (result.get("transition") or {}).get("changed"):
                    changed += 1
            except ValueError:
                errors += 1
        batches.append(
            {
                "processed": processed,
                "matched": matched,
                "changed": changed,
                "errors": errors,
            }
        )
        summary["processed"] += processed
        summary["matched"] += matched
        summary["changed"] += changed
        summary["errors"] += errors
    return {"summary": summary, "batches": batches}


def _write_report(report_path: str | None, report: dict[str, Any]) -> None:
    if not report_path:
        return
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 14 records backfill and re-evaluation")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--repository-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--trigger-event", default="INGESTION")
    parser.add_argument("--performed-by")
    parser.add_argument("--report-path")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    dry_run = not args.execute
    if not dry_run and not args.performed_by:
        raise SystemExit("--performed-by is required when --execute is used")

    run_id = _run_id()
    metadata_json = {
        "trigger_source": "phase14_backfill",
        "backfill_run_id": run_id,
        "mode": "dry_run" if dry_run else "execute",
    }

    db = SessionLocal()
    try:
        before_counts = _collect_counts(db, args.tenant_id, args.repository_id)
        identity_ids = _select_identity_ids(db, args.tenant_id, args.repository_id, args.limit)
        declaration_reprocess = _reprocess_identities(
            db,
            tenant_id=args.tenant_id,
            repository_id=args.repository_id,
            identity_ids=identity_ids,
            batch_size=max(1, min(args.batch_size, 500)),
            trigger_event=args.trigger_event,
            dry_run=dry_run,
            performed_by=args.performed_by,
            metadata_json=metadata_json,
        )
        hold_category_backfill = _backfill_hold_categories(
            db,
            tenant_id=args.tenant_id,
            repository_id=args.repository_id,
            dry_run=dry_run,
            performed_by=args.performed_by,
            metadata_json=metadata_json,
        )
        declaration_rows = _select_latest_declaration_rows(db, args.tenant_id, args.repository_id, args.limit)
        activity_state_backfill = _evaluate_activity_states(
            db,
            tenant_id=args.tenant_id,
            declaration_rows=declaration_rows,
            batch_size=max(1, min(args.batch_size, 500)),
            dry_run=dry_run,
            performed_by=args.performed_by,
            metadata_json=metadata_json,
        )
        after_counts = _collect_counts(db, args.tenant_id, args.repository_id)

        report = {
            "run_id": run_id,
            "generated_at": _now_iso(),
            "mode": "dry_run" if dry_run else "execute",
            "scope": {
                "tenant_id": args.tenant_id,
                "repository_id": args.repository_id,
                "limit": args.limit,
                "batch_size": args.batch_size,
                "trigger_event": args.trigger_event,
            },
            "before_counts": before_counts,
            "actions": {
                "declaration_reprocess": declaration_reprocess,
                "hold_category_backfill": hold_category_backfill,
                "activity_state_backfill": activity_state_backfill,
            },
            "after_counts": after_counts,
        }
        _write_report(args.report_path, report)
        print(json.dumps(report, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
