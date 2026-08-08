from __future__ import annotations

import time
from typing import Any, TypeVar
from uuid import uuid4

from fastapi import HTTPException, status
from openai import APITimeoutError, OpenAIError, RateLimitError
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.db_models import (
    BusinessDevelopmentDiscoveredOpportunity,
    BusinessDevelopmentDiscoveryTranslation,
)
from app.services.ai_service import client as openai_client
from app.services.audit_service import create_audit_log
from app.services.subscription_service import add_ai_token_usage, validate_usage_limit
from app.services.token_usage_service import estimate_ai_usage_tokens
from app.services.augmis_business_translation_prompts import (
    DISCOVERY_TRANSLATION_PROMPT_VERSION,
    PROMPT_BUNDLE_VERSION,
    build_discovery_translation_prompt,
)
from app.services.augmis_business_translation_utils import (
    detect_discovery_language,
    discovery_translation_payload,
    discovery_translation_source_hash,
    is_english_language,
    language_label,
)
from app.services.augmis_business_ai_service import _extract_json_object
from app.core.config import settings


ModelT = TypeVar("ModelT", bound=BaseModel)


class AugmisBusinessDiscoveryTranslationResult(BaseModel):
    source_language: str
    target_language: str
    translated_title: str | None = None
    translated_summary: str | None = None
    translated_description: str | None = None


def _is_missing_translation_table_error(exc: Exception) -> bool:
    if not isinstance(exc, ProgrammingError):
        return False
    message = str(exc).lower()
    return "bd_discovery_translations" in message and "does not exist" in message


def _translation_tables_not_initialized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Discovery translation tables are not initialized yet. Run the latest AUGMIS Business migration.",
    )


def _now():
    from app.services.augmis_business_listener_service import _now as listener_now

    return listener_now()


def _serialize_datetime(value):
    return value.isoformat() if value else None


def _require_openai_api_key() -> None:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Translation service unavailable because the OpenAI API key is not configured.",
        )


def _serialize_usage_metadata(*, response_usage: Any, prompt: str, answer: str) -> dict[str, Any]:
    input_tokens = getattr(response_usage, "prompt_tokens", None)
    output_tokens = getattr(response_usage, "completion_tokens", None)
    total_tokens = getattr(response_usage, "total_tokens", None)
    if total_tokens is None:
        total_tokens = estimate_ai_usage_tokens(prompt, "", answer)
    if input_tokens is None or output_tokens is None:
        estimated_input = estimate_ai_usage_tokens(prompt, "", "")
        input_tokens = input_tokens or estimated_input
        output_tokens = output_tokens or max(0, total_tokens - input_tokens)
    return {
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "total_tokens": int(total_tokens or 0),
        "estimated_cost_usd": None,
    }


