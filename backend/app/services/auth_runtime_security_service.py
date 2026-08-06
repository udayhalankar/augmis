from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.services.auth_governance_settings_service import get_auth_governance_settings
from app.services.auth_runtime_state_service import (
    load_auth_runtime_state,
    save_auth_runtime_state,
    utcnow_iso,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _cleanup_attempts(records: list[dict], window_minutes: int) -> list[dict]:
    threshold = _utcnow() - timedelta(minutes=window_minutes)
    return [
        record
        for record in records
        if datetime.fromisoformat(record["timestamp"]) >= threshold
    ]


def assert_login_allowed(email: str, ip_address: str | None) -> None:
    settings = get_auth_governance_settings()
    policy = settings["security_policy"]
    max_failed_attempts = int(policy["max_failed_attempts"])
    lockout_minutes = int(policy["lockout_minutes"])
    rate_window_minutes = int(policy["login_rate_limit_window_minutes"])
    rate_limit_attempts = int(policy["login_rate_limit_attempts"])

    state = load_auth_runtime_state()
    key = email.lower().strip()
    current = state.setdefault("login_failures", {}).setdefault(
        key,
        {"attempts": [], "lockout_until": None, "last_ip": ip_address},
    )

    lockout_until = current.get("lockout_until")
    if lockout_until and datetime.fromisoformat(lockout_until) > _utcnow():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account temporarily locked until {lockout_until}",
        )

    current["attempts"] = _cleanup_attempts(current.get("attempts", []), rate_window_minutes)
    if len(current["attempts"]) >= rate_limit_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    save_auth_runtime_state(state)


def record_failed_login(email: str, ip_address: str | None) -> dict:
    settings = get_auth_governance_settings()
    policy = settings["security_policy"]
    max_failed_attempts = int(policy["max_failed_attempts"])
    lockout_minutes = int(policy["lockout_minutes"])
    rate_window_minutes = int(policy["login_rate_limit_window_minutes"])

    state = load_auth_runtime_state()
    key = email.lower().strip()
    current = state.setdefault("login_failures", {}).setdefault(
        key,
        {"attempts": [], "lockout_until": None, "last_ip": ip_address},
    )
    current["attempts"] = _cleanup_attempts(current.get("attempts", []), rate_window_minutes)
    current["attempts"].append({"timestamp": utcnow_iso(), "ip_address": ip_address})

    if len(current["attempts"]) >= max_failed_attempts:
        lockout_until = (_utcnow() + timedelta(minutes=lockout_minutes)).isoformat()
        current["lockout_until"] = lockout_until
    else:
        lockout_until = None

    save_auth_runtime_state(state)
    return {
        "failed_attempts": len(current["attempts"]),
        "lockout_until": lockout_until,
    }


def clear_failed_login(email: str) -> None:
    state = load_auth_runtime_state()
    key = email.lower().strip()
    if key in state.get("login_failures", {}):
        del state["login_failures"][key]
        save_auth_runtime_state(state)


def assert_otp_request_allowed(email: str) -> dict:
    settings = get_auth_governance_settings()
    policy = settings["security_policy"]
    cooldown_seconds = int(policy["otp_resend_cooldown_seconds"])
    limit_per_hour = int(policy["otp_request_limit_per_hour"])

    state = load_auth_runtime_state()
    key = email.lower().strip()
    current = state.setdefault("otp_requests", {}).setdefault(
        key,
        {"requests": [], "last_requested_at": None},
    )
    threshold = _utcnow() - timedelta(hours=1)
    current["requests"] = [
        item for item in current.get("requests", [])
        if datetime.fromisoformat(item) >= threshold
    ]

    last_requested_at = current.get("last_requested_at")
    if last_requested_at:
        retry_after = cooldown_seconds - int((_utcnow() - datetime.fromisoformat(last_requested_at)).total_seconds())
        if retry_after > 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"OTP recently requested. Retry after {retry_after} seconds.",
            )

    if len(current["requests"]) >= limit_per_hour:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please try again later.",
        )

    save_auth_runtime_state(state)
    return {
        "cooldown_seconds": cooldown_seconds,
        "limit_per_hour": limit_per_hour,
    }


def record_otp_request(email: str) -> None:
    state = load_auth_runtime_state()
    key = email.lower().strip()
    current = state.setdefault("otp_requests", {}).setdefault(
        key,
        {"requests": [], "last_requested_at": None},
    )
    now = utcnow_iso()
    current["requests"].append(now)
    current["last_requested_at"] = now
    save_auth_runtime_state(state)
