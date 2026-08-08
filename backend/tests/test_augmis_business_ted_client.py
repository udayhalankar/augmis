from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from app.services import augmis_business_ted_client as ted_client
from app.services.augmis_business_ted_client import (
    TED_LEGACY_UNSUPPORTED_RESULT_FIELDS,
    TED_SEARCH_RESULT_FIELDS,
    TedApiError,
    TedSearchClient,
    build_ted_search_request_body,
    validate_ted_search_result_fields,
)


class TedSearchClientTest(unittest.TestCase):
    @patch("app.services.augmis_business_ted_client.requests.post")
    def test_request_payload_uses_canonical_alias_fields(self, mock_post: Mock):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "total": 1,
            "results": [
                {
                    "publication-number": ["123456-2026"],
                    "notice-identifier": ["TEN-0001"],
                    "notice-version": ["2"],
                    "notice-title": ["Workflow automation platform"],
                    "buyer-name": ["City Council"],
                    "buyer-country": ["DEU"],
                    "place-of-performance": ["DEU"],
                    "publication-date": ["20260808"],
                    "deadline": ["20260830"],
                    "notice-type": ["cn-standard"],
                    "procedure-type": ["open"],
                    "contract-nature": ["services"],
                    "classification-cpv": ["72262000", "48311100"],
                    "estimated-value-proc": ["95000"],
                    "estimated-value-cur-proc": ["EUR"],
                    "official-language": ["ENG"],
                    "announcement-url": ["https://ted.europa.eu/en/notice/123456-2026/html"],
                    "description-proc": ["Build workflow and reporting system"],
                }
            ],
        }
        mock_post.return_value = response

        result = TedSearchClient().search_notices(query="FT ~ workflow", page=1, limit=10)

        self.assertEqual(result["fields"], list(TED_SEARCH_RESULT_FIELDS))
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload, build_ted_search_request_body(query="FT ~ workflow", page=1, limit=10))
        self.assertTrue(set(payload["fields"]).issubset(set(TED_SEARCH_RESULT_FIELDS)))
        self.assertTrue(set(payload["fields"]).isdisjoint({"organization", "country", "source_url", "closing_date"}))

    def test_legacy_bt_and_opp_field_names_are_not_part_of_canonical_request(self):
        self.assertTrue(set(TED_LEGACY_UNSUPPORTED_RESULT_FIELDS).isdisjoint(set(TED_SEARCH_RESULT_FIELDS)))

    def test_invalid_field_configuration_fails_fast(self):
        with patch.object(
            ted_client,
            "TED_SEARCH_RESULT_FIELDS",
            TED_SEARCH_RESULT_FIELDS + ("organization",),
        ):
            with self.assertRaisesRegex(ValueError, "Unsupported TED search result field"):
                validate_ted_search_result_fields(ted_client.TED_SEARCH_RESULT_FIELDS)

    @patch("app.services.augmis_business_ted_client.requests.post")
    def test_missing_optional_values_map_safely(self, mock_post: Mock):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "total": 1,
            "results": [
                {
                    "publication-number": ["123456-2026"],
                    "notice-title": ["Workflow automation platform"],
                }
            ],
        }
        mock_post.return_value = response

        result = TedSearchClient().search_notices(query="FT ~ workflow", page=1, limit=10)

        notice = result["items"][0]
        self.assertIsNone(notice.buyer_name)
        self.assertIsNone(notice.deadline)
        self.assertEqual(notice.cpv_codes, [])
        self.assertEqual(notice.official_notice_url, "https://ted.europa.eu/en/notice/123456-2026/html")

    @patch("app.services.augmis_business_ted_client.requests.post")
    def test_multilingual_ted_payload_maps_successfully(self, mock_post: Mock):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "totalNoticeCount": 1,
            "notices": [
                {
                    "publication-number": "474387-2026",
                    "notice-identifier": "7fc9b0c8-3011-4547-9a20-c2a9763fdd68",
                    "notice-version": 1,
                    "buyer-country": ["FRA"],
                    "place-of-performance": ["FRA"],
                    "notice-type": "pin-only",
                    "publication-date": "2026-07-09+02:00",
                    "classification-cpv": ["72262000", "72230000"],
                    "buyer-name": {"fra": ["Commissariat a l'energie atomique"]},
                    "notice-title": {"eng": ["Maintenance of information technology software"]},
                    "description-proc": {"eng": ["Application maintenance and DevOps services"]},
                    "links": {
                        "htmlDirect": {
                            "ENG": "https://ted.europa.eu/en/notice/474387-2026/html",
                        }
                    },
                }
            ],
        }
        mock_post.return_value = response

        result = TedSearchClient().search_notices(query="FT ~ workflow", page=1, limit=10)

        notice = result["items"][0]
        self.assertEqual(notice.title, "Maintenance of information technology software")
        self.assertEqual(notice.buyer_name, "Commissariat a l'energie atomique")
        self.assertEqual(notice.official_notice_url, "https://ted.europa.eu/en/notice/474387-2026/html")
        self.assertEqual(notice.cpv_codes, ["72262000", "72230000"])

    @patch("app.services.augmis_business_ted_client.requests.post")
    def test_http_400_fields_error_is_concise_and_bounded(self, mock_post: Mock):
        response = Mock()
        response.status_code = 400
        response.headers = {"x-request-id": "ted-request-1"}
        long_error = (
            "Parameter 'fields' contains unsupported value (supported values are: "
            + ", ".join(f"field-{index}" for index in range(500))
            + ")"
        )
        response.json.return_value = {"message": long_error, "code": "BAD_REQUEST"}
        mock_post.return_value = response

        with self.assertRaises(TedApiError) as captured:
            TedSearchClient().search_notices(query="FT ~ workflow", page=1, limit=10)

        error = captured.exception
        self.assertEqual(
            str(error),
            "TED rejected the search request because the connector field configuration is invalid.",
        )
        self.assertEqual(error.http_status, 400)
        self.assertEqual(error.provider_error_code, "BAD_REQUEST")
        self.assertEqual(error.request_id, "ted-request-1")
        self.assertLessEqual(len(error.provider_message or ""), 240)
        self.assertNotIn("field-499", error.provider_message or "")

    @patch("app.services.augmis_business_ted_client.requests.post")
    def test_non_fields_http_400_uses_generic_rejection_message(self, mock_post: Mock):
        response = Mock()
        response.status_code = 400
        response.headers = {}
        response.json.return_value = {"message": "Query syntax invalid near FT"}
        mock_post.return_value = response

        with self.assertRaises(TedApiError) as captured:
            TedSearchClient().search_notices(query="FT ~ workflow", page=1, limit=10)

        self.assertEqual(str(captured.exception), "TED rejected the search request.")


if __name__ == "__main__":
    unittest.main()
