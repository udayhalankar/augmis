import json
from pathlib import Path

from app.core.config import settings


RUNTIME_SETTINGS_PATH = (
    Path(__file__).resolve().parents[2] / "storage" / "runtime_chunking_settings.json"
)


def _default_settings() -> dict:
    return {
        "max_chars": int(settings.CHUNK_MAX_CHARS),
        "overlap_chars": int(settings.CHUNK_OVERLAP_CHARS),
    }


def _read_runtime_file() -> dict:
    if not RUNTIME_SETTINGS_PATH.exists():
        return {}

    try:
        data = json.loads(RUNTIME_SETTINGS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_chunking_settings() -> dict:
    resolved = _default_settings()
    resolved.update(_read_runtime_file())

    max_chars = max(200, int(resolved.get("max_chars", settings.CHUNK_MAX_CHARS)))
    overlap_chars = max(0, int(resolved.get("overlap_chars", settings.CHUNK_OVERLAP_CHARS)))

    if overlap_chars >= max_chars:
        overlap_chars = max(0, max_chars // 5)

    return {
        "max_chars": max_chars,
        "overlap_chars": overlap_chars,
        "persistent": True,
    }


def update_chunking_settings(max_chars: int, overlap_chars: int) -> dict:
    payload = {
        "max_chars": max_chars,
        "overlap_chars": overlap_chars,
    }
    RUNTIME_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_SETTINGS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return get_chunking_settings()
