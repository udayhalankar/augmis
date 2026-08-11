from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from app.core.config import settings


FREELANCER_API_VERSION = "0.1"
FREELANCER_TIMEOUT_SECONDS = 20
FREELANCER_MAX_LIMIT = 50
FREELANCER_AUTH_HEADER = "freelancer-oauth-v1"


class FreelancerApiError(RuntimeError):
    def __init__(
        self,
        user_message: str,
        *,
        provider_message: str | None = None,
        http_status: int | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.provider_message = provider_message
        self.http_status = http_status
        self.request_id = request_id

    def to_diagnostic(self) -> dict[str, Any]:
        return {
            "provider_http_status": self.http_status,
            "provider_message": self.provider_message,
            "request_id": self.request_id,
        }


def _safe_json(response: requests.Response) -> dict[str, Any] | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _safe_provider_message(response: requests.Response) -> str | None:
    payload = _safe_json(response)
    if isinstance(payload, dict):
        for key in ("message", "detail", "error", "description"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return " ".join(value.split()).strip()[:240]
        result = payload.get("result")
        if isinstance(result, dict):
            for key in ("message", "error", "detail", "description"):
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    return " ".join(value.split()).strip()[:240]
    text = " ".join((response.text or "").split()).strip()
    return text[:240] if text else None


def _request_id(response: requests.Response) -> str | None:
    for key in ("x-request-id", "request-id", "trace-id"):
        value = response.headers.get(key)
        if value and value.strip():
            return value.strip()
    return None


def _raise_for_response(response: requests.Response, fallback: str) -> None:
    if response.ok:
        return
    provider_message = _safe_provider_message(response)
    status_code = response.status_code
    if status_code == 401:
        user_message = "Freelancer authentication failed."
    elif status_code == 403:
        user_message = "Freelancer access was denied."
    elif status_code == 429:
        user_message = "Freelancer API rate limit reached. Try again later."
    elif 500 <= status_code < 600:
        user_message = "Freelancer API is temporarily unavailable."
    else:
        user_message = fallback
    raise FreelancerApiError(
        user_message,
        provider_message=provider_message,
        http_status=status_code,
        request_id=_request_id(response),
    )


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        if candidate.isdigit():
            try:
                return datetime.fromtimestamp(float(candidate), tz=timezone.utc)
            except Exception:
                return None
        try:
            parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
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


def _job_name(job: dict[str, Any]) -> str | None:
    for key in ("name", "seo_name", "label"):
        value = job.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _job_category(job: dict[str, Any]) -> str | None:
    category = job.get("category")
    if isinstance(category, dict):
        value = category.get("name")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


@dataclass
class FreelancerProject:
    project_id: str
    title: str
    description: str | None
    seo_url: str | None
    project_type: str | None
    status: str | None
    currency_code: str | None
    budget_min: float | None
    budget_max: float | None
    bid_count: int | None
    bid_avg: float | None
    client_country: str | None
    client_location: str | None
    client_rating: float | None
    client_review_count: int | None
    client_payment_verified: bool | None
    client_projects_posted: int | None
    client_projects_completed: int | None
    client_username: str | None
    skills: list[str]
    categories: list[str]
    posted_at: datetime | None
    updated_at: datetime | None
    bid_end_at: datetime | None
    raw_project: dict[str, Any]


class FreelancerClient:
    def __init__(
        self,
        *,
        access_token: str,
        base_url: str | None = None,
        timeout_seconds: int = FREELANCER_TIMEOUT_SECONDS,
    ) -> None:
        self.access_token = access_token.strip()
        self.base_url = (base_url or settings.FREELANCER_API_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {
            FREELANCER_AUTH_HEADER: self.access_token,
            "Accept": "application/json",
        }

    def _get(self, path: str, *, params: list[tuple[str, Any]] | None = None) -> dict[str, Any]:
        try:
            response = requests.get(
                f"{self.base_url}{path}",
                headers=self._headers(),
                params=params or [],
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise FreelancerApiError("Freelancer API request timed out.") from exc
        except requests.RequestException as exc:
            raise FreelancerApiError("Freelancer API request failed.") from exc
        _raise_for_response(response, "Freelancer API request was rejected.")
        payload = _safe_json(response)
        if not isinstance(payload, dict):
            raise FreelancerApiError("Freelancer API returned an invalid response.")
        return payload

    def test_connection(self) -> dict[str, Any]:
        payload = self._get(f"/users/{FREELANCER_API_VERSION}/self")
        result = payload.get("result")
        user_id = None
        if isinstance(result, dict):
            if isinstance(result.get("id"), (int, str)):
                user_id = str(result["id"])
            elif isinstance(result.get("user"), dict) and isinstance(result["user"].get("id"), (int, str)):
                user_id = str(result["user"]["id"])
        return {
            "success": True,
            "provider": "freelancer",
            "message": "Freelancer access token is configured and the official API is reachable.",
            "account_id": user_id,
        }

    def resolve_job_ids(self, job_names: list[str]) -> dict[str, int]:
        cleaned = []
        seen: set[str] = set()
        for name in job_names:
            normalized = " ".join(str(name or "").split()).strip()
            key = normalized.lower()
            if normalized and key not in seen:
                cleaned.append(normalized)
                seen.add(key)
        if not cleaned:
            return {}
        payload = self._get(
            f"/projects/{FREELANCER_API_VERSION}/jobs/search/",
            params=[("job_names[]", name) for name in cleaned],
        )
        result = payload.get("result")
        jobs = result.get("jobs") if isinstance(result, dict) else None
        mapping: dict[str, int] = {}
        for item in _as_list(jobs):
            if not isinstance(item, dict):
                continue
            name = _job_name(item)
            job_id = item.get("id")
            if name and isinstance(job_id, int):
                mapping[name.lower()] = job_id
        return mapping

    def search_projects(
        self,
        *,
        query: str,
        limit: int,
        project_type: str | None = None,
        job_ids: list[int] | None = None,
        min_budget: float | None = None,
        max_budget: float | None = None,
        max_bid_count: int | None = None,
    ) -> dict[str, Any]:
        bounded_limit = max(1, min(limit, FREELANCER_MAX_LIMIT))
        params: list[tuple[str, Any]] = [
            ("query", query),
            ("limit", bounded_limit),
            ("compact", "true"),
            ("job_details", "true"),
        ]
        if project_type in {"fixed", "hourly"}:
            params.append(("project_types[]", project_type))
        for job_id in job_ids or []:
            params.append(("jobs[]", job_id))
        if min_budget is not None:
            params.append(
                ("min_avg_hourly_rate" if project_type == "hourly" else "min_avg_price", min_budget)
            )
        if max_budget is not None:
            params.append(
                ("max_avg_hourly_rate" if project_type == "hourly" else "max_avg_price", max_budget)
            )
        payload = self._get(f"/projects/{FREELANCER_API_VERSION}/projects/active/", params=params)
        result = payload.get("result")
        items = result.get("projects") if isinstance(result, dict) else []
        projects: list[FreelancerProject] = []
        filtered_bid_count = 0
        for item in _as_list(items):
            if not isinstance(item, dict):
                continue
            project = self._normalize_project(item)
            if max_bid_count is not None and project.bid_count is not None and project.bid_count > max_bid_count:
                filtered_bid_count += 1
                continue
            projects.append(project)
        return {
            "provider": "freelancer",
            "query": query,
            "api_call_count": 1,
            "raw_count": len(_as_list(items)),
            "filtered_bid_count": filtered_bid_count,
            "projects": projects,
        }

    def _normalize_project(self, payload: dict[str, Any]) -> FreelancerProject:
        budget = payload.get("budget") if isinstance(payload.get("budget"), dict) else {}
        currency_payload = payload.get("currency") if isinstance(payload.get("currency"), dict) else {}
        owner = payload.get("owner") if isinstance(payload.get("owner"), dict) else {}
        location = owner.get("location") if isinstance(owner.get("location"), dict) else {}
        bid_stats = payload.get("bid_stats") if isinstance(payload.get("bid_stats"), dict) else {}
        jobs = [job for job in _as_list(payload.get("jobs")) if isinstance(job, dict)]
        project_id = payload.get("id")
        if project_id is None:
            raise FreelancerApiError("Freelancer API returned a project without an id.")
        title = str(payload.get("title") or "").strip()
        if not title:
            raise FreelancerApiError("Freelancer API returned a project without a title.")
        rating_value = owner.get("reputation") if owner.get("reputation") is not None else owner.get("employer_reputation")
        rating = float(rating_value) if isinstance(rating_value, (int, float)) else None
        review_value = owner.get("reviews") if owner.get("reviews") is not None else owner.get("review_count")
        review_count = int(review_value) if isinstance(review_value, (int, float)) else None
        posted_count_value = owner.get("jobs_posted_count") if owner.get("jobs_posted_count") is not None else owner.get("projects_posted")
        completed_count_value = owner.get("jobs_completed_count") if owner.get("jobs_completed_count") is not None else owner.get("projects_completed")
        country_name = None
        if isinstance(location.get("country"), dict):
            country_name = location["country"].get("name")
        if not country_name and isinstance(owner.get("country"), dict):
            country_name = owner["country"].get("name")
        city_name = location.get("city") if isinstance(location.get("city"), str) else None
        if not city_name and isinstance(location.get("city"), dict):
            city_name = location["city"].get("name")
        return FreelancerProject(
            project_id=str(project_id),
            title=title,
            description=(str(payload.get("description") or "").strip() or str(payload.get("preview_description") or "").strip() or None),
            seo_url=str(payload.get("seo_url")).strip() if isinstance(payload.get("seo_url"), str) and str(payload.get("seo_url")).strip() else None,
            project_type=str(payload.get("type")).strip().lower() if isinstance(payload.get("type"), str) and str(payload.get("type")).strip() else None,
            status=str(payload.get("status")).strip().lower() if isinstance(payload.get("status"), str) and str(payload.get("status")).strip() else None,
            currency_code=str(currency_payload.get("code")).strip().upper() if isinstance(currency_payload.get("code"), str) and str(currency_payload.get("code")).strip() else None,
            budget_min=float(budget.get("minimum")) if isinstance(budget.get("minimum"), (int, float)) else None,
            budget_max=float(budget.get("maximum")) if isinstance(budget.get("maximum"), (int, float)) else None,
            bid_count=int(bid_stats.get("bid_count")) if isinstance(bid_stats.get("bid_count"), (int, float)) else None,
            bid_avg=float(bid_stats.get("bid_avg")) if isinstance(bid_stats.get("bid_avg"), (int, float)) else None,
            client_country=country_name.strip() if isinstance(country_name, str) and country_name.strip() else None,
            client_location=city_name.strip() if isinstance(city_name, str) and city_name.strip() else None,
            client_rating=rating,
            client_review_count=review_count,
            client_payment_verified=bool(owner.get("payment_verified")) if owner.get("payment_verified") is not None else None,
            client_projects_posted=int(posted_count_value) if isinstance(posted_count_value, (int, float)) else None,
            client_projects_completed=int(completed_count_value) if isinstance(completed_count_value, (int, float)) else None,
            client_username=str(owner.get("username")).strip() if isinstance(owner.get("username"), str) and str(owner.get("username")).strip() else None,
            skills=[name for name in (_job_name(job) for job in jobs) if name],
            categories=[name for name in (_job_category(job) for job in jobs) if name],
            posted_at=_parse_datetime(payload.get("time_submitted")),
            updated_at=_parse_datetime(payload.get("time_updated")),
            bid_end_at=_parse_datetime(payload.get("submitdate")),
            raw_project=payload,
        )
