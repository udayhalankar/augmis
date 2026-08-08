from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db_models import BusinessDevelopmentConnector, BusinessDevelopmentSearchProvider
from app.models.augmis_business_models import (
    AugmisBusinessSearchProviderCreateRequest,
    AugmisBusinessSearchProviderUpdateRequest,
)
from app.services.audit_service import create_audit_log
from app.services.augmis_business_connector_credential_service import (
    get_connector_credential_status,
    resolve_provider_credential,
    test_connector_credential,
)
from app.services.augmis_business_web_fetcher import validate_public_http_url
from app.services.augmis_business_web_search_provider import get_web_search_provider


BUILTIN_PROVIDER_DEFINITIONS = {
    "tavily": {
        "provider_code": "tavily",
        "display_name": "Tavily",
        "provider_type": "builtin",
        "adapter_code": "tavily",
        "description": "Built-in Tavily web-search provider.",
        "enabled": True,
        "credential_type": "api_key",
        "configuration_json": {},
    },
    "brave": {
        "provider_code": "brave",
        "display_name": "Brave",
        "provider_type": "builtin",
        "adapter_code": "brave",
        "description": "Built-in Brave web-search provider.",
        "enabled": True,
        "credential_type": "api_key",
        "configuration_json": {},
    },
}
BUILTIN_ADAPTER_OPTIONS = [
    {"adapter_code": "tavily", "display_name": "Tavily"},
    {"adapter_code": "brave", "display_name": "Brave"},
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_provider_code(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9-]+", "-", str(value or "").strip().lower()).strip("-")
    if len(normalized) < 2:
        raise HTTPException(status_code=400, detail="Provider code must contain at least 2 letters or numbers.")
    return normalized


def _validate_generic_rest_configuration(configuration: dict[str, Any]) -> dict[str, Any]:
    base_search_url = str(configuration.get("base_search_url") or "").strip()
    if not base_search_url:
        raise HTTPException(status_code=400, detail="Base Search URL is required.")
    if not base_search_url.lower().startswith("https://"):
        raise HTTPException(status_code=400, detail="Provider endpoint must use HTTPS.")
    try:
        validate_public_http_url(base_search_url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Provider endpoint is not permitted.") from exc
    http_method = str(configuration.get("http_method", "get") or "get").strip().lower()
    if http_method not in {"get", "post"}:
        raise HTTPException(status_code=400, detail="HTTP method must be GET or POST.")
    authentication_type = str(configuration.get("authentication_type", "api_key_header") or "api_key_header").strip().lower()
    if authentication_type not in {"api_key_header", "bearer_token"}:
        raise HTTPException(status_code=400, detail="Authentication type is invalid.")
    if authentication_type == "api_key_header" and not str(configuration.get("api_key_header_name") or "").strip():
        raise HTTPException(status_code=400, detail="API Key Header Name is required.")
    required_fields = {
        "query_parameter_name": "Query Parameter Name",
        "results_path": "Results Path",
        "title_field": "Title Field",
        "url_field": "URL Field",
        "snippet_field": "Snippet Field",
    }
    for key, label in required_fields.items():
        if not str(configuration.get(key) or "").strip():
            raise HTTPException(status_code=400, detail=f"{label} is required.")
    return {
        "base_search_url": base_search_url,
        "http_method": http_method,
        "authentication_type": authentication_type,
        "api_key_header_name": str(configuration.get("api_key_header_name") or "X-API-Key").strip(),
        "query_parameter_name": str(configuration.get("query_parameter_name") or "").strip(),
        "results_path": str(configuration.get("results_path") or "").strip(),
        "title_field": str(configuration.get("title_field") or "").strip(),
        "url_field": str(configuration.get("url_field") or "").strip(),
        "snippet_field": str(configuration.get("snippet_field") or "").strip(),
        "score_field": str(configuration.get("score_field") or "").strip() or None,
        "published_date_field": str(configuration.get("published_date_field") or "").strip() or None,
        "page_parameter": str(configuration.get("page_parameter") or "").strip() or None,
        "page_size_parameter": str(configuration.get("page_size_parameter") or "").strip() or None,
    }


def ensure_builtin_search_providers(db: Session) -> None:
    for provider_code, definition in BUILTIN_PROVIDER_DEFINITIONS.items():
        row = (
            db.query(BusinessDevelopmentSearchProvider)
            .filter(
                BusinessDevelopmentSearchProvider.tenant_id.is_(None),
                BusinessDevelopmentSearchProvider.provider_code == provider_code,
            )
            .first()
        )
        if row:
            changed = False
            for key, value in definition.items():
                if getattr(row, key) != value:
                    setattr(row, key, value)
                    changed = True
            if changed:
                row.updated_at = _now()
            continue
        db.add(
            BusinessDevelopmentSearchProvider(
                id=f"BD-SPR-{str(uuid4())[:12].upper()}",
                tenant_id=None,
                created_by=None,
                updated_by=None,
                updated_at=_now(),
                **definition,
            )
        )
    db.commit()


def _serialize_provider(db: Session, tenant_id: str, row: BusinessDevelopmentSearchProvider) -> dict[str, Any]:
    credential_status = get_connector_credential_status(db, tenant_id, row.provider_code)["data"]
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "provider_code": row.provider_code,
        "display_name": row.display_name,
        "provider_type": row.provider_type,
        "adapter_code": row.adapter_code,
        "description": row.description,
        "enabled": row.enabled,
        "credential_type": row.credential_type,
        "configuration_json": row.configuration_json or {},
        "credential_configured": credential_status["configured"],
        "credential_source": credential_status["credential_source"],
        "connection_status": credential_status.get("last_test_status") or "not_tested",
        "last_tested_at": credential_status.get("last_tested_at"),
        "last_test_error": credential_status.get("last_test_error"),
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _visible_provider_query(db: Session, tenant_id: str):
    ensure_builtin_search_providers(db)
    return db.query(BusinessDevelopmentSearchProvider).filter(
        (BusinessDevelopmentSearchProvider.tenant_id.is_(None))
        | (BusinessDevelopmentSearchProvider.tenant_id == tenant_id)
    )


def _require_search_provider(db: Session, tenant_id: str, provider_id: str) -> BusinessDevelopmentSearchProvider:
    row = (
        _visible_provider_query(db, tenant_id)
        .filter(BusinessDevelopmentSearchProvider.id == provider_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Search provider not found.")
    return row


def resolve_search_provider_by_code(db: Session, tenant_id: str, provider_code: str) -> BusinessDevelopmentSearchProvider:
    normalized = _normalize_provider_code(provider_code)
    row = (
        _visible_provider_query(db, tenant_id)
        .filter(BusinessDevelopmentSearchProvider.provider_code == normalized)
        .order_by(BusinessDevelopmentSearchProvider.tenant_id.desc().nulls_last())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Search provider not found.")
    if not row.enabled:
        raise HTTPException(status_code=409, detail="Provider is disabled.")
    return row


def list_search_providers(db: Session, tenant_id: str) -> dict[str, Any]:
    rows = (
        _visible_provider_query(db, tenant_id)
        .order_by(BusinessDevelopmentSearchProvider.tenant_id.asc().nulls_first(), BusinessDevelopmentSearchProvider.display_name.asc())
        .all()
    )
    return {
        "success": True,
        "data": [_serialize_provider(db, tenant_id, row) for row in rows],
        "options": {
            "provider_type_options": [
                {"value": "generic_rest", "label": "Generic REST Search API"},
            ],
            "builtin_adapter_options": BUILTIN_ADAPTER_OPTIONS,
        },
    }


def get_search_provider(db: Session, tenant_id: str, provider_id: str) -> dict[str, Any]:
    row = _require_search_provider(db, tenant_id, provider_id)
    return {"success": True, "data": _serialize_provider(db, tenant_id, row)}


def create_search_provider(
    db: Session,
    tenant_id: str,
    current_user: dict,
    payload: AugmisBusinessSearchProviderCreateRequest,
) -> dict[str, Any]:
    provider_code = _normalize_provider_code(payload.provider_code)
    if payload.provider_type != "generic_rest":
        raise HTTPException(status_code=400, detail="Only Generic REST Search API providers can be added from the UI.")
    existing = (
        db.query(BusinessDevelopmentSearchProvider)
        .filter(
            BusinessDevelopmentSearchProvider.tenant_id == tenant_id,
            BusinessDevelopmentSearchProvider.provider_code == provider_code,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Provider code already exists.")
    configuration = _validate_generic_rest_configuration(payload.configuration_json)
    row = BusinessDevelopmentSearchProvider(
        id=f"BD-SPR-{str(uuid4())[:12].upper()}",
        tenant_id=tenant_id,
        provider_code=provider_code,
        display_name=payload.display_name.strip(),
        provider_type="generic_rest",
        adapter_code=None,
        description=payload.description,
        enabled=payload.enabled,
        credential_type=payload.credential_type,
        configuration_json=configuration,
        created_by=current_user["user_id"],
        updated_by=current_user["user_id"],
        updated_at=_now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="CREATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Created search provider {row.display_name}",
        resource_type="bd_search_provider",
        resource_id=row.id,
        metadata={"provider_code": row.provider_code, "provider_type": row.provider_type},
    )
    return {"success": True, "data": _serialize_provider(db, tenant_id, row)}


def update_search_provider(
    db: Session,
    tenant_id: str,
    provider_id: str,
    current_user: dict,
    payload: AugmisBusinessSearchProviderUpdateRequest,
) -> dict[str, Any]:
    row = _require_search_provider(db, tenant_id, provider_id)
    if row.tenant_id is None:
        raise HTTPException(status_code=400, detail="Built-in providers cannot be edited from this screen.")
    changes = payload.model_dump(exclude_unset=True)
    if "configuration_json" in changes and changes["configuration_json"] is not None:
        changes["configuration_json"] = _validate_generic_rest_configuration(changes["configuration_json"])
    for key, value in changes.items():
        setattr(row, key, value)
    row.updated_by = current_user["user_id"]
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="UPDATE",
        event_category="AUGMIS_BUSINESS",
        description=f"Updated search provider {row.display_name}",
        resource_type="bd_search_provider",
        resource_id=row.id,
        metadata={"updated_fields": sorted(changes.keys())},
    )
    return {"success": True, "data": _serialize_provider(db, tenant_id, row)}


def delete_search_provider(db: Session, tenant_id: str, provider_id: str, current_user: dict) -> dict[str, Any]:
    row = _require_search_provider(db, tenant_id, provider_id)
    if row.tenant_id is None:
        raise HTTPException(status_code=400, detail="Built-in providers cannot be deleted.")
    in_use = next(
        (
            connector
            for connector in db.query(BusinessDevelopmentConnector)
            .filter(BusinessDevelopmentConnector.tenant_id == tenant_id)
            .all()
            if str((connector.configuration_json or {}).get("provider") or "").strip().lower() == row.provider_code
        ),
        None,
    )
    if in_use:
        raise HTTPException(status_code=409, detail="Provider is currently used by Web Opportunity Search.")
    provider_name = row.display_name
    provider_code = row.provider_code
    db.delete(row)
    db.commit()
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="DELETE",
        event_category="AUGMIS_BUSINESS",
        description=f"Deleted search provider {provider_name}",
        resource_type="bd_search_provider",
        resource_id=provider_id,
        metadata={"provider_code": provider_code},
    )
    return {"success": True, "deleted": 1}


def test_search_provider(
    db: Session,
    tenant_id: str,
    provider_id: str,
    current_user: dict,
) -> dict[str, Any]:
    row = _require_search_provider(db, tenant_id, provider_id)
    if not row.enabled:
        raise HTTPException(status_code=409, detail="Provider is disabled.")
    if row.provider_type == "builtin":
        result = test_connector_credential(db, tenant_id, row.provider_code, current_user)["data"]
    else:
        resolved = resolve_provider_credential(db, tenant_id, row.provider_code)
        if not resolved.api_key:
            raise HTTPException(status_code=400, detail="Provider credential is not configured.")
        provider_client = get_web_search_provider(
            row.provider_code,
            api_key=resolved.api_key,
            provider_type=row.provider_type,
            configuration=row.configuration_json or {},
            adapter_code=row.adapter_code,
        )
        try:
            provider_result = provider_client.test_connection()
            if resolved.secret_row:
                resolved.secret_row.last_tested_at = _now()
                resolved.secret_row.last_test_status = "success"
                resolved.secret_row.last_test_error = None
                db.commit()
            result = {
                **get_connector_credential_status(db, tenant_id, row.provider_code)["data"],
                "result": provider_result,
            }
        except Exception as exc:
            safe_message = str(exc).replace("\r", " ").replace("\n", " ").strip()
            if resolved.secret_row:
                resolved.secret_row.last_tested_at = _now()
                resolved.secret_row.last_test_status = "failed"
                resolved.secret_row.last_test_error = safe_message
                db.commit()
            result = {
                **get_connector_credential_status(db, tenant_id, row.provider_code)["data"],
                "result": {"success": False, "provider": row.provider_code, "message": safe_message},
            }
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="TEST",
        event_category="AUGMIS_BUSINESS",
        description=f"Tested search provider {row.display_name}",
        resource_type="bd_search_provider",
        resource_id=row.id,
        metadata={"provider_code": row.provider_code, "provider_type": row.provider_type},
    )
    return {"success": True, "data": _serialize_provider(db, tenant_id, row), "result": result.get("result")}
