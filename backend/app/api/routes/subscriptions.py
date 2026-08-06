from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.tenant_models import (
    TenantCreateRequest,
    TenantUpdatePlanRequest,
    UsageUpdateRequest,
)
from app.services.subscription_service import (
    create_tenant,
    get_all_plans,
    get_my_subscription,
    update_tenant_plan,
    update_usage,
)


router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])


@router.get("/plans")
def plans():
    return get_all_plans()


@router.get("/me")
def my_subscription(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_my_subscription(current_user, db)


@router.post("/tenants")
def create_new_tenant(
    payload: TenantCreateRequest,
    current_user: dict = Depends(require_role(["SUPER_ADMIN"])),
):
    return create_tenant(payload)


@router.patch("/tenants/{tenant_id}/plan")
def change_tenant_plan(
    tenant_id: str,
    payload: TenantUpdatePlanRequest,
    current_user: dict = Depends(require_role(["SUPER_ADMIN"])),
):
    return update_tenant_plan(tenant_id, payload.plan_id)


@router.patch("/usage")
def update_my_usage(
    payload: UsageUpdateRequest,
    current_user: dict = Depends(require_role(["SUPER_ADMIN", "TENANT_ADMIN"])),
    db: Session = Depends(get_db),
):
    return update_usage(current_user["tenant_id"], payload, db)
