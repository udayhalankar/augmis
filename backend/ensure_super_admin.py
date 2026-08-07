from app.core.database import SessionLocal
from app.db_models import Tenant, User


SUPER_ADMIN_TENANT_ID = "AUGMIS-PLATFORM"
SUPER_ADMIN_EMAIL = "superadmin@augmis.com"
DEFAULT_PASSWORD_HASH = "$2b$12$IBxtGX7IWuBL52l6gprpYu1eezAZuFqbLvfl1KTOWpDCvsytGED6y"  # admin123
DEFAULT_MODULES = [
    "dashboard",
    "copilot",
    "documents",
    "escalations",
    "augmis_business",
    "settings",
]
DEFAULT_PERMISSIONS = [
    "dashboard:view",
    "copilot:use",
    "documents:read",
    "documents:upload",
    "escalation:read",
    "escalation:manage",
    "business_development:read",
    "business_development:create",
    "business_development:update",
    "business_development:delete",
    "business_development:scan",
    "business_development:qualify",
    "business_development:outreach",
    "business_development:admin",
    "admin:users",
    "admin:settings",
]


def ensure_super_admin():
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.tenant_id == SUPER_ADMIN_TENANT_ID).first()
        if not tenant:
            tenant = Tenant(
                tenant_id=SUPER_ADMIN_TENANT_ID,
                tenant_name="AUGMIS Platform",
                status="ACTIVE",
                plan_id="PLAN-ENTERPRISE",
                subscription_status="ACTIVE",
                billing_status="PAID",
                subscription_start="2026-06-01",
                subscription_end="2027-06-01",
            )
            db.add(tenant)
            db.flush()

        user = db.query(User).filter(User.email == SUPER_ADMIN_EMAIL).first()
        if not user:
            user = User(
                user_id="USR-AUGMIS-0001",
                tenant_id=SUPER_ADMIN_TENANT_ID,
                tenant_name="AUGMIS Platform",
                name="AUGMIS Super Admin",
                email=SUPER_ADMIN_EMAIL,
                password_hash=DEFAULT_PASSWORD_HASH,
                role="SUPER_ADMIN",
                status="ACTIVE",
                allowed_modules=DEFAULT_MODULES,
                permissions=DEFAULT_PERMISSIONS,
            )
            db.add(user)
        else:
            user.tenant_id = SUPER_ADMIN_TENANT_ID
            user.tenant_name = "AUGMIS Platform"
            user.name = "AUGMIS Super Admin"
            user.role = "SUPER_ADMIN"
            user.status = "ACTIVE"
            user.allowed_modules = DEFAULT_MODULES
            user.permissions = DEFAULT_PERMISSIONS
            if not user.password_hash:
                user.password_hash = DEFAULT_PASSWORD_HASH

        db.commit()
        print("AUGMIS super admin ensured successfully.")
        print(f"Email: {SUPER_ADMIN_EMAIL}")
        print("Password: admin123")
    finally:
        db.close()


if __name__ == "__main__":
    ensure_super_admin()
