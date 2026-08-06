from typing import Optional

from pydantic import BaseModel


class PhaseCreateRequest(BaseModel):
    title: str
    description: str = ""
    status: str = "pending"


class PhaseUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class MilestoneCreateRequest(BaseModel):
    title: str
    description: str = ""
    status: str = "pending"


class MilestoneUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ItemCreateRequest(BaseModel):
    title: str
    description: str = ""
    status: str = "pending"
    item_type: str = "task"
    owner: str = ""
    due_date: str = ""


class ItemUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    item_type: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[str] = None
