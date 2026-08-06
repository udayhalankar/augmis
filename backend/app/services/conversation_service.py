from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db_models import ChatMessage, ChatSession
from app.models.conversation_models import AddMessageRequest, ChatSessionCreate


def serialize_message(message: ChatMessage):
    return {
        "id": message.message_id,
        "role": message.role,
        "content": message.content,
        "sources": message.sources or [],
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def serialize_session(session: ChatSession, messages: list[ChatMessage] | None = None):
    return {
        "id": session.session_id,
        "tenant_id": session.tenant_id,
        "user_id": session.user_id,
        "title": session.title,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "messages": [serialize_message(message) for message in messages] if messages is not None else [],
    }


def create_session(payload: ChatSessionCreate, current_user: dict, db: Session):
    session = ChatSession(
        session_id=f"CHAT-{str(uuid4())[:12].upper()}",
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        title=payload.title or "New Conversation",
        updated_at=datetime.utcnow(),
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "success": True,
        "data": serialize_session(session),
    }


def list_sessions(current_user: dict, db: Session):
    sessions = (
        db.query(ChatSession)
        .filter(
            ChatSession.tenant_id == current_user["tenant_id"],
            ChatSession.user_id == current_user["user_id"],
        )
        .order_by(desc(ChatSession.updated_at))
        .all()
    )

    data = []

    for session in sessions:
        message_count = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.session_id)
            .count()
        )

        data.append(
            {
                "id": session.session_id,
                "title": session.title,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                "message_count": message_count,
            }
        )

    return {
        "success": True,
        "data": data,
    }


def get_session(session_id: str, current_user: dict, db: Session):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.session_id == session_id,
            ChatSession.tenant_id == current_user["tenant_id"],
            ChatSession.user_id == current_user["user_id"],
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation session not found",
        )

    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session_id,
            ChatMessage.tenant_id == current_user["tenant_id"],
            ChatMessage.user_id == current_user["user_id"],
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return {
        "success": True,
        "data": serialize_session(session, messages),
    }


def add_message(
    session_id: str,
    payload: AddMessageRequest,
    current_user: dict,
    db: Session,
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.session_id == session_id,
            ChatSession.tenant_id == current_user["tenant_id"],
            ChatSession.user_id == current_user["user_id"],
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation session not found",
        )

    message = ChatMessage(
        message_id=f"MSG-{str(uuid4())[:12].upper()}",
        session_id=session_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        role=payload.role,
        content=payload.content,
        sources=payload.sources or [],
    )

    db.add(message)

    if session.title == "New Conversation" and payload.role == "user":
        session.title = payload.content[:60]

    session.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(message)

    return {
        "success": True,
        "data": serialize_message(message),
    }


def delete_session(session_id: str, current_user: dict, db: Session):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.session_id == session_id,
            ChatSession.tenant_id == current_user["tenant_id"],
            ChatSession.user_id == current_user["user_id"],
        )
        .first()
    )

    if not session:
        return {
            "success": True,
            "deleted": 0,
        }

    db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.tenant_id == current_user["tenant_id"],
        ChatMessage.user_id == current_user["user_id"],
    ).delete()

    db.delete(session)
    db.commit()

    return {
        "success": True,
        "deleted": 1,
    }


def clear_sessions(current_user: dict, db: Session):
    session_ids = [
        row.session_id
        for row in db.query(ChatSession.session_id)
        .filter(
            ChatSession.tenant_id == current_user["tenant_id"],
            ChatSession.user_id == current_user["user_id"],
        )
        .all()
    ]

    if not session_ids:
        return {
            "success": True,
            "message": "No conversations to clear",
        }

    db.query(ChatMessage).filter(
        ChatMessage.session_id.in_(session_ids),
        ChatMessage.tenant_id == current_user["tenant_id"],
        ChatMessage.user_id == current_user["user_id"],
    ).delete(synchronize_session=False)

    db.query(ChatSession).filter(
        ChatSession.session_id.in_(session_ids),
        ChatSession.tenant_id == current_user["tenant_id"],
        ChatSession.user_id == current_user["user_id"],
    ).delete(synchronize_session=False)

    db.commit()

    return {
        "success": True,
        "message": "User conversations cleared",
    }
