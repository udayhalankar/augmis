import hashlib
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.database import SessionLocal
from app.db_models import AuthSession


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _refresh_lifetime(remember_me: bool) -> timedelta:
    if remember_me:
        return timedelta(days=settings.AUTH_REFRESH_TOKEN_DAYS)
    return timedelta(days=1)


def _absolute_lifetime(remember_me: bool) -> timedelta:
    if remember_me:
        return timedelta(days=settings.AUTH_REMEMBER_ME_SESSION_DAYS)
    return timedelta(hours=settings.AUTH_SESSION_ABSOLUTE_TIMEOUT_HOURS)


@contextmanager
def _session_scope(db=None):
    should_close = db is None
    if db is None:
        db = SessionLocal()
    try:
        yield db
    finally:
        if should_close:
            db.close()


def _serialize_session(session: AuthSession) -> dict:
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "tenant_id": session.tenant_id,
        "email": session.email,
        "remember_me": bool(session.remember_me),
        "refresh_expires_at": session.refresh_expires_at.isoformat(),
        "absolute_expires_at": session.absolute_expires_at.isoformat(),
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "last_seen_at": session.last_seen_at.isoformat() if session.last_seen_at else None,
        "ip_address": session.ip_address,
        "user_agent": session.user_agent,
        "revoked_at": session.revoked_at.isoformat() if session.revoked_at else None,
    }


def _is_expired(session: AuthSession, now: datetime) -> bool:
    if session.revoked_at is not None:
        return True
    if session.refresh_expires_at <= now:
        return True
    if session.absolute_expires_at <= now:
        return True
    if session.last_seen_at + timedelta(minutes=settings.AUTH_SESSION_IDLE_TIMEOUT_MINUTES) <= now:
        return True
    return False


def _revoke_if_expired(session: AuthSession, now: datetime) -> bool:
    if not _is_expired(session, now):
        return False
    if session.revoked_at is None:
        session.revoked_at = now
    return True


def create_auth_session(
    *,
    user: dict,
    remember_me: bool,
    ip_address: str | None,
    user_agent: str | None,
    db=None,
) -> dict:
    now = _utcnow()
    session_id = f"SESS-{secrets.token_hex(8).upper()}"
    refresh_token = secrets.token_urlsafe(48)
    refresh_expires_at = now + _refresh_lifetime(remember_me)
    absolute_expires_at = now + _absolute_lifetime(remember_me)

    with _session_scope(db) as session_db:
        auth_session = AuthSession(
            session_id=session_id,
            user_id=user["user_id"],
            tenant_id=user["tenant_id"],
            email=user["email"],
            remember_me=remember_me,
            refresh_token_hash=_hash_value(refresh_token),
            refresh_expires_at=min(refresh_expires_at, absolute_expires_at),
            absolute_expires_at=absolute_expires_at,
            last_seen_at=now,
            ip_address=ip_address,
            user_agent=user_agent,
            created_by=user["user_id"],
            modified_by=user["user_id"],
        )
        session_db.add(auth_session)
        session_db.commit()

    return {
        "session_id": session_id,
        "refresh_token": refresh_token,
        "refresh_expires_at": min(refresh_expires_at, absolute_expires_at).isoformat(),
        "absolute_expires_at": absolute_expires_at.isoformat(),
    }


def validate_session(session_id: str | None, db=None) -> dict | None:
    if not session_id:
        return None

    now = _utcnow()
    with _session_scope(db) as session_db:
        session = session_db.query(AuthSession).filter(AuthSession.session_id == session_id).first()
        if not session:
            return None
        if _revoke_if_expired(session, now):
            session.modified_at = now
            session_db.commit()
            return None

        session.last_seen_at = now
        session.modified_at = now
        session_db.commit()
        session_db.refresh(session)
        return _serialize_session(session)


def refresh_auth_session(refresh_token: str, db=None) -> dict | None:
    now = _utcnow()
    token_hash = _hash_value(refresh_token)

    with _session_scope(db) as session_db:
        session = (
            session_db.query(AuthSession)
            .filter(AuthSession.refresh_token_hash == token_hash)
            .first()
        )
        if not session:
            return None
        if _revoke_if_expired(session, now):
            session.modified_at = now
            session_db.commit()
            return None

        next_refresh_token = secrets.token_urlsafe(48)
        next_refresh_expiry = min(
            now + _refresh_lifetime(bool(session.remember_me)),
            session.absolute_expires_at,
        )
        session.refresh_token_hash = _hash_value(next_refresh_token)
        session.refresh_expires_at = next_refresh_expiry
        session.last_seen_at = now
        session.modified_at = now
        session_db.commit()
        session_db.refresh(session)

        payload = _serialize_session(session)
        payload["refresh_token"] = next_refresh_token
        return payload


def revoke_session(session_id: str | None, db=None) -> bool:
    if not session_id:
        return False

    now = _utcnow()
    with _session_scope(db) as session_db:
        session = session_db.query(AuthSession).filter(AuthSession.session_id == session_id).first()
        if not session or session.revoked_at is not None:
            return False
        session.revoked_at = now
        session.modified_at = now
        session_db.commit()
        return True


def revoke_all_user_sessions(user_id: str, db=None) -> int:
    now = _utcnow()
    with _session_scope(db) as session_db:
        sessions = (
            session_db.query(AuthSession)
            .filter(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .all()
        )
        count = 0
        for session in sessions:
            session.revoked_at = now
            session.modified_at = now
            count += 1
        session_db.commit()
        return count


def list_user_sessions(user_id: str, db=None) -> list[dict]:
    now = _utcnow()
    with _session_scope(db) as session_db:
        sessions = (
            session_db.query(AuthSession)
            .filter(AuthSession.user_id == user_id)
            .order_by(AuthSession.last_seen_at.desc())
            .all()
        )
        active_sessions: list[dict] = []
        needs_commit = False
        for session in sessions:
            if _revoke_if_expired(session, now):
                session.modified_at = now
                needs_commit = True
                continue
            active_sessions.append(_serialize_session(session))
        if needs_commit:
            session_db.commit()
        return active_sessions
