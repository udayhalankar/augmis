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
    BusinessDevelopmentConnectorSecret,
    BusinessDevelopmentDiscoveredOpportunity,
    BusinessDevelopmentDiscoveryTranslation,
    BusinessDevelopmentExperienceItem,
    BusinessDevelopmentSearchProvider,
    BusinessDevelopmentSearchProfile,
    Tenant,
    User,
)
from app.services import augmis_business_listener_service as service
from app.services.augmis_business_connector_credential_service import (
    resolve_provider_credential,
    save_connector_credential,
)
from app.services.augmis_business_search_provider_service import ensure_builtin_search_providers


class ExternalWorkPipelineTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(
            self.engine,
            tables=[
                Tenant.__table__,
                User.__table__,
                AuditLog.__table__,
                BusinessDevelopmentExperienceItem.__table__,
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
        self.current_user = {
            "tenant_id": "TENANT-1",
            "user_id": "USER-1",
            "permissions": ["business_development:read", "business_development:scan", "business_development:admin"],
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

    def tearDown(self):
        self.db.close()

    @patch("app.services.augmis_business_listener_service.FreelancerClient._get")
    def test_freelancer_mock_uses_no_external_http(self, mock_get: Mock):
        connector = service.ensure_freelancer_connector(self.db, "TENANT-1", self.current_user)
        connector.configuration_json = {**(connector.configuration_json or {}), "mode": "mock"}
        self.db.commit()

        result = service.run_connector_scan(self.db, "TENANT-1", connector.id, self.current_user)["data"]

        self.assertEqual(result["run"]["status"], "completed")
        self.assertGreaterEqual(result["run"]["items_found"], 10)
        self.assertEqual(result["run"]["run_metadata_json"]["api_call_count"], 0)
        self.assertFalse(mock_get.called)

    def test_freelancer_mock_stable_ids_dedupe(self):
        connector = service.ensure_freelancer_connector(self.db, "TENANT-1", self.current_user)
        connector.configuration_json = {**(connector.configuration_json or {}), "mode": "mock"}
        self.db.commit()

        first = service.run_connector_scan(self.db, "TENANT-1", connector.id, self.current_user)["data"]["run"]
        second = service.run_connector_scan(self.db, "TENANT-1", connector.id, self.current_user)["data"]["run"]

        self.assertGreaterEqual(first["items_new"], 1)
        self.assertGreaterEqual(first["items_filtered"], 1)
        self.assertEqual(second["items_new"], 0)
        self.assertGreaterEqual(second["items_duplicate"], 10)

    def test_freelancer_mock_has_all_relevance_bands(self):
        connector = service.ensure_freelancer_connector(self.db, "TENANT-1", self.current_user)
        connector.configuration_json = {**(connector.configuration_json or {}), "mode": "mock"}
        self.db.commit()

        result = service.run_connector_scan(self.db, "TENANT-1", connector.id, self.current_user)["data"]
        discoveries = result["discoveries"]
        bands = {item["relevance_band"] for item in discoveries}

        self.assertTrue({"strong", "good", "possible", "weak", "low"}.issubset(bands))

    def test_freelancer_production_still_requires_token(self):
        connector = service.ensure_freelancer_connector(self.db, "TENANT-1", self.current_user)
        connector.configuration_json = {**(connector.configuration_json or {}), "mode": "production"}
        self.db.commit()

        with self.assertRaisesRegex(Exception, "Freelancer access token is not configured."):
            service.FreelancerMarketplaceConnector().discover(connector=connector, search_profile=None, credential=None)

    def test_external_work_strong_software_contract_scores_high(self):
        candidate = service.AugmisBusinessDiscoveredOpportunityCandidate(
            external_id="job-1",
            source_type="employment_contract",
            source_name="Remote OK",
            title="Senior Python FastAPI Automation Contractor",
            organization_name="Example",
            requirement_summary="Contract remote role for Python FastAPI APIs, workflow automation and analytics dashboards.",
            raw_text="contract remote python fastapi api automation workflow analytics dashboard",
            source_metadata={"engagement_type": "contract", "employment_type": "contract", "remote": True},
        )
        score, _, _ = service._calculate_preliminary_relevance(candidate, None)
        self.assertGreaterEqual(score, 80)

    def test_sales_only_role_scores_low(self):
        candidate = service.AugmisBusinessDiscoveredOpportunityCandidate(
            external_id="job-2",
            source_type="employment_contract",
            source_name="Remote OK",
            title="Sales Representative",
            organization_name="Example",
            requirement_summary="Inside sales, telemarketing and customer service role.",
            raw_text="sales telemarketing customer service recruiter",
            source_metadata={"engagement_type": "full_time"},
        )
        score, _, _ = service._calculate_preliminary_relevance(candidate, None)
        self.assertLess(score, 35)

    def test_adzuna_credentials_encrypted(self):
        save_connector_credential(
            self.db,
            "TENANT-1",
            "adzuna",
            self.current_user,
            {"app_id": "demo-id", "app_key": "demo-key-123456"},
        )
        resolved = resolve_provider_credential(self.db, "TENANT-1", "adzuna")
        row = self.db.query(BusinessDevelopmentConnectorSecret).filter(BusinessDevelopmentConnectorSecret.provider == "adzuna").one()

        self.assertNotIn("demo-key-123456", row.encrypted_value)
        self.assertEqual(resolved.credential_payload["app_id"], "demo-id")
        self.assertEqual(resolved.credential_payload["app_key"], "demo-key-123456")

    def test_adzuna_credentials_required(self):
        connector = service.ensure_adzuna_connector(self.db, "TENANT-1", self.current_user)
        with self.assertRaisesRegex(Exception, "Adzuna credentials are not configured."):
            service.run_connector_scan(self.db, "TENANT-1", connector.id, self.current_user)


if __name__ == "__main__":
    unittest.main()
