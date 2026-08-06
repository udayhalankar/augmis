from pathlib import Path


class VectorService:
    """Legacy Chroma wrapper kept as a temporary stub during pgvector-only validation."""

    def __init__(self):
        # The old Chroma client setup is intentionally commented out during the
        # pgvector-only validation phase.
        #
        # import chromadb
        # from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
        # from app.core.config import settings
        #
        # self.client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        # self.embedding_function = OpenAIEmbeddingFunction(
        #     api_key=settings.OPENAI_API_KEY,
        #     model_name=settings.OPENAI_EMBEDDING_MODEL,
        # )
        # self.collection_cache = None
        self.collection_cache = None

    @staticmethod
    def _disabled() -> RuntimeError:
        return RuntimeError(
            "Legacy Chroma vector service is disabled while the application is being "
            "validated on pgvector-only paths."
        )

    def get_collection(self, reset: bool = False):
        raise self._disabled()

    @staticmethod
    def make_doc_id(path: Path, chunk_no: int, text: str) -> str:
        raise VectorService._disabled()

    def add_documents(self, ids: list[str], documents: list[str], metadatas: list[dict]):
        raise self._disabled()

    def query(
        self,
        query: str,
        n_results: int = 8,
        business_area: str = "All",
        where_filter: dict | None = None,
    ) -> list[dict]:
        raise self._disabled()

    def stats(self):
        raise self._disabled()


vector_service = VectorService()
