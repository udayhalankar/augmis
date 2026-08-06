from collections.abc import Callable

from app.services.procurement_dashboard_service import get_procurement_dashboard
from app.services.proposal_dashboard_service import get_proposal_dashboard
from app.services.vendor_dashboard_service import get_vendor_dashboard


DashboardLoader = Callable[..., dict]


_ENGINE_LOADERS: dict[str, DashboardLoader] = {
    "proposal": get_proposal_dashboard,
    "vendor": get_vendor_dashboard,
    "procurement": get_procurement_dashboard,
}


def get_supported_intelligence_engines() -> list[str]:
    return sorted(_ENGINE_LOADERS.keys())


def resolve_intelligence_engine_loader(engine_name: str | None) -> DashboardLoader | None:
    normalized = str(engine_name or "").strip().lower()
    return _ENGINE_LOADERS.get(normalized)
