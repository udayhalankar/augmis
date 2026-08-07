from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.db_models import (
    AuditLog,
    BusinessDevelopmentConnector,
    BusinessDevelopmentConnectorRun,
    BusinessDevelopmentDiscoveredOpportunity,
    BusinessDevelopmentExperienceItem,
    BusinessDevelopmentOpportunity,
    BusinessDevelopmentSearchProfile,
    Tenant,
    User,
)
from app.services import augmis_business_listener_service as service


class AugmisBusinessWebSearchConnectorPipelineTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            self.engine,
            tables=[
                Tenant.__table__,
                User.__table__,
                AuditLog.__table__,
                BusinessDevelopmentExperienceItem.__table__,
                BusinessDevelopmentOpportunity.__table__,
                BusinessDevelopmentSearchProfile.__table__,
                BusinessDevelopmentConnector.__table__,
                BusinessDevelopmentConnectorRun.__table__,
                BusinessDevelopmentDiscoveredOpportunity.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.fixed_now = datetime(2026, 8, 7, 16, 0, 0, tzinfo=timezone.utc)
        self.original_now = service._now
        service._now = lambda: self.fixed_now
        self.current_user = {
            "tenant_id": "TENANT-1",
            "user_id": "USER-1",
            "permissions": [
                "business_development:read",
                "business_development:create",
                "business_development:update",
                "business_development:scan",
                "business_development:admin",
            ],
            "allowed_modules": ["augmis_business"],
        }
        self.db.add_all(
            [
                Tenant(tenant_id="TENANT-1", tenant_name="Tenant 1"),
                User(
                    user_id="USER-1",
                    tenant_id="TENANT-1",
                    name="Business Admin",
                    email="bd.admin@example.com",
                    password_hash="x",
                    role="tenant_admin",
                    status="ACTIVE",
                ),
                BusinessDevelopmentExperienceItem(
                    id="EXP-1",
                    tenant_id="TENANT-1",
                    name="Workflow Delivery",
                    category="Applications",
                    description="Workflow and dashboard experience.",
                    business_problems_json=[],
                    features_json=["Approvals", "Dashboards"],
                    technologies_json=["React", "FastAPI"],
                    industries_json=["Utilities"],
                    keywords_json=["workflow automation", "custom software"],
                    reusable_capabilities_json=["approval workflows"],
                    confidentiality_safe_summary="Workflow delivery experience.",
                    status="active",
                    created_by="USER-1",
                    updated_at=self.fixed_now,
                ),
            ]
        )
        self.db.commit()

    def tearDown(self):
        service._now = self.original_now
        self.db.close()

    @patch("app.services.augmis_business_listener_service.fetch_public_webpage")
    @patch("app.services.augmis_business_listener_service.extract_text_from_webpage")
    @patch("app.services.augmis_business_listener_service.get_web_search_provider")
    @patch("app.services.augmis_business_listener_service.resolve_provider_credential")
    def test_search_pipeline_accepts_opportunity_and_filters_job_noise(
        self,
        mock_resolve_provider_credential,
        mock_get_web_search_provider,
        mock_extract,
        mock_fetch,
    ):
        mock_resolve_provider_credential.return_value = service.ResolvedProviderCredential(
            provider="tavily",
            api_key="tvly-tenant-1234",
            credential_source="tenant_secret",
        )
        mock_provider = Mock()
        mock_provider.name = "tavily"
        mock_provider.search.return_value = {
            "provider": "tavily",
            "query": "workflow",
            "count": 2,
            "raw_count": 2,
            "api_call_count": 1,
            "usage": {"credits": 1},
            "results": [
                type(
                    "Result",
                    (),
                    {
                        "result_id": "1",
                        "title": "Workflow Automation RFP",
                        "url": "https://buyer.example/rfp/workflow",
                        "snippet": "Seeking vendor for workflow automation application.",
                        "source_domain": "buyer.example",
                        "published_at": None,
                        "rank": 1,
                        "provider_metadata": {},
                    },
                )(),
                type(
                    "Result",
                    (),
                    {
                        "result_id": "2",
                        "title": "Senior React Developer Job",
                        "url": "https://jobs.example/react-role",
                        "snippet": "Hiring a full-time React developer.",
                        "source_domain": "jobs.example",
                        "published_at": None,
                        "rank": 2,
                        "provider_metadata": {},
                    },
                )(),
            ],
        }
        mock_get_web_search_provider.return_value = mock_provider
        mock_fetch.return_value = {
            "url": "https://buyer.example/rfp/workflow",
            "status_code": 200,
            "content_type": "text/html",
            "body": "<html><body>Request for proposal for workflow automation software.</body></html>",
            "bytes_read": 120,
        }
        mock_extract.return_value = "Request for proposal for workflow automation software and dashboards."

        connector = service.ensure_web_search_connector(self.db, "TENANT-1", self.current_user)
        result = service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
        )["data"]

        self.assertEqual(result["run"]["status"], "completed")
        self.assertEqual(result["run"]["items_new"], 1)
        self.assertEqual(result["run"]["items_filtered"], 1)
        self.assertEqual(len(result["discoveries"]), 1)
        self.assertEqual(result["discoveries"][0]["source_type"], "web_search")
        self.assertEqual(result["run"]["run_metadata_json"]["provider"], "tavily")


if __name__ == "__main__":
    unittest.main()
