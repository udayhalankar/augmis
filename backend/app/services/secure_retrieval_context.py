from app.services.repository_service import (
    get_allowed_business_areas,
    get_allowed_repository_ids,
)


def build_secure_retrieval_filter(current_user: dict):
    allowed_repository_ids = get_allowed_repository_ids(
        current_user,
        permission_type="read",
    )
    allowed_business_areas = get_allowed_business_areas(
        current_user,
        permission_type="read",
    )

    return {
        "tenant_id": current_user["tenant_id"],
        "repository_ids": allowed_repository_ids,
        "business_areas": allowed_business_areas,
    }


def build_chroma_where_filter(current_user: dict):
    # Legacy Chroma-specific retrieval filter is intentionally disabled during
    # pgvector-only validation. The pgvector retrieval path uses its own access
    # filtering instead of a Chroma where-clause.
    raise RuntimeError(
        "build_chroma_where_filter is disabled because the Chroma path is being phased out."
    )
