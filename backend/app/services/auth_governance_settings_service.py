import json
from copy import deepcopy
from pathlib import Path

from app.core.config import settings


AUTH_GOVERNANCE_SETTINGS_FILE = (
    Path(__file__).resolve().parents[2] / "storage" / "runtime_auth_governance_settings.json"
)


def _default_settings() -> dict:
    return {
        "password_policy": {
            "min_length": 10,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_number": True,
            "require_symbol": True,
        },
        "registration_policy": {
            "self_registration_enabled": True,
            "domain_validation_enabled": False,
            "allowed_domains": [],
        },
        "security_policy": {
            "max_failed_attempts": 5,
            "lockout_minutes": 15,
            "login_rate_limit_window_minutes": 15,
            "login_rate_limit_attempts": 10,
            "otp_resend_cooldown_seconds": 60,
            "otp_request_limit_per_hour": 5,
            "invite_expiry_hours": 72,
        },
        "feature_flags": {
            "google_login_enabled": bool(settings.AUTH_GOOGLE_LOGIN_ENABLED),
            "mfa_enabled": bool(settings.AUTH_MFA_ENABLED),
            "self_registration_enabled": True,
            "invite_onboarding_enabled": True,
            "reset_link_enabled": True,
        },
        "provider_config": {
            "email_provider": settings.AUTH_EMAIL_PROVIDER,
            "smtp_host_configured": bool(settings.AUTH_SMTP_HOST),
            "smtp_from_email": settings.AUTH_SMTP_FROM_EMAIL,
            "google_login_env_enabled": bool(settings.AUTH_GOOGLE_LOGIN_ENABLED),
            "mfa_env_enabled": bool(settings.AUTH_MFA_ENABLED),
        },
    }


def get_auth_governance_settings() -> dict:
    defaults = _default_settings()
    if not AUTH_GOVERNANCE_SETTINGS_FILE.exists():
        return defaults

    try:
        current = json.loads(AUTH_GOVERNANCE_SETTINGS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return defaults

    merged = deepcopy(defaults)
    for top_level_key, top_level_value in current.items():
        if isinstance(top_level_value, dict) and isinstance(merged.get(top_level_key), dict):
            merged[top_level_key].update(top_level_value)
        else:
            merged[top_level_key] = top_level_value
    return merged


def update_auth_governance_settings(payload: dict) -> dict:
    current = get_auth_governance_settings()
    next_value = deepcopy(current)

    for top_level_key, top_level_value in payload.items():
        if isinstance(top_level_value, dict) and isinstance(next_value.get(top_level_key), dict):
            next_value[top_level_key].update(top_level_value)
        else:
            next_value[top_level_key] = top_level_value

    AUTH_GOVERNANCE_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTH_GOVERNANCE_SETTINGS_FILE.write_text(
        json.dumps(next_value, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    return next_value
