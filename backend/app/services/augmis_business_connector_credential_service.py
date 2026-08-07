from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db_models import BusinessDevelopmentConnectorSecret
from app.services.audit_service import create_audit_log
from app.services.augmis_business_web_search_provider import (
    MissingWebSearchApiKeyError,
    WebSearchProviderError,
    get_web_search_provider,
)


SUPPORTED_CREDENTIAL_PROVIDERS = {"tavily", "brave"}
SUPPORTED_CREDENTIAL_TYPE = "api_key"
SECRET_KEY_VERSION = "v1"
ENVIRONMENT_CREDENTIAL_NAMES = {
    "tavily": "TAVILY_API_KEY",
    "brave": "BRAVE_SEARCH_API_KEY",
}


@dataclass
class ResolvedProviderCredential:
    provider: str
    api_key: str | None
    credential_source: str
    masked_hint: str | None = None
    secret_row: BusinessDevelopmentConnectorSecret | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_provider(provider: str) -> str:
    normalized = str(provider or "").strip().lower()
    if normalized not in SUPPORTED_CREDENTIAL_PROVIDERS:
        raise HTTPException(status_code=404, detail="Credential provider not found")
    return normalized


def _masked_hint(value: str | None) -> str | None:
    if not value:
        return None
    trimmed = value.strip()
    if len(trimmed) < 4:
        return "Configured"
    return f"Ends in {trimmed[-4:]}"


def _environment_credential_value(provider: str) -> str | None:
    if provider == "tavily":
        return settings.TAVILY_API_KEY
    if provider == "brave":
        return settings.BRAVE_SEARCH_API_KEY
    return None


def _decode_master_key() -> bytes:
    raw = settings.AUGMIS_CONNECTOR_SECRET_KEY
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="UI secret storage is unavailable until AUGMIS_CONNECTOR_SECRET_KEY is configured.",
        )
    candidate = raw.strip()
    try:
        decoded = base64.urlsafe_b64decode(candidate + "=" * (-len(candidate) % 4))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Connector secret storage key is invalid.",
        ) from exc
    if len(decoded) != 32:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Connector secret storage key is invalid.",
        )
    return decoded


def connector_secret_storage_status() -> dict[str, Any]:
    if not settings.AUGMIS_CONNECTOR_SECRET_KEY:
        return {
            "storage_available": False,
            "storage_message": "UI secret storage is unavailable until AUGMIS_CONNECTOR_SECRET_KEY is configured.",
        }
    try:
        _decode_master_key()
    except HTTPException as exc:
        return {"storage_available": False, "storage_message": str(exc.detail)}
    return {"storage_available": True, "storage_message": None}


def _encrypt_value(plaintext: str) -> str:
    key = _decode_master_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")


def _decrypt_value(ciphertext: str) -> str:
    key = _decode_master_key()
    try:
        payload = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
        nonce = payload[:12]
        encrypted = payload[12:]
        plaintext = AESGCM(key).decrypt(nonce, encrypted, None)
        return plaintext.decode("utf-8")
    except (ValueError, InvalidTag) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored provider credential could not be decrypted.",
        ) from exc


def _serialize_secret_status(
    *,
    provider: str,
    configured: bool,
    credential_source: str,
    masked: str | None = None,
    row: BusinessDevelopmentConnectorSecret | None = None,
) -> dict[str, Any]:
    storage_status = connector_secret_storage_status()
    return {
        "provider": provider,
        "credential_type": SUPPORTED_CREDENTIAL_TYPE,
        "configured": configured,
        "credential_source": credential_source,
        "masked_hint": masked,
        "last_updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
        "last_tested_at": row.last_tested_at.isoformat() if row and row.last_tested_at else None,
        "last_test_status": row.last_test_status if row else None,
        "last_test_error": row.last_test_error if row else None,
        "storage_available": storage_status["storage_available"],
        "storage_message": storage_status["storage_message"],
    }


