from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
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
    pass


@dataclass(frozen=True)
class WebFetchRuntimePolicy:
    fetch_source_page: bool = True
    max_fetch_bytes: int = 100000
    fetch_timeout_seconds: int = 10
    max_extracted_text_chars: int = 30000
    max_redirects: int = 3
    user_agent: str = "AUGMIS-Web-Listener/1.0"


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


def validate_public_http_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise SafeWebFetchError("Unsupported URL scheme for source fetch.")
    if not parts.hostname:
        raise SafeWebFetchError("Source URL hostname is missing.")
    hostname = parts.hostname.lower()
    if hostname in BLOCKED_HOSTS:
        raise SafeWebFetchError("Localhost and loopback addresses are not allowed.")
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise SafeWebFetchError("Source hostname could not be resolved.") from exc
    for info in infos:
        ip = info[4][0]
        if not _is_public_ip(ip):
            raise SafeWebFetchError("Private or local network targets are not allowed.")


def default_web_fetch_runtime_policy() -> WebFetchRuntimePolicy:
    return WebFetchRuntimePolicy(
        fetch_source_page=True,
        max_fetch_bytes=settings.AUGMIS_WEB_FETCH_MAX_BYTES,
        fetch_timeout_seconds=settings.AUGMIS_WEB_FETCH_TIMEOUT_SECONDS,
        max_extracted_text_chars=min(settings.AUGMIS_WEB_FETCH_MAX_BYTES, 30000),
        max_redirects=settings.AUGMIS_WEB_FETCH_MAX_REDIRECTS,
        user_agent=settings.AUGMIS_WEB_DISCOVERY_USER_AGENT or "AUGMIS-Web-Listener/1.0",
    )


def _fetch_public_text_resource(
    url: str,
    *,
    policy: WebFetchRuntimePolicy | None = None,
    allowed_content_types: tuple[str, ...] = ("text/html", "text/plain"),
) -> dict[str, str | int | None]:
    validate_public_http_url(url)
    current_url = url
    session = requests.Session()
    runtime_policy = policy or default_web_fetch_runtime_policy()
    timeout = runtime_policy.fetch_timeout_seconds
    max_bytes = runtime_policy.max_fetch_bytes
    for _ in range(runtime_policy.max_redirects + 1):
        try:
            response = session.get(
                current_url,
                timeout=timeout,
                allow_redirects=False,
                headers={"User-Agent": runtime_policy.user_agent},
                stream=True,
            )
        except requests.Timeout as exc:
            raise SafeWebFetchError("Source page fetch timed out.") from exc
        except requests.RequestException as exc:
            raise SafeWebFetchError("Source page fetch failed.") from exc

        if 300 <= response.status_code < 400:
            location = response.headers.get("Location")
            if not location:
                raise SafeWebFetchError("Redirect response missing Location header.")
            redirected = urljoin(current_url, location)
            validate_public_http_url(redirected)
            current_url = redirected
            continue

        if response.status_code >= 400:
            raise SafeWebFetchError(f"Source page returned HTTP {response.status_code}.")

        content_type = (response.headers.get("Content-Type") or "").lower()
        if not any(allowed in content_type for allowed in allowed_content_types):
            raise SafeWebFetchError("Unsupported source content type.")

        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=4096):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise SafeWebFetchError(
                    "Source page was larger than the configured fetch limit. Search-result evidence was retained, but full source content was not downloaded."
                )
            chunks.append(chunk)
        raw = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
        return {
            "url": current_url,
            "status_code": response.status_code,
            "content_type": content_type,
            "body": raw,
            "bytes_read": total,
        }
    raise SafeWebFetchError("Source page exceeded maximum redirects.")


def fetch_public_webpage(
    url: str,
    *,
    policy: WebFetchRuntimePolicy | None = None,
) -> dict[str, str | int | None]:
    return _fetch_public_text_resource(
        url,
        policy=policy,
        allowed_content_types=("text/html", "text/plain"),
    )


def fetch_public_text_resource(
    url: str,
    *,
    policy: WebFetchRuntimePolicy | None = None,
) -> dict[str, str | int | None]:
    return _fetch_public_text_resource(
        url,
        policy=policy,
        allowed_content_types=("text/plain", "text/html", "application/xml", "text/xml"),
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
