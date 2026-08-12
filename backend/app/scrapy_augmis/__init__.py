from typing import Any


def run_scrapy_independent_scan(*args: Any, **kwargs: Any):
    from app.services.augmis_business_independent_discovery_service import run_scrapy_independent_scan as _impl

    return _impl(*args, **kwargs)


__all__ = ["run_scrapy_independent_scan"]