def _require_secret_row(db: Session, tenant_id: str, provider: str) -> BusinessDevelopmentConnectorSecret | None:
    return (
        db.query(BusinessDevelopmentConnectorSecret)
        .filter(
            BusinessDevelopmentConnectorSecret.tenant_id == tenant_id,
            BusinessDevelopmentConnectorSecret.provider == provider,
            BusinessDevelopmentConnectorSecret.credential_type == SUPPORTED_CREDENTIAL_TYPE,
        )
        .first()
    )


def list_connector_credential_statuses(db: Session, tenant_id: str) -> dict[str, Any]:
    return {
        "success": True,
        "data": [
            get_connector_credential_status(db, tenant_id, provider)["data"]
            for provider in sorted(SUPPORTED_CREDENTIAL_PROVIDERS)
        ],
    }


def get_connector_credential_status(db: Session, tenant_id: str, provider: str) -> dict[str, Any]:
    normalized = _normalize_provider(provider)
    row = _require_secret_row(db, tenant_id, normalized)
    if row:
        return {
            "success": True,
            "data": _serialize_secret_status(
                provider=normalized,
                configured=True,
                credential_source="tenant_secret",
                masked=_masked_hint(row.last_four),
                row=row,
            ),
        }
    env_value = _environment_credential_value(normalized)
    if env_value:
        return {
            "success": True,
            "data": _serialize_secret_status(
                provider=normalized,
                configured=True,
                credential_source="environment",
                masked=_masked_hint(env_value),
            ),
        }
    return {
        "success": True,
        "data": _serialize_secret_status(
            provider=normalized,
            configured=False,
            credential_source="none",
        ),
    }


def resolve_provider_credential(
    db: Session,
    tenant_id: str,
    provider: str,
) -> ResolvedProviderCredential:
    normalized = _normalize_provider(provider)
    row = _require_secret_row(db, tenant_id, normalized)
    if row:
        return ResolvedProviderCredential(
            provider=normalized,
            api_key=_decrypt_value(row.encrypted_value),
            credential_source="tenant_secret",
            masked_hint=_masked_hint(row.last_four),
            secret_row=row,
        )
    env_value = _environment_credential_value(normalized)
    if env_value:
        return ResolvedProviderCredential(
            provider=normalized,
            api_key=env_value,
            credential_source="environment",
            masked_hint=_masked_hint(env_value),
            secret_row=None,
        )
    return ResolvedProviderCredential(
        provider=normalized,
        api_key=None,
        credential_source="none",
        masked_hint=None,
        secret_row=None,
    )


def _safe_provider_error_message(provider: str, error: Exception) -> str:
    message = str(error) or f"{provider.title()} credential test failed."
    return message.replace("\r", " ").replace("\n", " ").strip()


