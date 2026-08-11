from __future__ import annotations

from dataclasses import dataclass, field
from html import escape, unescape
from html.parser import HTMLParser
import re
from typing import Any
from urllib.parse import urlparse


ALLOWED_HTML_TAGS = {"p", "br", "strong", "b", "em", "i", "ul", "ol", "li", "h1", "h2", "h3", "h4", "blockquote", "a"}
BLOCK_LEVEL_TAGS = {"p", "ul", "ol", "li", "h1", "h2", "h3", "h4", "blockquote"}
SKIP_CONTENT_TAGS = {"script", "style", "iframe", "svg", "object", "embed", "form", "input", "button", "video", "audio"}
HTML_TAG_PATTERN = re.compile(r"</?[a-zA-Z][^>]*>")
WHITESPACE_PATTERN = re.compile(r"[ \t\r\f\v]+")
MULTI_NEWLINE_PATTERN = re.compile(r"\n{3,}")


def _normalize_whitespace(value: str) -> str:
    text = unescape(value or "")
    text = text.replace("\xa0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = WHITESPACE_PATTERN.sub(" ", text)
    lines = [line.strip() for line in text.split("\n")]
    normalized = "\n".join(lines)
    normalized = MULTI_NEWLINE_PATTERN.sub("\n\n", normalized)
    return normalized.strip()


def _is_html(value: str) -> bool:
    if not value or "<" not in value or ">" not in value:
        return False
    return bool(HTML_TAG_PATTERN.search(value))


def _safe_href(value: str | None) -> str | None:
    href = (value or "").strip()
    if not href:
        return None
    parsed = urlparse(href)
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    return href


@dataclass
class _NormalizationAccumulator:
    html_parts: list[str] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)
    list_depth: int = 0

    def append_text(self, value: str) -> None:
        if not value:
            return
        self.text_parts.append(value)

    def ensure_block_break(self) -> None:
        if self.text_parts and not self.text_parts[-1].endswith("\n\n"):
            if self.text_parts[-1].endswith("\n"):
                self.text_parts.append("\n")
            else:
                self.text_parts.append("\n\n")

    def ensure_line_break(self) -> None:
        if self.text_parts and not self.text_parts[-1].endswith("\n"):
            self.text_parts.append("\n")


class _SafeHtmlNormalizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.acc = _NormalizationAccumulator()
        self.skip_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if normalized in SKIP_CONTENT_TAGS:
            self.skip_stack.append(normalized)
            return
        if self.skip_stack:
            return
        if normalized not in ALLOWED_HTML_TAGS:
            return
        if normalized in {"p", "blockquote", "h1", "h2", "h3", "h4"}:
            self.acc.ensure_block_break()
        elif normalized in {"ul", "ol"}:
            self.acc.ensure_block_break()
            self.acc.list_depth += 1
        elif normalized == "li":
            self.acc.ensure_line_break()
            self.acc.append_text(f"{'  ' * max(0, self.acc.list_depth - 1)}• ")
        elif normalized == "br":
            self.acc.ensure_line_break()

        if normalized == "a":
            href = _safe_href(dict(attrs).get("href"))
            if href:
                self.acc.html_parts.append(f'<a href="{escape(href, quote=True)}" rel="noopener noreferrer">')
                return
            return
        self.acc.html_parts.append(f"<{normalized}>")

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if self.skip_stack:
            if self.skip_stack[-1] == normalized:
                self.skip_stack.pop()
            return
        if normalized not in ALLOWED_HTML_TAGS:
            return
        if normalized in {"p", "blockquote", "h1", "h2", "h3", "h4"}:
            self.acc.ensure_block_break()
        elif normalized in {"ul", "ol"}:
            self.acc.list_depth = max(0, self.acc.list_depth - 1)
            self.acc.ensure_block_break()
        elif normalized == "li":
            self.acc.ensure_line_break()
        if normalized != "br":
            self.acc.html_parts.append(f"</{normalized}>")

    def handle_data(self, data: str) -> None:
        if self.skip_stack:
            return
        had_leading_space = bool(data[:1] and data[:1].isspace())
        had_trailing_space = bool(data[-1:] and data[-1:].isspace())
        normalized = _normalize_whitespace(data)
        if not normalized:
            return
        plain_value = normalized
        html_value = escape(normalized)
        if had_leading_space:
            plain_value = f" {plain_value}"
            html_value = f" {html_value}"
        if had_trailing_space:
            plain_value = f"{plain_value} "
            html_value = f"{html_value} "
        self.acc.append_text(plain_value)
        self.acc.html_parts.append(html_value)

    def handle_entityref(self, name: str) -> None:
        self.handle_data(unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self.handle_data(unescape(f"&#{name};"))


def _render_plain_text_from_text(value: str) -> str:
    normalized = _normalize_whitespace(value)
    if not normalized:
        return ""
    lines = []
    for raw_line in normalized.split("\n"):
        line = raw_line.strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def normalize_source_content(html_or_text: str | None) -> dict[str, str]:
    source = str(html_or_text or "")
    if not source.strip():
        return {"plain_text": "", "safe_html": "", "detected_format": "text"}
    if not _is_html(source):
        plain_text = _render_plain_text_from_text(source)
        safe_html = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in plain_text.split("\n\n") if paragraph.strip())
        return {
            "plain_text": plain_text,
            "safe_html": safe_html,
            "detected_format": "text",
        }
    parser = _SafeHtmlNormalizer()
    parser.feed(source)
    parser.close()
    plain_text = _render_plain_text_from_text("".join(parser.acc.text_parts))
    safe_html = "".join(parser.acc.html_parts).strip()
    safe_html = re.sub(r"(?:<br>\s*){3,}", "<br><br>", safe_html)
    return {
        "plain_text": plain_text,
        "safe_html": safe_html,
        "detected_format": "html",
    }


def build_normalized_discovery_content(
    *,
    requirement_value: str | None,
    summary_value: str | None,
    full_text_value: str | None,
) -> dict[str, Any]:
    requirement = normalize_source_content(requirement_value)
    summary = normalize_source_content(summary_value)
    full_text = normalize_source_content(full_text_value)
    return {
        "requirement": requirement,
        "summary": summary,
        "full_text": full_text,
    }
