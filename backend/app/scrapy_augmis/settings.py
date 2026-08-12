from __future__ import annotations

from typing import Any

from app.core.config import settings


def build_scrapy_settings(configuration: dict[str, Any], max_fetch_bytes: int | None = None) -> dict[str, Any]:
    fetch_limit = int(max_fetch_bytes or settings.AUGMIS_WEB_DISCOVERY_DEFAULT_MAX_HTML_RESPONSE_BYTES)
    return {
        "LOG_ENABLED": False,
        "ROBOTSTXT_OBEY": True,
        "COOKIES_ENABLED": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": int(configuration.get("per_domain_delay_seconds", 2) or 2),
        "DOWNLOAD_TIMEOUT": int(configuration.get("request_timeout_seconds", 15) or 15),
        "DOWNLOAD_MAXSIZE": fetch_limit,
        "DOWNLOAD_WARNSIZE": fetch_limit,
        "DEPTH_LIMIT": int(configuration.get("maximum_depth", 2) or 2),
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 2,
        "USER_AGENT": settings.AUGMIS_WEB_DISCOVERY_USER_AGENT,
    }
