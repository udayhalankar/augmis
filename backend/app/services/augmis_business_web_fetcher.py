from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urljoin, urlsplit

import requests

from app.core.config import settings


SCRIPT_STYLE_PATTERN = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "::1"}
BLOCKED_IPS = {
    ipaddress.ip_address("169.254.169.254"),
}


class SafeWebFetchError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "UNKNOWN_FETCH_ERROR",
        retryable: bool = False,
        http_status: int | None = None,
        final_url: str | None = None,
        redirect_count: int = 0,
        redirect_chain: list[dict[str, str | int | None]] | None = None,
        content_type: str | None = None,
        response_bytes: int | None = None,
        exception_class: str | None = None,
        attempted_at: datetime | None = None,
        server: str | None = None,
        retry_after: str | None = None,
        dns_result: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.http_status = http_status
        self.final_url = final_url
        self.redirect_count = redirect_count
        self.redirect_chain = redirect_chain or []
        self.content_type = content_type
        self.response_bytes = response_bytes
        self.exception_class = exception_class
        self.attempted_at = attempted_at or datetime.now(timezone.utc)
        self.server = server
        self.retry_after = retry_after
        self.dns_result = dns_result or []

    def to_diagnostic(self) -> dict[str, str | int | bool | list[dict[str, str | int | None]] | list[str] | None]:
        return {
            "error_code": self.code,
            "error_message": str(self),
            "http_status": self.http_status,
            "final_url": self.final_url,
            "redirect_count": self.redirect_count,
            "redirect_chain": self.redirect_chain[:8],
            "content_type": self.content_type,
            "response_bytes": self.response_bytes,
            "exception_class": self.exception_class,
            "attempted_at": self.attempted_at.isoformat(),
            "retryable": self.retryable,
            "server": self.server,
            "retry_after": self.retry_after,
            "dns_result": self.dns_result[:8],
        }


@dataclass(frozen=True)
class WebFetchRuntimePolicy:
    fetch_source_page: bool = True
    max_fetch_bytes: int = 100000
    fetch_timeout_seconds: int = 10
    max_extracted_text_chars: int = 30000
    max_redirects: int = 3
    user_agent: str = "AUGMIS-Web-Listener/1.0"
    accept_language: str = "en-US,en;q=0.8"


def _is_public_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if ip in BLOCKED_IPS:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve_public_http_url(url: str) -> tuple[str, list[str]]:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise SafeWebFetchError("Unsupported URL scheme for source fetch.", code="INVALID_URL")
    if not parts.hostname:
        raise SafeWebFetchError("Source URL hostname is missing.", code="INVALID_URL")
    hostname = parts.hostname.lower()
    if hostname in BLOCKED_HOSTS:
        raise SafeWebFetchError("Localhost and loopback addresses are not allowed.", code="INVALID_URL")
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise SafeWebFetchError(
            "Source hostname could not be resolved.",
            code="DNS_FAILURE",
            retryable=True,
            exception_class=type(exc).__name__,
        ) from exc
    resolved_ips: list[str] = []
    for info in infos:
        ip = info[4][0]
        if ip not in resolved_ips:
            resolved_ips.append(ip)
        if not _is_public_ip(ip):
            raise SafeWebFetchError(
                "Private or local network targets are not allowed.",
                code="DNS_REBIND_BLOCKED",
                dns_result=resolved_ips,
            )
    return hostname, resolved_ips


def validate_public_http_url(url: str) -> None:
    _resolve_public_http_url(url)


def default_web_fetch_runtime_policy() -> WebFetchRuntimePolicy:
    return WebFetchRuntimePolicy(
        fetch_source_page=True,
        max_fetch_bytes=settings.AUGMIS_WEB_FETCH_MAX_BYTES,
        fetch_timeout_seconds=settings.AUGMIS_WEB_FETCH_TIMEOUT_SECONDS,
        max_extracted_text_chars=min(settings.AUGMIS_WEB_FETCH_MAX_BYTES, 30000),
        max_redirects=settings.AUGMIS_WEB_FETCH_MAX_REDIRECTS,
        user_agent=settings.AUGMIS_WEB_DISCOVERY_USER_AGENT or "AUGMISOpportunityBot/1.0",
        accept_language="en-US,en;q=0.8",
    )


