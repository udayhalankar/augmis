from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_saas_access
from app.models.symployee_transmittal_models import (
    SymployeeAcknowledgementRequest,
    SymployeeTransmittalCreateRequest,
    SymployeeTransmittalItemRequest,
)
from app.services.symployee_transmittal_service import (
    acknowledge_transmittal,
    create_transmittal,
    create_transmittal_item,
    list_transmittals,
)


router = APIRouter(
    prefix="/api/symployees/document-controller/transmittals",
    tags=["SymployeeTransmittals"],
)


@router.get("")
def get_transmittals(
    direction: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": list_transmittals(
            db,
            current_user["tenant_id"],
            direction=direction,
            limit=limit,
        ),
    }


@router.post("")
def post_transmittal(
    payload: SymployeeTransmittalCreateRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    data = create_transmittal(
        db,
        current_user["tenant_id"],
        direction=payload.direction,
        purpose_code=payload.purpose_code,
        sender_org=payload.sender_org,
        recipient_org=payload.recipient_org,
        response_required=payload.response_required,
        response_due_at=payload.response_due_at,
        prepared_by=current_user["user_id"],
        workflow_instance_id=payload.workflow_instance_id,
        subject=payload.subject,
        notes=payload.notes,
        transmittal_number=payload.transmittal_number,
        metadata_json=payload.metadata_json,
    )
    return {"success": True, "data": data}


@router.post("/{transmittal_id}/items")
def post_transmittal_item(
    transmittal_id: str,
    payload: SymployeeTransmittalItemRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = create_transmittal_item(
            db,
            current_user["tenant_id"],
            transmittal_id=transmittal_id,
            identity_id=payload.identity_id,
            version_id=payload.version_id,
            sequence_no=payload.sequence_no,
            purpose_code=payload.purpose_code,
            response_code=payload.response_code,
            created_by=current_user["user_id"],
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/acknowledgements")
def post_acknowledgement(
    payload: SymployeeAcknowledgementRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = acknowledge_transmittal(
            db,
            current_user["tenant_id"],
            transmittal_id=payload.transmittal_id,
            transmittal_item_id=payload.transmittal_item_id,
            recipient_ref=payload.recipient_ref,
            recipient_name=payload.recipient_name,
            status=payload.status,
            response_status=payload.response_status,
            due_at=payload.due_at,
            comments=payload.comments,
            modified_by=current_user["user_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}
