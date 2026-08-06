from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    user_id: str
    tenant_id: str
    tenant_name: str
    name: str
    email: str
    role: str
    status: str
    allowed_modules: list[str]
    permissions: list[str]


class AuthMeResponse(BaseModel):
    success: bool
    data: CurrentUser


class CreateUserRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "VIEWER"
    allowed_modules: list[str] = []
    permissions: list[str] = []
    status: str = "ACTIVE"


class UpdateUserRequest(BaseModel):
    name: str
    email: str
    role: str = "VIEWER"
    allowed_modules: list[str] = []
    permissions: list[str] = []
    status: str = "ACTIVE"


class RegisterWorkspaceRequest(BaseModel):
    tenant_name: str
    name: str
    email: str
    password: str
    plan_id: str = "PLAN-ENTERPRISE"


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordOtpRequest(BaseModel):
    challenge_id: str
    otp: str
    new_password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    revoke_other_sessions: bool = False


class ResetPasswordLinkRequest(BaseModel):
    token: str
    new_password: str


class InviteUserRequest(BaseModel):
    email: str
    role: str = "VIEWER"
    allowed_modules: list[str] = []
    permissions: list[str] = []
    status: str = "ACTIVE"


class AcceptInviteRequest(BaseModel):
    name: str
    email: str
    password: str