def test_connector_credential(
    db: Session,
    tenant_id: str,
    provider: str,
    current_user: dict,
    transient_api_key: str | None = None,
) -> dict[str, Any]:
    normalized = _normalize_provider(provider)
    api_key = transient_api_key.strip() if transient_api_key else None
    resolved = (
        ResolvedProviderCredential(
            provider=normalized,
            api_key=api_key,
            credential_source="transient",
            masked_hint=_masked_hint(api_key),
            secret_row=None,
        )
        if api_key
        else resolve_provider_credential(db, tenant_id, normalized)
    )
    if not resolved.api_key:
        message = f"{normalized.title()} API key is not configured."
        if resolved.secret_row:
            resolved.secret_row.last_tested_at = _now()
            resolved.secret_row.last_test_status = "failed"
            resolved.secret_row.last_test_error = message
            db.commit()
        return {
            "success": True,
            "data": {
                **get_connector_credential_status(db, tenant_id, normalized)["data"],
                "result": {
                    "success": False,
                    "provider": normalized,
                    "message": message,
                },
            },
        }
    provider_client = get_web_search_provider(normalized, api_key=resolved.api_key)
    try:
        result = provider_client.test_connection()
        if resolved.secret_row:
            resolved.secret_row.last_tested_at = _now()
            resolved.secret_row.last_test_status = "success"
            resolved.secret_row.last_test_error = None
            db.commit()
        create_audit_log(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user["user_id"],
            event_type="TEST",
            event_category="AUGMIS_BUSINESS",
            description=f"Tested {normalized} connector credential",
            resource_type="bd_connector_secret",
            resource_id=resolved.secret_row.id if resolved.secret_row else None,
            metadata={"provider": normalized, "credential_source": resolved.credential_source, "result": "success"},
        )
        return {
            "success": True,
            "data": {
                **get_connector_credential_status(db, tenant_id, normalized)["data"],
                "result": result,
            },
        }
    except (MissingWebSearchApiKeyError, WebSearchProviderError, HTTPException) as exc:
        safe_message = _safe_provider_error_message(normalized, exc)
        if resolved.secret_row:
            resolved.secret_row.last_tested_at = _now()
            resolved.secret_row.last_test_status = "failed"
            resolved.secret_row.last_test_error = safe_message
            db.commit()
        create_audit_log(
            db=db,
            tenant_id=tenant_id,
            user_id=current_user["user_id"],
            event_type="TEST",
            event_category="AUGMIS_BUSINESS",
            description=f"Tested {normalized} connector credential",
            resource_type="bd_connector_secret",
            resource_id=resolved.secret_row.id if resolved.secret_row else None,
            metadata={"provider": normalized, "credential_source": resolved.credential_source, "result": "failed"},
        )
        return {
            "success": True,
            "data": {
                **get_connector_credential_status(db, tenant_id, normalized)["data"],
                "result": {
                    "success": False,
                    "provider": normalized,
                    "message": safe_message,
                },
            },
        }


def save_connector_credential(
    db: Session,
    tenant_id: str,
    provider: str,
    current_user: dict,
    api_key: str,
) -> dict[str, Any]:
    normalized = _normalize_provider(provider)
    encrypted = _encrypt_value(api_key.strip())
    row = _require_secret_row(db, tenant_id, normalized)
    action = "replaced" if row else "created"
    now = _now()
    if row:
        row.encrypted_value = encrypted
        row.key_version = SECRET_KEY_VERSION
        row.status = "active"
        row.last_four = api_key.strip()[-4:] if len(api_key.strip()) >= 4 else None
        row.updated_by = current_user["user_id"]
        row.updated_at = now
        row.last_tested_at = None
        row.last_test_status = None
        row.last_test_error = None
    else:
        row = BusinessDevelopmentConnectorSecret(
            id=f"BD-SEC-{str(uuid4())[:12].upper()}",
            tenant_id=tenant_id,
            connector_id=None,
            provider=normalized,
            credential_type=SUPPORTED_CREDENTIAL_TYPE,
            encrypted_value=encrypted,
            key_version=SECRET_KEY_VERSION,
            status="active",
            last_four=api_key.strip()[-4:] if len(api_key.strip()) >= 4 else None,
            created_by=current_user["user_id"],
            updated_by=current_user["user_id"],
            updated_at=now,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"{action.title()} {normalized} connector credential",
        resource_type="bd_connector_secret",
        resource_id=row.id,
        metadata={"provider": normalized, "action": action},
    )
    return {"success": True, "data": get_connector_credential_status(db, tenant_id, normalized)["data"]}


def delete_connector_credential(
    db: Session,
    tenant_id: str,
    provider: str,
    current_user: dict,
) -> dict[str, Any]:
    normalized = _normalize_provider(provider)
    row = _require_secret_row(db, tenant_id, normalized)
    if not row:
        return {"success": True, "deleted": 0, "data": get_connector_credential_status(db, tenant_id, normalized)["data"]}
    secret_id = row.id
    db.delete(row)
    db.commit()
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="DELETE",
        event_category="AUGMIS_BUSINESS",
        description=f"Cleared {normalized} connector credential",
        resource_type="bd_connector_secret",
        resource_id=secret_id,
        metadata={"provider": normalized, "action": "cleared"},
    )
    return {"success": True, "deleted": 1, "data": get_connector_credential_status(db, tenant_id, normalized)["data"]}
