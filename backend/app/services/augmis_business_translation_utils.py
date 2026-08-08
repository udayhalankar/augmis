from __future__ import annotations

from hashlib import sha256
from typing import Any

from app.db_models import BusinessDevelopmentDiscoveredOpportunity


LANGUAGE_LABELS: dict[str, str] = {
    "en": "English",
    "eng": "English",
    "de": "German",
    "deu": "German",
    "fr": "French",
    "fra": "French",
    "pl": "Polish",
    "pol": "Polish",
    "hu": "Hungarian",
    "hun": "Hungarian",
    "nl": "Dutch",
    "nld": "Dutch",
    "es": "Spanish",
    "spa": "Spanish",
    "it": "Italian",
    "ita": "Italian",
    "pt": "Portuguese",
    "por": "Portuguese",
    "ro": "Romanian",
    "ron": "Romanian",
    "cs": "Czech",
    "ces": "Czech",
    "sk": "Slovak",
    "slk": "Slovak",
    "sv": "Swedish",
    "swe": "Swedish",
    "da": "Danish",
    "dan": "Danish",
    "fi": "Finnish",
    "fin": "Finnish",
}

TED_LANGUAGE_NORMALIZATION: dict[str, str] = {
    "ENG": "en",
    "DEU": "de",
    "GER": "de",
    "FRA": "fr",
    "FRE": "fr",
    "POL": "pl",
    "HUN": "hu",
    "NLD": "nl",
    "DUT": "nl",
    "ESP": "es",
    "SPA": "es",
    "ITA": "it",
    "POR": "pt",
    "RON": "ro",
    "RUM": "ro",
    "CES": "cs",
    "CZE": "cs",
    "SLK": "sk",
    "SLO": "sk",
    "SWE": "sv",
    "DAN": "da",
    "FIN": "fi",
}

COMMON_LANGUAGE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pl", (" zamowienia ", "doradztwo", "uslugi", "postepowania", "gmina ", "szpitalu ")),
    ("de", (" und ", "leistung", "dienstleistungen", "rahmenvereinbarung", "stadt ")),
    ("fr", (" prestations ", "mise en ", "marches", "travaux", "consultation")),
    ("hu", (" szolgaltatas", " magyarorszag ", " beszerzes ", " keretmegallapodas ")),
    ("nl", (" aanbesteding ", " ontwikkeling ", " bezoekersstromen ", " gemeente ")),
)


def normalize_language_code(value: str | None) -> str | None:
    normalized = (value or "").strip()
    if not normalized:
        return None
    upper = normalized.upper()
    if upper in TED_LANGUAGE_NORMALIZATION:
        return TED_LANGUAGE_NORMALIZATION[upper]
    lower = normalized.lower()
    if lower in LANGUAGE_LABELS:
        return lower
    if len(lower) == 2:
        return lower
    return None


def language_label(code: str | None) -> str:
    normalized = normalize_language_code(code)
    if not normalized:
        return "Unknown"
    return LANGUAGE_LABELS.get(normalized, normalized.upper())


def is_english_language(code: str | None) -> bool:
    normalized = normalize_language_code(code)
    return normalized == "en"


def detect_discovery_language(row: BusinessDevelopmentDiscoveredOpportunity) -> str | None:
    raw = row.raw_content_json or {}
    source_metadata_candidates = (
        raw.get("official_language"),
        raw.get("source_language"),
        raw.get("language"),
    )
    for candidate in source_metadata_candidates:
        normalized = normalize_language_code(str(candidate) if candidate is not None else None)
        if normalized:
            return normalized

    text = " ".join(
        part.lower()
        for part in [row.title or "", row.requirement_summary or "", row.raw_summary or ""]
        if part
    )
    if not text:
        return None
    for language_code, hints in COMMON_LANGUAGE_HINTS:
        if any(hint.strip() and hint.strip() in text for hint in hints):
            return language_code
    return "en" if all(ord(character) < 128 for character in text[:240]) else None


def discovery_translation_payload(row: BusinessDevelopmentDiscoveredOpportunity) -> dict[str, Any]:
    raw = row.raw_content_json or {}
    ted_notice = raw.get("ted_notice") if isinstance(raw.get("ted_notice"), dict) else {}
    additional_information = ted_notice.get("additional-information") if isinstance(ted_notice, dict) else None
    additional_information_lot = ted_notice.get("additional-information-lot") if isinstance(ted_notice, dict) else None
    payload = {
        "title": row.title,
        "summary": row.requirement_summary or row.raw_summary,
        "description": row.raw_text or row.requirement_summary or row.raw_summary,
        "additional_information": additional_information,
        "additional_information_lot": additional_information_lot,
        "source_language": detect_discovery_language(row),
        "source_type": row.source_type,
        "source_name": row.source_name,
        "publication_number": raw.get("publication_number"),
        "notice_identifier": raw.get("notice_identifier"),
        "official_language": raw.get("official_language"),
        "estimated_currency": raw.get("estimated_currency"),
        "estimated_value": raw.get("estimated_value"),
        "cpv_codes": raw.get("cpv_codes"),
    }
    return payload


def discovery_translation_source_hash(row: BusinessDevelopmentDiscoveredOpportunity, source_language: str | None) -> str:
    payload = discovery_translation_payload(row)
    payload["source_language"] = source_language
    encoded = repr(payload).encode("utf-8", errors="ignore")
    return sha256(encoded).hexdigest()
