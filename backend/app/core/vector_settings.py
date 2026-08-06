import os

from dotenv import load_dotenv


load_dotenv()

VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "pgvector").lower()


def use_pgvector() -> bool:
    return VECTOR_BACKEND == "pgvector"


def use_chroma() -> bool:
    return VECTOR_BACKEND == "chroma"
