from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

import requests

from app.core.config import settings
from app.services.augmis_business_web_fetcher import validate_public_http_url


class WebSearchProviderError(Exception):
    pass


class MissingWebSearchApiKeyError(WebSearchProviderError):
    pass


@dataclass
class WebSearchResult:
    result_id: str
    title: str
    url: str
    snippet: str | None
    source_domain: str | None
    published_at: str | None
    rank: int
    provider_metadata: dict[str, Any]


class BaseWebSearchProvider:
    name: str
    display_name: str
    timeout_seconds: int

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    def _request_failed_message(self) -> str:
        return f"{self.display_name} request failed."

    def _request_timed_out_message(self) -> str:
        return f"{self.display_name} request timed out."

    def _invalid_key_message(self) -> str:
        return f"{self.display_name} API key is invalid or unauthorized."

    def _missing_key_message(self) -> str:
        return f"{self.display_name} API key is not configured."

    def _result(self, *, query: str, raw_count: int, results: list[WebSearchResult], usage: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "provider": self.name,
            "query": query,
            "count": len(results),
            "raw_count": raw_count,
            "results": results,
            "api_call_count": 1,
            "usage": usage or {},
        }

    def test_connection(self) -> dict[str, Any]:
        result = self.search(query='"workflow automation" RFP', count=1)
        return {
            "success": True,
            "message": f"{self.display_name} API key is configured and the provider returned results.",
            "provider": self.name,
            "result_count": result["count"],
        }

    def search(
        self,
        *,
        query: str,
        count: int,
        offset: int = 0,
        country: str | None = None,
        language: str | None = None,
        freshness_days: int | None = None,
        exclude_domains: list[str] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


def _safe_json_path_lookup(payload: Any, path: str | None) -> Any:
    if not path:
        return payload
    current = payload
    for token in [part.strip() for part in path.split(".") if part.strip()]:
        if isinstance(current, dict):
            current = current.get(token)
        elif isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


class GenericRestWebSearchProvider(BaseWebSearchProvider):
    display_name = "Generic REST Search"

    def __init__(
        self,
        *,
        name: str,
        configuration: dict[str, Any],
        api_key: str | None = None,
    ) -> None:
        super().__init__(api_key=api_key)
        self.name = name
        self.base_url = str(configuration.get("base_search_url") or "").strip()
        self.http_method = str(configuration.get("http_method", "get") or "get").strip().lower()
        self.authentication_type = str(configuration.get("authentication_type", "api_key_header") or "api_key_header").strip().lower()
        self.api_key_header_name = str(configuration.get("api_key_header_name", "X-API-Key") or "X-API-Key").strip()
        self.query_parameter_name = str(configuration.get("query_parameter_name", "q") or "q").strip()
        self.results_path = str(configuration.get("results_path", "results") or "results").strip()
        self.title_field = str(configuration.get("title_field", "title") or "title").strip()
        self.url_field = str(configuration.get("url_field", "url") or "url").strip()
        self.snippet_field = str(configuration.get("snippet_field", "snippet") or "snippet").strip()
        self.score_field = str(configuration.get("score_field") or "").strip() or None
        self.published_date_field = str(configuration.get("published_date_field") or "").strip() or None
        self.page_parameter = str(configuration.get("page_parameter") or "").strip() or None
        self.page_size_parameter = str(configuration.get("page_size_parameter") or "").strip() or None
        self.timeout_seconds = settings.AUGMIS_WEB_SEARCH_TIMEOUT_SECONDS
        validate_public_http_url(self.base_url)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if not self.api_key:
            raise MissingWebSearchApiKeyError(self._missing_key_message())
        if self.authentication_type == "bearer_token":
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            headers[self.api_key_header_name] = self.api_key
        return headers

    def search(
        self,
        *,
        query: str,
        count: int,
        offset: int = 0,
        country: str | None = None,
        language: str | None = None,
        freshness_days: int | None = None,
        exclude_domains: list[str] | None = None,
    ) -> dict[str, Any]:
        del country
        del language
        del freshness_days
        del exclude_domains
        query_count = max(1, min(count, 20))
        payload: dict[str, Any] = {self.query_parameter_name: query}
        if self.page_size_parameter:
            payload[self.page_size_parameter] = query_count
        if self.page_parameter:
            payload[self.page_parameter] = max(1, offset + 1)
        try:
            if self.http_method == "post":
                response = requests.post(
                    self.base_url,
                    headers=self._headers(),
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            else:
                response = requests.get(
                    self.base_url,
                    headers=self._headers(),
                    params=payload,
                    timeout=self.timeout_seconds,
                )
        except requests.Timeout as exc:
            raise WebSearchProviderError(self._request_timed_out_message()) from exc
        except requests.RequestException as exc:
            raise WebSearchProviderError(self._request_failed_message()) from exc
        if response.status_code == 401:
            raise WebSearchProviderError(self._invalid_key_message())
        if response.status_code == 403:
            raise WebSearchProviderError(f"{self.display_name} rejected the request.")
        if response.status_code == 429:
            raise WebSearchProviderError(f"{self.display_name} rate limit was reached.")
        if response.status_code >= 500:
            raise WebSearchProviderError(f"{self.display_name} returned a server error.")
        if response.status_code >= 400:
            raise WebSearchProviderError(f"{self.display_name} returned HTTP {response.status_code}.")
        try:
            body = response.json()
        except ValueError as exc:
            raise WebSearchProviderError(f"{self.display_name} returned malformed JSON.") from exc

        raw_results = _safe_json_path_lookup(body, self.results_path)
        if raw_results is None:
            raw_results = []
        if not isinstance(raw_results, list):
            raise WebSearchProviderError("Unable to map provider response.")

        parsed_results: list[WebSearchResult] = []
        for index, item in enumerate(raw_results, start=1):
            if not isinstance(item, dict):
                continue
            title = str(_safe_json_path_lookup(item, self.title_field) or "").strip()
            url = str(_safe_json_path_lookup(item, self.url_field) or "").strip()
            if not title or not url:
                raise WebSearchProviderError("Unable to map provider response.")
            snippet = str(_safe_json_path_lookup(item, self.snippet_field) or "").strip() or None
            score = _safe_json_path_lookup(item, self.score_field) if self.score_field else None
            published_at = (
                str(_safe_json_path_lookup(item, self.published_date_field) or "").strip() or None
                if self.published_date_field
                else None
            )
            hostname = urlsplit(url).hostname
            parsed_results.append(
                WebSearchResult(
                    result_id=f"{self.name}-{index}",
                    title=title,
                    url=url,
                    snippet=snippet,
                    source_domain=hostname.lower() if hostname else None,
                    published_at=published_at,
                    rank=index,
                    provider_metadata={"score": score, "raw_item": item},
                )
            )
        return self._result(query=query, raw_count=len(raw_results), results=parsed_results)


class BraveWebSearchProvider(BaseWebSearchProvider):
    name = "brave"
    display_name = "Brave"

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__(api_key=api_key)
        self.base_url = settings.BRAVE_SEARCH_BASE_URL
        self.timeout_seconds = settings.AUGMIS_WEB_SEARCH_TIMEOUT_SECONDS

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise MissingWebSearchApiKeyError(self._missing_key_message())
        return {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }

    def search(
        self,
        *,
        query: str,
        count: int,
        offset: int = 0,
        country: str | None = None,
        language: str | None = None,
        freshness_days: int | None = None,
        exclude_domains: list[str] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "q": query,
            "count": max(1, min(count, 20)),
            "offset": max(0, min(offset, 9)),
        }
        if country:
            params["country"] = country.upper()
        if language:
            params["search_lang"] = language
            params["ui_lang"] = f"{language}-US" if len(language) == 2 else language
        if freshness_days:
            params["freshness"] = f"pd{max(1, freshness_days)}"
        try:
            response = requests.get(
                self.base_url,
                headers=self._headers(),
                params=params,
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise WebSearchProviderError(self._request_timed_out_message()) from exc
        except requests.RequestException as exc:
            raise WebSearchProviderError(self._request_failed_message()) from exc

        if response.status_code == 401:
            raise WebSearchProviderError(self._invalid_key_message())
        if response.status_code == 403:
            raise WebSearchProviderError("Brave rejected the request.")
        if response.status_code == 429:
            raise WebSearchProviderError("Brave rate limit was reached.")
        if response.status_code >= 500:
            raise WebSearchProviderError("Brave returned a server error.")
        if response.status_code >= 400:
            raise WebSearchProviderError(f"Brave returned HTTP {response.status_code}.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise WebSearchProviderError("Brave returned malformed JSON.") from exc

        web_results = (((payload or {}).get("web") or {}).get("results")) or []
        parsed_results: list[WebSearchResult] = []
        for index, item in enumerate(web_results, start=1):
            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or "").strip()
            if not url or not title:
                continue
            parsed_results.append(
                WebSearchResult(
                    result_id=str(item.get("profile") or item.get("url") or f"brave-{index}"),
                    title=title,
                    url=url,
                    snippet=str(item.get("description") or "").strip() or None,
                    source_domain=str(item.get("meta_url", {}).get("hostname") or "").strip() or None,
                    published_at=str(item.get("age") or "").strip() or None,
                    rank=index,
                    provider_metadata={
                        "family_friendly": item.get("family_friendly"),
                        "language": item.get("language"),
                        "type": item.get("type"),
                    },
                )
            )

        return self._result(query=query, raw_count=len(web_results), results=parsed_results)


class TavilyWebSearchProvider(BaseWebSearchProvider):
    name = "tavily"
    display_name = "Tavily"

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__(api_key=api_key)
        self.base_url = settings.TAVILY_SEARCH_BASE_URL
        self.timeout_seconds = settings.AUGMIS_WEB_SEARCH_TIMEOUT_SECONDS

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise MissingWebSearchApiKeyError(self._missing_key_message())
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def search(
        self,
        *,
        query: str,
        count: int,
        offset: int = 0,
        country: str | None = None,
        language: str | None = None,
        freshness_days: int | None = None,
        exclude_domains: list[str] | None = None,
    ) -> dict[str, Any]:
        del offset
        del language
        payload: dict[str, Any] = {
            "query": query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": max(1, min(count, 20)),
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "auto_parameters": False,
        }
        blocked_domains = [item.strip().lower() for item in (exclude_domains or []) if str(item).strip()]
        if blocked_domains:
            payload["exclude_domains"] = blocked_domains[:150]
        if country:
            payload["country"] = country.strip().lower()
        if freshness_days:
            today = datetime.now(timezone.utc).date()
            payload["start_date"] = (today - timedelta(days=max(1, freshness_days))).isoformat()
            payload["end_date"] = today.isoformat()
        try:
            response = requests.post(
                self.base_url,
                headers=self._headers(),
                json=payload,
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise WebSearchProviderError(self._request_timed_out_message()) from exc
        except requests.RequestException as exc:
            raise WebSearchProviderError(self._request_failed_message()) from exc

        if response.status_code == 401:
            raise WebSearchProviderError(self._invalid_key_message())
        if response.status_code == 403:
            raise WebSearchProviderError("Tavily rejected the request.")
        if response.status_code == 429:
            raise WebSearchProviderError("Tavily rate limit was reached.")
        if response.status_code >= 500:
            raise WebSearchProviderError("Tavily returned a server error.")
        if response.status_code >= 400:
            raise WebSearchProviderError(f"Tavily returned HTTP {response.status_code}.")

        try:
            body = response.json()
        except ValueError as exc:
            raise WebSearchProviderError("Tavily returned malformed JSON.") from exc

        raw_results = (body or {}).get("results") or []
        if not isinstance(raw_results, list):
            raise WebSearchProviderError("Tavily returned an invalid results payload.")

        parsed_results: list[WebSearchResult] = []
        for index, item in enumerate(raw_results, start=1):
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or "").strip()
            if not url or not title:
                continue
            hostname = urlsplit(url).hostname
            parsed_results.append(
                WebSearchResult(
                    result_id=str(item.get("url") or f"tavily-{index}"),
                    title=title,
                    url=url,
                    snippet=str(item.get("content") or "").strip() or None,
                    source_domain=hostname.lower() if hostname else None,
                    published_at=str(item.get("published_date") or item.get("published_at") or "").strip() or None,
                    rank=index,
                    provider_metadata={
                        "score": item.get("score"),
                        "favicon": item.get("favicon"),
                        "images": item.get("images"),
                        "request_id": body.get("request_id"),
                        "response_time": body.get("response_time"),
                    },
                )
            )

        return self._result(
            query=query,
            raw_count=len(raw_results),
            results=parsed_results,
            usage=(body or {}).get("usage") if isinstance((body or {}).get("usage"), dict) else {},
        )


def get_web_search_provider(
    provider_name: str | None,
    api_key: str | None = None,
    *,
    provider_type: str = "builtin",
    configuration: dict[str, Any] | None = None,
    adapter_code: str | None = None,
) -> BaseWebSearchProvider:
    normalized = str(provider_name or "tavily").strip().lower()
    normalized_type = str(provider_type or "builtin").strip().lower()
    if normalized_type == "generic_rest":
        return GenericRestWebSearchProvider(
            name=normalized,
            configuration=configuration or {},
            api_key=api_key,
        )
    builtin_code = str(adapter_code or normalized).strip().lower()
    if builtin_code == "tavily":
        return TavilyWebSearchProvider(api_key=api_key)
    if builtin_code == "brave":
        return BraveWebSearchProvider(api_key=api_key)
    raise WebSearchProviderError(f"Unsupported web search provider: {provider_name}")


def get_web_search_provider_statuses() -> dict[str, dict[str, str | bool]]:
    return {
        "tavily": {
            "label": "Tavily",
            "configured": bool(settings.TAVILY_API_KEY),
            "message": "Configured" if settings.TAVILY_API_KEY else "API key not configured",
        },
        "brave": {
            "label": "Brave",
            "configured": bool(settings.BRAVE_SEARCH_API_KEY),
            "message": "Configured" if settings.BRAVE_SEARCH_API_KEY else "API key not configured",
        },
    }
