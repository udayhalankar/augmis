import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.core.database import SessionLocal


CHALLENGE_TABLE_NAME = "runtime_auth_challenges"
CHALLENGE_STORE_NAME = "default"
LEGACY_CHALLENGE_FILE = (
    Path(__file__).resolve().parents[2] / "storage" / "runtime_auth_challenges.json"
)
OTP_TTL_MINUTES = 10


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _empty_store() -> dict:
    return {"challenges": {}}


def _normalize_store(value) -> dict:
    if isinstance(value, dict):
        return value if isinstance(value.get("challenges"), dict) else _empty_store()
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else _empty_store()
        except json.JSONDecodeError:
            return _empty_store()
    return _empty_store()


def _load_legacy_store() -> dict | None:
    if not LEGACY_CHALLENGE_FILE.exists():
        return None

    try:
        payload = json.loads(LEGACY_CHALLENGE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    return payload if isinstance(payload, dict) else None


def _load_store_from_db() -> dict | None:
    db = SessionLocal()
    try:
        try:
            row = db.execute(
                text(
                    f"""
                    SELECT store_json
                    FROM {CHALLENGE_TABLE_NAME}
                    WHERE store_name = :store_name
                    """
                ),
                {"store_name": CHALLENGE_STORE_NAME},
            ).scalar_one_or_none()
        except ProgrammingError:
            db.rollback()
            return None
        return _normalize_store(row) if row is not None else None
    finally:
        db.close()


def _save_store_to_db(data: dict) -> None:
    db = SessionLocal()
    try:
        db.execute(
            text(
                f"""
                INSERT INTO {CHALLENGE_TABLE_NAME} (store_name, store_json, updated_at)
                VALUES (:store_name, CAST(:store_json AS JSONB), now())
                ON CONFLICT (store_name)
                DO UPDATE SET store_json = EXCLUDED.store_json, updated_at = now()
                """
            ),
            {
                "store_name": CHALLENGE_STORE_NAME,
                "store_json": json.dumps(data, indent=2, ensure_ascii=True),
            },
        )
        db.commit()
    except ProgrammingError:
        db.rollback()
        raise
    finally:
        db.close()


def _load_store() -> dict:
    store = _load_store_from_db()
    if store is not None:
        return store

    legacy_store = _load_legacy_store()
    if legacy_store is None:
        return _empty_store()

    try:
        _save_store_to_db(legacy_store)
    except ProgrammingError:
        return legacy_store

    return legacy_store


def _save_store(data: dict) -> None:
    payload = data if isinstance(data, dict) else _empty_store()
    try:
        _save_store_to_db(payload)
    except ProgrammingError:
        LEGACY_CHALLENGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        LEGACY_CHALLENGE_FILE.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )


def _hash_otp(otp: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{otp}".encode("utf-8")).hexdigest()


def purge_expired_challenges() -> None:
    store = _load_store()
    now = _utcnow()
    changed = False

    for challenge_id, challenge in list(store.get("challenges", {}).items()):
        expires_at = challenge.get("expires_at")
        used_at = challenge.get("used_at")
        if used_at:
            del store["challenges"][challenge_id]
            changed = True
            continue
        if expires_at:
            expiry = datetime.fromisoformat(expires_at)
            if expiry <= now:
                del store["challenges"][challenge_id]
                changed = True

    if changed:
        _save_store(store)


def create_otp_challenge(kind: str, email: str, metadata: dict | None = None) -> dict:
    purge_expired_challenges()
    store = _load_store()

    challenge_id = f"CHAL-{secrets.token_hex(6).upper()}"
    otp = f"{secrets.randbelow(1_000_000):06d}"
    salt = secrets.token_hex(8)
    expires_at = _utcnow() + timedelta(minutes=OTP_TTL_MINUTES)

    store.setdefault("challenges", {})[challenge_id] = {
        "kind": kind,
        "email": email.lower().strip(),
        "otp_hash": _hash_otp(otp, salt),
        "salt": salt,
        "expires_at": expires_at.isoformat(),
        "used_at": None,
        "metadata": metadata or {},
        "attempts": 0,
        "created_at": _utcnow().isoformat(),
    }
    _save_store(store)

    return {
        "challenge_id": challenge_id,
        "otp_preview": otp,
        "expires_at": expires_at.isoformat(),
        "delivery_mode": "onscreen_demo",
    }


def verify_otp_challenge(challenge_id: str, otp: str, expected_kind: str) -> dict:
    purge_expired_challenges()
    store = _load_store()
    challenge = store.get("challenges", {}).get(challenge_id)
    if not challenge:
        raise ValueError("OTP challenge not found or expired")

    if challenge.get("kind") != expected_kind:
        raise ValueError("OTP challenge kind mismatch")

    if challenge.get("used_at"):
        raise ValueError("OTP challenge already used")

    expiry = datetime.fromisoformat(challenge["expires_at"])
    if expiry <= _utcnow():
        del store["challenges"][challenge_id]
        _save_store(store)
        raise ValueError("OTP challenge expired")

    expected_hash = challenge.get("otp_hash")
    actual_hash = _hash_otp(otp, challenge.get("salt", ""))
    challenge["attempts"] = int(challenge.get("attempts", 0)) + 1

    if actual_hash != expected_hash:
        _save_store(store)
        raise ValueError("Invalid OTP")

    challenge["used_at"] = _utcnow().isoformat()
    _save_store(store)
    return challenge
