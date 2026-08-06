from typing import Any


def rebuild_index(
    datasource: str | None = None,
    current_user: dict | None = None,
    repository_id: str | None = None,
) -> dict[str, Any]:
    # Legacy local rebuild depended on the Chroma vector service. It is disabled
    # during the pgvector-only validation phase and should be replaced with a
    # real pgvector rebuild implementation if this workflow is still needed.
    raise RuntimeError(
        "Legacy rebuild_index is disabled because it depends on Chroma. "
        "Use pgvector indexing flows instead."
    )
