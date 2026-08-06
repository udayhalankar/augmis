from typing import Optional

from pydantic import BaseModel


class TenantCreateRequest(BaseModel):
    tenant_name: str
    plan_id: str = "PLAN-STARTER"


class TenantUpdatePlanRequest(BaseModel):
    plan_id: str


class UsageUpdateRequest(BaseModel):
    users_count: Optional[int] = None
    documents_count: Optional[int] = None
    storage_used_mb: Optional[float] = None
    ai_tokens_used: Optional[int] = None
