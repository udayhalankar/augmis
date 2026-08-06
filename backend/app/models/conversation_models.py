from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime
from uuid import uuid4


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: str
    content: str
    sources: list[dict[str, Any]] = []
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Conversation"


class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = "New Conversation"
    messages: list[ChatMessage] = []
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AddMessageRequest(BaseModel):
    role: str
    content: str
    sources: list[dict[str, Any]] = []