import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status

from app.db_models import User
from app.services.auth_service import find_user_by_email, hash_password, sanitize_user
from app.services.auth_governance_settings_service import get_auth_governance_settings
from app.services.auth_runtime_email_service import send_auth_email
from app.services.auth_runtime_state_service import (
    load_auth_runtime_state,
    save_auth_runtime_state,
    utcnow_iso,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_invite(current_user: dict, payload: dict, db) -> dict:
    if current_user["role"] not in ["SUPER_ADMIN", "TENANT_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create invites",
        )

    existing = find_user_by_email(payload["email"], db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User email already exists",
        )

    governance = get_auth_governance_settings()
    expiry_hours = int(governance["security_policy"]["invite_expiry_hours"])
    expires_at = (_utcnow() + timedelta(hours=expiry_hours)).isoformat()
    invite_token = secrets.token_urlsafe(32)
    invite_id = f"INV-{str(uuid4())[:8].upper()}"

    state = load_auth_runtime_state()
    state.setdefault("invites", {})[invite_token] = {
        "invite_id": invite_id,
        "tenant_id": current_user["tenant_id"],
        "tenant_name": current_user.get("tenant_name", ""),
        "email": payload["email"].lower().strip(),
        "role": payload["role"],
        "allowed_modules": payload.get("allowed_modules", []),
        "permissions": payload.get("permissions", []),
        "status": payload.get("status", "ACTIVE"),
        "invited_by": current_user["user_id"],
        "created_at": utcnow_iso(),
        "expires_at": expires_at,
        "accepted_at": None,
    }
    save_auth_runtime_state(state)

    accept_url = f"http://localhost:3000/accept-invite?token={invite_token}"
    email_result = send_auth_email(
        to_email=payload["email"],
        subject="Augmis workspace invitation",
        text_body=f"You were invited to {current_user.get('tenant_name', 'an Augmis workspace')}.\nAccept here: {accept_url}",
        metadata={
            "kind": "invite",
            "invite_id": invite_id,
            "tenant_id": current_user["tenant_id"],
        },
    )

    return {
        "success": True,
        "invite_id": invite_id,
        "invite_token_preview": invite_token,
        "accept_url_preview": accept_url,
        "email_delivery": email_result,
    }


def get_invite(token: str) -> dict:
    state = load_auth_runtime_state()
    invite = state.get("invites", {}).get(token)
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )
    if invite.get("accepted_at"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already accepted",
        )
    if datetime.fromisoformat(invite["expires_at"]) <= _utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired",
        )
    return invite


def accept_invite(token: str, payload: dict, db) -> dict:
    invite = get_invite(token)
    if payload["email"].lower().strip() != invite["email"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite email does not match",
        )

    if find_user_by_email(invite["email"], db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User email already exists",
        )

    user = User(
        user_id=f"USR-{str(uuid4())[:8].upper()}",
        tenant_id=invite["tenant_id"],
        tenant_name=invite.get("tenant_name", ""),
        name=payload["name"].strip(),
        email=invite["email"],
        password_hash=hash_password(payload["password"]),
        role=invite["role"],
        status=invite["status"],
        allowed_modules=invite.get("allowed_modules", []),
        permissions=invite.get("permissions", []),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    state = load_auth_runtime_state()
    state["invites"][token]["accepted_at"] = utcnow_iso()
    save_auth_runtime_state(state)

    return {
        "success": True,
        "user": sanitize_user(user),
    }
