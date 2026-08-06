from datetime import datetime, timedelta
from uuid import uuid4

import bcrypt
from fastapi import HTTPException, status
import jwt

from app.core.config import settings
from app.core.database import SessionLocal
from app.db_models import Tenant, TenantUsage, User
from app.models.auth_models import (
    AcceptInviteRequest,
    ChangePasswordRequest,
    CreateUserRequest,
    ForgotPasswordRequest,
    InviteUserRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterWorkspaceRequest,
    ResetPasswordLinkRequest,
    ResetPasswordOtpRequest,
    UpdateUserRequest,
)
from app.services.auth_governance_settings_service import get_auth_governance_settings
from app.services.auth_runtime_challenge_service import (
    create_otp_challenge,
    verify_otp_challenge,
)
from app.services.auth_runtime_email_service import send_auth_email
from app.services.auth_runtime_security_service import (
    assert_login_allowed,
    assert_otp_request_allowed,
    clear_failed_login,
    record_failed_login,
    record_otp_request,
)
from app.services.auth_runtime_session_service import (
    create_auth_session,
    list_user_sessions,
    refresh_auth_session,
    revoke_all_user_sessions,
    revoke_session,
)
from app.services.subscription_service import (
    _current_period,
    get_plan,
    refresh_tenant_usage_counts,
    validate_usage_limit,
)


SECRET_KEY = settings.AUTH_JWT_SECRET
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.AUTH_ACCESS_TOKEN_MINUTES
DEFAULT_TENANT_ADMIN_MODULES = [
    "dashboard",
    "copilot",
    "documents",
    "proposals",
    "vendors",
    "procurement",
    "escalations",
    "settings",
]
DEFAULT_TENANT_ADMIN_PERMISSIONS = [
    "dashboard:view",
    "copilot:use",
    "documents:read",
    "documents:upload",
    "proposal:read",
    "proposal:write",
    "vendor:read",
    "vendor:write",
    "procurement:read",
    "procurement:write",
    "escalation:read",
    "escalation:manage",
    "admin:users",
    "admin:settings",
]


