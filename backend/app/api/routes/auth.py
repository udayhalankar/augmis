from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
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
from app.services.audit_service import create_audit_log
from app.services.auth_service import (
    accept_user_invite,
    change_password,
    create_user_invite,
    create_user_for_tenant,
    delete_user_for_tenant,
    get_auth_capabilities,
    get_user_invite,
    get_user_sessions,
    list_users_for_tenant,
    login,
    logout_named_session,
    logout_all_sessions,
    logout_current_session,
    refresh_login,
    register_workspace,
    request_password_reset_link,
    request_password_reset_otp,
    reset_password_with_link,
    reset_password_with_otp,
    update_user_for_tenant,
)
from app.core.security import get_current_user, require_role


router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.get("/capabilities")
def auth_capabilities():
    return get_auth_capabilities()


@router.post("/login")
def auth_login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    result = login(
        payload,
        db,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    user = result.get("user")

    create_audit_log(
        db=db,
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
        event_type="LOGIN_SUCCESS",
        event_category="AUTH",
        description=f"User logged in: {user['email']}",
        resource_type="user",
        resource_id=user["user_id"],
        request=request,
        metadata={
            "email": user["email"],
            "role": user["role"],
        },
    )

    return result


@router.post("/refresh")
def auth_refresh(
    payload: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    result = refresh_login(payload, db)
    user = result.get("user")
    create_audit_log(
        db=db,
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
        event_type="SESSION_REFRESHED",
        event_category="AUTH",
        description=f"Session refreshed for {user['email']}",
        resource_type="session",
        resource_id=result.get("session_id"),
        request=request,
        metadata={},
    )
    return result


@router.post("/register")
def auth_register(
    payload: RegisterWorkspaceRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    result = register_workspace(payload, db)
    user = result.get("user")
    tenant = result.get("tenant", {})

    create_audit_log(
        db=db,
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
        event_type="WORKSPACE_REGISTERED",
        event_category="AUTH",
        description=f"Workspace registered: {tenant.get('tenant_name', user['tenant_name'])}",
        resource_type="tenant",
        resource_id=user["tenant_id"],
        request=request,
        metadata={
            "email": user["email"],
            "plan_id": tenant.get("plan_id"),
            "billing_status": tenant.get("billing_status"),
        },
    )

    return result


@router.post("/forgot-password/request-otp")
def auth_request_password_reset_otp(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    return request_password_reset_otp(payload, db)


@router.post("/forgot-password/request-link")
def auth_request_password_reset_link(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    return request_password_reset_link(payload, db)


@router.post("/forgot-password/reset")
def auth_reset_password_with_otp(
    payload: ResetPasswordOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    result = reset_password_with_otp(payload, db)
    create_audit_log(
        db=db,
        tenant_id="SYSTEM",
        user_id=None,
        event_type="PASSWORD_RESET_COMPLETED",
        event_category="AUTH",
        description="Password reset completed with OTP flow",
        resource_type="auth",
        resource_id=payload.challenge_id,
        request=request,
        metadata={"challenge_id": payload.challenge_id},
    )
    return result


@router.post("/forgot-password/reset-link")
def auth_reset_password_with_link(
    payload: ResetPasswordLinkRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    result = reset_password_with_link(payload, db)
    create_audit_log(
        db=db,
        tenant_id="SYSTEM",
        user_id=None,
        event_type="PASSWORD_RESET_LINK_COMPLETED",
        event_category="AUTH",
        description="Password reset completed with link flow",
        resource_type="auth",
        resource_id="password-reset-link",
        request=request,
        metadata={},
    )
    return result


@router.get("/me")
def auth_me(current_user: dict = Depends(get_current_user)):
    return {
        "success": True,
        "data": current_user,
    }


@router.get("/users")
def auth_users(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_users_for_tenant(current_user, db)


@router.get("/sessions")
def auth_sessions(current_user: dict = Depends(get_current_user)):
    return get_user_sessions(current_user)


@router.post("/logout")
def auth_logout(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = logout_current_session(current_user, current_user.get("session_id"))
    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="LOGOUT",
        event_category="AUTH",
        description=f"User logged out: {current_user['email']}",
        resource_type="session",
        resource_id=current_user.get("session_id"),
        request=request,
        metadata={"revoked": result.get("revoked", False)},
    )
    return result


@router.post("/logout-all")
def auth_logout_all(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = logout_all_sessions(current_user)
    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="LOGOUT_ALL",
        event_category="AUTH",
        description=f"All sessions revoked for {current_user['email']}",
        resource_type="user",
        resource_id=current_user["user_id"],
        request=request,
        metadata={"revoked_count": result.get("revoked_count", 0)},
    )
    return result


@router.post("/sessions/{session_id}/revoke")
def auth_revoke_named_session(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = logout_named_session(current_user, session_id)
    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="SESSION_REVOKED",
        event_category="AUTH",
        description=f"Session revoked for {current_user['email']}",
        resource_type="session",
        resource_id=session_id,
        request=request,
        metadata={},
    )
    return result


@router.post("/change-password")
def auth_change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = change_password(payload, current_user, current_user.get("session_id"), db)
    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="PASSWORD_CHANGED",
        event_category="AUTH",
        description=f"Password changed for {current_user['email']}",
        resource_type="user",
        resource_id=current_user["user_id"],
        request=request,
        metadata={"revoke_other_sessions": payload.revoke_other_sessions},
    )
    return result


@router.post("/users")
def auth_create_user(
    payload: CreateUserRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = create_user_for_tenant(payload, current_user, db)
    created_user = result["data"]

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="USER_CREATED",
        event_category="ADMIN",
        description=f"User created: {created_user['email']}",
        resource_type="user",
        resource_id=created_user["user_id"],
        request=request,
        metadata={
            "created_user_email": created_user["email"],
            "created_user_role": created_user["role"],
            "modules": created_user["allowed_modules"],
        },
    )

    return result


@router.patch("/users/{user_id}")
def auth_update_user(
    user_id: str,
    payload: UpdateUserRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = update_user_for_tenant(user_id, payload, current_user, db)
    updated_user = result["data"]

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="USER_UPDATED",
        event_category="ADMIN",
        description=f"User updated: {updated_user['email']}",
        resource_type="user",
        resource_id=updated_user["user_id"],
        request=request,
        metadata={
            "updated_user_email": updated_user["email"],
            "updated_user_role": updated_user["role"],
            "modules": updated_user["allowed_modules"],
        },
    )

    return result


@router.delete("/users/{user_id}")
def auth_delete_user(
    user_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = delete_user_for_tenant(user_id, current_user, db)

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="USER_DELETED",
        event_category="ADMIN",
        description=f"User deleted: {user_id}",
        resource_type="user",
        resource_id=user_id,
        request=request,
        metadata={},
    )

    return result


@router.post("/invites")
def auth_create_invite(
    payload: InviteUserRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = create_user_invite(payload, current_user, db)
    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="USER_INVITED",
        event_category="AUTH",
        description=f"User invite created for {payload.email}",
        resource_type="invite",
        resource_id=result["invite_id"],
        request=request,
        metadata={"role": payload.role},
    )
    return result


@router.get("/invites/{token}")
def auth_get_invite(token: str):
    return get_user_invite(token)


@router.post("/invites/{token}/accept")
def auth_accept_invite(
    token: str,
    payload: AcceptInviteRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    result = accept_user_invite(token, payload, db)
    user = result["user"]
    create_audit_log(
        db=db,
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
        event_type="INVITE_ACCEPTED",
        event_category="AUTH",
        description=f"Invite accepted for {user['email']}",
        resource_type="user",
        resource_id=user["user_id"],
        request=request,
        metadata={"email": user["email"]},
    )
    return result


@router.get("/governance")
def auth_governance(
    current_user: dict = Depends(require_role(["SUPER_ADMIN"])),
):
    from app.services.auth_governance_settings_service import get_auth_governance_settings

    return {"success": True, "data": get_auth_governance_settings()}


@router.patch("/governance")
def auth_update_governance(
    payload: dict,
    current_user: dict = Depends(require_role(["SUPER_ADMIN"])),
):
    from app.services.auth_governance_settings_service import update_auth_governance_settings

    return {"success": True, "data": update_auth_governance_settings(payload)}
