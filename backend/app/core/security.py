from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from app.core.request_context import update_request_context
from app.services.auth_service import (
    SECRET_KEY,
    ALGORITHM,
    find_user_by_email,
    sanitize_user,
)
from app.services.auth_runtime_session_service import validate_session
from app.services.subscription_service import validate_module_entitlement


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("email")
        token_type = payload.get("type")
        session_id = payload.get("sid")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        if token_type and token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if session_id and not validate_session(session_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is no longer active",
        )

    user = find_user_by_email(email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user_status = user.get("status") if isinstance(user, dict) else getattr(user, "status", None)

    if user_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    safe_user = sanitize_user(user)
    if session_id:
        safe_user["session_id"] = session_id
    update_request_context(
        tenant_id=safe_user.get("tenant_id"),
        user_id=safe_user.get("user_id"),
        user_email=safe_user.get("email"),
    )
    return safe_user


def require_role(allowed_roles: list[str]) -> Callable:
    def checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role access",
            )

        return current_user

    return checker


def require_permission(permission: str) -> Callable:
    def checker(current_user: dict = Depends(get_current_user)):
        permissions = current_user.get("permissions", [])

        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )

        return current_user

    return checker


def require_module(module_name: str) -> Callable:
    def checker(current_user: dict = Depends(get_current_user)):
        allowed_modules = current_user.get("allowed_modules", [])

        if module_name not in allowed_modules:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Module not allowed: {module_name}",
            )

        return current_user

    return checker


def require_module_and_permission(module_name: str, permission: str) -> Callable:
    def checker(current_user: dict = Depends(get_current_user)):
        allowed_modules = current_user.get("allowed_modules", [])
        permissions = current_user.get("permissions", [])

        if module_name not in allowed_modules:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Module not allowed: {module_name}",
            )

        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )

        return current_user

    return checker


def require_saas_access(module_name: str, permission: str) -> Callable:
    def checker(current_user: dict = Depends(get_current_user)):
        allowed_modules = current_user.get("allowed_modules", [])
        permissions = current_user.get("permissions", [])

        if module_name not in allowed_modules:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Module not allowed for user: {module_name}",
            )

        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )

        validate_module_entitlement(current_user["tenant_id"], module_name)

        return current_user

    return checker


def require_user_email(required_email: str) -> Callable:
    def checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("email", "").lower() != required_email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Only {required_email} can access this resource",
            )

        return current_user

    return checker
