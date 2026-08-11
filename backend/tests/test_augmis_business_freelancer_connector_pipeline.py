from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.db_models import (
    AuditLog,
    BusinessDevelopmentConnector,
    BusinessDevelopmentConnectorRun,
    BusinessDevelopmentConnectorSecret,
    BusinessDevelopmentDiscoveredOpportunity,
    BusinessDevelopmentDiscoveryTranslation,
    BusinessDevelopmentExperienceItem,
    BusinessDevelopmentOpportunity,
    BusinessDevelopmentSearchProvider,
    BusinessDevelopmentSearchProfile,
    Tenant,
    User,
)
from app.services import augmis_business_listener_service as service
from app.services.augmis_business_connector_credential_service import save_connector_credential
from app.services.augmis_business_search_provider_service import ensure_builtin_search_providers


class AugmisBusinessFreelancerConnectorPipelineTest(unittest.TestCase):
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
                BusinessDevelopmentSearchProvider.__table__,
                BusinessDevelopmentConnectorSecret.__table__,
                BusinessDevelopmentDiscoveredOpportunity.__table__,
                BusinessDevelopmentDiscoveryTranslation.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.fixed_now = datetime(2026, 8, 8, 8, 0, 0, tzinfo=timezone.utc)
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
            ]
        )
        self.db.commit()
        ensure_builtin_search_providers(self.db)
        save_connector_credential(self.db, "TENANT-1", "freelancer", self.current_user, "frl-token-1234")

    def tearDown(self):
        service._now = self.original_now
        self.db.close()

    @patch("app.services.augmis_business_listener_service.FreelancerClient")
    def test_marketplace_pipeline_creates_and_dedupes_discoveries(self, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client.resolve_job_ids.return_value = {
            "python": 77,
            "react.js": 88,
            "artificial intelligence": 99,
            "automation": 55,
            "api": 66,
            "workflow": 44,
            "postgresql": 33,
            "data analytics": 22,
            "machine learning": 11,
            "web development": 101,
        }
        posted_at = self.fixed_now - timedelta(hours=2)
        updated_at = self.fixed_now - timedelta(hours=1)
        bid_end_at = self.fixed_now + timedelta(days=5)

        def project(
            project_id: str,
            title: str,
            bid_count: int,
            description: str,
            *,
            skills: list[str] | None = None,
            categories: list[str] | None = None,
        ):
            return type(
                "FreelancerProjectStub",
                (),
                {
                    "project_id": project_id,
                    "title": title,
                    "description": description,
                    "seo_url": f"/projects/software/{project_id}",
                    "project_type": "fixed",
                    "status": "active",
                    "currency_code": "USD",
                    "budget_min": 3000.0,
                    "budget_max": 5000.0,
                    "bid_count": bid_count,
                    "bid_avg": 3500.0,
                    "client_country": "Saudi Arabia",
                    "client_location": "Riyadh",
                    "client_rating": 4.9,
                    "client_review_count": 18,
                    "client_payment_verified": True,
                    "client_projects_posted": 21,
                    "client_projects_completed": 9,
                    "client_username": "market-buyer",
                    "skills": skills or ["Python", "React.js", "API"],
                    "categories": categories or ["Web Development"],
                    "posted_at": posted_at,
                    "updated_at": updated_at,
                    "bid_end_at": bid_end_at,
                    "raw_project": {"id": project_id, "title": title},
                },
            )()

        def search_projects_side_effect(*, query: str, **_: object):
            if query == "workflow automation":
                projects = [project("1001", "Build workflow automation platform", 4, "Need Python React workflow automation.")]
            elif query == "document management":
                projects = [project("1001", "Build workflow automation platform", 4, "Need Python React workflow automation.")]
            elif query == "dashboard reporting":
                projects = [
                    project(
                        "1002",
                        "Logo design for startup",
                        2,
                        "Need logo design brochure photoshop.",
                        skills=["Logo Design", "Photoshop"],
                        categories=["Graphic Design"],
                    )
                ]
            else:
                projects = []
            return {
                "api_call_count": 1,
                "raw_count": len(projects),
                "filtered_bid_count": 0,
                "projects": projects,
                "provider": "freelancer",
                "query": query,
            }

        mock_client.search_projects.side_effect = search_projects_side_effect

        connector = service.ensure_freelancer_connector(self.db, "TENANT-1", self.current_user)
        result = service.run_connector_scan(self.db, "TENANT-1", connector.id, self.current_user)["data"]

        self.assertEqual(result["run"]["status"], "completed")
        self.assertEqual(result["run"]["items_new"], 1)
        self.assertEqual(result["run"]["items_filtered"], 1)
        self.assertEqual(result["run"]["items_duplicate"], 0)
        self.assertEqual(len(result["discoveries"]), 2)
        active = next(item for item in result["discoveries"] if item["external_id"] == "1001")
        filtered = next(item for item in result["discoveries"] if item["external_id"] == "1002")
        self.assertEqual(active["source_type"], "marketplace_project")
        self.assertEqual(active["source_name"], "Freelancer")
        self.assertEqual(filtered["discovery_status"], "irrelevant")
        self.assertGreaterEqual(active["preliminary_relevance_score"], 65)
        self.assertLessEqual(filtered["preliminary_relevance_score"], 35)


if __name__ == "__main__":
    unittest.main()
