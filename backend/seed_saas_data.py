from datetime import date
from uuid import uuid4

from app.core.database import SessionLocal
from app.db_models import Plan, Tenant, TenantUsage, User


def seed():
    db = SessionLocal()

    try:
        if not db.query(Plan).filter(Plan.plan_id == "PLAN-PROFESSIONAL").first():
            plans = [
                Plan(
                    plan_id="PLAN-STARTER",
                    plan_name="Starter",
                    price_monthly=500,
                    currency="INR",
                    max_users=5,
                    max_documents=100,
                    max_storage_mb=500,
                    monthly_ai_tokens=100000,
                    allowed_modules=["dashboard", "copilot", "documents"],
                    features=["AI Copilot", "Document Intelligence", "Executive Dashboard"],
                ),
                Plan(
                    plan_id="PLAN-PROFESSIONAL",
                    plan_name="Professional",
                    price_monthly=2500,
                    currency="INR",
                    max_users=25,
                    max_documents=1000,
                    max_storage_mb=5120,
                    monthly_ai_tokens=1000000,
                    allowed_modules=[
                        "dashboard",
                        "copilot",
                        "documents",
                        "escalations",
                    ],
                    features=[
                        "Business Area Intelligence",
                        "Escalation Intelligence",
                    ],
                ),
                Plan(
                    plan_id="PLAN-ENTERPRISE",
                    plan_name="Enterprise",
                    price_monthly=0,
                    currency="INR",
                    max_users=9999,
                    max_documents=999999,
                    max_storage_mb=102400,
                    monthly_ai_tokens=99999999,
                    allowed_modules=[
                        "dashboard",
                        "copilot",
                        "documents",
                        "escalations",
                        "settings",
                    ],
                    features=[
                        "All Modules",
                        "Advanced Governance",
                        "Custom Billing",
                        "Dedicated Support",
                    ],
                ),
            ]
            db.add_all(plans)

        if not db.query(Tenant).filter(Tenant.tenant_id == "TENANT-001").first():
            db.add(
                Tenant(
                    tenant_id="TENANT-001",
                    tenant_name="Infomentica Demo Tenant",
                    status="ACTIVE",
                    plan_id="PLAN-ENTERPRISE",
                    subscription_status="ACTIVE",
                    billing_status="PAID",
                    subscription_start="2026-06-01",
                    subscription_end="2026-07-01",
                )
            )

        if not db.query(Tenant).filter(Tenant.tenant_id == "AUGMIS-PLATFORM").first():
            db.add(
                Tenant(
                    tenant_id="AUGMIS-PLATFORM",
                    tenant_name="AUGMIS Platform",
                    status="ACTIVE",
                    plan_id="PLAN-ENTERPRISE",
                    subscription_status="ACTIVE",
                    billing_status="PAID",
                    subscription_start="2026-06-01",
                    subscription_end="2027-06-01",
                )
            )

        if not db.query(User).filter(User.email == "admin@infomentica.com").first():
            db.add(
                User(
                    user_id="USR-0001",
                    tenant_id="TENANT-001",
                    tenant_name="Infomentica Demo Tenant",
                    name="Tenant Admin",
                    email="admin@infomentica.com",
                    password_hash="$2b$12$IBxtGX7IWuBL52l6gprpYu1eezAZuFqbLvfl1KTOWpDCvsytGED6y",
                    role="TENANT_ADMIN",
                    status="ACTIVE",
                    allowed_modules=[
                        "dashboard",
                        "copilot",
                        "documents",
                        "escalations",
                        "settings",
                    ],
                    permissions=[
                        "dashboard:view",
                        "copilot:use",
                        "documents:read",
                        "documents:upload",
                        "escalation:read",
                        "escalation:manage",
                        "admin:users",
                        "admin:settings",
                    ],
                )
            )

        if not db.query(User).filter(User.email == "superadmin@augmis.com").first():
            db.add(
                User(
                    user_id="USR-AUGMIS-0001",
                    tenant_id="AUGMIS-PLATFORM",
                    tenant_name="AUGMIS Platform",
                    name="AUGMIS Super Admin",
                    email="superadmin@augmis.com",
                    password_hash="$2b$12$IBxtGX7IWuBL52l6gprpYu1eezAZuFqbLvfl1KTOWpDCvsytGED6y",
                    role="SUPER_ADMIN",
                    status="ACTIVE",
                    allowed_modules=[
                        "dashboard",
                        "copilot",
                        "documents",
                        "escalations",
                        "settings",
                    ],
                    permissions=[
                        "dashboard:view",
                        "copilot:use",
                        "documents:read",
                        "documents:upload",
                        "escalation:read",
                        "escalation:manage",
                        "admin:users",
                        "admin:settings",
                    ],
                )
            )

        if not db.query(TenantUsage).filter(
            TenantUsage.tenant_id == "TENANT-001",
            TenantUsage.period == date.today().strftime("%Y-%m"),
        ).first():
            db.add(
                TenantUsage(
                    usage_id=f"USAGE-{str(uuid4())[:8].upper()}",
                    tenant_id="TENANT-001",
                    users_count=1,
                    documents_count=0,
                    storage_used_mb=0,
                    ai_tokens_used=0,
                    period=date.today().strftime("%Y-%m"),
                )
            )
        db.commit()

        db.commit()
        print("SaaS seed data created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
