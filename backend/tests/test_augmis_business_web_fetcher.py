from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from app.services.augmis_business_web_fetcher import WebFetchRuntimePolicy
from app.services.augmis_business_web_fetcher import (
    SafeWebFetchError,
    extract_text_from_webpage,
    fetch_public_webpage,
    validate_public_http_url,
)


class AugmisBusinessWebFetcherTest(unittest.TestCase):
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
        response = Mock(status_code=200, headers={"Content-Type": "text/html; charset=utf-8"}, encoding="utf-8")
        response.iter_content.return_value = [b"<html><body>Hello world</body></html>"]
        session = Mock()
        session.get.return_value = response
        mock_session_cls.return_value = session
        payload = fetch_public_webpage("https://example.com")
        self.assertIn("Hello world", str(payload["body"]))

    @patch("app.services.augmis_business_web_fetcher.validate_public_http_url")
    @patch("app.services.augmis_business_web_fetcher.requests.Session")
    def test_private_redirect_is_rejected(self, mock_session_cls: Mock, mock_validate: Mock):
        redirect = Mock(status_code=302, headers={"Location": "http://127.0.0.1/admin"})
        session = Mock()
        session.get.return_value = redirect
        mock_session_cls.return_value = session
        mock_validate.side_effect = [None, SafeWebFetchError("Private or local network targets are not allowed.")]
        with self.assertRaises(SafeWebFetchError):
            fetch_public_webpage("https://example.com")

    @patch("app.services.augmis_business_web_fetcher.validate_public_http_url")
    @patch("app.services.augmis_business_web_fetcher.requests.Session")
    def test_oversized_page_stops_safely(self, mock_session_cls: Mock, mock_validate: Mock):
        response = Mock(status_code=200, headers={"Content-Type": "text/html; charset=utf-8"}, encoding="utf-8")
        response.iter_content.return_value = [b"x" * 30000]
        session = Mock()
        session.get.return_value = response
        mock_session_cls.return_value = session
        with self.assertRaisesRegex(SafeWebFetchError, "configured fetch limit"):
            fetch_public_webpage(
                "https://example.com",
                policy=WebFetchRuntimePolicy(max_fetch_bytes=25000, fetch_timeout_seconds=10, max_redirects=3),
            )

    def test_extract_text_respects_custom_limit(self):
        extracted = extract_text_from_webpage("<html><body>Hello world example</body></html>", max_chars=5)
        self.assertEqual(extracted, "Hello")


if __name__ == "__main__":
    unittest.main()
