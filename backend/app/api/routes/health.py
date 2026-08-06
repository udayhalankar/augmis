from fastapi import APIRouter
from importlib import metadata
from pathlib import Path
import platform as py_platform

from sqlalchemy import text

from app.core.database import engine
from app.core.config import settings
from app.services.auth_governance_settings_service import get_auth_governance_settings
from app.services.auth_service import get_auth_capabilities
from app.services.platform_settings_service import get_platform_settings_snapshot
from app.utils.extraction import get_ocr_diagnostics

router = APIRouter(tags=["Health"])


def _package_version(package_name: str) -> str | None:
    try:
        return metadata.version(package_name)
    except Exception:
        return None


def _build_database_health() -> dict:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            vector_enabled = bool(
                connection.execute(
                    text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                ).scalar()
            )

        return {
            "available": True,
            "status": "available",
            "error": None,
            "engine": "sqlalchemy",
            "driver": engine.url.drivername,
            "host": engine.url.host,
            "database": engine.url.database,
            "pgvector_enabled": vector_enabled,
        }
    except Exception as exc:
        return {
            "available": False,
            "status": "unavailable",
            "error": str(exc),
            "engine": "sqlalchemy",
            "driver": engine.url.drivername,
            "host": engine.url.host,
            "database": engine.url.database,
            "pgvector_enabled": False,
        }


def _build_openai_health() -> dict:
    return {
        "available": bool(str(settings.OPENAI_API_KEY or "").strip()),
        "status": "configured" if str(settings.OPENAI_API_KEY or "").strip() else "missing_api_key",
        "error": None if str(settings.OPENAI_API_KEY or "").strip() else "OpenAI API key is not configured.",
        "model": settings.OPENAI_MODEL,
        "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
        "api_key_configured": bool(str(settings.OPENAI_API_KEY or "").strip()),
        "sdk_version": _package_version("openai"),
    }


def _build_security_health() -> dict:
    governance = get_auth_governance_settings()
    capabilities = get_auth_capabilities().get("data", {})
    provider_config = governance.get("provider_config", {})
    feature_flags = governance.get("feature_flags", {})

    return {
        "email_provider": provider_config.get("email_provider"),
        "smtp_host_configured": bool(provider_config.get("smtp_host_configured")),
        "smtp_from_email": provider_config.get("smtp_from_email"),
        "google_login_enabled": bool(feature_flags.get("google_login_enabled")),
        "mfa_enabled": bool(feature_flags.get("mfa_enabled")),
        "self_registration_enabled": bool(feature_flags.get("self_registration_enabled")),
        "invite_onboarding_enabled": bool(feature_flags.get("invite_onboarding_enabled")),
        "reset_link_enabled": bool(feature_flags.get("reset_link_enabled")),
        "capabilities": capabilities,
    }


def _build_platform_diagnostics() -> dict:
    config_snapshot = get_platform_settings_snapshot()
    return {
        "python_version": py_platform.python_version(),
        "runtime_platform": py_platform.platform(),
        "vector_backend": settings.VECTOR_BACKEND,
        "scheduler": {
            "mode": settings.CONNECTOR_SYNC_SCHEDULER_MODE,
            "enabled": bool(settings.CONNECTOR_SYNC_SCHEDULER_ENABLED),
            "interval_minutes": settings.CONNECTOR_SYNC_SCHEDULER_INTERVAL_MINUTES,
            "timezone": settings.CONNECTOR_SYNC_SCHEDULER_TIMEZONE,
        },
        "libraries": {
            "fastapi": _package_version("fastapi"),
            "sqlalchemy": _package_version("sqlalchemy"),
            "psycopg2": _package_version("psycopg2-binary"),
            "pgvector": _package_version("pgvector"),
            "pypdf": _package_version("pypdf"),
            "pytesseract": _package_version("pytesseract"),
            "pypdfium2": _package_version("pypdfium2"),
        },
        "config": {
            "restart_required": config_snapshot.get("restart_required", False),
            "deprecated": config_snapshot.get("deprecated", {}),
        },
    }


@router.get("/health")
def health():
    datasource_path = (settings.DATASOURCE_PATH or "").strip()
    datasource_exists = bool(datasource_path) and Path(datasource_path).exists()
    ocr = get_ocr_diagnostics()
    openai = _build_openai_health()
    database = _build_database_health()
    security = _build_security_health()
    diagnostics = _build_platform_diagnostics()

    return {
        "ok": True,
        "service": "Infomentica DSS Enterprise API",
        "version": "1.2B",
        "model": settings.OPENAI_MODEL,
        "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
        "datasource": {
            "configured_path": datasource_path or None,
            "exists": datasource_exists,
            "status": "legacy_local_mount" if datasource_exists else "not_configured",
            "error": None,
            "deprecated": True,
            "message": (
                "DATASOURCE_PATH is a legacy local-mount health hint and is not required for production repository operation."
            ),
        },
        "ocr": {
            "available": ocr["available"],
            "status": "available" if ocr["available"] else "unavailable",
            "error": ocr["error"],
            "tesseract_cmd": ocr["tesseract_cmd"],
            "configured_tesseract_cmd": ocr["configured_tesseract_cmd"],
            "pytesseract_installed": ocr["pytesseract_installed"],
            "pypdfium2_installed": ocr["pypdfium2_installed"],
        },
        "openai": openai,
        "database": database,
        "security": security,
        "platform_diagnostics": diagnostics,
    }
