from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests


TED_API_BASE_URL = "https://api.ted.europa.eu"
TED_SEARCH_PATH = "/v3/notices/search"
TED_DIRECT_NOTICE_TEMPLATE = "https://ted.europa.eu/en/notice/{publication_number}/html"
TED_TIMEOUT_SECONDS = 20
TED_MAX_PER_PAGE = 250
TED_PROVIDER_MESSAGE_LIMIT = 240
TED_LANGUAGE_PREFERENCE = ("eng", "en", "mul", "fra", "deu")
TED_SEARCH_RESULT_FIELDS = (
    "publication-number",
    "notice-identifier",
    "notice-version",
    "notice-title",
    "buyer-name",
    "buyer-country",
    "place-of-performance",
    "publication-date",
    "deadline",
    "notice-type",
    "procedure-type",
    "contract-nature",
    "classification-cpv",
    "estimated-value-proc",
    "estimated-value-cur-proc",
    "official-language",
    "announcement-url",
    "description-proc",
    "additional-information",
    "additional-information-lot",
)
TED_ALLOWED_RESULT_FIELDS = frozenset(TED_SEARCH_RESULT_FIELDS)
TED_LEGACY_UNSUPPORTED_RESULT_FIELDS = (
    "OPP-010-notice",
    "BT-701-notice",
    "BT-757-notice",
    "OPP-121-Business",
    "BT-500-Organization-Company[OPT-200-Organization-Company = OPT-300-Procedure-Buyer]",
    "BT-514-Organization-Company[OPT-200-Organization-Company = OPT-300-Procedure-Buyer]",
    "BT-05(a)-notice",
    "deadline-receipt-tender-date-lot",
    "BT-02-notice",
    "BT-23-Procedure",
    "BT-262-Procedure",
    "BT-702(a)-notice",
    "OPP-122-Business",
    "OPP-130-Business",
    "BT-300-Lot",
    "description-glo",
)
TED_NOTICE_RESPONSE_FIELDS: dict[str, tuple[str, ...]] = {
    "publication_number": ("publication-number",),
    "notice_identifier": ("notice-identifier",),
    "notice_version": ("notice-version",),
    "title": ("notice-title", "announcement-title", "contract-title"),
    "buyer_name": ("buyer-name", "business-name"),
    "buyer_country": ("buyer-country", "business-country"),
    "place_of_performance": ("place-of-performance",),
    "publication_date": ("publication-date",),
    "deadline": ("deadline",),
    "notice_type": ("notice-type",),
    "procedure_type": ("procedure-type",),
    "contract_nature": ("contract-nature",),
    "cpv_codes": ("classification-cpv",),
    "estimated_value": ("estimated-value-proc", "estimated-value"),
    "estimated_currency": ("estimated-value-cur-proc", "estimated-value-cur"),
    "official_language": ("official-language",),
    "official_notice_url": ("announcement-url",),
    "summary": ("description-proc", "additional-information", "notice-title"),
    "lot_summary": ("additional-information-lot",),
}


class TedApiError(RuntimeError):
    def __init__(
        self,
        user_message: str,
        *,
        provider_message: str | None = None,
        http_status: int | None = None,
        provider_error_code: str | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.provider_message = provider_message
        self.http_status = http_status
        self.provider_error_code = provider_error_code
        self.request_id = request_id

    def to_diagnostic(self) -> dict[str, Any]:
        return {
            "provider_http_status": self.http_status,
            "provider_error_code": self.provider_error_code,
            "provider_message": self.provider_message,
            "request_id": self.request_id,
        }


def _bounded_text(value: str | None, limit: int = TED_PROVIDER_MESSAGE_LIMIT) -> str | None:
    cleaned = " ".join((value or "").split()).strip()
    if not cleaned:
        return None
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 3].rstrip()}..."


