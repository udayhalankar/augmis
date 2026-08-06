from fastapi import HTTPException, status

from app.services.intelligence_engine_registry_service import (
    get_supported_intelligence_engines,
    resolve_intelligence_engine_loader,
)
from app.services.work_area_service import get_work_area_definition


def _normalize_area_key(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").replace("-", " ").split())


def get_business_area_dashboard(
    business_area: str,
    tenant_id: str,
    *,
    include_records: bool = True,
    force_refresh: bool = False,
    db=None,
):
    normalized_area = _normalize_area_key(business_area)
    work_area_definition = get_work_area_definition(tenant_id, normalized_area)

    if work_area_definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work area '{business_area}' was not found.",
        )

    pattern_engine = str(work_area_definition.get("dashboard_type") or "generic").strip().lower()
    loader = resolve_intelligence_engine_loader(pattern_engine)

    if loader is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No specialized intelligence dashboard is configured for '{business_area}'. "
                f"Set the intelligence pattern engine to one of: {', '.join(get_supported_intelligence_engines())}."
            ),
        )

    return loader(
        tenant_id,
        include_records=include_records,
        force_refresh=force_refresh,
        db=db,
    )
