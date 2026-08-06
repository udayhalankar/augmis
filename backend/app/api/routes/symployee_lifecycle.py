from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_saas_access
from app.models.symployee_lifecycle_models import (
    SymployeeLifecycleEventListRequest,
    SymployeeLifecycleTransitionRequest,
)
from app.services.symployee_lifecycle_service import (
    create_lifecycle_transition,
    list_lifecycle_events,
)


router = APIRouter(prefix="/api/symployees/document-controller", tags=["SymployeeLifecycle"])


@router.get("/lifecycle-events")
def get_lifecycle_events(
    identity_id: str | None = Query(None),
    version_id: str | None = Query(None),
    state_dimension: str | None = Query(None),
    event_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    request = SymployeeLifecycleEventListRequest(
        identity_id=identity_id,
        version_id=version_id,
        state_dimension=state_dimension,
        event_type=event_type,
        limit=limit,
    )
    return {
        "success": True,
        "data": list_lifecycle_events(
            db,
            current_user["tenant_id"],
            identity_id=request.identity_id,
            version_id=request.version_id,
            state_dimension=request.state_dimension,
            event_type=request.event_type,
            limit=request.limit,
        ),
    }


@router.post("/lifecycle/transitions")
def post_lifecycle_transition(
    payload: SymployeeLifecycleTransitionRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:upload")),
    db: Session = Depends(get_db),
):
    try:
        data = create_lifecycle_transition(
            db,
            current_user["tenant_id"],
            identity_id=payload.identity_id,
            version_id=payload.version_id,
            state_dimension=payload.state_dimension,
            new_state=payload.new_state,
            performed_by=current_user["user_id"],
            reason=payload.reason,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": data}
