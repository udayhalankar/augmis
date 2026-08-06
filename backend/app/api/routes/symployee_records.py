from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_saas_access
from app.models.symployee_records_models import (
    SymployeeDispositionCaseRequest,
    SymployeeLegalHoldRequest,
    SymployeeRecordDeclarationRequest,
)
from app.services.symployee_records_service import (
    create_disposition_case,
    declare_record,
    place_legal_hold,
)


router = APIRouter(prefix="/api/symployees/document-controller/records", tags=["SymployeeRecords"])


@router.post("/declarations")
def post_record_declaration(
    payload: SymployeeRecordDeclarationRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = declare_record(
            db,
            current_user["tenant_id"],
            identity_id=payload.identity_id,
            version_id=payload.version_id,
            record_category=payload.record_category,
            owner_user_id=payload.owner_user_id,
            declared_by=current_user["user_id"],
            declaration_reason=payload.declaration_reason,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/legal-holds")
def post_legal_hold(
    payload: SymployeeLegalHoldRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = place_legal_hold(
            db,
            current_user["tenant_id"],
            identity_id=payload.identity_id,
            hold_category=payload.hold_category,
            hold_code=payload.hold_code,
            authority=payload.authority,
            placed_by=current_user["user_id"],
            reason=payload.reason,
            matter_reference=payload.matter_reference,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/disposition")
def post_disposition_case(
    payload: SymployeeDispositionCaseRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = create_disposition_case(
            db,
            current_user["tenant_id"],
            identity_id=payload.identity_id,
            disposition_type=payload.disposition_type,
            requested_by=current_user["user_id"],
            reason=payload.reason,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}
