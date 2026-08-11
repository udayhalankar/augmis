from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from app.core.config import settings


class ExternalWorkProviderError(RuntimeError):
    pass


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            return datetime.fromtimestamp(float(text), tz=timezone.utc)
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _request_json(url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
    try:
        response = requests.get(url, params=params or {}, headers=headers or {}, timeout=20)
    except requests.Timeout as exc:
        raise ExternalWorkProviderError("Provider request timed out.") from exc
    except requests.RequestException as exc:
        raise ExternalWorkProviderError("Provider request failed.") from exc
    if response.status_code in {401, 403}:
        raise ExternalWorkProviderError("Provider credentials were rejected.")
    if response.status_code == 429:
        raise ExternalWorkProviderError("Provider rate limit reached.")
    if not response.ok:
        raise ExternalWorkProviderError("Provider request was rejected.")
    try:
        return response.json()
    except ValueError as exc:
        raise ExternalWorkProviderError("Provider returned an invalid JSON response.") from exc


@dataclass
class ExternalWorkOpportunity:
    external_id: str
    provider: str
    source_name: str
    title: str
    description: str | None
    source_url: str | None
    company_name: str | None
    company_url: str | None
    location: str | None
    country: str | None
    region: str | None
    remote: bool | None
    employment_type: str | None
    engagement_type: str | None
    salary_min: float | None
    salary_max: float | None
    salary_currency: str | None
    salary_period: str | None
    posted_at: datetime | None
    expires_at: datetime | None
    category: str | None
    tags: list[str]
    skills: list[str]
    raw_payload: dict[str, Any]


class ExternalWorkOpportunityProvider:
    provider_code: str
    provider_name: str

    def test_connection(self, configuration: dict[str, Any], credential_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        results = self.search_opportunities(configuration, credential_payload=credential_payload, max_results=1)
        return {
            "success": True,
            "provider": self.provider_code,
            "message": f"{self.provider_name} endpoint is reachable.",
            "result_count": len(results),
        }

    def search_opportunities(
        self,
        configuration: dict[str, Any],
        credential_payload: dict[str, Any] | None = None,
        *,
        max_results: int | None = None,
    ) -> list[ExternalWorkOpportunity]:
        raise NotImplementedError


class RemoteOkProvider(ExternalWorkOpportunityProvider):
    provider_code = "remoteok"
    provider_name = "Remote OK"
    api_url = "https://remoteok.com/api"

    def search_opportunities(self, configuration: dict[str, Any], credential_payload: dict[str, Any] | None = None, *, max_results: int | None = None) -> list[ExternalWorkOpportunity]:
        del credential_payload
        payload = _request_json(self.api_url)
        if not isinstance(payload, list):
            raise ExternalWorkProviderError("Remote OK returned an invalid payload.")
        items = [item for item in payload if isinstance(item, dict) and item.get("id")]
        limit = int(max_results or configuration.get("maximum_results", 50) or 50)
        results: list[ExternalWorkOpportunity] = []
        for item in items[:limit]:
            tags = [str(tag).strip() for tag in _as_list(item.get("tags")) if str(tag).strip()]
            results.append(
                ExternalWorkOpportunity(
                    external_id=str(item["id"]),
                    provider=self.provider_code,
                    source_name=self.provider_name,
                    title=str(item.get("position") or item.get("title") or "").strip(),
                    description=str(item.get("description") or "").strip() or None,
                    source_url=str(item.get("url") or item.get("apply_url") or "").strip() or None,
                    company_name=str(item.get("company") or "").strip() or None,
                    company_url=str(item.get("company_logo") or "").strip() or None,
                    location=str(item.get("location") or "").strip() or None,
                    country=None,
                    region=None,
                    remote=True if item.get("location") else None,
                    employment_type=str(item.get("employment_type") or "").strip() or None,
                    engagement_type=str(item.get("employment_type") or "").strip().lower().replace(" ", "_") or "unknown",
                    salary_min=float(item["salary_min"]) if isinstance(item.get("salary_min"), (int, float)) else None,
                    salary_max=float(item["salary_max"]) if isinstance(item.get("salary_max"), (int, float)) else None,
                    salary_currency=str(item.get("salary_currency") or "").strip().upper() or None,
                    salary_period=None,
                    posted_at=_parse_datetime(item.get("date") or item.get("epoch")),
                    expires_at=None,
                    category=str(item.get("category") or "").strip() or None,
                    tags=tags,
                    skills=tags,
                    raw_payload=item,
                )
            )
        return results


class ArbeitnowProvider(ExternalWorkOpportunityProvider):
    provider_code = "arbeitnow"
    provider_name = "Arbeitnow"
    api_url = "https://www.arbeitnow.com/api/job-board-api"

    def search_opportunities(self, configuration: dict[str, Any], credential_payload: dict[str, Any] | None = None, *, max_results: int | None = None) -> list[ExternalWorkOpportunity]:
        del credential_payload
        params: dict[str, Any] = {}
        if configuration.get("remote_only"):
            params["remote"] = "true"
        payload = _request_json(self.api_url, params=params)
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise ExternalWorkProviderError("Arbeitnow returned an invalid payload.")
        limit = int(max_results or configuration.get("maximum_results", 50) or 50)
        results: list[ExternalWorkOpportunity] = []
        for item in data[:limit]:
            if not isinstance(item, dict):
                continue
            tags = [str(tag).strip() for tag in _as_list(item.get("tags")) if str(tag).strip()]
            job_types = [str(tag).strip() for tag in _as_list(item.get("job_types")) if str(tag).strip()]
            results.append(
                ExternalWorkOpportunity(
                    external_id=str(item.get("slug") or item.get("id") or item.get("url") or "").strip(),
                    provider=self.provider_code,
                    source_name=self.provider_name,
                    title=str(item.get("title") or "").strip(),
                    description=str(item.get("description") or "").strip() or None,
                    source_url=str(item.get("url") or "").strip() or None,
                    company_name=str(item.get("company_name") or "").strip() or None,
                    company_url=None,
                    location=str(item.get("location") or "").strip() or None,
                    country=None,
                    region=None,
                    remote=bool(item.get("remote")) if item.get("remote") is not None else None,
                    employment_type=", ".join(job_types) or None,
                    engagement_type=job_types[0].strip().lower().replace(" ", "_") if job_types else ("contract" if item.get("remote") else "unknown"),
                    salary_min=None,
                    salary_max=None,
                    salary_currency=None,
                    salary_period=None,
                    posted_at=_parse_datetime(item.get("created_at")),
                    expires_at=None,
                    category=None,
                    tags=tags + job_types,
                    skills=tags,
                    raw_payload=item,
                )
            )
        return results


class RemotiveProvider(ExternalWorkOpportunityProvider):
    provider_code = "remotive"
    provider_name = "Remotive"
    api_url = "https://remotive.com/api/remote-jobs"

    def search_opportunities(self, configuration: dict[str, Any], credential_payload: dict[str, Any] | None = None, *, max_results: int | None = None) -> list[ExternalWorkOpportunity]:
        del credential_payload
        params: dict[str, Any] = {}
        search_term = str(configuration.get("search_keyword") or "").strip()
        if search_term:
            params["search"] = search_term
        category = str(configuration.get("category") or "").strip()
        if category:
            params["category"] = category
        payload = _request_json(self.api_url, params=params)
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise ExternalWorkProviderError("Remotive returned an invalid payload.")
        limit = int(max_results or configuration.get("maximum_results", 50) or 50)
        results: list[ExternalWorkOpportunity] = []
        for item in jobs[:limit]:
            if not isinstance(item, dict):
                continue
            tags = [str(tag).strip() for tag in _as_list(item.get("tags")) if str(tag).strip()]
            results.append(
                ExternalWorkOpportunity(
                    external_id=str(item.get("id") or item.get("url") or "").strip(),
                    provider=self.provider_code,
                    source_name=self.provider_name,
                    title=str(item.get("title") or "").strip(),
                    description=str(item.get("description") or "").strip() or None,
                    source_url=str(item.get("url") or "").strip() or None,
                    company_name=str(item.get("company_name") or "").strip() or None,
                    company_url=str(item.get("company_logo_url") or "").strip() or None,
                    location=str(item.get("candidate_required_location") or "").strip() or None,
                    country=None,
                    region=None,
                    remote=True,
                    employment_type=str(item.get("job_type") or "").strip() or None,
                    engagement_type=str(item.get("job_type") or "").strip().lower().replace(" ", "_") or "unknown",
                    salary_min=None,
                    salary_max=None,
                    salary_currency=None,
                    salary_period=None,
                    posted_at=_parse_datetime(item.get("publication_date")),
                    expires_at=None,
                    category=str(item.get("category") or "").strip() or None,
                    tags=tags,
                    skills=tags,
                    raw_payload=item,
                )
            )
        return results


class AdzunaProvider(ExternalWorkOpportunityProvider):
    provider_code = "adzuna"
    provider_name = "Adzuna"
    api_url = "https://api.adzuna.com/v1/api"
    supported_countries = {"us", "gb", "ca", "in", "au", "de"}

    def search_opportunities(self, configuration: dict[str, Any], credential_payload: dict[str, Any] | None = None, *, max_results: int | None = None) -> list[ExternalWorkOpportunity]:
        payload = credential_payload or {}
        app_id = str(payload.get("app_id") or settings.ADZUNA_APP_ID or "").strip()
        app_key = str(payload.get("app_key") or settings.ADZUNA_APP_KEY or "").strip()
        if not app_id or not app_key:
            raise ExternalWorkProviderError("Adzuna credentials are not configured.")
        countries = [
            str(code).strip().lower()
            for code in _as_list(configuration.get("target_countries_json"))
            if str(code).strip().lower() in self.supported_countries
        ][:5]
        if not countries:
            countries = ["gb"]
        query = str(configuration.get("search_keyword") or "software developer").strip() or "software developer"
        results_per_page = min(int(max_results or configuration.get("maximum_results", 25) or 25), 50)
        results: list[ExternalWorkOpportunity] = []
        for country in countries:
            data = _request_json(
                f"{self.api_url}/jobs/{country}/search/1",
                params={
                    "app_id": app_id,
                    "app_key": app_key,
                    "results_per_page": results_per_page,
                    "what": query,
                },
            )
            jobs = data.get("results") if isinstance(data, dict) else None
            if not isinstance(jobs, list):
                raise ExternalWorkProviderError("Adzuna returned an invalid payload.")
            for item in jobs:
                if not isinstance(item, dict):
                    continue
                category = item.get("category") if isinstance(item.get("category"), dict) else {}
                company = item.get("company") if isinstance(item.get("company"), dict) else {}
                location = item.get("location") if isinstance(item.get("location"), dict) else {}
                area = [str(part).strip() for part in _as_list(location.get("area")) if str(part).strip()]
                results.append(
                    ExternalWorkOpportunity(
                        external_id=str(item.get("id") or item.get("redirect_url") or "").strip(),
                        provider=self.provider_code,
                        source_name=self.provider_name,
                        title=str(item.get("title") or "").strip(),
                        description=str(item.get("description") or "").strip() or None,
                        source_url=str(item.get("redirect_url") or "").strip() or None,
                        company_name=str(company.get("display_name") or "").strip() or None,
                        company_url=None,
                        location=str(location.get("display_name") or "").strip() or None,
                        country=country.upper(),
                        region=area[-1] if area else None,
                        remote=None,
                        employment_type=str(item.get("contract_type") or item.get("contract_time") or "").strip() or None,
                        engagement_type=str(item.get("contract_type") or item.get("contract_time") or "").strip().lower().replace(" ", "_") or "unknown",
                        salary_min=float(item["salary_min"]) if isinstance(item.get("salary_min"), (int, float)) else None,
                        salary_max=float(item["salary_max"]) if isinstance(item.get("salary_max"), (int, float)) else None,
                        salary_currency=None,
                        salary_period=None,
                        posted_at=_parse_datetime(item.get("created")),
                        expires_at=None,
                        category=str(category.get("label") or "").strip() or None,
                        tags=[str(category.get("label")).strip()] if category.get("label") else [],
                        skills=[],
                        raw_payload=item,
                    )
                )
        return results[:results_per_page * len(countries)]


def get_external_work_provider(provider_code: str) -> ExternalWorkOpportunityProvider:
    normalized = str(provider_code or "").strip().lower()
    mapping: dict[str, ExternalWorkOpportunityProvider] = {
        "remoteok": RemoteOkProvider(),
        "arbeitnow": ArbeitnowProvider(),
        "remotive": RemotiveProvider(),
        "adzuna": AdzunaProvider(),
    }
    provider = mapping.get(normalized)
    if not provider:
        raise ExternalWorkProviderError("External work provider is not supported.")
    return provider
