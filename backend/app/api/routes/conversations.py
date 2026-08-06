from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_saas_access
from app.models.conversation_models import AddMessageRequest, ChatSessionCreate
from app.services.conversation_service import (
    add_message,
    clear_sessions,
    create_session,
    delete_session,
    get_session,
    list_sessions,
)


router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


@router.post("")
def create_conversation(
    payload: ChatSessionCreate,
    current_user: dict = Depends(require_saas_access("copilot", "copilot:use")),
    db: Session = Depends(get_db),
):
    return create_session(payload, current_user, db)


@router.get("")
def get_conversations(
    current_user: dict = Depends(require_saas_access("copilot", "copilot:use")),
    db: Session = Depends(get_db),
):
    return list_sessions(current_user, db)


@router.get("/{session_id}")
def get_conversation(
    session_id: str,
    current_user: dict = Depends(require_saas_access("copilot", "copilot:use")),
    db: Session = Depends(get_db),
):
    return get_session(session_id, current_user, db)


@router.post("/{session_id}/messages")
def add_conversation_message(
    session_id: str,
    payload: AddMessageRequest,
    current_user: dict = Depends(require_saas_access("copilot", "copilot:use")),
    db: Session = Depends(get_db),
):
    return add_message(session_id, payload, current_user, db)


@router.delete("/{session_id}")
def remove_conversation(
    session_id: str,
    current_user: dict = Depends(require_saas_access("copilot", "copilot:use")),
    db: Session = Depends(get_db),
):
    return delete_session(session_id, current_user, db)


@router.delete("")
def remove_all_conversations(
    current_user: dict = Depends(require_saas_access("copilot", "copilot:use")),
    db: Session = Depends(get_db),
):
    return clear_sessions(current_user, db)
