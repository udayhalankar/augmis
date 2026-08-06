from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_saas_access
from app.services.audit_service import list_audit_logs


router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("/logs")
def audit_logs(
    event_category: str | None = Query(None),
    event_type: str | None = Query(None),
    request_id: str | None = Query(None),
    limit: int = 100,
    current_user: dict = Depends(
        require_saas_access("settings", "admin:settings")
    ),
    db: Session = Depends(get_db),
):
    return list_audit_logs(
        db=db,
        current_user=current_user,
        event_category=event_category,
        event_type=event_type,
        request_id=request_id,
        limit=limit,
    )
