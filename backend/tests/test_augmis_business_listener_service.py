from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import augmis_business as augmis_business_routes
from app.core.database import Base, get_db
from app.core.security import get_current_user
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
from app.models.augmis_business_models import (
    AugmisBusinessConnectorScanRequest,
    AugmisBusinessConnectorUpdateRequest,
    AugmisBusinessSearchProfileCreateRequest,
)
from app.services import augmis_business_listener_service as service


class AugmisBusinessListenerServiceTest(unittest.TestCase):
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
        self.fixed_now = datetime(2026, 8, 7, 11, 0, 0, tzinfo=timezone.utc)
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
        self.read_only_user = {
            **self.current_user,
            "permissions": ["business_development:read"],
        }
        self._seed_core()

    def tearDown(self):
        service._now = self.original_now
        self.db.close()

    def _seed_core(self):
        self.db.add_all(
            [
                Tenant(tenant_id="TENANT-1", tenant_name="Tenant 1"),
                Tenant(tenant_id="TENANT-2", tenant_name="Tenant 2"),
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
                    name="Workflow Dashboard",
                    category="Applications",
                    description="Workflow and dashboard delivery experience.",
                    business_problems_json=["Manual workflows"],
                    features_json=["Approvals", "Dashboards"],
                    technologies_json=["React", "FastAPI"],
                    industries_json=["Utilities"],
                    keywords_json=["workflow", "dashboard", "portal"],
                    reusable_capabilities_json=["records management", "approval workflows"],
                    confidentiality_safe_summary="Reusable workflow experience.",
                    status="active",
                    created_by="USER-1",
                    updated_at=self.fixed_now,
                ),
            ]
        )
        self.db.commit()

    def test_default_profile_and_fixture_connector_are_seeded(self):
        profile = service.ensure_default_search_profile(self.db, "TENANT-1", self.current_user)
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        self.assertEqual(profile.name, service.DEFAULT_PROFILE_NAME)
        self.assertEqual(connector.connector_type, service.FIXTURE_CONNECTOR_TYPE)

    def test_search_profile_create_and_update(self):
        created = service.create_search_profile(
            self.db,
            "TENANT-1",
            self.current_user,
            AugmisBusinessSearchProfileCreateRequest(
                name="Africa Focus",
                target_regions_json=["Africa"],
                include_keywords_json=["inspection"],
            ),
        )["data"]
        self.assertEqual(created["name"], "Africa Focus")
        updated = service.update_search_profile(
            self.db,
            "TENANT-1",
            created["id"],
            self.current_user,
            service.AugmisBusinessSearchProfileUpdateRequest(enabled=False),  # type: ignore[attr-defined]
        )["data"]
        self.assertFalse(updated["enabled"])

    def test_fixture_scan_creates_new_duplicate_and_filtered_counts(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        profile = service.ensure_default_search_profile(self.db, "TENANT-1", self.current_user)
        profile.include_keywords_json = []
        profile.include_technologies_json = []
        profile.include_capabilities_json = []
        profile.exclude_keywords_json = ["records management"]
        self.db.commit()
        result = service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]
        run = result["run"]
        self.assertEqual(run["items_found"], 3)
        self.assertEqual(run["items_duplicate"], 1)
        self.assertEqual(run["items_filtered"], 1)
        self.assertEqual(run["items_new"], 1)

    def test_repeat_scan_counts_existing_external_ids_as_duplicates_without_error(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        first = service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]["run"]
        second = service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]["run"]

        self.assertEqual(first["status"], "completed")
        self.assertEqual(second["status"], "completed")
        self.assertEqual(second["items_new"], 0)
        self.assertEqual(second["items_duplicate"], 3)
        connector_row = service._require_connector(self.db, "TENANT-1", connector.id)
        self.assertEqual(connector_row.status, "ready")
        self.assertIsNone(connector_row.last_error_message)

    def test_overlap_protection_blocks_second_running_scan(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        running = BusinessDevelopmentConnectorRun(
            id="BD-RUN-LOCK-1",
            tenant_id="TENANT-1",
            connector_id=connector.id,
            run_type="manual",
            status="running",
            started_at=self.fixed_now,
            run_metadata_json={},
            initiated_by="USER-1",
        )
        self.db.add(running)
        self.db.commit()
        with self.assertRaises(Exception) as exc:
            service.run_connector_scan(
                self.db,
                "TENANT-1",
                connector.id,
                self.current_user,
                AugmisBusinessConnectorScanRequest(run_type="manual"),
            )
        self.assertIn("already in progress", str(exc.exception))

    def test_import_discovery_creates_opportunity_and_blocks_repeat(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )
        discovery = (
            self.db.query(BusinessDevelopmentDiscoveredOpportunity)
            .filter(
                BusinessDevelopmentDiscoveredOpportunity.tenant_id == "TENANT-1",
                BusinessDevelopmentDiscoveredOpportunity.discovery_status == "new",
            )
            .first()
        )
        self.assertIsNotNone(discovery)
        result = service.import_discovery_as_opportunity(
            self.db,
            "TENANT-1",
            discovery.id,  # type: ignore[union-attr]
            self.current_user,
        )["data"]
        self.assertEqual(result["discovery"]["discovery_status"], "imported")
        self.assertTrue(result["opportunity"]["id"].startswith("BD-OPP-"))
        with self.assertRaises(Exception) as exc:
            service.import_discovery_as_opportunity(
                self.db,
                "TENANT-1",
                discovery.id,  # type: ignore[union-attr]
                self.current_user,
            )
        self.assertIn("already been imported", str(exc.exception))

    def test_list_discoveries_is_tenant_scoped(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )
        rows = service.list_discoveries(self.db, "TENANT-2")["data"]
        self.assertEqual(rows, [])

    def test_update_connector_enables_and_disables_status(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        disabled = service.update_connector(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorUpdateRequest(enabled=False),
        )["data"]
        self.assertEqual(disabled["status"], "disabled")

    def test_route_permission_enforcement_blocks_scan_without_permission(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        app = FastAPI()
        app.include_router(augmis_business_routes.router)

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: self.read_only_user
        client = TestClient(app)
        response = client.post(
            f"/api/augmis-business/connectors/{connector.id}/scan",
            json={"run_type": "manual"},
        )
        self.assertEqual(response.status_code, 403)

    @patch("app.services.augmis_business_listener_service.test_connector_credential")
    def test_web_connector_test_uses_credential_resolution_path(self, mock_test_connector_credential: Mock):
        connector = service.ensure_web_search_connector(self.db, "TENANT-1", self.current_user)
        mock_test_connector_credential.return_value = {
            "data": {"result": {"success": True, "message": "Connection successful."}}
        }

        result = service.test_connector(self.db, "TENANT-1", self.current_user, connector.id)

        self.assertTrue(result["data"]["result"]["success"])
        mock_test_connector_credential.assert_called_once_with(
            self.db,
            "TENANT-1",
            "tavily",
            self.current_user,
        )

    @patch.object(service.WebOpportunitySearchConnector, "discover")
    @patch("app.services.augmis_business_listener_service.resolve_provider_credential")
    def test_web_connector_scan_uses_resolved_provider_credential(
        self,
        mock_resolve_provider_credential: Mock,
        mock_discover: Mock,
    ):
        connector = service.ensure_web_search_connector(self.db, "TENANT-1", self.current_user)
        resolved_credential = service.ResolvedProviderCredential(
            provider="tavily",
            api_key="tvly-tenant-1234",
            credential_source="tenant_secret",
        )
        mock_resolve_provider_credential.return_value = resolved_credential
        mock_discover.return_value = []

        result = service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )

        self.assertTrue(result["success"])
        mock_resolve_provider_credential.assert_called_once_with(self.db, "TENANT-1", "tavily")
        self.assertIs(mock_discover.call_args.kwargs["credential"], resolved_credential)

    def test_web_connector_defaults_are_preserved_when_runtime_config_is_absent(self):
        connector = service.ensure_web_search_connector(self.db, "TENANT-1", self.current_user)
        connector.configuration_json = {"provider": "tavily"}
        self.db.commit()

        implementation = service.WebOpportunitySearchConnector()
        implementation.validate_config(connector.configuration_json)
        policy = service._effective_web_search_runtime_policy(connector.configuration_json)

        self.assertEqual(policy.max_fetch_bytes, 300000)
        self.assertEqual(policy.fetch_timeout_seconds, 15)
        self.assertEqual(policy.max_extracted_text_chars, 30000)
        self.assertEqual(policy.max_redirects, 3)

    def test_web_connector_runtime_limits_below_minimum_are_rejected(self):
        implementation = service.WebOpportunitySearchConnector()
        with self.assertRaisesRegex(Exception, "max_fetch_bytes must be between 25000 and 1000000"):
            implementation.validate_config(
                {
                    "provider": "tavily",
                    "max_fetch_bytes": 1000,
                }
            )

    def test_web_connector_runtime_limits_above_ceiling_are_rejected(self):
        implementation = service.WebOpportunitySearchConnector()
        with self.assertRaisesRegex(Exception, "fetch_timeout_seconds must be between 3 and 30"):
            implementation.validate_config(
                {
                    "provider": "tavily",
                    "fetch_timeout_seconds": 60,
                }
            )

    @patch("app.services.augmis_business_listener_service.fetch_public_webpage")
    @patch("app.services.augmis_business_listener_service.extract_text_from_webpage")
    @patch("app.services.augmis_business_listener_service.get_web_search_provider")
    @patch("app.services.augmis_business_listener_service.resolve_provider_credential")
    def test_web_connector_respects_max_source_fetches_per_scan(
        self,
        mock_resolve_provider_credential: Mock,
        mock_get_provider: Mock,
        mock_extract_text: Mock,
        mock_fetch_public_webpage: Mock,
    ):
        connector = service.ensure_web_search_connector(self.db, "TENANT-1", self.current_user)
        connector.configuration_json = {
            **(connector.configuration_json or {}),
            "max_source_fetches_per_scan": 1,
            "max_candidate_results": 10,
        }
        self.db.commit()
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
                        "snippet": "Seeking workflow automation vendor.",
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
                        "title": "Reporting Dashboard Tender",
                        "url": "https://buyer.example/rfp/dashboard",
                        "snippet": "Seeking dashboard implementation vendor.",
                        "source_domain": "buyer.example",
                        "published_at": None,
                        "rank": 2,
                        "provider_metadata": {},
                    },
                )(),
            ],
        }
        mock_get_provider.return_value = mock_provider
        mock_fetch_public_webpage.return_value = {
            "url": "https://buyer.example/rfp/workflow",
            "status_code": 200,
            "content_type": "text/html",
            "body": "<html><body>Workflow automation proposal</body></html>",
            "bytes_read": 120,
        }
        mock_extract_text.return_value = "Workflow automation proposal"

        result = service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
        )["data"]

        self.assertEqual(result["run"]["run_metadata_json"]["source_pages_attempted"], 1)
        self.assertEqual(result["run"]["run_metadata_json"]["source_pages_skipped_due_limit"], 1)
        self.assertEqual(mock_fetch_public_webpage.call_count, 1)


if __name__ == "__main__":
    unittest.main()
