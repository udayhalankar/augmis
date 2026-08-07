from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import requests

from app.services.augmis_business_web_search_provider import (
    BraveWebSearchProvider,
    MissingWebSearchApiKeyError,
    TavilyWebSearchProvider,
    WebSearchProviderError,
    get_web_search_provider,
)


class AugmisBusinessWebSearchProviderTest(unittest.TestCase):
    def setUp(self):
        self.brave_provider = BraveWebSearchProvider(api_key="brave-test-key")
        self.tavily_provider = TavilyWebSearchProvider(api_key="tvly-test-key")

    @patch("app.services.augmis_business_web_search_provider.requests.get")
    def test_brave_provider_maps_results(self, mock_get: Mock):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "url": "https://example.com/rfp",
                        "title": "Workflow Automation RFP",
                        "description": "Seeking vendor for workflow automation platform.",
                        "meta_url": {"hostname": "example.com"},
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        result = self.brave_provider.search(query="workflow automation RFP", count=5)
        self.assertEqual(result["provider"], "brave")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0].title, "Workflow Automation RFP")

    def test_brave_missing_api_key_is_reported(self):
        with self.assertRaises(MissingWebSearchApiKeyError) as exc:
            BraveWebSearchProvider(api_key=None).search(query="workflow", count=1)
        self.assertIn("brave", str(exc.exception).lower())

    @patch("app.services.augmis_business_web_search_provider.requests.get")
    def test_brave_rate_limit_is_reported(self, mock_get: Mock):
        mock_get.return_value = Mock(status_code=429)
        with self.assertRaises(WebSearchProviderError) as exc:
            self.brave_provider.search(query="workflow", count=1)
        self.assertIn("brave", str(exc.exception).lower())
        self.assertIn("rate limit", str(exc.exception).lower())

    @patch("app.services.augmis_business_web_search_provider.requests.get")
    def test_brave_invalid_key_response_is_reported(self, mock_get: Mock):
        mock_get.return_value = Mock(status_code=401)
        with self.assertRaises(WebSearchProviderError) as exc:
            self.brave_provider.search(query="workflow", count=1)
        self.assertIn("brave", str(exc.exception).lower())
        self.assertIn("invalid", str(exc.exception).lower())

    @patch("app.services.augmis_business_web_search_provider.requests.get")
    def test_brave_provider_5xx_is_reported(self, mock_get: Mock):
        mock_get.return_value = Mock(status_code=500)
        with self.assertRaises(WebSearchProviderError):
            self.brave_provider.search(query="workflow", count=1)

    @patch("app.services.augmis_business_web_search_provider.requests.get")
    def test_brave_malformed_json_is_reported(self, mock_get: Mock):
        mock_response = Mock(status_code=200)
        mock_response.json.side_effect = ValueError("bad json")
        mock_get.return_value = mock_response
        with self.assertRaises(WebSearchProviderError):
            self.brave_provider.search(query="workflow", count=1)

    @patch("app.services.augmis_business_web_search_provider.requests.post")
    def test_tavily_success_response_is_mapped(self, mock_post: Mock):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Dashboard Development Tender",
                    "url": "https://buyer.example/tender/dashboard",
                    "content": "Seeking dashboard and reporting implementation vendor.",
                    "score": 0.92,
                    "published_date": "2026-08-06",
                }
            ],
            "usage": {"credits": 1},
            "request_id": "req-1",
        }
        mock_post.return_value = mock_response
        result = self.tavily_provider.search(
            query="dashboard development tender",
            count=5,
            country="Kenya",
            freshness_days=30,
            exclude_domains=["jobs.example"],
        )
        self.assertEqual(result["provider"], "tavily")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["usage"], {"credits": 1})
        self.assertEqual(result["results"][0].provider_metadata["score"], 0.92)
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["country"], "kenya")
        self.assertEqual(kwargs["json"]["exclude_domains"], ["jobs.example"])

    def test_tavily_missing_api_key_is_reported(self):
        with self.assertRaises(MissingWebSearchApiKeyError) as exc:
            TavilyWebSearchProvider(api_key=None).search(query="workflow", count=1)
        self.assertIn("tavily", str(exc.exception).lower())

    @patch("app.services.augmis_business_web_search_provider.requests.post")
    def test_tavily_invalid_key_response_is_reported(self, mock_post: Mock):
        mock_post.return_value = Mock(status_code=401)
        with self.assertRaises(WebSearchProviderError) as exc:
            self.tavily_provider.search(query="workflow", count=1)
        self.assertIn("tavily", str(exc.exception).lower())
        self.assertIn("invalid", str(exc.exception).lower())

    @patch("app.services.augmis_business_web_search_provider.requests.post")
    def test_tavily_rate_limit_is_reported(self, mock_post: Mock):
        mock_post.return_value = Mock(status_code=429)
        with self.assertRaises(WebSearchProviderError) as exc:
            self.tavily_provider.search(query="workflow", count=1)
        self.assertIn("tavily", str(exc.exception).lower())
        self.assertIn("rate limit", str(exc.exception).lower())

    @patch("app.services.augmis_business_web_search_provider.requests.post")
    def test_tavily_timeout_is_reported(self, mock_post: Mock):
        mock_post.side_effect = requests.Timeout("slow")
        with self.assertRaises(WebSearchProviderError) as exc:
            self.tavily_provider.search(query="workflow", count=1)
        self.assertIn("timed out", str(exc.exception).lower())

    @patch("app.services.augmis_business_web_search_provider.requests.post")
    def test_tavily_malformed_result_is_reported(self, mock_post: Mock):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"results": "bad"}
        mock_post.return_value = mock_response
        with self.assertRaises(WebSearchProviderError) as exc:
            self.tavily_provider.search(query="workflow", count=1)
        self.assertIn("invalid results payload", str(exc.exception).lower())

    @patch("app.services.augmis_business_web_search_provider.requests.post")
    def test_tavily_empty_result_is_supported(self, mock_post: Mock):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"results": [], "usage": {"credits": 1}}
        mock_post.return_value = mock_response
        result = self.tavily_provider.search(query="workflow", count=1)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["raw_count"], 0)

    def test_provider_selection_returns_expected_provider(self):
        self.assertEqual(get_web_search_provider("tavily").name, "tavily")
        self.assertEqual(get_web_search_provider("brave").name, "brave")
        self.assertEqual(get_web_search_provider(None).name, "tavily")

    def test_unsupported_provider_does_not_fallback(self):
        with self.assertRaises(WebSearchProviderError):
            get_web_search_provider("unsupported")


if __name__ == "__main__":
    unittest.main()
