from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from app.services.augmis_business_freelancer_client import (
    FREELANCER_AUTH_HEADER,
    FreelancerApiError,
    FreelancerClient,
)


class FreelancerClientTest(unittest.TestCase):
    @patch("app.services.augmis_business_freelancer_client.requests.get")
    def test_test_connection_uses_official_auth_header(self, mock_get: Mock):
        response = Mock()
        response.ok = True
        response.json.return_value = {"result": {"id": 123}}
        mock_get.return_value = response

        result = FreelancerClient(access_token="token-123").test_connection()

        self.assertTrue(result["success"])
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["headers"][FREELANCER_AUTH_HEADER], "token-123")
        self.assertIn("/users/0.1/self", mock_get.call_args.args[0])

    @patch("app.services.augmis_business_freelancer_client.requests.get")
    def test_search_projects_maps_active_project_payload(self, mock_get: Mock):
        jobs_response = Mock()
        jobs_response.ok = True
        jobs_response.json.return_value = {"result": {"jobs": [{"id": 77, "name": "Python"}]}}

        projects_response = Mock()
        projects_response.ok = True
        projects_response.json.return_value = {
            "result": {
                "projects": [
                    {
                        "id": 555,
                        "title": "Build workflow automation platform",
                        "description": "Need React and Python delivery.",
                        "seo_url": "/projects/software/build-workflow-automation-platform",
                        "type": "fixed",
                        "status": "active",
                        "budget": {"minimum": 3000, "maximum": 5000},
                        "currency": {"code": "USD"},
                        "bid_stats": {"bid_count": 4, "bid_avg": 3500},
                        "time_submitted": 1786200000,
                        "time_updated": 1786203600,
                        "owner": {
                            "username": "buyer01",
                            "payment_verified": True,
                            "reputation": 4.9,
                            "review_count": 18,
                            "projects_posted": 21,
                            "projects_completed": 9,
                            "location": {"country": {"name": "Saudi Arabia"}, "city": {"name": "Riyadh"}},
                        },
                        "jobs": [
                            {"id": 77, "name": "Python", "category": {"name": "Web Development"}},
                            {"id": 88, "name": "React.js", "category": {"name": "Web Development"}},
                        ],
                    }
                ]
            }
        }
        mock_get.side_effect = [jobs_response, projects_response]

        client = FreelancerClient(access_token="token-123")
        job_ids = client.resolve_job_ids(["Python"])
        result = client.search_projects(query="workflow automation", limit=10, job_ids=list(job_ids.values()))

        self.assertEqual(job_ids["python"], 77)
        self.assertEqual(result["raw_count"], 1)
        project = result["projects"][0]
        self.assertEqual(project.project_id, "555")
        self.assertEqual(project.currency_code, "USD")
        self.assertEqual(project.skills, ["Python", "React.js"])
        self.assertEqual(project.client_country, "Saudi Arabia")
        self.assertTrue(project.client_payment_verified)

    @patch("app.services.augmis_business_freelancer_client.requests.get")
    def test_raises_safe_error_for_invalid_token(self, mock_get: Mock):
        response = Mock()
        response.ok = False
        response.status_code = 401
        response.headers = {}
        response.text = "Unauthorized"
        response.json.return_value = {"message": "Access token invalid"}
        mock_get.return_value = response

        with self.assertRaises(FreelancerApiError) as captured:
            FreelancerClient(access_token="bad-token").test_connection()

        self.assertEqual(str(captured.exception), "Freelancer authentication failed.")


if __name__ == "__main__":
    unittest.main()
