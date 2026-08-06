from fastapi import APIRouter, Query
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_saas_access
from app.services.dashboard_service import get_dashboard_data
from app.services.summary_service import generate_executive_summary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
def dashboard(
    business_area: str = Query("All"),
    risk_level: str = Query("All"),
    date_range: str = Query("All"),
    current_user: dict = Depends(require_saas_access("dashboard", "dashboard:view")),
):
    return get_dashboard_data(
        current_user=current_user,
        business_area=business_area,
        risk_level=risk_level,
        date_range=date_range,
    )

    


@router.api_route("/executive-summary", methods=["GET", "POST"])
def executive_summary(
    current_user: dict = Depends(require_saas_access("dashboard", "dashboard:view")),
    db: Session = Depends(get_db),
):
    return generate_executive_summary(current_user, db)
