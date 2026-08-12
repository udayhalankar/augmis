from __future__ import annotations

import unittest
import requests
from unittest.mock import Mock, patch

from app.services.augmis_business_web_fetcher import WebFetchRuntimePolicy
from app.services.augmis_business_web_fetcher import (
    SafeWebFetchError,
    extract_text_from_webpage,
    fetch_public_webpage,
    validate_public_http_url,
)


class AugmisBusinessWebFetcherTest(unittest.TestCase):
    def _response(self, *, status_code: int, headers: dict[str, str] | None = None, chunks: list[bytes] | None = None):
        response = Mock(status_code=status_code, headers=headers or {}, encoding="utf-8")
        response.iter_content.return_value = chunks or [b""]
        return response

    @patch("app.services.augmis_business_web_fetcher.socket.getaddrinfo")
    def test_public_https_url_is_allowed(self, mock_getaddrinfo: Mock):
        mock_getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 0))]
        validate_public_http_url("https://example.com/test")

    @patch("app.services.augmis_business_web_fetcher.socket.getaddrinfo")
    def test_localhost_is_rejected(self, mock_getaddrinfo: Mock):
        mock_getaddrinfo.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
        with self.assertRaises(SafeWebFetchError):
            validate_public_http_url("http://127.0.0.1/test")

    @patch("app.services.augmis_business_web_fetcher.socket.getaddrinfo")
    def test_private_ip_is_rejected(self, mock_getaddrinfo: Mock):
        mock_getaddrinfo.return_value = [(None, None, None, None, ("10.1.2.3", 0))]
        with self.assertRaises(SafeWebFetchError):
            validate_public_http_url("https://internal.example/test")

    @patch("app.services.augmis_business_web_fetcher.socket.getaddrinfo")
    def test_unsupported_scheme_is_rejected(self, mock_getaddrinfo: Mock):
        with self.assertRaises(SafeWebFetchError):
            validate_public_http_url("file:///tmp/test")

    @patch("app.services.augmis_business_web_fetcher.validate_public_http_url")
    @patch("app.services.augmis_business_web_fetcher.requests.Session")
    def test_fetch_reads_html_content(self, mock_session_cls: Mock, mock_validate: Mock):
        response = self._response(
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            chunks=[b"<html><body>Hello world</body></html>"],
        )
        session = Mock()
        session.get.return_value = response
        mock_session_cls.return_value = session
        payload = fetch_public_webpage("https://example.com")
        self.assertIn("Hello world", str(payload["body"]))

    @patch("app.services.augmis_business_web_fetcher.validate_public_http_url")
    @patch("app.services.augmis_business_web_fetcher.requests.Session")
    def test_private_redirect_is_rejected(self, mock_session_cls: Mock, mock_validate: Mock):
        redirect = self._response(status_code=302, headers={"Location": "http://127.0.0.1/admin"})
        session = Mock()
        session.get.return_value = redirect
        mock_session_cls.return_value = session
        mock_validate.side_effect = [None, SafeWebFetchError("Private or local network targets are not allowed.")]
        with self.assertRaises(SafeWebFetchError):
            fetch_public_webpage("https://example.com")

    @patch("app.services.augmis_business_web_fetcher.validate_public_http_url")
    @patch("app.services.augmis_business_web_fetcher.requests.Session")
    def test_oversized_page_stops_safely(self, mock_session_cls: Mock, mock_validate: Mock):
        response = self._response(
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            chunks=[b"x" * 30000],
        )
        session = Mock()
        session.get.return_value = response
        mock_session_cls.return_value = session
        with self.assertRaisesRegex(SafeWebFetchError, "configured HTML response size limit"):
            fetch_public_webpage(
                "https://example.com",
                policy=WebFetchRuntimePolicy(max_fetch_bytes=25000, fetch_timeout_seconds=10, max_redirects=3),
            )

    @patch("app.services.augmis_business_web_fetcher.requests.Session")
    @patch("app.services.augmis_business_web_fetcher._resolve_public_http_url")
    def test_content_length_oversized_html_is_rejected_before_streaming(self, mock_resolve: Mock, mock_session_cls: Mock):
        mock_resolve.return_value = ("example.com", ["8.8.8.8"])
        response = self._response(
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8", "Content-Length": "1500000"},
            chunks=[b"x" * 4096],
        )
        session = Mock()
        session.get.return_value = response
        mock_session_cls.return_value = session
        with self.assertRaises(SafeWebFetchError) as ctx:
            fetch_public_webpage(
                "https://example.com/large",
                policy=WebFetchRuntimePolicy(max_fetch_bytes=1000000, fetch_timeout_seconds=10, max_redirects=3),
            )
        self.assertEqual(ctx.exception.code, "BODY_TOO_LARGE")
        self.assertEqual(ctx.exception.content_length, 1500000)
        response.iter_content.assert_not_called()

    @patch("app.services.augmis_business_web_fetcher.requests.Session")
    @patch("app.services.augmis_business_web_fetcher._resolve_public_http_url")
    def test_http_403_is_not_retryable(self, mock_resolve: Mock, mock_session_cls: Mock):
        mock_resolve.return_value = ("example.com", ["8.8.8.8"])
        session = Mock()
        session.get.return_value = self._response(status_code=403, headers={"Content-Type": "text/html"})
        mock_session_cls.return_value = session
        with self.assertRaises(SafeWebFetchError) as ctx:
            fetch_public_webpage("https://example.com/forbidden")
        self.assertEqual(ctx.exception.code, "HTTP_403")
        self.assertFalse(ctx.exception.retryable)

    @patch("app.services.augmis_business_web_fetcher.requests.Session")
    @patch("app.services.augmis_business_web_fetcher._resolve_public_http_url")
    def test_http_429_honors_retry_after(self, mock_resolve: Mock, mock_session_cls: Mock):
        mock_resolve.return_value = ("example.com", ["8.8.8.8"])
        session = Mock()
        session.get.return_value = self._response(
            status_code=429,
            headers={"Content-Type": "text/html", "Retry-After": "120"},
        )
        mock_session_cls.return_value = session
        with self.assertRaises(SafeWebFetchError) as ctx:
            fetch_public_webpage("https://example.com/rate-limited")
        self.assertEqual(ctx.exception.code, "HTTP_429")
        self.assertTrue(ctx.exception.retryable)
        self.assertEqual(ctx.exception.retry_after, "120")

    @patch("app.services.augmis_business_web_fetcher.requests.Session")
    @patch("app.services.augmis_business_web_fetcher._resolve_public_http_url")
    def test_http_5xx_is_retryable(self, mock_resolve: Mock, mock_session_cls: Mock):
        mock_resolve.return_value = ("example.com", ["8.8.8.8"])
        session = Mock()
        session.get.return_value = self._response(status_code=503, headers={"Content-Type": "text/html"})
        mock_session_cls.return_value = session
        with self.assertRaises(SafeWebFetchError) as ctx:
            fetch_public_webpage("https://example.com/unavailable")
        self.assertEqual(ctx.exception.code, "HTTP_5XX")
        self.assertTrue(ctx.exception.retryable)

    @patch("app.services.augmis_business_web_fetcher.requests.Session")
    @patch("app.services.augmis_business_web_fetcher._resolve_public_http_url")
    def test_connection_timeout_is_retryable(self, mock_resolve: Mock, mock_session_cls: Mock):
        mock_resolve.return_value = ("example.com", ["8.8.8.8"])
        session = Mock()
        session.get.side_effect = requests.ConnectTimeout("timed out")
        mock_session_cls.return_value = session
        with self.assertRaises(SafeWebFetchError) as ctx:
            fetch_public_webpage("https://example.com/slow")
        self.assertEqual(ctx.exception.code, "CONNECTION_TIMEOUT")
        self.assertTrue(ctx.exception.retryable)

    @patch("app.services.augmis_business_web_fetcher.requests.Session")
    @patch("app.services.augmis_business_web_fetcher._resolve_public_http_url")
    def test_application_xhtml_is_accepted(self, mock_resolve: Mock, mock_session_cls: Mock):
        mock_resolve.return_value = ("example.com", ["8.8.8.8"])
        session = Mock()
        session.get.return_value = self._response(
            status_code=200,
            headers={"Content-Type": "application/xhtml+xml; charset=utf-8"},
            chunks=[b"<html><body>XHTML</body></html>"],
        )
        mock_session_cls.return_value = session
        payload = fetch_public_webpage("https://example.com/xhtml")
        self.assertEqual(payload["content_type"], "application/xhtml+xml; charset=utf-8")

    @patch("app.services.augmis_business_web_fetcher.requests.Session")
    @patch("app.services.augmis_business_web_fetcher._resolve_public_http_url")
    def test_binary_content_type_is_rejected(self, mock_resolve: Mock, mock_session_cls: Mock):
        mock_resolve.return_value = ("example.com", ["8.8.8.8"])
        session = Mock()
        session.get.return_value = self._response(status_code=200, headers={"Content-Type": "application/pdf"})
        mock_session_cls.return_value = session
        with self.assertRaises(SafeWebFetchError) as ctx:
            fetch_public_webpage("https://example.com/file.pdf")
        self.assertEqual(ctx.exception.code, "ATTACHMENT_SKIPPED")
        self.assertEqual(ctx.exception.resource_kind, "pdf")

    def test_extract_text_respects_custom_limit(self):
        extracted = extract_text_from_webpage("<html><body>Hello world example</body></html>", max_chars=5)
        self.assertEqual(extracted, "Hello")


if __name__ == "__main__":
    unittest.main()