def validate_password_strength(password: str) -> None:
    candidate = str(password or "")
    governance = get_auth_governance_settings()
    policy = governance["password_policy"]

    if len(candidate) < int(policy["min_length"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {policy['min_length']} characters long",
        )
    if policy.get("require_uppercase") and not any(char.isupper() for char in candidate):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain at least one uppercase letter")
    if policy.get("require_lowercase") and not any(char.islower() for char in candidate):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain at least one lowercase letter")
    if policy.get("require_number") and not any(char.isdigit() for char in candidate):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain at least one number")
    if policy.get("require_symbol") and all(char.isalnum() for char in candidate):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain at least one symbol")


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def find_user_by_email(email: str, db=None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        return (
            db.query(User)
            .filter(User.email == email.lower().strip())
            .first()
        )
    finally:
        if should_close:
            db.close()


def sanitize_user(user: User | dict) -> dict:
    if isinstance(user, dict):
        return {
            "user_id": user["user_id"],
            "tenant_id": user["tenant_id"],
            "tenant_name": user.get("tenant_name", ""),
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "status": user["status"],
            "allowed_modules": user.get("allowed_modules", []),
            "permissions": user.get("permissions", []),
        }

    return {
        "user_id": user.user_id,
        "tenant_id": user.tenant_id,
        "tenant_name": user.tenant_name or "",
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "allowed_modules": user.allowed_modules or [],
        "permissions": user.permissions or [],
    }


def create_access_token(user: User | dict, session_id: str | None = None) -> str:
    expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    safe_user = sanitize_user(user)

    payload = {
        "sub": safe_user["user_id"],
        "tenant_id": safe_user["tenant_id"],
        "email": safe_user["email"],
        "role": safe_user["role"],
        "allowed_modules": safe_user["allowed_modules"] or [],
        "permissions": safe_user["permissions"] or [],
        "type": "access",
        "sid": session_id,
        "exp": expires,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_password_reset_link_token(email: str) -> str:
    expires = datetime.utcnow() + timedelta(hours=1)
    return jwt.encode(
        {
            "email": email.lower().strip(),
            "type": "password_reset",
            "exp": expires,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_password_reset_link_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link",
        ) from exc
    if payload.get("type") != "password_reset" or not payload.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset link payload",
        )
    return str(payload["email"]).lower().strip()


def get_auth_capabilities() -> dict:
    governance = get_auth_governance_settings()
    flags = governance["feature_flags"]
    return {
        "success": True,
        "data": {
            "password_login": {"available": True, "label": "Email and password"},
            "otp_reset": {
                "available": True,
                "label": "OTP password reset",
                "delivery_mode": "onscreen_demo",
            },
            "reset_link": {
                "available": bool(flags.get("reset_link_enabled", True)),
                "label": "Reset link by email",
            },
            "google_login": {
                "available": bool(flags.get("google_login_enabled", False)),
                "label": "Google sign-in",
                "reason": "Google OAuth client credentials are not configured for this deployment.",
            },
            "mfa": {
                "available": bool(flags.get("mfa_enabled", False)),
                "label": "Multi-factor authentication",
                "reason": "MFA enrollment is not configured yet in this deployment.",
            },
            "registration": {
                "available": bool(flags.get("self_registration_enabled", True)),
                "label": "Self-registration",
            },
            "invite_onboarding": {
                "available": bool(flags.get("invite_onboarding_enabled", True)),
                "label": "Invite onboarding",
            },
        },
    }


def login(payload: LoginRequest, db=None, ip_address: str | None = None, user_agent: str | None = None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        assert_login_allowed(payload.email, ip_address)
        user = find_user_by_email(payload.email, db)

        if not user:
            record_failed_login(payload.email, ip_address)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if user.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        if not verify_password(payload.password, user.password_hash):
            failure_state = record_failed_login(payload.email, ip_address)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    "Invalid email or password"
                    if not failure_state.get("lockout_until")
                    else f"Account locked until {failure_state['lockout_until']}"
                ),
            )

        clear_failed_login(user.email)
        session = create_auth_session(
            user=sanitize_user(user),
            remember_me=payload.remember_me,
            ip_address=ip_address,
            user_agent=user_agent,
            db=db,
        )
        token = create_access_token(user, session["session_id"])

        return {
            "success": True,
            "access_token": token,
            "refresh_token": session["refresh_token"],
            "session_id": session["session_id"],
            "token_type": "bearer",
            "user": sanitize_user(user),
        }
    finally:
        if should_close:
            db.close()


def register_workspace(payload: RegisterWorkspaceRequest, db=None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        governance = get_auth_governance_settings()
        if not governance["feature_flags"].get("self_registration_enabled", True):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Self-registration is disabled")
        if not governance["registration_policy"].get("self_registration_enabled", True):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registration policy currently disables self-registration")
        validate_password_strength(payload.password)
        existing = find_user_by_email(payload.email, db)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User email already exists",
            )

        policy = governance["registration_policy"]
        if policy.get("domain_validation_enabled"):
            domain = payload.email.lower().strip().split("@")[-1]
            allowed_domains = [item.lower().strip() for item in policy.get("allowed_domains", []) if item]
            if allowed_domains and domain not in allowed_domains:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration email domain is not allowed")

        get_plan(payload.plan_id, db)

        tenant = Tenant(
            tenant_id=f"TENANT-{str(uuid4())[:8].upper()}",
            tenant_name=payload.tenant_name.strip(),
            status="ACTIVE",
            plan_id=payload.plan_id,
            subscription_status="ACTIVE",
            billing_status="TRIAL",
            subscription_start=datetime.utcnow().date().isoformat(),
            subscription_end="",
        )
        db.add(tenant)
        db.flush()

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

        new_user = User(
            user_id=f"USR-{str(uuid4())[:8].upper()}",
            tenant_id=tenant.tenant_id,
            tenant_name=tenant.tenant_name,
            name=payload.name.strip(),
            email=payload.email.lower().strip(),
            password_hash=hash_password(payload.password),
            role="TENANT_ADMIN",
            status="ACTIVE",
            allowed_modules=DEFAULT_TENANT_ADMIN_MODULES,
            permissions=DEFAULT_TENANT_ADMIN_PERMISSIONS,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        refresh_tenant_usage_counts(tenant.tenant_id, db)

        session = create_auth_session(
            user=sanitize_user(new_user),
            remember_me=True,
            ip_address=None,
            user_agent="self-registration",
            db=db,
        )
        token = create_access_token(new_user, session["session_id"])
        return {
            "success": True,
            "access_token": token,
            "refresh_token": session["refresh_token"],
            "session_id": session["session_id"],
            "token_type": "bearer",
            "user": sanitize_user(new_user),
            "tenant": {
                "tenant_id": tenant.tenant_id,
                "tenant_name": tenant.tenant_name,
                "plan_id": tenant.plan_id,
                "billing_status": tenant.billing_status,
            },
        }
    finally:
        if should_close:
            db.close()


def request_password_reset_otp(payload: ForgotPasswordRequest, db=None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        assert_otp_request_allowed(payload.email)
        user = find_user_by_email(payload.email, db)
        if not user:
            return {
                "success": True,
                "message": "If the email exists, an OTP has been issued.",
                "delivery_mode": "onscreen_demo",
            }

        challenge = create_otp_challenge(
            kind="password_reset",
            email=user.email,
            metadata={"user_id": user.user_id},
        )
        record_otp_request(user.email)
        email_result = send_auth_email(
            to_email=user.email,
            subject="Augmis password reset OTP",
            text_body=f"Your Augmis password reset OTP is {challenge['otp_preview']}. It expires at {challenge['expires_at']}.",
            metadata={"kind": "password_reset_otp", "challenge_id": challenge["challenge_id"]},
        )
        return {
            "success": True,
            "message": "OTP issued for password reset.",
            "email_delivery": email_result,
            **challenge,
        }
    finally:
        if should_close:
            db.close()


def request_password_reset_link(payload: ForgotPasswordRequest, db=None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        governance = get_auth_governance_settings()
        if not governance["feature_flags"].get("reset_link_enabled", True):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reset link flow is disabled")
        user = find_user_by_email(payload.email, db)
        if not user:
            return {
                "success": True,
                "message": "If the email exists, a reset link has been issued.",
            }
        token = create_password_reset_link_token(user.email)
        reset_link = f"{settings.AUTH_RESET_LINK_BASE_URL}?token={token}"
        email_result = send_auth_email(
            to_email=user.email,
            subject="Augmis password reset link",
            text_body=f"Use this reset link to change your password: {reset_link}",
            metadata={"kind": "password_reset_link", "email": user.email},
        )
        return {
            "success": True,
            "message": "Reset link issued.",
            "reset_link_preview": reset_link,
            "email_delivery": email_result,
        }
    finally:
        if should_close:
            db.close()


def reset_password_with_otp(payload: ResetPasswordOtpRequest, db=None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        validate_password_strength(payload.new_password)
        challenge = verify_otp_challenge(
            challenge_id=payload.challenge_id,
            otp=payload.otp,
            expected_kind="password_reset",
        )
        user = find_user_by_email(challenge["email"], db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User no longer exists",
            )

        user.password_hash = hash_password(payload.new_password)
        db.commit()
        db.refresh(user)
        revoke_all_user_sessions(user.user_id, db=db)

        return {
            "success": True,
            "message": "Password reset completed successfully.",
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        if should_close:
            db.close()


def reset_password_with_link(payload: ResetPasswordLinkRequest, db=None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        validate_password_strength(payload.new_password)
        email = decode_password_reset_link_token(payload.token)
        user = find_user_by_email(email, db)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User no longer exists")
        user.password_hash = hash_password(payload.new_password)
        db.commit()
        db.refresh(user)
        revoke_all_user_sessions(user.user_id, db=db)
        return {"success": True, "message": "Password reset completed successfully."}
    finally:
        if should_close:
            db.close()


def refresh_login(payload: RefreshTokenRequest, db=None):
    should_close = db is None
    if db is None:
        db = SessionLocal()
    try:
        session = refresh_auth_session(payload.refresh_token, db=db)
        if not session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        user = find_user_by_email(session["email"], db)
        if not user or user.status != "ACTIVE":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not available for refresh")
        token = create_access_token(user, session["session_id"])
        return {
            "success": True,
            "access_token": token,
            "refresh_token": session["refresh_token"],
            "session_id": session["session_id"],
            "token_type": "bearer",
            "user": sanitize_user(user),
        }
    finally:
        if should_close:
            db.close()


def logout_current_session(current_user: dict, session_id: str | None) -> dict:
    revoked = revoke_session(session_id)
    return {"success": True, "revoked": revoked, "message": "Session logged out."}


def logout_named_session(current_user: dict, session_id: str) -> dict:
    sessions = list_user_sessions(current_user["user_id"])
    if not any(session.get("session_id") == session_id for session in sessions):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found for current user",
        )
    revoked = revoke_session(session_id)
    return {"success": True, "revoked": revoked, "message": "Session revoked."}


def logout_all_sessions(current_user: dict) -> dict:
    revoked_count = revoke_all_user_sessions(current_user["user_id"])
    return {"success": True, "revoked_count": revoked_count}


def get_user_sessions(current_user: dict) -> dict:
    return {"success": True, "data": list_user_sessions(current_user["user_id"])}


def change_password(payload: ChangePasswordRequest, current_user: dict, session_id: str | None, db=None):
    should_close = db is None
    if db is None:
        db = SessionLocal()
    try:
        user = find_user_by_email(current_user["email"], db)
        if not user or not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
        validate_password_strength(payload.new_password)
        user.password_hash = hash_password(payload.new_password)
        db.commit()
        db.refresh(user)
        if payload.revoke_other_sessions:
            revoke_all_user_sessions(user.user_id, db=db)
        session = create_auth_session(
            user=sanitize_user(user),
            remember_me=True,
            ip_address=None,
            user_agent="password-change",
            db=db,
        )
        token = create_access_token(user, session["session_id"])
        if session_id:
            revoke_session(session_id, db=db)
        return {
            "success": True,
            "message": "Password changed successfully.",
            "access_token": token,
            "refresh_token": session["refresh_token"],
            "session_id": session["session_id"],
            "user": sanitize_user(user),
        }
    finally:
        if should_close:
            db.close()


def create_user_for_tenant(payload: CreateUserRequest, current_user: dict, db=None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        if current_user["role"] not in ["SUPER_ADMIN", "TENANT_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only tenant admins can create users",
            )
        if payload.role == "SUPER_ADMIN" and current_user["role"] != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only AUGMIS master admins can assign the SUPER_ADMIN role",
            )

        validate_usage_limit(current_user["tenant_id"], "users", db)

        existing = find_user_by_email(payload.email, db)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User email already exists",
            )

        new_user = User(
            user_id=f"USR-{str(uuid4())[:8].upper()}",
            tenant_id=current_user["tenant_id"],
            tenant_name=current_user.get("tenant_name", ""),
            name=payload.name,
            email=payload.email.lower().strip(),
            password_hash=hash_password(payload.password),
            role=payload.role,
            status=payload.status,
            allowed_modules=payload.allowed_modules,
            permissions=payload.permissions,
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        refresh_tenant_usage_counts(current_user["tenant_id"], db)

        return {
            "success": True,
            "data": sanitize_user(new_user),
        }
    finally:
        if should_close:
            db.close()


def update_user_for_tenant(
    user_id: str,
    payload: UpdateUserRequest,
    current_user: dict,
    db=None,
):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        if current_user["role"] not in ["SUPER_ADMIN", "TENANT_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only tenant admins can update users",
            )
        if payload.role == "SUPER_ADMIN" and current_user["role"] != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only AUGMIS master admins can assign the SUPER_ADMIN role",
            )

        user = (
            db.query(User)
            .filter(
                User.user_id == user_id,
                User.tenant_id == current_user["tenant_id"],
            )
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        existing = find_user_by_email(payload.email, db)
        if existing and existing.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User email already exists",
            )

        user.name = payload.name
        user.email = payload.email.lower().strip()
        user.role = payload.role
        user.status = payload.status
        user.allowed_modules = payload.allowed_modules
        user.permissions = payload.permissions
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "data": sanitize_user(user),
        }
    finally:
        if should_close:
            db.close()


def delete_user_for_tenant(user_id: str, current_user: dict, db=None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        if current_user["role"] not in ["SUPER_ADMIN", "TENANT_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only tenant admins can delete users",
            )

        user = (
            db.query(User)
            .filter(
                User.user_id == user_id,
                User.tenant_id == current_user["tenant_id"],
            )
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.user_id == current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot delete your own active account",
            )

        db.delete(user)
        db.commit()
        refresh_tenant_usage_counts(current_user["tenant_id"], db)
        revoke_all_user_sessions(user_id, db=db)

        return {
            "success": True,
            "message": "User deleted successfully.",
        }
    finally:
        if should_close:
            db.close()


def create_user_invite(payload: InviteUserRequest, current_user: dict, db=None):
    should_close = db is None
    if db is None:
        db = SessionLocal()
    try:
        from app.services.auth_invite_service import create_invite

        return create_invite(current_user, payload.model_dump(), db)
    finally:
        if should_close:
            db.close()


def get_user_invite(token: str) -> dict:
    from app.services.auth_invite_service import get_invite

    invite = get_invite(token)
    return {
        "success": True,
        "data": {
            "email": invite["email"],
            "tenant_name": invite.get("tenant_name", ""),
            "role": invite["role"],
            "expires_at": invite["expires_at"],
        },
    }


def accept_user_invite(token: str, payload: AcceptInviteRequest, db=None):
    should_close = db is None
    if db is None:
        db = SessionLocal()
    try:
        from app.services.auth_invite_service import accept_invite

        validate_password_strength(payload.password)
        result = accept_invite(token, payload.model_dump(), db)
        user = result["user"]
        session = create_auth_session(
            user=user,
            remember_me=True,
            ip_address=None,
            user_agent="invite-acceptance",
            db=db,
        )
        token_value = create_access_token(user, session["session_id"])
        return {
            "success": True,
            "access_token": token_value,
            "refresh_token": session["refresh_token"],
            "session_id": session["session_id"],
            "token_type": "bearer",
            "user": user,
        }
    finally:
        if should_close:
            db.close()


def list_users_for_tenant(current_user: dict, db=None):
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        if current_user["role"] not in ["SUPER_ADMIN", "TENANT_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only tenant admins can view users",
            )

        tenant_users = (
            db.query(User)
            .filter(User.tenant_id == current_user["tenant_id"])
            .all()
        )

        return {
            "success": True,
            "data": [sanitize_user(user) for user in tenant_users],
        }
    finally:
        if should_close:
            db.close()
