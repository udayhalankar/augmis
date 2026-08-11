from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from app.services.augmis_business_external_work_client import (
    AdzunaProvider,
    ArbeitnowProvider,
    RemotiveProvider,
    RemoteOkProvider,
)


class ExternalWorkProviderClientTests(unittest.TestCase):
    @patch("app.services.augmis_business_external_work_client.requests.get")
    def test_remoteok_public_feed_mapping(self, mock_get: Mock):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"legal": "ignore"},
            {
                "id": 42,
                "position": "Senior Python Automation Engineer",
                "company": "Example Tech",
                "location": "Worldwide",
                "tags": ["Python", "FastAPI", "Automation"],
                "description": "Contract remote automation role",
                "url": "https://remoteok.com/remote-jobs/42",
            },
        ]
        mock_get.return_value = mock_response

        result = RemoteOkProvider().search_opportunities({"maximum_results": 10})

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].external_id, "42")
        self.assertEqual(result[0].company_name, "Example Tech")
        self.assertEqual(result[0].skills, ["Python", "FastAPI", "Automation"])

    @patch("app.services.augmis_business_external_work_client.requests.get")
    def test_arbeitnow_public_api_mapping(self, mock_get: Mock):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "slug": "python-backend",
                    "title": "Python Backend Engineer",
                    "company_name": "Berlin Systems",
                    "location": "Berlin / Remote",
                    "description": "Build APIs and workflow systems.",
                    "remote": True,
                    "url": "https://arbeitnow.com/jobs/python-backend",
                    "tags": ["Python", "APIs"],
                    "job_types": ["Contract"],
                    "created_at": "2026-08-08T08:00:00+00:00",
                }
            ]
        }
        mock_get.return_value = mock_response

        result = ArbeitnowProvider().search_opportunities({"remote_only": True, "maximum_results": 10})

        self.assertEqual(result[0].external_id, "python-backend")
        self.assertTrue(result[0].remote)
        self.assertEqual(result[0].engagement_type, "contract")

    @patch("app.services.augmis_business_external_work_client.requests.get")
    def test_remotive_attribution_preserved(self, mock_get: Mock):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jobs": [
                {
                    "id": 77,
                    "title": "Integration Consultant",
                    "company_name": "Remote Platform",
                    "candidate_required_location": "Worldwide",
                    "category": "Software Development",
                    "job_type": "Contract",
                    "publication_date": "2026-08-08T10:00:00+00:00",
                    "url": "https://remotive.com/remote-jobs/software-dev/integration-consultant-77",
                    "description": "Integration and API consulting engagement.",
                    "tags": ["API", "Integration"],
                }
            ]
        }
        mock_get.return_value = mock_response

        result = RemotiveProvider().search_opportunities({"maximum_results": 10})

        self.assertEqual(result[0].provider, "remotive")
        self.assertEqual(result[0].source_url, "https://remotive.com/remote-jobs/software-dev/integration-consultant-77")
        self.assertEqual(result[0].employment_type, "Contract")

    @patch("app.services.augmis_business_external_work_client.requests.get")
    def test_adzuna_search_mapping(self, mock_get: Mock):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "adz-1",
                    "title": "Software Developer",
                    "description": "Contract software developer with API integration experience.",
                    "redirect_url": "https://adzuna.example/jobs/1",
                    "created": "2026-08-08T07:00:00+00:00",
                    "salary_min": 50000,
                    "salary_max": 70000,
                    "category": {"label": "IT Jobs"},
                    "company": {"display_name": "Adzuna Example"},
                    "contract_type": "contract",
                    "location": {"display_name": "London", "area": ["UK", "England", "London"]},
                }
            ]
        }
        mock_get.return_value = mock_response

        result = AdzunaProvider().search_opportunities(
            {"maximum_results": 10, "target_countries_json": ["gb"], "search_keyword": "software developer"},
            credential_payload={"app_id": "demo-id", "app_key": "demo-key-123456"},
        )

        self.assertEqual(result[0].external_id, "adz-1")
        self.assertEqual(result[0].country, "GB")
        self.assertEqual(result[0].salary_min, 50000)
        self.assertEqual(result[0].company_name, "Adzuna Example")


if __name__ == "__main__":
    unittest.main()