def validate_ted_search_result_fields(fields: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    canonical = tuple(fields)
    if not canonical:
        raise ValueError("TED search result fields cannot be empty.")
    seen: set[str] = set()
    invalid: list[str] = []
    duplicates: list[str] = []
    for field in canonical:
        if field not in TED_ALLOWED_RESULT_FIELDS:
            invalid.append(field)
        if field in seen:
            duplicates.append(field)
        seen.add(field)
    if invalid:
        raise ValueError(f"Unsupported TED search result field(s): {', '.join(invalid)}")
    if duplicates:
        raise ValueError(f"Duplicate TED search result field(s): {', '.join(duplicates)}")
    return canonical


def build_ted_search_request_body(*, query: str, page: int, limit: int) -> dict[str, Any]:
    return {
        "query": query,
        "fields": list(validate_ted_search_result_fields(TED_SEARCH_RESULT_FIELDS)),
        "page": page,
        "limit": max(1, min(limit, TED_MAX_PER_PAGE)),
        "paginationMode": "PAGE_NUMBER",
        "checkQuerySyntax": False,
    }


def _safe_error_payload(response: requests.Response) -> dict[str, Any] | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _safe_error_message(response: requests.Response) -> str | None:
    payload = _safe_error_payload(response)
    if isinstance(payload, dict):
        for key in ("message", "detail", "title", "error", "description"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return _bounded_text(value)
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                for key in ("message", "detail", "title", "description"):
                    value = first.get(key)
                    if isinstance(value, str) and value.strip():
                        return _bounded_text(value)
            if isinstance(first, str) and first.strip():
                return _bounded_text(first)
    return _bounded_text(response.text)


def _provider_error_code(response: requests.Response) -> str | None:
    payload = _safe_error_payload(response)
    if isinstance(payload, dict):
        for key in ("code", "errorCode", "error_code", "type"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _provider_request_id(response: requests.Response) -> str | None:
    for key in ("x-request-id", "x-correlation-id", "request-id", "trace-id"):
        value = response.headers.get(key)
        if value and value.strip():
            return value.strip()
    return None


def _ted_rejection_message(detail: str | None) -> str:
    lowered = (detail or "").lower()
    if "parameter 'fields'" in lowered or 'parameter "fields"' in lowered:
        return "TED rejected the search request because the connector field configuration is invalid."
    return "TED rejected the search request."


@dataclass
class TedNotice:
    publication_number: str | None
    notice_identifier: str | None
    notice_version: str | None
    title: str
    buyer_name: str | None
    buyer_country: str | None
    place_of_performance: list[str]
    publication_date: datetime | None
    deadline: datetime | None
    notice_type: str | None
    procedure_type: str | None
    contract_nature: str | None
    cpv_codes: list[str]
    estimated_value: float | None
    estimated_currency: str | None
    official_language: str | None
    official_notice_url: str | None
    summary: str | None
    lot_summary: str | None
    raw_notice: dict[str, Any]

    @property
    def stable_identifier(self) -> str | None:
        return self.notice_identifier or self.publication_number


def _flatten_strings(value: Any) -> list[str]:
    results: list[str] = []
    if value is None:
        return results
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            results.append(cleaned)
        return results
    if isinstance(value, (int, float)):
        results.append(str(value))
        return results
    if isinstance(value, list):
        for item in value:
            results.extend(_flatten_strings(item))
        return results
    if isinstance(value, dict):
        matched_preferred_key = False
        for key in ("value", "label", "text", "content", "name", "title", "url"):
            if key in value:
                matched_preferred_key = True
                results.extend(_flatten_strings(value[key]))
        if matched_preferred_key:
            return results
        lowered_keys = {str(key).lower(): key for key in value.keys()}
        for preferred_language in TED_LANGUAGE_PREFERENCE:
            matched_key = lowered_keys.get(preferred_language)
            if matched_key is not None:
                preferred_results = _flatten_strings(value[matched_key])
                if preferred_results:
                    return preferred_results
        for nested_value in value.values():
            results.extend(_flatten_strings(nested_value))
        return results
    return results


def _field_values(item: dict[str, Any], field: str) -> list[str]:
    if field in item:
        return _flatten_strings(item.get(field))
    fields_obj = item.get("fields")
    if isinstance(fields_obj, dict):
        return _flatten_strings(fields_obj.get(field))
    if isinstance(fields_obj, list):
        for entry in fields_obj:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("field") or entry.get("name") or entry.get("key")) == field:
                return _flatten_strings(entry.get("value") if "value" in entry else entry.get("values"))
    return []


def _pick_first(item: dict[str, Any], *fields: str) -> str | None:
    for field in fields:
        values = _field_values(item, field)
        if values:
            return values[0]
    return None


def _mapped_first(item: dict[str, Any], logical_name: str) -> str | None:
    return _pick_first(item, *TED_NOTICE_RESPONSE_FIELDS[logical_name])


def _mapped_values(item: dict[str, Any], logical_name: str) -> list[str]:
    values: list[str] = []
    for field in TED_NOTICE_RESPONSE_FIELDS[logical_name]:
        values = _field_values(item, field)
        if values:
            return values
    return values


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    for parser in (
        "%Y%m%d",
        "%Y-%m-%d",
        "%Y-%m-%d%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            parsed = datetime.strptime(text, parser)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_float(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _result_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("results", "items", "notices", "content"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _result_total(payload: dict[str, Any], item_count: int) -> int:
    for key in ("totalNoticeCount", "total", "count", "total_count"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
    return item_count


def _official_notice_url(publication_number: str | None, item: dict[str, Any]) -> str | None:
    direct = _mapped_first(item, "official_notice_url")
    if direct:
        return direct
    links = item.get("links")
    if isinstance(links, list):
        for entry in links:
            if not isinstance(entry, dict):
                continue
            url = str(entry.get("url") or entry.get("href") or "").strip()
            if url:
                return url
    if isinstance(links, dict):
        for preferred_key in ("htmlDirect", "html", "pdf", "xml"):
            values = _flatten_strings(links.get(preferred_key))
            if values:
                return values[0]
    if publication_number:
        return TED_DIRECT_NOTICE_TEMPLATE.format(publication_number=publication_number)
    return None


def _parse_notice(item: dict[str, Any]) -> TedNotice:
    publication_number = _mapped_first(item, "publication_number")
    title = _mapped_first(item, "title")
    if not title:
        raise TedApiError("TED returned a notice without a title.")
    return TedNotice(
        publication_number=publication_number,
        notice_identifier=_mapped_first(item, "notice_identifier"),
        notice_version=_mapped_first(item, "notice_version"),
        title=title,
        buyer_name=_mapped_first(item, "buyer_name"),
        buyer_country=_mapped_first(item, "buyer_country"),
        place_of_performance=_mapped_values(item, "place_of_performance"),
        publication_date=_parse_datetime(_mapped_first(item, "publication_date")),
        deadline=_parse_datetime(_mapped_first(item, "deadline")),
        notice_type=_mapped_first(item, "notice_type"),
        procedure_type=_mapped_first(item, "procedure_type"),
        contract_nature=_mapped_first(item, "contract_nature"),
        cpv_codes=_mapped_values(item, "cpv_codes"),
        estimated_value=_parse_float(_mapped_first(item, "estimated_value")),
        estimated_currency=_mapped_first(item, "estimated_currency"),
        official_language=_mapped_first(item, "official_language"),
        official_notice_url=_official_notice_url(publication_number, item),
        summary=_mapped_first(item, "summary"),
        lot_summary=_mapped_first(item, "lot_summary"),
        raw_notice=item,
    )


class TedSearchClient:
    def __init__(self, *, base_url: str = TED_API_BASE_URL, timeout_seconds: int = TED_TIMEOUT_SECONDS) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def search_notices(self, *, query: str, page: int, limit: int) -> dict[str, Any]:
        body = build_ted_search_request_body(query=query, page=page, limit=limit)
        try:
            response = requests.post(
                f"{self.base_url}{TED_SEARCH_PATH}",
                json=body,
                headers={"Accept": "application/json"},
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise TedApiError("TED request timed out.") from exc
        except requests.RequestException as exc:
            raise TedApiError("TED service is temporarily unavailable.") from exc
        if response.status_code >= 500:
            raise TedApiError("TED service is temporarily unavailable.", http_status=response.status_code)
        if response.status_code >= 400:
            detail = _safe_error_message(response)
            raise TedApiError(
                _ted_rejection_message(detail),
                provider_message=detail,
                http_status=response.status_code,
                provider_error_code=_provider_error_code(response),
                request_id=_provider_request_id(response),
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise TedApiError("TED returned an unexpected response.") from exc
        items = _result_items(payload)
        notices: list[TedNotice] = []
        invalid_items = 0
        for item in items:
            try:
                notices.append(_parse_notice(item))
            except TedApiError:
                invalid_items += 1
        return {
            "query": query,
            "page": page,
            "limit": body["limit"],
            "fields": list(body["fields"]),
            "total": _result_total(payload, len(items)),
            "items": notices,
            "invalid_items": invalid_items,
            "raw": payload,
        }