def _request_headers(policy: WebFetchRuntimePolicy, referer: str | None) -> dict[str, str]:
    headers = {
        "User-Agent": policy.user_agent,
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
        "Accept-Language": policy.accept_language,
        "Accept-Encoding": "gzip, deflate, br",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def _safe_header_value(value: str | None, *, limit: int = 200) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned[:limit]


def _content_type_allowed(content_type: str | None, allowed_content_types: tuple[str, ...]) -> bool:
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    return any(normalized == allowed for allowed in allowed_content_types)


def _classify_connection_error(exc: requests.ConnectionError) -> tuple[str, str, bool]:
    lowered = str(exc).lower()
    if "name or service not known" in lowered or "nodename nor servname provided" in lowered or "temporary failure in name resolution" in lowered:
        return "DNS_FAILURE", "Source hostname could not be resolved.", True
    if "connection reset" in lowered or "connection aborted" in lowered:
        return "CONNECTION_RESET", "Connection was reset while fetching the source page.", True
    if "refused" in lowered:
        return "CONNECTION_RESET", "Connection was refused while fetching the source page.", True
    return "UNKNOWN_FETCH_ERROR", "Source page fetch failed.", True


def _classify_redirect_target(url: str) -> str | None:
    lowered = url.lower()
    if any(term in lowered for term in ("stalesession", "stale_session", "sessionexpired", "session_expired", "invalidsession", "invalid_session")):
        return "STALE_SESSION"
    if any(term in lowered for term in ("/login", "/signin", "/sign-in", "/authenticate", "/auth", "login.jsp", "sessionexpired")):
        return "SESSION_REQUIRED"
    return None


def _fetch_public_text_resource(
    url: str,
    *,
    policy: WebFetchRuntimePolicy | None = None,
    allowed_content_types: tuple[str, ...] = ("text/html", "text/plain"),
    session: requests.Session | None = None,
    referer: str | None = None,
) -> dict[str, str | int | list[str] | list[dict[str, str | int | None]] | None]:
    _, initial_dns_result = _resolve_public_http_url(url)
    current_url = url
    runtime_policy = policy or default_web_fetch_runtime_policy()
    timeout = runtime_policy.fetch_timeout_seconds
    max_bytes = runtime_policy.max_fetch_bytes
    active_session = session or requests.Session()
    own_session = session is None
    redirect_chain: list[dict[str, str | int | None]] = []
    try:
        for _ in range(runtime_policy.max_redirects + 1):
            _, dns_result = _resolve_public_http_url(current_url)
            attempted_at = datetime.now(timezone.utc)
            try:
                response = active_session.get(
                    current_url,
                    timeout=timeout,
                    allow_redirects=False,
                    headers=_request_headers(runtime_policy, referer),
                    stream=True,
                )
            except requests.ConnectTimeout as exc:
                raise SafeWebFetchError(
                    "Source page connection timed out.",
                    code="CONNECTION_TIMEOUT",
                    retryable=True,
                    final_url=current_url,
                    redirect_count=len(redirect_chain),
                    redirect_chain=redirect_chain,
                    exception_class=type(exc).__name__,
                    attempted_at=attempted_at,
                    dns_result=dns_result,
                ) from exc
            except requests.ReadTimeout as exc:
                raise SafeWebFetchError(
                    "Source page read timed out.",
                    code="READ_TIMEOUT",
                    retryable=True,
                    final_url=current_url,
                    redirect_count=len(redirect_chain),
                    redirect_chain=redirect_chain,
                    exception_class=type(exc).__name__,
                    attempted_at=attempted_at,
                    dns_result=dns_result,
                ) from exc
            except requests.exceptions.SSLError as exc:
                raise SafeWebFetchError(
                    "TLS validation failed while fetching the source page.",
                    code="TLS_ERROR",
                    final_url=current_url,
                    redirect_count=len(redirect_chain),
                    redirect_chain=redirect_chain,
                    exception_class=type(exc).__name__,
                    attempted_at=attempted_at,
                    dns_result=dns_result,
                ) from exc
            except requests.ConnectionError as exc:
                code, message, retryable = _classify_connection_error(exc)
                raise SafeWebFetchError(
                    message,
                    code=code,
                    retryable=retryable,
                    final_url=current_url,
                    redirect_count=len(redirect_chain),
                    redirect_chain=redirect_chain,
                    exception_class=type(exc).__name__,
                    attempted_at=attempted_at,
                    dns_result=dns_result,
                ) from exc
            except requests.RequestException as exc:
                raise SafeWebFetchError(
                    "Source page fetch failed.",
                    code="UNKNOWN_FETCH_ERROR",
                    retryable=True,
                    final_url=current_url,
                    redirect_count=len(redirect_chain),
                    redirect_chain=redirect_chain,
                    exception_class=type(exc).__name__,
                    attempted_at=attempted_at,
                    dns_result=dns_result,
                ) from exc

            server = _safe_header_value(response.headers.get("Server"), limit=120)
            retry_after = _safe_header_value(response.headers.get("Retry-After"), limit=80)
            content_type = _safe_header_value(response.headers.get("Content-Type"))

            if 300 <= response.status_code < 400:
                location = response.headers.get("Location")
                if not location:
                    raise SafeWebFetchError(
                        "Redirect response missing Location header.",
                        code="UNKNOWN_FETCH_ERROR",
                        final_url=current_url,
                        http_status=response.status_code,
                        redirect_count=len(redirect_chain),
                        redirect_chain=redirect_chain,
                        content_type=content_type,
                        attempted_at=attempted_at,
                        server=server,
                        retry_after=retry_after,
                        dns_result=dns_result,
                    )
                redirected = urljoin(current_url, location)
                decision = _classify_redirect_target(redirected)
                redirect_chain.append(
                    {
                        "status": response.status_code,
                        "host": urlsplit(redirected).hostname,
                        "path": urlsplit(redirected).path,
                        "decision": decision or "follow",
                    }
                )
                try:
                    _resolve_public_http_url(redirected)
                except SafeWebFetchError as exc:
                    if exc.code == "DNS_REBIND_BLOCKED":
                        raise SafeWebFetchError(
                            "Redirect destination was blocked by public-network policy.",
                            code="REDIRECT_BLOCKED_PRIVATE_IP",
                            final_url=redirected,
                            http_status=response.status_code,
                            redirect_count=len(redirect_chain),
                            redirect_chain=redirect_chain,
                            content_type=content_type,
                            attempted_at=attempted_at,
                            server=server,
                            retry_after=retry_after,
                            dns_result=exc.dns_result,
                        ) from exc
                    raise
                if decision == "STALE_SESSION":
                    raise SafeWebFetchError(
                        "Redirected to a stale-session page.",
                        code="STALE_SESSION",
                        final_url=redirected,
                        http_status=response.status_code,
                        redirect_count=len(redirect_chain),
                        redirect_chain=redirect_chain,
                        content_type=content_type,
                        attempted_at=attempted_at,
                        server=server,
                        retry_after=retry_after,
                        dns_result=dns_result,
                    )
                if decision == "SESSION_REQUIRED":
                    raise SafeWebFetchError(
                        "Redirected to a login or session-gated page.",
                        code="SESSION_REQUIRED",
                        final_url=redirected,
                        http_status=response.status_code,
                        redirect_count=len(redirect_chain),
                        redirect_chain=redirect_chain,
                        content_type=content_type,
                        attempted_at=attempted_at,
                        server=server,
                        retry_after=retry_after,
                        dns_result=dns_result,
                    )
                referer = current_url
                current_url = redirected
                continue

            if response.status_code >= 400:
                code = "HTTP_5XX" if response.status_code >= 500 else f"HTTP_{response.status_code}"
                retryable = response.status_code in {429, 500, 502, 503, 504}
                raise SafeWebFetchError(
                    f"Source page returned HTTP {response.status_code}.",
                    code=code,
                    retryable=retryable,
                    http_status=response.status_code,
                    final_url=current_url,
                    redirect_count=len(redirect_chain),
                    redirect_chain=redirect_chain,
                    content_type=content_type,
                    attempted_at=attempted_at,
                    server=server,
                    retry_after=retry_after,
                    dns_result=dns_result,
                )

            if not _content_type_allowed(content_type, allowed_content_types):
                raise SafeWebFetchError(
                    "Unsupported source content type.",
                    code="CONTENT_TYPE_REJECTED",
                    http_status=response.status_code,
                    final_url=current_url,
                    redirect_count=len(redirect_chain),
                    redirect_chain=redirect_chain,
                    content_type=content_type,
                    attempted_at=attempted_at,
                    server=server,
                    retry_after=retry_after,
                    dns_result=dns_result,
                )

            chunks: list[bytes] = []
            total = 0
            try:
                for chunk in response.iter_content(chunk_size=4096):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        raise SafeWebFetchError(
                            "Source page exceeded the configured fetch size limit.",
                            code="BODY_TOO_LARGE",
                            http_status=response.status_code,
                            final_url=current_url,
                            redirect_count=len(redirect_chain),
                            redirect_chain=redirect_chain,
                            content_type=content_type,
                            response_bytes=total,
                            attempted_at=attempted_at,
                            server=server,
                            retry_after=retry_after,
                            dns_result=dns_result,
                        )
                    chunks.append(chunk)
            except requests.exceptions.ContentDecodingError as exc:
                raise SafeWebFetchError(
                    "Response decompression failed.",
                    code="DECOMPRESSION_ERROR",
                    retryable=True,
                    http_status=response.status_code,
                    final_url=current_url,
                    redirect_count=len(redirect_chain),
                    redirect_chain=redirect_chain,
                    content_type=content_type,
                    response_bytes=total,
                    exception_class=type(exc).__name__,
                    attempted_at=attempted_at,
                    server=server,
                    retry_after=retry_after,
                    dns_result=dns_result,
                ) from exc
            raw = b"".join(chunks).decode(response.encoding or response.apparent_encoding or "utf-8", errors="replace")
            if total == 0 or not raw.strip():
                raise SafeWebFetchError(
                    "Source page returned an empty response body.",
                    code="EMPTY_RESPONSE",
                    retryable=True,
                    http_status=response.status_code,
                    final_url=current_url,
                    redirect_count=len(redirect_chain),
                    redirect_chain=redirect_chain,
                    content_type=content_type,
                    response_bytes=total,
                    attempted_at=attempted_at,
                    server=server,
                    retry_after=retry_after,
                    dns_result=dns_result,
                )
            return {
                "url": current_url,
                "final_url": current_url,
                "status_code": response.status_code,
                "content_type": content_type,
                "body": raw,
                "bytes_read": total,
                "response_bytes": total,
                "redirect_count": len(redirect_chain),
                "redirect_chain": redirect_chain,
                "dns_result": dns_result or initial_dns_result,
                "server": server,
                "retry_after": retry_after,
            }
        raise SafeWebFetchError(
            "Source page exceeded maximum redirects.",
            code="REDIRECT_LIMIT",
            final_url=current_url,
            redirect_count=len(redirect_chain),
            redirect_chain=redirect_chain,
            dns_result=initial_dns_result,
        )
    finally:
        if own_session:
            active_session.close()


def fetch_public_webpage(
    url: str,
    *,
    policy: WebFetchRuntimePolicy | None = None,
    session: requests.Session | None = None,
    referer: str | None = None,
) -> dict[str, str | int | list[str] | list[dict[str, str | int | None]] | None]:
    return _fetch_public_text_resource(
        url,
        policy=policy,
        allowed_content_types=("text/html", "text/plain", "application/xhtml+xml"),
        session=session,
        referer=referer,
    )


def fetch_public_text_resource(
    url: str,
    *,
    policy: WebFetchRuntimePolicy | None = None,
    session: requests.Session | None = None,
    referer: str | None = None,
) -> dict[str, str | int | list[str] | list[dict[str, str | int | None]] | None]:
    return _fetch_public_text_resource(
        url,
        policy=policy,
        allowed_content_types=("text/plain", "text/html", "application/xhtml+xml", "application/xml", "text/xml"),
        session=session,
        referer=referer,
    )


def extract_text_from_webpage(
    html_text: str,
    *,
    max_chars: int | None = None,
) -> str:
    without_scripts = SCRIPT_STYLE_PATTERN.sub(" ", html_text)
    without_tags = TAG_PATTERN.sub(" ", without_scripts)
    cleaned = WHITESPACE_PATTERN.sub(" ", unescape(without_tags)).strip()
    limit = max_chars if max_chars is not None else default_web_fetch_runtime_policy().max_extracted_text_chars
    return cleaned[:limit]
