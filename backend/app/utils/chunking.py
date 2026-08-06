import re

from app.services.runtime_chunking_settings_service import get_chunking_settings


def clean_text(text: str) -> str:
    text = str(text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_text(
    text: str,
    max_chars: int | None = None,
    overlap: int | None = None,
) -> list[str]:
    text = clean_text(text)
    if not text:
        return []

    runtime_settings = get_chunking_settings()
    max_chars = int(max_chars or runtime_settings["max_chars"])
    overlap = int(overlap or runtime_settings["overlap_chars"])

    if max_chars < 200:
        max_chars = 200
    if overlap < 0:
        overlap = 0
    if overlap >= max_chars:
        overlap = max(0, max_chars // 5)

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = max(0, end - overlap)

    return chunks
