def index_uploaded_repository_document(upload_metadata: dict):
    # Legacy repository indexing depended on the Chroma vector service. Active
    # upload/index flows already use pgvector, so this path is disabled during
    # the pgvector-only validation phase.
    raise RuntimeError(
        "Legacy repository_indexing_service is disabled because it depends on Chroma. "
        "Use pgvector indexing paths instead."
    )
