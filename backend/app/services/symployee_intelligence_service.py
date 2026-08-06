from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.subscription_service import add_ai_token_usage, validate_usage_limit
from app.services.symployee_policy_service import resolve_required_policies
from app.services.token_usage_service import estimate_ai_usage_tokens


logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _extract_json_object(raw_content: str) -> dict[str, Any]:
    text = str(raw_content or "").strip()
    if not text:
        raise ValueError("Model returned empty content")

    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if fenced_match:
        text = fenced_match.group(1)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        data = json.loads(text[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("Model response must be a JSON object")
    return data


def _build_policy_prompt(
    *,
    file_name: str,
    parsed_text: str,
    metadata_candidate: dict,
    classification_policy: dict,
    metadata_policy: dict,
) -> str:
    return f"""
You are the AUGMIS Symployee Document Controller AI.

Return JSON only in this exact shape:
{{
  "classification": {{
    "document_type_code": "string",
    "title": "string",
    "discipline_code": "string|null",
    "project_code": "string|null",
    "originator_code": "string|null",
    "confidence_score": 0.0
  }},
  "metadata": {{
    "fields": {{
      "field_name": "value"
    }},
    "missing_required_fields": ["field_name"],
    "confidence_score": 0.0
  }}
}}

Classification policy:
{json.dumps(classification_policy, ensure_ascii=True, default=str)}

Metadata policy:
{json.dumps(metadata_policy, ensure_ascii=True, default=str)}

Connector metadata candidate:
{json.dumps(metadata_candidate, ensure_ascii=True, default=str)}

File name:
{file_name}

Document content excerpt:
{parsed_text[:12000]}

Rules:
- Use only policy-supported values where possible.
- Respect required fields from the metadata policy.
- If a value cannot be inferred confidently, return null or omit it from metadata fields.
- confidence_score must be between 0 and 1.
- Do not include commentary outside JSON.
"""


def generate_document_recommendations(
    db: Session,
    tenant_id: str,
    file_name: str,
    parsed_text: str,
    metadata_candidate: dict,
    repository_id: str | None = None,
    business_area: str | None = None,
    project_code: str | None = None,
) -> dict:
    validate_usage_limit(tenant_id, "ai_tokens", db)

    policies = resolve_required_policies(
        db=db,
        tenant_id=tenant_id,
        policy_domains=["classification", "metadata_schema"],
        repository_id=repository_id,
        business_area=business_area,
        project_code=project_code,
    )
    classification_policy = policies["classification"]
    metadata_policy = policies["metadata_schema"]

    user_prompt = _build_policy_prompt(
        file_name=file_name,
        parsed_text=parsed_text,
        metadata_candidate=metadata_candidate,
        classification_policy=classification_policy,
        metadata_policy=metadata_policy,
    )

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a controlled enterprise document classification and metadata extraction engine. Return JSON only.",
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.1,
        )
    except Exception as exc:
        logger.exception(
            "Symployee model-driven recommendation generation failed",
            extra={
                "category": "symployee_openai_request_failure",
                "is_critical": True,
                "metadata": {"tenant_id": tenant_id},
            },
        )
        raise ValueError(f"Symployee AI generation failed: {exc}") from exc

    raw_content = response.choices[0].message.content or ""
    payload = _extract_json_object(raw_content)

    tokens_used = getattr(response.usage, "total_tokens", None) or estimate_ai_usage_tokens(
        question=f"Classify and extract metadata for {file_name}",
        context=parsed_text[:12000],
        answer=raw_content,
    )
    add_ai_token_usage(tenant_id, tokens_used, db)

    classification = payload.get("classification") or {}
    metadata = payload.get("metadata") or {}

    return {
        "classification": {
            **classification,
            "policy_code": classification_policy["policy_code"],
            "policy_version_no": classification_policy["version_no"],
            "policy_scope_type": classification_policy.get("scope_type"),
            "policy_scope_ref": classification_policy.get("scope_ref"),
            "model_name": settings.OPENAI_MODEL,
            "model_provider": "openai",
            "prompt_profile_code": "symployee.document_controller.classification",
            "prompt_version": "v2",
        },
        "metadata": {
            **metadata,
            "policy_code": metadata_policy["policy_code"],
            "policy_version_no": metadata_policy["version_no"],
            "policy_scope_type": metadata_policy.get("scope_type"),
            "policy_scope_ref": metadata_policy.get("scope_ref"),
            "model_name": settings.OPENAI_MODEL,
            "model_provider": "openai",
            "prompt_profile_code": "symployee.document_controller.metadata",
            "prompt_version": "v2",
        },
        "usage": {
            "tokens_used": tokens_used,
        },
    }
