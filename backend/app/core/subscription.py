from typing import Callable

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.subscription_service import (
    validate_module_entitlement,
    validate_tenant_subscription,
    validate_usage_limit,
)


def require_active_subscription():
    def checker(
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        validate_tenant_subscription(current_user["tenant_id"], db)
        return current_user

    return checker


def require_subscribed_module(module_name: str) -> Callable:
    def checker(
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        validate_module_entitlement(current_user["tenant_id"], module_name, db)
        return current_user

    return checker


def require_usage_available(limit_name: str) -> Callable:
    def checker(
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        validate_usage_limit(current_user["tenant_id"], limit_name, db)
        return current_user

    return checker
