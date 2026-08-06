from datetime import date, datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.db_models import Document, Plan, Tenant, TenantUsage, User


def _current_period():
    return date.today().strftime("%Y-%m")


def serialize_plan(plan: Plan) -> dict:
    return {
        "plan_id": plan.plan_id,
        "plan_name": plan.plan_name,
        "price_monthly": plan.price_monthly,
        "currency": plan.currency,
        "max_users": plan.max_users,
        "max_documents": plan.max_documents,
        "max_storage_mb": plan.max_storage_mb,
        "monthly_ai_tokens": plan.monthly_ai_tokens,
        "allowed_modules": plan.allowed_modules or [],
        "features": plan.features or [],
    }


def serialize_tenant(tenant: Tenant) -> dict:
    return {
        "tenant_id": tenant.tenant_id,
        "tenant_name": tenant.tenant_name,
        "status": tenant.status,
        "plan_id": tenant.plan_id,
        "subscription_status": tenant.subscription_status,
        "billing_status": tenant.billing_status,
        "subscription_start": tenant.subscription_start,
        "subscription_end": tenant.subscription_end,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
    }


def serialize_usage(usage: TenantUsage) -> dict:
    return {
        "usage_id": usage.usage_id,
        "tenant_id": usage.tenant_id,
        "users_count": usage.users_count,
        "documents_count": usage.documents_count,
        "storage_used_mb": usage.storage_used_mb,
        "ai_tokens_used": usage.ai_tokens_used,
        "period": usage.period,
    }


def get_all_plans():
    db = SessionLocal()
    try:
        plans = db.query(Plan).all()
        return {
            "success": True,
            "data": [serialize_plan(plan) for plan in plans],
        }
    finally:
        db.close()


def get_plan(plan_id: str, db: Session | None = None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        plan = db.query(Plan).filter(Plan.plan_id == plan_id).first()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found",
            )
        return plan
    finally:
        if should_close:
            db.close()


def get_tenant(tenant_id: str, db: Session | None = None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )
        return tenant
    finally:
        if should_close:
            db.close()


def get_tenant_usage(tenant_id: str, db: Session | None = None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        period = _current_period()
        usage = (
            db.query(TenantUsage)
            .filter(TenantUsage.tenant_id == tenant_id, TenantUsage.period == period)
            .first()
        )

        if usage:
            return usage

        usage = TenantUsage(
            usage_id=f"USAGE-{str(uuid4())[:8].upper()}",
            tenant_id=tenant_id,
            users_count=0,
            documents_count=0,
            storage_used_mb=0,
            ai_tokens_used=0,
            period=period,
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)
        return usage
    finally:
        if should_close:
            db.close()


def get_subscription_context(tenant_id: str, db: Session | None = None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        tenant = get_tenant(tenant_id, db)
        plan = get_plan(tenant.plan_id, db)
        usage = get_tenant_usage(tenant_id, db)

        return {
            "tenant": serialize_tenant(tenant),
            "plan": serialize_plan(plan),
            "usage": serialize_usage(usage),
        }
    finally:
        if should_close:
            db.close()


def validate_tenant_subscription(tenant_id: str, db: Session | None = None):
    context = get_subscription_context(tenant_id, db)
    tenant = context["tenant"]

    if tenant.get("status") != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is inactive",
        )

    if tenant.get("subscription_status") != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Subscription is not active",
        )

    if tenant.get("billing_status") not in ["PAID", "TRIAL"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Billing is not active",
        )

    subscription_end = tenant.get("subscription_end")
    if subscription_end:
        end_date = datetime.strptime(subscription_end, "%Y-%m-%d").date()
        if end_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Subscription has expired",
            )

    return context


def validate_module_entitlement(
    tenant_id: str,
    module_name: str,
    db: Session | None = None,
):
    context = validate_tenant_subscription(tenant_id, db)
    plan = context["plan"]

    if module_name not in plan.get("allowed_modules", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Module not available in current subscription plan: {module_name}",
        )

    return context


