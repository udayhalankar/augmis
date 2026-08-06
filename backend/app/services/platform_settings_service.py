import json
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings


PLATFORM_SETTINGS_PATH = (
    Path(__file__).resolve().parents[2] / "storage" / "runtime_platform_settings.json"
)

SECRET_KEYS = {"openai_api_key", "database_url"}
RESTART_REQUIRED_KEYS = {
    "openai_api_key",
    "openai_model",
    "openai_embedding_model",
    "database_url",
}
CONFIG_FIELD_ORDER = [
    "openai_api_key",
    "openai_model",
    "openai_embedding_model",
    "database_url",
    "ocr_tesseract_cmd",
]
FIELD_LABELS = {
    "openai_api_key": "OpenAI API Key",
    "openai_model": "OpenAI Model",
    "openai_embedding_model": "OpenAI Embedding Model",
    "database_url": "Database URL",
    "ocr_tesseract_cmd": "OCR Tesseract Command",
}


def _read_runtime_file() -> dict:
    if not PLATFORM_SETTINGS_PATH.exists():
        return {}

    try:
        payload = json.loads(PLATFORM_SETTINGS_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_runtime_file(payload: dict) -> None:
    PLATFORM_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLATFORM_SETTINGS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def _mask_secret(value: str | None) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if len(raw) <= 8:
        return "*" * len(raw)
    return f"{raw[:4]}{'*' * max(len(raw) - 8, 4)}{raw[-4:]}"


def _normalize_optional_string(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _get_live_values() -> dict:
    return {
        "openai_api_key": _normalize_optional_string(settings.OPENAI_API_KEY),
        "openai_model": _normalize_optional_string(settings.OPENAI_MODEL),
        "openai_embedding_model": _normalize_optional_string(settings.OPENAI_EMBEDDING_MODEL),
        "database_url": _normalize_optional_string(settings.DATABASE_URL),
        "ocr_tesseract_cmd": _normalize_optional_string(settings.OCR_TESSERACT_CMD),
    }


def get_effective_platform_settings() -> dict:
    live_values = _get_live_values()
    overrides = _read_runtime_file()
    effective = dict(live_values)
    for key in CONFIG_FIELD_ORDER:
        if key in overrides:
            effective[key] = _normalize_optional_string(overrides.get(key))
    return effective


def _build_field_metadata(field_key: str, live_value: str | None, effective_value: str | None, has_override: bool) -> dict:
    secret = field_key in SECRET_KEYS
    restart_required = field_key in RESTART_REQUIRED_KEYS
    pending_restart = restart_required and effective_value != live_value
    return {
        "key": field_key,
        "label": FIELD_LABELS[field_key],
        "is_secret": secret,
        "restart_required": restart_required,
        "pending_restart": pending_restart,
        "applies_live": not restart_required,
        "configured": bool(effective_value),
        "value": None if secret else effective_value,
        "masked_value": _mask_secret(effective_value) if secret else None,
        "live_value": None if secret else live_value,
        "has_override": has_override,
    }


def get_platform_settings_snapshot() -> dict:
    live_values = _get_live_values()
    overrides = _read_runtime_file()
    effective = get_effective_platform_settings()
    fields = [
        _build_field_metadata(
            field_key=field_key,
            live_value=live_values.get(field_key),
            effective_value=effective.get(field_key),
            has_override=field_key in overrides,
        )
        for field_key in CONFIG_FIELD_ORDER
    ]
    return {
        "fields": fields,
        "restart_required": any(field["pending_restart"] for field in fields),
        "deprecated": {
            "datasource_path": {
                "key": "datasource_path",
                "label": "Datasource Path",
                "configured": bool(str(settings.DATASOURCE_PATH or "").strip()),
                "message": (
                    "DATASOURCE_PATH is a legacy local-mount health hint and is not the source of truth "
                    "for tenant repositories in production. Repository source_path and connector config drive live behavior."
                ),
                "can_remove_from_env": True,
            }
        },
    }


def validate_platform_settings_update(payload: dict) -> dict[str, str]:
    errors: dict[str, str] = {}

    if "openai_api_key" in payload:
        value = _normalize_optional_string(payload.get("openai_api_key"))
        if value and not value.startswith("sk-"):
            errors["openai_api_key"] = "OpenAI API key must start with 'sk-'."

    if "openai_model" in payload:
        value = _normalize_optional_string(payload.get("openai_model"))
        if not value:
            errors["openai_model"] = "OpenAI model is required."

    if "openai_embedding_model" in payload:
        value = _normalize_optional_string(payload.get("openai_embedding_model"))
        if not value:
            errors["openai_embedding_model"] = "OpenAI embedding model is required."

    if "database_url" in payload:
        value = _normalize_optional_string(payload.get("database_url"))
        parsed = urlparse(value or "")
        if not value:
            errors["database_url"] = "Database URL is required."
        elif not parsed.scheme or not parsed.netloc:
            errors["database_url"] = "Database URL must be a valid absolute connection string."

    if "ocr_tesseract_cmd" in payload:
        value = _normalize_optional_string(payload.get("ocr_tesseract_cmd"))
        if value and not (value.startswith("/") or ":" in value):
            errors["ocr_tesseract_cmd"] = "OCR Tesseract command must be an absolute Linux or Windows path."

    return errors


def update_platform_settings(payload: dict) -> dict:
    normalized_payload = {
        key: _normalize_optional_string(value)
        for key, value in payload.items()
        if key in CONFIG_FIELD_ORDER and value is not None
    }
    errors = validate_platform_settings_update(normalized_payload)
    if errors:
        raise ValueError(json.dumps(errors))

    current = _read_runtime_file()
    current.update(normalized_payload)
    _write_runtime_file(current)

    if "ocr_tesseract_cmd" in normalized_payload:
        settings.OCR_TESSERACT_CMD = normalized_payload.get("ocr_tesseract_cmd")

    return get_platform_settings_snapshot()
