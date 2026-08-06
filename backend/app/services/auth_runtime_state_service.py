import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.core.database import SessionLocal


STATE_TABLE_NAME = "runtime_auth_state"
STATE_ROW_NAME = "default"
LEGACY_STATE_FILE = Path(__file__).resolve().parents[2] / "storage" / "runtime_auth_state.json"


def _empty_state() -> dict:
    return {
        "login_failures": {},
        "otp_requests": {},
        "sessions": {},
        "invites": {},
        "email_log": [],
    }


def utcnow_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _normalize_state(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else _empty_state()
        except json.JSONDecodeError:
            return _empty_state()
    return _empty_state()


def _load_legacy_state() -> dict | None:
    if not LEGACY_STATE_FILE.exists():
        return None

    try:
        payload = json.loads(LEGACY_STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    return payload if isinstance(payload, dict) else None


def _load_state_from_db() -> dict | None:
    db = SessionLocal()
    try:
        try:
            row = db.execute(
                text(
                    f"""
                    SELECT state_json
                    FROM {STATE_TABLE_NAME}
                    WHERE state_name = :state_name
                    """
                ),
                {"state_name": STATE_ROW_NAME},
            ).scalar_one_or_none()
        except ProgrammingError:
            db.rollback()
            return None
        return _normalize_state(row) if row is not None else None
    finally:
        db.close()


def load_auth_runtime_state() -> dict:
    state = _load_state_from_db()
    if state is not None:
        return state

    legacy_state = _load_legacy_state()
    if legacy_state is None:
        return _empty_state()

    save_auth_runtime_state(legacy_state)
    return legacy_state


def save_auth_runtime_state(data: dict) -> None:
    payload = data if isinstance(data, dict) else _empty_state()

    db = SessionLocal()
    try:
        try:
            db.execute(
                text(
                    f"""
                    INSERT INTO {STATE_TABLE_NAME} (state_name, state_json, updated_at)
                    VALUES (:state_name, CAST(:state_json AS JSONB), now())
                    ON CONFLICT (state_name)
                    DO UPDATE SET state_json = EXCLUDED.state_json, updated_at = now()
                    """
                ),
                {
                    "state_name": STATE_ROW_NAME,
                    "state_json": json.dumps(payload, indent=2, ensure_ascii=True),
                },
            )
            db.commit()
        except ProgrammingError:
            db.rollback()
            LEGACY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            LEGACY_STATE_FILE.write_text(
                json.dumps(payload, indent=2, ensure_ascii=True),
                encoding="utf-8",
            )
    finally:
        db.close()