def validate_usage_limit(
    tenant_id: str,
    limit_name: str,
    db: Session | None = None,
):
    context = validate_tenant_subscription(tenant_id, db)

    plan = context["plan"]
    usage = context["usage"]

    limit_map = {
        "users": ("users_count", "max_users"),
        "documents": ("documents_count", "max_documents"),
        "storage": ("storage_used_mb", "max_storage_mb"),
        "ai_tokens": ("ai_tokens_used", "monthly_ai_tokens"),
    }

    if limit_name not in limit_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid usage limit name",
        )

    usage_key, plan_key = limit_map[limit_name]

    if float(usage.get(usage_key, 0)) >= float(plan.get(plan_key, 0)):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Usage limit exceeded: {limit_name}",
        )

    return context


def refresh_tenant_usage_counts(tenant_id: str, db: Session):
    usage = get_tenant_usage(tenant_id, db)

    users_count = db.query(User).filter(User.tenant_id == tenant_id).count()
    documents_count = db.query(Document).filter(Document.tenant_id == tenant_id).count()

    usage.users_count = users_count
    usage.documents_count = documents_count

    db.commit()
    db.refresh(usage)

    return serialize_usage(usage)


def add_storage_usage(tenant_id: str, file_size_bytes: int, db: Session):
    usage = get_tenant_usage(tenant_id, db)

    file_size_mb = round(file_size_bytes / (1024 * 1024), 4)
    usage.storage_used_mb = float(usage.storage_used_mb or 0) + file_size_mb

    db.commit()
    db.refresh(usage)

    return serialize_usage(usage)


def add_ai_token_usage(tenant_id: str, tokens_used: int, db: Session):
    usage = get_tenant_usage(tenant_id, db)

    usage.ai_tokens_used = int(usage.ai_tokens_used or 0) + int(tokens_used or 0)

    db.commit()
    db.refresh(usage)

    return serialize_usage(usage)


def get_my_subscription(current_user: dict, db: Session | None = None):
    context = get_subscription_context(current_user["tenant_id"], db)
    return {
        "success": True,
        "data": context,
    }


def create_tenant(payload):
    db = SessionLocal()
    try:
        tenant = Tenant(
            tenant_id=f"TENANT-{str(uuid4())[:8].upper()}",
            tenant_name=payload.tenant_name,
            status="ACTIVE",
            plan_id=payload.plan_id,
            subscription_status="ACTIVE",
            billing_status="TRIAL",
            subscription_start=date.today().isoformat(),
            subscription_end="",
        )
        db.add(tenant)

        usage = TenantUsage(
            usage_id=f"USAGE-{str(uuid4())[:8].upper()}",
            tenant_id=tenant.tenant_id,
            users_count=0,
            documents_count=0,
            storage_used_mb=0,
            ai_tokens_used=0,
            period=_current_period(),
        )
        db.add(usage)
        db.commit()
        db.refresh(tenant)

        return {
            "success": True,
            "data": serialize_tenant(tenant),
        }
    finally:
        db.close()


def update_tenant_plan(tenant_id: str, plan_id: str):
    db = SessionLocal()
    try:
        get_plan(plan_id, db)
        tenant = get_tenant(tenant_id, db)
        tenant.plan_id = plan_id
        tenant.subscription_status = "ACTIVE"
        tenant.billing_status = "PAID"
        db.commit()
        db.refresh(tenant)

        return {
            "success": True,
            "data": serialize_tenant(tenant),
        }
    finally:
        db.close()


def update_usage(tenant_id: str, payload, db: Session | None = None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        usage = get_tenant_usage(tenant_id, db)

        if payload.users_count is not None:
            usage.users_count = payload.users_count

        if payload.documents_count is not None:
            usage.documents_count = payload.documents_count

        if payload.storage_used_mb is not None:
            usage.storage_used_mb = payload.storage_used_mb

        if payload.ai_tokens_used is not None:
            usage.ai_tokens_used = payload.ai_tokens_used

        db.commit()
        db.refresh(usage)

        return {
            "success": True,
            "data": serialize_usage(usage),
        }
    finally:
        if should_close:
            db.close()
