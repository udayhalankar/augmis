from pathlib import Path

from app.utils.extraction import extract_file_text, extract_file_text_with_details


def parse_document(path: str) -> str:
    return extract_file_text(Path(path))


def parse_document_with_details(path: str) -> dict:
    return extract_file_text_with_details(Path(path))
