from fastapi import APIRouter, Depends, Query

from app.core.security import require_saas_access
from app.services.escalation_service import get_escalation_dashboard

router = APIRouter(prefix="/api/escalations", tags=["Escalations"])


@router.get("/dashboard")
def escalation_dashboard(
    include_records: bool = Query(True),
    current_user: dict = Depends(
        require_saas_access("escalations", "escalation:read")
    ),
):
    return get_escalation_dashboard(
        current_user["tenant_id"],
        include_records=include_records,
    )


@router.get("/dashboard/summary")
def escalation_dashboard_summary(
    current_user: dict = Depends(
        require_saas_access("escalations", "escalation:read")
    ),
):
    return get_escalation_dashboard(
        current_user["tenant_id"],
        include_records=False,
    )