def _require_discovery(db: Session, tenant_id: str, discovery_id: str) -> BusinessDevelopmentDiscoveredOpportunity:
    row = (
        db.query(BusinessDevelopmentDiscoveredOpportunity)
        .filter(
            BusinessDevelopmentDiscoveredOpportunity.tenant_id == tenant_id,
            BusinessDevelopmentDiscoveredOpportunity.id == discovery_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery not found")
    return row


def _serialize_translation(row: BusinessDevelopmentDiscoveryTranslation | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "discovery_id": row.discovery_id,
        "translation_version": row.translation_version,
        "source_language": row.source_language,
        "source_language_label": language_label(row.source_language),
        "target_language": row.target_language,
        "translated_title": row.translated_title,
        "translated_summary": row.translated_summary,
        "translated_description": row.translated_description,
        "translated_detail_json": row.translated_detail_json or {},
        "provider": row.provider,
        "model": row.model,
        "prompt_bundle_version": row.prompt_bundle_version,
        "prompt_version": row.prompt_version,
        "usage_json": row.usage_json or {},
        "created_by": row.created_by,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def get_latest_translation_row(
    db: Session,
    tenant_id: str,
    discovery_id: str,
    *,
    target_language: str = "en",
) -> BusinessDevelopmentDiscoveryTranslation | None:
    try:
        return (
            db.query(BusinessDevelopmentDiscoveryTranslation)
            .filter(
                BusinessDevelopmentDiscoveryTranslation.tenant_id == tenant_id,
                BusinessDevelopmentDiscoveryTranslation.discovery_id == discovery_id,
                BusinessDevelopmentDiscoveryTranslation.target_language == target_language,
            )
            .order_by(
                BusinessDevelopmentDiscoveryTranslation.translation_version.desc(),
                BusinessDevelopmentDiscoveryTranslation.created_at.desc(),
            )
            .first()
        )
    except Exception as exc:  # pragma: no cover - runtime migration fallback
        if _is_missing_translation_table_error(exc):
            return None
        raise


def _next_translation_version(db: Session, tenant_id: str, discovery_id: str) -> int:
    try:
        row = (
            db.query(BusinessDevelopmentDiscoveryTranslation.translation_version)
            .filter(
                BusinessDevelopmentDiscoveryTranslation.tenant_id == tenant_id,
                BusinessDevelopmentDiscoveryTranslation.discovery_id == discovery_id,
            )
            .order_by(BusinessDevelopmentDiscoveryTranslation.translation_version.desc())
            .first()
        )
    except Exception as exc:
        if _is_missing_translation_table_error(exc):
            raise _translation_tables_not_initialized() from exc
        raise
    return 1 if not row else int(row.translation_version or 0) + 1


def get_discovery_translation(
    db: Session,
    tenant_id: str,
    discovery_id: str,
    *,
    target_language: str = "en",
) -> dict[str, Any]:
    discovery = _require_discovery(db, tenant_id, discovery_id)
    try:
        translation = get_latest_translation_row(db, tenant_id, discovery.id, target_language=target_language)
    except Exception as exc:
        if _is_missing_translation_table_error(exc):
            raise _translation_tables_not_initialized() from exc
        raise
    source_language = detect_discovery_language(discovery)
    return {
        "success": True,
        "data": _serialize_translation(translation),
        "source_language": source_language,
        "source_language_label": language_label(source_language),
        "translation_required": not is_english_language(source_language),
    }


def _run_translation_agent(
    *,
    tenant_id: str,
    user_id: str,
    discovery_id: str,
    prompt: str,
    db: Session,
) -> tuple[AugmisBusinessDiscoveryTranslationResult, dict[str, Any]]:
    _require_openai_api_key()
    validate_usage_limit(tenant_id, "ai_tokens", db)
    started_at = _now()
    last_error: Exception | None = None
    for attempt in range(1, 3):
        try:
            response = openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a controlled AUGMIS Business translation engine. Return JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            raw_content = response.choices[0].message.content or ""
            payload = _extract_json_object(raw_content)
            parsed = AugmisBusinessDiscoveryTranslationResult.model_validate(payload)
            usage = _serialize_usage_metadata(
                response_usage=getattr(response, "usage", None),
                prompt=prompt,
                answer=raw_content,
            )
            add_ai_token_usage(tenant_id, usage["total_tokens"], db)
            metadata = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "discovery_id": discovery_id,
                "provider": "openai",
                "model": settings.OPENAI_MODEL,
                "prompt_version": DISCOVERY_TRANSLATION_PROMPT_VERSION,
                "started_at": _serialize_datetime(started_at),
                "completed_at": _serialize_datetime(_now()),
                "status": "success",
                **usage,
                "error_message": None,
            }
            create_audit_log(
                db=db,
                tenant_id=tenant_id,
                user_id=user_id,
                event_type="AI_RUN",
                event_category="AI",
                description="AUGMIS Business discovery translation completed",
                resource_type="bd_discovery",
                resource_id=discovery_id,
                metadata=metadata,
            )
            return parsed, metadata
        except ValidationError as exc:
            last_error = exc
            break
        except ValueError as exc:
            last_error = exc
            break
        except (APITimeoutError, RateLimitError, OpenAIError) as exc:
            last_error = exc
            if attempt >= 2:
                break
            time.sleep(0.6 * attempt)
        except Exception as exc:  # pragma: no cover
            last_error = exc
            if attempt >= 2:
                break
            time.sleep(0.6 * attempt)

    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="AI_RUN",
        event_category="AI",
        description="AUGMIS Business discovery translation failed",
        resource_type="bd_discovery",
        resource_id=discovery_id,
        metadata={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "discovery_id": discovery_id,
            "provider": "openai",
            "model": settings.OPENAI_MODEL,
            "prompt_version": DISCOVERY_TRANSLATION_PROMPT_VERSION,
            "started_at": _serialize_datetime(started_at),
            "completed_at": _serialize_datetime(_now()),
            "status": "failed",
            "error_message": str(last_error or "Unknown translation error"),
        },
    )
    if isinstance(last_error, ValidationError):
        raise HTTPException(status_code=502, detail="Translation could not be generated.")
    if isinstance(last_error, ValueError):
        raise HTTPException(status_code=502, detail="Translation could not be generated.")
    if isinstance(last_error, APITimeoutError):
        raise HTTPException(status_code=504, detail="Translation service unavailable.")
    if isinstance(last_error, RateLimitError):
        raise HTTPException(status_code=503, detail="AI provider rate limit reached.")
    if isinstance(last_error, OpenAIError):
        raise HTTPException(status_code=503, detail="Translation service unavailable.")
    raise HTTPException(status_code=503, detail="Translation could not be generated.")


def translate_discovery(
    db: Session,
    tenant_id: str,
    discovery_id: str,
    current_user: dict,
    *,
    force: bool = False,
    target_language: str = "en",
) -> dict[str, Any]:
    if target_language != "en":
        raise HTTPException(status_code=400, detail="Only English translation is supported in this phase.")
    discovery = _require_discovery(db, tenant_id, discovery_id)
    source_language = detect_discovery_language(discovery)
    if is_english_language(source_language):
        raise HTTPException(status_code=400, detail="Discovery is already in English. No translation required.")
    source_hash = discovery_translation_source_hash(discovery, source_language)
    if not force:
        try:
            cached = (
                db.query(BusinessDevelopmentDiscoveryTranslation)
                .filter(
                    BusinessDevelopmentDiscoveryTranslation.tenant_id == tenant_id,
                    BusinessDevelopmentDiscoveryTranslation.discovery_id == discovery.id,
                    BusinessDevelopmentDiscoveryTranslation.target_language == target_language,
                    BusinessDevelopmentDiscoveryTranslation.source_content_hash == source_hash,
                )
                .order_by(BusinessDevelopmentDiscoveryTranslation.translation_version.desc())
                .first()
            )
        except Exception as exc:
            if _is_missing_translation_table_error(exc):
                raise _translation_tables_not_initialized() from exc
            raise
        if cached:
            return {"success": True, "data": _serialize_translation(cached), "cached": True}

    prompt_payload = discovery_translation_payload(discovery)
    prompt_payload["source_language"] = source_language
    prompt = build_discovery_translation_prompt(prompt_payload)
    result, run_metadata = _run_translation_agent(
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        discovery_id=discovery.id,
        prompt=prompt,
        db=db,
    )
    version = _next_translation_version(db, tenant_id, discovery.id)
    row = BusinessDevelopmentDiscoveryTranslation(
        id=f"BD-DTR-{version}-{str(uuid4())[:8].upper()}",
        tenant_id=tenant_id,
        discovery_id=discovery.id,
        translation_version=version,
        source_language=result.source_language or (source_language or "unknown"),
        target_language="en",
        source_content_hash=source_hash,
        translated_title=result.translated_title,
        translated_summary=result.translated_summary,
        translated_description=result.translated_description,
        translated_detail_json={
            "translated_title": result.translated_title,
            "translated_summary": result.translated_summary,
            "translated_description": result.translated_description,
        },
        provider="openai",
        model=settings.OPENAI_MODEL,
        prompt_bundle_version=PROMPT_BUNDLE_VERSION,
        prompt_version=DISCOVERY_TRANSLATION_PROMPT_VERSION,
        usage_json=run_metadata,
        created_by=current_user["user_id"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        event_type="TRANSLATE",
        event_category="AUGMIS_BUSINESS",
        description="Discovery translated to English",
        resource_type="bd_discovery",
        resource_id=discovery.id,
        metadata={
            "translation_id": row.id,
            "translation_version": row.translation_version,
            "source_language": row.source_language,
            "target_language": row.target_language,
            "cached": False,
        },
    )
    return {"success": True, "data": _serialize_translation(row), "cached": False}
